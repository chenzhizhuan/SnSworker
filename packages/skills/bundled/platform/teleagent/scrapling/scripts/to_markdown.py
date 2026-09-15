"""
网页转 Markdown — 抓取网页并转为 LLM 友好的 Markdown 格式
来源：Scrapling 官方 README "RAG-ready Markdown" 功能
用法：python to_markdown.py <URL> [输出文件名] [CSS选择器]
示例：python to_markdown.py https://quotes.toscrape.com/ output.md
      python to_markdown.py https://quotes.toscrape.com/ output.md ".quote"

依赖安装：pip install "scrapling[rag]"   # 提供 markdownify（带选择器转换时需要）
"""

import sys
from scrapling.fetchers import Fetcher


def url_to_markdown(url, css_selector=None):
    """抓取网页并转为 Markdown

    Scrapling 的 page.markdown() 方法会将 HTML 转为干净的 Markdown，
    适合直接喂给 LLM 做 RAG 或内容分析。

    Args:
        url: 目标网页地址
        css_selector: 如果指定，仅提取匹配元素后再转 Markdown

    Returns:
        str: Markdown 格式文本
    """
    page = Fetcher.get(url)

    if css_selector:
        elements = page.css(css_selector)
        parts = []
        for el in elements:
            parts.append(el.html_content)
        # Selector 无 markdown() 方法（仅 Page 有），
        # 用 Scrapling 同款 markdownify 转换 HTML -> Markdown
        import markdownify
        return markdownify.markdownify(f"<div>{''.join(parts)}</div>", heading_style="ATX")

    return page.markdown()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python to_markdown.py <URL> [输出文件名] [CSS选择器]")
        print("示例: python to_markdown.py https://quotes.toscrape.com/ output.md")
        sys.exit(1)

    target_url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "output.md"
    selector = sys.argv[3] if len(sys.argv) > 3 else None

    print(f"正在抓取并转换: {target_url}")
    if selector:
        print(f"  限定选择器: {selector}")

    markdown_text = url_to_markdown(target_url, selector)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_text)

    print(f"\n转换完成! 共 {len(markdown_text)} 字符")
    print(f"已保存到: {output_file}")
    print(f"\n前500字预览:")
    print("-" * 50)
    print(markdown_text[:500])
    print("-" * 50)
