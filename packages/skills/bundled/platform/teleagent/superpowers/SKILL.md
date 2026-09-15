---
name: superpowers
description: Use when starting any software development task - provides a complete agentic development methodology including brainstorming, TDD, systematic debugging, plan writing, and code review. Activates before writing code to ensure design-first, test-driven, evidence-based workflows. Triggers on feature development, bug fixing, refactoring, and any multi-step coding project.
name_cn: 超能开发方法论
description_cn: 完整的智能体软件开发方法论，涵盖需求头脑风暴、测试驱动开发、系统化调试、计划编写和代码审查等全流程。
create_source: super-agent-skill-creator
version: 6.3.0
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'd22ed594-a63a-4dae-ac04-cdf72138b6a5'
  PropagateID: 'd22ed594-a63a-4dae-ac04-cdf72138b6a5'
  ReservedCode1: 'ffa00c72-1239-4c1b-8985-1a2923157c5d'
  ReservedCode2: 'ffa00c72-1239-4c1b-8985-1a2923157c5d'
---

# Superpowers - Agentic Development Methodology

## Overview

A complete software development methodology for coding agents. Before writing any code, step back and understand what you're building. Then plan, implement with TDD, and verify. Core principle: **process over guessing, evidence over claims, design before code.**

## Core Rule

**Invoke relevant sub-skills BEFORE any response or action** — including clarifying questions, exploring codebase, or checking files.

- "Let's build X" → brainstorming first, then implementation
- "Fix this bug" → systematic-debugging first, then fix
- "Implement this plan" → executing-plans or subagent-driven-development

If a sub-skill might apply, you MUST use it. User instructions override skills, which override defaults.

## The Workflow

```
1. Brainstorming     → Refine ideas into a design spec
2. Using Git Worktrees → Create isolated workspace
3. Writing Plans     → Break design into bite-sized tasks (2-5 min each)
4. Executing Plans   → Implement with TDD, review between tasks
5. TDD               → RED-GREEN-REFACTOR for every feature/bugfix
6. Code Review       → Verify before merging
7. Finish Branch     → Merge, PR, or keep as-is
```

## Sub-Skills Index

Read the corresponding skill directory when a sub-skill triggers:

| Sub-Skill | When to Use | Skill Directory |
|-----------|-------------|----------------|
| brainstorming | Before any creative work — creating features, building components, adding functionality | `brainstorming/` |
| writing-plans | Have a spec/requirements, before touching code | `writing-plans/` |
| executing-plans | Have a written plan to execute with checkpoints | `executing-plans/` |
| subagent-driven-development | Executing plans with independent tasks, dispatching fresh subagent per task | `subagent-driven-development/` |
| test-driven-development | Implementing any feature or bugfix, before writing code | `test-driven-development/` |
| systematic-debugging | Any bug, test failure, or unexpected behavior, BEFORE proposing fixes | `systematic-debugging/` |
| verification-before-completion | About to claim work is complete/fixed, before committing or creating PRs | `verification-before-completion/` |
| requesting-code-review | Completing tasks, implementing features, before merging | `requesting-code-review/` |
| receiving-code-review | Receiving review feedback, before implementing suggestions | `receiving-code-review/` |
| using-git-worktrees | Starting feature work needing isolation from current workspace | `using-git-worktrees/` |
| finishing-a-development-branch | Implementation complete, all tests pass, decide how to integrate | `finishing-a-development-branch/` |
| dispatching-parallel-agents | 2+ independent tasks that can be worked on without shared state | `dispatching-parallel-agents/` |
| writing-skills | Creating or editing skills | `writing-skills/` |

> **并行派发参考**：当用户要求多 subagent 并行执行计划时，参见 `references/parallel-sdd-dispatch.md`——按文件域分组避免写冲突、冲突矩阵构建、完成后共享文件检查与最终编译验证的完整流程。
>
> **并行派发与验证实战备忘**：Windows 环境下并行派发的预提取资源（PDF 等）与验证陷阱（`node --test` 路径参数、Playwright 不可用回退），参见 `references/parallel-dispatch-verification.md`。

## The Iron Laws

1. **No code without a failing test first** — TDD is mandatory, not optional
2. **No fixes without root cause investigation** — Symptom fixes are failure
3. **No completion claims without fresh verification evidence** — Run the command, read the output
4. **No implementation without design approval** — Present design, get sign-off, then build

## Rationalization Red Flags

These thoughts mean STOP — you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is too simple to need a design" | Simple projects hide the most assumptions |
| "I'll test after" | Tests-after prove nothing; you never watched them fail |
| "Just try this fix and see" | Systematic debugging is faster than guessing |
| "Should work now" | Run the verification command |
| "I'll skip TDD just this once" | Every "just this once" becomes a pattern |
| "The issue is simple, no process needed" | Simple issues have root causes too |
| "Close enough on spec compliance" | Spec gaps = not done |

## Quick Reference

| Phase | Key Action | Success Criteria |
|-------|-----------|------------------|
| Brainstorm | Ask questions, propose approaches, present design | User approves design |
| Plan | Break into 2-5 min tasks, no placeholders | Complete plan with exact code |
| TDD | Write test → watch fail → write code → watch pass → refactor | All tests green, each test watched failing first |
| Debug | Read errors → reproduce → trace data flow → root cause → fix | Understand WHAT and WHY |
| Review | Spec compliance + code quality | Critical/Important issues resolved |
| Verify | Run commands, read full output, confirm claim | Fresh evidence for every claim |
| Finish | Run full suite → present merge/PR/keep options | User decides integration path |

## Philosophy

- **Test-Driven Development** — Write tests first, always
- **Systematic over ad-hoc** — Process over guessing
- **Complexity reduction** — Simplicity as primary goal
- **Evidence over claims** — Verify before declaring success
- **YAGNI** — You Aren't Gonna Need It
- **DRY** — Don't Repeat Yourself

---

Based on [superpowers](https://github.com/obra/superpowers) v6.3.0 by Jesse Vincent / Prime Radiant, MIT License.