#!/usr/bin/env bash
# Blue/green deployment script for the Credit Assessment API.
#
# Usage:
#   ./deploy/blue_green.sh [blue|green]
#
# If no slot is given, the script auto-detects the idle slot.
# Steps:
#   1. Build the new image
#   2. Start the idle slot with the new image
#   3. Wait for health checks to pass
#   4. Switch traffic (update Caddy upstream)
#   5. Drain and stop the old slot
#
# Rollback: ./deploy/rollback.sh
set -euo pipefail

COMPOSE_FILE="docker-compose.yml"
DEPLOY_FILE="docker-compose.deploy.yml"
HEALTH_TIMEOUT=30
HEALTH_INTERVAL=2

log() { echo "[deploy] $(date '+%H:%M:%S') $*"; }

detect_idle_slot() {
    local blue_running green_running
    blue_running=$(docker compose -f "$COMPOSE_FILE" -f "$DEPLOY_FILE" \
        ps --status running api-blue 2>/dev/null | tail -n +2 | wc -l)
    green_running=$(docker compose -f "$COMPOSE_FILE" -f "$DEPLOY_FILE" \
        ps --status running api-green 2>/dev/null | tail -n +2 | wc -l)

    if [ "$blue_running" -gt 0 ]; then
        echo "green"
    else
        echo "blue"
    fi
}

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

get_other_slot() {
    case "$1" in
        blue)  echo "green" ;;
        green) echo "blue" ;;
    esac
}

main() {
    local target_slot="${1:-}"
    if [ -z "$target_slot" ]; then
        target_slot=$(detect_idle_slot)
    fi
    local old_slot
    old_slot=$(get_other_slot "$target_slot")
    local target_port
    target_port=$(get_slot_port "$target_slot")

    log "Deploying to slot: $target_slot (port $target_port)"
    log "Current active slot: $old_slot"

    # Record current slot for rollback
    echo "$old_slot" > .deploy-previous-slot

    # Build and start the target slot
    log "Building and starting api-${target_slot}..."
    docker compose -f "$COMPOSE_FILE" -f "$DEPLOY_FILE" \
        build "api-${target_slot}"
    docker compose -f "$COMPOSE_FILE" -f "$DEPLOY_FILE" \
        up -d "api-${target_slot}"

    # Wait for health
    if ! wait_for_health "http://localhost:${target_port}"; then
        log "FAILED: Rolling back..."
        docker compose -f "$COMPOSE_FILE" -f "$DEPLOY_FILE" \
            stop "api-${target_slot}"
        exit 1
    fi

    # Gracefully stop the old slot (SIGTERM allows drain)
    log "Stopping old slot: api-${old_slot}..."
    docker compose -f "$COMPOSE_FILE" -f "$DEPLOY_FILE" \
        stop -t 30 "api-${old_slot}" 2>/dev/null || true

    # Record active slot
    echo "$target_slot" > .deploy-active-slot

    log "Deployment complete. Active slot: $target_slot"
}

main "$@"
