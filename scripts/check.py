"""Quality gate runner (constitution XVI).

Runs ruff, mypy, pytest, the em-dash lint, and the .env leak test in order and stops
on the first failure. Usage: uv run python scripts/check.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STEPS: list[tuple[str, list[str]]] = [
    ("ruff check", [sys.executable, "-m", "ruff", "check", "."]),
    ("ruff format", [sys.executable, "-m", "ruff", "format", "--check", "."]),
    ("mypy", [sys.executable, "-m", "mypy", "app", "scripts", "tests"]),
    ("pytest", [sys.executable, "-m", "pytest", "-m", "not visual"]),
    ("em-dash lint", [sys.executable, "scripts/lint_em_dash.py"]),
    ("env leak test", [sys.executable, "-m", "pytest", "tests/lint/test_env_leak.py"]),
]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    env = dict(os.environ, PYTHONUTF8="1")
    for name, cmd in STEPS:
        print(f"==> {name}")
        result = subprocess.run(cmd, cwd=ROOT, env=env)
        if result.returncode != 0:
            print(f"FAIL: {name} (exit {result.returncode})")
            return result.returncode
    print("all gates green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
