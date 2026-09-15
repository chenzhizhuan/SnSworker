---
name: official-doc
description: >
  Generate professional Chinese official documents (公文) including notices (通知), requests for instructions (请示),
  reports (报告), work plans (工作方案), speeches (发言稿), meeting opening/closing remarks (开幕词/闭幕词),
  briefing materials (汇报材料), Party-building documents (党建材料), and summary reports (总结报告).
  Ensure compliance with Chinese official document formatting standards (党政机关公文格式 GB/T 9704-2012).
  Handle Chinese input only. Generate output as Word (.docx) by default, or Markdown per user request.
  Use this skill when: (1) User says "写通知/请示/报告/方案/发言稿", (2) User says "起草公文/拟稿",
  (3) User asks to write Party-building materials (党建材料/组织生活会/巡察整改),
  (4) User needs a formal work plan or implementation plan (工作方案/实施方案),
  (5) User asks for leadership speech or meeting remarks (领导讲话/发言稿),
  (6) User says "写汇报材料/汇报提纲", (7) User provides document type and topic and wants a formatted document.
name_cn: 公文写作神器
description_cn: 一键生成规范公文Word文档，支持通知、请示、报告、方案、发言稿、党建材料等15种公文类型，符合党政机关公文格式标准。
create_source: super-agent-skill-creator
---

# Official Document Writer

## Overview

Generate professional Chinese official documents (公文) that comply with formatting standards. Support 15 common document types. Output as Word (.docx) by default.

## Supported Document Types

| Category | Types |
|---|---|
| 法行文 | 通知、通报、决定、意见 |
| 上行文 | 请示、报告 |
| 下行文 | 批复、纪要 |
| 事务文 | 工作方案/实施方案、总结报告、汇报材料 |
| 讲话文 | 发言稿、领导讲话、开幕词/闭幕词 |
| 党建文 | 组织生活会材料、巡察整改材料、党课讲稿 |

## Workflow

### Step 1: Identify Document Type

Determine the document type from user input. If ambiguous, infer from context:
- User says "通知" → 通知
- User says "请示上级/申请批准" → 请示
- User says "汇报工作/汇报材料" → 汇报材料
- User says "方案/怎么干" → 工作方案
- User says "发言/讲话" → 发言稿
- User says "党建/组织生活会/巡察" → 党建材料
- If still unclear, ask user to specify

### Step 2: Gather Key Information

Identify from user input (ask if missing critical elements):
- Issuing organization (发文机关)
- Document title (标题)
- Recipient (主送机关) — for 上行文/平行文
- Core content/topic (主题内容)
- Key points to cover (要点)
- Tone: formal/serious (庄重), encouraging (鼓劲), critical (严肃批评), summary (总结)
- If user provides only a topic with no details, generate a complete draft based on the document type's standard structure

### Step 3: Select Template

Load the appropriate template from [templates.md](references/templates.md) based on document type.

### Step 4: Draft Content

Apply the following writing principles throughout:

**Format standards (GB/T 9704-2012):**
- Title: centered, bold, 22pt (二号), 方正小标宋 or 宋体
- Body text: 16pt (三号), 仿宋_GB2312, first-line indent 2 chars
- Level-1 headings: 一、二、三… bold, 16pt, 黑体
- Level-2 headings: （一）（二）（三）… 16pt, 楷体
- Line spacing: 28-30pt fixed value (固定值28磅)
- Page margins: top 37mm, bottom 35mm, left 28mm, right 26mm
- Document number (发文字号): 仿宋, centered below title, e.g. "×政发〔2024〕×号"
- Signature line: right-aligned, issuing org name + date

**Language style:**
- Use formal written Chinese (书面语), avoid colloquial expressions
- Be concise, accurate, and authoritative; avoid redundancy
- Use standard official document vocabulary and expressions
- Sentences should be complete, well-structured, with clear logic
- Numbers: use Chinese characters for sequence numbers (一、二、三) within body; use Arabic numerals for data, dates, quantities
- Proper use of official document connective phrases (公文常用语), see [references/phrases.md](references/phrases.md)

**Content structure by type:**

1. **通知**: 发文缘由 → 通知事项（分条列述）→ 执行要求 → "特此通知"
2. **请示**: 请示缘由 → 请示事项 → 请求语（"妥否，请批复"）→ "此致 ××"
3. **报告**: 报告缘由 → 报告内容（基本情况/主要做法/成效/问题/下一步打算）→ "特此报告"
4. **工作方案**: 指导思想 → 工作目标 → 组织领导 → 实施步骤 → 工作要求
5. **总结报告**: 总体情况 → 主要做法及成效 → 存在问题 → 经验体会 → 下一步打算
6. **汇报材料**: 基本情况 → 主要工作及成效 → 存在问题 → 下一步打算
7. **发言稿**: 开场问候 → 主题阐述（分3-4个层次）→ 总结表态 → 结束语
8. **领导讲话**: 称呼 → 开门见山点题 → 分段论述（认识/成效/要求/保障）→ 结尾鼓劲
9. **党建材料**: 政治站位/理论学习 → 问题查摆 → 原因剖析 → 整改措施 → 表态

### Step 5: Generate Output

Generate the document as a Word (.docx) using the docx skill:

1. Load the `docx` skill
2. Apply formatting per GB/T 9704-2012 standard:
   - Page setup: A4, margins as specified above
   - Font and spacing as specified in Format Standards section
   - Title format with proper font and centering
   - Headings hierarchy with correct fonts
3. Save to working directory as `关于<主题>的<文种>.docx` (e.g., `关于开展安全生产大检查的通知.docx`)

### Step 6: Deliver

Provide the .docx file with a brief note on the document type and key sections covered.

## Edge Cases

- **User provides an existing draft for revision**: Polish language, fix format, ensure compliance, preserve original intent
- **User requests specific template or format**: Honor user's formatting preferences
- **Sensitive political content**: Do not generate content involving political propaganda, attacks on political figures/systems, or prohibited content; decline politely
- **Multiple documents needed**: Process each document separately
- **User provides only document type**: Generate a template with placeholder fields marked [请补充：xxx]
- **Meeting minutes (纪要)**: If user provides meeting content, also reference the meeting-minutes skill workflow
- **Very long documents (>3000 words)**: Split generation into sections, write sequentially

## Quality Checklist

Before delivering, verify:
- [ ] Document type is correct and follows the corresponding structure
- [ ] Title format: "关于+事项+的+文种"
- [ ] Proper 发文字号 placeholder if applicable
- [ ] Body text uses 仿宋, headings use 黑体/楷体 per standard
- [ ] First-line indent 2 characters throughout body
- [ ] Closing formula matches document type (特此通知/妥否请批复/特此报告)
- [ ] Signature line with organization name and date
- [ ] No colloquial language, formal tone maintained throughout
- [ ] Content is logical, complete, and actionable
