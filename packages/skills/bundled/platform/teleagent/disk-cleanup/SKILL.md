---
name: disk-cleanup
description: Windows C盘深度清理工具。扫描并清理磁盘空间，覆盖回收站、系统临时文件、浏览器缓存、开发工具缓存(npm/pip/Yarn/JetBrains/VSCode)、聊天软件缓存(微信/企业微信/钉钉/QQ/腾讯会议)、办公软件缓存(WPS)、多版本残留等。当用户提到"C盘满了"、"磁盘空间不足"、"清理C盘"、"释放空间"、"深度清理"、"磁盘清理"时触发。
name_cn: C盘深度清理
description_cn: 扫描并深度清理Windows C盘空间，涵盖回收站、系统缓存、浏览器缓存、开发工具缓存、聊天软件缓存、WPS缓存、多版本残留等，释放磁盘空间。
create_source: super-agent-skill-creator
---

# C盘深度清理

Windows系统C盘空间扫描与深度清理。通过PowerShell脚本分阶段执行，安全释放磁盘空间。

## 工作流程

### 1. 扫描磁盘（scan模式）

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

## 清理项分类

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
