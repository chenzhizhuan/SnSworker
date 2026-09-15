#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""政企招投标三站统一采集 — 政府采购网 / 电信采购网 / 工信部

功能:
  - 三站统一采集标讯/政策，输出标准化字段 (title, date, source, url, region, category)
  - 关键词过滤（如"智能体 Agent AI 大模型"），命中标题才算
  - 自动去重（URL 去重）
  - 导出 CSV（含 BOM，Excel 友好）+ JSON
  - 支持指定站点、指定关键词、指定条数

用法:
  python gov_procurement_fetch.py                          # 采集全部三站，默认关键词
  python gov_procurement_fetch.py --kw "智能体,AI,大模型"    # 指定关键词
  python gov_procurement_fetch.py --only ccgp,miit          # 只采政府采购网+工信部
  python gov_procurement_fetch.py --top 5                   # 每站最多 5 条
  python gov_procurement_fetch.py --all                     # 不做关键词过滤，全量采集

实测（2026-09-10）:
  政府采购网: 列表页静态解析, 15 条公告
  电信采购网: StealthyFetcher 绕过瑞数, 27 条公告
  工信部:     搜索接口直通 JSON, 10 条政策文件
"""
import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime

import requests

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

DEFAULT_KW = "智能体,Agent,AI,大模型,人工智能,智慧,采购,招标,公告,通知"
DEFAULT_TOP = 20
OUTPUT_DIR = os.getcwd()


# ─── 工具函数 ───────────────────────────────────────────

def match_keywords(title, keywords):
    """标题是否命中任一关键词（不区分大小写）"""
    if not keywords:
        return True
    t = title.lower()
    return any(kw.lower() in t for kw in keywords)


def dedup(items):
    """按 (source, title, date) 去重，保留顺序

    注意: 电信采购网所有条目 URL 都是首页地址，不能按 URL 去重。
    """
    seen, out = set(), []
    for it in items:
        key = (it.get("source", ""), it.get("title", ""), it.get("date", ""))
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


def clean_title(t):
    """清理标题：去标签、去多余空白"""
    t = re.sub(r'<[^>]+>', '', t).strip()
    t = re.sub(r'\s+', ' ', t)
    return t


# ─── 1. 中国政府采购网 ──────────────────────────────────

def fetch_ccgp(keywords, top_n):
    """政府采购网 — 列表页静态解析"""
    results = []
    urls = [
        "http://www.ccgp.gov.cn/cggg/zygg/index.htm",     # 中央公告
        "http://www.ccgp.gov.cn/cggg/dfgg/index.htm",      # 地方公告
    ]
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Referer": "http://www.ccgp.gov.cn/"})

    for url in urls:
        try:
            r = s.get(url, timeout=15)
            r.encoding = "utf-8"
            if r.status_code != 200:
                continue
            # 提取 <a href="...">标题</a> + 附近日期
            # 政府采购网列表结构: <li><a href="...">标题</a> <span>2026-09-10</span></li>
            rows = re.findall(
                r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?(\d{4}-\d{2}-\d{2})',
                r.text, re.S
            )
            if not rows:
                # 兜底: 先提取链接，再按日期邻近配对
                links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.S)
                dates = re.findall(r'(\d{4}-\d{2}-\d{2})', r.text)
                for i, (href, title) in enumerate(links):
                    t = clean_title(title)
                    if len(t) >= 10 and ('ccgp' in href or href.startswith('/')):
                        date = dates[i] if i < len(dates) else ""
                        results.append({
                            "title": t, "date": date,
                            "source": "政府采购网", "url": href,
                            "region": "中央" if "zygg" in url else "地方",
                            "category": "公告",
                        })
            else:
                for href, title, date in rows:
                    t = clean_title(title)
                    if len(t) >= 6:
                        full_url = href if href.startswith("http") else f"http://www.ccgp.gov.cn{href}"
                        full_url = full_url.replace("ccgp.gov.cn.", "ccgp.gov.cn")  # 修复 URL 多余点
                        results.append({
                            "title": t, "date": date,
                            "source": "政府采购网", "url": full_url,
                            "region": "中央" if "zygg" in url else "地方",
                            "category": "公告",
                        })
        except Exception as e:
            print(f"  [ccgp] {url} 异常: {e}", file=sys.stderr)
        time.sleep(0.5)

    results = dedup(results)
    if keywords:
        results = [it for it in results if match_keywords(it["title"], keywords)]
    print(f"  [政府采购网] 采集 {len(results)} 条")
    return results[:top_n]


# ─── 2. 中国电信采购网 ──────────────────────────────────

def fetch_chinatelecom(keywords, top_n):
    """电信采购网 — StealthyFetcher 绕过瑞数后提取"""
    results = []
    try:
        from scrapling.fetchers import StealthyFetcher
    except ImportError:
        print("  [电信采购网] 需安装: pip install 'scrapling[fetchers]'", file=sys.stderr)
        return results

    try:
        page = StealthyFetcher.fetch(
            "https://caigou.chinatelecom.com.cn/",
            headless=True, network_idle=True, timeout=30000,
        )
        html = page.html_content if hasattr(page, "html_content") else str(page)

        # 提取公告: 日期做锚点, 向前找标题
        blocks = []
        for m in re.finditer(r'(20\d{2}-\d{2}-\d{2})', html):
            start = max(0, m.start() - 250)
            ctx = html[start:m.end() + 30]
            titles = re.findall(r'[>]([^<>]{6,80})[<]', ctx)
            clean = [t.strip() for t in titles
                     if len(t.strip()) >= 6
                     and not re.match(r'^[\d\s\-:：/]+$', t.strip())]
            if clean:
                blocks.append((m.group(1), clean[-1]))

        # 去重
        seen = set()
        for date, title in blocks:
            if (date, title) not in seen:
                seen.add((date, title))
                # 提取地区（标题前 【XX】 格式）
                region = ""
                rm = re.match(r'【(.+?)】', title)
                if rm:
                    region = rm.group(1)
                # 判断类别
                cat = "公告"
                if "公示" in title:
                    cat = "公示"
                elif "通知" in title:
                    cat = "通知"
                results.append({
                    "title": title, "date": date,
                    "source": "电信采购网",
                    "url": "https://caigou.chinatelecom.com.cn/",
                    "region": region, "category": cat,
                })
    except Exception as e:
        print(f"  [电信采购网] 异常: {e}", file=sys.stderr)

    results = dedup(results)
    if keywords:
        results = [it for it in results if match_keywords(it["title"], keywords)]
    print(f"  [电信采购网] 采集 {len(results)} 条")
    return results[:top_n]


# ─── 3. 工信部 ──────────────────────────────────────────

def fetch_miit(keywords, top_n):
    """工信部 — CMS 搜索接口直通 JSON"""
    results = []
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Referer": "https://www.miit.gov.cn/zwgk/zcwj/wjfb/index.html",
    })

    # 搜索接口: q 只传第一个关键词（接口不支持逗号分隔），留空返回最新
    q = keywords[0] if keywords else ""
    try:
        r = s.get(
            "https://www.miit.gov.cn/search-front-server/api/search/info",
            params={
                "websiteid": "110000000000000",
                "scope": "basic",
                "q": q, "pg": 1, "cateid": 196, "p": 1,
                "topl": 0, "sort": "time",
            },
            timeout=15,
        )
        j = r.json()
        items = j.get("data", {}).get("searchResult", {}).get("dataResults", [])
        if items is None:
            items = []
        for it in items:
            d = it.get("data", {})
            title = d.get("title", "")
            # cdate 是毫秒时间戳
            ts = d.get("cdate", "")
            date = ""
            if ts and ts.isdigit():
                date = datetime.fromtimestamp(int(ts) / 1000).strftime("%Y-%m-%d")
            url = d.get("url", "")
            if url and not url.startswith("http"):
                url = "https://www.miit.gov.cn" + url
            results.append({
                "title": title, "date": date,
                "source": "工信部", "url": url,
                "region": "中央", "category": "政策文件",
            })
    except Exception as e:
        print(f"  [工信部] 异常: {e}", file=sys.stderr)

    # 工信部接口已按关键词搜索，不需要再过滤
    print(f"  [工信部] 采集 {len(results)} 条")
    return results[:top_n]


# ─── 导出 ─────────────────────────────────────────────

def export_csv(items, path):
    """导出 CSV（含 BOM，Excel 友好）"""
    if not items:
        return
    fields = ["title", "date", "source", "url", "region", "category"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for it in items:
            w.writerow({k: it.get(k, "") for k in fields})


def export_json(items, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


# ─── 主函数 ───────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="政企招投标三站统一采集"
    )
    parser.add_argument("--kw", default=DEFAULT_KW,
                        help=f"关键词（逗号分隔），默认: {DEFAULT_KW}")
    parser.add_argument("--only", default="",
                        help="只采指定站点（ccgp,ct,miit 逗号分隔）")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP,
                        help=f"每站最多条数，默认 {DEFAULT_TOP}")
    parser.add_argument("--all", action="store_true",
                        help="不做关键词过滤，全量采集")
    parser.add_argument("-o", "--output", default="",
                        help="输出目录，默认脚本同目录")
    args = parser.parse_args()

    keywords = None if args.all else [k.strip() for k in args.kw.split(",") if k.strip()]
    sites = args.only.split(",") if args.only else ["ccgp", "ct", "miit"]
    out_dir = args.output or OUTPUT_DIR

    all_items = []
    print(f"=== 政企招投标采集 {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    if keywords:
        print(f"关键词: {keywords}")
    else:
        print("模式: 全量采集（无关键词过滤）")

    if "ccgp" in sites:
        print("\n[1/3] 政府采购网...")
        all_items.extend(fetch_ccgp(keywords, args.top))

    if "ct" in sites:
        print("\n[2/3] 电信采购网...")
        all_items.extend(fetch_chinatelecom(keywords, args.top))

    if "miit" in sites:
        print("\n[3/3] 工信部...")
        all_items.extend(fetch_miit(keywords, args.top))

    # 汇总
    print(f"\n=== 汇总: 共 {len(all_items)} 条 ===")
    for it in all_items[:10]:
        print(f"  [{it['source']}] {it['date']} | {it['title'][:45]}")

    # 导出（先确保输出目录存在，避免 -o 指定不存在目录时导出失败）
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    csv_path = os.path.join(out_dir, f"gov_procurement_{ts}.csv")
    json_path = os.path.join(out_dir, f"gov_procurement_{ts}.json")
    export_csv(all_items, csv_path)
    export_json(all_items, json_path)
    print(f"\n已导出:")
    print(f"  CSV : {csv_path}")
    print(f"  JSON: {json_path}")


if __name__ == "__main__":
    main()