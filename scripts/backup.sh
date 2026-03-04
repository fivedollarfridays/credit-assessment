#!/usr/bin/env bash
# Database backup script for Credit Assessment API
#
# Usage:
#   DATABASE_URL=postgresql://... ./scripts/backup.sh
#
# Environment variables:
#   DATABASE_URL  (required) — PostgreSQL connection string
#   BACKUP_DIR    (optional) — Defaults to /var/backups/credit-assessment
#
# This script is intended to be run via cron for automated daily backups.
# Example cron entry (daily at 02:00 UTC):
#   0 2 * * * DATABASE_URL=postgresql://... /opt/app/scripts/backup.sh
set -euo pipefail

DB_URL="${DATABASE_URL:?DATABASE_URL is required}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/credit-assessment}"
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
FILENAME="credit_assessment_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

pg_dump "$DB_URL" | gzip > "${BACKUP_DIR}/${FILENAME}"

echo "Backup created: ${BACKUP_DIR}/${FILENAME}"
