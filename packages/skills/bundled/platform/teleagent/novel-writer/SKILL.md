---
name: novel-writer
description: "Professional long-form novel writing workshop with a simulated editorial team of specialized agents (editor-in-chief, worldbuilder, plot architect, character designer, writer, polisher, continuity editor, genre consultant). Supports all genres (xianxia, urban, sci-fi, fantasy, romance, mystery, historical) with a complete pipeline from worldbuilding to final draft, designed for 800k+ word novels. Use when: writing a novel, creating web fiction, serializing a story, building a fictional world, designing characters, writing chapters, or any multi-chapter fiction creation task. Triggers: 写小说, 长篇小说, 网文, 连载小说, 创作故事, 小说大纲, 角色设计, 世界观设定, 章节写作, 小说润色, 写一部小说, 小说创作, 剧情架构."
name_cn: 小说写作大师
description_cn: 专业长篇小说创作工坊，模拟编辑部专家团队（总编、世界观架构师、剧情架构师、角色塑造师、执笔写手、润色师、连续性审核员、类型顾问）协作完成从世界观到终稿的完整流水线。支持全类型（玄幻/都市/科幻/奇幻/言情/悬疑/历史），专为80万字以上超长篇设计，包含设定圣经、剧情线追踪、伏笔管理等连贯性保障机制。
create_source: super-agent-skill-creator
---

# 小说写作大师

专业长篇小说创作工坊。通过模拟真实编辑部的专家团队协作，完成从构思到终稿的完整创作流程。

## 专家团队系统

本技能通过角色切换模拟7+1位专家协作。每位专家有独立的身份、方法论和输出规范。

| 角色 | 职责 | 主导阶段 |
|------|------|---------|
| 总编 | 统筹全局、质量裁决 | 全程 |
| 世界观架构师 | 构建世界设定 | Phase 1 |
| 剧情架构师 | 设计情节骨架与节奏 | Phase 3 |
| 角色塑造师 | 设计角色弧光与关系 | Phase 2 |
| 执笔写手 | 逐章写作 | Phase 4 |
| 文笔润色师 | 语言优化与去AI化 | Phase 4 |
| 连续性审核员 | 设定一致性守护 | Phase 4-5 |
| 类型顾问 | 类型规范建议 | 按需激活 |

**详细角色定义、方法论和输出规范**：读取 `references/expert-team.md`。

## 角色激活模板

切换专家角色时，使用以下提示词结构锚定身份：

```
═══════════════════════════════════════
  当前角色：[角色名]
  阶段：Phase [X]
═══════════════════════════════════════

身份：[一句话角色定位]
核心方法论：[参考 references/expert-team.md 中该角色的方法论]

当前任务：[具体任务描述]

输入材料：
- [列出本次任务所需的所有输入]

输出要求：
- [格式/字数/必含要素]

质量门控：
- [本阶段通过标准，参考 references/quality-checklist.md]
═══════════════════════════════════════
```

## 工作流：6阶段流水线

### Phase 0: 项目启动（总编主导）

1. 与用户确认创作需求：类型、基调、目标读者、预估篇幅、核心卖点
2. 根据类型，读取对应类型指南（见下方"类型指南导航"）
3. 撰写项目企划书，包含：
   - Logline（一句话故事概括：谁+想要什么+什么阻碍+什么代价）
   - 核心命题
   - 类型与基调
   - 篇幅规划（卷数/章数/每章字数）
   - 核心卖点
4. 总编审查：通过 quality-checklist.md 的 Phase 0 检查项
5. **门控**：企划书通过后进入 Phase 1

### Phase 1: 世界观构建（世界观架构师主导）

1. 读取 `assets/templates/setting-bible-template.md`
2. 读取 `references/expert-team.md` 中世界观架构师的方法论
3. 从核心概念出发，逐层构建：力量体系→地理→势力→历史→名词表
4. 对每个关键设定做3层自洽追问
5. **门控**：设定圣经通过总编审查（quality-checklist Phase 1），剧情架构师确认"可构建故事"

### Phase 2: 角色设计（角色塑造师主导）

1. 读取 `assets/templates/character-profile-template.md`
2. 设计主角和3-5个主要配角的完整档案
3. 设计反派（动机自洽）
4. 绘制角色关系图谱
5. 为每个重要角色编写对话风格指南
6. **门控**：角色档案通过总编审查（quality-checklist Phase 2），剧情架构师确认"角色服务于剧情"

### Phase 3: 故事架构（剧情架构师主导）

1. 读取 `assets/templates/outline-template.md`
2. 根据类型选择结构模型（参考类型指南）
3. 设计宏观结构 → 分卷概要 → 章节细纲
4. 读取 `assets/templates/chapter-outline-template.md`，逐章编写细纲
5. 建立伏笔总表和剧情线总表
6. 绘制张力曲线预览，确保无连续3章低谷
7. **门控**：大纲通过总编审查（quality-checklist Phase 3），角色塑造师确认"弧光有展现空间"

### Phase 4: 逐章写作（循环）

每章执行以下4步循环：

**Step 1 — 执笔写手写作**
- 激活执笔写手角色
- 读取 `references/chapter-crafting.md` 获取写作方法论
- 组装上下文（见"上下文管理"）
- 根据章节细纲写作，输出章节初稿

**Step 2 — 文笔润色师润色**
- 激活润色师角色
- 按 chapter-crafting.md 的"去AI化写作"清单逐项检查
- 检查句式变化、情绪展示、对话指纹、感官描写
- 输出润色稿 + 修改说明

**Step 3 — 连续性审核员检查**
- 激活连续性审核员角色
- 读取 `references/continuity-management.md`
- 检查设定一致性、角色状态、伏笔、时间线、OOC
- 更新角色状态表和剧情线追踪表
- 输出一致性审查报告（🔴致命/🟡警告/🔵建议）
- 🔴致命问题必须修复后重走 Step 1-3

**Step 4 — 总编验收**
- 检查 quality-checklist.md 的 Phase 4 项
- 通过 → 章节定稿，进入下一章
- 不通过 → 标注修改方向，回到对应 Step

**每5章阶段审查**：连续性审核员+总编执行 quality-checklist 的 4c 阶段审查。

**每卷卷末审查**：全团队执行 continuity-management.md 的卷末审查清单。

### Phase 5: 终审（全团队）

1. 连续性审核员：全书连贯性扫描（伏笔100%回收、时间线无矛盾）
2. 剧情架构师：节奏曲线审查、每卷高潮质量递进
3. 文笔润色师：全书风格统一性检查
4. 总编：终审定稿（quality-checklist Phase 5）
5. 输出终稿

## 上下文管理策略

80万字+无法全量传递上下文。每个阶段工作时，按需组装压缩上下文：

**写作每章时的上下文组装**：
1. 所有已完成卷的卷摘要（每卷500-800字）
2. 当前卷的阶段摘要（每10章300-500字）
3. 最近3章的详细摘要（每章200-300字）
4. 当前章节细纲
5. 出场角色的状态快照（从角色状态表提取）
6. 本章涉及的设定圣经分区（非全文）
7. 出场角色的对话风格指南
8. 剧情线追踪表当前状态

**摘要更新规则**：
- 每章定稿后：更新最近3章详摘
- 每10章：撰写阶段摘要
- 每卷结束：撰写卷摘要

**详细管理方案**：读取 `references/continuity-management.md`。

## 类型指南导航

Phase 0 确定类型后，读取对应指南：

| 类型 | 文件 | 适用场景 |
|------|------|---------|
| 仙侠/玄幻/修仙 | `references/genre-guides/xianxia.md` | 修仙、玄幻、仙侠、洪荒 |
| 都市 | `references/genre-guides/urban.md` | 都市重生、系统、异能、职场 |
| 科幻 | `references/genre-guides/scifi.md` | 星际、末日、AI、赛博 |
| 奇幻 | `references/genre-guides/fantasy.md` | 西幻、魔法、异世界 |
| 言情 | `references/genre-guides/romance.md` | 甜宠、虐恋、古言、校园 |
| 悬疑/推理 | `references/genre-guides/mystery.md` | 推理、惊悚、悬疑 |
| 历史 | `references/genre-guides/historical.md` | 历史正剧、架空、穿越 |

如类型不在上表中，取最接近的指南作为基础，在 Phase 0 补充该类型的特殊规范。

## 输出规范

- **最终交付**：.docx 格式（按卷/章分文件或合并为单文件，由用户选择）
- **过程文件**：设定圣经、角色档案、大纲、章节细纲、追踪表等存储在项目工作目录的 `.temp/` 下
- **字数统计**：每章定稿后报告字数和累计进度

## 参考文件索引

| 文件 | 内容 | 何时读取 |
|------|------|---------|
| `references/expert-team.md` | 7+1位专家的完整定义 | Phase 0 启动时读取，全程参考 |
| `references/continuity-management.md` | 连贯性管理系统 | Phase 4 开始时读取 |
| `references/chapter-crafting.md` | 章节写作方法论 | Phase 4 每章写作时参考 |
| `references/quality-checklist.md` | 各阶段质量审核清单 | 每阶段结束时读取对应部分 |
| `references/genre-guides/*.md` | 类型创作指南 | Phase 0 确定类型后读取 |
| `assets/templates/*.md` | 设定圣经/角色/大纲/细纲模板 | 对应阶段开始时读取 |
