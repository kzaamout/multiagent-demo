#!/usr/bin/env sh
# Start the Cloudflare Tunnel for Laptop mode (slice S7, research D8).
# Reads CLOUDFLARE_TUNNEL_TOKEN from .env at the repository root and hands it to cloudflared through the
# TUNNEL_TOKEN environment variable, so the token never appears on a command line. Runs in the foreground;
# Ctrl+C stops it. The public hostname is routed to http://localhost:8000 in the Cloudflare dashboard.
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
token=""
if [ -f "$root/.env" ]; then
    token=$(sed -n 's/^[[:space:]]*CLOUDFLARE_TUNNEL_TOKEN[[:space:]]*=[[:space:]]*//p' "$root/.env" | tail -n 1 | tr -d '"'"'" | tr -d '[:space:]')
fi
if [ -z "$token" ]; then
    echo "CLOUDFLARE_TUNNEL_TOKEN is empty in .env" >&2
    exit 2
fi
if ! command -v cloudflared >/dev/null 2>&1; then
    echo "cloudflared is not on the path (see docs/dependencies.md)" >&2
    exit 2
fi
TUNNEL_TOKEN="$token" exec cloudflared tunnel run
