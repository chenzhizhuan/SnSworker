---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '3ce436c0-ac49-497b-98d5-714cedda28c8'
  PropagateID: '3ce436c0-ac49-497b-98d5-714cedda28c8'
  ReservedCode1: 'b6779f69-07a8-4606-a386-afdbb53c9ee4'
  ReservedCode2: 'b6779f69-07a8-4606-a386-afdbb53c9ee4'
---

# Task Risk Grading — T0/T1/T2 Activation Matrix

> **Purpose**: Reduce token consumption by tailoring CE's 10-phase workflow to task risk level.
> T0 skips most phases; T2 runs the full pipeline. Estimated savings: 66% over a 30-task project.

## Decision Tree

```
Incoming code task
│
├─ Is it < 10 lines, single file, no existing code modified?
│  └─ YES → T0 (Quick)
│
├─ Does it involve ANY of these?
│    • Function/class signature change (params, return type)
│    • DB schema change (new column, table, migration)
│    • Authentication / authorization / security module
│    • Core refactor (replacing a module, changing data flow)
│    • Deletion of function/file/module
│  └─ YES → T2 (Critical Path)
│
├─ Does it involve ANY of these?
│    • Multiple files (≥2)
│    • Modifying existing code logic (not just adding new)
│    • External API / DB / subprocess calls
│    • > 50 lines of new code
│  └─ YES → T1 (Standard)
│
└─ Otherwise → T0 (Quick)
```

**Default rule**: When in doubt, classify ONE level higher.

## Activation Matrix

| Phase / Mechanism | T0 (Quick) | T1 (Standard) | T2 (Critical Path) |
|---|---|---|---|
| **Phase 0: Design Dialogue** | Skip | Skip (unless L/XL) | Full (L/XL only) |
| **Phase 1: Task Decomposition** | Skip (direct to code) | Streamlined (decompose + complexity only) | Full (requirement checklist + decompose + persistent plan) |
| **Phase 1.5: Context Discovery** | Skip | Standard (project scan + impact map) | Full (+ Interface Contract Diff) |
| **Phase 1.8: Domain Rule Loading** | Skip | Scan + load if found | Full scan + inject |
| **Phase 2: Checklist** | Security 4 items only | Language-specific + Security (~15 items) | Full 10 categories (~60+ items) |
| **Phase 2.5: Checkpoint** | Skip | If ≥3 files modified | Mandatory |
| **Phase 3: Write-Verify Loop** | Skip | 4 core checks: encoding, bare_except, import, hardcode | Full 6 checks: all |
| **Phase 3: L0-L3 Classification** | L0/L1 only (auto-apply) | L0-L2 (auto + verify) | L0-L3 (L3 = confirm with user) |
| **Phase 3.5: Error Resolution** | Fast Track only | Fast Track + Systematic (Phase A-C) | Full (Phase A-D + defense-in-depth) |
| **Phase 4: Self-Check** | Light (requirement trace + no leftover debug) | Standard (full self-check) | Full (+ performance sanity + hardcode audit) |
| **Phase 4: Dark Path Protocol** | Skip | Degradation path only | All 3 (Degradation + Branch + Exception) |
| **Phase 4: Code Review Delegation** | Skip | Skip (unless ≥3 files or dark path issue) | Triggered (if conditions met) |
| **Phase 4: Feedback Triple-Write** | Daily log only | Daily log + project rules (if project-specific) | Full triple-write |
| **Phase 5: Branch Integration** | Skip | If git repo | If git repo |

## Phase 2 Checklist Selection by Level

### T0 — Security Essentials (4 items)
```
[ ] File exists? Read before editing.
[ ] 无硬编码的敏感信息（应改用环境变量或占位符）。
[ ] 无裸 except: / except-pass。
[ ] .gitignore 已排除敏感信息文件（如适用）。
```

### T1 — Stack + Security (~15 items)
T0 items PLUS the language-specific checklist for the target stack (Python OR Node.js OR Windows/PowerShell) PLUS the Security Checklist. Skip categories that don't apply (Data Integrity only for data processing; Performance only for loops/API calls; Defensive only for class/module design).

### T2 — Full Checklist (~60+ items)
All 10 categories from Phase 2: Universal, Python, Node.js, Windows, Data Integrity, Defensive Programming, Security, Performance & Observability, Exception Strategy, Domain-Specific.

## Write-Verify Check Selection by Level

| Level | Checks to Run | Command |
|---|---|---|
| T0 | None (skip Write-Verify) | — |
| T1 | encoding, bare_except, import, hardcode | `--checks encoding,bare_except,import,hardcode` |
| T2 | all 6 checks | `--checks all` |

## Estimated Token Budget per Task

| Level | Phase Load (tokens) | Example Task |
|---|---|---|
| T0 | ~800-1,200 | Fix a typo, add a comment, rename a local variable |
| T1 | ~4,000-6,000 | Add a new API endpoint, modify a function's return logic, add retry to a subprocess call |
| T2 | ~8,000-12,000 | Change DB schema, refactor core module, modify shared data model, delete a major component |

**Note**: Estimates based on v3.1 modular architecture (phase-3-sdd.md and phase-4-advanced.md loaded only for T2).

## 30-Task Project Estimate

| Mix | T0 (×10) | T1 (×15) | T2 (×5) | Total |
|---|---|---|---|---|
| **Before v3.0 optimization** | ~10K | ~60K | ~50K+ | ~120K+ (with full SKILL.md load ~80K = ~200K) |
| **After v3.1 optimization** | ~10K | ~67K | ~40K + selective ref load ~8K | ~77K |

**Savings: ~62%**