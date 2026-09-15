---
name: daily-token-usage
description: 查询 TeleAgent 每日 Token 用量统计。从 TeleAgent 日志中解析 token 消耗数据（输入/输出/缓存读取/合计），输出当日明细和本月累计。触发场景：用户问"今天消耗了多少token""token用量""token统计""看看token消耗""本月token用量"等。关键词：token、用量、消耗、统计、额度。
name_cn: 每日Token用量查询
description_cn: 查询 TeleAgent 每日 Token 消耗统计，包括输入/输出/缓存读取用量及本月累计，支持文本和Markdown格式输出。
create_source: super-agent-skill-creator
---

# 每日Token用量查询

## 功能

从 TeleAgent 本地日志中解析 token 消耗数据，统计当日用量和本月累计用量。

## 使用方法

运行脚本 `scripts/token_stats.py`，支持以下参数：

```bash
# 统计今天（默认纯文本输出）
python scripts/token_stats.py

# 统计指定日期
python scripts/token_stats.py --date 2026-08-18

# 输出 Markdown 格式
python scripts/token_stats.py --format markdown

# 输出 JSON 格式（便于程序处理）
python scripts/token_stats.py --format json
```

**Windows 注意**：需设置 `$env:PYTHONIOENCODING="utf-8"` 后运行，避免编码错误。

## 输出内容

1. **今日用量**：调用次数、输入(Input)、输出(Output)、缓存读取(Cache)、合计
2. **本月累计**：活跃天数、调用次数、各项合计
3. **每日明细**：本月每天的分项数据

## 日志路径

默认从 `~/.local/share/TeleAgent/log/` 读取 `super-agent-server-YYYY-MM-DD.log` 文件，解析其中 `tokens(in=xxx out=xxx cacheRead=xxx)` 记录。

可通过环境变量 `TELEAGENT_LOG_DIR` 覆盖日志目录路径。
