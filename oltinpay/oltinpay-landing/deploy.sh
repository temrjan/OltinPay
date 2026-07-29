#!/usr/bin/env bash
# Reproducible landing deploy — run ON the server (7demo).
#
# Serves the landing from the repository instead of hand-copied files. Touches
# ONLY the oltinpay-landing container and /srv/oltinpay-landing — nothing else on
# the shared host (the central caddy route and other products are left alone).
#
# Usage (on the server):
#   REPO=/opt/oltinpay bash oltinpay/oltinpay-landing/deploy.sh
set -euo pipefail

REPO="${REPO:-/opt/oltinpay}"                         # OltinPay repo checkout on the server
LANDING="$REPO/oltinpay/oltinpay-landing"
DEST="/srv/oltinpay-landing"                          # static dir mounted into the caddy container
COMPOSE="${COMPOSE:-/root/server/oltinpay/docker-compose.yml}"  # landing compose project

git -C "$REPO" pull --ff-only

# public/ is the ONLY thing served; Caddyfile is config-only (mounted separately).
rsync -a --delete "$LANDING/public/" "$DEST/public/"
cp "$LANDING/Caddyfile" "$DEST/Caddyfile"

docker compose -f "$COMPOSE" up -d oltinpay-landing
echo "deployed landing at $(git -C "$REPO" rev-parse --short HEAD)"
