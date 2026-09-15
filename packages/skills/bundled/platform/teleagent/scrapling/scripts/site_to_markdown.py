"""
全站转 Markdown 爬虫 — 自动遍历整站并转为 LLM 友好的 Markdown
来源：Scrapling 官方 SiteToMarkdownSpider 模板 (scrapling.spiders.templates)
用法：python site_to_markdown.py <域名> <输出目录> [最大页数] [CSS选择器]
示例：python site_to_markdown.py quotes.toscrape.com ./output 10
      python site_to_markdown.py example.com ./md_output 0 "div.content"

官方模板特性：
- 自动爬取 allowed_domains 下所有页面链接
- 每页转为干净的 Markdown（默认只取 body 内容，排除 head/script）
- 写入 output_dir 目录，文件名按 URL 命名
- 支持 max_pages 限制爬取页数（0 = 不限）
- 支持 css_selector 只转换匹配元素

依赖安装：pip install "scrapling[fetchers]" "scrapling[rag]" && scrapling install
"""

import sys
from scrapling.spiders import SiteToMarkdownSpider


def crawl_site_to_markdown(domain, output_dir, max_pages=0, css_selector=None):
    """爬取整个网站并转为 Markdown 文件

    Args:
        domain: 目标域名（如 quotes.toscrape.com），不含协议前缀
        output_dir: Markdown 文件输出目录
        max_pages: 最大爬取页数（0 = 不限制）
        css_selector: CSS 选择器，只转换匹配元素（可选）

    Returns:
        list: 每页的 {url, title, markdown} 字典
    """
    class SiteSpider(SiteToMarkdownSpider):
        name = "site_to_md"
        start_urls = [f"https://{domain}/"]
        allowed_domains = {domain}
        output_dir = output_dir
        max_pages = max_pages
        # 只提取 body 内容，排除 head/script/style
        main_content_only = True

        if css_selector:
            css_selector = css_selector

    spider = SiteSpider()
    result = spider.start()

    return result.items


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python site_to_markdown.py <域名> <输出目录> [最大页数] [CSS选择器]")
        print("示例: python site_to_markdown.py quotes.toscrape.com ./output 10")
        print("      python site_to_markdown.py example.com ./md_output 0 'div.content'")
        print("\n参数说明:")
        print("  域名: 不含协议前缀，如 quotes.toscrape.com")
        print("  输出目录: Markdown 文件保存位置")
        print("  最大页数: 0 = 不限制（默认 0）")
        print("  CSS选择器: 只转换匹配元素（可选）")
        sys.exit(1)

    domain = sys.argv[1]
    output_dir = sys.argv[2]
    max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    css_selector = sys.argv[4] if len(sys.argv) > 4 else None

    print(f"全站转 Markdown: {domain}")
    print(f"  输出目录: {output_dir}")
    print(f"  最大页数: {'不限' if max_pages == 0 else max_pages}")
    if css_selector:
        print(f"  限定选择器: {css_selector}")

    items = crawl_site_to_markdown(domain, output_dir, max_pages, css_selector)

    print(f"\n爬取完成! 共转换 {len(items)} 个页面")
    for i, item in enumerate(items[:5], 1):
        title = item.get("title", "(无标题)")[:50]
        md_len = len(item.get("markdown", ""))
        print(f"  {i}. [{title}] ({md_len} 字符) -> {item.get('url', '')}")
    if len(items) > 5:
        print(f"  ... 共 {len(items)} 页")

    print(f"\nMarkdown 文件已保存到: {output_dir}/")
