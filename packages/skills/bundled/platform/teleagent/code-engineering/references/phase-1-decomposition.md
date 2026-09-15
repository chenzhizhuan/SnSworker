
# Phase 1: Task Decomposition — Detailed Protocol

> **Phase**: 1 (Task Decomposition — PLANNING)
> **Risk Level Activation**: T1: Streamlined, T2: Full, T0: Skip
> **Source**: Extracted from SKILL.md v2.1

---

Before writing any code, decompose the task into atomic steps.

### Requirement Checklist (BEFORE decomposition)
When user provides requirements with a numbered/bulleted list, **enumerate every single item and verify coverage**:
1. Count total requirements: does the user say "实现N个功能"? Count them.
2. List each requirement as a numbered item in TodoWrite
3. After decomposition, cross-check: every requirement maps to at least one step.
4. If requirements are implicit (e.g., "功能完整"), explicitly decompose into verifiable sub-items.
5. **Common pitfall**: Don't skip "展示"/"输出"/"报告"类需求 — they often imply specific data in the output.

### Decomposition Rules
- **Max step scope**: Each step produces one verifiable output (one function, one module, one config change)
- **Identify dependencies**: Step B depends on Step A's output? Mark it. Execute sequentially.
- **No hidden steps**: If step X requires reading a file, installing a package, or checking an API, make it an explicit step.
- **Complexity threshold**: Any step > 50 lines of new code MUST be further decomposed.

### TodoWrite Integration
- Create a todo item for each decomposed step
- Mark `in_progress` before starting, `completed` immediately after finishing
- Add new items if unexpected sub-problems emerge during execution

### Complexity Assessment Template
```
Input: User's raw request
Output: Numbered step list with scope estimate (S/M/L/XL per step)

S = < 20 lines, no external dependencies
M = 20-50 lines, may need file read/config check
L = > 50 lines, requires sub-decomposition
XL = multi-module new system, requires full design before execution
```

### Design Gate (conditional — based on complexity assessment)

After decomposition and complexity assessment, a design gate prevents jumping into code for large tasks without sufficient planning. The gate scales with complexity: small tasks pass freely, large tasks require explicit design approval.

| Complexity | Gate Requirement | Action |
|-----------|-----------------|--------|
| **S** (< 20 lines) | No gate | Proceed directly to Phase 1.5 |
| **M** (20-50 lines) | Phase 1.5 Impact Map confirmation | Draw Impact Map in Phase 1.5; if blast radius confirms as localized → proceed |
| **L** (> 50 lines) | **Phase 0: Design Dialogue** (see above) → user confirms design → then generate Persistent Plan Document | Phase 0's 9-step process replaces the design brief. Use the design brief template below as a quick reference within Phase 0 Step 5. |
| **XL** (multi-module) | **Phase 0: Design Dialogue** (see above) → user confirms design → then generate Persistent Plan Document | Phase 0's 9-step process replaces the full design. Use the full design template below as a quick reference within Phase 0 Step 5. |

**Design brief template (quick reference for L tasks within Phase 0 Step 5)**:
```
Task: [task name]
Complexity: L ([N] files, ~[N] lines estimated)
Approach: [2-3 sentence strategy description]
Key components: [list of functions/modules to create or modify]
Risks: [identified risks — what could go wrong]
Verification plan: [how to verify correctness after implementation]
→ AWAIT USER CONFIRMATION before proceeding
```

**Full design template (quick reference for XL tasks within Phase 0 Step 5)**:
```
Task: [task name]
Complexity: XL (multi-module system)
Architecture: [system architecture description — how modules connect]
Components:
  1. [component name] — responsibility, inputs, outputs
  2. [component name] — responsibility, inputs, outputs
  ...
Data flow: [how data moves through the system, source → processing → output]
Error handling: [strategy for failures — retry, degradations, circuit breakers]
Key interfaces: [API contracts between components — function signatures, data formats]
Testing strategy: [unit tests, integration tests, dark path tests]
→ AWAIT USER CONFIRMATION before proceeding to Phase 1 decomposition
```

**Gate enforcement**: For L/XL tasks, Phase 0: Design Dialogue IS the gate — completing Phase 0 and obtaining user approval satisfies the Design Gate. Do NOT begin Phase 1.5 (Context Discovery) until Phase 0 is complete and the user has confirmed the design. This prevents investing context-discovery effort into an approach the user might reject.

**Anti-rationalization check**: "I'm pretty sure the approach is right, I'll just start coding" → This is exactly what the design gate prevents. For L/XL tasks, the cost of a wrong approach is high (rework across multiple files/modules). A 2-minute design brief saves hours of rework.

### Persistent Plan Document (for L/XL tasks — generated after decomposition)

After completing decomposition and design gate for L/XL tasks, generate a persistent implementation plan document. This document serves as the single source of truth for execution — it survives context compression and enables subagent-driven development (Phase 3 SDD mode).

**Plan document header** (mandatory):

```markdown
# [Feature Name] Implementation Plan

**Goal:** [One sentence describing what this builds]
**Architecture:** [2-3 sentences about approach]
**Tech Stack:** [Key technologies/libraries]

## Global Constraints
[Project-wide requirements — version floors, dependency limits, naming rules, platform requirements — one line each with exact values. Every task's requirements implicitly include this section.]
```

**File structure mapping** (before defining tasks):
- Map out which files will be created or modified and what each is responsible for
- Design units with clear boundaries and well-defined interfaces; each file has one clear responsibility
- Follow established patterns in existing codebases; if a file being modified has grown unwieldy, a split in the plan is reasonable

**Task structure** — each task in the plan includes:

```markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Interfaces:**
- Consumes: [what this task uses from earlier tasks — exact signatures]
- Produces: [what later tasks rely on — exact function names, parameter and return types. A task's implementer sees only their own task; this block is how they learn the names and types neighboring tasks use.]

- [ ] Step 1: Write the failing test
- [ ] Step 2: Run test to verify it fails
- [ ] Step 3: Write minimal implementation
- [ ] Step 4: Run test to verify it passes
- [ ] Step 5: Commit
```

**Bite-sized task granularity**: Each step is one action (2-5 minutes). "Write the failing test" is a step. "Run it to make sure it fails" is a step. "Implement minimal code" is a step. "Run tests and verify pass" is a step. "Commit" is a step.

**No placeholders rule**: Every step must contain the actual content an engineer needs. These are plan failures — never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code — tasks may be read out of order)
- Steps that describe what to do without showing how (code blocks required for code steps)
- References to types, functions, or methods not defined in any task

**Plan self-review** (after writing the complete plan):
1. **Spec coverage**: Skim each requirement in the spec/design. Can you point to a task that implements it? List any gaps.
2. **Placeholder scan**: Search the plan for red-flag patterns listed above. Fix them.
3. **Type consistency**: Do types, method signatures, and property names in later tasks match what was defined in earlier tasks? `clearLayers()` in Task 3 but `clearFullLayers()` in Task 7 is a bug.
Fix issues inline. If a spec requirement has no task, add the task.

**Execution handoff**: After saving the plan, choose execution mode:
- **Subagent-Driven Development (SDD)** — recommended for multi-task plans. See Phase 3 SDD mode. Fresh subagent per task + two-stage review.
- **Inline Execution** — execute tasks in this session with checkpoints. Use standard Phase 3 Write-Verify Loop per step.

**Save plans to**: `.temp/plan-<feature-name>.md` or project docs directory per user preference.