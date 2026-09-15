---
name: colleague-distill
description: 将同事的工作方式、技术规范、沟通风格蒸馏成数字分身。支持上传 Word、PPT、PDF、聊天记录、邮件等各类文件，生成 Work Skill + Persona 双模型。当用户提到"蒸馏同事"、"创建数字分身"、"复刻同事工作方式"、"同事走了留下经验"、"离职交接"、"数字孪生"时触发。
name_cn: 同事蒸馏器
description_cn: 上传同事的 Word/PPT/聊天记录等文件，蒸馏生成能替他工作的数字分身
create_source: super-agent-skill-creator
---

# 同事蒸馏器

把同事的技能与性格蒸馏成 AI 数字分身——人走了，经验留下。

提供同事的原材料（Word、PPT、PDF、聊天记录、邮件、会议纪要等）加上你的主观描述，生成一个真正能替他工作的数字分身：
- 用他的技术规范写代码和文档
- 用他的语气、口头禅、决策风格回答问题
- 知道他什么时候会甩锅、推脱、或者突然认真起来

## 核心流程

### Phase 1：录入基本信息

向用户收集 3 个关键信息（均可跳过，跳过则从文件推断）：

1. **姓名/代号**：这位同事怎么称呼？（花名、昵称或代号）
2. **基本信息**：一句话描述——公司、职级、职位、性别
3. **性格画像**：一句话描述——MBTI、个性特点、你对他的印象

### Phase 2：采集原材料

引导用户提供文件。支持的格式：

| 格式 | 示例 | 可提取内容 |
|------|------|------------|
| Word (.docx) | 技术方案、需求文档、汇报材料 | 工作方法、文档风格、技术栈 |
| PPT (.pptx) | 汇报演示、方案宣讲 | 汇报风格、思维结构、关注重点 |
| PDF (.pdf) | 技术文档、合同、报告 | 知识体系、工作规范 |
| 聊天记录 (.txt/.json) | 微信导出、钉钉记录、企微记录 | 沟通风格、口头禅、性格特征 |
| 邮件 (.eml) | 工作邮件 | 正式沟通风格、优先级判断 |
| Excel (.xlsx) | 数据表格、排期表 | 工作规划方式、数据思维 |
| CSV/Markdown/HTML | 各类文本 | 按内容分析 |

**文件解析**：使用 `scripts/file_parser.py` 提取文件文本。

```bash
python -B scripts/file_parser.py <文件或目录路径> -o <输出路径>
python -B scripts/file_parser.py <目录路径> --stats  # 先查看文件统计
```

如果是多个文件，建议用户放入同一目录，使用目录批量提取。

### Phase 3：分析 & 生成

按双模型架构，分别生成 Work Skill 和 Persona：

**Work Skill（work.md）**：
- 读取 `references/work_template.md` 获取生成模板和分析原则
- 从提取的文本中分析：职责范围、技术栈、代码/工作风格、工作流程、经验知识库
- 重点：所有结论必须有据可依，信息不足留占位符

**Persona（persona.md）**：
- 读取 `references/persona_template.md` 获取生成模板和分析原则
- 从聊天记录和非正式材料中提取：核心性格、表达风格、口头禅、决策逻辑
- 关键：描述行为而非标签，给出"你会怎么说"的具体示例

### Phase 4：写入 & 确认

使用 `scripts/skill_writer.py` 创建目录结构并写入文件：

```bash
# 创建同事目录
python -B scripts/skill_writer.py create "张三" --base-dir colleagues

# 写入元数据
python -B scripts/skill_writer.py meta colleagues/zhang-san --name "张三" --company "XX公司" --role "后端工程师"

# 写入 work.md（从 stdin 读取内容）
python -B scripts/skill_writer.py write colleagues/zhang-san --type work < work_content.md

# 写入 persona.md
python -B scripts/skill_writer.py write colleagues/zhang-san --type persona < persona_content.md
```

生成的目录结构：

```
colleagues/zhang-san/
├── meta.json       # 元数据（姓名、公司、职级等）
├── work.md         # Work Skill（工作能力）
├── persona.md      # Persona（人格风格）
└── .versions/      # 版本历史（自动管理）
```

写入后，向用户展示 work.md 和 persona.md 的关键内容，请求确认。

## 增量更新

当用户说"我有新文件"或"追加"时：

1. 解析新文件文本
2. 对比现有 work.md 和 persona.md
3. 增量补充（不覆盖原有内容）：
   - 新文档 → 补充"经验知识库"
   - 新对话样本 → 补充"你会怎么说"示例
   - 性格修正 → patch 对应 Layer
4. 自动创建版本快照

## 对话纠正

当用户说"这不对"或"他不会这样"时：

1. 识别纠错类型（事实错误 / 性格错误 / 能力错误）
2. Patch 对应文件：
   - 事实错误 → 更新 meta.json
   - 性格错误 → patch persona.md Layer 0/2
   - 能力错误 → patch work.md
3. 展示修改前后对比，用户确认后写入

## 使用生成的数字分身

生成完成后，用户可以这样使用：

- "帮我用张三的风格写一个技术方案" → 读取 `work.md` + `persona.md` 作为上下文
- "张三会怎么评价这个代码？" → 加载 persona.md 后模拟回答
- "如果是张三处理这个线上问题，他会怎么做？" → 加载 work.md 后给出方案

## 依赖

文件解析依赖以下 Python 库（按需安装）：

```bash
pip install python-docx python-pptx pdfplumber openpyxl pypinyin
```

如果不安装，对应格式的文件将跳过并给出提示。
