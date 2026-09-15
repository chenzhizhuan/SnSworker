---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '9995475e-884c-44f7-acbf-e5d34a15a956'
  PropagateID: '9995475e-884c-44f7-acbf-e5d34a15a956'
  ReservedCode1: 'f9662687-d485-40bc-90fb-7805a297806d'
  ReservedCode2: 'f9662687-d485-40bc-90fb-7805a297806d'
---

# Phase 4: Post-Task Review — Detailed Protocol

> **Phase**: 4 (Post-Task Review)
> **Risk Level Activation**: T0: Light self-check | T1: Standard self-check | T2: Full (+dark path+code review in phase-4-advanced.md)
> **Source**: Extracted from SKILL.md v2.1

After completing all steps, perform a structured review. **This phase is the quality gate — nothing ships without passing it.**

For T2 tasks: Dark Path Protocol, Code Review Delegation, Receiving Review, and Feedback Triple-Write are in `references/phase-4-advanced.md`.

### Self-Check
1. **Requirement trace-back**: Re-read the original requirements list. For each requirement, verify the code actually delivers it (not just "approximately" or "basically"). Check output/report sections too — missing display items count as unmet.
2. Re-read all modified/created files end-to-end
3. Verify no leftover debug code, TODO comments, or placeholder values
4. Trace the critical path: Does input flow correctly to output?
5. Check edge cases: empty input, zero values, Unicode characters, long strings, None parameters
6. **Performance sanity check**: If task involves data processing, verify:
    - Test with realistic data volume (not just 3 rows)
    - Memory usage doesn't explode for large inputs
    - No obvious O(n^2) where O(n) suffices
    - Response time is acceptable for the use case
7. **敏感信息审查**：扫描项目中可能泄露到配置文件、缓存文件或日志中的硬编码敏感信息。重新运行 Phase 3 Write-Verify Loop 中的 `check_hardcode()` 函数，对所有配置文件（`.json`/`.yaml`/`.env`/`.toml`）与缓存目录（`data/cache/`）执行扫描。如发现：迁移到环境变量 / 加入 `.gitignore` / 写入缓存前剥离。

### Test Design Self-Check (when writing tests)
If the task involves writing unit tests, run this checklist BEFORE finishing:
1. **Expected values must be manually verified**: For each assertion, mentally execute the code path and confirm the expected value. NEVER guess or estimate.
2. **Boundary precision**: `threshold=20` → does `< 20` or `<= 20` match the requirement? Count carefully.
3. **Search/filter test data**: If testing "combined search" with keyword+price, manually check which test data items match ALL conditions — don't assume.
4. **String matching tests**: Spaces, case, special characters matter. `"蓝牙" ≠ "蓝 牙"`. Test what the function actually does, not what you think it does.
5. **File I/O encoding**: tempfile + json.dump + read back must use consistent `encoding="utf-8"` throughout.
6. **Coverage checklist**: One test per public method. Plus: empty input, invalid input, boundary value, duplicate/race condition.

### Verification Commands
Run the project's test/lint/start commands if available:
```powershell
# Python projects
python -m pytest [test_file] 2>&1
python -c "import [module]"  # quick import check

# Node.js projects
node --check [file.js]
npm test 2>&1

# Start the service and verify
```

If verification commands produce errors → **enter Phase 3.5 Error Resolution & Systematic Debugging**.

---

## Advanced Review (T2 only)

For T2 tasks requiring Dark Path Protocol, Code Review Delegation, Receiving Review, and Feedback Triple-Write with gate, see `references/phase-4-advanced.md`.

**Quick summary of advanced items**:
- **Dark Path**: Test degradation paths (field sync), branch reachability, exception paths
- **Code Review**: Dispatch fresh subagent when ≥3 files / signature change / L3 / circuit breaker
- **Triple-Write gate**: SKILL.md updates require gate check (universal + fits existing section + < 30 lines)
- **Error capture**: Trigger review-evolver on unexpected failures, user corrections, outdated knowledge, better approaches found