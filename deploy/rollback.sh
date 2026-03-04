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

_LOG_PREFIX="rollback"
HEALTH_TIMEOUT=20
. "$(dirname "$0")/_common.sh"

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
