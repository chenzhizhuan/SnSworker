---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'f04b3204-d4e9-4898-81a9-50b718ee3279'
  PropagateID: 'f04b3204-d4e9-4898-81a9-50b718ee3279'
  ReservedCode1: '9984d13c-fc08-4481-95da-8bd475982743'
  ReservedCode2: '9984d13c-fc08-4481-95da-8bd475982743'
---

# Performance & Observability Checklist

> **Phase**: 2 (Pre-Flight Constraint Check)
> **Load when**: Task involves data processing, loops, API calls, caching, logging, or external resource management (T2: always). See task-risk-grading.md for full activation matrix.
> **Source**: Extracted from SKILL.md v2.1

### Performance & Observability Checklist (when code involves data processing, loops, or API calls)
- [ ] **N+1 queries**: No DB/API calls inside loops → batch preload or use JOIN
- [ ] **Large data handling**: Dataset > 1000 rows → use pagination, streaming, or chunked processing
- [ ] **Caching**: Repeated expensive computations or API calls → implement cache with TTL and invalidation strategy
- [ ] **缓存敏感字段剥离**：将 API 响应缓存到磁盘前，必须先剥离响应中的鉴权字段。维护一个模块级 frozenset 存储敏感字段名集合（由片段拼接构造），然后执行过滤：`cached = {k: v for k, v in response.items() if k not in _SENSITIVE_FIELDS}`。敏感数据必须在调用时单独加载，不得嵌入缓存数据。
- [ ] **Logging levels**: Use structured logging: DEBUG (dev trace) / INFO (normal flow) / WARN (degraded) / ERROR (failure). No bare `print()` in production paths.
- [ ] **Resource cleanup**: DB connections, file handles, HTTP responses → ensure `finally`/`with` block cleanup
- [ ] **Timeout on external calls**: All HTTP/DB/external calls → set explicit timeout (default 30s for API, 120s for batch)
- [ ] **Condition-based waiting (NOT arbitrary sleep)**: Never use `time.sleep()` / `setTimeout()` to wait for async results (file I/O completion, subprocess finish, API response, service startup). Use condition polling instead:
  - **Poll with timeout**: Loop checking the condition, with a max wait time and clear error on timeout
  - **Python example**: `for _ in range(max_attempts): if condition_met(): break; time.sleep(0.5)` — always with `max_attempts` bounded
  - **Node.js example**: `await waitForCondition(() => fs.existsSync(path), { timeout: 5000, interval: 100 })`
  - **Error on timeout**: If the condition is not met within the timeout → raise a descriptive error (`TimeoutError("Service did not start within 30s")`), never fail silently
  - **If fixed sleep is truly unavoidable**: Add a comment explaining WHY this exact duration is needed: `# sleep 2s: Docker container needs ~2s for port binding after `docker start`` — bare `time.sleep(2)` without justification is a code smell