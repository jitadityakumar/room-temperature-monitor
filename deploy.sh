#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_ENV="$SCRIPT_DIR/.env.deploy"

if [ ! -f "$DEPLOY_ENV" ]; then
  echo "Error: $DEPLOY_ENV not found. Copy .env.deploy.example and fill it in."
  exit 1
fi

source "$DEPLOY_ENV"

deploy_local() {
  echo "=== Deploying locally ==="
  (
    cd "$LOCAL_REPO_DIR"
    git pull origin main
    cd poller
    docker compose up -d --build
  )
  echo "Local deploy done."
}

deploy_remote() {
  echo "=== Deploying to $REMOTE_HOST ==="
  ssh "$REMOTE_USER@$REMOTE_HOST" \
    "cd '$REMOTE_REPO_DIR' && git pull origin main \
      && cd poller && docker compose up -d --build \
      && cd ../kiosk && docker compose up -d --build"
  echo "Remote deploy done."
}

case "${1:-both}" in
  local)  deploy_local ;;
  remote) deploy_remote ;;
  both)   deploy_local && deploy_remote ;;
  *)
    echo "Usage: ./deploy.sh [local|remote|both]"
    exit 1
    ;;
esac
