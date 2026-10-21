---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'f7f2d2ed-8d0a-4f8c-ad7f-e3506c798cba'
  PropagateID: 'f7f2d2ed-8d0a-4f8c-ad7f-e3506c798cba'
  ReservedCode1: '8d190849-8342-4ad8-8072-cdf4afaff409'
  ReservedCode2: '8d190849-8342-4ad8-8072-cdf4afaff409'
---

# Release & Acceptance Checklist

6-gate release checklist. **NO RELEASE WITHOUT ALL GATES PASSING.**

```
Feature Complete → Gate 1: Functional → Gate 2: Non-Functional → Gate 3: Security
→ Gate 4: Deployment Readiness → Gate 5: Release Execution → Gate 6: Post-Release
```

---

## Gate 1: Functional Acceptance

- [ ] All acceptance criteria have passing tests
- [ ] Happy path works end-to-end
- [ ] Edge cases (empty, max, Unicode) and error cases (invalid, not found, timeout) tested
- [ ] Data integrity verified (CRUD cycle)
- [ ] Backward compatibility confirmed
- [ ] API contract matches OpenAPI spec
- [ ] Idempotency verified

---

## Gate 2: Non-Functional Acceptance

**Performance:**
- [ ] Response time within budget (p95 < ___ms) — measured, not assumed
- [ ] No N+1 queries (checked with query logging)
- [ ] New queries use indexes (`EXPLAIN ANALYZE`)
- [ ] Caching effective (hit rate > 80%)

**Reliability:**
- [ ] Graceful degradation when dependencies fail
- [ ] Retry logic works for transient failures
- [ ] All external calls have timeouts
- [ ] Health check endpoints verified

**Observability:**
- [ ] Structured logging with request ID
- [ ] Metrics exposed (count, latency, error rate)
- [ ] Alerts configured

---

## Gate 3: Security Review

- [ ] All input validated server-side
- [ ] SQL injection prevented (parameterized queries)
- [ ] XSS prevented (output encoding)
- [ ] File upload validated (type, size, name sanitized)
- [ ] Rate limiting on sensitive endpoints
- [ ] Users can only access their own resources
- [ ] Tokens expire (short-lived access + refresh)
- [ ] Passwords hashed (bcrypt/argon2)
- [ ] Sensitive data not logged; secrets in env vars
- [ ] No known vulnerabilities (`npm audit` / `pip audit`)

---

## Gate 4: Deployment Readiness

**Code:**
- [ ] All tests pass in CI; linter clean; code reviewed
- [ ] No unresolved TODO/FIXME/HACK

**Database:**
- [ ] Migration tested on staging with production-like data
- [ ] Down migration works; migration is non-destructive
- [ ] Backfill plan documented

**Configuration:**
- [ ] New env vars documented in `.env.example`
- [ ] Env vars set in staging AND production

**Rollback Plan Template:**
```markdown
## Rollback Plan: [Feature]
When: Error rate > 1% sustained 5 min / p99 > 3000ms / critical function broken
Steps:
1. Revert deploy: [command]
2. Rollback migration: [command]
3. Invalidate cache: [command]
4. Verify: [steps]
Time: [X minutes]
```

---

## Gate 5: Release Execution

```
1. ANNOUNCE in release channel
2. DATABASE — Apply migration, verify, check integrity
3. DEPLOY — Canary (10% → monitor 5 min → 50% → 100%). STOP if NOT OK.
4. SMOKE TEST — Health check 200, login works, core operation works
5. ANNOUNCE complete. Monitor 30 min.
```

| Metric | Canary OK | STOP | ROLLBACK |
|--------|-----------|------|----------|
| Error rate | < 0.1% | 0.5% | > 1% |
| p95 latency | < 500ms | 700ms | > 1000ms |

---

## Gate 6: Post-Release Validation

**Immediate (0-30 min):** Health checks green. Error rate normal. Latency normal. Core journey tested. Logs clean. Alerts silent.

**Short-term (1-24h):** No complaints. Business metrics stable. Memory/CPU stable. Queue backlogs clear.

---

## Release Readiness Score

Score each gate 0-2 (0=not checked, 1=partial, 2=fully verified with evidence):

| Gate | Score |
|------|-------|
| 1. Functional | /2 |
| 2. Non-Functional | /2 |
| 3. Security | /2 |
| 4. Deployment Readiness | /2 |
| 5. Release Execution | /2 |
| 6. Post-Release | /2 |
| **Total** | **/12** |

12 → Ship it. 10-11 → Ship with documented exceptions. < 10 → Do NOT release.

---

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Small change" | Small changes cause outages daily |
| "Tested locally" | Local ≠ production |
| "Fix it if it breaks" | You'll fix it at 3 AM |
| "Deadline today" | Broken code costs more than late code |
| "CI passed" | CI doesn't check everything |

> AI生成