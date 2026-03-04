#!/usr/bin/env bash
# Shared functions for deployment scripts.
# Source this file: . "$(dirname "$0")/_common.sh"
set -euo pipefail

COMPOSE_FILE="docker-compose.yml"
DEPLOY_FILE="docker-compose.deploy.yml"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-30}"
HEALTH_INTERVAL=2

_LOG_PREFIX="${_LOG_PREFIX:-deploy}"

log() { echo "[${_LOG_PREFIX}] $(date '+%H:%M:%S') $*"; }

wait_for_health() {
    local url="$1"
    local elapsed=0
    log "Waiting for $url to become healthy (timeout=${HEALTH_TIMEOUT}s)..."
    while [ "$elapsed" -lt "$HEALTH_TIMEOUT" ]; do
        if curl -sf "$url/health" > /dev/null 2>&1 && \
           curl -sf "$url/ready" > /dev/null 2>&1; then
            log "Health check passed at $url"
            return 0
        fi
        sleep "$HEALTH_INTERVAL"
        elapsed=$((elapsed + HEALTH_INTERVAL))
    done
    log "ERROR: Health check timed out for $url"
    return 1
}

get_slot_port() {
    case "$1" in
        blue)  echo "8001" ;;
        green) echo "8002" ;;
        *)     echo "unknown"; return 1 ;;
    esac
}
