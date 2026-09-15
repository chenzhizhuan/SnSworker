---
name: disk-cleaner
description: "Scan and clean junk files on Windows disk drives (C/D/E etc.). Covers temp files, caches, logs, recycle bin, Windows update cache, error reports, prefetch, crash dumps, and browser cache. Always scans first, presents report for user confirmation, then cleans. Use when user mentions: 清理磁盘, 清理垃圾, 清理C盘, 磁盘清理, disk cleanup, clean disk, free up space, 磁盘空间不足, 清理缓存, 清理临时文件, disk cleaner."
name_cn: 磁盘垃圾清理
description_cn: 扫描并清理Windows磁盘垃圾文件，支持多盘符，先扫描后确认再清理
create_source: super-agent-skill-creator
---

# 磁盘垃圾清理

扫描 Windows 磁盘垃圾文件，展示分类报告供用户确认后执行清理。

## 工作流程

1. **扫描** — 调用 `scripts/disk_scan.py` 扫描指定盘符，输出分类报告
2. **展示** — 将扫描结果以可读格式呈现给用户，标注安全等级和预估空间
3. **确认** — 用户选择要清理的类别或项目
4. **清理** — 调用 `scripts/disk_clean.py` 执行删除，输出清理结果

## 扫描

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

## 清理

```powershell
# 清理指定路径
python scripts/disk_clean.py --paths "C:\Windows\Temp" "C:\Users\xxx\AppData\Local\Temp"

# 从扫描结果 JSON 文件读取路径
python scripts/disk_scan.py C > scan_result.json
python scripts/disk_clean.py --json scan_result.json
```

**输出**: JSON 格式报告，每项含删除数量、释放空间、失败数和错误信息。

## 安全规则

- **禁止自动删除**: 始终先扫描展示，等用户确认后再执行清理
- **`safe_to_delete: false` 的项目**: 展示时必须突出标记"不建议删除"，需用户二次确认
- **回收站**: 使用安全清理方式（保留目录结构）
- **通配符路径**: 支持 `*.log` 等模式匹配
- **错误容忍**: 单个文件删除失败不中断整体流程，记录错误后继续

## 参考文档

- 各类垃圾文件路径和安全等级详见 [references/cleanup_targets.md](references/cleanup_targets.md)
