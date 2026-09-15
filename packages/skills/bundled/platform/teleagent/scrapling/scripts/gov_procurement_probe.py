#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""政企招投标站点探测 - 政府采购网/电信采购网/工信部 一键实测

实测结论（2026-09-10）:
  1. 中国政府采购网 ccgp.gov.cn
     - 列表页静态可爬: requests 直接 200，公告含日期/标题/链接
     - 搜索接口 search.ccgp.gov.cn/bxsearch 触发"频繁访问"风控，需延时/代理
  2. 中国电信采购网 caigou.chinatelecom.com.cn
     - 瑞数(Riversafe)动态防护，纯 requests 只返回 JS 壳(2KB)
     - StealthyFetcher 可绕过，拿到 27 条真实公告
  3. 工信部 miit.gov.cn
     - 首页静态可爬(42条新闻)；政策文件走 CMS 搜索接口
     - search-front-server/api/search/info 纯 requests 可调(JSON)

用法: python gov_procurement_probe.py
"""
import requests
import re
import argparse


UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def probe_ccgp():
    """政府采购网 - 列表页静态探测"""
    print("=" * 50)
    print("[1] 中国政府采购网 ccgp.gov.cn")
    try:
        r = requests.get("http://www.ccgp.gov.cn/cggg/zygg/index.htm",
                         headers={"User-Agent": UA}, timeout=15)
        r.encoding = "utf-8"
        print(f"  status={r.status_code}, len={len(r.text)}")
        items = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.S)
        real = [(re.sub(r'<[^>]+>', '', t).strip(), h) for t, h in items
                if len(re.sub(r'<[^>]+>', '', t).strip()) >= 10]
        print(f"  有效公告 {len(real)} 条")
        for t, h in real[:3]:
            print(f"    {t[:45]} | {h[:60]}")
        dates = re.findall(r'(\d{4}-\d{2}-\d{2})', r.text)
        print(f"  最新日期: {dates[:3]}")
    except Exception as e:
        print(f"  异常: {e}")
    # 搜索接口风控测试
    try:
        r2 = requests.get("http://search.ccgp.gov.cn/bxsearch",
                          params={"searchtype": "1", "page_index": 1,
                                  "kw": "智能体", "start_time": "2026:09:01",
                                  "end_time": "2026:09:10"},
                          headers={"User-Agent": UA,
                                   "Referer": "http://www.ccgp.gov.cn/"},
                          timeout=15)
        if "频繁访问" in r2.text:
            print("  搜索接口: ⚠️ 触发'频繁访问'风控（需 Cookie/延时/代理）")
        else:
            print(f"  搜索接口: status={r2.status_code}, len={len(r2.text)}")
    except Exception as e:
        print(f"  搜索接口异常: {e}")


def probe_chinatelecom():
    """电信采购网 - 纯 requests 探测（预期瑞数壳）"""
    print("=" * 50)
    print("[2] 中国电信采购网 caigou.chinatelecom.com.cn")
    try:
        r = requests.get("https://caigou.chinatelecom.com.cn/",
                         headers={"User-Agent": UA}, timeout=15)
        html = r.text
        print(f"  requests: status={r.status_code}, len={len(html)}")
        print(f"  含瑞数特征(confuse/cjs.js): {'confuse' in html or 'cjs.js' in html}")
        print(f"  → 纯 requests 拿不到真实数据，需 StealthyFetcher")
    except Exception as e:
        print(f"  异常: {e}")

    # 用 StealthyFetcher 绕过（需安装 scrapling[fetchers]）
    try:
        from scrapling.fetchers import StealthyFetcher
        page = StealthyFetcher.fetch("https://caigou.chinatelecom.com.cn/",
                                     headless=True, network_idle=True,
                                     timeout=30000)
        html = page.html_content if hasattr(page, "html_content") else str(page)
        # 提取公告（日期+标题）
        blocks = []
        for m in re.finditer(r'(20\d{2}-\d{2}-\d{2})', html):
            start = max(0, m.start() - 250)
            ctx = html[start:m.end() + 30]
            titles = re.findall(r'[>]([^<>]{6,60})[<]', ctx)
            clean = [t.strip() for t in titles if len(t.strip()) >= 6
                     and not re.match(r'^[\d\s\-:：/]+$', t.strip())]
            if clean:
                blocks.append((m.group(1), clean[-1]))
        seen, out = set(), []
        for d, t in blocks:
            if (d, t) not in seen:
                seen.add((d, t))
                out.append((d, t))
        print(f"  StealthyFetcher: 绕过瑞数 ✅, 提取 {len(out)} 条公告")
        for d, t in out[:5]:
            print(f"    {d} | {t[:45]}")
    except ImportError:
        print("  需安装: pip install 'scrapling[fetchers]'")
    except Exception as e:
        print(f"  StealthyFetcher 异常: {e}")


def probe_miit():
    """工信部 - 搜索接口探测"""
    print("=" * 50)
    print("[3] 工信部 miit.gov.cn")
    try:
        r = requests.get("https://www.miit.gov.cn/search-front-server/api/search/info",
                         params={"websiteid": "110000000000000", "scope": "basic",
                                 "q": "", "pg": 1, "cateid": 196, "p": 1,
                                 "topl": 0, "sort": "time"},
                         headers={"User-Agent": UA,
                                  "Referer": "https://www.miit.gov.cn/zwgk/zcwj/wjfb/index.html"},
                         timeout=15)
        j = r.json()
        results = j.get("data", {}).get("searchResult", {}).get("dataResults", [])
        print(f"  搜索接口: status={r.status_code}, 结果 {len(results)} 条")
        for it in results[:3]:
            d = it.get("data", {})
            print(f"    {d.get('title', '')[:50]}")
    except Exception as e:
        print(f"  异常: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="政企采购站点探测")
    parser.add_argument("--only", choices=["ccgp", "ct", "miit"],
                        help="只测指定站点")
    args = parser.parse_args()

    if args.only == "ccgp":
        probe_ccgp()
    elif args.only == "ct":
        probe_chinatelecom()
    elif args.only == "miit":
        probe_miit()
    else:
        probe_ccgp()
        probe_chinatelecom()
        probe_miit()