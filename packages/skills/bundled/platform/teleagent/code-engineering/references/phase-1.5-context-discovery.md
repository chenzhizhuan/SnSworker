---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '25e8a816-dd69-4dea-aced-06c7f838c398'
  PropagateID: '25e8a816-dd69-4dea-aced-06c7f838c398'
  ReservedCode1: 'b11b5f57-1139-4162-9699-8805318b96fa'
  ReservedCode2: 'b11b5f57-1139-4162-9699-8805318b96fa'
---

# Phase 1.5: Context Discovery — Detailed Protocol

> **Phase**: 1.5 (Context Discovery — AWARENESS)
> **Risk Level Activation**: T1: Standard, T2: Full (+Contract Diff), T0: Skip
> **Source**: Extracted from SKILL.md v2.1

---

After decomposition but BEFORE any coding, understand the project context and blast radius of your changes. **This phase prevents blind modifications that break unrelated code.**

### Project Structure Scan
1. Read the project directory tree (top 2 levels minimum)
2. Identify the architecture pattern (monolith/MVC/API+SPA/microservice/etc.)
3. Map key entry points: main files, config files, routing files, DB schemas
4. **敏感文件审查**：检查 `.gitignore` 是否存在并排除敏感信息文件（`*_config.json`、`*.env`、`data/cache/` 及任何含鉴权数据的文件）。如缺失或不完整，作为本任务的安全缺陷标记。

### Impact Analysis (for MODIFICATION tasks, not new projects)
When the task involves modifying existing code:

1. **Locate the modification target**: Find the file(s) and function(s) to change
2. **Trace callers**: Use `grep` to find all files/functions that reference the target
3. **Build the impact map**:
   ```
   Target: api.get_stock_detail() return format change
   ├── Caller 1: frontend/main.js renderStockCard() — must update field names
   ├── Caller 2: scripts/export.py export_csv() — must update columns
   └── Caller 3: tests/test_api.py — must update assertions
   ```
4. **List affected files** with required change type: `[MODIFY]` / `[ADD]` / `[DELETE]`
5. **Add affected-file steps to TodoWrite** — every impacted file needs its own step

### Multi-File Coordination Protocol
When changes touch >= 2 files:

1. **Draw the modification propagation graph**: A→B→C (A's change forces B's change, etc.)
2. **Execute in topological order**: Change the deepest dependency first, then its consumers
3. **Interface contract enforcement**: When changing an API/contract/function signature, ALL parties must be updated in the same batch:
   - Definition side + ALL call sites
   - Type annotations / docstrings
   - Tests that verify the contract
4. **Atomic batch**: All related changes must be committed/applied together — never leave a half-updated interface

### Context Scope Decision
| Scenario | Context Depth | Example |
|----------|--------------|---------|
| New file, no dependencies | Shallow — just check naming conventions | Adding a new utility script |
| Modify existing function signature | Medium — trace direct callers | Changing `get_price(stock)` to `get_price(stock, date)` |
| Modify shared data model / API contract | Deep — trace full propagation chain | Changing stock data JSON format |
| Refactor core module | Full — read entire module + all imports | Replacing SQLite with PostgreSQL |

### Interface Contract Diff (for SIGNATURE CHANGES)

When Phase 1.5 impact analysis identifies a modification to an existing function/class signature, perform a structured **before/after contract comparison**:

1. **Record the old signature**: Parameter names, types, return value structure
2. **Record the new signature**: What changed — added/removed parameters, return type changes, default value changes
3. **Diff and classify the change**:
   | Change Type | Risk Level | Examples |
   |------------|-----------|---------|
   | Added parameter with default | Low | `def f(x)` → `def f(x, y=None)` |
   | Added parameter without default | High | `def f(x)` → `def f(x, y)` — ALL callers must update |
   | Removed parameter | Critical | `def f(x, y)` → `def f(x)` — ALL callers passing it will break |
   | Return type changed | High | `returns str` → `returns dict` — ALL consumers of return value must update |
   | Return structure changed | High | `{"price": 10}` → `{"price": 10, "currency": "USD"}` — consumers may break |
4. **Trace ALL call sites**: `grep` for every reference to the modified function. For each call site:
   - If High/Critical change: verify the call site passes/uses the new signature correctly
   - If not yet adapted: create a TodoWrite step for it
5. **Atomic batch rule**: All call-site adaptations MUST be applied in the same execution batch as the signature change — never leave a half-updated interface

**Output**: A contract diff report added to the impact map from Phase 1.5, e.g.:
```
Contract Diff: run_predictions()
  OLD: (stock_code, kline_data, fusion_result)
  NEW: (stock_code, kline_data, fusion_result, emotion_cycle, limit_result)
  Change: 2 added params without defaults → HIGH RISK
  Call sites:
    ✓ daily_signal.py:1520 — already passes new params
    ✗ daily_signal.py:5325 — MISSING emotion_cycle, limit_result → needs adaptation step
    ✗ backtest_engine.py:89 — MISSING emotion_cycle → needs adaptation step
```