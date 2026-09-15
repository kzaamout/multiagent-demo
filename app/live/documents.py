"""PDF text, legibility, and page images with pypdfium2 (research D6).

Legibility is a heuristic, not a standard: the share of extracted characters that are letters,
digits, whitespace, or common punctuation. A page with fewer than 20 extracted characters scores
0.3, meaning it probably has no text layer and must be read visually. Review the heuristic on
the curated dataset.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium

MIN_TEXT_CHARS = 20
NO_TEXT_LAYER_CONFIDENCE = 0.3
RENDER_DPI = 150
_PUNCTUATION = set(".,;:!?()[]{}'\"-/%&#*+=<>@$_|\\")


@dataclass(frozen=True)
class PageText:
    page: int
    text: str
    confidence: float


def _confidence(text: str) -> float:
    stripped = text.strip()
    if len(stripped) < MIN_TEXT_CHARS:
        return NO_TEXT_LAYER_CONFIDENCE
    good = sum(1 for ch in stripped if ch.isalnum() or ch.isspace() or ch in _PUNCTUATION)
    return round(min(1.0, good / len(stripped)), 2)


def parse_pdf(path: Path) -> list[PageText]:
    """Text and a legibility confidence for every page. An unreadable file yields no pages."""
    try:
        document = pdfium.PdfDocument(str(path))
    except pdfium.PdfiumError:
        return []
    pages: list[PageText] = []
    try:
        for index in range(len(document)):
            page = document[index]
            try:
                textpage = page.get_textpage()
                try:
                    text = textpage.get_text_bounded()
                finally:
                    textpage.close()
            except pdfium.PdfiumError:
                text = ""
            finally:
                page.close()
            pages.append(PageText(page=index + 1, text=text, confidence=_confidence(text) if text else 0.0))
    finally:
        document.close()
    return pages


def page_count(path: Path) -> int:
    document = pdfium.PdfDocument(str(path))
    try:
        return len(document)
    finally:
        document.close()


def render_page_png(path: Path, page_number: int, dpi: int = RENDER_DPI) -> bytes:
    """Render one page (1-based) to PNG bytes for a vision model."""
    document = pdfium.PdfDocument(str(path))
    try:
        if not 1 <= page_number <= len(document):
            raise ValueError(f"{path.name} has no page {page_number}")
        page = document[page_number - 1]
        try:
            bitmap = page.render(scale=dpi / 72)
            try:
                image = bitmap.to_pil()
            finally:
                bitmap.close()
        finally:
            page.close()
    finally:
        document.close()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
