---
AIGC:
  ContentProducer: ''
  ContentPropagator: ''
  Label: '1'
---

# Phase 3: Subagent-Driven Development & Parallel Dispatch

> **Phase**: 3 (Execution — advanced mode)
> **Risk Level Activation**: T2 only (SDD) | T1/T2 (Parallel Dispatch on demand)
> **Source**: Extracted from phase-3-execution.md v3.1

> ⚠️ **Prerequisites for SDD**: Git repo with branch support, multi-task implementation plan from Phase 1, multiple subagent dispatch capability. If any prerequisite is missing, use Inline Execution instead.

---

## SDD Mode Overview

Subagent-Driven Development provides structured execution for multi-task plans. Fresh subagent per task → task review (spec + quality) → fix loop → final whole-branch review.

**When to use SDD vs Inline Execution**:
- Multi-task plan from Phase 1? → SDD (recommended)
- Tasks mostly independent? → SDD
- Tasks tightly coupled? → Inline Execution (standard Phase 3 Write-Verify Loop)
- Single task or trivial plan? → Inline Execution

**Continuous execution**: Do not pause between tasks. Only stop for: BLOCKED status, unresolvable ambiguity, or all tasks complete.

### The Ledger System (CRITICAL)

Conversation memory does not survive context compaction. Track progress in a ledger file, not only in todos.

**Ledger file**: `.temp/sdd-progress.md`

**Ledger format**:
```markdown
# SDD ledger — plan: <plan file path>

Task 1: complete (commits <base7>..<head7>, review clean)
Task 2: fix round 1/5 (2 addressed, 0 open; commits <a7>..<b7>)
Task 2: complete (commits <base7>..<head7>, review clean)
Task 3: parked — magic number finding — ruling: acceptable, documented in comment
Task 3: complete (commits <base7>..<head7>, 1 parked)
```

**Ledger rules**:
- First line names the plan file — a ledger naming a different plan belongs to another session, leave it in place.
- Tasks with `Task <N>: complete` are DONE — never re-dispatch them.
- A task whose last line is a fix round is mid-loop — resume the loop at the next round.
- After compaction, trust the ledger and `git log` over your own recollection.
- Every adjudication is a ledger entry — silent discards are forbidden.

### Model Selection Strategy

Use the least powerful model that can handle each role. **Always specify the model explicitly when dispatching a subagent** — an omitted model inherits the session default, silently defeating this strategy.

| Task Type | Model Tier | Example |
|-----------|-----------|---------|
| Mechanical implementation (1-2 files, complete spec) | Cheap/fast | Transcription + testing from plan text |
| Integration tasks (multi-file coordination) | Standard | Pattern matching, debugging |
| Architecture/design tasks | Most capable | System design, broad understanding |
| Task review (small mechanical diff) | Cheap-to-mid | Single-file scoped review |
| Task review (subtle/concurrency diff) | Most capable | Complex multi-file review |
| Fix loop rounds 4-5 | One tier above the stuck implementer | Fresh eyes + capability bump |
| Final whole-branch review | Most capable available | Full branch diff assessment |

**Turn count beats token price**: Cheapest models routinely take 2-3× turns on multi-step work, costing more overall. Use mid-tier as the floor for reviewers and implementers working from prose descriptions.

### The Task Loop

For each task in the plan:

**1. Dispatch the implementer** (fresh subagent, zero context pollution):
- Record BASE commit (`git rev-parse HEAD`) before dispatching — review packages need it
- Dispatch prompt contains: (1) one line on where this task fits; (2) the task brief; (3) interfaces and decisions from earlier tasks; (4) resolution of any ambiguity; (5) report-file path and report contract
- **NEVER** paste accumulated prior-task summaries into dispatches — a fresh subagent needs its task, the interfaces it touches, and global constraints. Nothing else.
- **Never dispatch multiple implementation subagents in parallel** (conflicts)

**2. Handle the report**:
- **DONE** → Generate review package, dispatch task reviewer
- **DONE_WITH_CONCERNS** → Read concerns; if correctness/scope, address before review; if observations, note and proceed
- **NEEDS_CONTEXT** → Provide missing context, re-dispatch
- **BLOCKED** → Assess: context problem (provide more) / needs reasoning (more capable model) / too large (break apart) / plan wrong (escalate to user)
- Never ignore an escalation or force the same model to retry without changes

**3. Review the task** (task-scoped gate — never skip):
- Hand the reviewer its diff as a file (review package: commit list + stat + full diff)
- Reviewer inputs: task brief + report file + review package + global constraints
- Reviewer reports: spec compliance (✅/❌) + task quality (approved/issues)
- Reviewer may report "⚠️ Cannot verify from diff" items — resolve each before marking task complete
- **Never pre-judge findings for the reviewer** — never instruct to ignore or not flag a specific issue

**4. The fix loop** (triggers on spec ❌, Critical/Important findings, or confirmed ⚠️ gaps):

Minor findings → record in ledger as deferred, point final review at the list. Never enter the loop for minors.

Plan-mandated findings (conflict with plan text) → present to user, ask which governs. Never dismiss or fix without asking.

Everything else enters the loop. **5 rounds maximum per task**:

- **Rounds 1-3**: Resume the original implementer (context intact). Send open findings verbatim.
- **Rounds 4-5**: Dispatch a fresh implementer on a more capable model.
- **Every round**: Implementer fixes → re-runs tests → appends report → scoped re-review
- **Never fix findings yourself in the controller session** — your context stays clean for coordination.

**The breaker** (round 5 re-review still has open findings):
- Stop dispatching. Adjudicate each open finding.
- **Real and load-bearing** → STOP: report to user

**5. Complete the task**: Append to ledger, mark todo complete, move to next task.

### Final Whole-Branch Review

After all tasks complete:
1. Generate full-branch review package (MERGE_BASE..HEAD)
2. Dispatch final reviewer on the most capable available model
3. If findings: dispatch ONE fix subagent with the complete findings list
4. Run exactly one scoped re-review of the fix wave
5. Adjudicate residuals (park with rulings, or stop on load-bearing)
6. No second fix wave — residual load-bearing findings surface to user at Phase 5

### SDD Common Rationalizations

| Excuse | Correction |
|--------|------------|
| "Close enough on spec compliance" | Reviewer found spec gaps = not done. Fix or hit the cap. |
| "I'll fix it myself, dispatching is overhead" | Controller fixes pollute context and skip review. |
| "One more round will converge" | Past the cap, rounds don't converge — structural failure. |
| "This finding is obviously wrong, I'll drop it" | Adjudicate only at the cap, every ruling is a ledger entry. |
| "The fix was small, skip the re-review" | Unreviewed fixes are how regressions land. |
| "Ledger bookkeeping is overhead" | The ledger survives compaction. Controllers without one re-dispatch completed tasks. |

---

## Parallel Agent Dispatch

For independent multi-domain failures (different test files, different subsystems, different bugs).

> Note: This pattern manages code-level parallel debugging. For project-level task orchestration, use the Kanban Skill instead.

### Decision Tree

```
Multiple failures?
├── No → Single investigation
└── Yes → Are they independent?
    ├── No (related — fix one might fix others) → Single agent investigates all together
    └── Yes → Can they work in parallel (no shared state, no file conflicts)?
        ├── No (shared state / same files) → Sequential agents
        └── Yes → Parallel dispatch
```

### Dispatch Pattern

1. **Identify independent domains** — group failures by what's broken
2. **Create focused agent tasks** — each agent gets specific scope, clear goal, constraints, expected output
3. **Dispatch in parallel** — issue all subagent dispatches in a single response
4. **Review and integrate** — verify fixes don't conflict, run full test suite, spot check

### Agent Prompt Quality

| Bad Pattern | Good Pattern |
|-------------|--------------|
| "Fix all the tests" — too broad | "Fix `agent-tool-abort.test.ts`" — focused scope |
| "Fix the race condition" — no context | Paste error messages and test names |
| No constraints — agent might refactor everything | "Do NOT change production code" |
| "Fix it" — vague output | "Return summary of root cause and changes made" |

<!-- Updated: 2026-09-08, extracted from phase-3-execution.md for T1/T2 token optimization -->