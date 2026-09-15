"""The setup script writes credentials only into .env and fills template lines in place."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_setup() -> ModuleType:
    spec = importlib.util.spec_from_file_location("setup_script", ROOT / "scripts" / "setup.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_env_values_fill_template_lines_and_are_never_printed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    setup = load_setup()
    env = tmp_path / ".env"
    monkeypatch.setattr(setup, "ENV_PATH", env)
    monkeypatch.setattr(setup, "EXAMPLE_PATH", ROOT / ".env.example")
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_PROFILE", "GEMINI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    secret = "zq9-setup-secret"
    monkeypatch.setenv("GEMINI_API_KEY", secret + "-gemini")
    answers = iter(["AKIA-test-id"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    monkeypatch.setattr(setup.getpass, "getpass", lambda _prompt="": secret)

    from app.live.providers import ModelConfig, SeatChoice

    cloud = ModelConfig.load()
    cloud = ModelConfig(
        providers=cloud.providers,
        models=cloud.models,
        seats={
            "orchestrator": SeatChoice(model="bedrock-sonnet-5"),
            "reviewer": SeatChoice(model="gemini-2-5-pro"),
        },
    )
    setup.ensure_env(argparse.Namespace(yes=True, no_prompt=False), cloud)

    text = env.read_text(encoding="utf-8")
    assert "AWS_ACCESS_KEY_ID=AKIA-test-id" in text
    assert f"AWS_SECRET_ACCESS_KEY={secret}\n" in text
    assert f"GEMINI_API_KEY={secret}-gemini" in text, "copied from the environment with consent"
    assert text.count("AWS_SECRET_ACCESS_KEY=") == 1 and "# AWS_PROFILE=" in text
    out = capsys.readouterr().out
    assert secret not in out and "AKIA-test-id" not in out


def test_local_seats_ask_for_no_cloud_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    setup = load_setup()
    from app.live.providers import ModelConfig, SeatChoice

    env = tmp_path / ".env"
    monkeypatch.setattr(setup, "ENV_PATH", env)
    monkeypatch.setattr(setup, "EXAMPLE_PATH", ROOT / ".env.example")
    monkeypatch.setattr("builtins.input", lambda _prompt="": pytest.fail("asked for input"))
    base = ModelConfig.load()
    local = ModelConfig(
        providers=base.providers, models=base.models, seats={"pricing": SeatChoice(model="llama3-1-8b")}
    )
    setup.ensure_env(argparse.Namespace(yes=False, no_prompt=False), local)
    out = capsys.readouterr().out
    assert "AWS keys are not needed" in out and "Gemini key is not needed" in out
