"""
全站翻页爬虫 — Spider 框架自动翻页采集 + 多格式导出
来源：Scrapling 官方 README Spider 示例
用法：python spider_crawl.py <起始URL> <CSS选择器> [翻页选择器] [输出文件名]
示例：python spider_crawl.py https://quotes.toscrape.com/ ".quote" ".next a" quotes

Spider 框架特性：
- 并发请求（默认 10 并发）
- 自动翻页跟随
- 内置 JSON/JSONL/CSV/XML 导出
- 支持暂停恢复（传 crawldir 参数）
"""

import sys
from scrapling.spiders import Spider, Response


def create_spider(start_url, item_selector, next_page_selector, concurrency=10):
    """动态创建一个翻页爬虫类

    Args:
        start_url: 起始 URL
        item_selector: 提取数据的 CSS 选择器（每匹配一个元素产出一条记录）
        next_page_selector: 翻页链接的 CSS 选择器
        concurrency: 并发请求数

    Returns:
        Spider 子类
    """
    class AutoSpider(Spider):
        name = "auto_crawler"
        start_urls = [start_url]
        concurrent_requests = concurrency

        async def parse(self, response: Response):
            for item in response.css(item_selector):
                # 提取元素内所有文本（含子元素）和 HTML
                all_text = item.get_all_text().strip()
                yield {
                    "text": all_text,
                    "html": item.html_content,
                    "css_selector": item.generate_css_selector,
                }

            # 自动翻页
            next_links = response.css(next_page_selector)
            if next_links:
                href = next_links[0].attrib.get('href')
                if href:
                    yield response.follow(href)

    return AutoSpider


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python spider_crawl.py <起始URL> <CSS选择器> <翻页选择器> [输出文件名]")
        print("示例: python spider_crawl.py https://quotes.toscrape.com/ '.quote' '.next a' quotes")
        sys.exit(1)

    url = sys.argv[1]
    item_sel = sys.argv[2]
    next_sel = sys.argv[3]
    output_name = sys.argv[4] if len(sys.argv) > 4 else "crawl_result"

    print(f"启动爬虫: {url}")
    print(f"  数据选择器: {item_sel}")
    print(f"  翻页选择器: {next_sel}")

    SpiderClass = create_spider(url, item_sel, next_sel)
    result = SpiderClass().start()

    print(f"\n爬取完成! 共 {len(result.items)} 条记录")

    # 多格式导出（官方内置功能）
    result.items.to_json(f"{output_name}.json")
    result.items.to_jsonl(f"{output_name}.jsonl")
    result.items.to_csv(f"{output_name}.csv")
    result.items.to_xml(f"{output_name}.xml")

    print(f"已导出: {output_name}.json / .jsonl / .csv / .xml")

    # 打印前5条预览
    for i, item in enumerate(result.items[:5], 1):
        text_preview = item["text"][:80] if item["text"] else "(空)"
        print(f"  {i}. {text_preview}")
