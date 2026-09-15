---
name: report-organizer
description: 报表整理子流程——基于云盘或本地数据文件，整理数据并生成Excel报表
---

# 报表整理子流程 (report-organizer)

## 功能

基于天翼云盘或本地的数据报表文件，利用大模型整理数据、生成新的Excel报表。支持读取 .xlsx/.csv/.tsv/.docx/.txt/.md/.pdf 格式，输出结构化的 .xlsx 报表。

**操作范围**：云端文件操作仅限云盘中"我的应用/云盘智能体"目录下的文件。如果搜不到文件，请确认目标文件是否已放入该目录。如需使用其他目录的文件，可先将文件下载到本地后再操作。

## 步骤

### 第一步：选择数据文件

用户选中文件或文件夹（本地或云端），并输入整理要求。

**云端文件**：

```bash
# 获取默认目录ID
python scripts/cloud189_lite.py get-folder

# 按关键词搜索
python scripts/cloud189_lite.py search-files --folder-id <folder_id> --keyword "<关键词>"

# 列出目录文件
python scripts/cloud189_lite.py list-files --folder-id <folder_id>
```

> **注意**：云端搜索范围仅限"我的应用/云盘智能体"目录。如果搜索无结果，请提醒用户：本流程仅支持操作该目录下的文件，请先将目标文件上传或移动到"我的应用/云盘智能体"文件夹中，或直接使用本地文件。

**本地文件**：直接使用本地路径，无需下载。

支持的数据格式：
- 表格类：`.xlsx`、`.xls`、`.csv`、`.tsv`
- 文档类：`.docx`、`.txt`、`.md`、`.pdf`

### 第二步：下载云端文件（如有）

```bash
python scripts/cloud189_lite.py download --file-id <file_id>
```

```powershell
Invoke-WebRequest -Uri "<download_url>" -OutFile ".temp/<filename>"
```

### 第三步：提取数据

```bash
# 单文件提取
python scripts/data_extractor.py extract --input <文件路径>

# 多文件批量提取
python scripts/data_extractor.py extract-multi --inputs <文件1> <文件2> <文件3>
```

### 第四步：大模型整理数据生成报表

参考 `references/prompts/report-organizer.md` 获取各类报表模板：

- **通用报表整理**：重新组织数据结构，突出关键指标
- **数据对比报表**：多期对比、预算vs实际、同比环比
- **汇总分析报表**：多数据源汇总、分项统计
- **趋势展示报表**：时序数据趋势、KPI跟踪
- **异常数据报表**：数据质量检查、异常值排查

**模板参数**：`{user_request}`、`{source_data}`

**关键规则**：
- LLM 必须严格输出合法 JSON
- 数据准确，不编造原始数据中不存在的内容
- 数值保留合理精度（金额2位小数、百分比1位、数量整数）
- 突出用户要求关注的关键数据

### 第五步：调用xlsx技能创建Excel

将JSON报表结构交给xlsx技能，创建实际的.xlsx文件。

### 第六步：保存报表

默认保存到用户工作目录根目录。文件命名规则：`<原文件名>_整理版.xlsx`。

**可选：上传回云盘**：

```bash
python scripts/cloud189_lite.py create-folder --name "<文件夹名>" --parent-id <parent_folder_id>
python scripts/cloud189_lite.py upload --local "<本地xlsx路径>" --folder-id <目标文件夹ID>
```
