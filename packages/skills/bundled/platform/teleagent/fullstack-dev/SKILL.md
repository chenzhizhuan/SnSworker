---
name: fullstack-dev
description: |
  Full-stack backend architecture and frontend-backend integration guide.
  TRIGGER when: building a full-stack app, creating REST API with frontend, scaffolding backend service,
  building CRUD/real-time/chat apps, Express+React, Next.js API, Node.js/Python/Go backend,
  designing service layers, implementing error handling/auth/caching, hardening for production.
  DO NOT TRIGGER when: pure frontend UI, pure CSS/styling, database schema only.
name_cn: 全栈开发
description_cn: 全栈应用架构与开发指南，涵盖后端架构、前后端集成、API设计、认证、数据库访问与生产加固。
create_source: super-agent-skill-creator
---

# Full-Stack Development Practices

## Core Principles

```
1. ✅ Organize by FEATURE, not by technical layer
2. ✅ Controllers never contain business logic
3. ✅ Services never import HTTP request/response types
4. ✅ All config from env vars, validated at startup, fail fast
5. ✅ Every error is typed, logged, and returns consistent format
6. ✅ All input validated at the boundary — trust nothing from client
7. ✅ Structured JSON logging with request ID — not console.log
```

---

## Workflow

### Step 0: Gather Requirements

Clarify before scaffolding: **Stack** (language/framework), **Service type** (API-only / monolith / microservice), **Database** (SQL/NoSQL), **Integration** (REST/GraphQL/tRPC/gRPC), **Real-time** (SSE/WebSocket/polling), **Auth** (JWT/session/OAuth/third-party). Skip if already specified.

### Step 1: Architectural Decisions

State decisions before coding:

| Decision | Options | Reference |
|----------|---------|-----------|
| Project structure | Feature-first (recommended) vs layer-first | [Section 1](#1-project-structure--layering) |
| API client approach | Typed fetch / React Query / tRPC / OpenAPI codegen | [Section 5](#5-api-client-patterns) |
| Auth strategy | JWT + refresh / session / third-party | [references/auth-and-env.md](references/auth-and-env.md) |
| Real-time method | Polling / SSE / WebSocket | [Section 11](#11-real-time-patterns) |

### Step 2: Scaffold & Implement

Use checklists below. Implement following patterns in this document.

### Step 3: Test & Verify

1. **Build check**: Backend and frontend compile without errors
2. **Smoke test**: `curl http://localhost:3000/health` + key endpoints
3. **Integration check**: Frontend connects to backend (CORS, auth)
4. **Real-time check** (if applicable): Two tabs sync correctly

### Step 4: Handoff Summary

- **What was built**: Features and endpoints
- **How to run**: Exact start commands
- **What's missing / next steps**
- **Key files**: Most important files to know

---

## Quick Start — New Backend Checklist

- [ ] Feature-first project structure
- [ ] Configuration centralized, env vars validated at startup (fail fast)
- [ ] Typed error hierarchy (not generic `Error`)
- [ ] Global error handler middleware
- [ ] Structured JSON logging with request ID
- [ ] Database migrations + connection pooling
- [ ] Input validation on all endpoints (Zod / Pydantic)
- [ ] Authentication middleware
- [ ] Health check endpoints (`/health`, `/ready`)
- [ ] Graceful shutdown (SIGTERM)
- [ ] CORS configured (explicit origins, not `*`)
- [ ] Security headers (helmet)
- [ ] `.env.example` committed (no real secrets)

## Quick Start — Frontend-Backend Integration

- [ ] Typed API client (fetch wrapper / React Query / tRPC / OpenAPI)
- [ ] Base URL from environment variable
- [ ] Auth token attached automatically (interceptor / middleware)
- [ ] API errors mapped to user-facing messages
- [ ] Loading states handled (skeleton/spinner)
- [ ] Type safety across boundary (shared types / OpenAPI / tRPC)
- [ ] CORS with explicit origins
- [ ] Refresh token flow (httpOnly cookie + transparent retry on 401)

---

## 1. Project Structure & Layering

### Feature-First Organization

```
✅ Feature-first                    ❌ Layer-first
src/                                src/
  orders/                             controllers/
    order.controller.ts                 order.controller.ts
    order.service.ts                    user.controller.ts
    order.repository.ts               services/
    order.dto.ts                        order.service.ts
  users/                              repositories/
    user.controller.ts                  ...
    user.service.ts
  shared/
    database/
    middleware/
```

### Three-Layer Architecture

```
Controller (HTTP) → Service (Business Logic) → Repository (Data Access)
```

| Layer | Responsibility | Never |
|-------|---------------|-------|
| Controller | Parse request, validate, call service, format response | Business logic, DB queries |
| Service | Business rules, orchestration, transactions | HTTP types, direct DB |
| Repository | Database queries, external API calls | Business logic, HTTP types |

### Dependency Injection

```typescript
class OrderService {
  constructor(
    private readonly orderRepo: OrderRepository,
    private readonly emailService: EmailService,
  ) {}
}
```

---

## 2. Configuration & Environment

### Centralized, Typed, Fail-Fast

```typescript
const config = {
  port: parseInt(process.env.PORT || '3000', 10),
  database: { url: requiredEnv('DATABASE_URL'), poolSize: intEnv('DB_POOL_SIZE', 10) },
  auth: { jwtSecret: requiredEnv('JWT_SECRET'), expiresIn: process.env.JWT_EXPIRES_IN || '1h' },
} as const;

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing required env var: ${name}`);
  return value;
}
```

**Rules**: All config via env vars (Twelve-Factor). Validate at startup — fail fast. Type-cast at config layer. Commit `.env.example` with dummies. Never hardcode secrets or scatter `process.env` throughout code.

---

## 3. Error Handling & Resilience

### Typed Error Hierarchy

```typescript
class AppError extends Error {
  constructor(message: string, public readonly code: string, public readonly statusCode: number,
    public readonly isOperational: boolean = true) { super(message); }
}
class NotFoundError extends AppError {
  constructor(resource: string, id: string) { super(`${resource} not found: ${id}`, 'NOT_FOUND', 404); }
}
class ValidationError extends AppError {
  constructor(public readonly errors: FieldError[]) { super('Validation failed', 'VALIDATION_ERROR', 422); }
}
```

### Global Error Handler

```typescript
app.use((err, req, res, next) => {
  if (err instanceof AppError && err.isOperational) {
    return res.status(err.statusCode).json({
      title: err.code, status: err.statusCode, detail: err.message, request_id: req.id,
    });
  }
  logger.error('Unexpected error', { error: err.message, stack: err.stack, request_id: req.id });
  res.status(500).json({ title: 'Internal Error', status: 500, request_id: req.id });
});
```

**Rules**: Typed domain errors. Global handler catches everything. Operational errors → structured response. Programming errors → log + generic 500. Never catch/ignore silently. Never return stack traces.

---

## 4. Database Access Patterns

### Migrations

Schema changes via migrations, never manual SQL. Migrations must be reversible. Review SQL before production.

### N+1 Prevention

```typescript
// ❌ N+1: 1 + N queries
const orders = await db.order.findMany();
for (const o of orders) { o.items = await db.item.findMany({ where: { orderId: o.id } }); }

// ✅ Single query
const orders = await db.order.findMany({ include: { items: true } });
```

### Transactions

```typescript
await db.$transaction(async (tx) => {
  const order = await tx.order.create({ data: orderData });
  await tx.inventory.decrement({ productId, quantity });
  await tx.payment.create({ orderId: order.id, amount });
});
```

### Connection Pooling

Pool size = `(CPU cores × 2) + spindle_count` (start 10-20). Always set connection timeout. Use PgBouncer for serverless.

---

## 5. API Client Patterns

| Approach | When | Type Safety | Effort |
|----------|------|-------------|--------|
| Typed fetch wrapper | Simple apps, small teams | Manual | Low |
| React Query + fetch | React apps, server state | Manual | Medium |
| tRPC | Same team, TS both sides | Automatic | Low |
| OpenAPI generated | Public API, multi-consumer | Automatic | Medium |

### Option A: Typed Fetch Wrapper

```typescript
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';

class ApiError extends Error {
  constructor(public status: number, public body: any) { super(body?.detail || `API error ${status}`); }
}

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  if (!res.ok) throw new ApiError(res.status, await res.json().catch(() => null));
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const apiClient = {
  get: <T>(path: string) => api<T>(path),
  post: <T>(path: string, data: unknown) => api<T>(path, { method: 'POST', body: JSON.stringify(data) }),
  put: <T>(path: string, data: unknown) => api<T>(path, { method: 'PUT', body: JSON.stringify(data) }),
  delete: <T>(path: string) => api<T>(path, { method: 'DELETE' }),
};
```

### Option B: React Query (Recommended for React)

```typescript
export function useOrders() {
  return useQuery({
    queryKey: ['orders'],
    queryFn: () => apiClient.get<{ data: Order[] }>('/api/orders'),
    staleTime: 1000 * 60,
  });
}

export function useCreateOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateOrderInput) => apiClient.post<{ data: Order }>('/api/orders', data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['orders'] }),
  });
}
```

---

## 6. Authentication & Middleware

> Full reference: [references/auth-and-env.md](references/auth-and-env.md) — JWT flow, refresh, Next.js SSR, RBAC, CORS.

### Middleware Order

```
Request → RequestID → Logging → CORS → RateLimit → BodyParse → Auth → Authz → Validation → Handler → ErrorHandler → Response
```

### JWT Rules

Short-lived access token (15min) + server-stored refresh. Minimal claims: userId, roles. Rotate signing keys. Never store tokens in localStorage. Never pass tokens in URL params.

### RBAC

```typescript
function authorize(...roles: Role[]) {
  return (req, res, next) => {
    if (!req.user) throw new UnauthorizedError();
    if (!roles.some(r => req.user.roles.includes(r))) throw new ForbiddenError();
    next();
  };
}
router.delete('/users/:id', authenticate, authorize('admin'), deleteUser);
```

### Automatic Token Refresh

```typescript
async function apiWithRefresh<T>(path: string, options: RequestInit = {}): Promise<T> {
  try { return await api<T>(path, options); }
  catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      const refreshed = await api<{ accessToken: string }>('/api/auth/refresh', {
        method: 'POST', credentials: 'include',
      });
      setAuthToken(refreshed.accessToken);
      return api<T>(path, options);  // retry
    }
    throw err;
  }
}
```

---

## 7. Logging & Observability

```typescript
// ✅ Structured
logger.info('Order created', { orderId: order.id, userId: user.id, total: order.total, duration_ms: Date.now() - startTime });
// Output: {"level":"info","msg":"Order created","orderId":"ord_123",...}

// ❌ Unstructured
console.log(`Order created for user ${user.id}`);
```

| Level | When | Production? |
|-------|------|------------|
| error | Immediate attention | Always |
| warn | Unexpected but handled | Always |
| info | Normal operations, audit | Always |
| debug | Dev troubleshooting | Dev only |

**Rules**: Request ID in every log. Log at layer boundaries. Never log passwords/tokens/PII. Never use console.log in production.

---

## 8. Background Jobs

**Rules**: All jobs IDEMPOTENT. Failed → retry (max 3) → dead letter queue → alert. Workers as SEPARATE processes. Never put long-running tasks in request handlers.

```typescript
async function processPayment(data: { orderId: string }) {
  const order = await orderRepo.findById(data.orderId);
  if (order.paymentStatus === 'completed') return;  // already processed
  await paymentGateway.charge(order);
  await orderRepo.updatePaymentStatus(order.id, 'completed');
}
```

---

## 9. Caching Patterns

### Cache-Aside

```typescript
async function getUser(id: string): Promise<User> {
  const cached = await redis.get(`user:${id}`);
  if (cached) return JSON.parse(cached);
  const user = await userRepo.findById(id);
  if (!user) throw new NotFoundError('User', id);
  await redis.set(`user:${id}`, JSON.stringify(user), 'EX', 900);  // 15min TTL
  return user;
}
```

**Rules**: ALWAYS set TTL. Invalidate on write. Cache for reads only, never authoritative state.

| Data Type | Suggested TTL |
|-----------|---------------|
| User profile | 5-15 min |
| Product catalog | 1-5 min |
| Config / feature flags | 30-60 sec |

---

## 10. File Upload Patterns

| Method | File Size | Server Load | Complexity |
|--------|-----------|-------------|------------|
| Presigned URL | Any (recommended > 5MB) | None (direct to S3) | Medium |
| Multipart | < 10MB | High (through server) | Low |
| Chunked/Resumable | > 100MB | Medium | High |

### Presigned URL Flow

```
Client → GET /api/uploads/presign?filename=photo.jpg&type=image/jpeg
Server → { uploadUrl, fileKey }
Client → PUT uploadUrl (direct to S3)
Client → POST /api/photos { fileKey } (save reference)
```

```typescript
// Backend
app.get('/api/uploads/presign', authenticate, async (req, res) => {
  const { filename, type } = req.query;
  const key = `uploads/${crypto.randomUUID()}-${filename}`;
  const url = await s3.getSignedUrl('putObject', {
    Bucket: process.env.S3_BUCKET, Key: key, ContentType: type, Expires: 300,
  });
  res.json({ uploadUrl: url, fileKey: key });
});
```

---

## 11. Real-Time Patterns

| Method | Direction | Complexity | When |
|--------|-----------|------------|------|
| Polling | Client → Server | Low | Status checks, < 10 clients |
| SSE | Server → Client | Medium | Notifications, feeds, AI streaming |
| WebSocket | Bidirectional | High | Chat, collaboration, gaming |

### SSE (Server → Client)

```typescript
// Backend
app.get('/api/events', authenticate, (req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
  const unsubscribe = eventBus.subscribe(req.user.id, (event) => {
    res.write(`event: ${event.type}\ndata: ${JSON.stringify(event.payload)}\n\n`);
  });
  req.on('close', () => unsubscribe());
});

// Frontend
function useServerEvents(userId: string) {
  useEffect(() => {
    const source = new EventSource(`/api/events?userId=${userId}`);
    source.addEventListener('notification', (e) => showToast(JSON.parse(e.data).message));
    return () => source.close();
  }, [userId]);
}
```

### WebSocket (Bidirectional)

```typescript
// Backend (ws library)
wss.on('connection', (ws, req) => {
  const userId = authenticateWs(req);
  if (!userId) { ws.close(4001, 'Unauthorized'); return; }
  ws.on('message', (raw) => handleMessage(userId, JSON.parse(raw.toString())));
  ws.on('close', () => cleanupUser(userId));
  const interval = setInterval(() => ws.ping(), 30000);
  ws.on('close', () => clearInterval(interval));
});
```

---

## 12. Cross-Boundary Error Handling

```typescript
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 401: return 'Please log in to continue.';
      case 403: return "You don't have permission.";
      case 404: return "Item doesn't exist.";
      case 429: return 'Too many requests. Please wait.';
      default: return 'Something went wrong. Please try again.';
    }
  }
  if (error instanceof TypeError && error.message === 'Failed to fetch') return 'Cannot connect to server.';
  return 'An unexpected error occurred.';
}
```

**Rules**: Map every error code to human message. Field errors next to form inputs. Auto-retry 5xx (max 3), never 4xx. Redirect to login on 401 after refresh fails. Never show raw API errors. Never silently swallow.

---

## 13. Production Hardening

### Health Checks

```typescript
app.get('/health', (req, res) => res.json({ status: 'ok' }));
app.get('/ready', async (req, res) => {
  const checks = { database: await checkDb(), redis: await checkRedis() };
  const ok = Object.values(checks).every(c => c.status === 'ok');
  res.status(ok ? 200 : 503).json({ status: ok ? 'ok' : 'degraded', checks });
});
```

### Graceful Shutdown

```typescript
process.on('SIGTERM', async () => {
  logger.info('SIGTERM received');
  server.close();
  await drainConnections();
  await closeDatabase();
  process.exit(0);
});
```

### Security Checklist

CORS: explicit origins (never `*`). Security headers (helmet). Rate limiting on public endpoints. Input validation on ALL endpoints. HTTPS enforced. Never expose internal errors.

---

## Integration Decision Tree

```
Same team owns frontend + backend?
├─ YES, both TypeScript → tRPC (end-to-end type safety)
├─ YES, different languages → OpenAPI spec → generated client
├─ NO, public API → REST + OpenAPI → generated SDKs
└─ Complex data, multiple frontends → GraphQL + codegen

Real-time needed?
├─ Server → Client only → SSE (simplest, auto-reconnect)
├─ Bidirectional → WebSocket (heartbeat + reconnection)
└─ Simple polling (< 10 clients) → React Query refetchInterval
```

---

## Anti-Patterns

| # | Don't | Do Instead |
|---|-------|-----------|
| 1 | Business logic in routes/controllers | Move to service layer |
| 2 | `process.env` scattered | Centralized typed config |
| 3 | `console.log` for logging | Structured JSON logger |
| 4 | Generic `Error('oops')` | Typed error hierarchy |
| 5 | Direct DB in controllers | Repository pattern |
| 6 | No input validation | Validate at boundary (Zod/Pydantic) |
| 7 | Catching errors silently | Log + rethrow or return error |
| 8 | Hardcoded config/secrets | Environment variables |
| 9 | Store JWT in localStorage | Memory + httpOnly refresh cookie |
| 10 | Show raw API errors to users | Map to human-readable messages |

---

## Common Issues

- **"Where does this business rule go?"** — HTTP concerns → controller. Business decisions → service. Database → repository.
- **"Service too big"** — Split by sub-domain. `OrderService` → `OrderCreationService` + `OrderFulfillmentService` + `OrderQueryService`.
- **"Tests slow (hitting DB)"** — Unit tests mock repository (fast). Integration tests use test containers or transaction rollback.

---

## Reference Documents

| Need to… | Reference |
|----------|-----------|
| Auth flow (JWT, refresh, Next.js SSR, RBAC), CORS, env vars | [references/auth-and-env.md](references/auth-and-env.md) |
| Design REST/GraphQL/gRPC endpoints | [references/api-design.md](references/api-design.md) |
| Design database schema, indexes, migrations, multi-tenancy | [references/db-schema.md](references/db-schema.md) |
| Build with Django / DRF | [references/django-best-practices.md](references/django-best-practices.md) |
| Test backend (unit, integration, contract, performance) | [references/testing-strategy.md](references/testing-strategy.md) |
| Validate release (6-gate checklist) | [references/release-checklist.md](references/release-checklist.md) |
| Choose tech stack | [references/technology-selection.md](references/technology-selection.md) |
