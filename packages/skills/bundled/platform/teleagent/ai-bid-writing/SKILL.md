---
name: ai-bid-writing
description: |
  信息化行业专业AI标书写作引擎。面向系统集成商、软件开发商、IT运维服务商、网络安全服务商，
  覆盖软件开发、系统集成、运维服务、网络安全、数据治理、云服务等信息化项目的技术方案编写。
  Trigger keywords: write bid, technical proposal, bidding document, proposal writing, generate proposal, write chapter X,
  scoring table, bid analysis, heading system, proposal outline, 写标书, 技术标, 投标方案, 方案写作, 生成方案, 写第X章, 评分表, 招标文件分析, 标题体系, 标书大纲,
  信息化, 系统集成, 软件开发, 运维服务, 网络安全, 等保, 信创.
---

# AI标书写作 — 信息化行业技术方案写作流程 v3.1

## 信息化项目专版 · 标题驱动 · 并发写作 · 自动Word转换

---

## 0. Input Document Preparation (doc2txt tool)

Before starting Step 1, convert all input documents to plain text using the bundled `doc2txt.py` converter.

### Supported Formats

| Format | Method | Output |
|--------|--------|--------|
| `.doc` | olefile + UTF-16LE text block scanning | `.txt` |
| `.docx` | python-docx paragraph extraction | `.txt` |
| `.xlsx` | openpyxl → Markdown table | `.md` |
| `.pdf` (text layer) | pymupdf text extraction | `.txt` |
| `.pdf` (scanned) | Returns hint message | — |

### Usage

```bash
# Single file
python {skill_base}/tools/doc2txt.py <file_path>

# Batch conversion
python {skill_base}/tools/doc2txt.py file1.doc file2.pdf file3.xlsx

# Specify output
python {skill_base}/tools/doc2txt.py input.doc -o output.txt
```

### Requirements

All dependencies are pure pip packages (zero system dependencies):

```bash
pip install olefile python-docx openpyxl pymupdf
```

### Important Notes

- The tool creates output files alongside the source files:
  - `原文件名_doc2txt.txt` for .doc/.docx/.pdf
  - `原文件名_doc2txt.md` for .xlsx
- Scanned PDFs (no text layer) return a hint message; use a vision-capable model or OCR tool separately.
- After conversion, read the `.txt`/`.md` output file and use its content for Step 1 analysis.

---

## I. Workflow Overview

```
┌────────┐    ┌───────────────┐    ┌────────────────────────────┐    ┌──────────────┐    ┌──────────┐
│ Step 1 │───▶│    Step 2     │───▶│          Step 3            │───▶│  Step 4      │───▶│  Step 5  │
│ Input  │    │Heading System★│    │ Concurrent Writing: Expand  │    │ Word 转换    │    │ 临时文件 │
│Analysis│    │   Core (25%)  │    │ per heading → word-count    │    │ md_to_docx   │    │ 清理     │
│  (5%)  │    │               │    │ check → expand →达标→ Merge  │    │ (自动)       │    │ (自动)   │
└────────┘    └───────────────┘    └────────────────────────────┘    └──────────────┘    └──────────┘
                     ↑                         ↑
       Headings determine           Each L3 heading independently
       scoring coverage             concurrent, merge when done
```

> **Core Principles**:
> Step 2 headings are driven by the scoring table. Each L3 heading = one independent writing task.
> Step 3 adds no intermediate layer — directly expand around L3 headings to target word count, with concurrent multi-chapter execution.
> Step 4/5 fully automated — markdown → .docx conversion then temp file cleanup, no manual steps.
>
> **信息化行业覆盖**：软件开发 / 系统集成 / 运维服务 / 网络安全（含等保测评）/ 数据治理 / 云服务 / 信创替代

---

## II. Core Calculation Formula

When the target word count is **T**:

| Parameter | Meaning | IT Industry Empirical Value | Formula |
|-----------|---------|---------------------------|---------|
| C | Total chapters | 6–12 chapters (IT项目通常少于工程类) | Determined by scoring table |
| H₃ | Total L3 headings | ≈ C × 5 (软件开发) ~ 8 (系统集成/运维) | Driven by scoring table and SOW |
| Pᴀᴠɢ | Avg. writing points per heading | 6–10 | = T / (H₃ × A) |
| A | Avg. word count per point | 400 (中文标书经验值) | Includes table conversion |
| **T** | **Target total word count** | **50K–200K（信息化项目典型范围）** | = H₃ × Pᴀᴠɢ × A |

**Validation (100,000 — 典型信息化项目):**

```
H₃ = 50 (50 L3 headings)
Pᴀᴠɢ = 5 (avg. 5 writing points per heading)
A = 400
T = 50 × 5 × 400 = 100,000 ✓
```

**Reverse Calculation (derive point count from target word count):**

```
Given T = 100,000, H₃ = 50, A = 400
Then Pᴀᴠɢ = 100,000 / (50 × 400) = 5
Meaning: plan 5 concrete writing points under each L3 heading
```

---

## III. Step 1: Input Analysis

### 3.1 Input Materials

| Document Type | Key Information | Priority |
|--------------|----------------|----------|
| 招标文件 / 技术规范书 | 评分标准 / 技术要求 / 硬性门槛 / 术语定义 | Required |
| 技术需求规格说明书 (SRS) | 功能需求 / 非功能需求 / 接口规范 / 性能指标 | Required |
| 工作说明书 (SOW) / 服务清单 | 服务范围 / 交付物清单 / SLA指标 / 人员资质要求 | High |
| 系统架构图 / 部署拓扑图 | 技术架构 / 网络拓扑 / 安全域划分 / 容灾架构 | High |
| 信创/等保合规要求 | 信创产品目录 / 等保等级要求 / 密码应用安全要求 | High |
| 合同条款 / 验收标准 | 违约条款 / 承诺指标 / 变更机制 / 验收测试标准 | Medium |
| 公司资质 / 案例资料 | 人员证书 / 资质文件 / 同类项目合同 / 软著/专利 | For writing stage |

### 3.2 Output: Requirements Analysis Report

Must include the following 6 modules:

1. **项目基本信息**: 名称 / 地点 / 规模 / 工期 / 预算金额 / 等保等级要求
2. **核心需求标签**: 3–5 个维度（安全合规 / 高可用 / 可扩展性 / 信创兼容性 / 数据治理 / 用户体验）
3. **硬性门槛清单**: 资质证书要求（CS/ITSS/CMMI/ISO等）/ 人员持证要求 / 信创产品目录 / 封装签章要求
4. **评标机制**: 综合评分法 / 经评审最低价法 / 定性评审（确认评分权重分布）
5. **客户术语表**: 招标文件中出现的专业术语（如等保三级、双活数据中心、微服务架构、数据中台等，整个方案必须回响）
6. **项目类型判定**: 软件开发 / 系统集成 / 运维服务 / 网络安全 / 数据治理 / 云服务 / 其他 → 决定行业标准引用和SOP粒度

### 3.3 Project Type Determination & Context

| 信息化项目类型 | 评分表典型特征 | 标题生成重点 |
|-------------|-------------|------------|
| **软件开发** | 需求分析 / 架构设计 / 功能模块 / 测试方案 / 源代码交付 | 技术架构深度展开、功能模块逐一响应 |
| **系统集成** | 设备供货 / 集成方案 / 实施计划 / 联调测试 / 培训验收 | 设备参数表、集成流程图、实施甘特图 |
| **运维服务** | 服务方案 / 人员配置 / 应急预案 / SLA承诺 / 管理制度 | 量化SOP和服务标准、SLA指标承诺表 |
| **网络安全** | 风险评估 / 等保合规 / 安全策略 / 应急响应 / 渗透测试 | 等保标准逐条对照、安全控制措施清单 |
| **数据治理** | 数据标准 / 数据质量 / 数据安全 / 数据共享 / 平台建设 | 数据架构、标准体系、治理流程量化 |
| **云服务** | 云架构 / 迁移方案 / 安全隔离 / 备份容灾 / 费用优化 | 云原生技术展开、SLA分层承诺 |

> Note: Project type is only used to help understand scoring table structure and determine industry standards when supplementing "completeness headings." **Headings MUST be driven by the scoring table as the primary source — templates must not replace it.**

---

## IV. Step 2: Heading System Generation (★★★ Core Stage)

This stage is the core of the entire writing workflow. Heading system quality directly determines scoring coverage and proposal structure.

---

### 4.1 Chapter Heading (L1 Heading) Generation Rules

**Generation Strategy**

Based on the project scoring table in the bidding document, read every scoring detail in the evaluation criteria table / bid-awarding factor table line by line. Do not omit any scoring point related to technical proposal preparation.

**Dimension Identification & Filtering**

For each scoring item, complete a dual judgment:

| Judgment | Content |
|----------|---------|
| Judgment 1 | Does this require response through technical proposal content? |
| Judgment 2 | Is this AI-generable proposal content? (Exclude items requiring manual entry: specific numeric indicators, company-specific information, proof document requirements) |

**Heading Refinement**

Refine the filtered scoring item core requirements into standardized chapter headings.

**Numbering Format**

Unified use of `Chapter X ××××` format.

---

### 4.2 L2 Heading Generation Rules

**Generation Strategy**

All L2 headings MUST prioritize alignment with scoring table, procurement requirements, and checklist specifications. Only when the above materials lack corresponding detail requirements may industry-standard supplements be added per the corresponding category. Unjustified new content is strictly prohibited.

**Four Mandatory Requirements**

| Requirement | Explanation |
|------------|-------------|
| 100% Scoring Point Coverage | Every scoring detail and procurement requirement clause related to the chapter MUST have a corresponding L2 heading — no omissions |
| Full Category Adaptation | Strictly match the project category's performance logic and industry norms. Do not generate headings inconsistent with project attributes |
| Generatability Filtering | Retain only AI-generable proposal headings. Completely exclude content requiring manual entry |
| Standardized Expression | Unified use of verb-object phrases, concise and clear, compliant with bidding professional standards |

**Processing Flow**

```
1. Define Core Scope
   With the chapter heading as the core topic, scan all user-provided
   scoring tables, requirements documents, checklists, and project introductions
   line by line for all directly/indirectly related scoring requirements,
   technical clauses, and performance requirements.

2. Aligned Core L2 Heading Generation
   Transform each valid clause identified into a corresponding L2 heading.
   Scoring item core requirements must be reflected in the headings.

3. Supplement Completeness Headings (Only When Necessary)
   Only when the above materials lack corresponding detail requirements,
   to ensure chapter logical closure, supplement L2 headings per the
   corresponding category's industry standard structure.
   Specific quantity and supplementary content must not exceed the
   chapter heading's core topic scope.

4. Compliance Filtering
   Exclude headings requiring manual entry. Retain only AI-generable
   proposal L2 headings.
```

---

### 4.3 L3 Heading Generation Rules

**Generation Strategy**

L3 headings MUST carry forward L2 heading core requirements, decomposing scoring item implementation details layer by layer to ensure every scoring point has actionable corresponding content.

**Four Mandatory Requirements**

| Requirement | Explanation |
|------------|-------------|
| Deep Scoring Point Response | L3 headings must carry forward L2 heading core requirements, decomposing scoring item implementation details layer by layer to ensure every scoring point has executable corresponding content |
| Full Category Adaptation | Strictly match the project category's performance elements, decomposing to category-specific execution actions, control standards, and implementation processes |
| Generatability Filtering | Retain only AI-generable proposal headings. Completely exclude content requiring manual entry |
| Standardized Expression | Unified use of verb-object structure. Single heading ≤ 15 characters translated equivalent. Concrete to specific execution actions. Eliminate vague expressions |

**Processing Flow**

```
1. Define Core Scope
   With the chapter heading and L2 heading as the core, scan all user-provided
   bidding document materials line by line for detailed technical requirements,
   performance standards, control rules, and acceptance clauses directly
   related to that L2 heading.

2. Aligned Core L3 Heading Generation
   Decompose and transform each valid clause identified into concrete L3 headings.
   Core parameters, standards, and requirements from clauses must be reflected
   in the headings.

3. Supplement Completeness Headings (Only When Necessary)
   Only when the above materials lack corresponding specific requirements,
   to ensure content logical closure, supplement L3 headings under each L2 heading
   following the corresponding category's PDCA cycle logic
   (Plan → Do → Check → Act).

4. Compliance Filtering
   Exclude headings requiring manual entry. Retain only AI-generable
   proposal L3 headings.
```

---

### 4.4 Heading System Output Format

After the heading system is complete, the following must be confirmed by the user before entering the next stage:

- Whether chapter headings fully cover all technical proposal scoring items in the scoring table
- Whether L2 headings under each chapter 100% carry forward the corresponding scoring details
- Whether L3 headings are concrete to executable implementation actions
- Whether any headings have been added without justification (all should have scoring item/procurement requirement correspondence)
- Whether excluded headings are reasonable (manual-entry items correctly excluded)

**Output Format Example:**

```markdown
# Chapter X Chapter Name

> Corresponding Scoring Item: XXXX (XX pts)
> Corresponding Bidding Clause: X.X.X

## X.1 L2 Heading (verb-object phrase, concise)
> Corresponding Scoring Detail: XXXXXX

### X.1.1 L3 Heading (concrete execution action)
> Corresponding Bid Requirement: XXXXXX

### X.1.2 L3 Heading
> Corresponding Bid Requirement: XXXXXX

## X.2 L2 Heading
> Corresponding Scoring Detail: XXXXXX

### X.2.1 L3 Heading
> ...
```

---

### 4.5 ★★★ Scoring Item-by-Item Cross-Reference Table (Must Produce Before Heading System Confirmation)

**Purpose**: Prevent scoring item omissions due to "interpretation bias." For example, if the bidding document says "需同时支持Oracle和MySQL数据库," the AI might generate only one "数据库设计" heading, losing half the scoring.

After the heading system is complete, a scoring item-by-item cross-reference table MUST be generated at the end of the document. **The user must confirm every scoring item has heading coverage before entering Step 3.**

```markdown
---
## Scoring Item-by-Item Cross-Reference Table (★★★ Confirm BEFORE entering writing stage)

| # | Scoring Item Original Text (copied from bid doc) | Points | Corresponding Chapter | Corresponding Headings | Coverage Status |
|---|------------------------------------------------|--------|----------------------|----------------------|-----------------|
| 1 | 技术方案：含需求分析、系统架构、功能设计、性能指标 | 15分 | Ch. 1 | 1.1–1.6 all | ✅ |
| 2 | 实施方案：含实施计划、部署方案、数据迁移、联调测试 | 10分 | Ch. 2 | 2.1–2.5 all | ✅ |
| 3 | 项目团队配置：含项目经理、技术负责人、持证情况 | 8分 | Ch. 3 | 3.1–3.4 all | ✅ |
| 4 | 售后服务方案：含SLA承诺、运维体系、应急响应 | 8分 | Ch. 4 | 4.1–4.5 all | ✅ |
| 5 | 网络安全方案：含等保合规、数据安全、访问控制 | 6分 | Ch. 5 | 5.1–5.4 all | ✅ |
| 6 | 培训方案：含系统管理员培训、最终用户培训 | 4分 | Ch. 6 | 6.1–6.2 all | ✅ |
| ... | (Every technical scoring item in one row, none omitted) | ... | ... | ... | ... |

> Statistics: Technical scoring total X items, X points, this table covers X items (100%)
> Uncovered items: None
```

**Filling Rules**:

| Rule | Explanation |
|------|------------|
| "Scoring Item Original Text" column | Must copy verbatim from bidding document; NO rewriting |
| Multi-heading correspondence | One scoring item may correspond to multiple headings (comma-separated) |
| ✅ Coverage Status | Clear heading coverage |
| ⚠️ Coverage Status | Partial coverage; must note what is missing |
| ❌ Coverage Status | No corresponding heading |
| If any ⚠️ or ❌ exists | MUST supplement headings before entering next stage |

---

### 4.6 Word Count Reallocation After Heading System

After the heading system is confirmed by the user, substitute C (chapter count) and H₃ (total L3 heading count) into the core formula:

```
T = H₃ × Pᴀᴠɢ × A

Where H₃ is now precisely known, no longer estimated.
Target words per chapter = (Chapter scoring points / Total technical bid points) × T
Points per L3 heading = Target words for chapter / L3 heading count in chapter / A
```

The word count allocation table produced at this stage is based on **actual scoring weights** rather than template estimates, dramatically improving precision.

---

## V. Step 3: Concurrent Chapter-by-Chapter Writing

### 5.0 Mandatory Pre-Writing Gate Check (★ 强制执行，不可跳过)

**在启动 Step 3 之前，主控 Agent 必须逐项确认以下清单。任何一项未满足，禁止进入写作阶段。**

```
┌─────────────────────────────────────────────────┐
│  ☐ 1. 标题体系已获用户确认                        │
│  ☐ 2. 每章字数配额已按评分权重分配完毕             │
│  ☐ 3. 已准备好统一术语表（Step 1 输出）            │
│  ☐ 4. 已准备好统一写作规范（人称、量化要求、表格要求）│
│  ☐ 5. 并发 Agent 数量 = 章数（每章一个独立 Agent）  │
│  ☐ 6. 所有 Agent 的 prompt 已包含：                │
│       - 完整 L1/L2/L3 标题树                       │
│       - 本章字数配额硬指标                          │
│       - 扩展循环指令（写→数→扩→达标）                │
│       - 写作规范（人称、表格、段落结构）             │
└─────────────────────────────────────────────────┘
```

### 5.0.1 ★ 硬性禁止规则（违反即流程失败）

| # | 禁止行为 | 原因 |
|---|---------|------|
| 1 | **禁止串行写作** | 不得用一个大文件逐章拼接。主控 Agent 必须为每一章启动独立 Agent，所有 Agent 同时运行 |
| 2 | **禁止跳过字数检查** | 每章 Agent 完成初稿后必须数字数，与配额对比。未达标必须进入扩展循环 |
| 3 | **禁止未达标就交稿** | 每章 Agent 不得在字数未达标（<95% 配额）的情况下终止。必须扩展至达标 |
| 4 | **禁止单章无 Agent** | 如果章数 > 并发能力上限，分批并发，但每章仍必须由独立 Agent 完成，不得由主控 Agent 直接写 |

### 5.0.2 主控 Agent 职责（★ 关键角色）

主控 Agent **不直接写作**，职责是：

1. **准备阶段**：确认标题体系已确认 → 分配字数配额 → 编写每章 Agent 的 prompt
2. **启动阶段**：一次性启动所有章的 Agent（并行），每章一个
3. **监控阶段**：等待所有 Agent 完成，收集每章的「完成报告」
4. **合并阶段**：按章号拼接 → 术语一致性检查 → 图片提示词检查（每章≥2处，格式正确）→ 评分对照表复核 → 输出完整 .md 方案
5. **Word 转换阶段**（自动，无需用户指令）：复制 md_to_docx.py → 配置路径 → 执行转换 → 生成 .docx
6. **清理阶段**（自动，无需用户指令）：删除 chapters/ 目录、merge.py、convert.py、tables_output.txt、*_doc2txt.txt、_flowcharts/ 等临时文件
7. **最终交付**：保留最终 .md + .docx 两个文件，输出清理汇总

### 5.0.3 每章 Agent 完成报告（★ 必须输出）

每个 Agent 完成任务后，必须以结构化格式输出完成报告：

```
## 第X章 完成报告

- 状态: 达标 / 未达标
- 目标字数: XX,XXX
- 实际字数: XX,XXX（达标率 XX%）
- L3 标题总数: X 个，已写 X 个（完成率 XX%）
- 扩展轮次: X 轮
- 最薄弱的 3 个 L3: (编号 + 字数)
- 字数 ≥500 的 L3 数量: X / X
```

主控 Agent 发现任何章的"状态: 未达标"时，必须将该章 Agent 重新唤醒并要求扩展，**不得手工填补内容**。

### 5.1 Core Philosophy

**No intermediate layer.** The heading system is the blueprint. L3 headings are the writing instructions. Expand content directly around each L3 heading — no pre-written outlines.

**Word count guaranteed by expansion loop.** Write → Count words → Insufficient → Expand → Count again →达标 → Next chapter.

**Concurrent chapter execution.** Launch as many parallel writing tasks as there are chapters. Merge when done.

### 5.2 Single-Chapter Writing-Expansion Loop

```
┌──────────────────────────────────────────────┐
│  Input: Complete L1/L2/L3 heading tree        │
│         + word count quota for chapter        │
└──────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────┐
│  Round 1: Write 500–800 words first draft     │
│           under each L3 heading               │
│           Count words, compare vs. chapter    │
│           quota                               │
└──────────────────────────────────────────────┘
                    ↓
            ┌──达标？────┐
            ↓ YES        ↓ NO
      ┌──────────┐   ┌──────────────┐
      │Quality   │   │Expand command│
      │Self-check│   │Which L3s are │
      │→ Pass    │   │too thin?     │
      └──────────┘   │→ Supplement  │
           ↓         │Data tables   │
      Next chapter   │missing?→ Add │
      / Merge        └──────────────┘
                          ↓
                    Return to count check
```

**Expansion Command Template** (for writing agent):

```
Current chapter word count: X,XXX | Target: XX,XXX | Gap: X,XXX

The following L3 headings are too thin — expand:
- X.X.X: Current ~XXX words, expand to ~XXXX words, direction: (concrete instruction)
- X.X.X: Current ~XXX words, expand to ~XXXX words, direction: (concrete instruction)
```

### 5.3 Concurrent Execution Strategy

**Launch as many parallel writers as there are chapters.** Each writer receives the complete heading tree + word count quota + writing standards, and completes the task independently.

```
After heading system confirmed:

Chapter 1 Writing Agent ──┐
Chapter 2 Writing Agent ──┤
Chapter 3 Writing Agent ──┤
Chapter 4 Writing Agent ──┤
Chapter 5 Writing Agent ──┼── All launch concurrently
Chapter 6 Writing Agent ──┤
Chapter 7 Writing Agent ──┤
  ...                     │
Chapter N Writing Agent ──┘
                    ↓
              All complete → Merge → Final Edit
```

**Concurrency Notes**:

| Item | Requirement |
|------|------------|
| Terminology consistency | Distribute unified terminology glossary to all agents before writing (Step 1 output) |
| Format consistency | Distribute unified format specs to all agents before writing (font/size/line-spacing/person) |
| Cross-references | Chapters write independently, do not reference unknown content. Cross-references inserted uniformly at merge stage |
| Merge order | After all chapters complete, concatenate by chapter number. Final editor performs consistency check |

### 5.4 Per-Chapter Writing Standards (Distribute to Each Agent)

```
You are writing Chapter X: XXX of the technical proposal for information technology project "XXX Project."

Your task:
1. Expand writing content heading by heading around the L3 heading tree below
2. Write 500–800 words first draft under each L3 heading
3. Count words after completion, compare vs. quota (this chapter quota: XX,XXX words)
4. If below quota, auto-expand thin L3 headings until达标

Writing requirements:
- Person: use "项目团队将/应/负责," avoid "我公司/我们"
- Quantification: all commitments, standards, timelines expressed in numbers. Prohibit "力争," "尽量," "努力"
- Tables: at least 1 data table (≥4 rows × 3 cols) under each L2 heading
- Paragraph structure: [概述 1–2句] → [展开 3–8句] → [支撑 数据/标准] → [小结 1–2句]
- Technical accuracy: 引用标准须准确（如等保2.0 GB/T 22239-2019、ITSS GB/T 28827、信创产品名录等）
- Client terminology: 招标文件中的技术术语必须在全文中自然出现≥3次
- ★ Image prompt keywords: 在正文中适合配图的位置（架构说明、流程描述、拓扑描述、方法论框架等），嵌入图片生成提示词，格式为正文【图片提示词：xxx】正文，每章至少2处。提示词须具体可生成，包含：图片类型（架构图/流程图/拓扑图/框架图）、核心元素、风格要求
```

### 5.5 Word Count Quota Allocation (Determine Before Writing)

```
Per-chapter quota = Target total words × (Chapter scoring points / Total technical proposal points)

Example: Target 100K words, Chapter 1 (技术方案) assigned 15 scoring points, total technical points 55
Chapter 1 quota = 100,000 × 15/55 ≈ 27,300 words
```

Write each chapter's quota into the heading system document as a hard metric for the writing agent.

### 5.6 Content Layering & Parallelizability

Although outlines are no longer needed, content type determines expansion depth:

| Type | Proportion | Writing Strategy |
|------|-----------|-----------------|
| **Standardized** (generic standards/systems/SOPs) | ~40% |达标 from first draft, minor adjustments |
| **Semi-custom** (has framework, needs project parameters) | ~35% | Needs 1–2 expansion rounds after first draft |
| **Fully custom** (requirements analysis/key challenges/commitments) | ~25% | Needs 2–3 expansion rounds after first draft |

Expansion directions for fully custom content:
- Add project-specific technical analysis ("以本项目核心业务系统为例，日均并发请求量...")
- Add technical architecture detail and performance metrics support
- Add technology selection comparisons（"微服务架构 vs 单体架构选型分析"、"开源 vs 商用数据库对比"）
- Add quantified benefit projections（"预计系统响应时间降低 X%，运维人力成本节省 Y 人/年"）
- Add compliance standards mapping（等保条款 → 技术措施 → 管理措施 对照表）

---

### 5.7 自动 Word 转换与临时文件清理（★ 合并后自动执行）

合并完成后，主控 Agent 自动执行以下两步，**无需用户额外指令**。

#### 5.7.1 自动 Word 转换

1. 读取 `{word_skill_base}/md_to_docx.py`，复制其全部内容
2. 在最终 .md 文件所在目录创建 `convert.py`，写入复制的内容
3. 修改 `convert.py` 中的配置区：
   ```python
   INPUT = r'<最终.md文件的绝对路径>'
   OUTPUT = r'<同目录下同名.docx文件的绝对路径>'
   CHAPTER_TITLE = '<项目名称>'
   TABLE_CAPTION_PREFIX = '表'
   ```
4. 运行 `python convert.py` 执行转换
5. 确认输出包含 `[OK] 文档已保存：...docx` 且文件存在

**依赖检查**：如果 `pip install python-docx matplotlib Pillow` 尚未安装，自动先执行安装。

#### 5.7.2 临时文件清理

**从任务开始即维护“生成文件清单”**：记录本次运行创建的文件和目录、创建用途、是否为最终交付件。最终 Word 验证成功后，按清单清理；不得仅依赖固定文件名或通配符猜测临时文件。

清理必须同时满足以下条件：

1. 仅删除本次运行创建、且已记录在生成文件清单中的路径。
2. 删除前解析绝对路径，路径必须位于当前工作区内；最终交付件、用户源文件、任务开始前已存在的文件一律保留。
3. `work/`、`chapters/`、`rendered/`、`_flowcharts/`、本次创建的 `docs/superpowers/`、构建/测试脚本、提取文本和缓存均视为临时产物，除非用户明确要求保留。
4. `~$*.docx`、`~$*.xlsx` 等 Office 锁文件可能对应用户正在打开的文档，不自动删除。
5. Windows 环境使用同一 PowerShell 流程完成路径验证与删除，优先 `Remove-Item -LiteralPath`；不得把路径交给另一 shell 拼接删除。
6. 完成最终页数、内容、结构和可访问性验证后再清理，禁止提前删除仍被验证或重建依赖的文件。
7. 仅当目录本身由本次运行创建且确认未混入既有文件时，才可递归删除整个目录；否则只删除清单中的子项，并仅移除清空后的空目录。

常见临时产物包括：

| 临时文件/目录 | 说明 | 删除命令 |
|-------------|------|---------|
| `work/`、`chapters/`、`rendered/` | 章节、图片、渲染页、构建和测试文件 | 按生成文件清单删除 |
| `convert.py`、`merge.py`、测试脚本 | 转换、合并及验证工具 | 按生成文件清单删除 |
| `tables_output.txt`、`*_doc2txt.txt`、`*_doc2txt.md` | 输入材料提取中间文件 | 仅删除本次生成的文件 |
| `_flowcharts/`、`__pycache__/` | 流程图缓存和 Python 缓存 | 按生成文件清单删除 |
| 本次创建的设计/计划文件 | 任务内部规格和执行计划 | 用户未要求保留时删除 |

> **保留文件**：所有用户源文件、任务开始前已存在的资料、最终 `.md`/`.docx` 交付件，以及用户明确要求保留的中间产物。

#### 5.7.3 清理完成确认

清理后重新扫描工作区，确认最终交付件仍存在且可打开，且生成文件清单中未保留无必要临时项。主控 Agent 输出简洁的清理汇总。例如：

> Word 转换完成。临时文件已清理：chapters/（4章文件+merge.py）、convert.py、tables_output.txt、2个doc2txt中间文件。保留文件：技术方案_商务部分.md、技术方案_商务部分.docx。

---

## VI. Full Document Writing Standards

### 6.1 Person & Sentence Structure

| ✅ Use | ❌ Prohibit |
|--------|-----------|
| 项目团队将 / 应 / 负责 | 我公司 / 我们 |
| 无主语句（"负责..."、"确保..."）与"将+动词"交错使用 | 整篇使用单一句式 |
| 量化指标（百分比 / 天数 / 频率 / 毫秒 / Mbps / TPS） | "力争"、"尽量"、"努力"等模糊承诺词 |
| 引用正式标准编号（如 GB/T 22239-2019、ISO/IEC 27001） | 笼统的"国家标准"、"行业规范" |

### 6.2 表格与数据

基础规则：
- 每个 L2 标题下至少 1 个数据表（≥4行×3列）
- 关键参数（性能指标 / 人员配置 / 设备参数 / 服务承诺）必须表格化呈现
- 表格不替代正文分析，正文+表格形成"文字结论→表格支撑"结构

信息化项目常用表格类型：

| 表格类型 | 适用场景 | 示例 |
|---------|---------|------|
| **技术参数表** | 设备供货、软件功能清单 | 服务器配置参数、软件模块功能列表 |
| **性能指标表** | SRS响应、验收标准 | 响应时间/并发数/可用性指标承诺 |
| **SLA承诺表** | 运维服务、云服务 | 响应时间/修复时间/可用性 分级承诺 |
| **兼容性矩阵** | 信创适配、系统对接 | 操作系统/数据库/中间件兼容性列表 |
| **等保合规对照表** | 网络安全方案 | 等保条款→技术措施→管理措施映射 |
| **实施计划表** | 系统集成、软件开发 | 阶段/任务/工期/责任人/交付物 |
| **人员资质表** | 团队配置 | 姓名/岗位/证书/经验年限 |
| **技术选型对比表** | 架构设计 | 方案A/B/C在性能/成本/风险维度对比 |

### 6.3 段落结构

```
[概述] 1–2句，点明本节的方案目标/范围/设计原则
[展开] 3–8句，逐点展开具体做法
[支撑] 数据表格 / 引用标准编号 / 技术指标
[小结] 1–2句，收束本节效果或引出下一节
```

### 6.5 图片提示词嵌入规范（★ 每章强制执行）

正文写作时，在适合配图的位置嵌入 AI 图片生成提示词，作为后续配图的依据。提示词嵌入正文中，不入表格，不被 Word 转换脚本过滤。

**格式**：`正文【图片提示词：xxx】正文`

**嵌入要求**：

| 要求 | 说明 |
|------|------|
| 每章最低数量 | 每章 ≥ 2 处，重点章节（实施方案、架构设计）≥ 4 处 |
| 嵌入位置 | 架构说明、流程描述、拓扑描述、方法论框架、组织架构等适合配图的段落中 |
| 提示词结构 | `图片类型 + 核心元素 + 风格要求`（如"系统逻辑架构图：展现前端接入层、业务服务层、数据层的三层架构关系，蓝色科技风格，标注关键组件名称"） |
| 图片类型参考 | 系统架构图、网络拓扑图、业务流程图、部署架构图、安全域划分图、组织架构图、实施路线图、运维服务体系图、数据流转图 |

**示例**（嵌入正文语境）：

> 项目团队将构建"前端接入层→业务服务层→数据持久层"的三层松耦合架构，各层之间通过标准化接口通信，实现横向扩展与纵向解耦【图片提示词：系统逻辑架构图，展示前端接入层（含负载均衡、API网关）、业务服务层（含微服务集群、消息中间件）、数据持久层（含主从数据库、缓存集群、对象存储）的三层架构关系，各层之间标注通信协议和数据流向，蓝色科技风格】。架构设计遵循高内聚、低耦合原则，各层独立部署、独立扩展。

### 6.6 信息化项目特殊写作规范

1. **技术准确性**：引用标准时须标注完整编号和年份（如 GB/T 22239-2019《信息安全技术 网络安全等级保护基本要求》），首次出现给出全称
2. **架构图描述**：系统架构、网络拓扑、部署架构章节须有文字描述，不能仅靠图表支撑——描述图内各组件的功能、关系、数据流
3. **接口规范**：涉及系统对接时，须说明接口方式（API/WebService/消息队列/中间库）、数据格式（JSON/XML）、认证方式
4. **信创合规**：若招标文件涉及信创要求，须逐项列明所选用产品的信创目录对应关系（CPU/OS/数据库/中间件/浏览器）
5. **等保措辞**：网络安全方案的术语须与等保2.0标准用词一致（"安全计算环境""安全区域边界""安全通信网络""安全管理中心"）

---

## VII. Full Process Quality Checklist

### After Step 2 Completion (Before Heading System Confirmation)

- [ ] Scoring item-by-item cross-reference table generated, verified line by line
- [ ] Every technical scoring item in the scoring table has a corresponding L1 heading
- [ ] L2 headings under each L1 heading 100% carry forward corresponding scoring details
- [ ] L3 headings are concrete to executable implementation actions
- [ ] No unjustified added headings (all must have scoring item/procurement requirement correspondence)
- [ ] Manual-entry items correctly excluded
- [ ] No ⚠️ or ❌ in coverage status
- [ ] Per-chapter word count quotas allocated by scoring weight

### During Per-Chapter Writing (Within Expansion Loop)

- [ ] Each L3 heading in the chapter has ≥500 words of substantive content
- [ ] Chapter actual word count达标 (≥95% of quota)
- [ ] If not达标, expansion launched with clear expansion directions

### After All Chapters Complete (Before Final Edit)

- [ ] Per-chapter word count deviation ≤10%
- [ ] 客户术语全篇频率合理（关键术语在各章均有出现）
- [ ] 无"力争""尽量""努力"等模糊承诺词
- [ ] 无"我公司""我们"等第一人称
- [ ] 跨章节引用由最终编辑统一插入
- [ ] 全篇术语一致性检查通过
- [ ] 评分对照表复核无遗漏
- [ ] 技术标准编号引用准确（等保/信创/国标编号正确无误）
- [ ] ★ 图片提示词：每章≥2处，格式正确（正文【图片提示词：xxx】正文），提示词具体可生成

### After Word Conversion & Cleanup (Auto)

- [ ] `convert.py` 配置正确，含正确的 INPUT / OUTPUT / CHAPTER_TITLE
- [ ] Word 转换成功，`.docx` 文件存在且大小合理（≥ 输入端 .md 的 50%）
- [ ] `chapters/` 目录及其内容已删除
- [ ] `convert.py` 已删除
- [ ] `tables_output.txt` 已删除
- [ ] `*_doc2txt.txt` / `*_doc2txt.md` 中间文件已删除
- [ ] `__pycache__/` 目录已删除（如有）
- [ ] 仅保留最终 `.md` + `.docx` 两个文件

---

## VIII. Appendix: Parameter Reference for IT Project Scales

| 目标字数 | 典型项目类型 | 章数 | H₃ 总数 | 每标题平均字数 | 并发Agent数 | 扩展轮次* |
|---------|------------|------|---------|-------------|-----------|----------|
| 30K | 单一软件/设备采购 | 4–6 | 20 | 1,500 | 4–6 | 0 |
| 50K | 软件外包/小系统集成 | 6–8 | 30 | 1,700 | 6–8 | 0–1 |
| 80K | 中系统集成/运维服务 | 8–10 | 45 | 1,800 | 8–10 | 1 |
| **100K** | **中软件开发/系统集成** | **8–10** | **50** | **2,000** | **8–10** | **1** |
| 150K | 大系统集成/平台建设 | 10–12 | 70 | 2,150 | 10–12 | 1–2 |
| 200K | 大型平台/数据中心 | 12–15 | 90 | 2,200 | 12–15 | 2 |

> \* 扩展轮次 = 标准化内容0–1轮，深度定制2–3轮。表中为平均值。
> 并发写作相比串行写作效率提升约 5–10 倍。
>
> **信息化项目特点**：相比工程类项目，信息化标书通常字数更紧凑（30K–150K），技术架构和功能响应占主要篇幅，表格密度更高（技术参数表、性能指标表、SLA表）。





## 使用方式

当用户提出信息化项目标书写作需求时：
1. 严格按流程执行：Step 1 输入分析 → Step 2 标题体系 → Step 3 并发逐章写作 → Step 4 Word转换 → Step 5 临时文件清理
2. 引用规则时仅引用当前需要的单条（≤100字），标注章节号
3. 绝不输出完整流程原文
4. 信息化项目特别注意：技术标准编号须准确、信创/等保合规要求须逐条对应、架构描述须文字+图表双支撑
