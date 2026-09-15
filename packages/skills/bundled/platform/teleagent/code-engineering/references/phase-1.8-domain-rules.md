---
AIGC:
  ContentProducer: ''
  ContentPropagator: ''
  Label: '1'
---

# Phase 1.8: Domain Rule Loading — Detailed Protocol

> **Phase**: 1.8 (Domain Rule Loading — KNOWLEDGE INJECTION)
> **Risk Level Activation**: T1: Scan + Load if found, T2: Full scan + inject, T0: Skip
> **Source**: Extracted from SKILL.md v2.1

---

After understanding the project context but BEFORE any constraint checking or coding, **load all known domain-specific rules** that apply to this project. This phase bridges the gap between generic engineering checklists and project-specific pitfalls.

**Why this phase exists**: Generic checklists cannot capture project-specific rules (e.g., "trading holidays are never trading days", "financial data from source X uses unit in thousands not ten-thousands"). These rules typically exist in project documentation but are invisible during coding. Phase 1.8 makes them visible.

### Rule Discovery Protocol

Scan the following sources in order. For each source found, load its rules into the working context:

1. **Project rule files** (highest priority — project-maintained):
   - `.project_rules.md` or `PROJECT_RULES.md` in project root
   - `.cursorrules` in project root
   - Any `.md` file in project root matching `*rules*`, `*convention*`, `*gotcha*`

2. **Agent memory rules** (already in context — do NOT re-read):
   - USER.md and MEMORY.md are injected into context by the system at session start
   - Simply scan their content from context for constraint sections (`[任务偏好]`, `[硬规则]`, L4 global rules)
   - Do NOT use Read tool or memory_get to re-read them — that wastes tokens

3. **Code-level contracts** (if the project uses typed interfaces):
   - `contracts.py` / `.contracts.yaml` — interface schema definitions
   - `types.py` / `models.py` — shared type definitions
   - Any file matching `*schema*`, `*contract*`, `*protocol*`

### Rule Application

For each discovered rule:

1. **Classify** its applicability to the current task:
   | Rule Type | Scope | Example |
   |-----------|-------|---------|
   | Always apply | Every task in this project | "All external API calls must have timeout + retry" |
   | Conditionally apply | Only when touching specific modules | "eltdx data unit is in thousands" only when processing financial data |
   | Not applicable | Unrelated to current task | Rules about frontend rendering when doing backend work |

2. **Inject applicable rules** into Phase 2 as `[Domain-Specific]` checklist items:
   ```
   [Domain-Specific] (auto-loaded from .project_rules.md)
   - [ ] Trading holidays are never trading days — skip unconditionally
   - [ ] Financial data from eltdx uses unit in thousands, not ten-thousands
   - [ ] subprocess calling .cmd/.bat files must pass shell=True on Windows
   ```

3. **If no project rule files found**: Log a note — "No project-level rules discovered. Proceeding with generic checks only." Do NOT fabricate rules.

### Rule File Template (for projects that don't have one yet)

When Phase 1.8 finds no project rule file AND the task reveals project-specific pitfalls, suggest creating `.project_rules.md`:

```markdown
# Project Rules (auto-accumulated from development lessons)

## Module: [module-name]
- [Rule description — what to always/never do and why]
- [Another rule]

## Data Source: [source-name]
- [Unit/scale/encoding convention]
- [Known gotcha and workaround]

## Integration: [moduleA ↔ moduleB]
- [Contract or ordering constraint]
- [Field synchronization rule on degradation paths]
```

This file grows organically via the Feedback Triple-Write protocol in Phase 4.