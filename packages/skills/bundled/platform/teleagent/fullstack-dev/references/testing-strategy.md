---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '6fab4484-67b2-4cb0-888c-5f0e49a26490'
  PropagateID: '6fab4484-67b2-4cb0-888c-5f0e49a26490'
  ReservedCode1: '15f885bd-4aed-451d-b05a-28be976a0ff5'
  ReservedCode2: '15f885bd-4aed-451d-b05a-28be976a0ff5'
---

# Backend Testing Strategy

Comprehensive testing guide covering the full pyramid: unit, integration, contract, and performance.

## Quick Start Checklist

- [ ] Test runner configured (Jest/Vitest, Pytest)
- [ ] Test database ready (Docker or in-memory)
- [ ] Database isolation per test (transaction rollback or truncation)
- [ ] Test factories for common entities
- [ ] Auth helper to generate tokens
- [ ] CI pipeline with real database service
- [ ] Coverage threshold enforced (≥ 80%)

---

## The Testing Pyramid

```
     ╱╲        E2E (few, slow)
    ╱  ╲
   ╱────╲       Integration (moderate) — API + DB + mocked externals
  ╱      ╲
 ╱────────╲      Unit (many, fast) — pure business logic
╱__________╲
```

| Level | What | Speed | Count |
|-------|------|-------|-------|
| Unit | Pure functions, business logic, no I/O | < 10ms | 70%+ |
| Integration | API routes + real DB + mocked externals | 50-500ms | ~20% |
| E2E | Full user flow across services | 1-30s | ~10% |
| Contract | API compatibility between services | < 100ms | Per boundary |
| Performance | Load, stress, soak | Minutes | Per critical path |

---

## 1. API Integration Testing

### What to Test for Every Endpoint

| Aspect | Tests |
|--------|-------|
| Happy path | Correct input → expected response + DB state |
| Auth | No token → 401, bad → 401, expired → 401 |
| Authorization | Wrong role → 403, not owner → 403 |
| Validation | Missing fields → 422, bad types → 422 |
| Not found | Invalid ID → 404 |
| Conflict | Duplicate → 409 |
| Idempotency | Same request twice → same result |
| Error format | All errors match RFC 9457 |

### TypeScript (Jest + Supertest)

```typescript
describe('POST /api/orders', () => {
  let token: string;
  beforeAll(async () => {
    await resetDatabase();
    const user = await createTestUser({ role: 'customer' });
    token = await getAuthToken(user);
  });

  it('creates order → 201 + correct DB state', async () => {
    const res = await request(app).post('/api/orders')
      .set('Authorization', `Bearer ${token}`)
      .send({ items: [{ productId: product.id, quantity: 2 }] });
    expect(res.status).toBe(201);
    expect(res.body.data.total).toBe(59.98);
  });

  it('rejects without auth → 401', async () => {
    const res = await request(app).post('/api/orders').send({ items: [] });
    expect(res.status).toBe(401);
  });
});
```

### Python (Pytest + FastAPI TestClient)

```python
def test_create_order_success(client, auth_headers, test_product):
    response = client.post("/api/orders", json={
        "items": [{"product_id": test_product.id, "quantity": 2}]
    }, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["data"]["total"] == 59.98
```

---

## 2. Database Testing

### Test Isolation

| Strategy | Speed | When |
|----------|-------|------|
| Transaction rollback | Fastest | Default for unit + integration |
| Truncation | Fast | When rollback isn't possible |
| Test containers | Slow startup | CI pipeline, full integration |

**Transaction rollback (recommended):**
```typescript
let tx: Transaction;
beforeEach(async () => { tx = await db.beginTransaction(); });
afterEach(async () => { await tx.rollback(); });
```

**Docker test containers (CI):**
```yaml
services:
  test-db:
    image: postgres:16-alpine
    tmpfs: /var/lib/postgresql/data  # RAM disk for speed
    environment:
      POSTGRES_DB: myapp_test
```

### Test Factories (Not Raw SQL)

```typescript
import { faker } from '@faker-js/faker';

export function buildUser(overrides: Partial<User> = {}): CreateUserDTO {
  return { email: faker.internet.email(), firstName: faker.person.firstName(), role: 'customer', ...overrides };
}
export async function createUser(overrides = {}) {
  return db.user.create({ data: buildUser(overrides) });
}
```

---

## 3. External Service Testing

### HTTP-Level Mocking (Not Function Mocking)

```typescript
import nock from 'nock';

it('processes payment successfully', async () => {
  nock('https://api.stripe.com').post('/v1/charges')
    .reply(200, { id: 'ch_123', status: 'succeeded' });
  const result = await paymentService.charge({ amount: 50.00, currency: 'usd' });
  expect(result.status).toBe('succeeded');
});

it('handles payment timeout', async () => {
  nock('https://api.stripe.com').post('/v1/charges').delay(10000).reply(200);
  await expect(paymentService.charge({ amount: 50, currency: 'usd' }))
    .rejects.toThrow('timeout');
});
```

---

## 4. Contract Testing (Pact)

```typescript
// Consumer
await pact.addInteraction()
  .given('user usr_123 exists')
  .uponReceiving('GET /users/usr_123')
  .withRequest('GET', '/api/users/usr_123')
  .willRespondWith(200, (b) => {
    b.jsonBody({ data: { id: MatchersV3.string(), email: MatchersV3.email() } });
  });

// Provider verifies in CI
await new Verifier({
  providerBaseUrl: 'http://localhost:3001',
  pactBrokerUrl: process.env.PACT_BROKER_URL,
  provider: 'UserService',
}).verifyProvider();
```

---

## 5. Performance Testing (k6)

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 20 },
    { duration: '1m', target: 100 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const res = http.get(`${__ENV.BASE_URL}/api/orders`);
  check(res, { 'status 200': (r) => r.status === 200 });
  sleep(1);
}
```

| Metric | Target |
|--------|--------|
| p95 response | < 500ms |
| p99 response | < 1000ms |
| Error rate | < 0.1% |

---

## Test File Organization

```
tests/
  unit/          # Pure logic, mocked dependencies
  integration/   # API + real DB
  contracts/     # Consumer-driven contracts
  performance/   # Load tests
  fixtures/      # factories/, seeds/
  helpers/       # setup, auth, db cleanup
```

---

## Anti-Patterns

| # | Don't | Do Instead |
|---|-------|-----------|
| 1 | Test only happy paths | Test errors, auth, validation, edges |
| 2 | Mock everything (no real DB) | Use test containers or test DB |
| 3 | Tests depend on order | Each test: own setup + teardown |
| 4 | Hardcode test data | Use factories (faker + overrides) |
| 5 | Test implementation details | Test behavior: input → output |
| 6 | Share mutable state | Isolate per test (rollback) |
| 7 | No performance test before release | Load test every major release |

---

## Common Issues

- **"Tests pass alone but fail together"** — Shared DB state. Use `beforeEach` truncate or transaction rollback.
- **"Jest did not exit after test run"** — Unclosed connections. Add `afterAll(async () => { await db.destroy(); await server.close(); })`.
- **"Integration tests slow in CI"** — Use `tmpfs` for PostgreSQL (RAM disk). Run migrations once in `beforeAll`, truncate in `beforeEach`. Parallelize with `--maxWorkers`.

> AI生成