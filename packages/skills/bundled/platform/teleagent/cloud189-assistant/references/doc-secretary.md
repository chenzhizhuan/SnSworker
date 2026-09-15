---
name: doc-secretary
description: 文档润色子流程——从云盘下载文档，完成润色、纠错、措辞优化、格式规范等处理
---

# 文档润色子流程 (doc-secretary)

## 功能

从天翼云盘下载文档，利用大模型完成语义纠错、措辞优化、格式规范等处理，将优化后文档保存到用户工作目录。

**操作范围**：本流程仅能操作云盘中"我的应用/云盘智能体"目录下的文件。如果搜不到文件，请确认目标文件是否已放入该目录。

## 步骤

### 第一步：查找并选择云盘文档

使用内置云盘脚本查找文档：

```bash
# 获取默认目录ID
python scripts/cloud189_lite.py get-folder

# 按关键词搜索文件
python scripts/cloud189_lite.py search-files --folder-id <folder_id> --keyword "<关键词>"

# 列出目录下所有文件
python scripts/cloud189_lite.py list-files --folder-id <folder_id>
```

> **注意**：搜索范围仅限"我的应用/云盘智能体"目录。如果搜索无结果，请提醒用户：本流程仅支持操作该目录下的文件，请先将目标文件上传或移动到"我的应用/云盘智能体"文件夹中。

支持处理的文档格式：`.docx`、`.txt`、`.md`、`.pdf`

### 第二步：下载文档

```bash
# 获取下载链接
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

### 第四步：大模型处理

根据用户需求选择处理方式。参考 `references/prompts/doc-secretary.md` 获取各类处理模板：

- **通用润色**：修正语法、错别字、标点，优化语句流畅度
- **汇报总结润色**：确保逻辑清晰、层次分明，使用专业职场用语
- **语义纠错**：检查语义错误、逻辑矛盾，标注存疑之处
- **措辞优化**：替换口语化表述为专业用语，精简冗长句式
- **格式规范检查**：检查标题层级、编号连续性、中英文间距

**关键规则**：
- 保持原文段落结构（段落间用 `\n\n` 分隔）
- 保持原文核心观点和数据不变
- 不添加原文中不存在的信息

### 第五步：保存优化后文档

将 LLM 处理后的文本写入临时文件，再调用脚本回写为文档：

```bash
python scripts/doc_handler.py save --content-file .temp/processed_content.txt --output <output_path> --source-format <原始格式>
```

输出路径默认保存到用户工作目录根目录。文件命名规则：`<原文件名>_润色版<扩展名>`。

**PDF 特殊处理**：PDF 文件回写时自动转为 `.docx` 格式输出。
