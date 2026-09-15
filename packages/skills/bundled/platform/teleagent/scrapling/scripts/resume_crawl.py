"""
断点续传爬虫 — 支持暂停/恢复的大规模爬取
来源：Scrapling 官方 README checkpoint/crawldir 用法
用法：python resume_crawl.py <起始URL> <CSS选择器> <翻页选择器> <输出目录> [输出文件名]
示例：python resume_crawl.py https://quotes.toscrape.com/ ".quote" ".next a" ./crawl_data quotes

断点续传机制：
- 首次运行：正常爬取，Ctrl+C 可优雅暂停，进度自动保存到 crawldir 目录
- 再次运行：传相同 crawldir，自动从上次中断处恢复
- 适合大规模爬取任务，不怕中断重来

依赖安装：pip install "scrapling[fetchers]"
"""

import sys
import os
from scrapling.spiders import Spider, Response


def create_resumable_spider(start_url, item_selector, next_page_selector, crawldir, concurrency=10):
    """创建一个支持断点续传的爬虫

    Args:
        start_url: 起始 URL
        item_selector: 提取数据的 CSS 选择器
        next_page_selector: 翻页链接的 CSS 选择器
        crawldir: 断点续传目录（进度保存位置）
        concurrency: 并发请求数

    Returns:
        Spider 子类
    """
    class ResumableSpider(Spider):
        name = "resumable_crawler"
        start_urls = [start_url]
        concurrent_requests = concurrency

        async def parse(self, response: Response):
            for item in response.css(item_selector):
                all_text = item.get_all_text().strip()
                yield {
                    "text": all_text,
                    "html": item.html_content,
                    "url": response.url,
                }

            # 自动翻页
            next_links = response.css(next_page_selector)
            if next_links:
                href = next_links[0].attrib.get('href')
                if href:
                    yield response.follow(href)

    return ResumableSpider


def run_resumable_crawl(start_url, item_selector, next_page_selector, crawldir,
                        output_name="crawl_result", concurrency=10):
    """执行断点续传爬取

    首次运行会从头开始爬取；若 crawldir 中有检查点，
    则自动从上次中断处恢复。

    Args:
        start_url: 起始 URL
        item_selector: 提取数据的 CSS 选择器
        next_page_selector: 翻页链接的 CSS 选择器
        crawldir: 断点续传目录
        output_name: 导出文件名（不含扩展名）
        concurrency: 并发请求数

    Returns:
        爬取结果列表
    """
    SpiderClass = create_resumable_spider(
        start_url, item_selector, next_page_selector, crawldir, concurrency
    )

    # 传入 crawldir 启用断点续传
    # 首次运行：创建检查点；再次运行：从检查点恢复
    is_resume = os.path.exists(crawldir) and os.listdir(crawldir)
    if is_resume:
        print(f"  检测到检查点，从上次中断处恢复: {crawldir}")
    else:
        print(f"  首次爬取，进度将保存到: {crawldir}")

    spider = SpiderClass(crawldir=crawldir)
    result = spider.start()

    print(f"\n爬取完成! 共 {len(result.items)} 条记录")

    # 多格式导出
    result.items.to_json(f"{output_name}.json")
    result.items.to_jsonl(f"{output_name}.jsonl")
    result.items.to_csv(f"{output_name}.csv")

    print(f"已导出: {output_name}.json / .jsonl / .csv")

    # 打印前5条预览
    for i, item in enumerate(result.items[:5], 1):
        text_preview = item["text"][:80] if item["text"] else "(空)"
        print(f"  {i}. {text_preview}")

    return result.items


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("用法: python resume_crawl.py <起始URL> <CSS选择器> <翻页选择器> <输出目录> [输出文件名]")
        print("示例: python resume_crawl.py https://quotes.toscrape.com/ '.quote' '.next a' ./crawl_data quotes")
        print("\n断点续传说明:")
        print("  首次运行: 从头开始爬取，Ctrl+C 可暂停，进度保存到输出目录")
        print("  再次运行: 传相同参数，自动从上次中断处恢复")
        sys.exit(1)

    url = sys.argv[1]
    item_sel = sys.argv[2]
    next_sel = sys.argv[3]
    crawldir = sys.argv[4]
    output_name = sys.argv[5] if len(sys.argv) > 5 else "crawl_result"

    print(f"断点续传爬虫: {url}")
    print(f"  数据选择器: {item_sel}")
    print(f"  翻页选择器: {next_sel}")

    run_resumable_crawl(url, item_sel, next_sel, crawldir, output_name)
