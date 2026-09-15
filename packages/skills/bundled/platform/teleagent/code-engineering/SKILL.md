---
name: code-engineering
description: Code engineering best practices for structured development. Use when writing, modifying, debugging, or refactoring code. Enforces task decomposition, constraint checking, template reuse, and post-task review. Triggers on any code-related task including bug fixes, new features, refactoring, scripts, automation, and system integration.
name_cn: 代码工程最佳实践
description_cn: 结构化代码开发框架，核心为十阶段工作流加T0/T1/T2三级风险分级。小改走快速通道，核心重构走全流程，按需加载协议节省token。十阶段涵盖设计、拆解、检查、验证、根因分析、复盘到分支集成，设硬门禁。内置反合理化拦截，对接review-evolver提取经验写入记忆。
version: '3.5'
updated: '2026-09-09'
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '59a5d773-3de9-4055-94ce-2c9572507dc7'
  PropagateID: '59a5d773-3de9-4055-94ce-2c9572507dc7'
  ReservedCode1: 'fc03ddbd-94d7-4e18-a30c-393a04f1982d'
  ReservedCode2: 'fc03ddbd-94d7-4e18-a30c-393a04f1982d'
---

# Code Engineering Best Practices

Every code task follows this **ten-phase** workflow, gated by **Task Risk Grading (T0/T1/T2)**. Detailed protocols are in reference files — load only what your risk level requires.

## Skill Dependencies
- **Surgical edit principles** (inherited): Minimal change philosophy.
- **review-evolver**: Experience extraction and evolution (Phase 4 delegates here).
- **review-evolver** (preferred) / **self-improvement** (fallback): Error/correction capture at runtime.

## Anti-Rationalization Interception (GLOBAL DISCIPLINE)

| Rationalization Thought | CE Contextual Correction |
|------------------------|--------------------------|
| "This is just a simple bug, I'll fix it directly" | Simple bugs have root causes. Phase 3.5 root-cause investigation is fast. |
| "Let me just change it and see if it works" | Investigate first — 2-min root-cause trace saves 30-min fix-break-fix cycles. |
| "I'll add tests later" | Tests written after implementation prove nothing. TDD's failing test is the proof. |
| "It should work now" | "Should" is not evidence. Run the verification command. |
| "The blast radius is probably small" | "Probably" is a guess. Phase 1.5 Impact Map replaces guesses with facts. |
| "This doesn't need the full workflow" | >10 lines triggers all phases. When in doubt, treat ONE level higher. |

**Enforcement**: Detect → Stop → Apply correction → Resume from corrected phase.

## Task Risk Grading (T0/T1/T2) — TOKEN OPTIMIZATION GATE

**Full reference**: `references/task-risk-grading.md`

```
< 10 lines, single file, no existing code modified?     → T0 (Quick)
Signature change / DB schema / auth / core refactor?     → T2 (Critical Path)
≥ 2 files / modifying existing logic / external calls?   → T1 (Standard)
Otherwise → T0.  Default: When in doubt, classify ONE level higher.
```

| Phase | T0 | T1 | T2 |
|---|---|---|---|
| Phase 0 (Design Dialogue) | Skip | Skip (unless L/XL) | Full (L/XL only) |
| Phase 1 (Decomposition) | Skip | Streamlined | Full |
| Phase 1.5 (Context Discovery) | Skip | Standard | Full (+Contract Diff) |
| Phase 1.8 (Domain Rules) | Skip | Scan+load | Full |
| Phase 2 (Checklist) | 4 security items | Stack+Security (~15) | Full (~60+) |
| Phase 2.5 (Checkpoint) | Skip | If ≥3 files | Mandatory |
| Phase 3 (Write-Verify) | Skip | 4 core checks | 6 full checks |
| Phase 3.5 (Error Resolution) | Fast Track | Fast+Systematic A-C | Full A-D+defense |
| Phase 4 (Self-Check) | Light | Standard | Full (+perf+hardcode) |
| Phase 4 (Dark Path) | Skip | Degradation only | All 3 (in phase-4-advanced) |
| Phase 4 (Code Review) | Skip | If ≥3 files/dark path | Triggered (in phase-4-advanced) |
| Phase 4 (Triple-Write) | Daily log | +project rules | Full |
| Phase 5 (Branch Integration) | Skip | If git repo | If git repo |

**Phase Loading**: T0 = this file only (~1.5K tokens). T1 = this file + task-risk-grading + phase-3-execution + phase-1-decomposition + 2-3 checklists (~4K tokens). T2 = T1 + phase-3-sdd + phase-4-advanced + defense-in-depth + all checklists + templates (~12K tokens).

## Phase 0: Design Dialogue `[T0: Skip | T1: Skip unless L/XL | T2: Full]`

> **Full protocol**: `references/phase-1-decomposition.md` (includes Phase 0 as Design Gate for L/XL)

For L/XL tasks: structured design dialogue MUST occur before coding. **HARD GATE**: No implementation until design is presented and user approves. See reference file for 9-step process, design brief template, and persistent plan document format.

## Phase 1: Task Decomposition `[T0: Skip | T1: Streamlined | T2: Full]`

> **Full protocol**: `references/phase-1-decomposition.md`

Decompose into atomic steps before coding. Each step = one verifiable output. Max step scope: one function/module/config change. Steps > 50 lines MUST be sub-decomposed. Create TodoWrite items for each step.

**Complexity**: S (<20 lines) / M (20-50) / L (>50, needs sub-decomposition) / XL (multi-module). Design Gate scales with complexity (S: none, M: Impact Map, L/XL: Phase 0 Design Dialogue + persistent plan).

## Phase 1.5: Context Discovery `[T0: Skip | T1: Standard | T2: Full]`

> **Full protocol**: `references/phase-1.5-context-discovery.md`

Before coding, understand blast radius. Scan project structure, locate modification targets, trace callers, build impact map. For signature changes: run Interface Contract Diff (before/after comparison + trace ALL call sites + atomic batch rule). Multi-file changes (≥2): draw modification propagation graph, execute in topological order.

## Phase 1.8: Domain Rule Loading `[T0: Skip | T1: Scan + Load if found | T2: Full scan + inject]`

> **Full protocol**: `references/phase-1.8-domain-rules.md`

Scan project rule files (`.project_rules.md`, `.cursorrules`) and code-level contracts. **Note**: USER.md and MEMORY.md are already in context via system injection — do NOT re-read them. Inject applicable rules into Phase 2 as `[Domain-Specific]` items. If no rules found, proceed with generic checks only.

## Phase 2: Constraint Check `[T0: 4 security items | T1: Stack+Security ~15 items | T2: Full ~60+ items]`

> **Checklist files**: `references/phase-2-checklist/checklist-*.md` (8 files by category)

**T0 — Security Essentials (4 items)**:
- [ ] File exists? Read before editing.
- [ ] 无硬编码的敏感信息（应改用环境变量或占位符）。
- [ ] 无裸 `except:` / `except-pass`。
- [ ] `.gitignore` 已排除敏感信息文件（如适用）。

**T1+**: Load the language-specific checklist (python/nodejs/windows) + `checklist-security.md` + **max 2** additional categories most relevant to the task. **T2**: Load all 8 checklist files.

> **T1 loading cap**: Never load more than 4 checklist files for T1. When uncertain which categories apply, prefer `data` + `exception` over `defensive` + `performance`.

## Phase 2.5: Checkpoint `[T0: Skip | T1: If ≥3 files | T2: Mandatory]`

Create recovery point before executing changes. Git repo: `git stash` or checkpoint commit. No git: copy affected files to `.temp/backup/pre-[task]/`. DB changes: dump table to `.temp/backup/`.

## Phase 3: Execution `[T0: Direct code, skip verify | T1: 4 core checks | T2: 6 full checks]`

> **Core protocol**: `references/phase-3-execution.md` (Modify Safety Levels, Write-Verify Loop, Templates, TDD)
> **SDD mode** (T2 only, multi-task plans): `references/phase-3-sdd.md`

**Modification Safety Levels**: L0 (cosmetic, auto-apply) / L1 (additive, auto-apply) / L2 (behavioral change, auto + verify) / L3 (structural, **confirm with user** + checkpoint + verify).

**Incremental Edits**: Surgical edits over rewrites. Single edit ≤ 30 lines. Read before edit. No speculative changes.

**Write-Verify Loop** (L2+ mandatory):
```powershell
# Resolve verify script path (CWD is project root, NOT skill root)
$verify = Join-Path $env:USERPROFILE ".config\TeleAgent\users\v1_public_1948258172463542272\skills\code-engineering\references\verify\verify_script.py"
$env:PYTHONDONTWRITEBYTECODE = "1"; python $verify --target "<file>" --checks all
# T1: --checks encoding,bare_except,import,hardcode
# T2: --checks all (6 checks)
```
Checks: encoding | bare_except | import | types | readback | hardcode. All PASS → proceed. Any FAIL → fix + re-run. Circuit breaker: 3+ consecutive failures on same step → escalate to user.

**Templates**: Check `references/` for Node.js HTTP Server, Python Data Pipeline, Frontend SPA Skeleton.

## Phase 3.5: Error Resolution `[T0: Fast Track only | T1: Fast+Systematic A-C | T2: Full A-D+defense-in-depth]`

> **Full protocol**: `references/phase-3.5-error-loop.md`

**Fast Track** (Syntax/Import/Encoding/Env/Network): Read error → targeted fix → retry (max 2). **Systematic Debug** (Runtime/Logic): Phase A (root cause, HARD GATE) → B (pattern analysis) → C (hypothesis verification, one at a time) → D (fix at origin + defense-in-depth + failing test). **Circuit Breaker**: Same error ≥max retries / error cascade 3+ / 5+ total attempts / root cause gate failed 3+ → rollback + escalate to user.

## Phase 4: Post-Task Review `[T0: Light | T1: Standard | T2: Full + advanced]`

> **Core protocol**: `references/phase-4-review.md` (Self-Check, Test Design)
> **Advanced** (T2 only — Dark Path, Code Review, Triple-Write with gate): `references/phase-4-advanced.md`

**Self-Check** (all levels): Requirement trace-back, re-read modified files, no leftover debug/TODO, trace critical path, edge cases.
**Performance sanity** (T2 only): Realistic data volume, memory usage, algorithmic complexity.
**敏感信息审查**（T2 only）：扫描所有配置与缓存文件，排查敏感信息泄露。

## Phase 5: Branch Integration `[T0: Skip | T1: If git repo | T2: If git repo]`

Verify tests → detect git environment → confirm base branch → present 3 options (merge locally / push+PR / keep as-is) → execute → cleanup. Discard requires explicit typed word `discard`.

## Quick Reference: Decision Tree

```
Is this a code task?
├── No → Skip this skill
├── Yes → Classify risk level (T0/T1/T2)
│   └── < 10 lines?
│       ├── Yes → T0: Write code, light self-check only
│       └── No → T1/T2: Load relevant Phase references
│           └── Phase 1 → 1.5 → 1.8 → 2 → 2.5 → 3 → 3.5 → 4 → 5
│               (skip phases per activation matrix for T1)
├── L3 modification? → MUST confirm with user + checkpoint
├── Signature change? → MUST run Interface Contract Diff (Phase 1.5)
└── L/XL task? → MUST run Phase 0 Design Dialogue first
```

## Reference Files Index

| File | Phase | Load When |
|------|-------|-----------|
| `references/task-risk-grading.md` | Global | Always (T0/T1/T2 classification) |
| `references/phase-1-decomposition.md` | Phase 0+1 | T1/T2 |
| `references/phase-1.5-context-discovery.md` | Phase 1.5 | T1/T2 |
| `references/phase-1.8-domain-rules.md` | Phase 1.8 | T1/T2 |
| `references/phase-2-checklist/checklist-python.md` | Phase 2 | T1+ (Python) |
| `references/phase-2-checklist/checklist-nodejs.md` | Phase 2 | T1+ (Node.js) |
| `references/phase-2-checklist/checklist-windows.md` | Phase 2 | T1+ (Windows) |
| `references/phase-2-checklist/checklist-data.md` | Phase 2 | T1+ (data processing) |
| `references/phase-2-checklist/checklist-defensive.md` | Phase 2 | T1+ (class/module design) |
| `references/phase-2-checklist/checklist-security.md` | Phase 2 | T1+ (always) |
| `references/phase-2-checklist/checklist-performance.md` | Phase 2 | T1+ (loops/API calls) |
| `references/phase-2-checklist/checklist-exception.md` | Phase 2 | T1+ (try/except code) |
| `references/phase-3-execution.md` | Phase 3 | T1/T2 (core: Modify Safety, Write-Verify, Templates, TDD) |
| `references/phase-3-sdd.md` | Phase 3 (advanced) | T2 only (SDD + Parallel Dispatch) |
| `references/phase-3.5-error-loop.md` | Phase 3.5 | T1/T2 (on error) |
| `references/phase-4-review.md` | Phase 4 | T1/T2 (Self-Check, Test Design) |
| `references/phase-4-advanced.md` | Phase 4 (advanced) | T2 only (Dark Path, Code Review, Triple-Write) |
| `references/verify/verify_script.py` | Phase 3 | T1/T2 (Write-Verify) |
| `references/defense-in-depth.md` | Phase 3.5 | T2 (defense layers + subprocess patterns) |
| `references/root-cause-tracing.md` | Phase 3.5 | T2 (root cause) |
| `references/nodejs-http-server.md` | Phase 3 | Template |
| `references/python-data-pipeline.md` | Phase 3 | Template |
| `references/frontend-spa-skeleton.md` | Phase 3 | Template |
| `references/template-specification.md` | Phase 3 | Template creation |
| `references/test-design-specification.md` | Phase 4 | Test writing |

## CHANGELOG

### v3.5 (2026-09-09) — Security: AIGC Watermark User ID Removal

| 变更 | 说明 |
|------|------|
| AIGC字段标准化 | ContentProducer/Propagator置空，删除ProduceID/PropagateID/ReservedCode1/ReservedCode2四个非必要UUID字段，保留Label；写入使用无BOM UTF-8 |

### v3.4 (2026-09-09) — Security: __pycache__ Blacklist Fix

| 变更 | 说明 |
|------|------|
| 删除 references/verify/__pycache__/ | 清理Python编译缓存目录（含.pyc文件） |
| Write-Verify 命令加 PYTHONDONTWRITEBYTECODE=1 | 防止未来执行verify_script.py时再生成编译缓存 |
| verify_script.py check_types 修复 | 残留的 `as _` 统一为 `as e`，与 checklist-exception 规则一致 |

### v3.3 (2026-09-09) — Security: Dead Code & Stale Directory Cleanup

| 变更 | 说明 |
|------|------|
| 删除跨会话快照目录 | ce_snapshot.py（190行）+ schema（116行）从未使用，0个快照文件 |
| 删除 kanban 残留目录 | 任务编排残留空目录 |
| SKILL.md 清理引用 | 移除 Phase 1.5 中快照脚本引用和 Reference Index 条目 |

### v3.2 (2026-09-09) — Token Optimization: Residual Cleanup

| 变更 | 说明 |
|------|------|
| Phase 1.5 快照描述精简 | ~120字 → ~30字，节省~80 tokens |
| Phase 1.8 去冗余 | USER.md/MEMORY.md 已在上下文中，标注"do NOT re-read"，避免重复扫描 |
| Phase 2 Checklist 加载上限 | T1 硬限制最多4个checklist文件，防止过度加载 |
| 激活矩阵一致性修复 | Phase 0 T2 补充"(L/XL only)"限定符，与 task-risk-grading.md 对齐 |
| Write-Verify 路径健壮化 | 改用 `$env:USERPROFILE` 绝对路径，不再依赖 CWD 假设 |

### v3.1 (2026-09-08) — Token Optimization: Deep Refactor

**Phase 3/4 参考文件拆分**：将 T1 不需要的 T2 专属内容提取到独立文件，大幅降低 T1 任务 token 消耗。

| 变更 | 说明 |
|------|------|
| 新增 `phase-3-sdd.md` | 从 phase-3-execution.md 提取 SDD 模式 + Parallel Dispatch（T2 only） |
| 新增 `phase-4-advanced.md` | 从 phase-4-review.md 提取 Dark Path + Code Review + Triple-Write gate（T2 only） |
| phase-3-execution.md 精简 | 375行 → 250行，T1 节省 ~1,250 tokens |
| phase-4-review.md 精简 | 296行 → 80行，T1 节省 ~2,160 tokens |
| defense-in-depth.md 瘦身 | 移除 ChanLunPro 项目特定示例（保留通用模式），233行 → 140行 |
| verify_script.py 修复 | bare_except 正则支持点号异常名（如 `httpx.ConnectError`）、异常变量命名统一为 `as e`、readback 全文件扫描（不再只查前500字节） |
| 路径引用修复 | Write-Verify 命令增加 `$skillPath` 解析，修复 CWD 假设错误 |
| Feedback Triple-Write 加门控 | SKILL.md 更新需通过 gate check（universal + fits section + <30 lines），防止技能无序膨胀 |
| Token 预算更新 | T1 估算 2.5-4K → 4-6K（更贴近实际），T2 估算 8-12K 不变 |
| 激活矩阵修正 | Phase 0 T2 标注 "(L/XL only)" 与 SKILL.md 对齐 |

**预期效果**：T1 典型任务 token 节省 ~3,400 tokens（phase-3 + phase-4 拆分 + defense-in-depth 瘦身）。

### v3.0 (2026-08-16) — Token Optimization: Modular Refactor

**SKILL.md 重构为模块化按需加载架构**：

| 变更 | 说明 |
|------|------|
| SKILL.md 主文件瘦身 | 1492行 → ~200行，仅保留核心决策逻辑+激活矩阵+快速参考 |
| 10个 Phase 协议移到参考文件 | Phase 1/1.5/1.8/3/3.5/4 各有独立参考文件，按T0/T1/T2等级加载 |
| 8个 checklist 拆分为独立文件 | python/nodejs/windows/data/defensive/security/performance/exception |
| Task Risk Grading (T0/T1/T2) | v2.1引入的分级机制保留，作为Token优化核心门控 |
| Write-Verify 预置化 | verify_script.py 参数化调用，T1/T2分别用4/6项检查 |
| Reference Files Index | 新增完整参考文件索引表，标注加载条件 |
| 预期Token节省 | 30任务项目从~200K降至~70K(节省66%) |

### v2.1 (2026-08-16) — Token Optimization: Risk Grading

新增 Task Risk Grading (T0/T1/T2) 分级机制。各Phase标注适用等级。Write-Verify调用指令更新。

### v2.0 (2026-08-16) — 结构性大版本升级

九阶段→十阶段框架重构。新增Phase 0 (Design Dialogue)和Phase 5 (Branch Integration)。新增Anti-Rationalization Interception、SDD模式、TDD路径、并行代理派发、Code Review收发、持久化计划文档。

### v1.0 (2026-08-13) — 初始版本

九阶段代码工程框架。