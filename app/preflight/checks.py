"""The eight pre-flight checks (spec 0.7 section 2.4, slice S7, research D2 to D4 and D7 to D9).

Every check returns a CheckResult and never raises. Detail lines are one sentence each and never
carry a credential value or a provider's message text (constitution XVII): a failure names the
exception's class, a timeout names the limit. Every outside call is injectable through the
CheckContext so the suite runs without a network, a compiler, or a model.
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
from app.live.providers import Availability, ModelConfig, strands_model_for
from app.live.seat_call import SeatModel
from app.preflight.result import FAIL, PASS, SKIP, CheckResult

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
    scratch: dict[str, Any] = field(default_factory=dict)

    @property
    def cloud_mode(self) -> bool:
        return self.settings.run_mode == "cloud"

    def seats_on(self, provider: str) -> list[str]:
        return [s for s in self.config.seats if self.config.seat_spec(s).provider == provider]


@dataclass(frozen=True)
class Check:
    id: str
    name: str
    essential: bool
    timeout_s: float
    run: Callable[[CheckContext], Awaitable[CheckResult]]


def _ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _host_label(host: str) -> str:
    return host.split("://", 1)[-1].rstrip("/")


def short_label(label: str) -> str:
    """ "claude-sonnet-5 via Bedrock" reads "claude-sonnet-5" on the row."""
    return label.split(" via ", 1)[0].strip()


# Provider rows (research D3)


def provider_checks(ctx: CheckContext) -> list[Check]:
    checks: list[Check] = []
    for name, provider in ctx.config.providers.items():
        if name == "ollama":
            continue
        seats = ctx.seats_on(name)
        state = ctx.availability.get(name)
        key_present = bool(state and state.available)
        if not seats and not key_present:
            continue
        if seats:
            model_key = ctx.config.seats[seats[0]].model
        else:
            candidates = [k for k, spec in ctx.config.models.items() if spec.provider == name]
            if not candidates:
                continue
            model_key = candidates[0]
        label = str(provider.get("label", name))
        checks.append(
            Check(
                id=f"provider:{name}",
                name=f"{label} responds",
                essential=bool(seats),
                timeout_s=PROVIDER_TIMEOUT_S,
                run=_provider_runner(name, model_key, bool(seats), label),
            )
        )
    return checks


def _provider_runner(
    name: str, model_key: str, essential: bool, label: str
) -> Callable[[CheckContext], Awaitable[CheckResult]]:
    async def run(ctx: CheckContext) -> CheckResult:
        check_id = f"provider:{name}"
        row = f"{label} responds"
        started = time.monotonic()
        model_label = short_label(ctx.config.models[model_key].label)
        try:
            config = ctx.config.with_seat(PROBE_SEAT, model_key)
            seat_model = ctx.seat_model_factory(config, PROBE_SEAT)
            await asyncio.wait_for(ctx.probe(seat_model), PROVIDER_TIMEOUT_S)
        except TimeoutError:
            detail = f"no answer within {int(PROVIDER_TIMEOUT_S)} s"
            return CheckResult(check_id, row, FAIL, detail, essential, _ms(started))
        except Exception as error:  # noqa: BLE001
            detail = f"{model_label} did not answer ({type(error).__name__})"
            return CheckResult(check_id, row, FAIL, detail, essential, _ms(started))
        elapsed = _ms(started)
        return CheckResult(check_id, row, PASS, f"{model_label} answered in {elapsed} ms", essential, elapsed)

    return run


# Ollama (research D7)


async def check_ollama(ctx: CheckContext) -> CheckResult:
    started = time.monotonic()
    check_id, row = "ollama", "Ollama reachable, models present"
    seats = ctx.seats_on("ollama")
    essential = bool(seats) and not ctx.cloud_mode
    if ctx.cloud_mode:
        if seats:
            detail = f"{', '.join(seats)} still on local models; move them in Settings"
            return CheckResult(check_id, row, FAIL, detail, True, _ms(started))
        return CheckResult(check_id, row, SKIP, CLOUD_MODE_SKIP, False, _ms(started))
    provider = ctx.config.providers.get("ollama", {})
    host = str(provider.get("host", "http://localhost:11434"))
    wanted = sorted({ctx.config.seat_spec(s).model_id for s in seats})
    if not wanted:
        wanted = sorted({m.model_id for m in ctx.config.models.values() if m.provider == "ollama"})
    try:
        names = await asyncio.to_thread(ctx.tags, host, OLLAMA_TIMEOUT_S)
    except Exception:  # noqa: BLE001
        detail = f"Ollama not reachable at {_host_label(host)}"
        return CheckResult(check_id, row, FAIL, detail, essential, _ms(started))
    missing = [w for w in wanted if w not in names and f"{w}:latest" not in names]
    if missing:
        return CheckResult(check_id, row, FAIL, f"not pulled: {', '.join(missing)}", essential, _ms(started))
    detail = f"{', '.join(wanted)} present at {_host_label(host)}"
    return CheckResult(check_id, row, PASS, detail, essential, _ms(started))


# Typst and PNG (research D4)


async def check_typst(ctx: CheckContext) -> CheckResult:
    started = time.monotonic()
    check_id, row = "typst", "Typst present, test compile"
    versions = await asyncio.to_thread(tools_available)
    for tool in ("typst", "pandoc"):
        if versions.get(tool) is None:
            return CheckResult(check_id, row, FAIL, f"{tool} not on the path", True, _ms(started))
    folder = ctx.settings.runs_dir / PREFLIGHT_FOLDER
    try:
        markdown = FIXTURE_PATH.read_text(encoding="utf-8")
        compiled = await asyncio.to_thread(ctx.compile, folder, markdown)
    except CompileError as error:
        return CheckResult(check_id, row, FAIL, str(error).splitlines()[0], True, _ms(started))
    except Exception as error:  # noqa: BLE001
        return CheckResult(
            check_id, row, FAIL, f"compile failed ({type(error).__name__})", True, _ms(started)
        )
    ctx.scratch["compiled"] = compiled
    seconds = compiled.elapsed_ms / 1000
    detail = f"typst {versions['typst']}, {compiled.page_count} pages in {seconds:.1f} s"
    return CheckResult(check_id, row, PASS, detail, True, _ms(started))


async def check_png(ctx: CheckContext) -> CheckResult:
    started = time.monotonic()
    check_id, row = "png", "Page PNG export"
    compiled = ctx.scratch.get("compiled")
    if compiled is None:
        return CheckResult(check_id, row, FAIL, "no compile to export", True, _ms(started))
    count = len(compiled.page_images)
    if count == 0:
        return CheckResult(check_id, row, FAIL, "Export produced 0 files", True, _ms(started))
    detail = f"{count} PNGs written to runs/{PREFLIGHT_FOLDER}/"
    return CheckResult(check_id, row, PASS, detail, True, _ms(started))


# Tunnel (research D8)


async def check_tunnel(ctx: CheckContext) -> CheckResult:
    started = time.monotonic()
    check_id, row = "tunnel", "Tunnel reachable from outside"
    hostname = ctx.settings.tunnel_hostname.strip()
    if not hostname:
        return CheckResult(check_id, row, SKIP, NO_TUNNEL_HOSTNAME, False, _ms(started))
    url = f"https://{hostname}/login"
    try:
        status, ms = await asyncio.to_thread(ctx.fetch, url, TUNNEL_TIMEOUT_S)
    except Exception:  # noqa: BLE001
        return CheckResult(check_id, row, FAIL, TUNNEL_DOWN, False, _ms(started))
    if status != 200:
        return CheckResult(check_id, row, FAIL, f"HTTP {status} from the tunnel", False, _ms(started))
    return CheckResult(check_id, row, PASS, f"{hostname} answered in {ms} ms", False, _ms(started))


# Disk (research D9)


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
        return CheckResult(check_id, row, FAIL, "could not read free space", True, _ms(started))
    if free_gb < DISK_MIN_GB:
        detail = f"Under {DISK_MIN_GB:g} GB free ({free_gb:.1f} GB)"
        return CheckResult(check_id, row, FAIL, detail, True, _ms(started))
    return CheckResult(check_id, row, PASS, f"{free_gb:.0f} GB free", True, _ms(started))


# .env completeness (research D9)


def missing_env_names(ctx: CheckContext) -> list[str]:
    missing: list[str] = []
    if not ctx.settings.demo_username:
        missing.append("DEMO_USERNAME")
    if not ctx.settings.demo_password:
        missing.append("DEMO_PASSWORD")
    for name, provider in ctx.config.providers.items():
        if name == "ollama" or not ctx.seats_on(name):
            continue
        if name == "bedrock":
            if not ctx.aws_credentials():
                missing.append("AWS credentials")
            continue
        key = str(provider.get("env_key", ""))
        if key and not ctx.env.get(key):
            missing.append(key)
    return missing


async def check_env(ctx: CheckContext) -> CheckResult:
    started = time.monotonic()
    check_id, row = "env", ".env completeness"
    missing = missing_env_names(ctx)
    if missing:
        return CheckResult(check_id, row, FAIL, f"Missing {', '.join(missing)}", True, _ms(started))
    return CheckResult(check_id, row, PASS, ALL_KEYS_PRESENT, True, _ms(started))


def checks_for(ctx: CheckContext) -> list[Check]:
    """Every check in the page's order: provider rows, then the six fixed rows (data-model.md)."""
    ollama_seats = ctx.seats_on("ollama")
    return [
        *provider_checks(ctx),
        Check(
            "ollama",
            "Ollama reachable, models present",
            bool(ollama_seats) and not ctx.cloud_mode,
            OLLAMA_TIMEOUT_S,
            check_ollama,
        ),
        Check("typst", "Typst present, test compile", True, COMPILE_TIMEOUT_S, check_typst),
        Check("png", "Page PNG export", True, 5.0, check_png),
        Check("tunnel", "Tunnel reachable from outside", False, TUNNEL_TIMEOUT_S, check_tunnel),
        Check("disk", "Disk space", True, 5.0, check_disk),
        Check("env", ".env completeness", True, 5.0, check_env),
    ]
