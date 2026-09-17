"""prepare_documents: the deterministic Intake tool that splits a tender package into sheets (spec 0.7 stage 1).

No model is involved. Every PDF in the dataset inputs becomes one PDF, one PNG, and one text file
per page under `runs/<run_id>/prepared/`, and `manifest.md` (with `manifest.json` beside it) lists
every sheet with its sheet number, title, discipline, "Issued for" stamp, revision date, page count,
and legibility confidence. A field the title block does not yield is recorded as `unknown`, never
guessed (CLAUDE.md rule 14); the Intake Analyst raises an assumption for it.

The title block rules are heuristics over the text layer, written so a miss produces `unknown`
rather than a wrong value: a labelled field ("SHEET", "SHEET TITLE") is taken as written; otherwise
a sheet number is accepted only when exactly one candidate appears in the tail of the page text, a
title only when it sits right after that number and is not a title block label, and a stamp only
when every "Issued for" phrase on the page agrees.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pypdfium2 as pdfium

from app.live.documents import _confidence

UNKNOWN = "unknown"
NOT_APPLICABLE = "n/a"
MANIFEST_MD = "manifest.md"
MANIFEST_JSON = "manifest.json"
PREPARED_DIR = "prepared"
MAX_IMAGE_SIDE = 4000
MIN_RENDER_SCALE = 0.5
TAIL_CHARS = 400
TITLE_WINDOW = 120
TITLE_BLOCK_CHARS = 160
DISCIPLINES = {"A": "A", "E": "E", "M": "M", "S": "S", "P": "P"}
DRAWING_FIELDS = ("sheet_number", "title", "discipline", "issued_for", "revision_date")

_SHEET = re.compile(r"(?<![A-Z0-9])([A-Z]{1,2})-?(\d{3}|\d\.\d{1,2})(?![A-Z0-9.])")
_SHEET_LABEL = re.compile(
    r"(?:SHEET|DWG|DRAWING)\s*(?:NO\.?|NUMBER|#)?\s*[:\r\n]+\s*([A-Z]{1,2}-?\d{3}|[A-Z]\d\.\d{1,2})(?![A-Z0-9.])",
    re.I,
)
_TITLE_LABEL = re.compile(r"(?:SHEET|DRAWING)\s+TITLE\s*[:\r\n]+\s*([^\r\n]{3,80})", re.I)
_TITLE = re.compile(r"\b([A-Z]{2,}(?:[ &/-]+[A-Z]{2,}){1,7})\b")
_LABEL_WORDS = frozenset(
    "VERSION DESCRIPTION DATE SCALE SHEET NUMBER DRAWN CHECKED ISSUED PROJECT STATUS CLIENT CONSULTANT STAMP "
    "REVISION REVISIONS TITLE NTS NORTH".split()
)
_ISSUED = re.compile(r"ISSUED\s+FOR:?\s+([A-Z][A-Z /&]{2,40}?)(?=\s+\d|\s*[\r\n]|\s{2,}|$)", re.I)
_ISO_DATE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
_DMY_DATE = re.compile(r"\b(\d{1,2})[ -]([A-Z]{3})[A-Z]*[,.]?[ -](\d{2,4})\b", re.I)
_MONTHS = {
    m: i
    for i, m in enumerate(
        ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1
    )
}
_STAMP_NOISE = re.compile(r"[^A-Z /&]")
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class TitleBlock:
    sheet_number: str = UNKNOWN
    title: str = UNKNOWN
    discipline: str = UNKNOWN
    issued_for: str = UNKNOWN
    revision_date: str = UNKNOWN

    def unknown_fields(self) -> tuple[str, ...]:
        return tuple(name for name in DRAWING_FIELDS if getattr(self, name) == UNKNOWN)


@dataclass(frozen=True)
class SheetRecord:
    sheet_id: str
    source: str
    page: int
    page_count: int
    kind: str
    sheet_number: str
    title: str
    discipline: str
    issued_for: str
    revision_date: str
    confidence: float
    pdf: str
    png: str
    text: str
    unknown_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class PreparedFile:
    source: str
    kind: str
    page_count: int
    sheets: list[SheetRecord] = field(default_factory=list)
    problem: str | None = None
    duration_ms: int = 0

    def summary(self) -> str:
        if self.problem:
            return self.problem
        unknown = sum(len(s.unknown_fields) for s in self.sheets)
        names = ", ".join(s.sheet_id for s in self.sheets[:6]) + (", ..." if len(self.sheets) > 6 else "")
        text = f"{self.page_count} page{'s' if self.page_count != 1 else ''}, sheets {names}"
        if self.kind == "drawing":
            text += f"; {unknown} title block field{'s' if unknown != 1 else ''} unknown"
        return text


@dataclass(frozen=True)
class Prepared:
    folder: Path
    files: list[PreparedFile]
    manifest_ms: int = 0

    @property
    def sheets(self) -> list[SheetRecord]:
        return [s for f in self.files for s in f.sheets]

    def drawing_sheets(self) -> list[SheetRecord]:
        return [s for s in self.sheets if s.kind == "drawing"]

    def unknown_count(self) -> int:
        return sum(len(s.unknown_fields) for s in self.sheets)

    def sheet(self, name: str) -> SheetRecord | None:
        wanted = name.lower()
        for record in self.sheets:
            if record.sheet_id.lower() == wanted or record.sheet_number.lower() == wanted:
                return record
        return None


# Title block reading


def _normalize_date(day: str, month: str, year: str) -> str | None:
    number = _MONTHS.get(month[:3].lower())
    if number is None:
        return None
    y = int(year)
    y = y + 2000 if y < 100 else y
    try:
        return dt.date(y, number, int(day)).isoformat()
    except ValueError:
        return None


def _date_in(text: str) -> str | None:
    iso = _ISO_DATE.search(text)
    if iso:
        try:
            return dt.date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3))).isoformat()
        except ValueError:
            return None
    dmy = _DMY_DATE.search(text)
    if dmy:
        return _normalize_date(dmy.group(1), dmy.group(2), dmy.group(3))
    return None


def _sheet_number(text: str, tail: str) -> str:
    """A labelled sheet number wins; otherwise the one candidate in the tail of the page, else unknown."""
    labelled = _SHEET_LABEL.search(text)
    if labelled:
        return labelled.group(1).upper()
    candidates = list(
        dict.fromkeys(
            f"{m.group(1)}{'-' if '-' in m.group(0) else ''}{m.group(2)}" for m in _SHEET.finditer(tail)
        )
    )
    return candidates[0] if len(candidates) == 1 else UNKNOWN


def _is_label_row(text: str) -> bool:
    words = [w for w in re.split(r"[^A-Za-z]+", text.upper()) if w]
    return ":" in text or not words or any(w in _LABEL_WORDS for w in words)


def _title(text: str, tail: str, sheet_number: str) -> str:
    """A labelled title wins unless it is a row of labels; otherwise the first run of two or more capitalised
    words right after the sheet number, when that number sits in the title block at the end of the page text
    and the run is not a title block label; else unknown."""
    labelled = _TITLE_LABEL.search(text)
    if labelled and not _is_label_row(labelled.group(1)):
        return labelled.group(1).strip()
    if sheet_number == UNKNOWN or sheet_number not in tail:
        return UNKNOWN
    position = tail.rfind(sheet_number)
    if len(tail) - position > TITLE_BLOCK_CHARS:
        return UNKNOWN
    window = tail[position + len(sheet_number) :][:TITLE_WINDOW]
    for match in _TITLE.finditer(window):
        if not _is_label_row(match.group(1)):
            return match.group(1).strip()
    return UNKNOWN


def _stamp(text: str) -> tuple[str, str]:
    """The "Issued for" stamp when every occurrence on the page agrees, and the date written beside it."""
    phrases: dict[str, int] = {}
    for match in _ISSUED.finditer(text):
        phrase = _STAMP_NOISE.sub("", match.group(1).upper()).strip()
        phrase = re.sub(r"^(?:ISSUED FOR:?\s*)+", "", phrase).strip()
        if len(phrase) >= 3:
            phrases.setdefault(phrase, match.end())
    if len(phrases) != 1:
        return UNKNOWN, UNKNOWN
    phrase, end = next(iter(phrases.items()))
    return phrase.capitalize(), _date_in(text[end : end + 40]) or UNKNOWN


def read_title_block(text: str, tail_chars: int = TAIL_CHARS) -> TitleBlock:
    """Read what the page text states about itself. Anything ambiguous is unknown."""
    if not text.strip():
        return TitleBlock()
    tail = text[-tail_chars:]
    sheet_number = _sheet_number(text, tail)
    discipline = DISCIPLINES.get(sheet_number[0], "other") if sheet_number != UNKNOWN else UNKNOWN
    title = _title(text, tail, sheet_number)
    issued_for, revision_date = _stamp(text)
    return TitleBlock(sheet_number, title, discipline, issued_for, revision_date)


# Splitting


def _safe(name: str) -> str:
    return _SAFE_NAME.sub("-", name).strip("-") or "sheet"


def _unique(base: str, used: set[str], page: int) -> str:
    name = base
    if name.lower() in used:
        name = f"{base}-p{page:02d}"
    counter = 2
    while name.lower() in used:
        name = f"{base}-p{page:02d}-{counter}"
        counter += 1
    used.add(name.lower())
    return name


def _render(page: pdfium.PdfPage) -> bytes:
    width, height = page.get_size()
    scale = min(MAX_IMAGE_SIDE / max(width, height, 1.0), 150 / 72)
    scale = max(scale, MIN_RENDER_SCALE)
    bitmap = page.render(scale=scale)
    try:
        image = bitmap.to_pil()
    finally:
        bitmap.close()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _single_page_pdf(source: pdfium.PdfDocument, index: int, target: Path) -> None:
    document = pdfium.PdfDocument.new()
    try:
        document.import_pages(source, pages=[index])
        document.save(str(target))
    finally:
        document.close()


def _page_text(page: pdfium.PdfPage) -> str:
    try:
        textpage = page.get_textpage()
    except pdfium.PdfiumError:
        return ""
    try:
        return str(textpage.get_text_bounded())
    finally:
        textpage.close()


NO_TITLE_BLOCK = TitleBlock(NOT_APPLICABLE, NOT_APPLICABLE, NOT_APPLICABLE, NOT_APPLICABLE, NOT_APPLICABLE)


def prepare_file(path: Path, source: str, kind: str, out_dir: Path, used: set[str]) -> PreparedFile:
    """Split one PDF into per-page files. An unreadable file is recorded, never skipped silently."""
    started = time.monotonic()
    if path.suffix.lower() != ".pdf":
        return PreparedFile(source, kind, 0, problem="not a PDF; passed through unread")
    try:
        document = pdfium.PdfDocument(str(path))
    except pdfium.PdfiumError:
        return PreparedFile(source, kind, 0, problem="unreadable PDF; every field unknown")
    sheets: list[SheetRecord] = []
    stem = _safe(path.stem)
    try:
        count = len(document)
        for index in range(count):
            page = document[index]
            try:
                text = _page_text(page)
                png = _render(page)
            finally:
                page.close()
            block = read_title_block(text) if kind == "drawing" else NO_TITLE_BLOCK
            if count == 1:
                base = stem
            elif block.sheet_number not in (UNKNOWN, NOT_APPLICABLE):
                base = _safe(block.sheet_number)
            else:
                base = f"{stem}-p{index + 1:02d}"
            sheet_id = _unique(base, used, index + 1)
            names = (f"{sheet_id}.pdf", f"{sheet_id}.png", f"{sheet_id}.txt")
            _single_page_pdf(document, index, out_dir / names[0])
            (out_dir / names[1]).write_bytes(png)
            (out_dir / names[2]).write_text(text, encoding="utf-8", newline="\n")
            sheets.append(
                SheetRecord(
                    sheet_id=sheet_id,
                    source=source,
                    page=index + 1,
                    page_count=count,
                    kind=kind,
                    sheet_number=block.sheet_number,
                    title=block.title,
                    discipline=block.discipline,
                    issued_for=block.issued_for,
                    revision_date=block.revision_date,
                    confidence=_confidence(text) if text else 0.0,
                    pdf=names[0],
                    png=names[1],
                    text=names[2],
                    unknown_fields=block.unknown_fields() if kind == "drawing" else (),
                )
            )
    finally:
        document.close()
    return PreparedFile(source, kind, count, sheets, duration_ms=int((time.monotonic() - started) * 1000))


def prepare_documents(request_files: list[Path], drawing_files: list[Path], out_dir: Path) -> Prepared:
    """Prepare every input file into `out_dir` and write the manifest. Deterministic: same inputs, same output."""
    out_dir.mkdir(parents=True, exist_ok=True)
    used: set[str] = set()
    files: list[PreparedFile] = []
    for path in request_files:
        files.append(prepare_file(path, path.name, "request", out_dir, used))
    for path in drawing_files:
        files.append(prepare_file(path, f"drawings/{path.name}", "drawing", out_dir, used))
    started = time.monotonic()
    write_manifest(Prepared(out_dir, files))
    return Prepared(out_dir, files, int((time.monotonic() - started) * 1000))


# Manifest


def write_manifest(prepared: Prepared) -> None:
    rows = [
        "| Sheet | Source | Page | Sheet number | Title | Discipline | Issued for | Revision date | "
        "Pages in source | Legibility |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in prepared.sheets:
        rows.append(
            f"| {s.sheet_id} | {s.source} | {s.page} | {s.sheet_number} | {s.title} | {s.discipline} | "
            f"{s.issued_for} | {s.revision_date} | {s.page_count} | {s.confidence:.2f} |"
        )
    problems = [f"- {f.source}: {f.problem}" for f in prepared.files if f.problem]
    count = len(prepared.files)
    lines = [
        "# Prepared documents",
        "",
        "Written by prepare_documents, a deterministic tool with no model call. Each sheet has a PDF, a PNG, and "
        "a text file named after it in this folder. A field that reads `unknown` could not be read from the "
        "title block; grade it as an assumption, do not guess it. `n/a` marks a request document, which has no "
        "title block.",
        "",
        f"Sheets: {len(prepared.sheets)} from {count} file{'s' if count != 1 else ''}. "
        f"Drawing sheets: {len(prepared.drawing_sheets())}. Title block fields unknown: {prepared.unknown_count()}.",
        "",
        *rows,
    ]
    if problems:
        lines += ["", "Files with problems:", *problems]
    (prepared.folder / MANIFEST_MD).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    data = {
        "sheets": [asdict(s) for s in prepared.sheets],
        "files": [
            {
                "source": f.source,
                "kind": f.kind,
                "page_count": f.page_count,
                "problem": f.problem,
                "sheets": [s.sheet_id for s in f.sheets],
            }
            for f in prepared.files
        ],
    }
    (prepared.folder / MANIFEST_JSON).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )


def read_manifest(folder: Path) -> Prepared | None:
    """The prepared set of a run folder, or None when Intake has not prepared anything yet."""
    path = folder / MANIFEST_JSON
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    by_source: dict[str, list[SheetRecord]] = {}
    for raw in data.get("sheets", []):
        raw = dict(raw)
        raw["unknown_fields"] = tuple(raw.get("unknown_fields", ()))
        record = SheetRecord(**raw)
        by_source.setdefault(record.source, []).append(record)
    files = [
        PreparedFile(
            f["source"], f["kind"], int(f["page_count"]), by_source.get(f["source"], []), f.get("problem")
        )
        for f in data.get("files", [])
    ]
    return Prepared(folder, files)
