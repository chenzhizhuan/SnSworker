---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '9bf8f4f1-994d-487a-837c-fd672158d3b9'
  PropagateID: '9bf8f4f1-994d-487a-837c-fd672158d3b9'
  ReservedCode1: 'd43f18d6-8c40-4e46-b75c-55cf0b7f50f4'
  ReservedCode2: 'd43f18d6-8c40-4e46-b75c-55cf0b7f50f4'
---

# Auth Flow & Environment Management

JWT bearer flow, automatic token refresh, Next.js server-side auth, RBAC, CORS, and environment variable patterns.

---

## JWT Bearer Flow

```
1. Login:   Client → POST /api/auth/login { email, password }
            Server → { accessToken (15min), refreshToken (7d, httpOnly cookie) }
2. Request: Client → GET /api/orders  Authorization: Bearer <accessToken>
3. Refresh: Client → 401 → POST /api/auth/refresh (cookie auto-sent) → new accessToken → retry
4. Logout:  Client → POST /api/auth/logout → invalidate refresh token → clear cookie
```

### Frontend: Automatic Token Refresh

```typescript
async function apiWithRefresh<T>(path: string, options: RequestInit = {}): Promise<T> {
  try { return await api<T>(path, options); }
  catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      const refreshed = await api<{ accessToken: string }>('/api/auth/refresh', {
        method: 'POST', credentials: 'include',
      });
      setAuthToken(refreshed.accessToken);
      return api<T>(path, options);
    }
    throw err;
  }
}
```

---

## Next.js: Server-Side Auth (App Router)

```typescript
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('session')?.value;
  if (!token && request.nextUrl.pathname.startsWith('/dashboard'))
    return NextResponse.redirect(new URL('/login', request.url));
  return NextResponse.next();
}

// app/dashboard/page.tsx — server component
export default async function Dashboard() {
  const token = (await cookies()).get('session')?.value;
  const user = await fetch(`${process.env.API_URL}/api/me`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(r => r.json());
  return <DashboardContent user={user} />;
}
```

---

## Backend: Middleware Order

```
Request → 1.RequestID → 2.Logging → 3.CORS → 4.RateLimit → 5.BodyParse
       → 6.Auth → 7.Authz → 8.Validation → 9.Handler → 10.ErrorHandler → Response
```

## JWT Rules

- Short-lived access token (15min) + server-stored refresh
- Minimal claims: userId, roles (not entire user object)
- Rotate signing keys periodically
- Never store tokens in localStorage (XSS risk)
- Never pass tokens in URL query params

## RBAC Pattern

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

## Auth Decision Table

| Method | When | Frontend |
|--------|------|----------|
| Session | Same-domain, SSR | Django templates / htmx |
| JWT | Different domain, SPA, mobile | React, Vue, mobile apps |
| OAuth2 | Third-party login, API consumers | Any |

## Iron Rules

- Access token: short-lived (15min), in memory
- Refresh token: httpOnly cookie (XSS-safe)
- Automatic transparent refresh on 401
- Redirect to login when refresh fails
- Never trust client-side auth checks alone — server must validate

---

## Environment Variable Rules

```
✅ API base URL from env var — NEVER hardcoded
✅ Prefix client-side vars: NEXT_PUBLIC_ (Next.js) / VITE_ (Vite)
✅ Backend URL = server-only env var (for SSR, not exposed to browser)
✅ CORS: explicit origins per environment

❌ Never use localhost in production builds
❌ Never expose backend secrets with NEXT_PUBLIC_ prefix
❌ Never commit .env.local (commit .env.example)
```

## CORS Configuration

```typescript
const ALLOWED_ORIGINS = {
  development: ['http://localhost:3000', 'http://localhost:5173'],
  staging: ['https://staging.example.com'],
  production: ['https://example.com', 'https://www.example.com'],
};

app.use(cors({
  origin: ALLOWED_ORIGINS[process.env.NODE_ENV || 'development'],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
}));
```

---

## Common Issues

- **"CORS error in browser but works in Postman"** — CORS is browser-only. Backend must return `Access-Control-Allow-Origin`. For cookies: `credentials: true` both sides. Check preflight `OPTIONS`.
- **"Env var undefined in browser"** — Missing `NEXT_PUBLIC_` / `VITE_` prefix. Rebuild after adding new vars (embedded at build time).
- **"Auth works on load but breaks on navigation"** — Token in component state (lost on unmount). Use React Context, cookie, or React Query cache with `staleTime: Infinity`.

> AI生成