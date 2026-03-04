# Security Incident Runbook

## Severity: Critical

## Symptoms

- Unusual API key usage patterns
- Authentication bypass attempts in logs
- Data exfiltration indicators
- Sentry alerts for unexpected errors
- Reports of unauthorized access

## Immediate Response (< 15 minutes)

### Step 1: Contain
```bash
# Rotate JWT secret immediately
export JWT_SECRET=$(openssl rand -hex 32)
docker compose restart api

# Revoke compromised API keys (if known)
curl -X DELETE https://api.example.com/admin/api-keys/{compromised_key} \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Step 2: Assess scope
```bash
# Check recent access logs
docker compose logs --since=1h api | grep -E "401|403|500"

# Check for unusual patterns
docker compose logs --since=1h api | grep -i "unauthorized\|forbidden\|invalid"
```

### Step 3: Preserve evidence
```bash
# Snapshot current logs
docker compose logs api > /tmp/incident_$(date +%Y%m%d_%H%M%S).log

# Snapshot database
./scripts/backup.sh
```

## Decision Tree

```
Type of incident?
├── Compromised API key
│   ├── Revoke key immediately
│   ├── Audit key usage in logs
│   └── Notify affected customer
├── JWT secret leak
│   ├── Rotate secret (invalidates ALL tokens)
│   ├── Force all users to re-authenticate
│   └── Audit recent token usage
├── SQL injection attempt
│   ├── Review Sentry for actual breaches
│   ├── SQLAlchemy parameterized queries should prevent
│   └── Check for any data modification
└── Unauthorized data access
    ├── Check tenant isolation (org_id scoping)
    ├── Audit cross-org data access
    └── Notify affected tenants
```

## Communication

| Audience | When | Channel |
|----------|------|---------|
| Engineering team | Immediately | Slack #incidents |
| Security team | < 15 min | PagerDuty escalation |
| Affected customers | < 1 hour | Email notification |
| Management | < 2 hours | Incident report |
| Legal/compliance | < 24 hours | Formal notification |

## Post-Incident

1. Complete incident timeline
2. Preserve all logs and evidence
3. Conduct root cause analysis
4. File compliance notifications (GDPR/CCPA if applicable)
5. Schedule post-mortem within 24 hours
6. Update security controls based on findings

## Escalation

| Time | Action |
|------|--------|
| 0-5 min | On-call contains the incident |
| 5-15 min | Security team engaged |
| 15-30 min | Management notified |
| 1 hour | Customer notification if data affected |
| 24 hours | Compliance/legal notification |
