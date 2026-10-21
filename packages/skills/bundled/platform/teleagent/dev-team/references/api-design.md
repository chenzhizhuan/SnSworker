---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'f7f4a3e5-d023-463d-af0b-504fcc24ba4e'
  PropagateID: 'f7f4a3e5-d023-463d-af0b-504fcc24ba4e'
  ReservedCode1: '94f1df96-b923-4bb9-a721-7b25be4ec1af'
  ReservedCode2: '94f1df96-b923-4bb9-a721-7b25be4ec1af'
---

# API Design Guidelines

Framework-agnostic API design guide. Covers REST, GraphQL, and gRPC.

## Quick Start Checklist

- [ ] Resource named as **plural noun** (`/orders`, not `/getOrders`)
- [ ] URL **kebab-case**, body fields **camelCase**
- [ ] Correct **HTTP method** (GET=read, POST=create, PUT=replace, PATCH=partial, DELETE=remove)
- [ ] Correct **status code** (201 Created, 422 Validation, 404 Not Found)
- [ ] Error response follows **RFC 9457** envelope
- [ ] **Pagination** on all list endpoints (default 20, max 100)
- [ ] **Authentication** via Authorization header (not query param)
- [ ] **Request ID** in response header (`X-Request-Id`)

---

## 1. Resource Modeling

```
✅ /users                         — plural noun
✅ /users/{id}/orders              — 1 level nesting
✅ /reviews?orderId={oid}          — flatten deep nesting with query params
❌ /getUsers                       — verb in URL
❌ /users/{uid}/orders/{oid}/items/{iid}/reviews  — 3+ levels deep
```

Max nesting: **2 levels**. Beyond that, promote to top-level resource with filters.

Resources map to **domain concepts**, not database tables: `/checkout-sessions` (domain) not `/tbl_order_header` (DB leak).

---

## 2. HTTP Methods & Status Codes

| Method | Semantics | Idempotent | Request Body |
|--------|-----------|-----------|-------------|
| GET | Read | Yes | Never |
| POST | Create / Action | No | Always |
| PUT | Full replace | Yes | Always |
| PATCH | Partial update | No* | Always |
| DELETE | Remove | Yes | Rarely |

**Success:** 200 OK, 201 Created (+ `Location` header), 202 Accepted (async), 204 No Content (DELETE)

**Client Errors:** 400 (malformed), 401 (no auth), 403 (no permission), 404 (not found / hide 403), 409 (conflict), 422 (validation), 429 (rate limit + `Retry-After`)

**Server Errors:** 500 (unexpected), 502 (upstream fail), 503 (overloaded), 504 (timeout)

---

## 3. Error Handling (RFC 9457)

```json
{
  "type": "https://api.example.com/errors/insufficient-funds",
  "title": "Insufficient Funds",
  "status": 422,
  "detail": "Account balance $10.00 is less than withdrawal $50.00.",
  "instance": "/transactions/txn_abc123",
  "request_id": "req_7f3a8b2c",
  "errors": [{ "field": "amount", "message": "Exceeds balance", "code": "INSUFFICIENT_BALANCE" }]
}
```

```typescript
// Express middleware
app.use((err, req, res, next) => {
  if (err instanceof AppError) {
    return res.status(err.status).json({
      type: `https://api.example.com/errors/${err.code}`,
      title: err.title, status: err.status, detail: err.detail, request_id: req.id,
    });
  }
  res.status(500).json({ title: 'Internal Error', status: 500, request_id: req.id });
});
```

**Rules**: Return RFC 9457 envelope for ALL errors. Include request_id. Per-field validation in `errors` array. Never expose stack traces. Never return 200 for errors.

---

## 4. Authentication & Authorization

```
✅ Authorization: Bearer eyJhbGci...      (header)
❌ GET /users?token=eyJhbGci...            (URL — appears in logs)

✅ 401 → "Who are you?"  (missing/invalid credentials)
✅ 403 → "You can't do this"  (authenticated, no permission)
✅ 404 → Hide resource existence  (use instead of 403 when needed)
```

**Rate Limit Headers (always include):**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1625097600
Retry-After: 30
```

---

## 5. Pagination & Filtering

| Strategy | When | Pros | Cons |
|----------|------|------|------|
| **Cursor** (preferred) | Large/dynamic datasets | Consistent, no skips | Can't jump to page N |
| **Offset** | Small/stable datasets, admin UIs | Simple, page jumps | Drift on insert/delete |

**Cursor response:** `{ "data": [...], "pagination": { "next_cursor": "eyJpZCI6MTIwfQ", "has_more": true } }`

**Offset response:** `{ "data": [...], "pagination": { "page": 3, "per_page": 20, "total": 256 } }`

Always enforce: default 20 items, max 100.

**Standard filter patterns:**
```
GET /orders?status=shipped&created_after=2025-01-01&sort=-created_at&fields=id,status
```
Exact match, range (`?price_gte=10&price_lte=100`), date range, sort (`-` prefix for desc), sparse fields, search (`?q=term`).

---

## 6. Versioning

| Strategy | Format | Best For |
|----------|--------|----------|
| **URL path** (recommended) | `/v1/users` | Public APIs |
| **Header** | `Api-Version: 2` | Internal APIs |
| **Query param** | `?version=2` | Legacy (avoid) |

Non-breaking: new optional fields/endpoints/params. Breaking: remove/rename fields, change types, stricter validation.

**Deprecation headers:**
```
Sunset: Sat, 01 Mar 2026 00:00:00 GMT
Deprecation: true
Link: <https://api.example.com/v2/users>; rel="successor-version"
```

---

## 7. Request / Response Design

**Consistent envelope:**
```json
{ "data": { "id": "ord_123", "status": "pending" }, "meta": { "request_id": "req_abc", "timestamp": "2025-06-15T10:30:00Z" } }
```

| Rule | Correct |
|------|---------|
| Timestamps | ISO 8601 `"2025-06-15T10:30:00Z"` |
| Public IDs | UUID `"550e8400-..."` |
| Null vs absent (PATCH) | `{ "nickname": null }` = clear field; absent = don't change |

---

## 8. API Style Decision Tree

```
Browser + mobile, flexible queries → GraphQL (DataLoader, depth ≤7, Relay pagination)
Standard CRUD, public consumers → REST (this guide)
Service-to-service, high throughput → gRPC (Protobuf, streaming)
Same team, TypeScript both sides → tRPC (shared types, no codegen)
Real-time bidirectional → WebSocket / SSE
```

---

## Anti-Patterns

| # | Don't | Do Instead |
|---|-------|-----------|
| 1 | Verbs in URLs (`/getUser`) | HTTP methods + noun resources |
| 2 | Return 200 for errors | Correct 4xx/5xx status codes |
| 3 | Expose database IDs | UUIDs for public identifiers |
| 4 | No pagination on lists | Always paginate (default 20) |
| 5 | Token in URL query | Authorization header |
| 6 | Deep nesting (3+ levels) | Flatten with query params |
| 7 | Break changes without version | Maintain compatibility or version |

---

## Common Issues

- **"Should this be a new resource or sub-resource?"** — If child makes sense on its own, promote it (`/reviews?orderId=123`). If only in parent context, nest (max 2 levels).
- **"PUT or PATCH?"** — PUT = complete resource (missing → null). PATCH = only changed fields. When unsure → PATCH (safer).
- **"400 or 422?"** — 400 = can't parse at all (malformed JSON). 422 = parsed OK but validation fails (invalid email).

> AI生成