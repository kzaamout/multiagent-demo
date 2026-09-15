"""FastAPI application: static pages flattened from the design export, the run API, and the
server-sent event stream. Contract: specs/001-event-spine-stubbed-loop/contracts/http-api.md.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agents.stubs import bundle_for
from app.buildinfo import build_info
from app.config import Settings, load_settings
from app.orchestrator.orchestrator import Answer
from app.runs.bus import StreamBus
from app.runs.registry import Registry
from app.runs.replay import ReplaySession
from app.schema.bundles import PromptBundle

KEEPALIVE_SECONDS = 15.0


class RunRequest(BaseModel):
    dataset_id: str
    workflow: str = "electrical_rfp"
    mode: Literal["team"] = "team"
    names: dict[str, str] | None = None


class AnswerItem(BaseModel):
    question_id: str
    answer: str = ""
    action: Literal["answer", "escalate"] = "answer"


class AnswersRequest(BaseModel):
    answers: list[AnswerItem]


class DecisionRequest(BaseModel):
    decision: Literal["approve", "edit", "reject"]
    notes: str = ""


class ReplayRequest(BaseModel):
    dataset_id: str
    speed: Literal[1, 4] = 1


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or load_settings()
    bus = StreamBus()
    registry = Registry(cfg, bus)
    replays: dict[str, ReplaySession] = {}

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        for session in replays.values():
            if session.task is not None and not session.task.done():
                session.task.cancel()

    app = FastAPI(title="Sterling AI multi-agent demo", lifespan=lifespan)
    app.state.settings = cfg
    app.state.registry = registry
    app.state.bus = bus
    app.state.replays = replays

    app.mount("/static", StaticFiles(directory=cfg.static_dir), name="static")

    def page(name: str) -> HTMLResponse:
        path = cfg.pages_dir / f"{name}.html"
        if not path.exists():
            raise HTTPException(404, f"page {name} not found")
        info = build_info(cfg.root)
        html = path.read_text(encoding="utf-8").replace("{{BUILD_STAMP}}", info.stamp)
        return HTMLResponse(html)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse("/demo")

    @app.get("/demo", response_class=HTMLResponse)
    async def demo_page() -> HTMLResponse:
        return page("demo")

    @app.get("/login", response_class=HTMLResponse)
    async def login_page() -> HTMLResponse:
        return page("login")

    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page() -> HTMLResponse:
        return page("settings")

    @app.get("/preflight", response_class=HTMLResponse)
    async def preflight_page() -> HTMLResponse:
        return page("preflight")

    # Metadata and datasets

    @app.get("/api/meta")
    async def meta() -> dict[str, Any]:
        info = build_info(cfg.root)
        return {
            "build": {"hash": info.hash, "date": info.date},
            "preflight": "pending",
            "stub_pace": cfg.stub_pace,
            "workflow": cfg.workflow,
            "retry_budget": cfg.retry_budget,
            "cost_ceiling": cfg.cost_ceiling,
            "schema_version": cfg.schema_version,
            "live_run_id": registry.live.run_id if registry.is_live() and registry.live else None,
        }

    @app.get("/api/datasets")
    async def datasets() -> list[dict[str, Any]]:
        return registry.dataset_listing()

    # Runs

    @app.post("/api/runs", status_code=201)
    async def start_run(body: RunRequest) -> dict[str, Any]:
        if body.workflow != cfg.workflow:
            raise HTTPException(400, f"workflow {body.workflow} arrives in S8")
        if body.dataset_id not in registry.datasets:
            raise HTTPException(404, f"unknown dataset {body.dataset_id}")
        if registry.is_live():
            raise HTTPException(409, "a run is already in progress")
        try:
            orchestrator = registry.start_run(body.dataset_id, names=body.names)
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        return {
            "run_id": orchestrator.run_id,
            "stream_url": f"/api/streams/{orchestrator.run_id}/events",
            "retry_budget": orchestrator.state.retry_budget,
            "cost_ceiling": orchestrator.state.cost_ceiling,
        }

    def get_orchestrator(run_id: str) -> Any:
        orchestrator = registry.get_run(run_id)
        if orchestrator is None:
            raise HTTPException(404, f"unknown run {run_id}")
        return orchestrator

    @app.get("/api/runs/{run_id}")
    async def run_status(run_id: str) -> dict[str, Any]:
        o = get_orchestrator(run_id)
        return {
            "run_id": o.run_id,
            "dataset_id": o.dataset.dataset_id,
            "workflow": o.workflow,
            "mode": "team",
            "status": o.status,
            "exit": o.state.exit,
            "retry_budget": o.state.retry_budget,
            "cost_ceiling": o.state.cost_ceiling,
            "roster": [a.model_dump() for a in o.roster.values()],
            "started_at": o.clock.ts(0),
            "event_count": len(o.events),
            "pending": o.pending(),
        }

    @app.get("/api/runs/{run_id}/events")
    async def run_events(run_id: str) -> list[dict[str, Any]]:
        o = registry.get_run(run_id)
        if o is not None:
            return [e.model_dump(mode="json", by_alias=True) for e in o.events]
        recorded = registry.read_recording(run_id)
        if recorded is None:
            raise HTTPException(404, f"unknown run {run_id}")
        return [e.model_dump(mode="json", by_alias=True) for e in recorded]

    @app.post("/api/runs/{run_id}/answers", status_code=202)
    async def answers(run_id: str, body: AnswersRequest) -> dict[str, str]:
        o = get_orchestrator(run_id)
        try:
            o.submit_answers([Answer(a.question_id, a.answer, a.action) for a in body.answers])
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        return {"status": "accepted"}

    @app.post("/api/runs/{run_id}/decision", status_code=202)
    async def decision(run_id: str, body: DecisionRequest) -> dict[str, str]:
        o = get_orchestrator(run_id)
        try:
            o.submit_decision(body.decision, body.notes)
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        return {"status": "accepted"}

    @app.post("/api/runs/{run_id}/pause", status_code=202)
    async def pause(run_id: str) -> dict[str, str]:
        get_orchestrator(run_id).pause()
        return {"status": "accepted"}

    @app.post("/api/runs/{run_id}/resume", status_code=202)
    async def resume(run_id: str) -> dict[str, str]:
        get_orchestrator(run_id).resume()
        return {"status": "accepted"}

    @app.post("/api/runs/{run_id}/stop", status_code=202)
    async def stop(run_id: str) -> dict[str, str]:
        get_orchestrator(run_id).stop()
        return {"status": "accepted"}

    @app.get("/api/prompts/{prompt_ref}")
    async def prompt(prompt_ref: str) -> dict[str, Any]:
        found: PromptBundle | None = None
        for o in registry.runs.values():
            if prompt_ref in o.bundles:
                found = o.bundles[prompt_ref]
                break
        if found is None:
            found = bundle_for(prompt_ref)
        if found is None:
            raise HTTPException(404, f"unknown prompt bundle {prompt_ref}")
        data = found.model_dump()
        data["sections"] = [{"label": label, "text": text} for label, text in found.sections()]
        return data

    # Replay

    @app.post("/api/replays", status_code=201)
    async def start_replay(body: ReplayRequest) -> dict[str, Any]:
        if body.dataset_id not in registry.datasets:
            raise HTTPException(404, f"unknown dataset {body.dataset_id}")
        if registry.is_live():
            raise HTTPException(409, "a run is in progress")
        source = registry.replay_source(body.dataset_id)
        if source is None:
            raise HTTPException(404, "no recording or golden log for this dataset")
        session = ReplaySession(
            dataset_id=body.dataset_id, source=source.kind, path=source.path, speed=float(body.speed), bus=bus
        )
        session.load()
        replays[session.session_id] = session
        session.start()
        return {
            "session_id": session.session_id,
            "run_id": session.run_id,
            "source": session.source,
            "stream_url": f"/api/streams/{session.session_id}/events",
            "event_count": len(session.events),
            "speed": body.speed,
        }

    # Stream

    @app.get("/api/streams/{stream_id}/events")
    async def stream(stream_id: str, request: Request, since: int | None = None) -> StreamingResponse:
        if not bus.exists(stream_id):
            raise HTTPException(404, f"unknown stream {stream_id}")
        last_event_id = request.headers.get("last-event-id")
        start = since if since is not None else int(last_event_id) if last_event_id and last_event_id.isdigit() else 0

        async def generate() -> AsyncIterator[str]:
            iterator = bus.subscribe(stream_id, since_seq=start).__aiter__()
            pending: asyncio.Task[Any] | None = None
            try:
                while True:
                    if pending is None:
                        pending = asyncio.ensure_future(iterator.__anext__())
                    done, _ = await asyncio.wait({pending}, timeout=KEEPALIVE_SECONDS)
                    if not done:
                        yield ": keepalive\n\n"
                        continue
                    task, pending = pending, None
                    try:
                        event = task.result()
                    except StopAsyncIteration:
                        return
                    data = json.dumps(event, ensure_ascii=False)
                    yield f"id: {event['seq']}\nevent: {event['type']}\ndata: {data}\n\n"
                    if event["type"] == "run.terminated":
                        return
            finally:
                if pending is not None:
                    pending.cancel()
                await iterator.aclose()  # type: ignore[attr-defined]

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

    return app


app = create_app()
