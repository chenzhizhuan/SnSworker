---
name: 标书编写
description: 标书编写技能。Use when drafting bid proposal content, including 技术方案编写, 商务文件编写, 标书正文起草, 章节大纲设计, 评分点响应, 标书风格调整, or turning a response matrix into proposal prose. Triggers on 标书编写, 编写标书, 标书正文, 技术方案编写, 商务文件编写, 评分点响应, 根据响应矩阵写标书, 投标文件正文. Covers outline design, section drafting, style matching, and self-review before handoff to compliance reviewer.
metadata:
  tabtin:
    category: writing
    tags:
      - tender
      - bidding
      - proposal
      - writing
---

# 标书编写技能

Use this skill to draft bid proposal sections based on a response matrix, proposal framework, scoring criteria, and reference materials. You are the core writer in the bid pipeline — the bid-analyst feeds you the response matrix and proposal framework, and you produce proposal prose.

## Core Principle

你是投标链条的核心产出环节——"写出能拿分的内容"。你的上游是标书分析（提供响应矩阵、评分标准和投标文件框架），你的下游是合规审查员（检查你的产出）。

Do not start writing immediately. First confirm scope, read the response matrix, check writing style references, then draft section by section with human review gates.

Treat AI-generated content as a reviewable draft, not as final evidence. Mark missing or uncertain information as `待补充素材` or `需人工确认` instead of inventing company facts.

Support partial-assignment bid work. The user may only own the technical volume, a single subsection, or selected content inside a larger proposal. Keep business, price, legal, qualification, and unassigned technical chapters as context or risk notes unless the user explicitly assigns them.

## Workflow

### Step 1: 确认任务范围

**做什么：** 明确本次要写哪些章节、不负责哪些、有哪些固定要求。

**输入：**
- 标书分析输出的响应矩阵
- 标书分析输出的投标文件框架
- 招标文件（项目背景、评分标准、格式要求）
- 用户指定的负责章节和不负责章节
- 历史参考稿（如有）

**输出：**

任务范围确认表：

| 维度 | 内容 |
|------|------|
| 我负责章节 | |
| 他人负责章节 | |
| 仅作参考章节 | |
| 暂不处理章节 | |
| 截止时间 | |
| 必须参考的材料 | |
| 当前缺失信息 | |

逐章篇幅确认表（必须逐章确认，不得笼统填写）：

| 章节编号 | 章节标题 | 目标页数 | 页数来源 | 备注 |
|---------|---------|---------|---------|------|
| | | | 招标文件要求/用户指定/建议值 | |

**约束：**
- 不要默认用户负责整份标书
- 责任范围不清楚时先列出需要确认的问题
- 区分"已明确的信息"和"待确认的信息"
- 逐章篇幅未确认前，不得开始编写
- 这一步结束后提示：这一步做了什么、得到什么结果、下一步需要提供或确认什么

**责任归属确认（必须人工确认）：**
- 如果 tender-analysis 输出的响应矩阵已包含责任归属，必须与用户逐项确认，不要直接采纳
- 确认完成后，将确认结果记录在"任务范围确认表"中，作为后续编写的依据
- 不要自行推断哪些章节由我司编写、哪些由其他单位提供，必须由人工明确指定

---

### Step 2: 建立责任边界

**做什么：** 在任务范围基础上，细化每个章节的上下游依赖关系。

**输入：**
- Step 1 确认的任务范围
- 分工信息

**输出：**

| 章节/内容项 | 责任归属 | 与我负责内容的关系 | 我需要获取的信息 | 我需要交付给他人的内容 | 风险或待确认事项 |
|------------|---------|------------------|----------------|---------------------|----------------|

责任归属只能使用：`我负责`、`他人负责`、`仅作参考`、`暂不处理`。

**约束：**
- 只围绕用户负责的章节展开
- 商务、报价、法务、资质、人员证书、业绩证明等范围外内容只做关联提醒，不代写
- 如果用户的章节依赖其他章节，明确"需要协同"或"需要上游输入"

---

### Step 3: 分析写作风格

**做什么：** 如果有历史稿或参考稿，先分析其风格特征，再开始写。

**输入：**
- 历史参考稿或用户认可版本
- 知识库"方案素材库"中的写作风格参考
- 如无参考稿且知识库无相关素材，读取 `references/writing-style.md` 中的默认风格规范

**输出：**

风格分析摘要：
1. 标题层级特点（几级标题、编号方式）
2. 正文段落密度（每节平均几段、每段平均几句）
3. 表格和图示使用比例
4. 常用表达方式和语气
5. 需要避免的问题
6. 对本次写作的风格建议

**约束：**
- 优先参考用户认可的历史稿，不要套用通用 AI 标书结构
- 如参考素材不属于同类项目，说明哪些可借鉴、哪些不能照搬

---

### Step 4: 设计章节大纲

**做什么：** 基于响应矩阵、评分标准和风格分析，为每个负责章节设计正文大纲。

**输入：**
- 响应矩阵
- 评分标准矩阵
- 投标文件框架
- 风格分析结果
- 目标章节和固定标题/编号
- 页数要求

**输出：**

| 建议标题 | 写作重点 | 对应评分点/要求 | 需要材料 | 风险提示 | 是否建议配图/表 |
|---------|---------|---------------|---------|---------|---------------|

**约束：**
- 大纲必须覆盖所有范围内关键评分点和硬性要求
- **保留框架中的章节编号**：如果投标文件框架已提供编号（如"## 1 商务投标文件封面""### 13.1 资格审查资料-基本条件"），必须原样保留，不要重新编号或去掉编号
- 控制标题颗粒度，避免很多小标题只写 1-2 短段
- 标题要自然、专业、简洁，避免"XXX与XXX""XXX和XXX"这类 AI 味标题
- 如果某个标题下无法写出充分正文，应合并到更大的标题
- 配图只在能说明流程、进度、责任、风险或交付闭环时使用，不为装饰或凑页数

**大纲确认（必须人工确认）：**
- 大纲输出后必须暂停，列出每个章节的标题、写作重点、对应评分点、建议篇幅，逐项请用户确认
- 用户确认或修改后，才进入 Step 5 编写正文
- 不要跳过确认直接开始编写

---

### Step 5: 编写正文内容

**做什么：** 基于确认的大纲，逐章节编写投标正文。

**输入：**
- Step 4 确认的大纲
- 响应矩阵和评分标准
- 公司素材（从知识库检索：历史方案、技术架构、项目经验等）
- 风格参考

**输出：**
- 章节标题
- 正文内容
- 已响应评分点清单
- 待补充素材清单
- 依赖其他章节/他人材料清单
- 风险提示

**写作规则（必须严格遵守）：**

1. 只撰写用户负责的章节，不代写商务、报价、法务、资质或其他人负责内容
2. 主语使用 `我司`，除非用户另有要求
3. 内容围绕评分点和硬性要求展开
4. 语言专业、稳健、真诚，体现投标人服务诚意
5. 不得编造未提供的公司资质、案例、人员、系统、数据或承诺
6. 不要出现 `根据招标文件`、`依据招标文件要求`、`详见招标文件`、`招标文件第 X 条` 等索引式表达
7. 每个标题下正文要充分展开，避免只有 1-2 个短段
8. 不要用重复表格、重复段落或碎标题凑页数
9. 如果资料不足，先标注 `待补充素材` 或 `需人工确认`，不要自行编造
10. 配图只在能说明流程、进度、责任、风险或交付闭环时使用
11. **不添加分析元数据**：输出正文时不要包含"类型：评分响应内容""对应评分项：XXX""建议篇幅：X页"等分析注释，这些属于 tender-analysis 的输出，不应出现在标书正文中
12. **基于框架文档输出**：以 tender-analysis 输出的投标文件框架为底稿，输出的文档必须保持完整的投标文件框架结构和章节编号。自己负责的章节，将正文插入到框架中对应的章节位置；不负责的章节留空，仅保留原标题。整体输出是一份结构完整的投标文件，而不是只输出负责部分的零散内容
13. **继承框架格式**：框架文档中的模板文字（块引用部分）、表格结构、固定表述必须原样保留，不得修改或删除。正文编写在模板之后，不得覆盖模板内容
14. **格式规范**：正文宋体（西文/数字 Times New Roman）小四，1.5倍行距，首行缩进2字符。标题黑体，1.5倍行距。表格文字宋体五号。详细规格见 Document Formatting Specifications
15. **交付文档必须包含目录（强制生成项，不得省略）**：最终交付的 .docx 文档必须在封面之后、正文之前**实际渲染完整目录**（不得仅在说明文字中提及目录）。整份标书目录须列出全部分册及全部章节（如第一分册 商务/第二分册 技术/第三分册 报价 + 各章节编号与标题）；单章文档目录须列出该章全部一级小节（必要时含二级小节，如 24.1/24.2...）。目录中的标题文字须与正文标题完全一致。文档格式必须遵循 Document Formatting Specifications：标题黑体（一级小三15pt、二级四号14pt）、正文宋体+Times New Roman 小四12pt、1.5倍行距、首行缩进2字符、表格文字宋体五号10.5pt

**段落密度要求：**
- 每个标题下应有充分展开的正文
- 通过以下方式扩充内容深度：项目理解、实施逻辑、阶段安排、资源协调、风险处理、交付物形成、审查闭环、跨章节协调
- 宁可少几个标题配厚段落，也不要很多标题配薄内容

**页数处理：**
- 如用户要求页数，先确认是整份页数还是单章页数
- 从实际 Word 文档计算页数，不要从字数估算
- 增加页数通过有用内容实现：场景化说明、执行细节、招标针对性响应、质量控制、风险控制、交付逻辑
- **篇幅要求较长时（单章超过30页），主动使用表格和图片来充实内容**：表格用于对比、清单、流程步骤、参数说明等结构化信息；图片用于流程图、架构图、进度图、责任矩阵等可视化内容。表格和图片必须有实际信息量，不得为空壳
- 不得用重复表格、重复模板或碎标题凑页数

**配图规则：**
- 好的配图场景：实施流程图、服务响应闭环、项目进度路径、责任与协作流、问题处理与升级路径、风险预警与纠偏机制、交付物形成与审查闭环
- 保持商务、简洁、易读
- 中文标签与正文一致
- 不得引入招标文件或素材中未支持的事实、工具、产品名、人员、日期或承诺
- 配图放在相关正文附近，附简短说明
- 如果简单表格或文字说明比图更清晰，不要生成图片

---

### Step 6: 自查与交付

**做什么：** 写完后做一轮自查，确保质量达标再移交给合规审查员。

**输入：**
- Step 5 输出的正文草稿

**输出：**

自查清单：

| 检查项 | 状态 | 说明 |
|-------|------|------|
| 评分点覆盖率 | X/Y 已覆盖 | 未覆盖项列出 |
| 硬性要求覆盖 | X/Y 已覆盖 | 未覆盖项列出 |
| 幻觉/无依据内容 | 有/无 | 如有，列出位置 |
| 过度承诺 | 有/无 | 如有，列出位置 |
| 索引式表达 | 有/无 | 如有，列出位置 |
| 重复内容 | 有/无 | 如有，列出位置 |
| 标题编号 | 正确/有误 | 如有误，列出位置 |
| 目录包含 | 有/无 | 交付文档开头必须包含完整目录（封面后、正文前，实际渲染进文档），缺失即不合格 |
| 格式规范 | 符合/不符合 | 对照 Document Formatting Specifications：标题黑体/正文宋体小四/1.5倍行距/首行缩进2字符/表格五号 |
| 页数要求 | 满足/不满足 | |
| 配图必要性 | 合理/过多/过少 | |
| 越界内容 | 有/无 | 如有，列出位置 |

交付结论：
- `可移交合规审查` / `需补充后移交` / `存在高风险，暂不移交`

**约束：**
- 如存在高风险（废标项未解决、关键评分点未覆盖），不要标记为可移交
- 自查结果和正文一起移交给合规审查员
- 标书编写完成并通过自查后，必须提示用户：`标书编写技能已完成，下一步建议使用「合规审查技能」，对完整投标文件进行废标风险、评分点覆盖、格式和交付质量审查。`

---

### Step 7: 商务材料自动填充（用户上传商务信息文档时）

**做什么：** 当用户上传商务信息文档（.docx/.pdf，含营业执照、资质证书、人员证件、业绩合同、社保记录、企业能力证书等）并要求「贴到标书对应位置」时，自动把文档中的**文本+图片**按内容类型插入投标文件框架的对应章节，保持格式规范。

**流程摘要（完整细节见 `references/business-materials-filling.md`）：**

1. **提取**：`extract_docx_text` 提取文本识别分组标题；`zipfile` 解包 `word/media/` 导出全部图片；读 `word/document.xml` + `word/_rels/document.xml.rels` 按 `r:embed` 文档流顺序建立「标题→图片」真实分组（不能靠文件名猜归属）。
2. **压缩**：扫描件 PNG 用 Pillow 转 JPG（最长边1600px、quality=82、透明转白底），输出到 `figs/biz_jpg/`，通常 20MB→3MB。
3. **映射插入**：按材料类型插入对应章节——营业执照/资质/人员证件→14.1 基本条件（人员证件放「项目人员材料（姓名 工号）」小节）；业绩合同→14.4 业绩要求 + 26 业绩表；社保→27；质量/信息安全/软著→31。插入格式：`**XX（扫描件）：**` 加粗标题 + `![图题](figs/biz_jpg/imageN.jpg)` 图片引用；材料缺口如实标注（如"已提供1项，需再补2项"、"待补充"），不编造。
4. **渲染**：md2docx_skill custom 模式渲染整份投标文件 docx（目录/分页符/黑体宋体/行距/表格格式自动保持）。渲染用 subprocess 并给足 timeout（280s+），避免超时。
5. **验证（必须做）**：python-docx 按正文 Heading 样式定位 14.1/14.4/26/27 真实段落区间（跳过目录区），统计各区间含 `<w:drawing>` 段落数；检查 `word/media/` 总图数、章节1-50无缺失、文件体积（压缩后 <10MB）。交付链接必须指向最新文件（写新文件名或工作区根目录，避免旧缓存）。

**约束：**
- 只填用户上传文档中真实存在的材料，缺口标注待补充，绝不编造资质/业绩/人员
- 图片路径引用前必须校验文件存在；透明 PNG 转 JPG 必须先铺白底
- 交付时向用户说明：每类材料放入的章节、压缩前后体积、仍需人工补充的缺口

---

## Document Formatting Specifications

When generating or formatting `.docx` bid proposal files using python-docx, apply these formatting rules:

### Body Text
- Font: Chinese 宋体 (SimSun) + Western Times New Roman, 小四 (12pt = 24 half-points)
- Line spacing: 1.5x (w:line="360" w:lineRule="auto")
- First-line indent: 2 characters (w:firstLineChars="200")
- Preserve existing bold formatting

### Heading Styles
All headings use 1.5x line spacing, bold, color auto.

- **Heading 1**: 黑体 (SimHei), 小三 (15pt = 30 half-points)
- **Heading 2**: Chinese 黑体 + Western Times New Roman, 四号 (14pt = 28 half-points)
- **Heading 3**: Chinese 黑体 + Western Times New Roman, 四号 (14pt = 28 half-points)
- **Heading 4**: Chinese 黑体 + Western Times New Roman, 小四 (12pt = 24 half-points)
- **Heading 5**: Chinese 黑体 + Western Times New Roman, 小四 (12pt = 24 half-points)
- **Heading 6**: Chinese 黑体 + Western Times New Roman, 小四 (12pt = 24 half-points)
- **Heading 7**: Chinese 黑体 + Western Times New Roman, 小四 (12pt = 24 half-points)

### Table Cell Text
- Font: Chinese 宋体 + Western Times New Roman, 五号 (10.5pt = 21 half-points)

### Table Titles
- Position: Immediately above the table, in a separate paragraph
- Alignment: Centered
- Font: 宋体 (SimSun), 小四 (12pt), italic
- No numbering prefix (e.g., use "核心业务系统建设范围", not "表39-5-1 核心业务系统建设范围")
- Table title paragraphs do not have first-line indent

### Technical Implementation Notes
- Use python-docx to manipulate OOXML; do not use regex replacement (avoids XML corruption)
- Section detection: Use text content matching (e.g., "成功案例" → "服务管理方案"), not style names
- Table title insertion: Scan all tables to get body indices, then insert in reverse order to avoid index shifting
- Use a body-index set to skip paragraphs already used as table titles, avoiding duplicate formatting

## Risk Rules

- Do not fabricate company qualifications, project cases, personnel, systems, certifications, data, commitments, or implementation capacity
- If evidence is missing, write `待补充素材` or `需人工确认`
- Separate analysis outputs from draft proposal content
- Keep assigned-scope work separate from full-proposal context. If full tender analysis is useful, label outputs as `范围内`, `关联项`, or `范围外`
- Do not expand the user's responsibility without permission
- For high-risk items such as rejection clauses, qualifications, performance cases, legal commitments, delivery deadlines, service levels, staffing, and prices, recommend human confirmation
- When working from long files, process them in sections and maintain a running requirement/scoring/risk table

## References

- Read `references/writing-style.md` before drafting outlines, writing proposal prose, or revising style/depth.
- Read `references/prompt-templates.md` when the user needs reusable prompts or staged execution prompts.
- Read `references/quality-checklist.md` before self-review or delivery checks.
- When the user uploads business material documents (docx/pdf) to be filled into the proposal, read `references/business-materials-filling.md` and follow its extract → compress → map-insert → render → verify flow.
