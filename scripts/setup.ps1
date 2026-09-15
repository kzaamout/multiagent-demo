# Sets up the demo on Windows: installs uv if it is missing, installs the Python dependencies,
# then runs scripts/setup.py for .env, Ollama and the local model, and the readiness check.
#
# From the repository folder:
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
# Options are passed to scripts/setup.py, for example: -File scripts\setup.ps1 --yes

# Native tools write progress to stderr, so failures are read from exit codes rather than error records.
$ErrorActionPreference = 'Continue'
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host 'uv is not installed. Installing it with the official installer from astral.sh.'
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$HOME\.local\bin;$env:Path"
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host 'uv installed but is not on PATH yet. Open a new terminal and run this script again.'
        exit 1
    }
}

$env:PYTHONUTF8 = '1'
uv sync
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run python scripts/setup.py @args
exit $LASTEXITCODE
