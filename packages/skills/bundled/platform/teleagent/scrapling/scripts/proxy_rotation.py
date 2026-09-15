"""
代理轮换采集器 — 多代理自动轮换抓取，防 IP 封禁
来源：Scrapling 官方 ProxyRotator + FetcherSession 用法
用法：python proxy_rotation.py <URL> <代理1> <代理2> ... [CSS选择器]
示例：python proxy_rotation.py https://quotes.toscrape.com/ \
        http://proxy1:8080 http://user:pass@proxy2:3128 ".quote .text::text"

代理格式：
  字符串格式: "http://proxy:8080" 或 "http://user:pass@proxy:8080"
  也支持 Playwright dict 格式（在代码中传入）

依赖安装：pip install "scrapling[fetchers]"
"""

import sys
from scrapling.fetchers import FetcherSession
from scrapling.engines.toolbelt import ProxyRotator


def scrape_with_proxy_rotation(url, proxy_list, css_selector=None, impersonate="chrome"):
    """使用代理轮换策略抓取单个页面

    ProxyRotator 支持：
    - 循环轮换（默认策略，按顺序逐一使用）
    - 自定义轮换策略（传入 callable）
    - 字符串格式和 Playwright dict 格式代理

    Args:
        url: 目标网页地址
        proxy_list: 代理列表，如 ["http://proxy1:8080", "http://user:pass@proxy2:3128"]
        css_selector: CSS 选择器（可选）
        impersonate: 伪装的浏览器类型

    Returns:
        dict: 包含 url、status、data、proxy_used 的字典
    """
    rotator = ProxyRotator(proxy_list)

    # 获取当前轮到的代理
    current_proxy = rotator.get_proxy()
    print(f"  使用代理: {current_proxy}")

    with FetcherSession(impersonate=impersonate) as session:
        page = session.get(url, proxy=current_proxy, stealthy_headers=True)

        result = {
            "url": url,
            "status": page.status,
            "proxy_used": current_proxy,
            "data": []
        }

        if css_selector:
            result["data"] = page.css(css_selector).getall()
        else:
            result["data"] = page.get_all_text()

    return result


def scrape_batch_with_rotation(urls, proxy_list, css_selector=None, impersonate="chrome"):
    """批量抓取时自动轮换代理（每个请求用不同代理）

    Args:
        urls: URL 列表
        proxy_list: 代理列表
        css_selector: CSS 选择器（可选）
        impersonate: 伪装的浏览器类型

    Returns:
        list: 每个页面的提取结果
    """
    rotator = ProxyRotator(proxy_list)
    results = []

    with FetcherSession(impersonate=impersonate) as session:
        for url in urls:
            proxy = rotator.get_proxy()
            print(f"  [{len(results)+1}/{len(urls)}] 代理: {proxy}")

            page = session.get(url, proxy=proxy, stealthy_headers=True)
            page_data = {
                "url": url,
                "status": page.status,
                "proxy_used": proxy,
                "data": []
            }
            if css_selector:
                page_data["data"] = page.css(css_selector).getall()
            else:
                page_data["data"] = page.get_all_text()
            results.append(page_data)

    return results


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python proxy_rotation.py <URL> <代理1> <代理2> ... [CSS选择器]")
        print("示例: python proxy_rotation.py https://quotes.toscrape.com/ \\")
        print("        http://proxy1:8080 http://user:pass@proxy2:3128 '.quote .text::text'")
        print("\n代理格式: http://proxy:port 或 http://user:pass@proxy:port")
        sys.exit(1)

    target_url = sys.argv[1]
    # 从参数中分离代理和选择器（选择器以 . 或 # 开头）
    args = sys.argv[2:]
    proxies = [a for a in args if a.startswith("http")]
    selector = next((a for a in args if not a.startswith("http")), None)

    print(f"代理轮换抓取: {target_url}")
    print(f"  可用代理: {len(proxies)} 个")
    if selector:
        print(f"  选择器: {selector}")

    result = scrape_with_proxy_rotation(target_url, proxies, selector)

    print(f"\n状态码: {result['status']}")
    print(f"使用代理: {result['proxy_used']}")
    if isinstance(result["data"], list):
        print(f"提取到 {len(result['data'])} 条数据:")
        for i, item in enumerate(result["data"][:10], 1):
            text = item[:80] if isinstance(item, str) else str(item)
            print(f"  {i}. {text}")
    else:
        print(f"页面文本前300字: {result['data'][:300]}")
