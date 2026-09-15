#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TeleAgent 每日 Token 用量统计脚本
从 TeleAgent 日志中解析 token 消耗数据，输出当日明细和本月累计。
"""

import re
import sys
import os
import json
from datetime import datetime, date
from pathlib import Path

# 日志目录
LOG_DIR = os.environ.get(
    "TELEAGENT_LOG_DIR",
    os.path.join(os.path.expanduser("~"), ".local", "share", "TeleAgent", "log")
)

# token 行正则
TOKEN_RE = re.compile(r"tokens\(in=(\d+)\s+out=(\d+)\s+cacheRead=(\d+)\)")


def parse_token_line(line: str):
    """从一行日志中提取 in/out/cacheRead token 数"""
    m = TOKEN_RE.search(line)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def get_log_file(target_date: date) -> Path:
    """获取指定日期的日志文件路径"""
    filename = f"super-agent-server-{target_date.strftime('%Y-%m-%d')}.log"
    return Path(LOG_DIR) / filename


def count_day(target_date: date):
    """统计单日 token 用量，返回 dict 或 None"""
    log_file = get_log_file(target_date)
    if not log_file.exists():
        return None

    total_in = 0
    total_out = 0
    total_cache = 0
    call_count = 0

    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                result = parse_token_line(line)
                if result:
                    total_in += result[0]
                    total_out += result[1]
                    total_cache += result[2]
                    call_count += 1
    except Exception as e:
        print(f"[ERROR] 读取日志失败: {log_file} - {e}", file=sys.stderr)
        return None

    if call_count == 0:
        return None

    return {
        "date": target_date.strftime("%Y-%m-%d"),
        "input": total_in,
        "output": total_out,
        "cache_read": total_cache,
        "total": total_in + total_out + total_cache,
        "calls": call_count,
    }


def count_month(year: int, month: int, up_to: date = None):
    """统计整月 token 用量（截至 up_to 日期）"""
    total_in = 0
    total_out = 0
    total_cache = 0
    total_calls = 0
    day_details = []

    # 构建日期范围
    if up_to is None:
        up_to = date(year, month, 1)
        # 如果是当月，用今天
        today = date.today()
        if today.year == year and today.month == month:
            up_to = today

    day = date(year, month, 1)
    while day.month == month and day <= up_to:
        day_data = count_day(day)
        if day_data:
            total_in += day_data["input"]
            total_out += day_data["output"]
            total_cache += day_data["cache_read"]
            total_calls += day_data["calls"]
            day_details.append(day_data)
        day = day.replace(day=day.day + 1)  # 可能溢出，用 timedelta 更安全

    return {
        "year": year,
        "month": month,
        "input": total_in,
        "output": total_out,
        "cache_read": total_cache,
        "total": total_in + total_out + total_cache,
        "calls": total_calls,
        "days_active": len(day_details),
        "day_details": day_details,
    }


def format_number(n: int) -> str:
    """格式化数字为万"""
    if n >= 10000:
        return f"{n / 10000:.1f}万"
    return str(n)


def format_text(today_data, month_data):
    """生成文本报告"""
    lines = []
    lines.append(f"📊 Token 用量统计（{today_data['date']}）")
    lines.append("")
    lines.append("【今日用量】")
    lines.append(f"  调用次数：{today_data['calls']} 次")
    lines.append(f"  输入：{format_number(today_data['input'])}")
    lines.append(f"  输出：{format_number(today_data['output'])}")
    lines.append(f"  缓存读取：{format_number(today_data['cache_read'])}")
    lines.append(f"  合计：{format_number(today_data['total'])}")
    lines.append("")
    lines.append(f"【{month_data['year']}年{month_data['month']}月累计】")
    lines.append(f"  活跃天数：{month_data['days_active']} 天")
    lines.append(f"  调用次数：{month_data['calls']} 次")
    lines.append(f"  输入：{format_number(month_data['input'])}")
    lines.append(f"  输出：{format_number(month_data['output'])}")
    lines.append(f"  缓存读取：{format_number(month_data['cache_read'])}")
    lines.append(f"  合计：{format_number(month_data['total'])}")

    # 列出每日明细
    if month_data["day_details"]:
        lines.append("")
        lines.append("【每日明细】")
        for d in month_data["day_details"]:
            lines.append(
                f"  {d['date']} | 调用{d['calls']}次 | "
                f"输入{format_number(d['input'])} | "
                f"输出{format_number(d['output'])} | "
                f"缓存{format_number(d['cache_read'])} | "
                f"合计{format_number(d['total'])}"
            )

    return "\n".join(lines)


def format_markdown(today_data, month_data):
    """生成 Markdown 报告"""
    lines = []
    lines.append(f"## 📊 Token 用量统计（{today_data['date']}）")
    lines.append("")
    lines.append("### 今日用量")
    lines.append("")
    lines.append("| 指标 | 数量 |")
    lines.append("|------|------|")
    lines.append(f"| 调用次数 | {today_data['calls']} 次 |")
    lines.append(f"| 输入 (Input) | {format_number(today_data['input'])} |")
    lines.append(f"| 输出 (Output) | {format_number(today_data['output'])} |")
    lines.append(f"| 缓存读取 (Cache) | {format_number(today_data['cache_read'])} |")
    lines.append(f"| **合计** | **{format_number(today_data['total'])}** |")
    lines.append("")
    lines.append(f"### {month_data['year']}年{month_data['month']}月累计")
    lines.append("")
    lines.append("| 指标 | 数量 |")
    lines.append("|------|------|")
    lines.append(f"| 活跃天数 | {month_data['days_active']} 天 |")
    lines.append(f"| 调用次数 | {month_data['calls']} 次 |")
    lines.append(f"| 输入 (Input) | {format_number(month_data['input'])} |")
    lines.append(f"| 输出 (Output) | {format_number(month_data['output'])} |")
    lines.append(f"| 缓存读取 (Cache) | {format_number(month_data['cache_read'])} |")
    lines.append(f"| **合计** | **{format_number(month_data['total'])}** |")
    lines.append("")

    # 每日明细表
    if month_data["day_details"]:
        lines.append("### 每日明细")
        lines.append("")
        lines.append("| 日期 | 调用次数 | 输入 | 输出 | 缓存读取 | 合计 |")
        lines.append("|------|---------|------|------|---------|------|")
        for d in month_data["day_details"]:
            lines.append(
                f"| {d['date']} | {d['calls']} | "
                f"{format_number(d['input'])} | "
                f"{format_number(d['output'])} | "
                f"{format_number(d['cache_read'])} | "
                f"{format_number(d['total'])} |"
            )

    return "\n".join(lines)


def main():
    """主函数
    
    用法:
      python token_stats.py              # 统计今天
      python token_stats.py --date 2026-08-18  # 统计指定日期
      python token_stats.py --format text      # 输出纯文本
      python token_stats.py --format markdown  # 输出 Markdown
      python token_stats.py --format json      # 输出 JSON
    """
    # 默认值
    target_date = date.today()
    fmt = "text"

    # 解析参数
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--date" and i + 1 < len(args):
            target_date = datetime.strptime(args[i + 1], "%Y-%m-%d").date()
            i += 2
        elif args[i] == "--format" and i + 1 < len(args):
            fmt = args[i + 1]
            i += 2
        elif args[i] == "--help" or args[i] == "-h":
            print(main.__doc__)
            return
        else:
            i += 1

    # 统计当日
    today_data = count_day(target_date)
    if not today_data:
        print(f"未找到 {target_date.strftime('%Y-%m-%d')} 的日志数据或无 token 记录", file=sys.stderr)
        # 仍输出月度统计
        today_data = {
            "date": target_date.strftime("%Y-%m-%d"),
            "input": 0,
            "output": 0,
            "cache_read": 0,
            "total": 0,
            "calls": 0,
        }

    # 统计当月
    month_data = count_month(target_date.year, target_date.month, target_date)

    # 输出
    if fmt == "json":
        output = {
            "today": today_data,
            "month": {k: v for k, v in month_data.items() if k != "day_details"},
            "day_details": month_data["day_details"],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    elif fmt == "markdown":
        print(format_markdown(today_data, month_data))
    else:
        print(format_text(today_data, month_data))


if __name__ == "__main__":
    main()
