"""
浏览器自动化采集器 — JS 动态渲染页面抓取（Playwright 驱动）
来源：Scrapling 官方 README DynamicFetcher/DynamicSession 用法
用法：python dynamic_render.py <URL> [CSS选择器] [--visible] [--xpath XPATH]
示例：python dynamic_render.py https://quotes.toscrape.com/ ".quote .text::text"
      python dynamic_render.py https://quotes.toscrape.com/ --xpath "//span[@class='text']/text()"
      python dynamic_render.py https://quotes.toscrape.com/ ".quote" --visible

依赖安装：pip install "scrapling[fetchers]" && scrapling install
"""

import sys
from scrapling.fetchers import DynamicFetcher, DynamicSession


def dynamic_scrape(url, css_selector=None, xpath=None, headless=True, network_idle=True):
    """使用浏览器自动化抓取 JS 动态渲染页面

    DynamicFetcher 基于 Playwright Chromium，支持完整的 JS 执行，
    适合抓取 Vue/React/Angular 等 SPA 单页应用。

    Args:
        url: 目标网页地址
        css_selector: CSS 选择器（可选）
        xpath: XPath 选择器（可选，与 css_selector 二选一）
        headless: 是否无头模式（False 可看到浏览器窗口，便于调试）
        network_idle: 是否等待网络空闲（确保 AJAX 请求完成）

    Returns:
        dict: 包含 url、status、data 的字典
    """
    page = DynamicFetcher.fetch(
        url,
        headless=headless,
        network_idle=network_idle,
    )

    result = {
        "url": url,
        "status": page.status,
        "data": []
    }

    if xpath:
        result["data"] = page.xpath(xpath).getall()
    elif css_selector:
        result["data"] = page.css(css_selector).getall()
    else:
        result["data"] = page.get_all_text()

    return result


def dynamic_session_scrape(urls, css_selector=None, xpath=None, headless=True):
    """使用浏览器会话模式连续抓取多个 JS 渲染页面

    会话模式下浏览器保持打开，避免反复启动/关闭的开销。
    适合需要连续抓取多个动态页面的场景。

    Args:
        urls: 要抓取的 URL 列表
        css_selector: CSS 选择器（可选）
        xpath: XPath 选择器（可选）
        headless: 是否无头模式

    Returns:
        list: 每个页面的提取结果
    """
    results = []

    with DynamicSession(headless=headless, disable_resources=False, network_idle=True) as session:
        for url in urls:
            page = session.fetch(url, load_dom=False)

            page_data = {
                "url": url,
                "status": page.status,
                "data": []
            }

            if xpath:
                page_data["data"] = page.xpath(xpath).getall()
            elif css_selector:
                page_data["data"] = page.css(css_selector).getall()
            else:
                page_data["data"] = page.get_all_text()

            results.append(page_data)

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python dynamic_render.py <URL> [CSS选择器] [--visible] [--xpath XPATH]")
        print("示例: python dynamic_render.py https://quotes.toscrape.com/ '.quote .text::text'")
        print("      python dynamic_render.py https://quotes.toscrape.com/ --xpath \"//span[@class='text']/text()\"")
        print("      python dynamic_render.py https://quotes.toscrape.com/ '.quote' --visible  (显示浏览器窗口)")
        sys.exit(1)

    target_url = sys.argv[1]
    args = sys.argv[2:]

    visible = "--visible" in args
    xpath = None
    selector = None

    # 解析 --xpath 参数
    if "--xpath" in args:
        idx = args.index("--xpath")
        if idx + 1 < len(args):
            xpath = args[idx + 1]
    else:
        # 非 -- 开头的参数视为 CSS 选择器
        selector = next((a for a in args if not a.startswith("--")), None)

    print(f"浏览器自动化抓取: {target_url}")
    if visible:
        print("  模式: 可见窗口（调试模式）")
    if xpath:
        print(f"  XPath: {xpath}")
    elif selector:
        print(f"  CSS 选择器: {selector}")

    result = dynamic_scrape(target_url, css_selector=selector, xpath=xpath, headless=not visible)

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
