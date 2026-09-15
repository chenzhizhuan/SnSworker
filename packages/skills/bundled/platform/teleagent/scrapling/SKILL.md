---
name: scrapling
description: "Adaptive web scraping framework that handles everything from a single request to full-scale crawls. Bypasses anti-bot systems like Cloudflare Turnstile, learns from website changes, supports CSS/XPath selection, session requests, stealth mode and spider crawls. Use when users ask about 爬虫, 网页抓取, web scraping, data extraction, crawl websites, 采集网页数据, scraping with Python, bypass Cloudflare, adaptive scraping, spider."
name_cn: 高性能网页爬虫
description_cn: "自适应网页爬虫框架：单次请求到全量爬取一条龙，自带绕过 Cloudflare/反爬验证、三种抓取器（普通/隐身/浏览器）、自适应元素定位、会话保持与代理轮换、Spider 并发爬取。内置微博/知乎/B站/贴吧/抖音/小红书六大平台反爬实测经验与一键探测脚本（抖音 a_bogus 签名绕过、小红书登录态采集），附豆瓣 PoW 破解、IP 封禁排查、断点续爬等踩坑实录。政企场景：政府采购网/电信采购网（瑞数防护绕过）/工信部招投标标讯采集；金融场景：央行/证监会/招标投标公共服务平台监管动态与标讯采集。"
create_source: super-agent-skill-creator
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '4aa33619-034a-4827-b500-5135bdd71236'
  PropagateID: '4aa33619-034a-4827-b500-5135bdd71236'
  ReservedCode1: 'ca3c701d-fcc4-415d-98d3-f689acba3bf7'
  ReservedCode2: 'ca3c701d-fcc4-415d-98d3-f689acba3bf7'
---

# Scrapling 智能爬虫

## Description

Scrapling 是一个自适应的现代化网页爬虫框架（GitHub 78k+ Stars），核心能力包括：

- **自适应解析**：解析器能学习网站变化，在页面改版后自动重新定位元素，无需修改代码
- **反反爬能力**：内置绕过 Cloudflare Turnstile 等验证的隐身抓取器（StealthyFetcher）
- **三种抓取模式**：普通 HTTP 请求（Fetcher）、隐身模式（StealthyFetcher）、浏览器自动化（DynamicFetcher）
- **会话保持**：FetcherSession / StealthySession / DynamicSession 支持 Cookie 和登录态跨请求保持
- **Spider 全量爬取**：类似 Scrapy 的 Spider 框架，支持并发、自动翻页、暂停恢复、自动限速
- **多格式导出**：内置 JSON / JSONL / CSV / XML 导出，一行代码保存采集结果
- **网页转 Markdown**：page.markdown() 方法将网页转为 LLM 友好的 Markdown 格式，适合 RAG 场景

本技能提供 10 个可运行的场景脚本，覆盖从单页采集到全站爬取、反爬绕过到断点续传的常见需求，所有代码均基于 Scrapling 官方文档和源码验证通过。还内置官方 94 项断言一键自检脚本。

## 概览

| 属性 | 说明 |
|---|---|
| 开发者 | D4Vinci |
| 许可证 | BSD-3-Clause |
| 运行环境 | Python 3.10+ |
| 爬取模式 | 普通请求 / 隐身抓取 / 浏览器自动化 |
| 反爬能力 | 内置 Cloudflare Turnstile 等绕过 |
| GitHub Stars | 78k+ |

## 安装

```bash
# 基础安装（仅解析引擎，不含抓取器）
pip install scrapling

# 完整安装（含抓取器 + 浏览器依赖）
pip install "scrapling[fetchers]"
scrapling install            # 下载浏览器与指纹依赖

# 按需扩展
pip install "scrapling[ai]"     # MCP server（AI 对话集成）
pip install "scrapling[rag]"    # Markdown 转换（RAG 场景）
pip install "scrapling[shell]"   # 交互式抓取 Shell
pip install "scrapling[all]"     # 全量安装
```

> **注意**：基础安装只含解析器，直接 import fetchers 会报 ModuleNotFoundError。使用抓取器前需安装 `scrapling[fetchers]` 并运行 `scrapling install`。

## 场景脚本

本技能在 `scripts/` 目录下提供 10 个经过实际运行验证的脚本，覆盖常见爬虫场景：

### 1. 基础请求采集器（basic_scrape.py）

单页抓取并用 CSS 选择器提取数据。适合快速采集单个页面的内容。

```bash
python scripts/basic_scrape.py <URL> [CSS选择器]
python scripts/basic_scrape.py https://quotes.toscrape.com/ ".quote .text::text"
```

核心代码来自官方 README 基础用法：

```python
from scrapling.fetchers import Fetcher

page = Fetcher.get('https://quotes.toscrape.com/')
quotes = page.css('.quote .text::text').getall()
```

### 2. 会话模式采集器（session_scrape.py）

保持 Cookie 与登录态，连续抓取多个页面。适合需要登录或跨页保持状态的场景。

```bash
python scripts/session_scrape.py <URL1> <URL2> ...
python scripts/session_scrape.py https://quotes.toscrape.com/page/1/ https://quotes.toscrape.com/page/2/
```

核心代码来自官方 README 会话模式用法：

```python
from scrapling.fetchers import FetcherSession

with FetcherSession(impersonate='chrome') as session:
    page = session.get('https://quotes.toscrape.com/', stealthy_headers=True)
    quotes = page.css('.quote .text::text').getall()
```

### 3. 全站翻页爬虫（spider_crawl.py）

使用 Spider 框架自动翻页采集，支持并发请求，爬取结果一键导出 JSON/JSONL/CSV/XML 四种格式。

```bash
python scripts/spider_crawl.py <起始URL> <数据选择器> <翻页选择器> [输出文件名]
python scripts/spider_crawl.py https://quotes.toscrape.com/ ".quote" ".next a" quotes
```

核心代码来自官方 README Spider 示例：

```python
from scrapling.spiders import Spider, Response

class QuotesSpider(Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com/"]
    concurrent_requests = 10

    async def parse(self, response: Response):
        for quote in response.css('.quote'):
            yield {
                "text": quote.css('.text::text').get(),
                "author": quote.css('.author::text').get(),
            }
        next_page = response.css('.next a')
        if next_page:
            yield response.follow(next_page[0].attrib['href'])

result = QuotesSpider().start()
print(f"Scraped {len(result.items)} quotes")
result.items.to_json("quotes.json")
```

### 4. 离线 HTML 解析器（parse_html.py）

不请求网络，直接解析本地 HTML 文件。支持 CSS 选择器、XPath、find_all 等多种提取方式。适合处理已下载的 HTML 或本地网页文件。

```bash
python scripts/parse_html.py <HTML文件路径> <CSS选择器>
python scripts/parse_html.py page.html "table tr td::text"
```

核心代码来自官方 README 解析器用法：

```python
from scrapling.parser import Selector

page = Selector("<html>...</html>")
data = page.css('.title::text').getall()
```

### 5. 网页转 Markdown（to_markdown.py）

抓取网页并转为 LLM 友好的 Markdown 格式，适合 RAG 知识库构建和内容分析。需要安装 `scrapling[rag]`。

```bash
python scripts/to_markdown.py <URL> [输出文件名] [CSS选择器]
python scripts/to_markdown.py https://quotes.toscrape.com/ output.md
```

核心代码来自官方 README RAG-ready Markdown 功能：

```python
from scrapling.fetchers import Fetcher

page = Fetcher.get('https://example.com/')
markdown_text = page.markdown()  # 转为干净的 Markdown 格式
```

### 6. 隐身抓取采集器（stealth_scrape.py）

使用 StealthyFetcher 绕过 Cloudflare Turnstile 等反爬验证。支持 `--solve-cloudflare` 专项求解和隐身会话模式。

```bash
python scripts/stealth_scrape.py <URL> [CSS选择器] [--solve-cloudflare]
python scripts/stealth_scrape.py https://quotes.toscrape.com/ ".quote .text::text"
python scripts/stealth_scrape.py https://nopecha.com/demo/cloudflare "#padded_content a" --solve-cloudflare
```

核心代码来自官方 README 隐身模式用法：

```python
from scrapling.fetchers import StealthyFetcher, StealthySession

StealthyFetcher.adaptive = True
page = StealthyFetcher.fetch('https://nopecha.com/demo/cloudflare', headless=True, solve_cloudflare=True)
data = page.css('#padded_content a').getall()
```

### 7. 代理轮换采集器（proxy_rotation.py）

使用官方 ProxyRotator 实现多代理自动轮换，防止 IP 封禁。支持字符串和 dict 格式代理。

```bash
python scripts/proxy_rotation.py <URL> <代理1> <代理2> ... [CSS选择器]
python scripts/proxy_rotation.py https://quotes.toscrape.com/ http://proxy1:8080 http://user:pass@proxy2:3128 ".quote .text::text"
```

核心代码来自官方 ProxyRotator 源码：

```python
from scrapling.fetchers import FetcherSession
from scrapling.engines.toolbelt import ProxyRotator

rotator = ProxyRotator(["http://proxy1:8080", "http://proxy2:3128"])
proxy = rotator.get_proxy()  # 循环轮换

with FetcherSession(impersonate='chrome') as session:
    page = session.get(url, proxy=proxy, stealthy_headers=True)
```

### 8. 浏览器自动化采集器（dynamic_render.py）

使用 DynamicFetcher 抓取 JS 动态渲染页面（Vue/React/Angular SPA）。支持 CSS/XPath 选择器和可见窗口调试模式。

```bash
python scripts/dynamic_render.py <URL> [CSS选择器] [--visible] [--xpath XPATH]
python scripts/dynamic_render.py https://quotes.toscrape.com/ ".quote .text::text"
python scripts/dynamic_render.py https://quotes.toscrape.com/ --xpath "//span[@class='text']/text()"
python scripts/dynamic_render.py https://quotes.toscrape.com/ ".quote" --visible  # 显示浏览器
```

核心代码来自官方 README 浏览器自动化用法：

```python
from scrapling.fetchers import DynamicFetcher, DynamicSession

with DynamicSession(headless=True, network_idle=True) as session:
    page = session.fetch('https://quotes.toscrape.com/', load_dom=False)
    data = page.xpath('//span[@class="text"]/text()').getall()
```

### 9. 全站转 Markdown 爬虫（site_to_markdown.py）

使用官方 SiteToMarkdownSpider 模板，自动遍历整站并转为 LLM 友好的 Markdown 文件。适合构建 RAG 知识库。

```bash
python scripts/site_to_markdown.py <域名> <输出目录> [最大页数] [CSS选择器]
python scripts/site_to_markdown.py quotes.toscrape.com ./output 10
```

核心代码来自官方 SiteToMarkdownSpider 模板：

```python
from scrapling.spiders import SiteToMarkdownSpider

class SiteSpider(SiteToMarkdownSpider):
    name = "site_to_md"
    start_urls = ["https://example.com/"]
    allowed_domains = {"example.com"}
    output_dir = "./output"
    max_pages = 10

SiteSpider().start()  # 每页自动转 Markdown 并写入文件
```

### 10. 断点续传爬虫（resume_crawl.py）

基于官方 checkpoint 机制，支持 Ctrl+C 暂停后从断点恢复。适合大规模爬取任务。

```bash
python scripts/resume_crawl.py <起始URL> <CSS选择器> <翻页选择器> <输出目录> [输出文件名]
python scripts/resume_crawl.py https://quotes.toscrape.com/ ".quote" ".next a" ./crawl_data quotes
```

核心代码来自官方 README 断点续传用法：

```python
from scrapling.spiders import Spider, Response

class ResumableSpider(Spider):
    name = "resumable"
    start_urls = ["https://quotes.toscrape.com/"]

    async def parse(self, response: Response):
        for quote in response.css('.quote'):
            yield {"text": quote.css('.text::text').get()}
        next_page = response.css('.next a')
        if next_page:
            yield response.follow(next_page[0].attrib['href'])

# 传入 crawldir 启用断点续传
ResumableSpider(crawldir="./crawl_data").start()
```

## 脚本速查表

| 场景 | 脚本 | 命令示例 |
|---|---|---|
| 单页采集 | `basic_scrape.py` | `python basic_scrape.py <URL> "选择器"` |
| 多页会话 | `session_scrape.py` | `python session_scrape.py <URL1> <URL2>` |
| 全站翻页 | `spider_crawl.py` | `python spider_crawl.py <URL> "选择器" "翻页选择器"` |
| 离线解析 | `parse_html.py` | `python parse_html.py <HTML文件> "选择器"` |
| 网页转MD | `to_markdown.py` | `python to_markdown.py <URL> output.md` |
| 隐身反爬 | `stealth_scrape.py` | `python stealth_scrape.py <URL> "选择器" --solve-cloudflare` |
| 代理轮换 | `proxy_rotation.py` | `python proxy_rotation.py <URL> http://proxy:port` |
| JS渲染页 | `dynamic_render.py` | `python dynamic_render.py <URL> "选择器" --visible` |
| 全站转MD | `site_to_markdown.py` | `python site_to_markdown.py example.com ./output 10` |
| 断点续传 | `resume_crawl.py` | `python resume_crawl.py <URL> "选择器" "翻页" ./data` |
| 一键自检 | `run_selftest.py` | `python run_selftest.py` |

## 快速开始

### 1. 基础请求 + CSS 选择

```python
from scrapling.fetchers import Fetcher

page = Fetcher.get('https://quotes.toscrape.com/')
quotes = page.css('.quote .text::text').getall()
```

### 2. 会话模式（保持登录/携带 Cookie）

```python
from scrapling.fetchers import Fetcher, FetcherSession

with FetcherSession(impersonate='chrome') as session:
    page = session.get('https://quotes.toscrape.com/', stealthy_headers=True)
    quotes = page.css('.quote .text::text').getall()
```

### 3. 隐身模式（绕过 Cloudflare）

```python
from scrapling.fetchers import StealthyFetcher

StealthyFetcher.adaptive = True
page = StealthyFetcher.fetch('https://nopecha.com/demo/cloudflare', headless=True, network_idle=True)
data = page.css('#padded_content a').getall()
```

### 4. 浏览器自动化（完整 DOM）

```python
from scrapling.fetchers import DynamicFetcher, DynamicSession

with DynamicSession(headless=True, disable_resources=False, network_idle=True) as session:
    page = session.fetch('https://quotes.toscrape.com/', load_dom=False)
    data = page.xpath('//span[@class="text"]/text()').getall()

page = DynamicFetcher.fetch('https://quotes.toscrape.com/')
data = page.css('.quote .text::text').getall()
```

### 5. Spider 全量爬取

```python
from scrapling.spiders import Spider, Response

class MySpider(Spider):
    name = "demo"
    start_urls = ["https://example.com/"]

    async def parse(self, response: Response):
        for item in response.css('.product'):
            yield {"title": item.css('h2::text').get()}

MySpider().start()
```

## 高级解析与选择器

Scrapling 支持多种元素选择方式：

```python
from scrapling.fetchers import Fetcher

page = Fetcher.get('https://quotes.toscrape.com/')

# CSS 选择器
quotes = page.css('.quote .text::text').getall()

# XPath 选择器
quotes = page.xpath('//span[@class="text"]/text()').getall()

# BeautifulSoup 风格 find_all
quotes = page.find_all('div', class_='quote')

# 按文本查找（partial=True 模糊匹配）
result = page.find_by_text('world', partial=True)

# 正则匹配
matched = page.css('.quote .text::text').re(r'\"(.+?)\"')
first = page.css('.quote .text::text').re_first(r'\"(.+?)\"')

# 链式选择
first_quote = page.css('.quote')[0]
author = first_quote.css('.author::text').get()
```

## 自适应抓取（核心卖点）

首次抓取时用 `auto_save=True` 保存元素位置，网站改版后用 `adaptive=True` 自动重新定位：

```python
# 首次抓取：定位并保存元素位置
products = page.css('.product', auto_save=True)

# 网站改版后：adaptive=True 自动重新定位，无需改代码
products = page.css('.product', adaptive=True)
```

## DOM 导航 API

```python
first_quote = page.css('.quote')[0]

# 父元素
parent = first_quote.parent

# 下一个 / 上一个兄弟元素
nxt = first_quote.next
prev = first_quote.previous

# 所有兄弟元素
siblings = first_quote.siblings

# 子元素
children = first_quote.children

# 查找祖先元素（传入判断函数）
ancestor = first_quote.find_ancestor(lambda el: el.tag == 'div')

# 查找相似元素
similar = first_quote.find_similar()

# 生成选择器
css_selector = first_quote.generate_css_selector
xpath_selector = first_quote.generate_xpath_selector
```

## CLI 用法

```bash
# 安装 shell 扩展后可使用
scrapling fetch https://example.com          # 抓取页面
scrapling extract "css selector" https://... # 提取元素
scrapling shell                              # 交互式抓取 shell
```

## 翻页采集与数据导出

Spider 框架内置 JSON/JSONL/CSV/XML 导出：

```python
from scrapling.spiders import Spider, Response

class QuotesSpider(Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com/"]
    concurrent_requests = 10

    async def parse(self, response: Response):
        for quote in response.css('.quote'):
            yield {
                "text": quote.css('.text::text').get(),
                "author": quote.css('.author::text').get(),
            }
        next_page = response.css('.next a')
        if next_page:
            yield response.follow(next_page[0].attrib['href'])

result = QuotesSpider().start()
print(f"Scraped {len(result.items)} quotes")
result.items.to_json("quotes.json")
result.items.to_jsonl("quotes.jsonl")
result.items.to_csv("quotes.csv")
result.items.to_xml("quotes.xml")
```

## 使用场景

- **电商比价**：采集商品标题、价格、销量，用 Spider 框架翻页抓取全站
- **舆情监控**：抓取新闻/社交页面内容，转 Markdown 后喂给 LLM 做情感分析
- **反爬网站**：用 StealthyFetcher 绕过 Cloudflare Turnstile 等验证
- **数据采集**：构建 RAG 语料库，page.markdown() 一行转 Markdown
- **批量爬取**：Spider 框架做全站抓取，内置并发、自动限速、暂停恢复
- **本地解析**：Selector 直接解析 HTML 字符串，不请求网络
- **表格提取**：用 CSS 选择器从 HTML 表格中批量提取数据

## 反爬绕过配置

### StealthyFetcher 参数说明

| 参数 | 说明 | 默认值 |
|---|---|---|
| `headless` | 无头模式（False 可看到浏览器） | `True` |
| `network_idle` | 等待网络空闲（确保 AJAX 完成） | `False` |
| `solve_cloudflare` | Cloudflare Turnstile 专项求解 | `False` |
| `google_search` | 模拟从 Google 搜索进入（增加可信度） | `True` |
| `disable_resources` | 禁止加载资源（图片/CSS/字体，提速） | `True` |

### 代理轮换策略

```python
from scrapling.engines.toolbelt import ProxyRotator, cyclic_rotation

# 默认循环轮换
rotator = ProxyRotator(["http://proxy1:8080", "http://proxy2:3128"])

# 自定义轮换策略（如随机选择）
import random
def random_rotation(proxies, current_index):
    idx = random.randint(0, len(proxies) - 1)
    return proxies[idx], idx

rotator = ProxyRotator(proxies, strategy=random_rotation)
```

代理格式支持两种：
- 字符串：`"http://user:pass@proxy:8080"`
- dict（Playwright 风格）：`{"server": "http://proxy:8080", "username": "user", "password": "pass"}`

## 故障排查

| 报错 | 原因 | 解决方案 |
|---|---|---|
| `ModuleNotFoundError: No module named 'scrapling.fetchers'` | 只装了基础包 | `pip install "scrapling[fetchers]"` |
| `ModuleNotFoundError: No module named 'markdownify'` | 缺 Markdown 转换依赖 | `pip install "scrapling[rag]"` |
| `AttributeError: 'Selector' has no attribute 'markdown'` | `markdown()` 是 Page 方法，不是 Selector 的 | 用 `page.markdown()` 或 `markdownify.markdownify(html)` |
| `generate_css_selector` 报错 | 它是属性不是方法 | 不加括号：`el.generate_css_selector` |
| `next_sibling` 报错 | 该属性不存在 | 用 `el.next` 或 `el.previous` |
| `find_by_text(tag=...)` 报错 | 不支持 tag 参数 | 用 `page.find_by_text('keyword', partial=True)` |
| 浏览器启动失败 | 未安装浏览器依赖 | 运行 `scrapling install` |
| SSL 连接被关闭 | 网络/代理问题 | Scrapling 自动重试，也可检查代理配置 |
| Cloudflare 页面无法绕过 | 需要更强的隐身模式 | 加 `solve_cloudflare=True` 参数 |
| 详情页 302 跳 `sec.douban.com/c` | 站点 PoW 挑战（可解） | 复现 JS 逻辑本地求 nonce，见"实战经验 §2" |
| 403 跳 `sec.douban.com/b` | **IP 级封禁（解不了）** | 换出口 IP / 代理节点，见"实战经验 §4-5" |
| 代理换了仍被封 | 代理规则强制目标域名直连 | 检查 Clash/代理规则是否 DIRECT，见"实战经验 §5" |

## 实战经验（豆瓣电影 Top250 采集）

> 以下为真实抓取豆瓣 Top250（2500 部全量清单 → 详情 → 完整演职员）时验证过的实战经验，适用同类反爬严格的站点（微博、知乎、B 站等国内平台思路相通）。

### 1. 采集分层与反爬强度全景

豆瓣数据分三层，每层反爬强度不同，**先摸清分层再定方案**：

| 层级 | 路径 | 反爬强度 | 策略 |
|---|---|---|---|
| 列表页 | `movie.douban.com/top250?start=0&filter=` | 弱 | Fetcher + `stealthy_headers=True` 即可，但主演字段截断为 `/...` |
| 详情页 | `/subject/<id>/` | 中 | 302 → `sec.douban.com/c` PoW 挑战，需本地破解 |
| 完整演职员 | `/subject/<id>/celebrities` | 强（同详情页） | 需带 PoW 破解后的 session cookie 访问 |

**流程**：先 `Fetcher.get(top250 首页)` 试水（带 `stealthy_headers=True`）；确认列表可访问后，再逐层探测详情页与 celebrities 子页的反爬等级，避免盲目上 StealthyFetcher。

### 2. 详情页 PoW 反爬挑战（已破解）

豆瓣 `movie.douban.com` 详情页返回 302 跳转到 `sec.douban.com/c`，这是一个 **Proof-of-Work 挑战页**，普通请求、StealthyFetcher、DynamicFetcher 全部无法直接通过，必须复现其 JS 逻辑：

```python
# 挑战页 HTML 内含 tok / cha / red 三个隐藏字段
# 页面 JS 逻辑：找 nonce 使 sha512(cha + nonce) 前 4 位为 "0000"
import hashlib, re
from curl_cffi import requests

HEADERS = {'User-Agent': '...', 'Referer': 'https://movie.douban.com/top250'}
s = requests.Session(impersonate='chrome')

# 1. 首次请求命中验证页
r = s.get(url, headers=HEADERS)
if 'sec.douban.com' in r.url:
    tok = re.search(r'id="tok"[^>]*value="([^"]*)"', r.text).group(1)
    cha = re.search(r'id="cha"[^>]*value="([^"]*)"', r.text).group(1)
    red = re.search(r'id="red"[^>]*value="([^"]*)"', r.text).group(1)
    # 2. 本地求解 PoW（约 0.04 秒）
    nonce = 0
    while not hashlib.sha512((cha + str(nonce)).encode()).hexdigest().startswith('0000'):
        nonce += 1
    # 3. 提交解
    s.post('https://sec.douban.com/c',
           data={'tok': tok, 'cha': cha, 'sol': nonce, 'red': red},
           headers=HEADERS)
    # 4. cookie 已种下，重新访问原页
    r = s.get(url, headers=HEADERS)
```

**要点**：
- 挑战的 difficulty 为 4（前 4 位 `0000`），Python 暴力求解毫秒级；若遇更高难度（如 5 位），把 while 条件改成 `.startswith('00000')` 即可
- 破解一次后 session 携带 cookie，后续请求自动通过（无需每页都解）
- `curl_cffi` 的 `impersonate='chrome'` 比 scrapling Fetcher 更适合处理这种带签名/挑战的场景
- **常见误诊**：遇到 403 先看 `r.url` 是否落在 `sec.douban.com`——若是 `/c` 是 PoW 挑战（可解），若是 `/b` 是 IP 封禁（解不了）

### 3. 列表页字段截断 → 必须进详情页/子页

豆瓣列表页的"主演"字段只显示前 4-5 位并截断为 `/...`，**要拿完整演职员必须进详情页**：

```python
# 详情页首页只显示 6 位演职员（含"全部 68"链接）
# 完整列表在子页面：<详情链接>/celebrities
celeb_url = link.rstrip('/') + '/celebrities'
# 该页按区块组织，每个区块一个 header，成员为 <li class="celebrity">：
# 导演 Director / 演员 Actor (饰 角色名) / 编剧 Writer / 配音 Voice (配 角色)
# 用正则匹配 <li class="celebrity"> 内的 name 与 role 字段
```

**注意**：动画片的配音演员角色为 `配音 Voice (配 xxx)`，**不能简单按"演员"关键词过滤**，否则会漏掉全部配音主演（曾实测 54 部动画片配音演员全部被漏，需单独把 Voice 归入主演）。

### 4. IP 级封禁识别（403 + sec.douban.com/b）

高频抓取后触发更严格的封禁：所有 `movie.douban.com` 请求返回 403 跳转 `sec.douban.com/b?r=...`（登录跳转页），此时**换 UA、换浏览器指纹、等 8 小时均无效**，只能换出口 IP：

| 现象 | 含义 | 处理 |
|---|---|---|
| 列表页可访问、详情页 403 | 详情页反爬严格 | 用 PoW 破解 |
| 首页 200、`movie.*` 全部 403 | **IP 被 movie 子域拉黑** | 必须换出口 IP（代理/热点/VPN） |
| 代理出口 IP = 直连 IP | 代理规则强制直连，绕不开 | 改代理规则或换网络 |
| 403 跳 `sec.douban.com/b` | IP 级封禁 | 冷却（实测 8 小时仍无效）或换 IP |

**排查命令**：
```bash
# 看直连出口 IP
curl -s https://api.ipify.org
# 看走代理后的出口 IP（配合 Clash 等代理端口）
curl -s -x http://127.0.0.1:7897 https://api.ipify.org
# 对比两者是否一致，一致说明代理规则把目标域名强制直连了
```

### 5. 根因排查：代理为何救不了你（Clash 强制直连）

实测本机 Clash 规则将 `douban.com` 强制 `DIRECT`（规则文件约第 5160-5161 行 `DOMAIN-SUFFIX,douban.com,DIRECT`），导致**代理出口 IP 与直连出口 IP 完全相同**，换代理节点也绕不开封禁。

```bash
# 查看当前 Clash 生效规则
grep -n "douban" /path/to/clash/config.yaml
# 若看到 douban 强制 DIRECT，删掉/注释该条并 reload，代理才能接管
```

**通用排查思路**（适用于任何代理环境下 IP 封禁）：
1. `curl api.ipify.org`（直连）与 `curl -x 代理 api.ipify.org` 对比出口 IP
2. 若两者相同 → 代理规则把目标域名 DIRECT 了，先改规则再换节点
3. 若两者不同仍被封 → 换节点/换 IP，若仍 403 则等待更久（本次实测 8 小时冷却无效，只能换网）

### 6. 断点续爬三件套（大规模采集必做）

2500 部电影逐一抓详情，中途必遇封禁。**务必做三件事**：
- 每抓详情立即写 JSON 缓存（`detail_cache.json`），防中途崩溃丢数据
- 失败条目记入 `pending` 列表（如 `pending_links.json`），下次只补抓 pending，支持断点续传
- 全程 `time.sleep(1.5-2)` 礼貌延时，避免触发限流；若批量成功率下降，先把延时翻倍

### 7. 定时任务补抓的坑

IP 封禁未解除时，**定时补抓任务必然失败**，且每次失败会白白消耗配额。上线定时任务前先自检：
- 当前 IP 是否仍被封（`curl` 试一个详情页看 403？）
- 若被 IP 级封禁，先解决网络（换热点/换节点）再启任务
- 补抓脚本建议支持断点续传（读 pending 列表），失败自动跳过不中断

---

## 实战经验（六大知名站点反爬实测）

> 以下为 2026-09 用 scrapling 对 **百度贴吧 / 微博 / 知乎 / B站 / 抖音 / 小红书** 六种抓取器（Fetcher / FetcherSession / StealthyFetcher / DynamicFetcher）+ 移动端 API + 原始 requests + Playwright 实测的最新结论。每个站点反爬思路不同，**通用规律：先探测再定方案，页面难爬就找 API，PC 难爬就试移动端，API 要签名就借用浏览器环境**。

### 总览表

| 平台 | Fetcher | FetcherSession | StealthyFetcher | 页面结论 | 可用方案（实测打通） |
|---|---|---|---|---|---|
| 百度贴吧 | 403 安全验证 | 403 安全验证 | 403 滑块验证 | 全挂 | 需登录 Cookie 或 Playwright 真人过验证 |
| 微博 | SSRF 拦截 | SSRF 拦截 | 200 跳登录 | 登录墙 | visitor 访客流程 + `ajax/side/hotSearch` |
| 知乎 | 403 | 403 | 200 跳登录 | 登录墙 | **API 直通**（无签名） |
| B站 | 200 JS 壳 | 200 JS 壳 | 200 JS 壳 | 页面无数据 | **先拿 buvid3 cookie 再调 API** |
| 抖音 | 200 JS 壳 | 200 JS 壳 | 200 JS 壳 | 页面无数据 | **Playwright 页面内 fetch**（自动带 `a_bogus` 签名） |
| 小红书 | 200 JS 壳 | 200 JS 壳 | 200 JS 壳 | 登录墙 | **登录 Cookie + 探索页 DOM 提取** |

### 1. 通用坑：curl_cffi 的 SSRF 防护会拦 302 跳内网

实测微博首页 302 跳 `passport.weibo.com` 时，curl_cffi 直接报错：
```
curl: (7) Redirect to internal IP 127.0.0.1 rejected (SSRF protection)
```
这不是网络问题，是 curl_cffi 的安全策略（防止 SSRF 攻击）。**遇到先确认是否跳内网**，`Fetcher.get(..., follow_redirects=False)` 看 `Location` 头即可。

### 2. 百度贴吧：百度安全验证（最难缠）

**现象**：无论 Fetcher / FetcherSession / StealthyFetcher，`tieba.baidu.com/f?kw=xxx` 一律 403，页面标题 `百度安全验证`，含 `captcha`、滑块特征。移动端 UA、PC UA、搜索页全部 403。

**结论**：贴吧（含百度系大部分站点）已启用 **IP 级风控 + 旋转验证码**，纯请求层无法绕过。

**可行方案**（GitHub 社区验证）：
1. **登录 Cookie**：浏览器手动登录贴吧，导出 Cookie 随请求携带（仍可能触发滑块）
2. **Playwright 真实浏览器**：模拟真人操作过验证码（旋转滑块），成功率取决于 IP 信誉
3. **换干净 IP**：数据中心 IP 信誉差，家庭宽带/代理 IP 更易通过
4. 不建议投入过多：百度风控是"旋转验证码 + 行为检测"组合，纯脚本性价比低

### 3. 微博：visitor 访客 Cookie 流程（已打通）

**现象**：
- `weibo.com` 首页 302 → `passport.weibo.com/visitor/visitor`（访客系统）
- 直接调 `weibo.com/ajax/side/hotSearch` → 403 `{"error":...}`
- 移动端 `m.weibo.cn/api/...` → 432 或跳 visitor

**解法**：先完成访客流程，拿到基础 Cookie 后再调 PC 热搜接口，实测成功拿到 52 条热搜：

```python
import requests
s = requests.Session()
s.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ... Chrome/120.0",
    "Referer": "https://weibo.com/",
})
# 1. 先访问一次首页触发访客系统（302 到 passport.weibo.com/visitor/visitor）
r0 = s.get("https://weibo.com/", allow_redirects=False)   # 302 → 访客
# 2. 主动访问 visitor 接口，种下访客 Cookie（XSRF-TOKEN）
r1 = s.get("https://passport.weibo.com/visitor/visitor",
           params={"entry": "miniblog", "a": "enter",
                   "url": "https://weibo.com/", "domain": ".weibo.com"})
# 3. 带 Cookie 调 PC 热搜接口 ✅
r2 = s.get("https://weibo.com/ajax/side/hotSearch")
data = r2.json()["data"]["realtime"]   # 52 条热搜 [{word, num, ...}]
```

**要点**：
- 关键不是 `SUB` 而是 **访客流程产生的会话 Cookie**（XSRF-TOKEN 等）
- `weibo.com/ajax/*` 系列接口对无登录访客友好，热搜/广场可用
- 若要微博正文/用户信息，仍需登录 Cookie（`SUB`），社区方案是 **Cookie 池**（多账号轮换，见 SpiderClub/weibospider）

### 4. 知乎：移动端 API 是后门（已打通，最简单）

**现象**：
- PC 页面 `www.zhihu.com/hot` → Fetcher 403、StealthyFetcher 200 但跳 `signin` 登录墙
- PC API `www.zhihu.com/api/v3/...` → 401 需要登录
- **移动端 API `api.zhihu.com/topstory/...` → 200 直接出 JSON，无需任何 Cookie/签名** ✅

```python
import requests
# 唯一要求：带一个移动端/桌面 UA，加 Referer 更稳
r = requests.get(
    "https://api.zhihu.com/topstory/hot-lists/total?limit=10",
    headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) ...",
             "Referer": "https://www.zhihu.com/"},
    timeout=15)
data = r.json()["data"]   # 热榜 JSON，含 target.title / target.excerpt 等
```

**可用端点**（实测）：
- 热榜：`/topstory/hot-lists/total`（无需登录）
- 问题回答：`/api/v4/questions/{id}/answers` 需登录（401）
- 用户信息：需登录

**结论**：知乎的核心反爬都在 **PC 网页层**，移动端 API 目前未设防（前提是带正确移动端 UA + Referer），是低成本高收益入口。

### 5. B站：先种 buvid3 Cookie 再调 API（已打通）

**现象**：
- 页面 `bilibili.com/v/popular/rank/all` 三种抓取器都 200，但内容是 **JS 壳**（HTML 只有 4KB，数据全靠前端 JS 渲染，需 DynamicFetcher 才能拿到 DOM）
- `api.bilibili.com/x/web-interface/popular` 无 cookie 直接 403
- 搜索 API 无签名 412

**解法**：先访问主站拿 `buvid3` cookie，再调 API 全部 200：

```python
import requests
s = requests.Session()
s.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ... Chrome/120",
    "Referer": "https://www.bilibili.com/",
})
# 1. 预热：访问主站拿 buvid3 + b_nut
s.get("https://www.bilibili.com/", timeout=15)
# 2. 热门视频 ✅（无签名即可）
r = s.get("https://api.bilibili.com/x/web-interface/popular?ps=20&pn=1")
print(r.json()["data"]["list"])   # 视频标题/UP/播放/封面
# 3. 排行榜 ✅
r2 = s.get("https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all")
# 4. 搜索 ✅（带 cookie 后也无需 WBI 签名）
r3 = s.get("https://api.bilibili.com/x/web-interface/search/type",
           params={"search_type": "video", "keyword": "王者荣耀"})
```

**要点**：
- **buvid3 是 B 站所有 API 的通行证**，预热主站即可自动种下
- 搜索/排行/热门接口实测无需 WBI 签名；**部分接口**（如关注列表、互动）需要 wbi 签名，方案见 `SocialSisterYi/bilibili-API-collect`（B站接口官方文档合集，最权威）
- 若 API 返回 `-412`（请求被风控），通常是并发过高或 IP 信誉差，加延时/换 IP

### 6. 抖音：页面内 fetch 绕过 a_bogus 签名（已打通）

**现象**：
- 页面 `douyin.com/hot` 三种抓取器都 200，但内容是 **JS 壳**（榜单异步加载）
- `DynamicFetcher` 渲染后能拿到 200 + RENDER_DATA（132KB），但**热榜数据不在内嵌 JSON 里**（榜单是独立 XHR 拉的）
- `StealthyFetcher` 亦可拿到页面，但同样无榜单
- `DynamicSession` **没有 `.get()` 方法**（只有 fetch），无法直接调 API
- 纯 requests 调热榜 API → 需要 `a_bogus` 签名（Web 端签名算法，社区逆向方案易失效）

**解法**：**Playwright 页面上下文中直接 `fetch` API**，利用页面自身的 JS 签名环境自动生成 `a_bogus`，一次成功（实测拿到 51 条热点）：

```python
import json, asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )
        page = await ctx.new_page()
        # 1. 先访问热榜页，让页面 JS 跑起来（种 cookie、加载签名环境）
        await page.goto("https://www.douyin.com/hot",
                        wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(5000)
        # 2. 在页面上下文中 fetch API（自动带签名环境 a_bogus）
        result = await page.evaluate("""
        async () => {
            const url = 'https://www.douyin.com/aweme/v1/web/hot/search/list/'
                      + '?device_platform=webapp&aid=6383&channel=channel_pc_web'
                      + '&detail_list=1&source=6&pc_client_type=1'
                      + '&version_code=190500&version_name=19.5.0';
            const resp = await fetch(url, {
                headers: {
                    'Accept': 'application/json, text/plain, */*',
                    'Referer': 'https://www.douyin.com/hot',
                }
            });
            return await resp.text();
        }
        """)
        j = json.loads(result)
        words = j["data"]["word_list"]   # 51 条热点话题 [{word, hot_value, schema_url, ...}]
        for w in words[:3]:
            print(w["word"], w["hot_value"], w.get("schema_url"))
        await browser.close()

asyncio.run(main())
```

**要点**：
- **页面内 fetch = 借用浏览器自身签名环境**（`a_bogus` 由页面 JS 自动生成），这是抖音 3 端（PC/移动/App）签名中最容易绕过的路径
- 热搜接口参数：`device_platform=webapp&aid=6383&channel=channel_pc_web&source=6` 等为 PC Web 端固定参数，实测可直接用
- 返回的是**热点话题**（含 `schema_url` 指向搜索页），不是具体视频；要视频列表需再走话题搜索接口
- `DynamicFetcher` / `StealthyFetcher` 能渲染页面但拿不到异步榜单——**页面壳 ≠ 数据可用**，必须确认数据实际来源

### 7. 小红书：登录 Cookie + 探索页 DOM 提取（已打通）

**现象**：
- 页面 `xiaohongshu.com/explore` 三种抓取器都 200，但无登录态时内容是**登录墙**（推荐流不渲染）
- 纯 requests + cookies 调 `edith.xiaohongshu.com/api/sns/web/v1/search/notes` → **404**（接口已变更或需 `xsec_token`）
- 搜索页 DOM 提取 → 0 条（搜索结果需登录或结构变化）
- homefeed API 拦截 → 0 条（未触发）
- 小红书无公开"热榜"接口，最热内容只能从**探索推荐流**按点赞数排序取

**解法**：**Playwright + 登录 Cookie（`xhs-operator/data/cookies.json`）打开探索页，深滚动触发加载后 DOM 提取**，实测拿到 30 条笔记：

```python
import json, asyncio
from playwright.async_api import async_playwright

def load_cookies(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

async def main():
    cookies_list = load_cookies("xhs-operator/data/cookies.json")  # 登录态，9月保存实测仍有效
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )
        await ctx.add_cookies([{
            "name": c["name"], "value": c["value"],
            "domain": c["domain"], "path": c["path"],
            "expires": c.get("expires", -1) if c.get("expires", -1) > 0 else -1,
        } for c in cookies_list])
        page = await ctx.new_page()
        await page.goto("https://www.xiaohongshu.com/explore",
                        wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(6000)
        for _ in range(8):        # 深滚动触发懒加载
            await page.mouse.wheel(0, 2000)
            await page.wait_for_timeout(2500)
        # DOM 提取（section.note-item 卡片，取标题/作者/链接/点赞）
        notes = await page.evaluate("""() => {
            const cards = document.querySelectorAll('section.note-item, .note-item, [class*=note-item]');
            const result = [];
            cards.forEach((c) => {
                const t = c.querySelector('.title, [class*=title]');
                const a = c.querySelector('.author .name, a.author .name, [class*=author] .name');
                const link = c.querySelector('a[href*="/explore/"], a[href*="/discovery/item/"]');
                const idMatch = link ? (link.getAttribute('href') || '').match(/explore\\/([0-9a-f]+)/) : null;
                let likeEl = c.querySelector('.like-wrapper .count, [class*=like] [class*=count]');
                if (!likeEl) likeEl = c.querySelector('span[class*=count]');
                let likeText = likeEl ? likeEl.textContent.trim() : '';
                let likeNum = 0;
                const m = likeText.match(/([0-9.]+)\\s*(万|w|W)?/);
                if (m) {
                    likeNum = parseFloat(m[1]);
                    if (m[2]) likeNum *= 10000;
                }
                if (t && idMatch) result.push({
                    id: idMatch[1],
                    title: t.textContent.trim(),
                    author: a ? a.textContent.trim() : '',
                    like_text: likeText, like_num: likeNum,
                    url: 'https://www.xiaohongshu.com/explore/' + idMatch[1],
                });
            });
            return result;
        }""")
        seen, unique = {}, []
        for n in notes:           # 去重 + 按点赞排序
            if n["id"] not in seen:
                seen[n["id"]] = n
                unique.append(n)
        unique.sort(key=lambda x: x["like_num"], reverse=True)
        for n in unique[:5]:
            print(f"{n['like_text']:>6} 赞 | {n['title'][:45]} | {n['author']}")
        await browser.close()

asyncio.run(main())
```

**要点**：
- **登录 Cookie 是前提**：Cookie 有效期以天计（实测 9 月 5 日保存的到 9 月 10 日仍可用），长期采集需定期更新；Cookie 存于 `xhs-operator/data/cookies.json`
- **探索页 DOM 提取**优于搜索接口：搜索接口 `edith.xiaohongshu.com/api/sns/web/v1/search/notes` 实测 404，homefeed API 需签名且拦截困难
- **注意坑**：作者名会混入点赞数（如 `momo` 与数字混淆），需用正则 `([0-9.]+)\s*(万|w|W)?` 清洗
- 无水印笔记图下载：note URL 加 `/download` 或从页面 `window.__INITIAL_STATE__` 提取（需登录）

### 8. 跨平台通用心法

1. **先探测，再写码**：先用 `curl -I` / 单次请求看状态码、跳转链、Content-Type，判断是页面壳 / 登录墙 / 验证码 / API
2. **页面爬不动 → 找 API**：现代 SPA 站点数据都在 XHR/JSON API，网页壳只是渲染层
3. **PC 爬不动 → 试移动端**：移动端 API 反爬普遍比 PC 松（知乎实测）
4. **API 要 cookie → 先预热**：很多站点"首次访问种 cookie"（B站 buvid3、微博 visitor）
5. **Cookie / 签名**：大规模采集务必配 Cookie 池 + 代理池（GitHub 方案：weibospider、bilibili-api、bilibili-API-collect）
6. **识别"JS 壳"**：HTTP 200 但 HTML 只有几 KB 且无数据 → 必是 SPA，用 DynamicFetcher 或直接调它的 XHR 接口
7. **API 要签名 → 页面内 fetch**：`a_bogus` 这类 JS 签名，与其逆向算法，不如在 Playwright 页面上下文里直接 `fetch` API（抖音实测），签名由页面 JS 自动生成，零逆向成本
8. **登录墙 → 复用登录 Cookie + DOM 提取**：无公开接口时（如小红书），用浏览器登录一次导出 Cookie，后续 Playwright 带 Cookie 打开页面直接提 DOM，比逆向签名接口稳定得多

### 9. 实测环境备注（供复现）

- **测试时间**：2026-09，scrapling 0.4.15，出口 IP 216.38.169.128（本机直连，代理规则未接管）
- **注意**：本机 IP 曾被豆瓣封禁（`movie.douban.com` 403），但**未影响**贴吧/微博/知乎/B站/抖音/小红书的测试结论，说明各平台风控互相独立
- **微博 hotSearch 实测**：完成 visitor 流程后成功拿 52 条热搜（`华为折叠屏` 热度 115 万等）
- **B站实测**：预热主站后 popular（20 条）、ranking（100 条）、search 全部 code=0
- **知乎实测**：移动端 `api.zhihu.com/topstory/hot-lists/total` 直接 200，37905 字节热榜 JSON
- **抖音实测**：Playwright 页面内 fetch 热榜 API，拿到 51 条热点（教师节话题热度 1200 万+）；`DynamicSession` 无 `.get()` 方法
- **小红书实测**：登录 Cookie（9月5日保存）9月10日仍有效，探索页 DOM 提取 30 条，Top 点赞 4.9 万；搜索接口 `edith.../search/notes` 404

## 实战经验（政企采购站点实测）

> 2026-09 对电信招投标核心三站：**中国政府采购网 / 中国电信采购网 / 工信部** 的实测。场景：电信员工日常投标商机监控、政策跟踪。**结论：政府采购网静态可爬、电信采购网瑞数防护可用 StealthyFetcher 绕过、工信部有免登录搜索接口。**

### 总览

| 站点 | 用途 | 纯 requests | 可用方案（实测打通） | 反爬等级 |
|---|---|---|---|---|
| 中国政府采购网 ccgp.gov.cn | 全国政采标讯 | ✅ 列表页直接可爬 | 列表页静态解析 + 搜索接口（需防频控） | 低 |
| 中国电信采购网 caigou.chinatelecom.com.cn | 自家/友商采购项目 | ❌ 只返回瑞数 JS 壳(2KB) | **StealthyFetcher 绕过瑞数**，拿渲染后 DOM | 高（瑞数动态防护） |
| 工信部 miit.gov.cn | 政策文件/通信业数据 | ✅ 搜索接口直通 | `search-front-server/api/search/info` 返回 JSON | 低 |

### 1. 中国政府采购网：列表页静态可爬（最简单）

**现象**：`ccgp.gov.cn/cggg/zygg/index.htm` 等列表页纯 requests 直接 200，公告含日期/标题/链接，`<meta charset="utf-8">`。

```python
import requests, re
r = requests.get("http://www.ccgp.gov.cn/cggg/zygg/index.htm",
                 headers={"User-Agent": UA}, timeout=15)
r.encoding = "utf-8"          # 必须显式设编码，否则中文乱码
items = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.S)
# 过滤导航链接，保留真正公告（标题 ≥10 字）
real = [(re.sub(r'<[^>]+>', '', t).strip(), h) for t, h in items
        if len(re.sub(r'<[^>]+>', '', t).strip()) >= 10]
```

**要点**：
- **必须 `r.encoding = "utf-8"`**，否则中文变 `æ` 乱码（页面无 charset 声明时 `apparent_encoding` 可能误判）
- 列表页本身无分页参数（`index.htm`），分页模式待验证；全量标讯建议走搜索接口
- **搜索接口 `search.ccgp.gov.cn/bxsearch` 有"频繁访问"风控**：实测直接请求返回 2946 字节的"频繁访问"提示页，需带 Referer + Cookie 预热 + 延时，或换代理

### 2. 中国电信采购网：瑞数（Riversafe）动态防护 → StealthyFetcher 可绕过

**现象**：
- 纯 requests 首页 200，但 body 仅 1.9KB，全是 `<script src="/34efae.../confuse/...js">`、`cjs.js`、`f.js` 等动态脚本——典型**瑞数 4 代**防护特征（`/confuse/` 路径 + 每次访问不同的随机 JS 路径）
- 跟随重定向后会种下 `F82089F504F67EE2`、`D1DEA30ACA0D4D8A` 等动态 cookie，但**仍拿不到真实数据**（JS 壳不变）

**解法**：`StealthyFetcher` 直接绕过（实测 4.3 秒拿到 138KB 渲染后 DOM）：

```python
from scrapling.fetchers import StealthyFetcher

page = StealthyFetcher.fetch("https://caigou.chinatelecom.com.cn/",
                             headless=True, network_idle=True, timeout=30000)
html = page.html_content   # 138KB，含真实公告
```

**提取公告**（日期+标题，StealthyFetcher 渲染后 DOM 中公告标题在 `<p>`/tooltip 而非 `<a>`）：
```python
blocks = []
for m in re.finditer(r'(20\d{2}-\d{2}-\d{2})', html):
    start = max(0, m.start() - 250)
    ctx = html[start:m.end() + 30]
    titles = re.findall(r'[>]([^<>]{6,60})[<]', ctx)
    clean = [t.strip() for t in titles if len(t.strip()) >= 6
             and not re.match(r'^[\d\s\-:：/]+$', t.strip())]
    if clean:
        blocks.append((m.group(1), clean[-1]))
```

**要点**：
- 瑞数特征识别：`/confuse/` 路径、`cjs.js`、随机化 JS 文件名（每次不同）、动态 cookie —— 一眼判定，别在 requests 上浪费
- **StealthyFetcher 对瑞数有效**（已实测拿到 27 条真实公告），比 Playwright 更轻量
- 首页即含各省最新公告（广西/河南/甘肃/新疆/天翼云等），监控"寻源公告/采购公告"用首页即可

### 3. 工信部：CMS 搜索接口直通（无需渲染）

**现象**：
- 首页静态可爬（42 条新闻），但**政策文件列表页 `zwgk/zcwj/wjfb/index.html` 只有 2KB**，`window.location.href` 跳转 + CMS 异步加载，无真实列表
- 分页 `index_1.html` 等全部 404

**解法**：页面渲染时发现真实接口 `search-front-server/api/search/info`，纯 requests 直接可调（200 + JSON）：

```python
r = requests.get("https://www.miit.gov.cn/search-front-server/api/search/info",
    params={"websiteid": "110000000000000", "scope": "basic",
            "q": "智能体",          # 关键词，留空返回最新
            "pg": 1, "cateid": 196, "p": 1, "sort": "time"},
    headers={"User-Agent": UA,
             "Referer": "https://www.miit.gov.cn/zwgk/zcwj/wjfb/index.html"},
    timeout=15)
j = r.json()["data"]["searchResult"]["dataResults"]
for it in j:
    d = it["data"]
    print(d["title"], d["cdate"], d["url"])   # cdate 是毫秒时间戳
```

**要点**：
- `cateid=196` 是"政策文件"栏目；`q` 可传关键词（如"智能体"），留空返回最新文件
- **CMS 站点通用套路**：列表页是壳 → 打开浏览器 DevTools 看 XHR → 找到 `search-front-server` 这类搜索接口，纯 requests 直通，比渲染快 10 倍
- 工信部还有政策库/新闻等其他栏目，cateid 不同，可按需探测

### 4. 三站统一采集脚本（关键词过滤 + 去重 + 导出）

上述三站已封装为统一采集脚本 `scripts/gov_procurement_fetch.py`，支持关键词过滤、自动去重、CSV/JSON 导出：

```bash
# 采集全部三站，默认关键词（智能体/Agent/AI/大模型/采购/招标…）
python scripts/gov_procurement_fetch.py

# 指定关键词
python scripts/gov_procurement_fetch.py --kw "智能体,AI,大模型"

# 只采政府采购网+工信部
python scripts/gov_procurement_fetch.py --only ccgp,miit

# 全量采集（不过滤关键词），每站最多 10 条
python scripts/gov_procurement_fetch.py --all --top 10
```

**输出字段**（标准化）：`title, date, source, url, region, category`

**实测结果**（2026-09-10）：
- 政府采购网 37 条（中央+地方公告，今日日期）
- 电信采购网 27 条（各省寻源公告/中标公示，地区自动提取）
- 工信部 1-10 条（政策文件，按关键词搜索）

**脚本设计要点**：
- **去重键**：`(source, title, date)`——电信采购网所有条目 URL 都是首页地址，不能按 URL 去重
- **编码**：政府采购网必须 `r.encoding = "utf-8"`，否则中文乱码
- **URL 修复**：政府采购网链接含 `ccgp.gov.cn.`（多余点），脚本自动修正为 `ccgp.gov.cn/`
- **地区提取**：电信采购网标题前 `【XX】` 格式自动提取为 region 字段
- **输出目录**：默认输出到运行目录（`os.getcwd()`），不污染脚本目录

## 实战经验（金融监管与金融行业站点实测）

> 2026-09-13 从**金融行业视角**（电信员工做金融行业商机、银行/证券/保险招标与监管政策跟踪）实测：**中国人民银行 / 中国证监会 / 中国招标投标公共服务平台**。结论：央行、证监会静态列表页可爬（含详情正文），招标平台列表分页可爬（详情 SPA 反爬只取列表）；金融监管总局（JS 壳 + 接口全 404）与中央政采（接口返回 `code:-1`）暂不可行。

### 总览

| 站点 | 用途 | 纯 requests | 可用方案（实测打通） | 反爬等级 |
|---|---|---|---|---|
| 央行 pbc.gov.cn | 货币政策/新闻发布/金融数据 | ✅ 列表+详情均可爬 | 静态列表解析 + TRS_Editor 正文提取 | 低 |
| 证监会 csrc.gov.cn | 监管动态/政策/IPO 信息 | ✅ 列表可爬 | 静态列表解析（`content.shtml` 详情） | 低 |
| 招标投标公共服务平台 bulletin.cebpubservice.com | 全国招投标公告（金融/政府/国企） | ✅ 列表分页可爬 | 搜索接口分页（`bulletin.html?searchDate=...`） | 中（详情 SPA 反爬） |
| 金融监管总局 nfra.gov.cn | 银行/保险监管政策 | ❌ JS 壳 | 无（`/DocInfo/` 系列接口全 404，放弃） | 高（纯 JS 壳） |
| 中央政采 zycg.gov.cn | 中央单位采购公告 | ❌ 接口报错 | REST 接口返回 `{"msg":"公告列表查询失败","code":"-1"}`，站端问题，放弃 | 中 |

### 1. 央行：静态列表 + 详情正文（最简单）

**现象**：`pbc.gov.cn/goutongjiaoliu/113456/113469/index.html`（新闻发布）纯 requests 200，列表为 `<font class="newslist_style"><a href="...">标题</a></font><span class="hui12">2026-09-11</span>` 结构。

```python
import requests, re
r = requests.get("http://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html",
                 headers={"User-Agent": UA}, timeout=15)
r.encoding = "utf-8"   # 必须显式设置，否则中文乱码
rows = re.findall(
    r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?<span class="hui12">(\d{4}-\d{2}-\d{2})</span>',
    r.text, re.S)
# 过滤非详情链接：央行详情 URL 形如 /goutongjiaoliu/.../2026091115515046822/index.html
real = [(re.sub(r'<[^>]+>', '', t).strip(), h, d) for h, t, d in rows
        if re.search(r'/20\d{10,}/', h)]   # 详情路径含 20 位时间戳
```

**要点**：
- **必须 `r.encoding = "utf-8"`**，否则中文乱码（与政采网同理）
- 标题提取**用 `<a href>文本</a>`**，不要用 `title` 属性——央行链接带 `istitle="true"` 干扰
- **详情 URL 过滤**：栏目导航/首页链接不含 `/20\d{10,}/`（20 位时间戳），用该正则精准过滤
- **详情正文**：容器 `class="TRS_Editor"` 或 `class="xl_xxy"`，`re.search(r'(?:class|id)="(?:content|article|TRS_Editor|xl_xxy)[^"]*"[^>]*>(.*?)</(?:div|section)>', ...)` 可提取
- 常用栏目：新闻发布 `113469`、货币政策 `125440`（LPR 公告）、金融数据统计等

### 2. 证监会：静态列表页（`content.shtml` 详情）

**现象**：`csrc.gov.cn/csrc/c100028/common_list.shtml`（新闻发布）纯 requests 200，条目 `<a href="/csrc/c100028/c1615676/content.shtml">标题</a>` 结构，详情页为 `content.shtml` 后缀。

```python
r = requests.get("http://www.csrc.gov.cn/csrc/c100028/common_list.shtml",
                 headers={"User-Agent": UA}, timeout=15)
r.encoding = "utf-8"
items = re.findall(r'<a[^>]+href="([^"]*content\.shtml)"[^>]*>([^<]{6,})</a>', r.text)
# 返回 (href, 标题)，补齐域名即可访问详情
```

**要点**：
- 列表页**无日期字段**（表格里只有标题+链接），date 留空；要日期需进详情页
- 栏目路径 `c100028` 为新闻发布、`c101954` 为信息公开，可按需替换
- 同域名其他栏目（行政处罚、IPO 审核等）结构相同，改栏目 ID 即可复用

### 3. 招标投标公共服务平台：列表分页可爬，详情 SPA 反爬

**现象**：
- 首页是 JS 异步加载，但**搜索列表页** `bulletin.cebpubservice.com/xxfbcmses/search/bulletin.html` 纯 requests 可拿表格（每页 20 条）
- **必须带 `searchDate`（当前日期减 N 天）**，否则查不到数据；`dates=30` 控制回看天数
- 表格 6 列：标题（含 uuid）、分类、地区、平台、日期、状态；公告链接为 `javascript:urlOpen('uuid')`
- **详情页是 SPA**（`ctbpsp.com/#/bulletinDetail?uuid=...`），真实详情 API `/cutominfoapi/bulletin/{uuid}` 返回 JS 混淆壳（反爬），**只取列表不取详情**

```python
import datetime
t = datetime.date.today() - datetime.timedelta(days=30)
url = ("https://bulletin.cebpubservice.com/xxfbcmses/search/bulletin.html?"
       f"searchDate={t.strftime('%Y-%m-%d')}&dates=30&word=&categoryId=88"
       "&industryName=&area=&status=&publishMedia=&sourceInfo=&showStatus=&page=1")
r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
trs = re.findall(r'<tr[^>]*>.*?</tr>', r.text, re.S)
for tr in trs[1:]:  # 跳过表头
    tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)
    uuid = re.search(r"urlOpen\('([^']+)'\)", tds[0]).group(1)
    title = re.sub(r'<[^>]+>', '', tds[0]).strip()  # 或取 <a> 内文本
    # tds[2] 地区(【辽宁】), tds[4] 日期  → 拼详情链接
```

**要点**：
- **`searchDate` 必须传**，不传/传错则返回空表（容易踩的坑）
- **翻页无验证码**：VAPTCHA 校验逻辑在 JS 中已注释，`page=2` 直接可翻
- `categoryId`：88 招标公告 / 89 变更 / 90 结果 / 91 候选人 / 92 资格
- **详情链接**用 `https://ctbpsp.com/#/bulletinDetail?uuid={uuid}` 形式，用户在浏览器可打开
- 该平台聚合全国公共资源交易/央企/国企/各地采购平台公告，是**跨平台标讯监控**的好入口

### 4. 三站统一采集脚本（关键词过滤 + 去重 + 导出）

三站已封装为统一采集脚本 `scripts/finance_regulatory_fetch.py`，支持指定站点、关键词过滤、去重、CSV/JSON 导出：

```bash
# 采集全部三站，默认关键词（智能体/Agent/AI/金融/银行/证券/招标/采购…）
python scripts/finance_regulatory_fetch.py

# 指定关键词（金融行业视角）
python scripts/finance_regulatory_fetch.py --kw "智能体,AI,金融,银行,采购,招标"

# 只采央行+证监会
python scripts/finance_regulatory_fetch.py --only pbc,csrc

# 全量采集（不过滤），每站最多 10 条
python scripts/finance_regulatory_fetch.py --all --top 10
```

**输出字段**（与政企脚本一致）：`title, date, source, url, region, category`

**实测结果**（2026-09-13）：
- 央行 17 条（新闻发布 + 货币政策，含日期）
- 证监会 18 条（新闻发布/信息公开，日期留空需进详情）
- 招标平台 20 条（全国跨平台招标公告，含地区/平台/分类）

**脚本设计要点**：
- **去重键** `(source, title, date)`：招标平台每条 uuid 不同但同一公告可能跨平台重复，标题+日期去重更稳
- **编码**：央行必须 `r.encoding = "utf-8"`
- **央行详情过滤**：`re.search(r'/20\d{10,}/', href)` 识别真实详情链接（20 位时间戳路径）
- **招标平台**：`searchDate` 必须为当前日期减 N 天；地区列 `【XX】` 自动提取

## 自检脚本

运行 `scripts/run_selftest.py` 执行官方 94 项 parser 测试，验证 Scrapling 安装是否正常：

```bash
python scripts/run_selftest.py
# 期望输出: ✅ 全部测试通过! Scrapling 安装正常。
```

## 注意事项

- 完整抓取功能需要 `pip install "scrapling[fetchers]"` + `scrapling install` 下载浏览器
- 基础安装只含解析器，直接 import fetchers 会报 ModuleNotFoundError
- Markdown 转换需要安装 `pip install "scrapling[rag]"`
- 网络代理按需求配置，可配合代理轮换（ProxyRotator）
- `page.markdown()` 是 Page 对象方法，Selector/Element 没有；带选择器转 Markdown 用 `markdownify`
- `generate_css_selector` / `generate_xpath_selector` 是属性不是方法，不加括号
- DOM 导航用 `.next` / `.previous` / `.siblings`，不是 `next_sibling`
- 更多高级特性（MCP、RAG、代理）见 `references/README.md`

## 打包

| 文件 | 说明 |
|---|---|
| `scripts/basic_scrape.py` | 基础请求采集器 — 单页抓取 + CSS 选择器提取 |
| `scripts/session_scrape.py` | 会话模式采集器 — 保持 Cookie 连续多页抓取 |
| `scripts/spider_crawl.py` | 全站翻页爬虫 — Spider 框架自动翻页 + 四格式导出 |
| `scripts/parse_html.py` | 离线 HTML 解析器 — 本地文件解析，支持 CSS/XPath/find_all |
| `scripts/to_markdown.py` | 网页转 Markdown — 抓取网页转 LLM 友好格式 |
| `scripts/stealth_scrape.py` | 隐身抓取采集器 — 绕过 Cloudflare 等反爬验证 |
| `scripts/proxy_rotation.py` | 代理轮换采集器 — 多代理自动轮换防封禁 |
| `scripts/dynamic_render.py` | 浏览器自动化采集器 — JS 动态渲染页面抓取 |
| `scripts/site_to_markdown.py` | 全站转 Markdown 爬虫 — 自动遍历整站转 Markdown |
| `scripts/resume_crawl.py` | 断点续传爬虫 — 支持暂停/恢复的大规模爬取 |
| `scripts/domestic_platform_probe.py` | 国内四大平台探测 — 一键实测贴吧/微博/知乎/B站可用性与反爬（抖音/小红书见 `douyin_hot_pw.py` / `xhs_explore_dom.py`） |
| `scripts/douyin_hot_pw.py` | 抖音热榜抓取 — Playwright 页面内 fetch 绕过 a_bogus 签名（已实测 51 条） |
| `scripts/xhs_explore_dom.py` | 小红书探索页抓取 — 登录 Cookie + DOM 提取 + 按点赞排序（已实测 30 条） |
| `scripts/gov_procurement_probe.py` | 政企采购三站探测 — 政府采购网/电信采购网/工信部 一键实测（含瑞数绕过） |
| `scripts/gov_procurement_fetch.py` | 政企招投标三站统一采集 — 关键词过滤+去重+CSV/JSON 导出（已实测 65 条） |
| `scripts/finance_regulatory_fetch.py` | 金融监管与金融行业三站统一采集 — 央行/证监会/招标投标公共服务平台（已实测 55 条） |
| `scripts/run_selftest.py` | 官方测试一键自检 — 94 项断言验证安装 |
| `scripts/selftest/` | 官方 parser 测试套件（6 个测试文件） |
| `references/README.md` | 项目官方 README（完整文档入口） |

## 参考

- 触发场景：用户需要网页抓取、数据采集、绕过反爬、爬虫框架
- 详细文档：https://scrapling.readthedocs.io/