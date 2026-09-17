# Quickstart: verify S6

Prerequisites: S4 setup (Typst and pandoc on the path), a recording for the pinned run id under the runs folder, `PUBLIC_RUN_ID` in `.env` when it differs from the default.

## Gates

```
uv run python scripts/check.py
uv run pytest -m visual
```

## The page

```
$env:PYTHONUTF8 = "1"
uv run uvicorn app.main:app --port 8000
```

Open http://localhost:8000/introduction in a private window (no session exists yet; after S7 the page stays public).

1. **Sections.** Scroll the seven sections; the copy is the content files word for word; no em dash.
2. **Diagrams.** The architecture bands, the fully lit loop with three labelled backward arrows and the exits card, and the two-up demo-versus-production drawing with laptop and AgentCore badges.
3. **Team.** Eight cards; click any to expand role, owns, sees, tools; the six seats show today's model labels.
4. **Replay.** The frame at the bottom plays the pinned run; switch to 4x; open a thread and a prompt toggle inside the frame; the pages and markers appear when the compiled events fire; no Run, Pause, Stop, Approve, Edit or Reject anywhere in the frame; no link leaves the frame.
5. **Public boundary.** In the same private window open `/public/run/<another recorded id>/events`: 404. Open `/api/runs/<pinned id>/events`: it answers today and will need the login after S7.
6. **PDF.** Open http://localhost:8000/introduction.pdf, or run `uv run python scripts/intro_pdf.py`; the PDF carries every section and the three drawings.

## Evidence to record

The pinned run id and its dataset and exit; the screenshot comparison result; the content diff result; the PDF page count; the roadmap S6 status line.
