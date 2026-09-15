#!/bin/sh
# Sets up the demo on macOS or Linux: installs uv if it is missing, installs the Python dependencies,
# then runs scripts/setup.py for .env, Ollama and the local model, and the readiness check.
#
# From the repository folder:
#   sh scripts/setup.sh
# Options are passed to scripts/setup.py, for example: sh scripts/setup.sh --yes
set -eu
cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. Installing it with the official installer from astral.sh."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  PATH="$HOME/.local/bin:$PATH"
  export PATH
fi

export PYTHONUTF8=1
uv sync
exec uv run python scripts/setup.py "$@"
