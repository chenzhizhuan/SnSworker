#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小红书探索页热帖抓取 - Playwright + 登录 Cookie + DOM 提取

原理：小红书无公开热榜接口，搜索接口 edith.xiaohongshu.com 已 404（需 xsec_token），
homefeed API 需签名。最稳方案是浏览器登录一次导出 Cookie，Playwright 带 Cookie
打开探索页，深滚动触发懒加载后直接提取 DOM，按点赞数排序取最热。

实测（2026-09）：拿到 30 条笔记，Top 点赞 4.9 万；9月5日保存的 Cookie 9月10日仍有效。

用法:
    python xhs_explore_dom.py [cookies.json] [topN]
    # 默认 cookies.json 位置与 Top 10；可指定，如 python xhs_explore_dom.py xhs-operator/data/cookies.json 5
"""
import json
import sys
import asyncio
from playwright.async_api import async_playwright

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

DEFAULT_COOKIES = "xhs-operator/data/cookies.json"


def load_cookies(path: str) -> list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


async def fetch_xhs_explore(cookies_path: str = DEFAULT_COOKIES, top_n: int = 10) -> list:
    """返回探索页按点赞排序前 top_n 条 [{title, author, like_text, like_num, url}]"""
    cookies_list = load_cookies(cookies_path)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=UA,
            viewport={"width": 1440, "height": 900},
        )
        await ctx.add_cookies([{
            "name": c["name"], "value": c["value"],
            "domain": c["domain"], "path": c["path"],
            "expires": c.get("expires", -1) if c.get("expires", -1) > 0 else -1,
        } for c in cookies_list])
        page = await ctx.new_page()

        await page.goto("https://www.xiaohongshu.com/explore",
                        wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(6000)
        for _ in range(8):        # 深滚动触发懒加载
            await page.mouse.wheel(0, 2000)
            await page.wait_for_timeout(2500)

        notes = await page.evaluate("""() => {
            const cards = document.querySelectorAll('section.note-item, .note-item, [class*=note-item]');
            const result = [];
            cards.forEach((c) => {
                const t = c.querySelector('.title, [class*=title]');
                const a = c.querySelector('.author .name, a.author .name, [class*=author] .name');
                const link = c.querySelector('a[href*="/explore/"], a[href*="/discovery/item/"]');
                const href = link ? link.getAttribute('href') : '';
                const idMatch = href.match(/explore\\/([0-9a-f]+)/);
                let likeEl = c.querySelector('.like-wrapper .count, [class*=like] [class*=count]');
                if (!likeEl) likeEl = c.querySelector('span[class*=count]');
                let likeText = likeEl ? likeEl.textContent.trim() : '';
                let likeNum = 0;
                const m = likeText.match(/([0-9.]+)\\s*(万|w|W)?/);
                if (m) {
                    likeNum = parseFloat(m[1]);
                    if (m[2]) likeNum *= 10000;
                }
                if (t && idMatch) result.push({
                    id: idMatch[1],
                    title: t.textContent.trim(),
                    author: a ? a.textContent.trim() : '',
                    like_text: likeText, like_num: likeNum,
                    url: 'https://www.xiaohongshu.com/explore/' + idMatch[1],
                });
            });
            return result;
        }""")
        await browser.close()

    # 去重 + 按点赞排序
    seen, unique = {}, []
    for n in notes:
        if n["id"] not in seen:
            seen[n["id"]] = n
            unique.append(n)
    unique.sort(key=lambda x: x["like_num"], reverse=True)
    print(f"提取 {len(notes)} 条，去重后 {len(unique)} 条，Top {min(top_n, len(unique))}：")
    for n in unique[:top_n]:
        print(f"  {n['like_text']:>6} 赞 | {n['title'][:45]} | {n['author']}")
    return [{
        "platform": "小红书",
        "title": n["title"],
        "author": n["author"],
        "like_text": n["like_text"],
        "like_num": n["like_num"],
        "url": n["url"],
    } for n in unique[:top_n]]


if __name__ == "__main__":
    cpath = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_COOKIES
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    asyncio.run(fetch_xhs_explore(cpath, n))