#!/usr/bin/env bash
# Database restore script for Credit Assessment API
#
# Usage:
#   DATABASE_URL=postgresql://... ./scripts/restore.sh /path/to/backup.sql.gz
#
# Environment variables:
#   DATABASE_URL  (required) — PostgreSQL connection string
#
# Arguments:
#   $1  (required) — Path to the gzip-compressed SQL backup file
#
# Recovery time objective (RTO): < 1 hour
# Recovery point objective (RPO): < 1 hour (daily backups)
set -euo pipefail

DB_URL="${DATABASE_URL:?DATABASE_URL is required}"
BACKUP_FILE="${1:?Usage: restore.sh <backup-file>}"

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

gunzip -c "$BACKUP_FILE" | psql "$DB_URL"

echo "Restore completed from: $BACKUP_FILE"
