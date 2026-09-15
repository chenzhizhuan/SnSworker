#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深技大热点新闻抓取脚本
抓取深圳技术大学官网(https://www.sztu.edu.cn)「技大焦点」下的
「校园新闻」「媒体聚焦」，以及「科研实训」下的「科学研究」三个栏目，
按时间窗口筛选新闻，输出结构化 JSON。

用法:
    python fetch_sztu_news.py [--days 7] [--max-pages 3] [--output sztu_news.json]

参数:
    --days        目标时间窗口天数（默认 1）
    --max-pages   每个栏目最多翻页数（默认 3）
    --output      输出 JSON 文件路径（默认 sztu_news.json）

输出 JSON 结构:
    {
      "generated_at": "2026-08-27 10:00:00",
      "query_days": 1,
      "effective_window_days": 7,   # 实际生效窗口（自动放宽后）
      "total": 12,
      "items": [
        {
          "column": "校园新闻" | "媒体聚焦",
          "title": "新闻标题",
          "date": "2026-08-08",
          "media": "深圳特区报",       # 仅媒体聚焦有
          "summary": "摘要文字",
          "url": "https://www.sztu.edu.cn/info/1003/4447.htm",
          "is_external": false
        }
      ]
    }
"""

import argparse
import datetime
import json
import re
import sys

import requests
from bs4 import BeautifulSoup

BASE = "https://www.sztu.edu.cn"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# 栏目配置: 名称、列表页相对路径、翻页路径模板
COLUMNS = {
    "xynews": {"name": "校园新闻", "list": "jdjd/xyxw.htm", "page": "jdjd/xyxw/{n}.htm"},
    "mtjj":   {"name": "媒体聚焦", "list": "jdjd/mtjj.htm", "page": "jdjd/mtjj/{n}.htm"},
    "kyyx":   {"name": "科学研究", "list": "kysx/kxyj.htm", "page": "kysx/kxyj/{n}.htm"},
}

DATE_RE = re.compile(r"(\d{4})[/年.-](\d{1,2})[/月.-](\d{1,2})")


def fetch_page(url, timeout=20, retries=2):
    """抓取页面，失败自动重试（默认 2 次重试 + 1 次退避）。"""
    import time
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException as e:
            if attempt < retries:
                wait = 2 * (attempt + 1)  # 退避：2s, 4s, ...
                print(f"[warn] 请求失败(第{attempt+1}次)，{wait}s 后重试: {url} | {e}", file=sys.stderr)
                time.sleep(wait)
            else:
                raise
    # 理论不会走到这里
    raise requests.RequestException(f"重试 {retries} 次后仍失败: {url}")


def parse_date(text):
    m = DATE_RE.search(text or "")
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def to_abs(href):
    if not href:
        return ""
    if href.startswith("http"):
        return href
    return BASE + "/" + href.lstrip("./")


def fetch_column(key, max_pages):
    """抓取一个栏目的新闻列表。"""
    col = COLUMNS[key]
    items, seen = [], set()

    for page_no in range(1, max_pages + 1):
        url = BASE + "/" + (col["list"] if page_no == 1 else col["page"].format(n=page_no))
        try:
            soup = fetch_page(url)
        except requests.RequestException as e:
            print(f"[warn] {col['name']} 第{page_no}页抓取失败: {e}", file=sys.stderr)
            break

        found = False
        # 新闻条目均为 <a> 包裹 .yy-ifo 区块
        for a in soup.select("a"):
            ifo = a.select_one(".yy-ifo")
            if ifo is None:
                continue
            href = a.get("href", "")
            is_external = href.startswith("http") and "sztu.edu.cn" not in href
            if not (is_external or re.search(r"info/\d+/\d+\.htm", href)):
                continue

            span = ifo.select_one("span")
            h3 = ifo.select_one("h3")
            if h3 is None:
                continue
            date = parse_date(span.get_text() if span else "")
            title = h3.get_text(" ", strip=True)
            # 媒体聚焦标题形如 「<span>深圳特区报</span>深圳毕业生解锁别样青春」
            media = ""
            if key == "mtjj":
                hs = h3.select_one("span")
                if hs:
                    media = hs.get_text(strip=True)
                    title = h3.get_text(" ", strip=True).replace(media, "", 1).strip()
            p = ifo.select_one("p")
            summary = p.get_text(" ", strip=True) if p else ""

            dedup = (title[:40], href)
            if dedup in seen:
                continue
            seen.add(dedup)

            items.append({
                "column": col["name"],
                "title": title,
                "date": date.isoformat() if date else "",
                "media": media,
                "summary": summary,
                "url": to_abs(href),
                "is_external": bool(is_external),
            })
            found = True

        print(f"[info] {col['name']} 第{page_no}页: 解析 {len(items)} 条(累计)", file=sys.stderr)
        if not found:
            break

    return items


def select_by_window(items, days):
    """按时间窗口筛选；窗口内无结果则自动放宽（每轮 +7 天，最多 5 轮）。"""
    today = datetime.date.today()
    for extra in range(6):
        cutoff = today - datetime.timedelta(days=days + extra * 7)
        matched = [it for it in items if it["date"] and cutoff <= datetime.date.fromisoformat(it["date"]) <= today]
        if matched:
            return matched, days + extra * 7
    return [], days + 5 * 7


def main():
    ap = argparse.ArgumentParser(description="抓取深圳技术大学官网热点新闻")
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--max-pages", type=int, default=3)
    ap.add_argument("--output", default="sztu_news.json")
    args = ap.parse_args()

    all_items = []
    for key in COLUMNS:
        try:
            all_items.extend(fetch_column(key, args.max_pages))
        except Exception as e:
            print(f"[warn] 栏目 {key} 异常: {e}", file=sys.stderr)

    # 跨栏目去重：同一标题（前40字）+ URL 出现在多个栏目时只保留首条
    global_seen = set()
    unique_items = []
    for it in all_items:
        dedup_key = (it["title"][:40], it["url"])
        if dedup_key in global_seen:
            continue
        global_seen.add(dedup_key)
        unique_items.append(it)
    all_items = unique_items

    if not all_items:
        print("[error] 未抓到任何新闻，请检查网络或站点结构", file=sys.stderr)
        sys.exit(1)

    matched, window = select_by_window(all_items, args.days)
    matched.sort(key=lambda x: x["date"], reverse=True)

    result = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "query_days": args.days,
        "effective_window_days": window,
        "total": len(matched),
        "items": matched,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[ok] 共 {len(matched)} 条新闻（实际窗口 {window} 天），已写入 {args.output}")


if __name__ == "__main__":
    main()