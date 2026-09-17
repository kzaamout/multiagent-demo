"""Compile a committed draft into a PDF and page images (spec 0.7 section 8, slice S4).

The pipeline is the career-hub one: pandoc turns the markdown into Typst source with a template,
Typst compiles that source to a PDF and to one PNG per page, and the intermediate source is kept
beside the outputs. Provenance tags become numbered markers whose positions Typst reports, so the
artifact panel can lay hover targets over the page images. Nothing here emits an event: the module
writes files and returns a record, and the Orchestrator emits `artifact.compiled` from it.
"""

from __future__ import annotations

from app.compile.brand import Brand, read_brand
from app.compile.markers import MarkerDraft, appendix, prepare_markdown
from app.compile.pipeline import Compiled, CompileError, compile_draft, tools_available
from app.compile.timeline import compile_timeline

__all__ = [
    "Brand",
    "Compiled",
    "CompileError",
    "MarkerDraft",
    "appendix",
    "compile_draft",
    "compile_timeline",
    "prepare_markdown",
    "read_brand",
    "tools_available",
]
