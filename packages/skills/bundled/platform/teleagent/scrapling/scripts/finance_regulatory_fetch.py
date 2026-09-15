#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""金融监管与金融行业信息统一采集 — 央行 / 证监会 / 招标投标公共服务平台

功能:
  - 三站统一采集金融监管动态/招标公告，输出标准化字段 (title, date, source, url, region, category)
  - 关键词过滤（如"智能体 Agent AI 金融 招标"），命中标题才算
  - 自动去重（(source, title, date) 去重）
  - 导出 CSV（含 BOM，Excel 友好）+ JSON
  - 支持指定站点、指定关键词、指定条数

用法:
  python finance_regulatory_fetch.py                          # 采集全部三站，默认关键词
  python finance_regulatory_fetch.py --kw "金融,AI,智能体"     # 指定关键词
  python finance_regulatory_fetch.py --only pbc,csrc          # 只采央行+证监会
  python finance_regulatory_fetch.py --top 5                  # 每站最多 5 条
  python finance_regulatory_fetch.py --all                    # 不做关键词过滤，全量采集

实测（2026-09-13）:
  央行: 列表页静态解析, 新闻发布栏目 15 条; 详情页 TRS_Editor/xl_xxy 容器可提取正文
  证监会: 列表页静态解析, 新闻发布栏目 18 条; 详情页内容可提取
  招标投标公共服务平台: 搜索列表分页 20 条/页; 详情 API 为 JS 混淆壳, 只取列表

踩坑记录:
  - 央行需显式 r.encoding = "utf-8"; 标题提取用 <a href>文本</a>, 勿用 title 属性(有 istitle 干扰)
  - 央行详情正文容器: class="TRS_Editor" 或 class="xl_xxy"
  - 招标平台必须带 searchDate(当前日期减N天), 否则查不到数据
  - 招标平台公告详情链接为 javascript:urlOpen('uuid'), 真实详情在 ctbpsp.com SPA 中, API 反爬
  - 金融监管总局(nfra) 为 JS 壳 + 接口全 404, 放弃
  - 中央政采(zycg) REST 接口返回 {"msg":"公告列表查询失败","code":"-1"}, 站端问题, 放弃
"""
import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, date, timedelta

import requests

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

DEFAULT_KW = "智能体,Agent,AI,大模型,人工智能,金融,银行,证券,保险,招标,采购,公告,通知"
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
    """按 (source, title, date) 去重，保留顺序"""
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


def guess_category(title):
    """按标题粗判类别"""
    if any(k in title for k in ("中标", "成交", "结果")):
        return "中标结果"
    if any(k in title for k in ("变更", "更正", "补充")):
        return "变更公告"
    if any(k in title for k in ("候选人", "预中标", "评标")):
        return "候选人公示"
    if "资格" in title and "预审" in title:
        return "资格预审"
    if any(k in title for k in ("招标", "采购", "询价", "磋商", "比选")):
        return "招标公告"
    if any(k in title for k in ("公示", "公告")):
        return "公告"
    if "通知" in title:
        return "通知"
    return "动态"


# ─── 1. 中国人民银行 ────────────────────────────────────

PBC_SECTIONS = [
    ("新闻发布", "http://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html"),
    ("货币政策", "http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125440/index.html"),
]

def fetch_pbc(keywords, top_n):
    """央行 — 静态列表页解析（新闻发布 / 货币政策）"""
    results = []
    s = requests.Session()
    s.headers.update({"User-Agent": UA})

    for section, url in PBC_SECTIONS:
        try:
            r = s.get(url, timeout=15)
            r.encoding = "utf-8"
            if r.status_code != 200:
                continue
            # 列表结构: <a href="/goutongjiaoliu/.../index.html">标题</a></font>
            #           <span class="hui12">2026-09-11</span>
            rows = re.findall(
                r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
                r'<span class="hui12">(\d{4}-\d{2}-\d{2})</span>',
                r.text, re.S
            )
            for href, title, date_str in rows:
                t = clean_title(title)
                # 过滤非详情链接（栏目入口、导航、首页等）
                # 央行详情 URL 形如 /goutongjiaoliu/113456/113469/2026091018550019961/index.html
                if len(t) < 6:
                    continue
                if not re.search(r'/20\d{10,}/', href):
                    continue
                full_url = href if href.startswith("http") else f"http://www.pbc.gov.cn{href}"
                results.append({
                    "title": t, "date": date_str,
                    "source": "央行", "url": full_url,
                    "region": "中央", "category": section,
                })
        except Exception as e:
            print(f"  [央行] {url} 异常: {e}", file=sys.stderr)
        time.sleep(0.5)

    results = dedup(results)
    if keywords:
        results = [it for it in results if match_keywords(it["title"], keywords)]
    print(f"  [央行] 采集 {len(results)} 条")
    return results[:top_n]


# ─── 2. 证监会 ─────────────────────────────────────────────

CSRC_SECTIONS = [
    ("新闻发布", "http://www.csrc.gov.cn/csrc/c100028/common_list.shtml"),
    ("信息公开", "http://www.csrc.gov.cn/csrc/c101954/common_list.shtml"),
]

def fetch_csrc(keywords, top_n):
    """证监会 — 静态列表页列表（新闻发布 / 信息公开）"""
    results = []
    s = requests.Session()
    s.headers.update({"User-Agent": UA})

    for section, url in CSRC_SECTIONS:
        try:
            r = s.get(url, timeout=15)
            r.encoding = "utf-8"
            if r.status_code != 200:
                continue
            # 列表结构: <a href="/csrc/c100028/c1615671/content.shtml">标题</a>
            rows = re.findall(
                r'<a[^>]+href="([^"]*content\.shtml)"[^>]*>([^<]{6,})</a>',
                r.text
            )
            for href, title in rows:
                t = clean_title(title)
                full_url = href if href.startswith("http") else f"http://www.csrc.gov.cn{href}"
                results.append({
                    "title": t, "date": "",
                    "source": "证监会", "url": full_url,
                    "region": "中央", "category": section,
                })
        except Exception as e:
            print(f"  [证监会] {url} 异常: {e}", file=sys.stderr)
        time.sleep(0.5)

    results = dedup(results)
    if keywords:
        results = [it for it in results if match_keywords(it["title"], keywords)]
    print(f"  [证监会] 采集 {len(results)} 条")
    return results[:top_n]


# ─── 3. 中国招标投标公共服务平台 ──────────────────────────

def fetch_cebpub(keywords, top_n):
    """招标投标公共服务平台 — 公告列表分页"""
    results = []
    s = requests.Session()
    s.headers.update({"User-Agent": UA})

    try:
        # 必须带 searchDate（当前日期减 N 天），否则接口查不到数据
        days = 30
        t = date.today() - timedelta(days=days)
        url = (
            "https://bulletin.cebpubservice.com/xxfbcmses/search/bulletin.html?"
            f"searchDate={t.strftime('%Y-%m-%d')}&dates={days}&word="
            "&categoryId=88&industryName=&area=&status="
            "&publishMedia=&sourceInfo=&showStatus=&page=1"
        )
        r = s.get(url, timeout=20)
        if r.status_code != 200:
            print(f"  [招标平台] 状态码 {r.status_code}", file=sys.stderr)
            return results

        trs = re.findall(r'<tr[^>]*>.*?</tr>', r.text, re.S)
        for tr in trs[1:]:  # 跳过表头
            tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)
            if len(tds) < 6:
                continue
            # 第1列: javascript:urlOpen('uuid') + 标题
            uuid_m = re.search(r"urlOpen\('([^']+)'\)", tds[0])
            title_m = re.search(r'<a[^>]+>(.*?)</a>', tds[0], re.S)
            if not (uuid_m and title_m):
                continue
            uuid = uuid_m.group(1)
            title = clean_title(title_m.group(1))
            # 第2列: 分类  第3列: 地区  第4列: 平台  第5列: 日期
            cat_raw = clean_title(tds[1]) if len(tds) > 1 else ""
            region_raw = clean_title(tds[2]) if len(tds) > 2 else ""
            platform = clean_title(tds[3]) if len(tds) > 3 else ""
            date_str = clean_title(tds[4]) if len(tds) > 4 else ""
            # 地区列形如 【辽宁】
            region = re.sub(r'[【】]', '', region_raw)
            if not region:
                rm = re.match(r'【(.+?)】', title)
                region = rm.group(1) if rm else ""
            results.append({
                "title": title, "date": date_str,
                "source": "招标投标公共服务平台", "url": f"https://ctbpsp.com/#/bulletinDetail?uuid={uuid}",
                "region": region, "category": cat_raw or "招标公告",
            })
    except Exception as e:
        print(f"  [招标公告] 异常: {e}", file=sys.stderr)

    results = dedup(results)
    if keywords:
        results = [it for it in results if match_keywords(it["title"], keywords)]
    print(f"  [招标公告] 采集 {len(results)} 条")
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
        description="金融监管与金融行业信息统一采集"
    )
    parser.add_argument("--kw", default=DEFAULT_KW,
                        help=f"关键词（逗号分隔），默认: {DEFAULT_KW}")
    parser.add_argument("--only", default="",
                        help="只采指定站点（pbc,csrc,ceb 逗号分隔）")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP,
                        help=f"每站最多条数，默认 {DEFAULT_TOP}")
    parser.add_argument("--all", action="store_true",
                        help="不做关键词过滤，全量采集")
    parser.add_argument("-o", "--output", default="",
                        help="输出目录，默认脚本同目录")
    args = parser.parse_args()

    keywords = None if args.all else [k.strip() for k in args.kw.split(",") if k.strip()]
    sites = args.only.split(",") if args.only else ["pbc", "csrc", "fin"]
    out_dir = args.output or OUTPUT_DIR

    all_items = []
    print(f"=== 金融监管与金融行业采集 {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    if keywords:
        print(f"关键词: {keywords}")
    else:
        print("模式: 全量采集（无关键词过滤）")

    if "pbc" in sites:
        print("\n[1/3] 央行...")
        all_items.extend(fetch_pbc(keywords, args.top))

    if "csrc" in sites:
        print("\n[2/3] 证监会...")
        all_items.extend(fetch_csrc(keywords, args.top))

    if "fin" in sites:
        print("\n[3/3] 招标投标公共服务平台...")
        all_items.extend(fetch_cebpub(keywords, args.top))

    # 汇总
    print(f"\n=== 汇总: 共 {len(all_items)} 条 ===")
    for it in all_items[:10]:
        print(f"  [{it['source']}] {it['date']} | {it['title'][:45]}")

    # 导出
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    csv_path = os.path.join(out_dir, f"finance_regulatory_{ts}.csv")
    json_path = os.path.join(out_dir, f"finance_regulatory_{ts}.json")
    export_csv(all_items, csv_path)
    export_json(all_items, json_path)
    print(f"\n已导出:")
    print(f"  CSV : {csv_path}")
    print(f"  JSON: {json_path}")


if __name__ == "__main__":
    main()