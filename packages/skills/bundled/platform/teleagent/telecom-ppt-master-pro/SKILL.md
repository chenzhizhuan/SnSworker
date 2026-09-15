---
name: telecom-ppt-master-pro
description: Create, modify and quality-assure China Telecom-style PowerPoint for operations analysis, business review, symposium, work deployment, advocacy training, branch/user profiles and Excel data reports. Deep-red visual system, 7 themes, 34 page templates, 12 scenario presets, native 5G template inheritance, optional local progress preview, JS/Python engines, and an engineering quality gate (task routing, machine-readable artifacts, validation scripts, smoke tests).
name_cn: 电信PPT大师v91
description_cn: 创建、原生编辑、模板复用并质检中国电信风格PPT，覆盖经营分析、业务复盘、座谈会、宣贯培训、专项汇报、营业部/用户画像及数据报表场景。深红视觉体系，7主题、34模板、12场景预设、5G原生模板继承；JS/Python双引擎，可选本地进度预览；v9.0工程化质量校验，数据可追溯、结果可校验。
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'ff5869f8-d4f0-47d2-adf1-875b3d9ce86a'
  PropagateID: 'ff5869f8-d4f0-47d2-adf1-875b3d9ce86a'
  ReservedCode1: 'e60f4a1c-7595-4a43-9ea7-df4645c4ce6b'
  ReservedCode2: 'e60f4a1c-7595-4a43-9ea7-df4645c4ce6b'
---

# 电信PPT大师 v9.0

生成电信风格PPT（中国电信标准化运营系列），基于 `视图.pptx` 的深红配色体系。
v9.0 重磅升级（工程化质量保障体系）：合并 .codex 工程版的**全套工程质量防线**——任务路由（create-new-deck / edit-native-deck / create-template-workspace）、机器可读工件链（source-manifest → requirements → slide-plan → design-lock → build-manifest → qa-report → delivery-manifest）、7道关卡、需求锁定 A/B/C 风险分级、能力诚实声明、7个校验脚本与冒烟测试。让 PPT 生成**数据可追溯、结果可校验、限制被诚实披露**，真正适合政企正式汇报与高管级材料。
v8.2 重磅升级：**python-pptx 原生底版继承**——加载官方 `电信5G原生模板1.0.pptx`，通过 slide layout `2019-004` 继承原生页眉元素（真实5G logo图片 image1.png + 原生红色方块叠块 + 原生红色横线），正文区自由排版。**告别 pptxgenjs 代码复刻页眉**（旧的 `drawTemplateHeader` 方案降级为备选）。原生继承方案产出的PPT页眉100%还原官方模板，5G logo为真实图片而非文字模拟。
v8.1 重磅升级：(1) **内置电信5G原生模板**——用户未指定底版时可选择官方模板（左上标题+5G logo+红色分隔线）；(2) **实时进度预览**——JS生成可采用 pages 模块在浏览器中展示逐页状态，环境不支持时自动降级为普通生成。
v7.2 新增双引擎架构：主引擎保持JS(pptxgenjs)+ Python辅引擎(SVG管道)，融入ppt-master(39.8k stars开源项目)的设计方法论——双轨锁定防漂、72种图像布局、三角色协作、逐页上下文投影。高端场景（座谈会封面/动画旁白/非标准画布/模板填充）可切换到Python SVG管道生成原生深度PPT。同步新增**浏览器实时预览工具**（`assets/progress-preview/`）：生成脚本接入后，用户在浏览器里实时看到每一页状态与缩略图，替换"等几十秒才知道效果"的黑盒体验。
v7.1 新增**图形布局引擎**（10种原生图形布局+智能匹配），自动识别内容逻辑推荐时间轴/流程/金字塔/循环/总分/漏斗/殿堂/垂直步骤/阶梯/价值链等图形布局，告别"方框+文字"。
v7.0 新增高管座谈会设计体系（executive-blue主题+T17-T24模板+座谈会发言体），服务于总经理座谈会/半年会/经营复盘等高管级材料场景。
v6.0 采用**五层架构**：数据智能 + 模板锚定 + 风格记忆 + 创意设计 + 精控执行。主引擎 pptxgenjs (JavaScript)，辅引擎 Python SVG管道(ppt-master)，支持7套主题、34种页面模板(T1-T16+T17-T24+T25-T34)、12种场景预设、19种+6种内容模式、完整7步工作流。

## 触发条件

当用户消息包含以下任一关键词时使用本技能:
- "电信PPT" / "电信风格PPT" / "运营PPT" / "标准化运营PPT"
- "座谈会" / "总经理座谈会" / "半年会" / "经营复盘" / "高管发言" / "发言材料" / "领导讲话材料" / "述职发言"
- "框架图" / "总视图" / "架构图PPT"
- "宣贯PPT" / "动员PPT"
- 提供Excel/markdown/图片并要求"生成PPT"
- "做PPT" / "PPT" / "幻灯片" / "汇报" / "答辩" / "课件"
- 不要仅因用户泛泛提到 PPT、课件、答辩或普通公司汇报而触发

## 核心原则

1. **风格绝对统一**: 所有PPT严格遵循 `references/style-guide.md`（通用场景）或 `references/executive-style-guide.md`（座谈会场景）中的配色、字体、形状规范
2. **文字风格统一**: 文字描述严格遵循 `references/writing-style.md` 中的句式、措辞、段式规范（含座谈会发言体）
3. **7步推荐工作流**: 需求→主题→规划→生成→QA→微调→记忆，可按任务规模合并步骤
4. **内容简洁提炼**: 每条 ≤15字，数字目标高亮（电信红主题用红色加粗，座谈会蓝主题用正绿负红双色编码），拒绝长句
5. **布局优先三栏**: 内容自然分3类时优先三栏卡片布局
6. **多主题+电信优先**: 支持7种主题，电信场景自动使用 `telecom-red`，座谈会场景自动使用 `executive-blue`
7. **自进化+风格记忆**: 每次生成后收集反馈，微调自动沉淀为记忆
8. **双引擎互补**: 日常电信场景走JS(pptxgenjs，1-3分钟)，高端设计/动画/旁白走Python(SVG管道，10-20分钟)，详见 `references/dual-engine-guide.md`
9. **实时进度预览**: 推荐使用 pages 模块结构接入 `assets/progress-preview/`，浏览器可逐页显示构建状态；宿主提供受控渲染器时显示缩略图，其他环境自动使用无缩略图模式。详见 `references/pipeline.md` §实时预览
10. **模板选择**: 用户未指定底版时，建议在 Step 2 中确认是否使用内置 `assets/电信5G原生模板1.0.pptx`（全锚定模式：所有页面统一使用页眉头部——红色方块+标题+5G logo+红线分隔；正文区在红线下自由排版）。详见 `references/template-anchoring.md` §8。
11. **原生底版继承优先**（v8.2新增）: 使用5G模板底版时，**优先采用 python-pptx 原生继承方案**（加载模板→用 `2019-004` layout 新建 slide→页眉元素由 layout 原生提供），而非 pptxgenjs 的 `drawTemplateHeader` 代码复刻方案。详见 `references/template-anchoring.md` §9。
12. **任务路由先行**（v9.0新增）: 开工前先读 `references/task-routing.md`，从 create-new-deck / edit-native-deck / create-template-workspace 三条路线中选一条主路线，只加载对应参考文件，避免盲目全量加载。
13. **数据可追溯**（v9.0新增）: 保留原始值、单位、周期、口径和来源；推导值记录公式。不编造数据、来源、实时能力、动画、旁白或已完成的视觉 QA。
14. **结果可校验**（v9.0新增）: 正式交付必须跑 `scripts/validate_output_pptx.py` 与 QA 报告校验，无法验证时诚实披露，不得把"可打开"当作"原生保真"。
15. **限制诚实披露**（v9.0新增）: 文档声称的能力不等于本机可用，以 `scripts/check_environment.py --json` 和 `references/capabilities.md` 为准。

---

## 共同边界

> 适用于所有路线与所有关卡。优先级：用户本次明确要求 > 已锁定需求 > 用户材料和模板 > 场景专项规范 > 通用默认值。

- 不得编造数据、来源、实时能力、动画、旁白或已完成的视觉 QA。
- 用户未授权联网时，不用外部资料补齐业务事实。
- 不覆盖用户原始文件；项目产物写入用户工作区，不写入 Skill 安装目录。
- 不要求用户选择 `pptxgenjs`、`python-pptx` 或 SVG；根据结果要求和环境能力自动路由。
- 只有用户明确同意"下次记住"时，才写长期偏好。
- 用户已给足信息并明确要求直接完成时，不因流程形式再确认；仅当仍存在会改变内容、口径、模板或交付物的高影响选择时才停下询问。

---

## 任务路由与质量工程（v9.0）

开工前先读 `references/task-routing.md`，从以下三条路线中**只选一条主路线**，再加载对应参考文件，避免并发加载全部 references：

| 路线 | 适用 | 必须输出 | 参考 |
|------|------|---------|------|
| `create-new-deck` | 从材料/数据/大纲创建新 Deck | PPTX、slide-plan、design-lock、QA报告 | `references/requirements-gate.md` |
| `edit-native-deck` | 修改现有 PPTX，保留母版/动画/备注/关系 | 新PPTX、change set、QA报告 | `references/task-routing.md` §原生编辑 |
| `create-template-workspace` | 把模板分析为可复用 Layout Map/设计锁/起始工程 | Layout Map、设计锁、3页样例 | `references/template-anchoring.md` |

### 机器可读工件链

完整生产流程维护以下工件（见 `references/artifact-contracts.md`），小范围原生编辑可只维护 `source-manifest` + change set + `qa-report` + `delivery-manifest`：

```text
source-manifest.json
  -> deck-requirements.json
  -> slide-plan.json
  -> design-lock.json
  -> build-manifest.json
  -> qa-report.json
  -> delivery-manifest.json
```

### 7道关卡（按风险启用）

1. **来源关卡**：盘点用户消息、附件、模板和可用环境；原始来源只读保留
2. **需求关卡**：新建/大改时读 `references/requirements-gate.md`，A/B/C 风险分级；仅 A 级未知会阻塞
3. **规划关卡**：生成 `slide-plan.json` 并运行 `scripts/validate_slide_plan.py`
4. **设计关卡**：锁定画布/主题/模板/字体/引擎/QA等级，运行 `scripts/validate_design_lock.py`
5. **生成关卡**：只用环境检查确认可用的引擎；记录输入输出哈希
6. **QA关卡**：先结构/文件→逐页视觉→Deck节奏；运行 `scripts/validate_qa_report.py`
7. **交付关卡**：交付清单披露已完成检查、失败项和未验证限制

> 用户已给足信息并明确要求直接完成时，不因流程形式再确认；只有高影响选择（内容/口径/模板/交付物）改变时才停下询问。

---

## 五层架构（v6.0）

| 层级 | 名称 | 核心能力 | 参考文件 |
|------|------|---------|---------|
| Layer 1 | 数据智能 | Excel解析→语义理解→自动点评→Table Contract精准落位 | `references/data-intelligence.md` |
| Layer 2 | 模板锚定 | 用户模板→Layout Map解剖→Template Contract→框架走模板+内容走程序 | `references/template-anchoring.md` |
| Layer 3 | 风格记忆 | 四文件三级记忆+增量沉淀+权重衰减 | `references/style-memory.md` |
| Layer 4 | 创意设计 | 设计方向推荐(2-3选1)+5场景设计库 | `references/creative-design.md` |
| Layer 5 | 精控执行 | 自然语言→格式操作映射+微调记忆闭环 | `references/refinement-mapping.md` |

---

## 执行流程（7步工作流）

### Step 1: 启动准备 + 需求解析

1. 读取以下 references 文件获取最新规范：
   - `references/design-system.md` — **v8.0 设计 token 体系（权威来源）**：颜色色阶、字体配对、间距系统、表面材质层级
   - `references/style-guide.md` — 视觉设计规范（通用场景，telecom-red）
   - `references/executive-style-guide.md` — 高管座谈会设计规范（v7.0，executive-blue）
   - `references/writing-style.md` — 文字描述规范（含§九座谈会发言体）
   - `references/themes.md` — 主题完整token化配色体系（7套，含10级色阶+字体配对）
   - `references/content-patterns.md` — 内容组织模式 + 模板映射（含模式16-19 + 图形布局推荐）
   - `references/graphic-layout-guide.md` — **v7.1 图形布局智能匹配指南**（关键词矩阵、结构特征、10种布局参数格式）
   - `references/evolution-log.md` — 已学会的能力和已知局限
   - `references/presets.md` — 场景预设（含executive-symposium）
   - `references/data-intelligence.md` — 数据智能层规范（v6.0）
   - `references/template-anchoring.md` — 模板锚定层规范（v6.0）
   - `references/creative-design.md` — 创意设计层规范（v6.0）
   - `references/refinement-mapping.md` — 精控执行层规范（v6.0）

2. 读取风格记忆文件（v6.0 新增）：
   - `memory/CORPORATE_SPEC.md` — 企业规范（强制）
   - `memory/WRITING_STYLE.md` — 写作风格
   - `memory/LAYOUT_HABITS.md` — 版面习惯
   - `memory/REFINEMENT_LOG.md` — 微调记录

3. 根据输入类型选择解析方式：

| 输入类型 | 解析工具 | 关键提取 | v6.0增强 |
|---|---|---|---|
| Excel (.xlsx) | pandas / openpyxl | 层级关系、量化数据 | **Layer 1**: 自动数据点评+Table Contract |
| Markdown (.md) | 直接读取 | H1/H2/H3层级、表格、要点 | — |
| 图片 (.png/.jpg) | `image_understanding` | 文字内容、层级关系、配色、箭头流程 | — |
| 现有PPT (.pptx) | `python -m markitdown` | 全部文字内容 | **Layer 2**: 可作为模板解剖 |
| 文字描述 | 直接读取 | 用户意图、关键信息 | — |

4. 对提取的原始内容进行精简提炼：
   - 删除冗余修饰词，保留核心语义
   - 每条目控制在 15 字以内
   - 标记所有量化目标（含 `≥`/`%`/数字的句子）
   - 识别天然的结构层级（大类→子类→条目）
   - 判断适用内容模式（参见 content-patterns.md 的15种+6种Excel驱动模式）
   - **v7.1 图形布局识别**：对每页内容进行结构分析，识别关键词和结构特征，参考 `references/graphic-layout-guide.md` 的关键词检测矩阵和结构特征加分规则，推荐最匹配的图形布局（时间轴/流程/金字塔/循环/总分/漏斗/殿堂/垂直步骤/阶梯/价值链）。当内容逻辑明确匹配某种图形布局时，优先使用图形布局模板（T25-T34）替代默认卡片式模板

5. **Excel 智能处理**（Layer 1 · v6.0 新增）：
   - 识别数据结构和层级关系
   - 自动生成数据摘要并确认
   - 自动生成数据点评
   - 填写 Table Contract
   - 参考 `assets/excel-data-utils.js` 中的格式化函数

### Step 2: 模板 + 主题 + 预设 + 创意方向选择

#### 模板底版选择（v8.1 新增 · v8.2 增强）

> 用户未指定底版时，建议一次性确认是否采用内置模板；已有明确选择时直接沿用。

```
是否使用电信5G原生模板作为PPT底版？

- 使用模板：每页左上角显示标题（红色方块装饰+蓝色副标题），右上角5G logo，红色横线分隔页眉与正文区，正文区纯白自由排版。无传统导航栏/页脚。
- 不使用模板：使用电信PPT大师默认布局（深红通栏导航+底部红色横幅页脚+红色竖条标题区）。
```

用户确认使用模板后，**v8.2 起需进一步选择实现方案**（默认推荐原生继承）：

| 实现方案 | 引擎 | 页眉来源 | 推荐度 | 适用场景 |
|---------|------|---------|--------|---------|
| **原生继承（v8.2 推荐）** | python-pptx | slide layout `2019-004` 原生元素（真实5G logo图片+原生方块+原生红线） | ★★★★★ | 需100%还原官方模板、5G logo需真实图片 |
| 代码复刻（v8.1 备选） | pptxgenjs | `drawTemplateHeader()` 代码绘制（文字模拟5G logo） | ★★★☆☆ | 需实时预览、纯JS工作流、无python-pptx环境 |

选择对照：

| 选择 | 模式 | 实现方案 | 页眉函数/方式 | 安全区域 | 页脚 |
|------|------|---------|---------|---------|------|
| **使用模板·原生继承** | 全锚定 | python-pptx + `2019-004` layout | layout原生继承 + `add_header_title(s, prefix, suffix)` 补标题文字 | y=1.15"~7.35" | 无（正文直达底部） |
| **使用模板·代码复刻** | 全锚定 | pptxgenjs | `drawTemplateHeader(s, ctx, prefix, suffix)` | y=1.15"~7.35" | 无（正文直达底部） |
| **不使用模板** | 标准 | pptxgenjs | `addTelecomNav` + `addTitle` | y=0.55"~7.05" | `addTelecomFooter` |

模板详细 Layout Map 和代码骨架见 `references/template-anchoring.md` §8（代码复刻）与 §9（原生继承·v8.2）。

#### 主题选择

| 用户说 | 使用主题 |
|--------|----------|
| "电信"/"电信风格"/"运营PPT"/"标准化运营" | `telecom-red`（默认） |
| "座谈会"/"半年会"/"经营复盘"/"高管发言"/"发言材料" | `executive-blue`（v7.0） |
| "毕业答辩"/"学术汇报" | `academic-red` |
| "公司汇报"/"投资人 pitch"/"董事会" | `business-navy` |
| "AI/ML/技术分享"/"产品发布"(科技) | `tech-cyan` |
| "培训"/"教学"/"新员工" | `warm-amber` |
| "极简"/"设计作品集"/"艺术展" | `minimal-mono` |
| 提供品牌色 hex | 使用品牌色定制器 + 最近基础主题 |
| 没有偏好 | `telecom-red`（电信PPT大师默认） |

详细主题配色参见 `references/themes.md`。

#### 预设选择

| 场景 | 预设 | 推荐长度 |
|------|------|----------|
| **总经理座谈会/半年会/经营复盘/高管发言** | `executive-symposium`（v7.0） | 15-25页 |
| 电信业务报告/运营分析/宣贯材料 | `telecom-report`（默认） | 8-16页 |
| 经营分析会 | `business-analysis`（v6.0） | 8-14页 |
| 工作布置会 | `work-deployment`（v6.0） | 8-12页 |
| 专项汇报 | `special-report`（v6.0） | 8-14页 |
| 述职报告 | `performance-review`（v6.0） | 10-16页 |
| 对标分析 | `benchmarking`（v6.0） | 8-12页 |
| 学术会议口头报告 | `academic-oral` | 10-14页 |
| 毕业论文答辩 | `academic-defense` | 18-28页 |
| 企业汇报/经营分析 | `business-report` | 8-14页 |
| 培训课件/课程 | `training-courseware` | 12-24页 |
| 简短快速汇报 | `quick-routine` | 6-10页 |

详细预设规则参见 `references/presets.md`。

#### 创意方向推荐（Layer 4 · v6.0 新增）

当场景匹配5种创意预设时，先推荐2-3个设计方向让用户选择：

```
🎨 PPT设计方案推荐

场景识别：经营分析会

方案A · 仪表盘式：顶部KPI→中部图表→底部发现（8-10页）
方案B · 对比发现式：左右对比+差异高亮（10-12页）
方案C · 叙事线式：发现→分析→策略（12-14页）

请选择方案（A/B/C），或说明你的偏好。
```

详见 `references/creative-design.md`。

#### 模板锚定准备（Layer 2 · v6.0 新增）

当用户提供了 .pptx 模板时：

1. 运行 `python assets/template-analyzer.py --input 模板.pptx --output layouts/模板.json`
2. 生成 Layout Map 并向用户确认
3. 确定锚定模式（全锚定/半锚定/灵感锚定）

详见 `references/template-anchoring.md`。

#### 方案确认

**将选定的主题、预设、页数规划、创意方向展示给用户确认后再进入 Step 3。**

### Step 3: Slide Contract 规划

填写 Slide Contract 表格（参见 `references/slide-contract.md`）：

| Slide | Role | Claim-or-Topic | Proof Object | Template | Layout | Anchors | Source | Notes |
|-------|------|----------------|--------------|----------|--------|---------|--------|-------|

**Table Contract**（含表格数据时填写，参见 `slide-contract.md` §Table Contract）：

| TableID | DataSource | Position | ColSpec | RowSpec | ConditionFormat | AutoComment |
|---------|-----------|----------|---------|---------|----------------|-------------|

**Pass/Fail 规则**（用于生成前质量校验）：
- 每页只有一个主要角色
- 每个内容页回答一个主要问题/表达一个主要信息
- 每个内容页最多一个主要证明对象
- Template 必须是 T1-T16、ED# + T# 或 `T# + local variant`
- 使用模板锚定时 Layout 和 Anchors 必须对应 Layout Map 中的有效条目
- Source 不能为空
- 无连续3页相同模板结构

**方案确认**

复杂或高风险改版时展示 Slide Contract + Table Contract 供用户确认；常规任务可按已确认需求直接进入生成。

### Step 4: 代码生成

#### 技术栈

- **引擎**: pptxgenjs (JavaScript)，统一使用
- **画布**: `pres.layout = 'LAYOUT_WIDE'` (13.33"×7.50", 16:9)
- **字体**: `Microsoft YaHei`（中文）/ `Arial`（英文）

#### 启动模板选择

| 主题 | 启动模板 | 说明 |
|------|---------|------|
| `telecom-red` | `assets/telecom-boilerplate.js` | 含电信特有导航/页脚/阴影/装饰线 |
| 其他5种主题 | `assets/boilerplate.js` | 通用多主题启动模板 |

参考 `assets/example_minimal.js` 获取最小完整示例。
参考 `assets/excel-data-utils.js` 获取数据格式化和表格生成工具（v6.0）。

#### 版面安全边界

| 参数 | 通用主题 | 电信主题 |
|------|---------|---------|
| 有效内容区 | y=1.85"~7.10" | y=0.55"~7.05" |
| 顶部保留区 | 0~1.85" | 0~0.52" |
| 底部保留区 | 7.10~7.50" | 7.05~7.50" |

详细约束参见 `references/style-guide.md` §4.5。

#### 设计规范（v8.0 Token 化配色 · 电信主题）

- **配色使用 token 体系**：禁止硬编码 hex 值，必须使用 `C.brand[500]`、`C.neutral[800]` 等语义 token
- 主色: `C.brand[500]`（#C00000），数字目标必须红色加粗（使用 `C.brand[600]` 强调）
- 卡片: 圆角 0.08-0.12"，底板色 `C.brand[100]`（浅粉），描边 `C.border`，阴影 `C.elevation.card`
- 标题栏: `C.surfaceHeader`（浅粉底板）+ `C.brand[600]`（深红加粗文字）
- 正文色: `C.neutral[800]`（#262626 替代纯黑，更柔和）
- 辅助灰: `C.neutral[500]`（#888888）
- 红色竖条装饰标记条目层级（颜色 `C.brand[600]`）
- 黄色高亮 `C.highlight` 用于数据/重点底色
- 最小字号 ≥ 7pt，正文 11pt（v8.0 统一为 text-base），标题 14-16pt
- 字体配对: 中文 → `F.cn`（微软雅黑），英文/数字 → `F.number`（Arial），大标题可升级到 `F.display`
- 数字数值使用 `F.number` 确保等宽对齐（tabular-nums）
- 使用 `addTelecomNav`/`addTelecomFooter` 替代默认导航/页脚
- 使用 `fmtNumber(text, withBg)` 格式化数字目标
- 使用 `drawTelecomCard` 生成电信风格卡片，阴影参数用 `C.elevation.card`

#### 页面模板（T1-T34）

参见 `references/page-templates.md`，包含34种模板的完整JS代码。
- T1-T16：通用模板（封面/目录/章节分隔/概念定义/主图展示/两栏对比/三卡片行/2×2矩阵/图表数据/表格/流程管道/时间线/KPI指标/引用高亮/总结/致谢Q&A）
- T17-T24（v7.0新增）：座谈会高级模板（座谈会封面/目录/结论先行数据页/分公司画像2×2网格/三组纵向分栏/多面板仪表盘/四象限矩阵/工作部署页）
- T25-T34（v7.1新增）：**图形布局模板**（时间轴/流程箭头/金字塔/循环图/总分树形/漏斗图/殿堂框架/垂直步骤/阶梯进化/价值链），全部使用pptxgenjs原生形状，PowerPoint中完全可编辑。调用 `assets/graphic-layouts.js` 的 `create(pres).drawXxx()` 系列函数生成，支持智能匹配 `recommendLayout()` 自动推荐最合适的布局

#### 文件输出

- 输出到用户工作空间
- 命名格式：`{主题描述}.pptx`

#### 实时进度预览（v7.2 新增，v8.3 安全收敛）

> 推荐使用 pages 模块结构获得逐页构建状态。宿主环境提供受控渲染器时可同步展示缩略图；否则自动降级为无缩略图预览，不影响PPT生成。

生成代码时优先采用 pages 模块结构并接入 `assets/progress-preview/`，让用户在浏览器里看到逐页构建状态；简单任务或受限环境可直接生成并执行常规QA。

| 普通生成模式 | pages 模块预览模式 |
|---|---|
| `pres.addSlide()` × N → `writeFile()` | `module.exports = { deckMeta, setup, buildSlides }` |
| 跑完才知道对错 | 每页状态 + 缩略图实时可见 |
| 用户只能干等 | 用户能随时叫停微调 |

**接入三步**：
1. `module.exports = { deckMeta, setup, buildSlides }` — 导出三项
2. `if (require.main === module) run(...)` — 守卫递归
3. 每个 `buildSlides[i](pres, ctx)` 独立可调用，不依赖闭包 mutable 状态

完整改造示例和约束见 `references/pipeline.md` §「实时预览」。
工具架构、文件清单、排错表见 `assets/progress-preview/README.md`。

> CI、批处理、headless 服务器或无受控渲染器环境可直接生成并走常规 PPTX→PDF→PNG QA。

### Step 5: QA 双重检查

#### 5.1 逐页 QA（10项，v6.0 扩展）

参见 `references/qa-checklist.md`，对每个渲染后的页面检查：

1. 内容在安全区域内
2. 无裁剪或溢出文字
3. 导航栏反映当前章节
4. 页脚显示正确页码
5. 主题色使用一致
6. 图片清晰且尺寸合适
7. 视觉层级清晰
8. **模板锚定一致性**（v6.0，使用模板时检查）
9. **表格精准落位**（v6.0，含表格时检查）
10. **微调指令精准执行**（v6.0，微调后检查）

**任何一项失败，按 `references/troubleshooting.md` 修复并重新渲染。**

#### 5.2 Deck QA

参见 `references/deck-qa-checklist.md`，全 deck 级检查：

- 至少使用4种宏观版式（10页deck）
- 无连续3页相同结构
- 每个章节有锚点页
- 结果页有 takeaway
- 方法页有信息流/流程
- 总结闭合论述

**电信额外检查**：数字目标红色加粗、三栏均衡、文字≤15字、无蓝色大面积主色。

#### 5.3 生成后自检

```
□ 内容未超出安全区域
□ 同页内无形状重叠
□ 多条目均分高度一致
□ 文字未贴边
□ 文字 ≥ 7pt
□ 模板锚定位置精确（如使用）
□ Table Contract 条件格式已应用（如含表格）
```

**全部通过后进入 Step 6。**

#### 5.4 校验闭环（v9.0 新增）

正式交付必须通过以下机器校验（不是可选）：

```powershell
python scripts/validate_output_pptx.py output.pptx
python scripts/validate_qa_report.py qa-report.json
```

- 生成 `slide-plan.json` / `design-lock.json` 时同步跑 `validate_slide_plan.py` / `validate_design_lock.py`
- 视觉 QA 必须基于真实渲染图（PPTX→PDF→PNG），脚本不能替代目视判断
- 无法渲染时只能声明「文件/结构检查通过，视觉 QA 未完成」，并写入 `qa-report.json` 的 `limitations`
- 交付至少说明：PPTX 路径、使用的模板/主题、已完成的 QA、未验证限制

### Step 6: 微调执行（Layer 5 · v6.0 新增）

生成完成后询问用户微调需求：

> 有没有需要调整的地方？比如字体、颜色、布局、数据高亮等？

用户提出微调时：

1. 按 `refinement-mapping.md` 的映射表解析微调指令
2. 精确定位代码中的修改点
3. 修改并重新渲染
4. 执行 QA 检查 10（微调精准执行）
5. 微调记录写入 `memory/REFINEMENT_LOG.md`
6. 同类微调达3次时自动升级为固定规范

### Step 7: 记忆沉淀（Layer 3 · v6.0 新增）

将本次交互中的风格偏好沉淀到记忆文件：

| 沉淀类型 | 写入目标 | 条件 |
|----------|---------|------|
| 微调记录 | `memory/REFINEMENT_LOG.md` | 每次微调后 |
| 版面习惯 | `memory/LAYOUT_HABITS.md` | 微调升级 |
| 写作风格 | `memory/WRITING_STYLE.md` | 用户口头偏好 |
| 企业规范 | `memory/CORPORATE_SPEC.md` | 用户提供模板/规范 |
| 已学会的能力 | `references/evolution-log.md` | 新模式/修复/新增 |

询问用户：
> 这次生成有没有需要记住的偏好？下次直接应用？

---

## 快速参考

### 配色速查

#### telecom-red（默认主题，来自 design-system.md + themes.md）

```
品牌色阶: brand[50]=#FFF5F5 → brand[500]=#C00000 → brand[900]=#4D0004
金色色阶: accent[50]=#FFFCE0 → accent[400]=#FFD700 → accent[900]=#605000
灰度色阶: neutral[50]=#FAFAFA → neutral[500]=#888888 → neutral[800]=#262626

语义Token:
底板: C.surface / 卡片底: C.brand[100] / 标题栏: C.surfaceHeader
正文: C.neutral[800] / 辅助: C.neutral[500] / 描边: C.border / 高亮: C.highlight
字体: F.cn(微软雅黑) + F.number(Arial数据) + F.display(大标题)
```

#### executive-blue（座谈会主题，来自 design-system.md + executive-style-guide.md）

```text
品牌蓝色阶: brand[50]=#F0F7FD → brand[500]=#0070C0 → brand[900]=#002050
红色色阶: accent[50]=#FFF0F0 → accent[500]=#C00000 → accent[900]=#4D0004
绿色色阶: positive[50]=#F0FDF4 → positive[500]=#16A34A → positive[900]=#052E16

语义Token:
底板: C.surface / 卡片底: C.white / 标题栏: C.surfaceHeader(#E8F0F8)
正文: C.neutral[800] / 辅助: C.neutral[500] / 达标绿: C.positive[500] / 达标浅底: C.positive[100]
导航: 蓝色通栏 C.brand[500]  /  页脚: 浅灰横线  /  结论条: 蓝底白字
```

### 文件结构

```text
telecom-ppt-master/
├── SKILL.md                          # 本文件（技能入口）
├── assets/
│   ├── boilerplate.js                # 通用多主题启动模板
│   ├── telecom-boilerplate.js        # 电信风格专用启动模板（v8.0 Token体系）
│   ├── example_minimal.js            # 最小完整示例（5页）
│   ├── excel-data-utils.js           # Excel数据工具函数库（v6.0）
│   ├── graphic-layouts.js            # 图形布局引擎库（v7.1，10种图形布局+智能匹配）
│   ├── template-analyzer.py          # PPT模板解剖器（v9.0·v2 hash-aware + --sample-slides）
│   ├── telecom-ppt-master-icon.png    # Agent 图标（v9.0）
│   ├── progress-preview/             # 实时预览工具（v7.2，浏览器可视化生成进度）
│   │   ├── server.js                 # 本地 Web 服务器（HTTP+SSE+静态服务，默认端口51720）
│   │   ├── reporter.js               # 进度上报器（生成脚本调用的HTTP客户端）
│   │   ├── runner.js                 # 一站式入口：启动server+构建+调度渲染
│   │   ├── render-single.js          # 旧版兼容入口（不执行系统命令）
│   │   ├── render-worker.ps1      # 渲染工作器（v9.0 可执行版）
│   │   ├── gen_demo.js               # 示例生成脚本（5页电信红deck）
│   │   ├── lib/themes.js             # telecom-red主题+helpers
│   │   ├── public/                   # 前端三件套（index.html + style.css + app.js）
│   │   └── README.md                 # 完整架构图/文件清单/排错表
│   ├── examples/                     # 示例脚本（v9.0）
│   │   ├── build_fttr_on_template.py # FTTR培训12页示例（原生页眉继承）
│   │   └── template_deck_spec.json     # 模板构建 spec 示例
│   ├── 电信5G原生模板1.0.pptx           # v8.2 原生继承方案底版（1 master + 12 layouts，关键layout「2019-004」含原生页眉）
│   ├── 电信5G原生模板.pptx             # v8.1 内置模板（代码复刻方案参考）
│   ├── 底版2.pptx                    # [参考资产] 原python-pptx底版
│   └── view-template.pptx           # [参考资产] 视图.pptx原始模板
├── layouts/                          # Layout Map 存储（v6.0）
│   └── {模板描述}.json
├── memory/                           # 风格记忆文件（v6.0）
│   ├── WRITING_STYLE.md              # 写作风格
│   ├── CORPORATE_SPEC.md             # 企业规范
│   ├── LAYOUT_HABITS.md              # 版面习惯
│   └── REFINEMENT_LOG.md             # 微调记录
├── references/
│   ├── design-system.md             # v8.0 设计token体系（权威来源·融合open-design）
│   ├── style-guide.md               # 视觉设计规范（通用场景，telecom-red）
│   ├── executive-style-guide.md     # 高管座谈会设计规范（v7.0，executive-blue）
│   ├── writing-style.md             # 文字描述规范（v2.0，含§九座谈会发言体）
│   ├── content-patterns.md           # 内容组织模式+模板映射（v7.0，含模式16-19）
│   ├── data-intelligence.md         # 数据智能层规范（v6.0）
│   ├── template-anchoring.md        # 模板锚定层规范（v6.0）
│   ├── style-memory.md              # 风格记忆层规范（v6.0）
│   ├── creative-design.md           # 创意设计层规范（v6.0）
│   ├── refinement-mapping.md        # 精控执行层规范（v6.0）
│   ├── evolution-log.md             # 迭代进化日志（v7.0）
│   ├── themes.md                    # 7套主题配色（含executive-blue）
│   ├── presets.md                   # 7+5个场景预设（含executive-symposium）
│   ├── page-templates.md            # 34种页面模板(T1-T34)
│   ├── graphic-layout-guide.md      # 图形布局智能匹配指南（v7.1）
│   ├── slide-contract.md            # Slide/Table/Template Contract规则
│   ├── task-routing.md              # 任务路由（v9.0）
│   ├── requirements-gate.md         # 需求锁定关卡（v9.0）
│   ├── artifact-contracts.md        # 机器可读工件合同（v9.0）
│   ├── capabilities.md              # 能力诚实声明（v9.0）
│   ├── pipeline.md                  # pptxgenjs配置管道
│   ├── qa-checklist.md              # 10项逐页QA检查
│   ├── deck-qa-checklist.md         # Deck级QA检查
│   ├── troubleshooting.md           # 排错指南
│   ├── dual-engine-guide.md         # 双引擎使用指南（v7.2）
│   └── ppt-master-design-insights.md # ppt-master设计方法论（v7.2）
├── python-pipeline/                  # Python SVG辅引擎（v7.2）
│   └── README.md                    # Python管道设置与使用指南
├── scripts/                          # 工程化脚本（v9.0）
│   ├── build_on_template.py          # python-pptx 参数化模板构建器（--template/--layout/--spec/--output/--dry-run）
│   ├── check_environment.py          # 环境能力探测（--json）
│   ├── validate_requirements.py      # 需求锁定校验
│   ├── validate_slide_plan.py        # Slide Plan 校验
│   ├── validate_design_lock.py       # 设计锁校验
│   ├── validate_output_pptx.py       # 输出PPTX文件级校验
│   ├── validate_qa_report.py         # QA报告校验
│   └── validate_integrity.py         # Skill 完整性校验
├── tests/                            # 冒烟测试（v9.0）
│   ├── run_smoke.py                  # 确定性回归测试入口
│   └── fixtures/                     # 测试夹具 JSON
├── agents/
│   └── openai.yaml                   # Agent 界面配置（v9.0）
└── python-pipeline/                  # Python SVG辅引擎（v7.2）
    └── README.md                     # Python管道设置与使用指南
```

### 关键差异：三种电信场景主题对比

| 维度 | telecom-red（默认） | executive-blue（v7.0座谈会） | 通用主题 |
|------|----------------------|------------------------------|---------|
| 适用场景 | 运营分析/宣贯材料/通报 | 总经理座谈会/半年会/经营复盘 | 答辩/培训/汇报 |
| 主色 | 电信深红 #C00000 | 电信蓝 #0070C0 | 按主题 |
| 强调色 | 金色 #FFD700 | 电信红 #C00000（异常/负面） | 按主题 |
| 启动模板 | telecom-boilerplate.js | telecom-boilerplate.js (executive helper) | boilerplate.js |
| 导航 | 深红通栏 h=0.52" | 蓝色通栏 h=0.50"+模块进度标签 | 主色条 h=0.5" |
| 页脚 | 深红横幅白字 | 浅灰横线+灰字 | 灰色底栏 |
| 安全区域 | y=0.55~7.05" | y=0.55~7.10" | y=1.85~7.1" |
| 卡片风格 | 浅粉填充+浅红描边+红竖条 | 白色填充+浅蓝灰描边 | 白底+灰描边 |
| 数字格式 | fmtNumber() 红色加粗+黄底 | fmtExecutiveNumber() 正绿负红双色 | 默认加粗 |
| 结论条 | 无 | 蓝底白字加粗（标题区下方） | 无 |
| 阴影 | 轻阴影 blur=5 | 轻阴影 blur=5 | 标准阴影 blur=8 |
| 文字风格 | writing-style.md 电信体 | writing-style.md §九座谈会发言体 | 默认风格 |
| 设计规范 | style-guide.md | executive-style-guide.md | style-guide.md |

---

## 技术建议与安全边界（v8.3）

- **pages 模块 + 实时进度预览（JS引擎）**：复杂 JS 项目推荐写成 `module.exports = { deckMeta, setup, buildSlides }` 结构，通过 `run()` 接入 `assets/progress-preview/runner.js`；简单或受限环境可直接生成。
- **模板选择**：用户未明确底版时，建议在 Step 2 中确认是否使用内置 `assets/电信5G原生模板1.0.pptx`（页眉头部：红色方块+标题+5G logo+红线）。
- **原生继承优先**（v8.2新增）：用户选择使用5G模板底版时，**默认采用 python-pptx 原生继承方案**（加载1.0模板→`2019-004` layout新建slide→页眉原生继承）。仅当用户明确需要实时预览或纯JS工作流时，才降级使用 pptxgenjs `drawTemplateHeader` 代码复刻方案。
- **安全边界**（v8.3 加固，上架审核修复）：本地预览仅绑定回环地址；缩略图缓存目录 `CACHE_DIR` 在 server 启动时一次性锁定并强制限定在技能目录内（`--cache-dir` 越界自动回退），**运行期间不可被客户端改写**——`/api/config` 已从可改写 POST 改为只读 GET，杜绝把缓存目录指向任意系统目录的越权目录穿越；`/cache/*` 与静态文件路由用 `isWithin` + `safeJoin` 双重校验，封堵 `..`、`..\`、盘符穿越；CORS 收紧为 `null`（仅本地）+ `X-Content-Type-Options: nosniff`；仅放行 GET/POST，其余 405。缩略图渲染仅通过宿主提供的受控适配器完成。修改 server/runner 后必须跑 `node --check` 语法校验并实测穿越读系统文件被 404 拦截。
- **唯一例外**：CI 环境、无浏览器/无 PowerPoint 的 headless 服务器。

---

## 能力诚实声明（v9.0）

文档声称不等于本机可用。开工前运行 `python scripts/check_environment.py --json` 探测实际能力，再按 `references/capabilities.md` 的状态口径路由：

| 状态 | 含义 |
|------|------|
| `stable` | Skill 自带确定性实现并有回归测试 |
| `stable-guidance` | 规范稳定，具体页面由项目代码实现 |
| `environment-dependent` | 依赖本机软件（PowerPoint/Node/渲染器） |
| `external` | 需要 Skill 外部组件，不得假装内置 |
| `agent-review` | 需基于可见工件判断，不能只靠结构脚本 |

- **pptxgenjs 新建 Deck**：需 Node.js + pptxgenjs
- **python-pptx 模板起始构建**：需 `pptx` 库，内置5G模板验证5种基础页型
- **PowerPoint COM 渲染/编辑**：依赖本机安装的 PowerPoint，不跨平台保证
- **原生动画/旁白/SmartArt 无损编辑**：需 PowerPoint 自动化或最小 OOXML，`python-pptx` 不保证

能力判定以 `check_environment.py` 实机结果为准，不以文档声明为准。

---

## 双引擎架构（v7.2）

### 引擎选择

| 场景 | 引擎 | 理由 |
|------|------|------|
| 电信业务报告/运营分析/宣贯 | **JS (pptxgenjs)** 默认 | 快速、内容组织强、数据智能成熟 |
| 总经理座谈会/半年会封面设计 | **Python (SVG)** | 高设计感、原生深度 |
| 需要幻灯片切换动画/元素入场动画 | **Python (SVG)** | JS引擎动画能力弱 |
| 需要演讲者备注→语音旁白 | **Python (SVG)** | JS引擎不支持 |
| 非16:9画布（小红书/朋友圈/海报） | **Python (SVG)** | 支持8种画布格式 |
| 已有.pptx模板填充内容 | **Python (SVG)** | 原生模板填充工作流 |
| 数据驱动表格/图表密集型 | **JS (pptxgenjs)** | 数据智能层成熟 |

详细决策树和配置指南见 `references/dual-engine-guide.md`。

### 设计方法论融入（来自 ppt-master）

从 ppt-master (hugohe3, GitHub 39.8k stars, MIT) 提取了以下不依赖SVG管道的设计理念：

- **双轨锁定**: design_spec(人类意图) + lock.json(机器约束)，防长PPT颜色/字体漂移
- **逐页上下文投影**: 每页生成前注入全局锁+前一页节奏+图表映射
- **72种图像布局**: 翻译为page-templates.md补充，反"AI默认左图右文"
- **三角色协作**: 策略师→设计师→QA工程师，减少上下文混乱
- **pptxgenjs能力边界表**: 明确什么能做/需要变通/做不到

详见 `references/ppt-master-design-insights.md`。

Python辅引擎模块位于 `python-pipeline/`，源码位于 `.temp/ppt-master-source/`。

---

## 自进化机制

v7.2 起自进化升级为**八层架构**：v6.0五层 + 高管座谈会设计体系 + 图形布局引擎 + 双引擎架构：

1. **每次生成后**: 自动收集用户反馈，记录新模式/新偏好/修复项
2. **每次启动时**: 读取进化日志 + 风格记忆文件 + executive-style-guide.md，应用已学会的能力
3. **微调闭环**: 微调→记录→3次升级→固定规范（Layer 5 → Layer 3）
4. **模板沉淀**: 用户模板→Layout Map→企业规范（Layer 2 → Layer 3）
5. **座谈会场景自动触发**: 关键词匹配→executive-blue主题+executive-symposium预设+T17-T24模板
6. **图形布局自动推荐**（v7.1）: 内容结构分析→关键词+结构特征匹配→recommendLayout()→T25-T34图形布局模板，告别"方框+文字"
7. **双引擎智能切换**（v7.2）: 日常电信场景→JS引擎；高端设计/动画/旁白→Python引擎；封面JS+正文Python混合使用
8. **实时进度预览**（v7.2新增，v8.3安全收敛）: 推荐用 pages 模块接入 `assets/progress-preview/`，浏览器实时显示每页状态；缩略图由宿主受控适配器提供
9. **模板选择**（v8.1新增）: 用户未指定底版时确认是否使用内置 `assets/电信5G原生模板1.0.pptx`，全锚定模式统一页眉
10. **原生底版继承优先**（v8.2新增）: 使用5G模板底版时默认采用 python-pptx 原生继承方案（layout 2019-004 继承真实5G logo图片+原生方块+原生红线），pptxgenjs代码复刻方案降为备选
11. **手动触发**: 用户说"更新电信PPT技能" + 描述新需求
12. **工程化校验闭环**（v9.0）: 修改 Skill 后跑 `scripts/validate_integrity.py` + `tests/run_smoke.py`，对 JS 做语法检查、对 Python 做编译检查，并生成至少一个 3 页最小 Deck 验证
13. **能力诚实声明**（v9.0）: 新能力先写入 `references/capabilities.md` 并标状态，不得在文档中虚报本机不可用能力
14. **新规则单文件落点**（v9.0）: 新规则只进入一个权威文件，其他位置用链接引用，避免多文件漂移

迭代内容类型:
- 新配色方案
- 新布局模式
- 新内容类型（图表/封面/过渡页等）
- 风格偏好调整（字号/间距/圆角等）
- 修复已知问题
- 新主题/预设/模板
- 用户微调习惯沉淀

下次生成PPT时会自动读取最新的进化日志、风格记忆和布局习惯，确保越用越精准。

---

## 稳定约束

以下为跨场景统一约束，任何主题/模板/引擎不得违背：

- 默认 16:9 画布为 13.333 × 7.5 英寸；其他比例需明确记录。
- 中文优先微软雅黑（`F.cn`），英文和数字 Arial（`F.number`）；缺失字体时记录回退。
- 新 JS 使用语义 token（如 `C.brand[500]`），不得新增 `C.primary` 等旧别名用法。
- `telecom-red` 主色为 `#C00000`；颜色不能作为正负或风险的唯一表达手段。
- 默认电信红正文安全区 y=0.55-7.05；内置 5G 模板按 Layout Map 锚定，不套用默认安全区。
- T25-T34 优先使用 `assets/graphic-layouts.js` 的可编辑原生形状。
- 新规则只进入一个权威文件，其他位置用链接引用，避免多文件漂移。