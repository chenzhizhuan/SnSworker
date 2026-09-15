#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""国内四大平台反爬可用性一键探测脚本
实测验证（2026-09，scrapling 0.4.15）：
  - 百度贴吧：Fetcher/FetcherSession/StealthyFetcher 全部 403 安全验证，纯请求层无法绕过
  - 微博：先完成 visitor 访客流程再调 PC 热搜接口可拿 52 条热搜
  - 知乎：PC 网页/API 均需登录，但移动端 API 直接 200 出 JSON（无签名）
  - B站：页面是 JS 壳，先访问主站种 buvid3 cookie 再调 API 全部打通
用法：
  python domestic_platform_probe.py            # 全平台探测
  python domestic_platform_probe.py zhihu      # 只测知乎
依赖：requests（仅标准库之外的这一个）
"""
import sys
import time

import requests

MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")
PC_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def probe_tieba():
    """百度贴吧：预期 403 百度安全验证（IP 级风控）"""
    print("\n===== 百度贴吧 =====")
    s = requests.Session()
    s.headers.update({"User-Agent": PC_UA, "Referer": "https://www.baidu.com/"})
    try:
        r = s.get("https://tieba.baidu.com/f?kw=%E7%8E%8B%E8%80%85%E8%8D%A3%E8%80%80", timeout=15)
        print(f"  HTTP {r.status_code} | title 含'百度安全验证': {'安全验证' in r.text}")
        print("  结论：IP 风控 + 旋转验证码，纯 HTTP 无法绕过；需登录 Cookie 或 Playwright 真人过验证")
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
    time.sleep(1)


def probe_weibo():
    """微博：visitor 访客流程后调 PC 热搜接口"""
    print("\n===== 微博 =====")
    s = requests.Session()
    s.headers.update({"User-Agent": PC_UA, "Referer": "https://weibo.com/"})
    try:
        # 1. 触发访客系统
        r0 = s.get("https://weibo.com/", allow_redirects=False, timeout=15)
        print(f"  首页: HTTP {r0.status_code} -> {r0.headers.get('Location','')[:50]}")
        # 2. 完成访客流程
        s.get("https://passport.weibo.com/visitor/visitor",
              params={"entry": "miniblog", "a": "enter", "url": "https://weibo.com/",
                      "domain": ".weibo.com"}, timeout=15)
        # 3. 热搜接口
        r = s.get("https://weibo.com/ajax/side/hotSearch", timeout=15)
        j = r.json()
        realtime = j.get("data", {}).get("realtime", [])
        print(f"  hotSearch: HTTP {r.status_code} | 热搜 {len(realtime)} 条")
        for item in realtime[:3]:
            print(f"    - {item.get('word','')[:30]} 热:{item.get('num','')}")
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
    time.sleep(1)


def probe_zhihu():
    """知乎：移动端 API 直通"""
    print("\n===== 知乎 =====")
    s = requests.Session()
    s.headers.update({"User-Agent": MOBILE_UA, "Referer": "https://www.zhihu.com/"})
    try:
        r = s.get("https://api.zhihu.com/topstory/hot-lists/total?limit=5", timeout=15)
        j = r.json()
        data = j.get("data", [])
        print(f"  热榜 API: HTTP {r.status_code} | {len(data)} 条")
        for item in data[:3]:
            t = item.get("target", {})
            print(f"    - {t.get('title','')[:40]}")
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
    time.sleep(1)


def probe_bilibili():
    """B站：预热种 cookie 后调 API"""
    print("\n===== B站 =====")
    s = requests.Session()
    s.headers.update({"User-Agent": PC_UA, "Referer": "https://www.bilibili.com/"})
    try:
        # 1. 预热主站
        s.get("https://www.bilibili.com/", timeout=15)
        cookies = {c.name for c in s.cookies}
        print(f"  主站 cookies: {cookies}")
        # 2. 热门 API
        r = s.get("https://api.bilibili.com/x/web-interface/popular?ps=3&pn=1", timeout=15)
        j = r.json()
        if j.get("code") == 0:
            print(f"  popular: HTTP {r.status_code} code=0 | {len(j['data']['list'])} 条")
            for it in j["data"]["list"][:3]:
                print(f"    - {it.get('title','')[:40]} | UP:{it.get('owner',{}).get('name')}")
        else:
            print(f"  popular: code={j.get('code')} msg={j.get('message')}")
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
    time.sleep(1)


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    probes = {"tieba": probe_tieba, "weibo": probe_weibo, "zhihu": probe_zhihu, "bilibili": probe_bilibili}
    if only:
        probes[only]()
    else:
        for fn in probes.values():
            fn()


if __name__ == "__main__":
    main()