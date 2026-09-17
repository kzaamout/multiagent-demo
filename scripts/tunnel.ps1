# Start the Cloudflare Tunnel for Laptop mode (slice S7, research D8).
# Reads CLOUDFLARE_TUNNEL_TOKEN from .env at the repository root and hands it to cloudflared through the
# TUNNEL_TOKEN environment variable, so the token never appears on a command line. Runs in the foreground;
# Ctrl+C stops it. The public hostname is routed to http://localhost:8000 in the Cloudflare dashboard.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $root '.env'
$token = ''
if (Test-Path $envPath) {
    foreach ($line in Get-Content $envPath) {
        if ($line -match '^\s*CLOUDFLARE_TUNNEL_TOKEN\s*=\s*(.*)$') {
            $token = $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
}
if (-not $token) {
    [Console]::Error.WriteLine('CLOUDFLARE_TUNNEL_TOKEN is empty in .env')
    exit 2
}
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    [Console]::Error.WriteLine('cloudflared is not on the path (winget install Cloudflare.cloudflared)')
    exit 2
}
$env:TUNNEL_TOKEN = $token
& cloudflared tunnel run
exit $LASTEXITCODE
