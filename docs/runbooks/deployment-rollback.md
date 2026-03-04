# Deployment Rollback Runbook

## Severity: Warning

## When to Rollback

- New deployment failing health checks
- Error rate spike after deployment
- Latency degradation after deployment
- Critical bug discovered in new release

## Automated Rollback (< 30 seconds)

```bash
./deploy/rollback.sh
```

This script:
1. Identifies the previously active deployment slot (blue/green)
2. Restarts it from the existing image (no rebuild)
3. Validates health via `/health` and `/ready`
4. Stops the failed deployment slot

## Manual Rollback

### Step 1: Identify current deployment
```bash
docker compose -f docker-compose.deploy.yml ps
```

### Step 2: Start previous version
```bash
# If blue is current (failing), start green
docker compose -f docker-compose.deploy.yml up -d api-green

# Wait for health
sleep 10
curl -s http://localhost:8002/health
```

### Step 3: Stop failing deployment
```bash
docker compose -f docker-compose.deploy.yml stop api-blue
```

### Step 4: Verify
```bash
curl -s http://localhost:8002/health  # should return {"status": "ok"}
curl -s http://localhost:8002/ready   # should return {"status": "ok"}
```

## Git-based Rollback

If you need to revert to a specific version:
```bash
git log --oneline -10  # find the good commit
git revert HEAD        # revert the bad commit
git push origin main   # trigger CI/CD
```

## Post-Rollback

1. Notify the team of the rollback
2. Investigate the root cause of the failed deployment
3. Fix the issue in a new branch
4. Re-deploy through normal CI/CD pipeline

## Escalation

| Time | Action |
|------|--------|
| 0-2 min | Run automated rollback |
| 2-5 min | If automated fails, manual rollback |
| 5-15 min | Escalate to team lead |
| 15+ min | Escalate to engineering manager |
