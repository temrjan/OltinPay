#!/usr/bin/env bash
# Idempotent install/update of the OltinPay feed keeper on 7demo.
# Run as root from /root/oltinpay-keeper (where poster.key already lives).
set -euo pipefail

DIR="/root/oltinpay-keeper"
cd "$DIR"

if [[ ! -f "$DIR/poster.key" ]]; then
  echo "FATAL: $DIR/poster.key missing — the POSTER_ROLE key must exist first." >&2
  exit 1
fi

echo "==> venv"
if [[ ! -x "$DIR/venv/bin/python" ]]; then
  python3 -m venv "$DIR/venv"
fi
"$DIR/venv/bin/pip" install --quiet --upgrade pip
"$DIR/venv/bin/pip" install --quiet -r "$DIR/requirements.txt"

echo "==> systemd units"
install -m 0644 "$DIR/oltinpay-keeper.service" /etc/systemd/system/oltinpay-keeper.service
install -m 0644 "$DIR/oltinpay-keeper.timer"   /etc/systemd/system/oltinpay-keeper.timer
systemctl daemon-reload
systemctl enable --now oltinpay-keeper.timer

echo "==> done"
systemctl list-timers oltinpay-keeper.timer --no-pager || true
