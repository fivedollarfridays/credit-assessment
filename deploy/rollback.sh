#!/usr/bin/env bash
# Rollback to the previous deployment slot.
#
# Usage:
#   ./deploy/rollback.sh
#
# Reads .deploy-previous-slot to determine which slot to restore,
# then starts it and stops the current active slot.
# Target: rollback in < 30 seconds (no rebuild needed).
set -euo pipefail

COMPOSE_FILE="docker-compose.yml"
DEPLOY_FILE="docker-compose.deploy.yml"
HEALTH_TIMEOUT=20
HEALTH_INTERVAL=2

log() { echo "[rollback] $(date '+%H:%M:%S') $*"; }

wait_for_health() {
    local url="$1"
    local elapsed=0
    log "Waiting for $url to become healthy..."
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
    esac
}

main() {
    if [ ! -f .deploy-previous-slot ]; then
        log "ERROR: No previous slot recorded. Nothing to roll back to."
        exit 1
    fi

    local previous_slot
    previous_slot=$(cat .deploy-previous-slot)
    local previous_port
    previous_port=$(get_slot_port "$previous_slot")
    local current_slot
    current_slot=$(cat .deploy-active-slot 2>/dev/null || echo "unknown")

    log "Rolling back: $current_slot -> $previous_slot"

    # Start the previous slot (image already exists, no rebuild)
    docker compose -f "$COMPOSE_FILE" -f "$DEPLOY_FILE" \
        up -d "api-${previous_slot}"

    # Wait for health
    if ! wait_for_health "http://localhost:${previous_port}"; then
        log "ERROR: Rollback target is unhealthy. Manual intervention required."
        exit 1
    fi

    # Stop the current (failed) slot
    if [ "$current_slot" != "unknown" ]; then
        log "Stopping failed slot: api-${current_slot}..."
        docker compose -f "$COMPOSE_FILE" -f "$DEPLOY_FILE" \
            stop -t 30 "api-${current_slot}" 2>/dev/null || true
    fi

    # Update active slot marker
    echo "$previous_slot" > .deploy-active-slot

    log "Rollback complete. Active slot: $previous_slot"
}

main "$@"
