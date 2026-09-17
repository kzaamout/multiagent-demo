"""FastAPI application: static pages flattened from the design export, the run API, and the
server-sent event stream. Contract: specs/001-event-spine-stubbed-loop/contracts/http-api.md.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agents.stubs import bundle_for
from app.buildinfo import build_info
from app.compile import CompileError, compile_timeline, tools_available
from app.config import Settings, load_settings
from app.intro.page import pinned_run, render_page
from app.intro.pdf import missing_tools, render_pdf
from app.live.chat import ChatRefused, chat, chat_allowed, find_bundle
from app.live.providers import Availability, ModelConfig, SeatModelFactory, strands_model_for
from app.orchestrator.orchestrator import Answer
from app.runs.bus import StreamBus
from app.runs.comparison import comparison
from app.runs.recorder import read_events
from app.runs.registry import LiveUnavailable, Registry
from app.runs.replay import ReplaySession
from app.schema.bundles import PromptBundle
from app.schema.events import Event

KEEPALIVE_SECONDS = 15.0


class RunRequest(BaseModel):
    dataset_id: str
    workflow: str = "electrical_rfp"
    mode: Literal["team", "single"] = "team"
    model: str | None = None
    names: dict[str, str] | None = None
    dry_intake: bool = False


class SeatModelRequest(BaseModel):
    model: str


class AnswerItem(BaseModel):
    question_id: str
    answer: str = ""
    action: Literal["answer", "escalate"] = "answer"


class AnswersRequest(BaseModel):
    answers: list[AnswerItem]


class DecisionRequest(BaseModel):
    decision: Literal["approve", "edit", "reject"]
    notes: str = ""
    markdown: str = ""
    """The edited draft for `edit` (S4); ignored for approve and reject."""


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str


class ChatRequest(BaseModel):
    run_id: str
    agent_id: str
    messages: list[ChatMessage]


class ReplayRequest(BaseModel):
    dataset_id: str
    speed: Literal[1, 4] = 1


def create_app(
    settings: Settings | None = None,
    seat_model_factory: SeatModelFactory | None = None,
    model_config: ModelConfig | None = None,
    availability: dict[str, Availability] | None = None,
) -> FastAPI:
    cfg = settings or load_settings()
    bus = StreamBus()
    registry = Registry(
        cfg, bus, seat_model_factory=seat_model_factory, model_config=model_config, availability=availability
    )
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

    # Introduction (public, spec 2.1) and the public replay of one pinned run (spec 6)

    def public_events(run_id: str) -> list[Event]:
        """The pinned run's events; any other id is refused before the disk is touched."""
        if run_id != cfg.public_run_id:
            raise HTTPException(404, "not a public run")
        live = registry.get_run(run_id)
        events = live.events if live is not None else registry.events_for(run_id)
        if not events:
            raise HTTPException(404, "the pinned recording is not on this machine")
        return events

    @app.get("/introduction", response_class=HTMLResponse)
    async def introduction_page() -> HTMLResponse:
        events = registry.events_for(cfg.public_run_id)
        info = build_info(cfg.root)
        html = render_page(cfg, registry.seat_table(), events).replace("{{BUILD_STAMP}}", info.stamp)
        return HTMLResponse(html)

    @app.get("/introduction.pdf")
    async def introduction_pdf() -> FileResponse:
        missing = missing_tools()
        if missing:
            raise HTTPException(503, "compiler missing (" + ", ".join(missing) + ")")
        try:
            pdf = await asyncio.to_thread(render_pdf, cfg)
        except CompileError as error:
            raise HTTPException(500, f"the Introduction did not compile: {error}") from None
        return FileResponse(pdf, media_type="application/pdf", filename="sterling-ai-introduction.pdf")

    @app.get("/public/run/{run_id}/meta")
    async def public_meta(run_id: str) -> dict[str, Any]:
        events = public_events(run_id)
        pinned = pinned_run(cfg, events)
        return {
            "run_id": pinned.run_id,
            "dataset_id": pinned.dataset_id,
            "exit": pinned.exit,
            "has_pages": pinned.has_pages,
        }

    @app.get("/public/run/{run_id}/events")
    async def public_run_events(run_id: str) -> list[dict[str, Any]]:
        return [e.model_dump(mode="json", by_alias=True) for e in public_events(run_id)]

    @app.get("/public/run/{run_id}/files/{path:path}")
    async def public_run_file(run_id: str, path: str) -> FileResponse:
        public_events(run_id)
        folder = (cfg.runs_dir / run_id).resolve()
        if not folder.is_dir():
            golden = registry.golden_folder(run_id)
            if golden is None:
                raise HTTPException(404, "file not found")
            folder = golden.resolve()
        target = (folder / path).resolve()
        if not target.is_relative_to(folder) or not target.is_file():
            raise HTTPException(404, "file not found")
        if target.suffix not in {".md", ".png", ".pdf", ".json"}:
            raise HTTPException(404, "file not found")
        return FileResponse(target)

    @app.get("/public/run/{run_id}/prompts/{prompt_ref}")
    async def public_prompt(run_id: str, prompt_ref: str) -> dict[str, Any]:
        public_events(run_id)
        path = cfg.runs_dir / run_id / "prompts" / f"{prompt_ref}.json"
        found = bundle_for(prompt_ref)
        if found is None and path.is_file():
            found = PromptBundle.model_validate_json(path.read_text(encoding="utf-8"))
        if found is None:
            raise HTTPException(404, "unknown prompt")
        data = found.model_dump()
        data["sections"] = [{"label": label, "text": text} for label, text in found.sections()]
        return data

    # Metadata and datasets

    @app.get("/api/meta")
    async def meta() -> dict[str, Any]:
        info = build_info(cfg.root)
        return {
            "build": {"hash": info.hash, "date": info.date},
            "preflight": "pending",
            "stub_pace": cfg.stub_pace,
            "workflow": cfg.workflow,
            "review_max_cycles": cfg.review_max_cycles,
            "retry_budget": cfg.retry_budget,
            "cost_ceiling": cfg.cost_ceiling,
            "schema_version": cfg.schema_version,
            "live_run_id": registry.live.run_id if registry.is_live() and registry.live else None,
            "idle_roster": {seat: agent.model_dump() for seat, agent in registry.idle_roster().items()},
        }

    @app.get("/api/providers")
    async def providers() -> dict[str, Any]:
        """Availability as booleans and reasons only; never a credential value."""
        return registry.provider_report()

    # Seats (S5, contracts/http-api-s5.md)

    @app.get("/api/seats")
    async def seats() -> dict[str, Any]:
        """Every seat with its live card and every model with its availability. Never a credential value."""
        return registry.seat_table()

    @app.post("/api/seats/{seat}")
    async def set_seat(seat: str, body: SeatModelRequest) -> dict[str, Any]:
        try:
            swap = registry.set_seat_model(seat, body.model)
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        except LiveUnavailable as unavailable:
            raise HTTPException(409, "; ".join(unavailable.problems)) from None
        live = registry.live if registry.is_live() else None
        if live is not None and seat in live.roster:
            agent = live.roster[seat].model_copy(update={"model": swap.model})
            seat_model = None
            if registry.mode_for(live.dataset.dataset_id) == "live":
                factory = registry.seat_model_factory or (
                    lambda s: strands_model_for(registry.effective_config(), s)
                )
                seat_model = factory(seat)
            await live.change_model(seat, agent, seat_model)
        return {
            "seat": swap.seat,
            "model": swap.model.model_dump(),
            "warning": swap.warning,
            "applied": swap.applied,
        }

    @app.get("/api/datasets")
    async def datasets() -> list[dict[str, Any]]:
        return registry.dataset_listing()

    @app.get("/api/datasets/{dataset_id}/comparison")
    async def dataset_comparison(dataset_id: str) -> dict[str, Any]:
        """The newest terminated Team and Single-model recordings for the dataset (S5). Recordings only."""
        if dataset_id not in registry.datasets:
            raise HTTPException(404, f"unknown dataset {dataset_id}")
        return comparison(cfg.runs_dir, dataset_id)

    @app.get("/api/datasets/{dataset_id}/golden")
    async def golden(dataset_id: str, upto: int | None = None) -> list[dict[str, Any]]:
        """The committed golden log, optionally cut at a seq. Used to render a fixed state."""
        if dataset_id not in registry.datasets:
            raise HTTPException(404, f"unknown dataset {dataset_id}")
        path = registry.dataset(dataset_id).golden_path
        if not path.exists():
            raise HTTPException(404, "no golden log for this dataset")
        events = read_events(path)
        if upto is not None:
            events = [e for e in events if e.seq <= upto]
        return [e.model_dump(mode="json", by_alias=True) for e in events]

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
            orchestrator = registry.start_run(
                body.dataset_id,
                names=body.names,
                dry_intake=body.dry_intake,
                mode=body.mode,
                model_key=body.model,
            )
        except LiveUnavailable as unavailable:
            raise HTTPException(409, "Live run unavailable: " + "; ".join(unavailable.problems)) from None
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        return {
            "run_id": orchestrator.run_id,
            "mode": orchestrator.mode,
            "stream_url": f"/api/streams/{orchestrator.run_id}/events",
            "review_max_cycles": orchestrator.state.review_max_cycles,
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
            "mode": o.mode,
            "status": o.status,
            "exit": o.state.exit,
            "review_max_cycles": o.state.review_max_cycles,
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
            o.submit_decision(body.decision, body.notes, markdown=body.markdown)
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        return {"status": "accepted"}

    @app.get("/api/runs/{run_id}/timeline.pdf")
    async def run_timeline(run_id: str) -> FileResponse:
        """The run timeline as a PDF rendered from the event log (S4 decision 5a), for a run that has
        ended, a recording, or a golden log."""
        o = registry.get_run(run_id)
        if o is not None and not o.state.terminated:
            raise HTTPException(409, "the run has not ended")
        events = o.events if o is not None else registry.events_for(run_id)
        if not events:
            raise HTTPException(404, f"unknown run {run_id}")
        missing = [name for name, version in tools_available().items() if version is None]
        if missing:
            raise HTTPException(503, "compiler missing (" + ", ".join(missing) + ")")
        folder = cfg.runs_dir / run_id
        if not folder.is_dir():
            folder = cfg.runs_dir / "_golden" / run_id
            folder.mkdir(parents=True, exist_ok=True)
        try:
            pdf = await asyncio.to_thread(compile_timeline, folder, events)
        except CompileError as error:
            raise HTTPException(500, f"the timeline did not compile: {error}") from None
        return FileResponse(pdf, media_type="application/pdf", filename=f"run-{run_id[:8]}-timeline.pdf")

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

    @app.get("/api/runs/{run_id}/files/{path:path}")
    async def run_file(run_id: str, path: str) -> FileResponse:
        """A file a run's events refer to, such as a committed draft. Read-only, inside the run folder."""
        runs_root = cfg.runs_dir.resolve()
        folder = (runs_root / run_id).resolve()
        if folder.parent != runs_root:
            raise HTTPException(404, "file not found")
        if not folder.is_dir():
            # A golden log's run never existed under runs/; its compiled pages live with the dataset.
            golden = registry.golden_folder(run_id)
            if golden is None:
                raise HTTPException(404, "file not found")
            folder = golden.resolve()
        target = (folder / path).resolve()
        if not target.is_relative_to(folder) or not target.is_file():
            raise HTTPException(404, "file not found")
        if target.suffix not in {".md", ".png", ".pdf", ".json"}:
            raise HTTPException(404, "file not found")
        return FileResponse(target)

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

    # Chat (S5, spec 2.7): out of band, read-only, nothing recorded, nothing emitted.

    @app.post("/api/chat")
    async def chat_with_agent(body: ChatRequest) -> dict[str, Any]:
        found = find_bundle(registry, body.run_id, body.agent_id)
        if found is None:
            raise HTTPException(404, f"no prompt bundle for {body.agent_id} in run {body.run_id}")
        if not chat_allowed(registry, body.run_id):
            raise HTTPException(409, "chat is available when the run is paused or finished")
        bundle, card = found
        config = registry.effective_config()
        if body.agent_id == "single":
            key = next((k for k, m in config.models.items() if m.model_id == card.model.model_id), None)
            key = key or (config.seats["orchestrator"].model if "orchestrator" in config.seats else None)
            if key is None:
                raise HTTPException(404, "no model for the Single-model seat")
            config = config.with_seat("single", key)
        elif body.agent_id not in config.seats:
            raise HTTPException(404, f"no model configured for seat {body.agent_id}")
        factory = registry.seat_model_factory or (lambda seat: strands_model_for(config, seat))
        try:
            seat_model = factory(body.agent_id)
            answer = await chat(seat_model, bundle, [m.model_dump() for m in body.messages])
        except ChatRefused as refused:
            raise HTTPException(refused.status, refused.reason) from None
        except Exception as error:  # noqa: BLE001
            raise HTTPException(502, f"The model could not be reached ({type(error).__name__}).") from None
        return {
            "text": answer.text,
            "model": answer.model.model_dump(),
            "tokens_in": answer.tokens_in,
            "tokens_out": answer.tokens_out,
            "est_cost": answer.est_cost,
            "latency_ms": answer.latency_ms,
        }

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
        start = (
            since
            if since is not None
            else int(last_event_id)
            if last_event_id and last_event_id.isdigit()
            else 0
        )

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
                # A client that disconnects leaves a read in flight; let it finish cancelling
                # before closing the subscription, or the close races the running generator.
                if pending is not None:
                    pending.cancel()
                    with contextlib.suppress(asyncio.CancelledError, StopAsyncIteration):
                        await pending
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
