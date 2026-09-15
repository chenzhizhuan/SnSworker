
# Phase 3.5: Error Resolution & Systematic Debugging — Detailed Protocol

> **Phase**: 3.5 (Error Resolution & Systematic Debugging)
> **Risk Level Activation**: T0: Fast Track only | T1: Fast+Systematic A-C | T2: Full A-D+defense-in-depth
> **Source**: Extracted from SKILL.md v2.1

When code execution produces errors during Phase 3 or Phase 4 verification, follow this structured resolution process. **Never silently skip errors or assume they'll resolve themselves.**

### Step 1: Error Classification — Fast Track vs Systematic

First, classify the error to determine which resolution path to take:

| Error Type | Pattern | Resolution Path | Max Retries |
|-----------|---------|-----------------|-------------|
| **Syntax** | `SyntaxError`, `IndentationError`, parse failures | **Fast Track**: Read error line + context → fix directly → retry | 2 |
| **Import/Module** | `ModuleNotFoundError`, `ImportError` | **Fast Track**: Install missing package or fix import path → retry | 2 |
| **Encoding** | `UnicodeDecodeError`, `GBK codec error` | **Fast Track**: Switch to explicit UTF-8 encoding → retry | 1 |
| **Runtime** | `TypeError`, `KeyError`, `AttributeError`, `ZeroDivisionError` | **Systematic Debug** (Phase A-D below) | 3 |
| **Logic** | Wrong output, unexpected behavior, assertion failure | **Systematic Debug** (Phase A-D below) | 3 |
| **Environment** | Port occupied, file not found, permission denied | **Fast Track**: Kill zombie process / create dir / fix path → retry | 2 |
| **Timeout/Network** | API timeout, connection refused | **Fast Track**: Check service status → restart if needed → add retry logic | 2 |

### Step 2: Fast Track Resolution (for Syntax / Import / Encoding / Environment / Network)

```
1. Capture error output (stderr + stdout)
2. Read the error location + 5 lines of surrounding context
3. Apply the targeted fix (surgical edit on the specific line)
4. Re-run the failing verification command
5. If pass → continue; if fail with SAME error → increment retry counter
6. If retry counter exceeds max → escalate to Systematic Debug
```

### Step 3: Systematic Debug (for Runtime / Logic errors)

Runtime and logic errors rarely have single-line fixes. They indicate a misunderstanding of data flow, state, or assumptions. Use the four-phase systematic debugging process below.

#### Phase A: Root Cause Investigation (HARD GATE — must complete before proposing any fix)

> **Reference**: `references/root-cause-tracing.md` — full methodology with worked examples.

1. **Read the complete error message and stack trace** — do not skim. Note every frame in the traceback, not just the last one.
2. **Stabilize reproduction** — find the minimal sequence of actions that reliably triggers the error. If you can't reproduce it, you can't verify the fix.
3. **Check recent changes** — what was modified since the last known-working state? `git diff` or file modification times. The bug was likely introduced by a recent change.
4. **Root cause tracing** — walk backward along the call chain from the crash site:
   - At each frame, ask: "What value did this function receive? Where did it come from?"
   - Continue tracing until you find the **original trigger** — the first point where something went wrong.
   - Use instrumentation logging if the error depends on runtime state (see root-cause-tracing.md "Adding Stack Traces for Investigation").
5. **HARD GATE — Can you answer this question?**: "Where is the original trigger point, and what exact condition caused the value to become wrong?"
   - **Yes** → Proceed to Phase B
   - **No** → Do NOT propose a fix. Continue investigating. A fix without root cause understanding is a guess.

#### Phase B: Pattern Analysis

1. **Find similar code that works correctly** — is there another function/module that does something similar without the error?
2. **Compare the working code with the broken code** — what's different? The difference is likely the bug or its close relative.
3. **Check for similar past fixes** — scan `daily-log/` or `.learnings/` for similar error patterns that were resolved before.

#### Phase C: Hypothesis Verification

1. **Form a single hypothesis** — "I believe the root cause is X because Y." One hypothesis at a time.
2. **Design the minimal change** that tests ONLY this hypothesis — do not bundle multiple fixes.
3. **Verify the hypothesis** — apply the minimal change and run the reproduction.
   - Hypothesis confirmed (error gone) → proceed to Phase D
   - Hypothesis rejected (error persists) → revert the change, form a new hypothesis
4. **NO simultaneous changes** — never modify multiple things at once during debugging. If you change two things and the error disappears, you don't know which fix worked (or if both were needed).

#### Phase D: Implementation & Defense-in-Depth

> **Reference**: `references/defense-in-depth.md` — full four-layer validation methodology.

1. **Write a failing test first** (TDD path — see Phase 3 TDD Optional Path) that captures the bug. Confirm it fails for the right reason.
2. **Apply the root-cause fix** — fix at the origin, not at the symptom site. Symptom-level fixes (try/except swallows, `if x is None` guards at the crash point) hide bugs and cause silent data corruption.
3. **Run the failing test** — confirm it now passes.
4. **Defense-in-depth** — add validation at each layer the data passes through, making the bug structurally impossible to recur:
   - **Layer 1 (Entry Point)**: Validate input at the API/function boundary
   - **Layer 2 (Business Logic)**: Validate semantic correctness for this operation
   - **Layer 3 (Environment)**: Guard against dangerous contexts (prod vs test, read vs write)
   - **Layer 4 (Debug)**: Instrument logging before dangerous operations
5. **Run full verification** — re-run the Write-Verify Loop from Phase 3.

### Escalation & Circuit Breaker

**Circuit breaker** — if ANY of these conditions are met, STOP the auto-repair loop:

1. **Same error retry count exceeded** for the error type (see Max Retries in classification table)
2. **Error cascade**: fixing error A produces a different error B, fixing B produces C, and the chain reaches 3+ distinct errors
3. **New error is worse than original**: e.g., was a warning, now a crash; was localized, now system-wide
4. **5+ total fix attempts** on the same step without convergence
5. **Phase A root cause gate failed 3+ times** — you cannot identify the original trigger after 3 investigation attempts → the problem likely exceeds current context, escalate to user
6. **3+ rejected hypotheses in Phase C** — if three single-variable hypotheses are all wrong, the mental model of the system is likely incorrect → step back, re-read the code from scratch, or escalate

When circuit breaker triggers:
1. **Rollback to last checkpoint** (Phase 2.5)
2. **Report to user** with structured context:
   ```
   [BLOCKED] Step: [step description]
   Error: [error message]
   Root cause investigation: [what was found / not found]
   Fix attempts: [N] ([list of what was tried])
   Hypotheses tested: [list of hypotheses and why they were rejected]
   Recommendation: [ask user for guidance / suggest alternative approach]
   ```
3. Wait for user input before proceeding

### Error Prevention Patterns (learn from common failures)

| Pattern | Prevention |
|---------|-----------|
| Circular import upon adding new module | Check import graph before adding cross-references |
| API contract mismatch after refactor | Phase 1.5 impact map + update all call sites in same batch |
| State leak between test cases | Verify `setUp`/`tearDown` properly resets state |
| Race condition in async code | Check shared state access patterns, add locks if needed |
| Encoding mismatch after file write | Always verify written file by reading it back |
| Silent data corruption from None propagation | Defense-in-depth Layer 1+2 validation at all boundaries |