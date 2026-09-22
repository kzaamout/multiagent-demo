"""The compile pipeline: markdown to Typst with a template, Typst to PDF and page images, then the
marker positions and the page text (spec 0.7 section 8; S4 decisions 1b, 2a, 3b).

Shape reused from the career-hub `compile-to-pdf` scripts: pandoc `-t typst --template`, then
`typst compile` for the PDF, `typst compile --format png --ppi 150` for the pages, and the
intermediate `.typ` kept beside the outputs. Every tool runs as a subprocess without a shell and
with a timeout, and a failure surfaces as `CompileError` carrying the tool's first error line.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from app.compile.brand import Brand
from app.compile.markers import MarkerDraft, prepare_markdown, with_appendix
from app.live.documents import parse_pdf

ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES = ROOT / "templates"
RESPONSE_TEMPLATE = TEMPLATES / "rfp-response.typ"
PPI = 150
POINTS_PER_INCH = 72
STEP_TIMEOUT_S = 60
VERSION_TIMEOUT_S = 10
ARTIFACTS = "artifacts"

_TOOL_VERSION = re.compile(r"(\d+\.\d+(?:\.\d+)?)")


class CompileError(RuntimeError):
    """A compile step failed; the message is the tool's first error line."""


@dataclass(frozen=True)
class Marker:
    n: int
    tag_id: str
    source_id: str
    page: int
    x: float
    y: float
    label: str
    """What the page prints for this marker. Recordings made before 2026-09-21 have no label, and the
    panel shows their number, which is what their pages print."""


@dataclass(frozen=True)
class Compiled:
    version: int
    pdf_path: str
    page_images: list[str]
    marker_count: int
    unresolved: list[int]
    page_count: int
    elapsed_ms: int
    tool_versions: dict[str, str]
    markers_path: str
    pages_path: str
    typ_path: str

    def to_json(self) -> dict[str, object]:
        return asdict(self)


def tools_available() -> dict[str, str | None]:
    """Version of each external tool, or None when it is not on the path or does not answer."""
    found: dict[str, str | None] = {}
    for name in ("pandoc", "typst"):
        exe = shutil.which(name)
        if exe is None:
            found[name] = None
            continue
        try:
            out = subprocess.run(
                [exe, "--version"], capture_output=True, text=True, timeout=VERSION_TIMEOUT_S, check=False
            )
        except (OSError, subprocess.TimeoutExpired):
            found[name] = None
            continue
        match = _TOOL_VERSION.search(out.stdout or "")
        found[name] = match.group(1) if match else None
    return found


def _run(args: list[str], cwd: Path, step: str) -> subprocess.CompletedProcess[str]:
    try:
        done = subprocess.run(
            args, cwd=str(cwd), capture_output=True, text=True, timeout=STEP_TIMEOUT_S, check=False
        )
    except FileNotFoundError as error:
        raise CompileError(f"{step}: {args[0]} is not on the path") from error
    except subprocess.TimeoutExpired as error:
        raise CompileError(f"{step}: {args[0]} did not finish within {STEP_TIMEOUT_S} s") from error
    if done.returncode != 0:
        raise CompileError(f"{step}: {_first_error_line(done.stderr, done.stdout)}")
    return done


def _first_error_line(stderr: str, stdout: str) -> str:
    for text in (stderr, stdout):
        for line in text.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("warning") and not stripped.startswith("= hint"):
                return stripped
    return "the tool reported an error without a message"


def _pandoc(markdown_path: Path, typ_path: Path, template: Path, variables: Mapping[str, str]) -> None:
    args = ["pandoc", "-f", "markdown-smart", "-t", "typst", "--template", str(template)]
    for key, value in variables.items():
        args += ["-V", f"{key}={value}"]
    args += ["-o", str(typ_path), str(markdown_path)]
    _run(args, typ_path.parent, "pandoc")


def _typst_pdf(typ_path: Path, pdf_path: Path) -> None:
    _run(["typst", "compile", typ_path.name, pdf_path.name], typ_path.parent, "typst pdf")


def _page_texts(typ_path: Path, pdf_path: Path) -> list[str]:
    """The text of each page as the Reviewer reads it, with each provenance marker written " [a]".

    Extracted from the page as displayed, a superscript marker is glued to its figure. While markers
    were numbers, one price tagged five times read $79,063.751 to $79,063.755, and the Reviewer failed
    that as five different prices: 113 of its 125 blocker findings say figures disagree, and 14 of the 22
    runs that spent their whole review budget failed on a disagreement that exists only in this text. So
    the text comes from a second compile in which the template writes the marker in brackets. That
    compile is for reading only and is removed; if it fails, the displayed page's text is better than
    none, and a letter glued to a figure cannot be read as one of its digits.
    """
    text_pdf = pdf_path.with_name(pdf_path.stem + ".text.pdf")
    try:
        _run(
            ["typst", "compile", "--input", "markers=text", typ_path.name, text_pdf.name],
            typ_path.parent,
            "typst text",
        )
        return [p.text for p in parse_pdf(text_pdf)]
    except CompileError:
        return [p.text for p in parse_pdf(pdf_path)]
    finally:
        text_pdf.unlink(missing_ok=True)


def _typst_pages(typ_path: Path, stem: str) -> list[Path]:
    folder = typ_path.parent
    for old in folder.glob(f"{stem}-*.png"):
        old.unlink()
    _run(
        ["typst", "compile", "--format", "png", "--ppi", str(PPI), typ_path.name, f"{stem}-{{p}}.png"],
        folder,
        "typst png",
    )
    produced = sorted(folder.glob(f"{stem}-*.png"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))
    pages: list[Path] = []
    for index, path in enumerate(produced, start=1):
        target = folder / f"page-{index:02d}.png"
        if target.exists():
            target.unlink()
        path.rename(target)
        pages.append(target)
    return pages


def _typst_markers(typ_path: Path, drafts: list[MarkerDraft]) -> list[Marker]:
    folder = typ_path.parent
    try:
        done = _run(["typst", "query", typ_path.name, "<prov>", "--field", "value"], folder, "typst query")
        raw = done.stdout
    except CompileError:
        done = _run(
            ["typst", "eval", "query(<prov>).map(it => it.value)", "--in", typ_path.name, "--format", "json"],
            folder,
            "typst eval",
        )
        raw = done.stdout
    values = json.loads(raw or "[]")
    by_n = {int(v["n"]): v for v in values if isinstance(v, dict) and "n" in v}
    scale = PPI / POINTS_PER_INCH
    markers: list[Marker] = []
    for d in drafts:
        v = by_n.get(d.n)
        if v is None:
            continue
        markers.append(
            Marker(
                n=d.n,
                tag_id=d.tag_id,
                source_id=d.source_id,
                page=int(v["page"]),
                x=round(float(v["x"]) * scale, 1),
                y=round(float(v["y"]) * scale, 1),
                label=d.label,
            )
        )
    return markers


def _stage_logo(brand: Brand, folder: Path) -> str:
    if brand.logo_path is None:
        return ""
    target = folder / f"logo{brand.logo_path.suffix.lower()}"
    shutil.copyfile(brand.logo_path, target)
    return target.name


def compile_draft(
    run_folder: Path,
    version: int,
    markdown: str,
    brand: Brand,
    sources: Mapping[str, str] | None = None,
    headlines: Mapping[str, str] | None = None,
    template: Path = RESPONSE_TEMPLATE,
    client: str = "",
) -> Compiled:
    """Compile one draft version into `runs/<id>/artifacts/v<N>/` and return the record.

    `sources` maps short source ids to event ids; a marker whose source id is absent is listed in
    `unresolved`. `headlines` maps short source ids to the headline printed in the appendix.
    """
    started = time.monotonic()
    folder = run_folder / ARTIFACTS / f"v{version}"
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"draft-v{version}"

    prepared, drafts = prepare_markdown(markdown)
    prepared = with_appendix(prepared, drafts, headlines)
    markdown_path = folder / f"{stem}.prepared.md"
    markdown_path.write_text(prepared, encoding="utf-8", newline="\n")

    typ_path = folder / f"{stem}.typ"
    pdf_path = folder / f"{stem}.pdf"
    variables = {
        "prospect-name": brand.prospect_name,
        # Whose letterhead this is, and who it is for, are two different names. The cover used the
        # prospect's name for both, so a proposal on the bidder's letterhead said it was prepared for the
        # bidder, while the body addressed the client the brief names. Reviewers raised that 12 times in
        # the 42 run sweep of 2026-09-19, as a blocker 10 times, and it ended 3 runs with the review
        # budget spent, because no rework can change a cover that comes from configuration.
        "client-name": client,
        "logo-path": _stage_logo(brand, folder),
        "primary-colour": brand.primary_colour,
        "version": str(version),
    }
    _pandoc(markdown_path, typ_path, template, variables)
    _typst_pdf(typ_path, pdf_path)
    pages = _typst_pages(typ_path, stem)
    markers = _typst_markers(typ_path, drafts)
    texts = _page_texts(typ_path, pdf_path)
    if len(texts) < len(pages):
        texts += [""] * (len(pages) - len(texts))

    markers_path = folder / "markers.json"
    markers_path.write_text(
        json.dumps([asdict(m) for m in markers], indent=1), encoding="utf-8", newline="\n"
    )
    pages_path = folder / "pages.json"
    pages_path.write_text(json.dumps(texts, indent=1), encoding="utf-8", newline="\n")

    def relative(path: Path) -> str:
        return path.relative_to(run_folder).as_posix()

    unresolved = [d.n for d in drafts if sources is not None and d.source_id not in sources]
    versions = {k: v for k, v in tools_available().items() if v is not None}
    compiled = Compiled(
        version=version,
        pdf_path=relative(pdf_path),
        page_images=[relative(p) for p in pages],
        marker_count=len(markers),
        unresolved=unresolved,
        page_count=len(pages),
        elapsed_ms=int((time.monotonic() - started) * 1000),
        tool_versions=versions,
        markers_path=relative(markers_path),
        pages_path=relative(pages_path),
        typ_path=relative(typ_path),
    )
    (folder / "compiled.json").write_text(
        json.dumps(compiled.to_json(), indent=1), encoding="utf-8", newline="\n"
    )
    return compiled


def read_compiled(run_folder: Path, version: int) -> Compiled | None:
    """The record a compile left for a version, or None when that version was never compiled."""
    path = run_folder / ARTIFACTS / f"v{version}" / "compiled.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Compiled(**data)


def render_markdown(
    markdown: str, template: Path, variables: Mapping[str, str], out_dir: Path, stem: str
) -> Path:
    """Compile plain markdown (no markers) to `<out_dir>/<stem>.pdf` through the same two steps."""
    out_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = out_dir / f"{stem}.md"
    markdown_path.write_text(markdown, encoding="utf-8", newline="\n")
    typ_path = out_dir / f"{stem}.typ"
    pdf_path = out_dir / f"{stem}.pdf"
    _pandoc(markdown_path, typ_path, template, variables)
    _typst_pdf(typ_path, pdf_path)
    return pdf_path
