---
name: doc-translator
description: 文档翻译子流程——从云盘下载外文文献，支持通用/学术/技术/逐段对照/摘要翻译
---

# 文档翻译子流程 (doc-translator)

## 功能

从天翼云盘下载外文文献，利用大模型完成翻译，将翻译后文档保存到用户工作目录。

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

### 第四步：大模型翻译

根据用户需求选择翻译方式。参考 `references/prompts/doc-translator.md` 获取各类翻译模板：

- **通用翻译**：准确传达原文，术语首次出现附原文，语言自然流畅
- **学术论文翻译**：学术术语准确，公式/引用保持原样，学术严谨
- **技术文档翻译**：代码块/路径/配置项不翻译，保持格式不变
- **逐段对照翻译**：原文与译文交替排列，便于对照阅读
- **摘要翻译**：仅翻译摘要部分，或生成内容概要

**确定目标语言**：
- 用户明确指定时使用指定语言（如"翻译成日语"）
- 未指定时根据原文语言自动判断：英文→中文，中文→英文，其他→中文

**关键规则**：
- 准确传达原文含义，不遗漏、不增补
- 保持原文段落结构
- 学术/技术术语首次出现时在括号内附原文
- 公式、代码、引用标记保持原样

### 第五步：保存翻译后文档

将 LLM 翻译后的文本写入临时文件，再调用脚本回写为文档：

```bash
python scripts/doc_handler.py save --content-file .temp/translated_content.txt --output <output_path> --source-format <原始格式>
```

输出路径默认保存到用户工作目录根目录。文件命名规则：`<原文件名>_翻译版<扩展名>`。

**PDF 特殊处理**：PDF 文件回写时自动转为 `.docx` 格式输出。
