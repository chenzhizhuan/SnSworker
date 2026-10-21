---
name: 磁盘深度清理
description: Windows 磁盘深度清理统一技能（合并原「C盘深度清理」与「磁盘垃圾清理」）。两条路线：①C盘深度清理（回收站/系统临时/浏览器缓存/开发工具缓存/聊天软件缓存/多版本残留，PowerShell 引擎）；②全盘符扫描清理（C/D/E 任意盘，临时/缓存/日志/更新缓存/错误报告/prefetch/崩溃转储，Python 引擎，先扫描出报告再确认后清理）。触发词：清理磁盘、清理垃圾、清理C盘、磁盘清理、C盘满了、磁盘空间不足、释放空间、深度清理、清理缓存、清理临时文件、disk cleanup、clean disk、free up space、disk cleaner。
name_cn: 磁盘深度清理（统一版）
description_cn: 扫描并深度清理Windows磁盘空间：C盘深度清理（回收站、系统缓存、浏览器缓存、开发工具缓存、聊天软件缓存、多版本残留）+ 多盘符扫描清理（临时/缓存/日志/更新缓存/错误报告），先扫描后确认再清理，释放磁盘空间。
create_source: super-agent-skill-creator
metadata:
  tabtin:
    category: utility
---

# 磁盘深度清理（统一版）

Windows 磁盘空间扫描与深度清理统一技能，合并自「C盘深度清理」与「磁盘垃圾清理」。

## 路线选择

| 用户诉求 | 路线 | 引擎 |
|---|---|---|
| C盘满了/清理C盘/深度清理/聊天软件缓存 | 路线一：C盘深度清理 | PowerShell（scripts/disk_cleanup.ps1） |
| 清理D盘/E盘/指定盘符/多盘扫描 | 路线二：多盘符扫描清理 | Python（scripts/disk_scan.py + disk_clean.py） |
| 仅看哪里能释放空间 | 先跑路线二 scan 或路线一 scan 模式 | — |

未指定盘符且用户说“清理磁盘/清理垃圾”时，默认走路线二先全盘扫描出报告，用户确认范围后执行。

## 工作流程

### 路线一：C盘深度清理（PowerShell）

#### 1. 扫描磁盘（scan模式）

先运行扫描，了解当前磁盘占用分布：

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/disk_cleanup.ps1" -Mode scan
```

向用户展示扫描结果，用表格汇总各目录占用大小，标记可清理项。

### 2. 执行清理

根据用户选择的清理范围，运行对应模式：

**标准清理（安全项，无需确认）：**
```powershell
powershell -ExecutionPolicy Bypass -File "scripts/disk_cleanup.ps1" -Mode standard
```
清理内容：回收站、系统临时文件、浏览器缓存、开发工具缓存(npm/pip/Yarn/JetBrains/VSCode)、WPS缓存、多版本残留、Updater pending、Playwright旧版、Postman旧版、网易云缓存、深信服VPN日志、百度网盘/iSlide/HBuilder/语雀缓存。

**深度清理（含聊天媒体缓存，需用户确认）：**
```powershell
powershell -ExecutionPolicy Bypass -File "scripts/disk_cleanup.ps1" -Mode deep
```
清理内容：微信4.0缓存(日志/更新包/插件)、旧版微信缓存、企业微信缓存(升级包/小程序)、腾讯会议缓存、QQ缓存、钉钉CEF缓存和日志、钉钉图片缓存、IM聊天媒体缓存(图片/视频/文件)、utForpc下载缓存。

**全部清理：**
```powershell
powershell -ExecutionPolicy Bypass -File "scripts/disk_cleanup.ps1" -Mode all
```

### 3. 交互流程

1. 先运行 `scan` 模式展示当前磁盘状态和各目录占用
2. 用 `question` 工具询问用户选择清理范围：
   - 标准清理（推荐，安全项自动清理）
   - 深度清理（清理聊天软件缓存和媒体，需确认）
   - 全部清理
   - 仅扫描不清理
3. 执行对应模式的脚本
4. 展示清理前后对比（前可用 → 后可用 → 释放空间）

### 4. 注意事项

- 深度清理聊天媒体缓存后，聊天记录不会丢失，但图片/视频/文件需重新下载
- 脚本中的聊天软件路径基于用户实际安装环境，如果路径不存在会自动跳过
- 如果脚本因编码问题报错，需用 UTF-8 BOM 编码重新保存
- 每次最多等待脚本执行5分钟（扫描大目录可能较慢），如超时可分批执行
- 清理完成后，可选建议用户运行Windows磁盘清理工具(cleanmgr)进一步释放空间

## 清理项分类（路线一）

| 类别 | 标准清理 | 深度清理 |
|------|---------|---------|
| 回收站 | ✓ | - |
| 系统临时文件/日志/崩溃转储 | ✓ | - |
| 浏览器缓存(Edge/Chrome) | ✓ | - |
| 开发工具缓存(npm/pip/Yarn/JetBrains/VSCode) | ✓ | - |
| WPS缓存/备份/日志 | ✓ | - |
| 多版本残留(旧版钉钉/Postman/Playwright) | ✓ | - |
| Updater pending/VMware下载 | ✓ | - |
| 网易云/深信服/百度网盘/iSlide/HBuilder/语雀 | ✓ | - |
| 微信4.0缓存(日志/更新/插件) | - | ✓ |
| 旧版微信缓存 | - | ✓ |
| 企业微信缓存(升级包/小程序) | - | ✓ |
| 腾讯会议/QQ缓存 | - | ✓ |
| 钉钉CEF缓存/日志/旧环境 | - | ✓ |
| 钉钉图片缓存 | - | ✓ |
| IM聊天媒体(图片/视频/文件) | - | ✓ |
| utForpc下载缓存 | - | ✓ |

## 路线二：多盘符扫描清理（Python）

适用任意盘符（C/D/E…），先生成分类报告，确认后按类别清理。

### 1. 扫描

```powershell
python scripts/disk_scan.py C
python scripts/disk_scan.py D --categories temp cache log
```

**输出**: JSON 格式报告，包含:
- `disk_usage`: 磁盘使用情况（总量/已用/可用/使用率）
- `categories`: 按类别分组的垃圾项，每项含路径、说明、大小、文件数、安全等级
- `summary`: 汇总信息（总大小、可安全删除大小）

**类别列表**:

| Key | 说明 |
|-----|------|
| temp | 临时文件 |
| cache | 缓存文件（缩略图/pip/npm/nuget/字体） |
| log | 日志文件 |
| recycle | 回收站 |
| update | Windows 更新缓存 |
| error_report | 错误报告 |
| prefetch | 预读取文件 |
| crash_dump | 崩溃转储 |
| browser_cache | 浏览器缓存 |

### 2. 清理

```powershell
# 清理指定路径
python scripts/disk_clean.py --paths "C:\Windows\Temp" "C:\Users\xxx\AppData\Local\Temp"

# 从扫描结果 JSON 文件读取路径
python scripts/disk_scan.py C > scan_result.json
python scripts/disk_clean.py --json scan_result.json
```

**输出**: JSON 格式报告，每项含删除数量、释放空间、失败数和错误信息。

### 安全规则（路线二）

- **禁止自动删除**: 始终先扫描展示，等用户确认后再执行清理
- **`safe_to_delete: false` 的项目**: 展示时必须突出标记"不建议删除"，需用户二次确认
- **回收站**: 使用安全清理方式（保留目录结构）
- **通配符路径**: 支持 `*.log` 等模式匹配
- **错误容忍**: 单个文件删除失败不中断整体流程，记录错误后继续
- 各类垃圾文件路径和安全等级详见 [references/cleanup_targets.md](references/cleanup_targets.md)

## 历史来源

本技能为二合一统一版（2026-10-19）：
- `disk-cleanup`（C盘深度清理）→ 主体：PowerShell 引擎 + C盘深度清理项清单
- `disk-cleaner`（磁盘垃圾清理）→ 多盘符扫描清理路线 + Python 脚本（disk_scan.py / disk_clean.py）+ cleanup_targets.md
原两个技能目录已移除，触发词与能力全部并入本技能。
