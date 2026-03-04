# Service Outage Runbook

## Severity: Critical

## Symptoms

- Health check (`GET /health`) returning non-200
- Readiness probe (`GET /ready`) returning `degraded`
- Alert: `HighErrorRate` or `HealthCheckFailure` firing
- Users reporting 5xx errors

## Triage (< 5 minutes)

1. **Check health endpoints**
   ```bash
   curl -s https://api.example.com/health | jq .
   curl -s https://api.example.com/ready | jq .
   ```

2. **Check running containers**
   ```bash
   docker compose ps
   docker compose logs --tail=50 api
   ```

3. **Check metrics**
   ```bash
   curl -s https://api.example.com/metrics | grep http_requests_total
   ```

## Decision Tree

```
Health check failing?
├── Yes → Check container logs for startup errors
│   ├── Database connection error → See database-recovery.md
│   ├── Port binding error → Check for port conflicts
│   └── OOM killed → Increase memory limits
├── No, but high error rate
│   ├── 429 errors → Rate limiting triggered, check customer tiers
│   ├── 401/403 errors → Auth/JWT issues, check jwt_secret config
│   └── 500 errors → Check application logs for stack traces
└── No, but high latency
    ├── Database slow → Check DB connections and query performance
    └── External service slow → Check Stripe API, Sentry connectivity
```

## Resolution Steps

### Container crash loop
```bash
docker compose logs --tail=100 api
docker compose restart api
docker compose ps  # verify healthy
```

### Deploy rollback
```bash
./deploy/rollback.sh
```
See [deployment-rollback.md](deployment-rollback.md) for details.

### Full restart
```bash
docker compose down
docker compose up -d
# Wait for health check
sleep 10
curl -s https://api.example.com/health
```

## Escalation

| Time | Action |
|------|--------|
| 0-5 min | On-call engineer triages |
| 5-15 min | Attempt automated rollback |
| 15-30 min | Escalate to team lead |
| 30+ min | Escalate to engineering manager |

## Post-Incident

1. Update incident timeline
2. Identify root cause
3. Create follow-up tasks
4. Schedule post-mortem within 48 hours
