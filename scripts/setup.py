r"""Set up a presenter laptop for live runs, then check it is ready.

Run it through the bootstrap for your system, which installs uv and the Python dependencies first:
    Windows:        powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
    macOS or Linux: sh scripts/setup.sh
or directly with: uv run python scripts/setup.py

Steps: create .env from .env.example and ask for missing credentials with hidden input; install
Ollama if it is missing and pull the local seat models from config/models.yaml; check every seat's
provider without calling a model. Credential values are written only to .env and never printed.
Options: --yes (install without asking), --no-prompt (never ask; report what is missing),
--skip-ollama, --skip-network-checks, --browser-tests (install Chromium for the visual tests).
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402
from dotenv import dotenv_values, load_dotenv  # noqa: E402

from app.live.providers import ModelConfig, check_availability, unavailable_seats  # noqa: E402

ENV_PATH = ROOT / ".env"
EXAMPLE_PATH = ROOT / ".env.example"
OK, WARN, FAIL = "ok  ", "warn", "FAIL"


def say(status: str, message: str) -> None:
    print(f"  [{status}] {message}")


def ask_yes(question: str, *, default: bool, args: argparse.Namespace) -> bool:
    if args.yes:
        return True
    if args.no_prompt:
        return False
    suffix = " [Y/n] " if default else " [y/N] "
    answer = input(question + suffix).strip().lower()
    return default if not answer else answer.startswith("y")


# .env


def _set_env_value(name: str, value: str) -> None:
    """Replace NAME= in .env, uncommenting a template line if present, or append it."""
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    for index, line in enumerate(lines):
        stripped = line.strip().lstrip("#").strip()
        if stripped.startswith(name + "="):
            lines[index] = f"{name}={value}"
            break
    else:
        lines.append(f"{name}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_env(args: argparse.Namespace) -> None:
    print("\n1. Credentials in .env")
    if not ENV_PATH.exists():
        shutil.copyfile(EXAMPLE_PATH, ENV_PATH)
        say(OK, "created .env from .env.example")
    values = {k: (v or "") for k, v in dotenv_values(ENV_PATH).items()}

    def present(name: str) -> bool:
        return bool(values.get(name, "").strip())

    def fill(name: str, label: str, secret: bool) -> None:
        if present(name):
            say(OK, f"{name} is set")
            return
        from_environment = os.environ.get(name, "").strip()
        if from_environment and ask_yes(
            f"  {name} is set in this computer's environment but not in .env. Copy it into .env?",
            default=True,
            args=args,
        ):
            _set_env_value(name, from_environment)
            values[name] = from_environment
            say(OK, f"{name} copied into .env")
            return
        if args.no_prompt:
            say(WARN, f"{name} is missing from .env")
            return
        entered = (getpass.getpass if secret else input)(f"  {label} (Enter to skip): ").strip()
        if entered:
            _set_env_value(name, entered)
            values[name] = entered
            say(OK, f"{name} saved to .env")
        else:
            say(WARN, f"{name} skipped")

    if present("AWS_PROFILE"):
        say(OK, "AWS_PROFILE is set, so Bedrock uses that profile instead of access keys")
    else:
        fill("AWS_ACCESS_KEY_ID", "AWS access key ID for Bedrock", secret=False)
        fill("AWS_SECRET_ACCESS_KEY", "AWS secret access key", secret=True)
    fill("GEMINI_API_KEY", "Google Gemini API key", secret=True)

    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_PROFILE", "GEMINI_API_KEY"):
        outside = os.environ.get(name)
        if outside and present(name) and outside != values.get(name):
            say(
                WARN,
                f"{name} in this computer's environment differs from .env; the app uses the environment "
                "value. Remove the environment variable to use .env.",
            )


# Ollama


def _ollama_host(config: ModelConfig) -> str:
    return str(config.providers.get("ollama", {}).get("host", "http://localhost:11434")).rstrip("/")


def _ollama_up(host: str) -> bool:
    try:
        return httpx.get(f"{host}/api/tags", timeout=2.0).status_code == 200
    except httpx.HTTPError:
        return False


def _ollama_binary() -> Path | None:
    found = shutil.which("ollama")
    if found:
        return Path(found)
    if platform.system() == "Windows":
        candidate = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
        if candidate.exists():
            return candidate
    return None


def _install_ollama(args: argparse.Namespace) -> bool:
    system = platform.system()
    if system == "Windows" and shutil.which("winget"):
        if not ask_yes("  Ollama is not installed. Install it now with winget?", default=True, args=args):
            return False
        command = [
            "winget", "install", "--id", "Ollama.Ollama", "-e", "--silent",
            "--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity",
        ]  # fmt: skip
        return subprocess.run(command, check=False).returncode == 0
    if system == "Linux":
        if not ask_yes(
            "  Ollama is not installed. Run the official install script from ollama.com (needs sudo)?",
            default=True,
            args=args,
        ):
            return False
        return (
            subprocess.run(
                ["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"], check=False
            ).returncode
            == 0
        )
    say(
        FAIL,
        "Ollama is not installed. Download it from https://ollama.com/download, start it, and run setup again.",
    )
    return False


def _start_ollama(binary: Path) -> None:
    app = binary.parent / "ollama app.exe"
    target = [str(app)] if app.exists() else [str(binary), "serve"]
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(
        target,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=flags,
    )


def _pull(host: str, model: str) -> bool:
    print(f"  pulling {model} from the Ollama library")
    last = -10
    with httpx.stream(
        "POST", f"{host}/api/pull", json={"model": model, "stream": True}, timeout=None
    ) as response:
        for line in response.iter_lines():
            if not line:
                continue
            status = json.loads(line)
            if "error" in status:
                say(FAIL, f"{model}: {status['error']}")
                return False
            total, completed = status.get("total"), status.get("completed")
            if total and completed is not None:
                percent = int(completed * 100 / total)
                if percent >= last + 10:
                    last = percent
                    print(f"    {status.get('status', 'downloading')}: {percent}%")
    return True


def ensure_ollama(config: ModelConfig, args: argparse.Namespace) -> None:
    print("\n2. Ollama and the local models")
    wanted = sorted(
        {
            config.seat_spec(seat).model_id
            for seat in config.seats
            if config.seat_spec(seat).provider == "ollama"
        }
    )
    if not wanted:
        say(OK, "no seat uses a local model")
        return
    host = _ollama_host(config)
    if not _ollama_up(host):
        binary = _ollama_binary()
        if binary is None:
            if not _install_ollama(args):
                say(WARN, "Ollama not installed; seats on local models cannot run live")
                return
            binary = _ollama_binary()
        if binary is None:
            say(FAIL, "Ollama installed but not found; open a new terminal and run setup again")
            return
        if not _ollama_up(host):
            print("  starting Ollama")
            _start_ollama(binary)
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline and not _ollama_up(host):
                time.sleep(1)
        if not _ollama_up(host):
            say(FAIL, f"Ollama did not answer at {host}; start the Ollama app and run setup again")
            return
    say(OK, f"Ollama answers at {host}")
    tags = httpx.get(f"{host}/api/tags", timeout=5.0).json().get("models", [])
    present = {str(m.get("name")) for m in tags}
    for model in wanted:
        if model in present or f"{model}:latest" in present:
            say(OK, f"{model} is pulled")
        elif _pull(host, model):
            say(OK, f"{model} pulled")
    say(OK, "context length is sent with each request from config/models.yaml; no Ollama setting to change")


# Checks


def network_checks(config: ModelConfig) -> None:
    """Checks that cost nothing: identity and model metadata, never a model call."""
    print("\n4. Provider access, without calling a model")
    providers_in_use = {config.seat_spec(seat).provider for seat in config.seats}
    if "bedrock" in providers_in_use:
        try:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError

            region = config.providers["bedrock"].get("region")
            session = boto3.Session(region_name=region)
            if session.get_credentials() is None:
                raise LookupError
            session.client("sts").get_caller_identity()
            say(OK, "AWS credentials are valid")
            bedrock = session.client("bedrock")
            for model_id in sorted(
                {
                    config.seat_spec(s).model_id
                    for s in config.seats
                    if config.seat_spec(s).provider == "bedrock"
                }
            ):
                try:
                    profile = bedrock.get_inference_profile(inferenceProfileIdentifier=model_id)
                    foundation = profile["models"][0]["modelArn"].rsplit("/", 1)[-1]
                    access = bedrock.get_foundation_model_availability(modelId=foundation)
                    authorized = access.get("authorizationStatus") == "AUTHORIZED"
                    agreed = access.get("agreementAvailability", {}).get("status") == "AVAILABLE"
                    entitled = access.get("entitlementAvailability") == "AVAILABLE"
                    if authorized and agreed and entitled:
                        say(OK, f"{model_id} is enabled in {region}")
                    else:
                        say(
                            FAIL,
                            f"{model_id}: open the Bedrock console in {region}, Model access, and enable the model "
                            "(Anthropic models may ask for a one-time use case form)",
                        )
                except ClientError as error:
                    code = error.response.get("Error", {}).get("Code", "error")
                    say(
                        WARN,
                        f"{model_id}: could not check model access ({code}); the keys may lack bedrock:Get permissions",
                    )
        except LookupError:
            say(WARN, "no AWS credentials set, so Bedrock access was not checked")
        except (BotoCoreError, ClientError) as error:
            say(FAIL, f"AWS refused the credentials ({type(error).__name__})")
    if "google" in providers_in_use:
        key = os.environ.get("GEMINI_API_KEY", "")
        for model_id in sorted(
            {config.seat_spec(s).model_id for s in config.seats if config.seat_spec(s).provider == "google"}
        ):
            name = model_id.split("/", 1)[-1]
            try:
                response = httpx.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{name}",
                    headers={"x-goog-api-key": key},
                    timeout=15.0,
                )
                if response.status_code == 200:
                    say(OK, f"Gemini key works and {name} is available")
                else:
                    say(FAIL, f"Gemini refused the key or model {name} (HTTP {response.status_code})")
            except httpx.HTTPError as error:
                say(FAIL, f"Gemini not reachable ({type(error).__name__})")


def readiness(config: ModelConfig) -> bool:
    print("\n3. Seat providers")
    availability = check_availability(config)
    in_use = {config.seat_spec(seat).provider for seat in config.seats}
    for name, state in availability.items():
        if name not in in_use:
            print(f"         {name}: not used by any seat")
            continue
        say(OK if state.available else WARN, f"{name}: {state.reason}")
    problems = unavailable_seats(config, availability)
    for problem in problems:
        say(FAIL, problem)
    return not problems


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--yes", action="store_true", help="install without asking")
    parser.add_argument("--no-prompt", action="store_true", help="never ask; report what is missing")
    parser.add_argument("--skip-ollama", action="store_true")
    parser.add_argument("--skip-network-checks", action="store_true")
    parser.add_argument("--browser-tests", action="store_true", help="install Chromium for the visual tests")
    args = parser.parse_args(argv)

    print("Sterling AI demo setup")
    ensure_env(args)
    load_dotenv(ENV_PATH, override=False)
    config = ModelConfig.load()
    if not args.skip_ollama:
        ensure_ollama(config, args)
    ready = readiness(config)
    if not args.skip_network_checks:
        network_checks(config)
    if args.browser_tests:
        print("\n5. Browser for the visual tests")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)

    print()
    if ready:
        print("Ready for live runs. Start the demo with:")
    else:
        print(
            "Not every seat can run live yet; datasets without curated inputs still run on stubs. Start the demo with:"
        )
    print("  uv run uvicorn app.main:app --port 8000")
    print("then open http://localhost:8000/demo")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
