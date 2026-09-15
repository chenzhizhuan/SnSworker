---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '6b696636-7dd0-43ed-99b9-0490db0e4565'
  PropagateID: '6b696636-7dd0-43ed-99b9-0490db0e4565'
  ReservedCode1: 'ab352154-d87f-4e01-aa37-07a7a956047c'
  ReservedCode2: 'ab352154-d87f-4e01-aa37-07a7a956047c'
---

# Technology Selection Framework

Structured decision framework. **NO CHOICE WITHOUT EXPLICIT TRADE-OFF ANALYSIS.**

---

## Phase 1: Requirements First

### Non-Functional (Quantify!)

| Dimension | Good Answer |
|-----------|-------------|
| Scale | "1K concurrent, 500 RPS peak" |
| Latency | "< 200ms API, < 2s reports" |
| Availability | "99.9% (8.7h downtime/year)" |
| Data volume | "100GB/year, 10M rows" |
| Consistency | "Strong for payments, eventual for feeds" |
| Compliance | "GDPR data residency EU, SOC 2 Type II" |

### Team Constraints

Size, existing expertise, hiring market, timeline, budget.

---

## Phase 2: Evaluation Matrix

Score 1-5 on weighted criteria:

| Criterion | Weight |
|-----------|--------|
| Meets functional requirements | 5× |
| Meets non-functional requirements | 5× |
| Team expertise / learning curve | 4× |
| Ecosystem maturity | 3× |
| Community & long-term viability | 3× |
| Operational complexity | 3× |
| Hiring pool | 2× |
| Cost (license + infra + training) | 2× |

**Rules:** Score 1 on 5× criterion → disqualified. Within 10% → choose what team knows. Within 15% → time-boxed PoC (2-5 days).

---

## Phase 3: Decision Trees

### Backend Language / Framework

```
REST/GraphQL API, rapid development
├─ Team knows TypeScript → NestJS (enterprise) / Fastify (lightweight) / Next.js (full-stack)
├─ Team knows Python → FastAPI (async) / Django (admin-heavy) / Flask (lightweight)
└─ Team knows Java/Kotlin → Spring Boot (enterprise) / Quarkus (lightweight)

High concurrency, systems-level
├─ Microservices, network → Go
├─ Extreme perf, safety → Rust (Axum/Actix)
└─ Fault tolerance → Elixir (Phoenix)

Real-time → Node.js Socket.io / Elixir Phoenix / Go
ML / data → Python (FastAPI + ML libs)
```

### Database

```
Structured, relational, ACID → PostgreSQL ← DEFAULT CHOICE
  ├─ Read-heavy, MySQL ecosystem → MySQL / MariaDB
  └─ Embedded / serverless → SQLite / Turso / D1

Semi-structured → MongoDB / DynamoDB / Elasticsearch
Key-value / cache → Redis / Valkey
Time-series → TimescaleDB / ClickHouse
Graph → Neo4j / Apache AGE
Vector (AI) → pgvector / Pinecone / Qdrant
```

### Caching

| Pattern | When |
|---------|------|
| Application (Redis) | Sessions, frequent reads, rate limiting |
| HTTP (CDN) | Static assets, public API responses |
| Query (materialized views) | Complex aggregations |
| In-process (LRU) | Config, small lookup tables |

### Message Queue

| Pattern | When |
|---------|------|
| Task queue (BullMQ/Celery/SQS) | Email, exports, payments |
| Event streaming (Kafka/Redpanda) | Event sourcing, real-time pipelines |
| Lightweight pub/sub (Redis Streams/NATS) | Simple notifications |

### Hosting

| Model | When |
|-------|------|
| Serverless (Vercel/Workers/Lambda) | Variable traffic, pay-per-use |
| Container (Cloud Run/Railway) | Steady traffic, simple ops |
| Kubernetes (EKS/GKE) | 10+ services, K8s expertise |
| VPS (DO/Hetzner/EC2) | Predictable, cost-sensitive |

---

## Phase 4: ADR Template

```markdown
# ADR-{NNN}: {Title}
## Status: Proposed | Accepted | Deprecated
## Context: What problem? What forces?
## Decision: What chose and why?
## Evaluation: | Criterion | Weight | Chosen | Runner-up |
## Consequences: Positive / Negative / Risks
## Alternatives Rejected: Option B: because...
```

---

## Common Stack Templates

### Startup / MVP (Speed)

TypeScript + Next.js/NestJS + PostgreSQL (Supabase/Neon) + Clerk/Better Auth + Upstash Redis + Vercel/Railway

### SaaS / Business (Balance)

TypeScript/Python + NestJS/FastAPI + PostgreSQL + BullMQ/Celery + OAuth JWT + AWS ECS/Cloud Run + Datadog/Grafana

### High-Performance (Scale)

Go/Rust + PostgreSQL + Redis + ClickHouse + Kafka + Kubernetes + Prometheus + Grafana + Jaeger

### AI / ML Application

Python FastAPI + Next.js + PostgreSQL + pgvector + Celery + Redis + Modal/AWS GPU

---

## Anti-Patterns

| # | Don't | Do Instead |
|---|-------|-----------|
| 1 | "X is trending on HN" | Evaluate against YOUR requirements |
| 2 | Resume-Driven Development | Choose what team can maintain |
| 3 | "Must scale to 1M users" day 1 | Build for 10× current need |
| 4 | Evaluate for weeks | Time-box 3-5 days, then decide |
| 5 | No decision documentation | Write ADR for every major choice |
| 6 | Ignore operational cost | Include deploy/monitor/debug cost |
| 7 | "We'll rewrite later" | Assume you won't. Choose carefully. |
| 8 | Microservices by default | Start monolith, extract when needed |

---

## Common Issues

- **"Team can't agree"** — Time-box 3 days. Fill matrix. Within 10% → pick majority knows. Document in ADR.
- **"Picked X but doesn't fit"** — < 2 weeks invested → switch. > 2 weeks → document pain, plan phased migration.
- **"Do we need microservices?"** — Almost certainly no. Start monolith. Extract when: different scaling/team/cadence.

> AI生成