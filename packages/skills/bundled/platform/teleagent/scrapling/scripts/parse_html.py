"""
离线 HTML 解析器 — 不请求网络，直接解析本地 HTML 字符串
来源：Scrapling 官方 README "parser right away" 用法
用法：python parse_html.py <HTML文件路径> <CSS选择器>
示例：python parse_html.py page.html "table tr td::text"

支持多种选择器：
- CSS 选择器: page.css('div.class::text')
- XPath 选择器: page.xpath('//div[@class="x"]/text()')
- BeautifulSoup 风格: page.find_all('div', class_='x')
- 正则匹配: page.find_by_regex(r'pattern')
- 文本搜索: page.find_by_text('keyword', partial=True)
"""

import sys
from scrapling.parser import Selector


def parse_html_file(html_path, css_selector=None, xpath=None, find_all_tag=None, find_all_class=None):
    """解析本地 HTML 文件

    Args:
        html_path: HTML 文件路径
        css_selector: CSS 选择器（可选）
        xpath: XPath 选择器（可选）
        find_all_tag: find_all 的标签名（可选）
        find_all_class: find_all 的 class 名（可选）

    Returns:
        list: 提取到的数据列表
    """
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    page = Selector(html_content)
    results = []

    if css_selector:
        results = page.css(css_selector).getall()
    elif xpath:
        results = page.xpath(xpath).getall()
    elif find_all_tag:
        if find_all_class:
            elements = page.find_all(find_all_tag, class_=find_all_class)
        else:
            elements = page.find_all(find_all_tag)
        results = [el.text.strip() if el.text else el.html_content for el in elements]

    return results


def parse_html_string(html_string, css_selector=None):
    """直接解析 HTML 字符串

    Args:
        html_string: HTML 字符串
        css_selector: CSS 选择器（可选）

    Returns:
        list: 提取到的数据列表
    """
    page = Selector(html_string)
    if css_selector:
        return page.css(css_selector).getall()
    return [page.get_all_text()]


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python parse_html.py <HTML文件路径> <CSS选择器>")
        print("示例: python parse_html.py page.html 'table tr td::text'")
        sys.exit(1)

    html_file = sys.argv[1]
    selector = sys.argv[2]

    print(f"解析文件: {html_file}")
    print(f"选择器: {selector}")

    data = parse_html_file(html_file, css_selector=selector)

    print(f"\n提取到 {len(data)} 条数据:")
    for i, item in enumerate(data[:20], 1):
        text = item[:80] if isinstance(item, str) else str(item)
        print(f"  {i}. {text}")
    if len(data) > 20:
        print(f"  ... 共 {len(data)} 条")
