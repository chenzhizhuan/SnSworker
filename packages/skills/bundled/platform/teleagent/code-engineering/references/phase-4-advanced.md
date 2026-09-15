---
AIGC:
  ContentProducer: ''
  ContentPropagator: ''
  Label: '1'
---

# Phase 4: Advanced Review — Dark Path & Code Review

> **Phase**: 4 (Post-Task Review — advanced)
> **Risk Level Activation**: T2 mandatory | T1 degraded (degradation path only)
> **Source**: Extracted from phase-4-review.md v3.1

---

## Dark Path Protocol

Happy-path testing alone misses the majority of integration bugs. After passing the standard Self-Check, **forcibly test three categories of dark paths**.

### 1. Degradation Path Testing

For each external dependency (API, database, MCP service, file I/O) touched by this change:
- Mock the dependency to return `None`, empty data, timeout, or error
- Verify: Does the code crash? Does it degrade gracefully? Is the degradation visible in logs?
- **Degradation completeness check**: When degradation modifies a primary computation, verify ALL related fields are updated consistently (e.g., signal, score, action, display_text). Incomplete degradation is a critical bug.

```
Degradation Test Template:
──────────────────────────
Dependency: [name]
Failure mode: [None / empty / timeout / error]
Expected behavior: [graceful degrade to X]
Field synchronization:
  [field_1] → should be [value] ✓/✗
  [field_2] → should be [value] ✓/✗
Result: [PASS/FAIL]
```

### 2. Branch Reachability Testing

For every `if/elif/else`, `match/case`, or `switch` added or modified:
- Identify all branches (including `else` and `default`)
- For each branch: construct a test input that exercises it
- Verify the branch produces the correct output
- **Special attention**: Low-frequency branches (degradation paths, error handlers) — these are most likely to harbor undetected bugs

```
Branch Coverage Template:
─────────────────────────
Condition: [expression]
Branches:
  [condition_A] → input [X] → expected [Y] → actual [Z] ✓/✗
  [condition_B] → input [X] → expected [Y] → actual [Z] ✓/✗
  [else]       → input [X] → expected [Y] → actual [Z] ✓/✗
Unreachable: [any branch that cannot be triggered = dead code]
```

### 3. Exception Path Testing

Scan all try/except blocks in modified code:
- For each except clause: can it actually be triggered?
- Does the except clause log the error with enough context to diagnose?
- Does recovery (if any) leave the system in a consistent state?
- Nested try/except: does the inner exception propagate correctly to the outer handler?

**Execution timing**:
- During Phase 4 Self-Check, after happy-path verification passes
- For L2 changes: test at minimum the Degradation path
- For L3 changes: test all three categories (Degradation + Branch + Exception)
- Results recorded as part of Self-Check output

---

## Code Review Delegation (T2 mandatory under conditions)

Self-review has a blind spot: the same mental model that wrote the code reviews it. For high-impact changes, delegate an independent review to a fresh-context subagent.

**Trigger conditions** (meet ANY):
- **Scope**: Modified >= 3 files in this task
- **Contract change**: Modified any function/class signature (Phase 1.5 Interface Contract Diff was triggered)
- **Risk level**: Any L3-level modification
- **Debugging intensity**: Phase 3.5 circuit breaker was triggered
- **Dark path discovery**: Dark Path Protocol revealed a degradation path issue, branch unreachability, or exception handling gap

**Delegation protocol**:
1. Dispatch a fresh-context subagent (read-only, no file modifications)
2. Review dimensions: spec compliance, security checklist, dark path coverage, contract consistency, defense-in-depth
3. Evaluate findings: CRITICAL → fix immediately; WARNING → assess and fix; INFO → log and proceed
4. Audit trail: Record in task summary

> **Note**: If subagent dispatch is not available, perform the review yourself with a "steelman" mindset — re-read as a skeptical external reviewer.

### Receiving Code Review

**Core principle**: Verify before implementing. Ask before assuming. Technical correctness over social comfort.

**6-Step Response Pattern**:
1. READ: Complete feedback without reacting
2. UNDERSTAND: Restate requirement in own words
3. VERIFY: Check against codebase reality (grep, test, trace)
4. EVALUATE: Technically sound for THIS codebase?
5. RESPOND: Technical acknowledgment or reasoned pushback
6. IMPLEMENT: One item at a time, test each

**Forbidden Responses** (performative agreement):
NEVER: "You're absolutely right!" / "Great point!" / "Excellent feedback!" / "Thanks for catching that!"

INSTEAD: Restate the technical requirement / Ask clarifying questions / Push back with technical reasoning if wrong / Just start working

**When feedback IS correct**:
- ✅ "Fixed. [Brief description of what changed]"
- ✅ "Good catch — [specific issue]. Fixed in [location]."

**Handling Unclear Feedback**: If ANY item is unclear: **STOP** — do not implement anything yet. Ask for clarification on ALL unclear items first.

**YAGNI Check**: When a reviewer suggests "properly implementing" a feature:
1. `grep` the codebase for actual usage
2. If unused → question whether to implement
3. If used → then implement properly

**Push back when**: suggestion breaks existing functionality, reviewer lacks full context, violates YAGNI, is technically incorrect for the stack, or conflicts with user's prior decisions.

**Source-Specific Handling**:
| Source | Trust Level | Action |
|--------|------------|--------|
| User feedback | Trusted | Implement after understanding |
| External reviewer (subagent) | Skeptical | Verify before implementing |
| External reviewer (human) | Skeptical but check | Same as subagent |

**Implementation Order**:
1. Clarify ALL unclear items first
2. Blocking issues (breaks, security)
3. Simple fixes (typos, imports, naming)
4. Complex fixes (refactoring, logic changes)
5. Test each fix individually
6. Verify no regressions from the fix batch

---

## Experience Extraction & Skill Evolution

### Feedback Triple-Write (WITH GATE)

Every lesson discovered during Phase 4 must be written to destinations based on scope. **Gate**: Universal lessons that modify SKILL.md require review for architectural consistency before writing.

**Write destinations**:

| # | Destination | What to write | When | How |
|---|------------|--------------|------|-----|
| 1 | **Daily log** | Full incident record: Context → Problem → Solution | Always | Via review-evolver if available, otherwise `daily-log/YYYY-MM-DD.md` |
| 2 | **Project rules** | Project-specific rule or gotcha | When project-specific | Append to `.project_rules.md` in project root |
| 3 | **Skill improvement** | Universal pattern or checklist item | When universal AND passes gate | See Gate below |

**Gate for SKILL.md updates** (prevents uncontrolled expansion):
1. Is the lesson truly universal (not project-specific)?
2. Does it fit an existing Phase/checklist section, or does it require a new section?
3. If it requires a new section: does the new section stay under 30 lines?
4. **If any answer is No → write to daily-log + project rules only, skip SKILL.md**

```
Universal lesson → gate check → fits existing section? → yes → update SKILL.md
                                                       → no  → new section < 30 lines? → yes → add + changelog
                                                                                               → no  → project rules only
```

**Example — Triple-Write in action**:

> Lesson: "大盘择时降级时，action字段未同步更新，导致日志和邮件展示不一致"
>
> - **daily-log**: "大盘择时降级bug：降级移组时8处未同步action字段..."
> - **.project_rules.md**: Under "Integration: timing_engine ↔ signal_engine": "- Degradation must synchronize signal, score, action fields atomically"
> - **SKILL.md**: Add to Phase 4 Dark Path Protocol: "Degradation completeness check: verify ALL related fields are updated"

**Quality gate**: Before closing Phase 4, confirm:
- [ ] At least one destination written (daily log is minimum)
- [ ] If .project_rules.md exists, project-specific lessons are appended
- [ ] SKILL.md updated only if lesson passes the gate above

### Error & Correction Capture

Trigger review-evolver (preferred) or self-improvement if any of the following occurred:
- A command or tool failed unexpectedly
- User corrected your approach
- You discovered your knowledge was outdated
- You found a better approach than what you initially used

### TodoWrite Cleanup
- Verify all todo items are marked completed
- If any items were cancelled, document why
- If Phase 2.5 checkpoint was created, clean up `.temp/backup/` unless user wants it retained

<!-- Updated: 2026-09-08, extracted from phase-4-review.md for T1/T2 token optimization -->
<!-- Updated: 2026-09-08, added Feedback Triple-Write gate to prevent uncontrolled SKILL.md expansion -->