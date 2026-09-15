"""
会话模式采集器 — 保持 Cookie 与登录态进行多页面连续抓取
来源：Scrapling 官方 README Session 用法示例
用法：python session_scrape.py <URL1> <URL2> ...
示例：python session_scrape.py https://quotes.toscrape.com/page/1/ https://quotes.toscrape.com/page/2/
"""

import sys
import json
from scrapling.fetchers import FetcherSession


def scrape_with_session(urls, css_selector=None):
    """使用会话模式连续抓取多个页面

    会话模式下 Cookie 和连接状态会跨请求保持，
    适合需要登录或连续操作的场景。

    Args:
        urls: 要抓取的 URL 列表
        css_selector: CSS 选择器（可选）

    Returns:
        list: 每个页面的提取结果
    """
    results = []

    with FetcherSession(impersonate='chrome') as session:
        for url in urls:
            page = session.get(url, stealthy_headers=True)

            page_data = {
                "url": url,
                "status": page.status,
                "data": []
            }

            if css_selector:
                page_data["data"] = page.css(css_selector).getall()
            else:
                page_data["data"] = page.get_all_text()

            results.append(page_data)

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python session_scrape.py <URL1> <URL2> ...")
        print("示例: python session_scrape.py https://quotes.toscrape.com/page/1/ https://quotes.toscrape.com/page/2/")
        sys.exit(1)

    target_urls = sys.argv[1:]
    selector = ".quote .text::text"  # 默认提取语录文本

    print(f"会话模式抓取 {len(target_urls)} 个页面")
    results = scrape_with_session(target_urls, selector)

    for r in results:
        print(f"\n[{r['status']}] {r['url']}")
        print(f"  提取到 {len(r['data'])} 条数据")
        for i, item in enumerate(r["data"][:3], 1):
            print(f"    {i}. {item[:70]}")
