# Database Recovery Runbook

## Severity: Critical

## Symptoms

- Readiness probe returning `{"database": "unavailable", "status": "degraded"}`
- Application logs showing `sqlalchemy.exc.OperationalError`
- Alert: `HealthCheckFailure` with database component down

## Triage (< 5 minutes)

1. **Check database connectivity**
   ```bash
   docker compose exec db pg_isready -U postgres
   ```

2. **Check database logs**
   ```bash
   docker compose logs --tail=50 db
   ```

3. **Check disk space**
   ```bash
   docker compose exec db df -h /var/lib/postgresql/data
   ```

## Decision Tree

```
Database reachable?
├── No → Container down
│   ├── OOM killed → Increase memory, restart
│   ├── Disk full → Free space, restart
│   └── Crash → Check logs, restart or restore
├── Yes, but connections refused
│   ├── Max connections reached → Kill idle connections
│   └── pg_hba.conf issue → Check auth config
└── Yes, but queries slow
    ├── Long-running queries → Check pg_stat_activity
    └── Missing indexes → Check query plans
```

## Resolution Steps

### Restart database
```bash
docker compose restart db
sleep 5
docker compose exec db pg_isready -U postgres
```

### Restore from backup
```bash
# List available backups
ls -la /var/backups/credit-assessment/

# Restore most recent
./scripts/restore.sh /var/backups/credit-assessment/credit_assessment_LATEST.sql.gz

# Verify
docker compose exec db psql -U postgres -c "SELECT count(*) FROM assessment_records;"
```

### Run pending migrations
```bash
docker compose exec api alembic upgrade head
```

### Kill idle connections
```bash
docker compose exec db psql -U postgres -c "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE state = 'idle'
  AND query_start < now() - interval '10 minutes';
"
```

## Recovery Objectives

| Metric | Target |
|--------|--------|
| RTO (Recovery Time) | < 1 hour |
| RPO (Recovery Point) | < 1 hour (daily backups + WAL) |

## Escalation

| Time | Action |
|------|--------|
| 0-5 min | On-call attempts restart |
| 5-15 min | Attempt restore from backup |
| 15-30 min | Escalate to DBA/team lead |
| 30+ min | Escalate to engineering manager |
