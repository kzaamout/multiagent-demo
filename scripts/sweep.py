"""Run a model sweep: every configuration in a plan file, one run at a time, through the same API the Demo
page uses (owner decisions 2026-09-17, question 9a).

    uv run python scripts/sweep.py config/sweep/stage-1.yaml [--worker laptop] [--dry-run]

A plan names a baseline seat assignment, the models and seats to vary one at a time, and the models to put
on every seat at once. The plan expands to a job list: baseline first, then each model's variations
together so Ollama keeps one model loaded as long as possible. A job is skipped when the model cannot serve
the seat (a text-only model on the Estimator or the Reviewer). Jobs are claimed in
`runs/_sweep/<label>.jsonl`, so a second worker on another machine, pointed at the same runs folder, takes
the next unclaimed job. Each finished run carries `sweep.json` naming the job and that Handoff was approved
by the sweep, not by a person. Clarifications take their proposed default; a blocker is escalated or
answered as the plan says; a run past `max_minutes` is stopped. Results are read by
`scripts/model_report.py --write`.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, request

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.live.providers import ModelConfig  # noqa: E402

VISION_SEATS = ("estimator", "reviewer")
CLAIMS_DIR = "_sweep"


@dataclass(frozen=True)
class Job:
    label: str
    config_key: str
    varied_seat: str
    model_key: str
    seats: dict[str, str]
    dataset_id: str
    repeat: int

    @property
    def key(self) -> str:
        return f"{self.label}/{self.config_key}/{self.dataset_id}/{self.repeat}"


def eligible(config: ModelConfig, seat: str, model_key: str) -> tuple[bool, str]:
    spec = config.models.get(model_key)
    if spec is None:
        return False, f"unknown model {model_key}"
    if seat in VISION_SEATS and not spec.image_input:
        return False, f"{spec.label} cannot read images, which the {seat} needs"
    return True, ""


def expand(plan: dict[str, Any], config: ModelConfig) -> tuple[list[Job], list[str]]:
    """The plan's jobs in run order, and the combinations skipped with their reasons."""
    label = str(plan["label"])
    baseline: dict[str, str] = dict(plan["baseline"])
    datasets = [str(d) for d in plan.get("datasets", [])]
    repeats = int(plan.get("repeats", 1))
    vary = plan.get("vary") or {}
    configs: list[tuple[str, str, str, dict[str, str]]] = []
    skipped: list[str] = []
    if plan.get("baseline_job", True):
        configs.append(("baseline", "", "", baseline))
    # `pairs` names the seat and model combinations to run, for a stage that repeats only what an earlier
    # stage found worth measuring. `vary` builds the cross product instead, for a screening stage.
    for pair in plan.get("pairs") or []:
        seat, model_key = str(pair["seat"]), str(pair["model"])
        ok, why = eligible(config, seat, model_key)
        if not ok:
            skipped.append(f"{seat}={model_key}: {why}")
            continue
        configs.append((f"{seat}={model_key}", seat, model_key, {**baseline, seat: model_key}))
    for model_key in vary.get("models", []):
        for seat in vary.get("seats", []):
            if baseline.get(seat) == model_key:
                continue
            ok, why = eligible(config, seat, str(model_key))
            if not ok:
                skipped.append(f"{seat}={model_key}: {why}")
                continue
            configs.append((f"{seat}={model_key}", seat, str(model_key), {**baseline, seat: str(model_key)}))
        if model_key in (plan.get("whole") or []):
            configs.append(
                (f"all={model_key}", "all", str(model_key), dict.fromkeys(baseline, str(model_key)))
            )
    for model_key in plan.get("whole") or []:
        if model_key in vary.get("models", []):
            continue
        ok, why = eligible(config, "estimator", str(model_key))
        if not ok:
            skipped.append(f"all={model_key}: {why}")
            continue
        configs.append((f"all={model_key}", "all", str(model_key), dict.fromkeys(baseline, str(model_key))))
    jobs = [
        Job(label, key, seat, model_key, seats, dataset_id, repeat)
        for dataset_id in datasets
        for repeat in range(repeats)
        for key, seat, model_key, seats in configs
    ]
    return jobs, skipped


class Claims:
    """One line per job in runs/_sweep/<label>.jsonl; a job with any line is taken."""

    def __init__(self, runs_dir: Path, label: str) -> None:
        self.path = runs_dir / CLAIMS_DIR / f"{label}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = self.path.with_suffix(".lock")

    def _locked(self, fn: Any) -> Any:
        for _ in range(200):
            try:
                handle = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                time.sleep(0.1)
                continue
            try:
                return fn()
            finally:
                os.close(handle)
                os.unlink(self.lock)
        raise RuntimeError(f"could not take {self.lock}")

    def lines(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [
            json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]

    def append(self, record: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def claim(self, job: Job, worker: str) -> bool:
        def attempt() -> bool:
            if any(line.get("job") == job.key for line in self.lines()):
                return False
            self.append({"job": job.key, "worker": worker, "status": "claimed", "at": _now()})
            return True

        return bool(self._locked(attempt))

    def finish(self, job: Job, worker: str, record: dict[str, Any]) -> None:
        self._locked(lambda: self.append({"job": job.key, "worker": worker, **record}))


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class Api:
    def __init__(self, base: str) -> None:
        self.base = base

    def call(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        req = request.Request(
            self.base + path, data=data, method=method, headers={"content-type": "application/json"}
        )
        try:
            with request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read() or b"null")
        except error.HTTPError as failure:
            detail = failure.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(f"{method} {path} -> {failure.code}: {detail}") from None


def drive(api: Api, job: Job, plan: dict[str, Any], log: Any) -> dict[str, Any]:
    """Set the seats, start the run, answer what it asks, approve at Handoff, and say how it ended."""
    for seat, model_key in job.seats.items():
        api.call("POST", f"/api/seats/{seat}", {"model": model_key})
    started = api.call("POST", "/api/runs", {"dataset_id": job.dataset_id})
    run_id = str(started["run_id"])
    log(f"  run {run_id} started for {job.key}")
    t0 = time.time()
    answered: set[str] = set()
    decided = False
    outcome = "done"
    seen_stage = 0
    while True:
        status = api.call("GET", f"/api/runs/{run_id}")
        events = api.call("GET", f"/api/runs/{run_id}/events")
        stages = [e for e in events if e["type"] == "stage.changed"]
        for e in stages[seen_stage:]:
            p = e["payload"]
            log(f"    stage {p.get('from')} -> {p['to']} ({p['direction']})")
        seen_stage = len(stages)
        pending = status.get("pending") or {}
        kind = pending.get("kind")
        if kind in ("clarifications", "blocker"):
            defaults = {
                e["payload"]["question_id"]: e["payload"].get("proposed_default", "")
                for e in events
                if e["type"] == "clarification.needed"
            }
            answers = [
                {"question_id": q, "answer": defaults.get(q, ""), "action": "answer"}
                for q in pending.get("question_ids") or []
                if q not in answered
            ]
            blocker = pending.get("blocker")
            if blocker and blocker["blocker_id"] not in answered:
                if str(plan.get("blocker", "escalate")) == "escalate":
                    answers.append({"question_id": blocker["blocker_id"], "answer": "", "action": "escalate"})
                else:
                    answers.append(
                        {
                            "question_id": blocker["blocker_id"],
                            "answer": "Proceed on the stated assumption.",
                            "action": "answer",
                        }
                    )
            if answers:
                try:
                    api.call("POST", f"/api/runs/{run_id}/answers", {"answers": answers})
                    answered.update(a["question_id"] for a in answers)
                    log(f"    answered {[a['question_id'] for a in answers]}")
                except RuntimeError as failure:
                    log(f"    answer refused: {failure}")
        elif kind == "handoff" and not decided:
            decided = True
            api.call("POST", f"/api/runs/{run_id}/decision", {"decision": "approve", "notes": ""})
            log("    approved by the sweep")
        if events and events[-1]["type"] == "run.terminated":
            break
        if time.time() - t0 > float(plan.get("max_minutes", 30)) * 60:
            outcome = "timeout"
            log("    past max_minutes, stopping the run")
            try:
                api.call("POST", f"/api/runs/{run_id}/stop")
            except RuntimeError as failure:
                log(f"    stop refused: {failure}")
            for _ in range(20):
                events = api.call("GET", f"/api/runs/{run_id}/events")
                if events and events[-1]["type"] == "run.terminated":
                    break
                time.sleep(1)
            break
        time.sleep(3)
    term = events[-1]["payload"] if events and events[-1]["type"] == "run.terminated" else {}
    summary = term.get("summary") or {}
    return {
        "status": outcome,
        "run_id": run_id,
        "exit": term.get("exit"),
        "stop_reason": summary.get("stop_reason"),
        "minutes": round((time.time() - t0) / 60, 1),
        "est_cost": summary.get("est_cost"),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("plan", help="a plan file such as config/sweep/stage-1.yaml")
    parser.add_argument(
        "--worker", default=socket.gethostname(), help="this worker's name in the claims file"
    )
    parser.add_argument("--dry-run", action="store_true", help="list the jobs and the skipped combinations")
    args = parser.parse_args(argv)
    plan = yaml.safe_load(Path(args.plan).read_text(encoding="utf-8"))
    config = ModelConfig.load()
    jobs, skipped = expand(plan, config)
    print(f"{len(jobs)} jobs in {plan['label']}; {len(skipped)} combinations skipped", flush=True)
    for line in skipped:
        print(f"  skipped {line}", flush=True)
    if args.dry_run:
        for job in jobs:
            print(f"  {job.key}", flush=True)
        return 0

    os.environ["COST_CEILING"] = str(plan.get("ceiling", "1.00"))
    import uvicorn

    from app.config import load_settings
    from app.main import create_app

    settings = load_settings()
    if settings.agent_mode == "stub":
        print("AGENT_MODE=stub in .env; a sweep needs live seats", flush=True)
        return 2
    claims = Claims(settings.runs_dir, str(plan["label"]))
    app = create_app(settings)
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.1)
    api = Api(f"http://127.0.0.1:{port}")

    def log(text: str) -> None:
        print(f"{_now()} {text}", flush=True)

    done = failed = 0
    for job in jobs:
        if not claims.claim(job, args.worker):
            continue
        log(f"job {job.key}")
        started_at = _now()
        try:
            result = drive(api, job, plan, log)
        except Exception as failure:  # noqa: BLE001
            result = {"status": "failed", "error": str(failure)[:400]}
            log(f"  failed: {failure}")
        result["at"] = _now()
        claims.finish(job, args.worker, result)
        run_id = result.get("run_id")
        if run_id:
            marker = settings.runs_dir / str(run_id) / "sweep.json"
            marker.write_text(
                json.dumps(
                    {
                        **asdict(job),
                        "job": job.key,
                        "worker": args.worker,
                        "started_at": started_at,
                        "ended_at": result["at"],
                        "status": result["status"],
                        "decision": "approved by the sweep, not by a person",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
        if result["status"] == "done":
            done += 1
            log(f"  exit {result.get('exit')} in {result.get('minutes')} min")
        else:
            failed += 1
    server.should_exit = True
    log(f"finished: {done} done, {failed} failed or stopped; run scripts/model_report.py --write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
