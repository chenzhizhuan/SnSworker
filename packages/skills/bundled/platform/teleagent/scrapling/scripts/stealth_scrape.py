"""
隐身抓取采集器 — 绕过 Cloudflare 等反爬验证抓取页面
来源：Scrapling 官方 README StealthyFetcher/StealthySession 用法
用法：python stealth_scrape.py <URL> [CSS选择器] [--solve-cloudflare]
示例：python stealth_scrape.py https://quotes.toscrape.com/ ".quote .text::text"
      python stealth_scrape.py https://nopecha.com/demo/cloudflare "#padded_content a" --solve-cloudflare

依赖安装：pip install "scrapling[fetchers]" && scrapling install
"""

import sys
from scrapling.fetchers import StealthyFetcher, StealthySession


def stealth_scrape(url, css_selector=None, solve_cloudflare=False, headless=True):
    """使用隐身模式抓取页面，绕过反爬验证

    StealthyFetcher 基于 Patchright（Playwright 隐身分支），
    自动伪装浏览器指纹，可绕过 Cloudflare Turnstile 等验证。

    Args:
        url: 目标网页地址
        css_selector: CSS 选择器（可选），不传则返回页面全部文本
        solve_cloudflare: 是否启用 Cloudflare 专项求解（耗时更长）
        headless: 是否无头模式（False 可看到浏览器窗口）

    Returns:
        dict: 包含 url、status、data 的字典
    """
    # 开启自适应（网页结构变化时自动重新定位元素）
    StealthyFetcher.adaptive = True

    page = StealthyFetcher.fetch(
        url,
        headless=headless,
        network_idle=True,        # 等待网络空闲（页面完全加载）
        solve_cloudflare=solve_cloudflare,
    )

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


def stealth_session_scrape(urls, css_selector=None, solve_cloudflare=False):
    """使用隐身会话模式连续抓取多个页面

    会话模式下浏览器保持打开，避免反复启动/关闭的开销。
    适合需要连续抓取多个受保护页面的场景。

    Args:
        urls: 要抓取的 URL 列表
        css_selector: CSS 选择器（可选）
        solve_cloudflare: 是否启用 Cloudflare 专项求解

    Returns:
        list: 每个页面的提取结果
    """
    results = []

    with StealthySession(headless=True, solve_cloudflare=solve_cloudflare) as session:
        for url in urls:
            page = session.fetch(url, google_search=False)
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
        print("用法: python stealth_scrape.py <URL> [CSS选择器] [--solve-cloudflare]")
        print("示例: python stealth_scrape.py https://quotes.toscrape.com/ '.quote .text::text'")
        print("      python stealth_scrape.py https://nopecha.com/demo/cloudflare '#padded_content a' --solve-cloudflare")
        sys.exit(1)

    target_url = sys.argv[1]
    selector = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    do_solve = "--solve-cloudflare" in sys.argv

    print(f"隐身模式抓取: {target_url}")
    if do_solve:
        print("  已启用 Cloudflare 专项求解")
    if selector:
        print(f"  选择器: {selector}")

    result = stealth_scrape(target_url, selector, solve_cloudflare=do_solve)

    print(f"\n状态码: {result['status']}")
    if isinstance(result["data"], list):
        print(f"提取到 {len(result['data'])} 条数据:")
        for i, item in enumerate(result["data"][:10], 1):
            text = item[:80] if isinstance(item, str) else str(item)
            print(f"  {i}. {text}")
        if len(result["data"]) > 10:
            print(f"  ... 共 {len(result['data'])} 条")
    else:
        print(f"页面文本前500字: {result['data'][:500]}")
