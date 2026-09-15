
# Exception Strategy Checklist

> **Phase**: 2 (Pre-Flight Constraint Check)
> **Load when**: Task involves try/except blocks, external API/DB integration, or degradation path implementation (T2: always — MANDATORY for all code with try/except). See task-risk-grading.md for full activation matrix.
> **Source**: Extracted from SKILL.md v2.1

### Exception Strategy (MANDATORY for all code with try/except)

**Absolute prohibitions**:
- [ ] **No bare `except:`** — always `except Exception as e:` at minimum (bare except catches KeyboardInterrupt, SystemExit, and hides real bugs)
- [ ] **No `except ... pass`** — at minimum log the error: `except ... as e: log(f"error: {e}")`. Silent suppression is acceptable ONLY for explicitly documented "expected and ignorable" cases with a comment explaining why
- [ ] **No `except Exception:` without `as e`** — you need the exception object for logging/diagnosis

**Exception handling patterns**:
- [ ] **External call protection**: All calls to APIs / databases / external processes MUST be wrapped in try/except with: (1) specific exception type, (2) error logging, (3) degradation strategy (retry / fallback value / graceful failure)
- [ ] **Degradation completeness**: When implementing a degradation/downgrade path, ALL related fields must be updated — not just the primary computation. Common failure: downgrading a signal but forgetting to update the `action` field
- [ ] **Exception granularity**: Catch the most specific exception type possible. `except Exception` is acceptable only as a top-level safety net, never as the sole handler for a known failure mode

**Exception anti-pattern scanner** (run as part of Write-Verify Loop in Phase 3):
```python
# Patterns to flag:
#   except\s*:                    → bare except (CRITICAL)
#   except\s+\w+\s*:\s*$          → except without 'as e' (WARNING)
#   except\s+.*:\s*pass\s*$       → silent suppression (WARNING)
#   except\s+Exception\s*:\s*$    → overly broad without logging (INFO)
```