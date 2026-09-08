#!/usr/bin/env bash
# Deploy ismaisiealive.org: rsync the code to the droplet and restart the service.
# One-time setup: set DROPLET_HOST below (or export it in your shell).
set -euo pipefail
cd "$(dirname "$0")"

DROPLET_HOST="${DROPLET_HOST:-root@137.184.19.209}"
REMOTE_DIR="/home/maisie/IsMaisieAlive"
SERVICE="ismaisiealive"

if [ "$DROPLET_HOST" = "CHANGE_ME" ]; then
    echo "Edit deploy.sh and set DROPLET_HOST to root@YOUR_DROPLET_IP (or export DROPLET_HOST)." >&2
    exit 1
fi

echo "==> Syncing code to $DROPLET_HOST..."
rsync -av --delete \
    --exclude .venv --exclude data --exclude .env \
    --exclude __pycache__ --exclude '*.pyc' --exclude .git \
    ./ "$DROPLET_HOST:$REMOTE_DIR/"

echo "==> Updating dependencies and fixing ownership..."
ssh "$DROPLET_HOST" "chown -R maisie:maisie $REMOTE_DIR && su - maisie -c 'cd $REMOTE_DIR && .venv/bin/pip install -q -r requirements.txt'"

echo "==> Restarting $SERVICE..."
ssh "$DROPLET_HOST" "systemctl restart $SERVICE && sleep 1 && systemctl is-active $SERVICE"

echo "==> Deployed. Maisie's status is live at https://ismaisiealive.org"
