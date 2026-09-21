"""The pre-flight checks (spec 0.8 section 2.4; slice S7, research D2 to D4 and D7 to D9; spec 012
research D6 and D9).

One row per model in the registry, then the fixed rows. Every check returns a CheckResult and
never raises. Detail lines are one sentence each and never carry a credential value or a
provider's message text (constitution XVII): a failure names the exception's class, a timeout
names the limit. Every outside call is injectable through the CheckContext so the suite runs
without a network, a compiler, or a model.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.compile.pipeline import Compiled, CompileError, tools_available
from app.config import Settings
from app.live.providers import Availability, ModelConfig, ModelSpec, strands_model_for
from app.live.seat_call import SeatModel
from app.preflight.result import FAIL, FIXED, PASS, SKIP, CheckResult, now_iso

PROBE_SEAT = "preflight-probe"
PROVIDER_TIMEOUT_S = 30.0
OLLAMA_TIMEOUT_S = 5.0
COMPILE_TIMEOUT_S = 60.0
TUNNEL_TIMEOUT_S = 10.0
DISK_MIN_GB = 5.0
PREFLIGHT_FOLDER = "preflight"
FIXTURE_PATH = Path(__file__).resolve().parent / "fixture.md"

CLOUD_MODE_SKIP = "Local models are not used in Cloud mode"
NO_TUNNEL_HOSTNAME = "No tunnel hostname in .env"
TUNNEL_DOWN = "Tunnel not connected"
ALL_KEYS_PRESENT = "All required keys present"
NO_AWS_CREDENTIALS = "No AWS credentials"
OLLAMA_UNREACHABLE = "Ollama not reachable"
LOGIN_NAMES = ("DEMO_USERNAME", "DEMO_PASSWORD")
AWS_CREDENTIALS = "AWS credentials"

# Where the Ollama row leaves the pulled model names for the local model rows: a set, or None
# when Ollama did not answer.
OLLAMA_TAGS = "ollama_tags"

ProbeFn = Callable[[SeatModel], Awaitable[None]]
FetchFn = Callable[[str, float], tuple[int, int]]
TagsFn = Callable[[str, float], set[str]]
DiskFn = Callable[[Path], Any]
CompileFn = Callable[[Path, str], Compiled]
FactoryFn = Callable[[ModelConfig, str], SeatModel]


async def strands_probe(seat_model: SeatModel) -> None:
    """One minimal model call: a fresh agent with no tools asked for one word (owner decision 5)."""
    from strands import Agent as StrandsAgent

    agent = StrandsAgent(
        model=seat_model.strands_model,
        system_prompt="Reply with the single word ready.",
        tools=[],
        callback_handler=None,
        name="preflight-probe",
        retry_strategy=None,
    )
    await agent.invoke_async("Are you ready?")


def httpx_fetch(url: str, timeout: float) -> tuple[int, int]:
    """HTTP status and milliseconds; raises on a transport error."""
    import httpx

    started = time.monotonic()
    response = httpx.get(url, timeout=timeout, follow_redirects=False)
    return response.status_code, int((time.monotonic() - started) * 1000)


def ollama_tags(host: str, timeout: float) -> set[str]:
    """The model names Ollama has pulled; raises when it is not reachable."""
    import httpx

    response = httpx.get(f"{host.rstrip('/')}/api/tags", timeout=timeout)
    response.raise_for_status()
    return {str(m.get("name")) for m in response.json().get("models", [])}


def compile_fixture(folder: Path, markdown: str) -> Compiled:
    """The S4 pipeline on the fixture, writing under runs/preflight/ (research D4)."""
    from app.compile import Brand, compile_draft

    brand = Brand(prospect_name="Pre-flight", logo_path=None, primary_colour="#003c33")
    return compile_draft(folder, 1, markdown, brand)


def aws_credentials_present() -> bool:
    try:
        import boto3

        return boto3.Session().get_credentials() is not None
    except Exception:  # noqa: BLE001
        return False


@dataclass
class CheckContext:
    settings: Settings
    config: ModelConfig
    availability: dict[str, Availability]
    seat_model_factory: FactoryFn = strands_model_for
    probe: ProbeFn = strands_probe
    fetch: FetchFn = httpx_fetch
    tags: TagsFn = ollama_tags
    disk_usage: DiskFn = shutil.disk_usage
    compile: CompileFn = compile_fixture
    aws_credentials: Callable[[], bool] = aws_credentials_present
    env: Mapping[str, str] = field(default_factory=lambda: os.environ)
    intro_recording_present: Callable[[], bool] = lambda: True
    datasets_without_replay: Callable[[], list[str]] = list
    scratch: dict[str, Any] = field(default_factory=dict)

    @property
    def cloud_mode(self) -> bool:
        return self.settings.run_mode == "cloud"

    def seats_on(self, provider: str) -> list[str]:
        return [s for s in self.config.seats if self.config.seat_spec(s).provider == provider]

    @property
    def ollama_host(self) -> str:
        return str(self.config.providers.get("ollama", {}).get("host", "http://localhost:11434"))


@dataclass(frozen=True)
class Check:
    id: str
    name: str
    timeout_s: float
    run: Callable[[CheckContext], Awaitable[CheckResult]]
    subject: dict[str, Any] = field(default_factory=lambda: dict(FIXED))


def _ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _host_label(host: str) -> str:
    return host.split("://", 1)[-1].rstrip("/")


def short_label(label: str) -> str:
    """ "claude-sonnet-5 via Bedrock" reads "claude-sonnet-5" on the row."""
    return label.split(" via ", 1)[0].strip()


def provider_label(config: ModelConfig, provider: str) -> str:
    return str(config.providers.get(provider, {}).get("label", provider))


# Model rows (spec 012 research D6)


def model_check_id(model_key: str) -> str:
    return f"model:{model_key}"


def model_subject(spec: ModelSpec) -> dict[str, Any]:
    return {"kind": "model", "model_key": spec.key, "provider": spec.provider}


def model_check(ctx: CheckContext, model_key: str) -> Check:
    spec = ctx.config.models[model_key]
    if spec.provider == "ollama":
        return Check(
            model_check_id(model_key),
            f"{spec.model_id} pulled in Ollama",
            OLLAMA_TIMEOUT_S,
            _local_runner(model_key),
            model_subject(spec),
        )
    return Check(
        model_check_id(model_key),
        f"{spec.label} answers",
        PROVIDER_TIMEOUT_S,
        _cloud_runner(model_key),
        model_subject(spec),
    )


def cloud_model_checks(ctx: CheckContext) -> list[Check]:
    return [model_check(ctx, k) for k, s in ctx.config.models.items() if s.provider != "ollama"]


def local_model_checks(ctx: CheckContext) -> list[Check]:
    return [model_check(ctx, k) for k, s in ctx.config.models.items() if s.provider == "ollama"]


def _cloud_runner(model_key: str) -> Callable[[CheckContext], Awaitable[CheckResult]]:
    async def run(ctx: CheckContext) -> CheckResult:
        spec = ctx.config.models[model_key]
        check_id, row, subject = model_check_id(model_key), f"{spec.label} answers", model_subject(spec)
        started = time.monotonic()
        state = ctx.availability.get(spec.provider)
        if not (state and state.available):
            detail = (
                NO_AWS_CREDENTIALS
                if spec.provider == "bedrock"
                else f"No key in .env for {provider_label(ctx.config, spec.provider)}"
            )
            return CheckResult(check_id, row, SKIP, detail, _ms(started), now_iso(), subject)
        model_label = short_label(spec.label)
        try:
            config = ctx.config.with_seat(PROBE_SEAT, model_key)
            seat_model = ctx.seat_model_factory(config, PROBE_SEAT)
            await asyncio.wait_for(ctx.probe(seat_model), PROVIDER_TIMEOUT_S)
        except TimeoutError:
            detail = f"no answer within {int(PROVIDER_TIMEOUT_S)} s"
            return CheckResult(check_id, row, FAIL, detail, _ms(started), now_iso(), subject)
        except Exception as error:  # noqa: BLE001
            detail = f"{model_label} did not answer ({type(error).__name__})"
            return CheckResult(check_id, row, FAIL, detail, _ms(started), now_iso(), subject)
        elapsed = _ms(started)
        detail = f"{model_label} answered in {elapsed} ms"
        return CheckResult(check_id, row, PASS, detail, elapsed, now_iso(), subject)

    return run


def _local_runner(model_key: str) -> Callable[[CheckContext], Awaitable[CheckResult]]:
    async def run(ctx: CheckContext) -> CheckResult:
        spec = ctx.config.models[model_key]
        check_id, row = model_check_id(model_key), f"{spec.model_id} pulled in Ollama"
        subject = model_subject(spec)
        started = time.monotonic()
        if ctx.cloud_mode:
            return CheckResult(check_id, row, SKIP, CLOUD_MODE_SKIP, _ms(started), now_iso(), subject)
        if OLLAMA_TAGS not in ctx.scratch:
            await _read_tags(ctx)
        names = ctx.scratch.get(OLLAMA_TAGS)
        if names is None:
            return CheckResult(check_id, row, FAIL, OLLAMA_UNREACHABLE, _ms(started), now_iso(), subject)
        if spec.model_id not in names and f"{spec.model_id}:latest" not in names:
            return CheckResult(check_id, row, FAIL, "not pulled", _ms(started), now_iso(), subject)
        detail = f"present at {_host_label(ctx.ollama_host)}"
        return CheckResult(check_id, row, PASS, detail, _ms(started), now_iso(), subject)

    return run


async def _read_tags(ctx: CheckContext) -> set[str] | None:
    try:
        names: set[str] | None = await asyncio.to_thread(ctx.tags, ctx.ollama_host, OLLAMA_TIMEOUT_S)
    except Exception:  # noqa: BLE001
        names = None
    ctx.scratch[OLLAMA_TAGS] = names
    return names


# Ollama reachability (S7 research D7, spec 012 FR-013)


async def check_ollama(ctx: CheckContext) -> CheckResult:
    started = time.monotonic()
    check_id, row = "ollama", "Ollama reachable"
    seats = ctx.seats_on("ollama")
    if ctx.cloud_mode:
        if seats:
            detail = f"{', '.join(seats)} still on local models; move them in Settings"
            return CheckResult(check_id, row, FAIL, detail, _ms(started), now_iso())
        return CheckResult(check_id, row, SKIP, CLOUD_MODE_SKIP, _ms(started), now_iso())
    names = await _read_tags(ctx)
    host = _host_label(ctx.ollama_host)
    if names is None:
        return CheckResult(check_id, row, FAIL, f"{OLLAMA_UNREACHABLE} at {host}", _ms(started), now_iso())
    detail = f"reachable at {host}, {len(names)} models pulled"
    return CheckResult(check_id, row, PASS, detail, _ms(started), now_iso())


# Typst and PNG (S7 research D4)


async def check_typst(ctx: CheckContext) -> CheckResult:
    started = time.monotonic()
    check_id, row = "typst", "Typst present, test compile"
    versions = await asyncio.to_thread(tools_available)
    for tool in ("typst", "pandoc"):
        if versions.get(tool) is None:
            return CheckResult(check_id, row, FAIL, f"{tool} not on the path", _ms(started), now_iso())
    folder = ctx.settings.runs_dir / PREFLIGHT_FOLDER
    try:
        markdown = FIXTURE_PATH.read_text(encoding="utf-8")
        compiled = await asyncio.to_thread(ctx.compile, folder, markdown)
    except CompileError as error:
        return CheckResult(check_id, row, FAIL, str(error).splitlines()[0], _ms(started), now_iso())
    except Exception as error:  # noqa: BLE001
        detail = f"compile failed ({type(error).__name__})"
        return CheckResult(check_id, row, FAIL, detail, _ms(started), now_iso())
    ctx.scratch["compiled"] = compiled
    seconds = compiled.elapsed_ms / 1000
    detail = f"typst {versions['typst']}, {compiled.page_count} pages in {seconds:.1f} s"
    return CheckResult(check_id, row, PASS, detail, _ms(started), now_iso())


async def check_png(ctx: CheckContext) -> CheckResult:
    started = time.monotonic()
    check_id, row = "png", "Page PNG export"
    compiled = ctx.scratch.get("compiled")
    if compiled is None:
        return CheckResult(check_id, row, FAIL, "no compile to export", _ms(started), now_iso())
    count = len(compiled.page_images)
    if count == 0:
        return CheckResult(check_id, row, FAIL, "Export produced 0 files", _ms(started), now_iso())
    detail = f"{count} PNGs written to runs/{PREFLIGHT_FOLDER}/"
    return CheckResult(check_id, row, PASS, detail, _ms(started), now_iso())


# Tunnel (S7 research D8)


async def check_tunnel(ctx: CheckContext) -> CheckResult:
    started = time.monotonic()
    check_id, row = "tunnel", "Tunnel reachable from outside"
    hostname = ctx.settings.tunnel_hostname.strip()
    if not hostname:
        return CheckResult(check_id, row, SKIP, NO_TUNNEL_HOSTNAME, _ms(started), now_iso())
    url = f"https://{hostname}/login"
    try:
        status, ms = await asyncio.to_thread(ctx.fetch, url, TUNNEL_TIMEOUT_S)
    except Exception:  # noqa: BLE001
        return CheckResult(check_id, row, FAIL, TUNNEL_DOWN, _ms(started), now_iso())
    if status != 200:
        return CheckResult(check_id, row, FAIL, f"HTTP {status} from the tunnel", _ms(started), now_iso())
    return CheckResult(check_id, row, PASS, f"{hostname} answered in {ms} ms", _ms(started), now_iso())


# Disk (S7 research D9)


async def check_disk(ctx: CheckContext) -> CheckResult:
    started = time.monotonic()
    check_id, row = "disk", "Disk space"
    folder = ctx.settings.runs_dir
    while not folder.exists() and folder.parent != folder:
        folder = folder.parent
    try:
        usage = await asyncio.to_thread(ctx.disk_usage, folder)
        free_gb = usage.free / 1_000_000_000
    except Exception:  # noqa: BLE001
        return CheckResult(check_id, row, FAIL, "could not read free space", _ms(started), now_iso())
    if free_gb < DISK_MIN_GB:
        detail = f"Under {DISK_MIN_GB:g} GB free ({free_gb:.1f} GB)"
        return CheckResult(check_id, row, FAIL, detail, _ms(started), now_iso())
    return CheckResult(check_id, row, PASS, f"{free_gb:.0f} GB free", _ms(started), now_iso())


# .env completeness (S7 research D9, spec 012 data model): names only, never a value


def env_facts(ctx: CheckContext) -> dict[str, Any]:
    """Which login names are unset and, for every provider but Ollama, the missing key's name."""
    login_missing = [
        name
        for name, value in zip(
            LOGIN_NAMES, (ctx.settings.demo_username, ctx.settings.demo_password), strict=True
        )
        if not value
    ]
    keys_missing: dict[str, str] = {}
    for name, provider in ctx.config.providers.items():
        if name == "ollama":
            continue
        if name == "bedrock":
            if not ctx.aws_credentials():
                keys_missing[name] = AWS_CREDENTIALS
            continue
        key = str(provider.get("env_key", ""))
        if key and not ctx.env.get(key):
            keys_missing[name] = key
    return {"kind": "env", "login_missing": login_missing, "keys_missing": keys_missing}


def env_verdict(subject: dict[str, Any], seat_providers: set[str]) -> tuple[str, str]:
    """The env row's status and detail for the seats given: the login pair in either mode, and a
    key only for a provider a seat is on (data model, "The env row on read")."""
    missing = list(subject.get("login_missing", []))
    keys = subject.get("keys_missing", {})
    missing.extend(keys[p] for p in sorted(keys) if p in seat_providers)
    if missing:
        return FAIL, f"Missing {', '.join(missing)}"
    return PASS, ALL_KEYS_PRESENT


async def check_env(ctx: CheckContext) -> CheckResult:
    started = time.monotonic()
    subject = env_facts(ctx)
    seat_providers = {ctx.config.seat_spec(s).provider for s in ctx.config.seats}
    status, detail = env_verdict(subject, seat_providers)
    return CheckResult("env", ".env completeness", status, detail, _ms(started), now_iso(), subject)


# Recordings (spec 012 research D9)


async def check_intro_recording(ctx: CheckContext) -> CheckResult:
    started = time.monotonic()
    check_id, row = "intro-recording", "Introduction recording present"
    if ctx.intro_recording_present():
        return CheckResult(check_id, row, PASS, "The pinned run is on this machine", _ms(started), now_iso())
    detail = "The pinned run is not on this machine"
    return CheckResult(check_id, row, FAIL, detail, _ms(started), now_iso())


async def check_replays(ctx: CheckContext) -> CheckResult:
    started = time.monotonic()
    check_id, row = "replays", "Every dataset has a replay"
    missing = ctx.datasets_without_replay()
    if missing:
        detail = f"No recording or golden log for {', '.join(missing)}"
        return CheckResult(check_id, row, FAIL, detail, _ms(started), now_iso())
    return CheckResult(check_id, row, PASS, "A recording or golden log for each", _ms(started), now_iso())


def sequential_checks(ctx: CheckContext) -> list[Check]:
    """The rows that run one after another: PNG export reads Typst's compile, and the local model
    rows read the tags the Ollama row fetched."""
    return [
        Check("ollama", "Ollama reachable", OLLAMA_TIMEOUT_S, check_ollama),
        *local_model_checks(ctx),
        Check("typst", "Typst present, test compile", COMPILE_TIMEOUT_S, check_typst),
        Check("png", "Page PNG export", 5.0, check_png),
        Check("tunnel", "Tunnel reachable from outside", TUNNEL_TIMEOUT_S, check_tunnel),
        Check("disk", "Disk space", 5.0, check_disk),
        Check("env", ".env completeness", 5.0, check_env),
        Check("intro-recording", "Introduction recording present", 5.0, check_intro_recording),
        Check("replays", "Every dataset has a replay", 5.0, check_replays),
    ]


def checks_for(ctx: CheckContext) -> list[Check]:
    """Every check in the page's order: cloud model rows, Ollama, local model rows, then the
    fixed rows (spec 012 research D6)."""
    return [*cloud_model_checks(ctx), *sequential_checks(ctx)]


def recheck_checks(ctx: CheckContext, model_key: str) -> list[Check]:
    """What a seat change reruns (spec 012 research D10): the model's row, with the Ollama row
    first for a local model, then the env row."""
    if model_key not in ctx.config.models:
        raise ValueError(f"unknown model {model_key}")
    checks: list[Check] = []
    if ctx.config.models[model_key].provider == "ollama":
        checks.append(Check("ollama", "Ollama reachable", OLLAMA_TIMEOUT_S, check_ollama))
    checks.append(model_check(ctx, model_key))
    checks.append(Check("env", ".env completeness", 5.0, check_env))
    return checks
