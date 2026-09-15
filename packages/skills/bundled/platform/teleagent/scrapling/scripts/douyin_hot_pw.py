#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抖音热榜抓取 - Playwright 页面内 fetch（自动带 a_bogus 签名环境）

原理：抖音 Web 端热榜 API 需要 a_bogus 签名，逆向算法成本高且易失效。
本脚本在 Playwright 页面上下文中直接 fetch API，由页面 JS 自动生成签名，零逆向成本。

实测（2026-09）：成功拿到 51 条热点话题。
用法:
    python douyin_hot_pw.py [topN]
    # 默认输出 Top 3，可指定数量，如 python douyin_hot_pw.py 10
"""
import json
import sys
import asyncio
from playwright.async_api import async_playwright

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

HOT_API = ("https://www.douyin.com/aweme/v1/web/hot/search/list/"
           "?device_platform=webapp&aid=6383&channel=channel_pc_web"
           "&detail_list=1&source=6&pc_client_type=1"
           "&version_code=190500&version_name=19.5.0")


async def fetch_douyin_hot(top_n: int = 3) -> list:
    """返回抖音热点榜前 top_n 条 [{word, hot_value, schema_url, ...}]"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=UA,
            viewport={"width": 1440, "height": 900},
        )
        page = await ctx.new_page()
        # 1. 先访问热榜页，让页面 JS 跑起来（种 cookie、加载签名环境）
        await page.goto("https://www.douyin.com/hot",
                        wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(5000)
        # 2. 在页面上下文中 fetch API（自动带签名环境 a_bogus）
        result = await page.evaluate("""
        async (url) => {
            const resp = await fetch(url, {
                headers: {
                    'Accept': 'application/json, text/plain, */*',
                    'Referer': 'https://www.douyin.com/hot',
                }
            });
            return await resp.text();
        }
        """, HOT_API)
        await browser.close()

    j = json.loads(result)
    words = j["data"]["word_list"]
    print(f"榜单条目数: {len(words)}")
    out = []
    for w in words[:top_n]:
        label = w.get("label")
        if isinstance(label, dict):
            label = label.get("text", "")
        item = {
            "platform": "抖音",
            "title": w.get("word", ""),
            "hot_value": w.get("hot_value", ""),
            "position": w.get("position", ""),
            "label": label,
            "url": w.get("schema_url", ""),
        }
        out.append(item)
        print(f"  - {item['title']} | 热度:{item['hot_value']} | {item['url']}")
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    out = asyncio.run(fetch_douyin_hot(n))
    with open("douyin_hot.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"已写入 douyin_hot.json（{len(out)} 条）")