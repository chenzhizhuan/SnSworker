---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '0e96dcd2-1854-4be9-abea-c887c396ccfa'
  PropagateID: '0e96dcd2-1854-4be9-abea-c887c396ccfa'
  ReservedCode1: '27749d7c-df99-4a71-a9cf-c7f511aa8797'
  ReservedCode2: '27749d7c-df99-4a71-a9cf-c7f511aa8797'
---

# Phase 3: Template Reuse & Execution — Detailed Protocol

> **Phase**: 3 (Template Reuse & Execution)
> **Risk Level Activation**: T0: Direct code, skip verify | T1: 4 core checks | T2: 6 full checks
> **Source**: Extracted from SKILL.md v2.1

Check references/ for applicable templates before writing from scratch. For MODIFICATION tasks, apply the incremental change strategy below.

### Modification Safety Levels

Before each code change, classify its safety level. This determines whether to proceed automatically or seek confirmation:

| Level | Description | Examples | Action |
|-------|-------------|----------|--------|
| **L0** | Cosmetic / non-functional | Format, import reorder, comment, rename local var | Auto-apply |
| **L1** | Additive, no existing behavior change | New function, new file, new parameter with default value | Auto-apply |
| **L2** | Behavioral change, localized | Modify function logic, change return value format, add/remove API endpoint | Auto-apply + verification step |
| **L3** | Structural / cross-cutting | Modify DB schema, change shared data model, refactor core module, delete function/file | **Confirm with user** + checkpoint + verification step |

**Default rule**: If unsure, treat as one level higher.

### Incremental Edit Principles

1. **Surgical edits over rewrites**: Use `edit` tool for targeted changes, never `write` to overwrite an entire existing file unless it's a new file
2. **Single edit <= 30 lines**: If a logical change requires > 30 lines of edit, decompose it further or use multiple sequential edits
3. **Preserve what works**: Never rewrite functioning code "just to clean it up" unless the task explicitly requires refactoring
4. **No speculative changes**: Don't add features "while you're in the area" unless they're in the requirements
5. **Test after each L2+ change**: Run relevant tests/verification after each behavioral change, not just at the end

### Execution Flow for Modification Tasks

```
For each step in the TodoWrite:
1. Classify the change level (L0-L3)
2. If L3 → confirm with user, ensure Phase 2.5 checkpoint exists
3. Read the target file (MUST read before edit, even if you wrote it earlier)
4. Apply the minimal edit using edit tool
5. **敏感信息写入守护**：写入任何包含鉴权字段的文件前，须校验值不是真实敏感数据。真实值必须使用环境变量引用（采用 `_env` 后缀约定）或 `PLACEHOLDER`。如检测到真实敏感数据，立即停止并警告用户。
6. If L2+ → run Write-Verify Loop (see below)
7. Mark todo completed
8. Next step
```

### Write-Verify Loop (MANDATORY for L2+ changes)

After writing or modifying code, **automatically execute a verification script** to catch issues that checklist review misses. This replaces manual checklist compliance with machine-enforced checks.

**Step 1: Run prebuilt verify script** — call the prebuilt verification tool:

```powershell
# --module is OPTIONAL: omit it to skip the import check (do NOT pass --module "")
python references/verify/verify_script.py --target "<target_file>" --checks all
# When module import validation is needed:
python references/verify/verify_script.py --target "<target_file>" --module "<module_import_path>" --checks all
```

For targeted checks (faster, lower token cost):
```powershell
python references/verify/verify_script.py --target "<target_file>" --checks encoding,bare_except,import,hardcode
```

| Check | What it does | When to include |
|-------|-------------|----------------|
| encoding | Zero-width char (U+200B) + UTF-8 BOM scan | Always |
| bare_except | Regex scan: bare except / except-pass / except without `as e` | Python files |
| import | subprocess `python -c "import {module}"` | When --module provided |
| types | mypy type check | Typed languages |
| readback | .bat CRLF / .json BOM format integrity | .bat/.cmd/.json files |
| hardcode | 硬编码敏感信息扫描（覆盖多种常见敏感字段类型） | 所有源码与配置文件 |

**Step 2: Evaluate results**:
- All `[PASS]` → proceed to next step
- Any `[FAIL]` → fix the issue, re-run verify until all pass
- `[SKIP]` is acceptable (e.g., mypy not installed)
- **Circuit breaker**: If 3+ consecutive verify-fix cycles fail on the same step, escalate to user

### Execution Flow for New Project Tasks

```
1. Check references/ for applicable template
2. If found → copy skeleton, customize per Usage Checklist
3. If not found → write from scratch following Phase 2 checklist
4. Consider Template Self-Build Protocol if the pattern is reusable
```

### Available Templates (see references/ directory)
- **Node.js HTTP Server**: `references/nodejs-http-server.md` - Standard server skeleton with health check, CORS, error handling
- **Python Data Pipeline**: `references/python-data-pipeline.md` - Pandas data pipeline with retry, logging, JSON output
- **Frontend SPA Skeleton**: `references/frontend-spa-skeleton.md` - HTML/ECharts SPA with responsive layout and API integration

### SDD Mode (T2 only — for multi-task plans)
For subagent-driven development with persistent plans, see `references/phase-3-sdd.md`. Requires git repo, multi-task plan, and subagent dispatch capability.

### Template Usage Protocol
1. Read the applicable template from references/
2. Copy the skeleton structure
3. Customize for the specific task (fill in business logic, adjust endpoints)
4. Verify all placeholder markers are resolved (no TODO/FIXME left)

### Anti-Patterns to Avoid
- **No cargo-cult copying**: Understand what each template section does before using it
- **No partial templates**: Use the complete template structure; cherry-picking breaks integrity
- **No stale templates**: If a template doesn't fit the current task, write from scratch instead of force-fitting

### Template Self-Build Protocol

When no existing template fits the task AND the task involves a reusable pattern (will likely repeat), build a new template:

**Trigger criteria** (meet ANY):
- Same code pattern written 2+ times across different conversations
- A project creates a new service/module type not covered by existing templates
- User explicitly requests: "把这个存为模板" / "下次类似任务复用这个结构"

**Build process**:
1. Identify the skeleton: What stays constant across instances? (imports, structure, error handling, logging)
2. Identify the customization points: What changes per instance? (endpoints, business logic, data fields)
3. Read `references/template-specification.md` for the standard template format
4. Write the template file to `references/<template-name>.md`
5. Update the "Available Templates" list above in SKILL.md
6. Validate: Can you instantiate a real working file from this template in one pass?

### Template Iteration Protocol

Templates degrade if they don't evolve with usage. Iteration triggers:

| Signal | Action |
|--------|--------|
| Repeatedly need to add the same boilerplate when using a template | Template is missing a section — **add it** |
| A template section is always deleted/overridden when used | Template is bloated — **remove or make optional** |
| A bug/issue is caught that could have been prevented by a checklist item | Add to Pre-flight checklist in Phase 2 |
| New environment constraint discovered (e.g., new API limitation) | Add to relevant template + Pre-flight checklist |
| User corrects a generated pattern | Update the template to embed the correction |

**Iteration process**:
1. Identify the specific deficiency (missing section / redundant section / wrong pattern)
2. Read the current template
3. Edit the template (use edit tool, not rewrite)
4. Add a changelog comment at template bottom: `<!-- Updated: YYYY-MM-DD, reason -->`
5. If the change affects Phase 2 checklist, update checklist accordingly

### TDD Optional Path (conditional — triggered by specific scenarios)

Test-Driven Development is not mandatory for all tasks (CE's default is Write-Verify Loop which provides machine-enforced post-write checks). TDD is triggered conditionally when the task meets ANY of these criteria:

**Trigger conditions** (meet ANY):
- **New feature development** (not modification of existing code): writing a new function, module, or service from scratch
- **Phase 3.5 systematic debug fix**: after root cause is identified in Phase A, the fix should be validated by a failing test (see Phase D Step 1)
- **User explicitly requests TDD** or says "写测试" / "write tests" / "test-driven"
- **Core business logic**: code that handles money, trades, user data, or anything where a logic bug has high consequences

**TDD Flow (Red-Green-Refactor)**:

```
1. RED — Write a failing test first
   - Define the expected behavior as a test function
   - Run the test → it MUST fail (HARD GATE)
   - If the test passes before implementation → the test is wrong (it tests nothing new), or the feature already exists
   - The failure proves the test has teeth

2. GREEN — Write the minimal implementation to make the test pass
   - Do NOT write more than needed to turn the test green
   - Run the test → it MUST pass
   - If it doesn't pass → the implementation is incomplete, fix it (but don't add extra features)

3. REFACTOR — Improve the code while keeping tests green
   - Clean up structure, extract helpers, improve naming
   - Run the test after EACH refactor step → must stay green
   - If the test goes red during refactoring → you broke something, revert and try again
```

**TDD vs Write-Verify Loop — when to use which**:

| Scenario | Use TDD | Use Write-Verify Loop |
|----------|---------|----------------------|
| New feature from scratch | Yes — test defines the spec | No |
| Modifying existing function | No (test the existing behavior first) | Yes — verify after modification |
| Bug fix (Phase 3.5) | Yes — write test that reproduces the bug first | Yes — also run after fix |
| Script / automation | No — overkill | Yes — post-run verification |
| Config change | No | Yes — verify config loads correctly |
| Core business logic | Yes — high cost of bugs | Yes — both are needed |

**Integration with Phase 3.5**: When TDD is triggered by Phase 3.5 (bug fix), the RED step (failing test) corresponds to Phase D Step 1, and the GREEN step corresponds to Phase D Step 2-3. The failing test becomes part of the permanent test suite, preventing regression.

### Parallel Agent Dispatch

When facing 2+ independent failures (different test files, different subsystems, different bugs), investigating sequentially wastes time. Each investigation is independent and can happen in parallel.

**Note**: This pattern manages code-level parallel debugging. For project-level task orchestration, use the Kanban skill instead.

#### Decision Tree

```
Multiple failures?
├── No → Single investigation
└── Yes → Are they independent?
    ├── No (related — fix one might fix others) → Single agent investigates all together
    └── Yes → Can they work in parallel (no shared state, no file conflicts)?
        ├── No (shared state / same files) → Sequential agents
        └── Yes → Parallel dispatch
```

**Use when**:
- 3+ test files failing with different root causes
- Multiple subsystems broken independently
- Each problem can be understood without context from others
- No shared state between investigations

**Don't use when**:
- Failures are related (fixing one might fix others)
- Need to understand full system state
- Agents would interfere (editing same files, using same resources)
- Exploratory debugging (don't yet know what's broken)

#### Dispatch Pattern

1. **Identify independent domains** — group failures by what's broken. Each domain is independent if fixing one doesn't affect another.
2. **Create focused agent tasks** — each agent gets:
   - **Specific scope**: One test file or subsystem
   - **Clear goal**: Make these tests pass / fix this subsystem
   - **Constraints**: Don't change other code; don't refactor unrelated areas
   - **Expected output**: Summary of root cause and what was fixed
3. **Dispatch in parallel** — issue all subagent dispatches in a single response (multiple dispatches in one response = parallel; one per response = sequential)
4. **Review and integrate** — when agents return:
   - Read each summary
   - Verify fixes don't conflict (check for same-file edits)
   - Run full test suite (not just individual files)
   - Spot check — agents can make systematic errors

#### Agent Prompt Quality

| Bad Pattern | Good Pattern |
|-------------|-------------|
| "Fix all the tests" — too broad, agent gets lost | "Fix `agent-tool-abort.test.ts`" — focused scope |
| "Fix the race condition" — no context | Paste error messages and test names |
| No constraints — agent might refactor everything | "Do NOT change production code" or "Fix tests only" |
| "Fix it" — vague output | "Return summary of root cause and changes made" |