---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '7a1dd16b-d6ea-4748-9d66-e7479d2b4061'
  PropagateID: '7a1dd16b-d6ea-4748-9d66-e7479d2b4061'
  ReservedCode1: 'ba935d2d-539a-447a-9f65-f641ebd67056'
  ReservedCode2: 'ba935d2d-539a-447a-9f65-f641ebd67056'
---

# Database Schema Design

ORM-agnostic relational database schema guide. Primarily PostgreSQL-focused.

## Core Principles

```
1. ✅ Start normalized (3NF) — denormalize only with measured evidence
2. ✅ Every table has a primary key, created_at, updated_at
3. ✅ UUID for public-facing IDs, serial for internal join keys
4. ✅ NOT NULL by default — null is a business decision
5. ✅ Index every column in WHERE, JOIN, ORDER BY
6. ✅ Foreign keys enforced in database
7. ✅ Migrations are additive — never drop/rename in production without multi-step plan
```

---

## 1. Data Modeling

### Primary Keys

| Strategy | When | Pros | Cons |
|----------|------|------|------|
| `bigserial` | Internal FK joins | Compact, fast | Enumerable, not for public IDs |
| `uuid` v4 | Public-facing resources | Non-guessable, globally unique | Larger, random I/O |
| `uuid` v7 | Public + needs ordering | Non-guessable + insert-friendly | Newer |
| `text` slug | URL-friendly | Human-readable | Must enforce uniqueness |

**Recommended:**
```sql
CREATE TABLE orders (
    id          bigserial PRIMARY KEY,
    public_id   uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);
```

### Relationships

```sql
-- One-to-Many
CREATE TABLE orders (
    id      bigserial PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- Many-to-Many (junction table)
CREATE TABLE order_items (
    id         bigserial PRIMARY KEY,
    order_id   bigint NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id bigint NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity   int NOT NULL CHECK (quantity > 0),
    UNIQUE (order_id, product_id)
);
```

### ON DELETE Behavior

| Behavior | When | Example |
|----------|------|---------|
| `CASCADE` | Child meaningless without parent | order_items when order deleted |
| `RESTRICT` | Prevent accidental deletion | products referenced by order_items |
| `SET NULL` | Preserve child, clear reference | orders.assigned_to when employee leaves |

---

## 2. Normalization vs Denormalization

Start **normalized (3NF)**:

| Form | Rule | Violation Example |
|------|------|-------------------|
| 1NF | No repeating groups | `tags = "go,python,rust"` in one column |
| 2NF | No partial dependencies | `order_items.product_name` depends on `product_id` alone |
| 3NF | No transitive dependencies | `orders.customer_city` depends on `customer_id`, not `order_id` |

**Denormalize ONLY when:**
1. Measured performance problem (EXPLAIN ANALYZE)
2. Read-heavy (read:write > 100:1)
3. Accept consistency maintenance cost (triggers, app logic, materialized views)

**Safe patterns:**
```sql
-- Materialized view
CREATE MATERIALIZED VIEW order_summary AS SELECT ...;
REFRESH MATERIALIZED VIEW CONCURRENTLY order_summary;

-- Cached aggregate column (app-maintained)
ALTER TABLE orders ADD COLUMN item_count int NOT NULL DEFAULT 0;

-- JSONB snapshot (freeze-at-write-time)
CREATE TABLE order_items (
    id              bigserial PRIMARY KEY,
    unit_price      numeric(10,2) NOT NULL,    -- frozen price
    product_snapshot jsonb NOT NULL           -- frozen product details
);
```

---

## 3. Indexing Strategy

### Index Types (PostgreSQL)

| Type | When | Example |
|------|------|---------|
| **B-Tree** (default) | Equality, range, ORDER BY | `WHERE status = 'active'` |
| **GIN** | Arrays, JSONB, full-text | `WHERE tags @> '{go}'` |
| **BRIN** | Very large tables, time-series | Sorted by timestamp |

### Decision Rules

1. Index every WHERE, JOIN, ORDER BY column
2. Composite index for multi-column WHERE (leftmost prefix rule)
3. Partial index for subsets: `WHERE status = 'pending'`
4. Covering index (`INCLUDE`) to avoid table lookup
5. Don't index low-cardinality columns alone (boolean)

### Composite Index: Column Order

```sql
-- Query: WHERE user_id = ? AND status = ? ORDER BY created_at DESC
CREATE INDEX idx_orders_user_status_created ON orders(user_id, status, created_at DESC);
```

Leftmost prefix rule: Index on `(A, B, C)` supports `(A)`, `(A, B)`, `(A, B, C)` but NOT `(B)` or `(C)`.

### Partial Index

```sql
CREATE INDEX idx_orders_pending ON orders(created_at DESC) WHERE status = 'pending';
```

### Covering Index

```sql
CREATE INDEX idx_orders_user_covering ON orders(user_id) INCLUDE (status, total);
-- Index-only: SELECT status, total FROM orders WHERE user_id = 123;
```

### When NOT to Index

Tables < 1,000 rows (seq scan faster). Write-heavy where cost > benefit. Low-cardinality alone. Duplicate/unused indexes.

---

## 4. Zero-Downtime Migrations

**Golden Rule:** NEVER make destructive changes in one step. ADD → MIGRATE DATA → REMOVE OLD (separate deploys).

**Rename column (3 deploys):**
```
Deploy 1: Add new column + backfill. App writes BOTH.
Deploy 2: Switch reads to new column. Still writes both.
Deploy 3: Drop old column. App only uses new.
```

**Add NOT NULL column (2 deploys):**
```sql
-- Deploy 1: Add nullable, backfill
ALTER TABLE orders ADD COLUMN currency text;
UPDATE orders SET currency = 'USD' WHERE currency IS NULL;
-- Deploy 2: Add constraint
ALTER TABLE orders ALTER COLUMN currency SET NOT NULL;
```

**Add index without locking:**
```sql
CREATE INDEX CONCURRENTLY idx_orders_status ON orders(status);  -- ✅ no table lock
```

**Batch backfill template:**
```sql
DO $$
DECLARE batch_size int := 10000; affected int;
BEGIN
  LOOP
    UPDATE orders SET currency = 'USD'
    WHERE id IN (SELECT id FROM orders WHERE currency IS NULL LIMIT batch_size);
    GET DIAGNOSTICS affected = ROW_COUNT;
    EXIT WHEN affected = 0;
    PERFORM pg_sleep(0.1);
  END LOOP;
END $$;
```

**Safety:** Migration < 30s. No exclusive locks. Rollback plan tested. Backfill in batches. New column nullable first.

---

## 5. Multi-Tenant Design

| Approach | Isolation | When |
|----------|-----------|------|
| Row-level (`tenant_id`) | Low | SaaS MVP, < 1,000 tenants |
| Schema-per-tenant | Medium | Regulated industries |
| Database-per-tenant | High | Enterprise, strict isolation |

### Row-Level (Most Common)

```sql
CREATE TABLE orders (
    id         bigserial PRIMARY KEY,
    tenant_id  bigint NOT NULL REFERENCES tenants(id),
    user_id    bigint NOT NULL REFERENCES users(id),
    total      numeric(10,2) NOT NULL
);
CREATE INDEX idx_orders_tenant_user ON orders(tenant_id, user_id);

-- Row-Level Security
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON orders
  USING (tenant_id = current_setting('app.tenant_id')::bigint);
```

**Rules:** tenant_id in EVERY table. First column in every composite index. App middleware enforces tenant context. Test with 2+ tenants. Never allow cross-tenant queries.

---

## 6. Common Schema Patterns

### Soft Delete
```sql
ALTER TABLE orders ADD COLUMN deleted_at timestamptz;
CREATE INDEX idx_orders_active ON orders(status, created_at DESC) WHERE deleted_at IS NULL;
```

### Audit Trail
```sql
CREATE TABLE audit_log (
    id          bigserial PRIMARY KEY,
    table_name  text NOT NULL, record_id bigint NOT NULL,
    action      text NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_data    jsonb, new_data jsonb,
    changed_by  bigint REFERENCES users(id), changed_at timestamptz NOT NULL DEFAULT now()
);
```

### Enum Columns

**Recommended:** `text + CHECK constraint` (easier to migrate than PostgreSQL enum).
```sql
ALTER TABLE orders ADD COLUMN status text NOT NULL DEFAULT 'pending'
  CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled'));
```

### Polymorphic Associations

❌ Anti-pattern: `commentable_type + commentable_id` (no FK integrity).

✅ Fix: Separate FK columns (nullable) or separate tables.

### JSONB

✅ Use for flexible/optional data (metadata, settings). Index with GIN when queried.
❌ Never use for data that should be columns. Never to avoid schema design.

---

## 7. Table Partitioning

When: Table > 100M rows AND queries filter on partition key AND old data droppable by partition.

```sql
CREATE TABLE events (...) PARTITION BY RANGE (created_at);
CREATE TABLE events_2025_01 PARTITION OF events FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

---

## Anti-Patterns

| # | Don't | Do Instead |
|---|-------|-----------|
| 1 | Premature denormalization | Start 3NF, denormalize when measured |
| 2 | Auto-increment as public API IDs | UUID for public, serial for internal |
| 3 | No FK constraints | FK enforced in database |
| 4 | Nullable by default | NOT NULL by default |
| 5 | No indexes on FK columns | Index every FK column |
| 6 | Single-step destructive migration | ADD → MIGRATE → REMOVE |
| 7 | `CREATE INDEX` without `CONCURRENTLY` | Always CONCURRENTLY on live tables |
| 8 | Polymorphic FK | Separate FK columns or tables |
| 9 | JSONB for everything | JSONB for flexible data only |
| 10 | No `created_at` / `updated_at` | Timestamp pair on every table |

> AI生成