"""
基础请求采集器 — 单页抓取并提取数据
来源：Scrapling 官方 README 基础用法示例
用法：python main.py <URL> [CSS选择器]
示例：python main.py https://quotes.toscrape.com/ ".quote .text::text"
"""

import sys
import json
from scrapling.fetchers import Fetcher


def scrape(url, css_selector=None):
    """抓取单个页面并提取数据

    Args:
        url: 目标网页地址
        css_selector: CSS 选择器（可选），不传则返回页面全部文本

    Returns:
        dict: 包含 url、status、data 的字典
    """
    page = Fetcher.get(url)

    result = {
        "url": url,
        "status": page.status,
        "data": []
    }

    if css_selector:
        result["data"] = page.css(css_selector).getall()
    else:
        result["data"] = page.get_all_text()

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python main.py <URL> [CSS选择器]")
        print("示例: python main.py https://quotes.toscrape.com/ '.quote .text::text'")
        sys.exit(1)

    target_url = sys.argv[1]
    selector = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"正在抓取: {target_url}")
    result = scrape(target_url, selector)

    if isinstance(result["data"], list):
        print(f"状态码: {result['status']}")
        print(f"提取到 {len(result['data'])} 条数据:")
        for i, item in enumerate(result["data"][:10], 1):
            text = item[:80] if isinstance(item, str) else str(item)
            print(f"  {i}. {text}")
        if len(result["data"]) > 10:
            print(f"  ... 共 {len(result['data'])} 条")
    else:
        print(f"状态码: {result['status']}")
        print(f"页面文本前500字: {result['data'][:500]}")
