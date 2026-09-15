---
name: ppt-assistant
description: PPT生成子流程——从云盘下载文档，生成PPT内容大纲，调用pptx技能创建演示文稿
---

# PPT生成子流程 (ppt-assistant)

## 功能

从天翼云盘下载项目方案类文档，利用大模型生成PPT内容大纲（JSON格式），再调用pptx技能创建实际的.pptx演示文稿。生成的PPT默认保存到用户本地工作目录，也可选择上传回天翼云盘。

**操作范围**：本流程仅能操作云盘中"我的应用/云盘智能体"目录下的文件。如果搜不到文件，请确认目标文件是否已放入该目录。

## 步骤

### 第一步：查找并选择云盘文档

用户输入生成PPT的要求，同时通过对话框选择云盘文件作为PPT内容来源。

```bash
# 获取默认目录ID
python scripts/cloud189_lite.py get-folder

# 按关键词搜索文件
python scripts/cloud189_lite.py search-files --folder-id <folder_id> --keyword "<关键词>"

# 列出目录下所有文件
python scripts/cloud189_lite.py list-files --folder-id <folder_id>
```

> **注意**：搜索范围仅限"我的应用/云盘智能体"目录。如果搜索无结果，请提醒用户：本流程仅支持操作该目录下的文件，请先将目标文件上传或移动到"我的应用/云盘智能体"文件夹中。

支持读取的文档格式：`.docx`、`.txt`、`.md`、`.pdf`

### 第二步：下载文档

```bash
python scripts/cloud189_lite.py download --file-id <file_id>
```

拿到 `download_url` 后，用 PowerShell 下载到 `.temp/` 目录：

```powershell
Invoke-WebRequest -Uri "<download_url>" -OutFile ".temp/<filename>"
```

### 第三步：提取文档文本

```bash
python scripts/doc_handler.py extract --input .temp/<filename>
```

输出 JSON，包含 `content` 字段（文档全文）和 `format` 字段（文件格式）。

### 第四步：大模型生成PPT内容大纲

根据用户需求选择PPT模板类型。参考 `references/prompts/ppt-assistant.md` 获取各类模板：

- **通用大纲**：适用任何主题
- **产品介绍PPT**：产品发布、路演、客户推介
- **项目方案PPT**：立项评审、技术方案、可行性分析
- **工作汇报PPT**：周报/月报/季报、项目进展、年终总结
- **培训课件PPT**：内部培训、技术分享、新员工入职

**模板参数**：`{user_request}`、`{source_content}`、`{page_count}`、`{style}`

**关键规则**：
- LLM 必须严格输出合法 JSON，格式与模板中的示例一致
- 每个 slide 的 content 为要点列表，每条不超过30字
- 封面页 `type: "title"`，内容页 `type: "content"`，结尾页 `type: "ending"`
- 页数控制在用户指定范围内

### 第五步：调用pptx技能创建PPT

将第四步生成的JSON大纲交给pptx技能，逐页生成PPT内容。

### 第六步：保存PPT

默认保存到用户工作目录根目录。文件命名规则：`<原文件名>_PPT版.pptx`。

**可选：上传回云盘**：

```bash
# 创建目标目录（可选）
python scripts/cloud189_lite.py create-folder --name "<文件夹名>" --parent-id <parent_folder_id>

# 上传文件
python scripts/cloud189_lite.py upload --local "<本地pptx路径>" --folder-id <目标文件夹ID>
```
