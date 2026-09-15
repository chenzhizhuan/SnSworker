---
name: cloud189-assistant
description: Tianyi Cloud Drive assistant that routes user requests to the right sub-workflow — document polishing/proofreading, document translation, PPT generation, report organizing, or photo search. Document/report/PPT operations are limited to "我的应用/云盘智能体" directory; photo search supports full-disk search. Self-contained, no dependency on other skills (except pptx/xlsx skills for output generation).
name_cn: 天翼云盘助手
description_cn: 天翼云盘统一助手，根据用户意图路由到对应子流程——文档润色、文档翻译、PPT生成、报表整理、照片搜索。文档/报表/PPT操作仅限"我的应用/云盘智能体"目录；照片搜索支持全盘搜索。自包含运行，PPT和报表生成分别依赖pptx和xlsx技能。
---

# 天翼云盘助手

## 概述

天翼云盘统一入口，根据用户意图自动路由到5个子功能：

| 子功能 | 说明 | 文件操作范围 |
|--------|------|-------------|
| **文档润色** (doc-secretary) | 润色、纠错、措辞优化、格式规范 | 仅"我的应用/云盘智能体"目录 |
| **文档翻译** (doc-translator) | 多模式翻译（通用/学术/技术/逐段/摘要） | 仅"我的应用/云盘智能体"目录 |
| **PPT生成** (ppt-assistant) | 基于云盘文档生成PPT | 仅"我的应用/云盘智能体"目录 |
| **报表整理** (report-organizer) | 整理数据并生成Excel报表 | 仅"我的应用/云盘智能体"目录（本地文件不限） |
| **照片搜索** (photo-search) | 自然语言全盘搜索照片 | 全盘搜索，不受目录限制 |

确认用户意图后，读取对应的 `references/<子功能>.md` 获取详细执行步骤。

## 路由规则

根据用户输入判断意图，路由到对应子流程：

| 用户意图关键词 | 路由到 |
|---------------|--------|
| 润色、纠错、优化措辞、格式规范、文档处理 | `doc-secretary` |
| 翻译、翻译成xx语、学术论文翻译、摘要翻译 | `doc-translator` |
| 做PPT、生成PPT、演示文稿、幻灯片、转成PPT | `ppt-assistant` |
| 整理报表、汇总数据、生成Excel、整理表格 | `report-organizer` |
| 搜照片、找图片、照片搜索、看xx的照片 | `photo-search` |

**路由后行动**：读取 `references/<路由目标>.md`，按其中的详细流程执行。不要在顶层猜测子流程的详细步骤。

## 通用前置步骤：检查云盘登录状态

**所有子流程执行前**，先检查天翼云盘登录状态：

```bash
python scripts/cloud189_lite.py info
```

根据返回结果判断：

- **`has_token: true`**：已登录，继续路由到的子流程。
- **`has_token: false`** 或返回 `InvalidAccessToken` / `AccessToen not exits`：Token 缺失或过期，需引导用户重新登录：
  1. 提示用户打开授权页面：`https://cloud.189.cn/web/ecloud-auth/index.html`
  2. 登录后复制授权码
  3. 执行登录命令：
     ```bash
     python scripts/cloud189_lite.py login --auth-code <授权码>
     ```
  4. 登录成功后继续子流程。

**注意**：天翼云盘 OAuth2 授权码有时效性，需获取后尽快使用。

## 渐进式披露原则

1. **顶层**（本文件）：仅包含功能概览、路由规则、通用前置步骤
2. **子流程**（references/ 下的文件）：包含具体执行步骤、命令示例、模板引用
3. 按需加载：只有确认了路由方向后，才读取对应子流程文档

## 依赖安装

首次使用前安装依赖：

```bash
pip install python-docx openpyxl pypdf requests
```

## 资源说明

### scripts/
- `cloud189_lite.py` — 天翼云盘全功能操作脚本（登录、Token状态、搜索文件、列出文件、下载、智能搜图、创建目录、上传），自包含无需外部技能依赖
- `doc_handler.py` — 文档文本提取与回写脚本，支持 extract 和 save 两个子命令
- `data_extractor.py` — 数据提取脚本，支持 xlsx/csv/tsv/docx/txt/md/pdf 格式，保留表格行列结构和文本段落
- `requirements.txt` — Python 依赖清单

### references/
- `doc-secretary.md` — 文档润色子流程详细步骤
- `doc-translator.md` — 文档翻译子流程详细步骤
- `ppt-assistant.md` — PPT生成子流程详细步骤
- `report-organizer.md` — 报表整理子流程详细步骤
- `photo-search.md` — 照片搜索子流程详细步骤
- `prompts/` — 各子功能的提示词模板
  - `doc-secretary.md` — 文档润色模板
  - `doc-translator.md` — 翻译模板
  - `ppt-assistant.md` — PPT大纲生成模板
  - `report-organizer.md` — 报表整理模板
  - `photo-search.md` — 搜索提示词优化模板

## 注意事项
- 大部分操作都必须在"我的应用/云盘智能体"目录下进行，涉及folder_id参数的命令，请确保该id正确，可用`get-folder`命令获取默认目录ID。
