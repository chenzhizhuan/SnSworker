#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
search_tools.py — SuperAgent 内置零配置多平台搜索工具
仅依赖 Python 标准库（urllib + json），无需安装任何第三方工具。
覆盖：GitHub / B站 / Reddit / Hacker News / V2EX / Jina Reader（网页阅读）

用法:
    python search_tools.py github "python web framework" -n 5
    python search_tools.py bilibili "AI教程" -n 5
    python search_tools.py reddit "electric cars" -n 5
    python search_tools.py hackernews "Rust" -n 5
    python search_tools.py v2ex
    python search_tools.py hackernews-trending
    python search_tools.py read "https://example.com/article"
    python search_tools.py doctor

每条结果输出 JSON 数组元素，包含 title/url/desc/score/source 等字段。
搜索状态遵循 web-search-enhancement.md 七态规范。
"""

import argparse
import hashlib
import json
import urllib.request
import urllib.parse
import urllib.error
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# ========== 全局配置 ==========

VERSION = "1.0.0"
TIMEOUT = 15  # 单次请求超时秒数
USER_AGENT = "SuperAgent-SearchTools/{}".format(VERSION)
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ========== 工具函数 ==========

def _http_get(url, headers=None, timeout=TIMEOUT):
    """发起 HTTP GET 请求，返回 (status_code, body_text) 或 (error_status, None)。"""
    if headers is None:
        headers = {}
    if "User-Agent" not in headers:
        headers["User-Agent"] = USER_AGENT
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
        return "unreachable:{}".format(type(e).__name__), None


def _output_results(platform, items):
    """统一输出搜索结果为 JSON 数组。

    Args:
        platform: 平台名称（保留用于语义标注，当前未在输出中使用）。
        items: 搜索结果列表。
    """
    print(json.dumps(items, ensure_ascii=False, indent=2))


def _parse_json_response(body, platform_name):
    """解析 JSON 响应体，失败时输出错误并返回 None。

    统一处理 json.loads + 类型守卫，消除5处重复的 try/isinstance 模式。
    """
    if not body:
        return None
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        _output_status(platform_name, "error", "响应JSON解析失败")
        return None
    if not isinstance(data, dict):
        _output_status(platform_name, "error", "响应格式异常（非JSON对象）")
        return None
    return data


def _output_status(platform, status, message=""):
    """输出搜索状态（七态规范）。"""
    obj = {"platform": platform, "status": status, "items": [], "message": message}
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _truncate(text, max_len=200):
    """截断文本到指定长度。"""
    if not text:
        return ""
    text = text.strip().replace("\n", " ")
    return text[:max_len - 3] + "..." if len(text) > max_len else text


# ========== GitHub 搜索 ==========

def search_github(query, num=10):
    """通过 GitHub REST API 搜索仓库（免认证，限 10 次/分钟）。"""
    encoded = urllib.parse.quote(query)
    url = "https://api.github.com/search/repositories?q={}&sort=stars&order=desc&per_page={}".format(
        encoded, min(num, 30)
    )
    code, body = _http_get(url, headers={"Accept": "application/vnd.github.v3+json"})

    if code == 200 and body:
        data = _parse_json_response(body, "GitHub")
        if data is None:
            return
        items = []
        _github_items = data.get("items", [])
        if not isinstance(_github_items, list):
            _github_items = []
        for repo in _github_items[:num]:
            if not isinstance(repo, dict):
                continue
            items.append({
                "platform": "GitHub",
                "title": repo.get("full_name", ""),
                "url": repo.get("html_url", ""),
                "desc": _truncate(repo.get("description", "")),
                "stars": repo.get("stargazers_count", 0),
                "language": repo.get("language", ""),
                "source": "GitHub API",
                "status": "ok"
            })
        _output_results("GitHub", items)
    elif code == 403:
        _output_status("GitHub", "rate-limited", "GitHub API 限流（免认证 10次/分钟）")
    elif str(code).startswith("unreachable"):
        _output_status("GitHub", "unreachable", "网络不可达")
    else:
        _output_status("GitHub", "no-results", "HTTP {}".format(code))


# ========== B站搜索 ==========

# WBI签名所需的反转字符表（B站固定值）
_WBI_MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 11, 22, 30, 41, 14, 37, 44, 13, 52, 6, 24, 28,
    55, 20, 36, 17, 19, 0, 38, 51, 57, 7, 4, 21, 16, 29, 63, 34,
    25, 61, 9, 60, 26, 1, 40, 48, 33, 59, 42, 62, 54, 12, 39, 56
]


def _wbi_get_mixin_key(img_key, sub_key):
    """从 img_key 和 sub_key 生成 mixin_key（B站 WBI 签名核心步骤）。"""
    raw = img_key + sub_key
    if len(raw) < 64:
        return None
    return "".join(raw[i] for i in _WBI_MIXIN_KEY_ENC_TAB)[:32]


def _wbi_sign_params(params, mixin_key):
    """对查询参数添加 w_rid 和 wts 签名。"""
    params["wts"] = int(time.time())
    # 按 key 排序后拼接
    query = urllib.parse.urlencode(sorted(params.items()))
    w_rid = hashlib.md5((query + mixin_key).encode("utf-8")).hexdigest()
    params["w_rid"] = w_rid
    return params


def _wbi_get_keys():
    """从 B站 nav API 获取 img_key 和 sub_key。返回 (img_key, sub_key) 或 None。"""
    code, body = _http_get(
        "https://api.bilibili.com/x/web-interface/nav",
        headers={"User-Agent": BROWSER_UA}
    )
    if code == 200 and body:
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        wbi_img = (data.get("data") or {}).get("wbi_img", {})
        img_url = wbi_img.get("img_url", "")
        sub_url = wbi_img.get("sub_url", "")
        img_key = img_url.rsplit("/", 1)[-1].split(".")[0] if img_url else ""
        sub_key = sub_url.rsplit("/", 1)[-1].split(".")[0] if sub_url else ""
        if img_key and sub_key:
            return img_key, sub_key
    return None


def search_bilibili(query, num=10):
    """通过 B站公开搜索 API 搜索视频（支持 WBI 签名）。"""
    encoded = urllib.parse.quote(query)
    page_size = min(num, 20)

    # 尝试获取 WBI 密钥并签名
    wbi_keys = _wbi_get_keys()
    if wbi_keys:
        img_key, sub_key = wbi_keys
        mixin_key = _wbi_get_mixin_key(img_key, sub_key)
        params = {
            "search_type": "video",
            "keyword": query,
            "page": 1,
            "page_size": page_size,
        }
        if mixin_key:
            signed_params = _wbi_sign_params(params, mixin_key)
            query_string = urllib.parse.urlencode(signed_params)
            url = "https://api.bilibili.com/x/web-interface/wbi/search/type?{}".format(query_string)
        else:
            url = "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={}&page=1&page_size={}".format(
                encoded, page_size
            )
    else:
        # WBI 密钥获取失败，降级为传统端点（不带 wbi 前缀）
        url = "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={}&page=1&page_size={}".format(
            encoded, page_size
        )

    code, body = _http_get(url, headers={
        "User-Agent": BROWSER_UA,
        "Referer": "https://www.bilibili.com"
    })

    if code == 200 and body:
        data = _parse_json_response(body, "B站")
        if data is None:
            return
        results = (data.get("data") or {}).get("result", [])
        if not isinstance(results, list):
            results = []
        if not results and data.get("code") != 0:
            _output_status("B站", "rate-limited", data.get("message", "B站搜索被限流"))
            return
        items = []
        for v in results[:num]:
            if not isinstance(v, dict):
                continue
            # B站搜索结果 title 含 <em class="keyword"> 标签，需清理
            title = v.get("title", "").replace('<em class="keyword">', "").replace("</em>", "")
            bvid = v.get("bvid", "")
            vid_url = "https://www.bilibili.com/video/{}".format(bvid) if bvid else v.get("arcurl", "")
            items.append({
                "platform": "B站",
                "title": title,
                "url": vid_url,
                "desc": _truncate(v.get("description", "")),
                "play": v.get("play", 0),
                "danmaku": v.get("video_review", 0),
                "author": v.get("author", ""),
                "source": "Bilibili API",
                "status": "ok"
            })
        _output_results("B站", items)
    elif str(code).startswith("unreachable"):
        _output_status("B站", "unreachable", "网络不可达")
    else:
        _output_status("B站", "no-results", "HTTP {}".format(code))


# ========== Reddit 搜索 ==========

def search_reddit(query, num=10):
    """通过 Reddit 公开 JSON API 搜索帖子。"""
    encoded = urllib.parse.quote(query)
    url = "https://www.reddit.com/search.json?q={}&limit={}&sort=relevance".format(
        encoded, min(num, 25)
    )
    code, body = _http_get(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SuperAgent/1.0"
    })

    if code == 200 and body:
        data = _parse_json_response(body, "Reddit")
        if data is None:
            return
        children = (data.get("data") or {}).get("children", [])
        if not isinstance(children, list):
            children = []
        items = []
        for child in children[:num]:
            if not isinstance(child, dict):
                continue
            d = child.get("data", {})
            if not isinstance(d, dict):
                d = {}
            selftext = d.get("selftext", "")
            items.append({
                "platform": "Reddit",
                "title": d.get("title", ""),
                "url": "https://www.reddit.com{}".format(d.get("permalink", "")),
                "desc": _truncate(selftext) if selftext else _truncate(d.get("title", "")),
                "score": d.get("score", 0),
                "comments": d.get("num_comments", 0),
                "subreddit": d.get("subreddit", ""),
                "author": d.get("author", ""),
                "source": "Reddit JSON API",
                "status": "ok"
            })
        _output_results("Reddit", items)
    elif code == 429:
        _output_status("Reddit", "rate-limited", "Reddit 限流")
    elif str(code).startswith("unreachable"):
        _output_status("Reddit", "unreachable", "网络不可达")
    else:
        _output_status("Reddit", "no-results", "HTTP {}".format(code))


# ========== Hacker News 搜索 ==========

def search_hackernews(query, num=10):
    """通过 Algolia HN Search API 搜索 Hacker News 帖子。"""
    encoded = urllib.parse.quote(query)
    url = "https://hn.algolia.com/api/v1/search?query={}&hitsPerPage={}&tags=story".format(
        encoded, min(num, 50)
    )
    code, body = _http_get(url)

    if code == 200 and body:
        data = _parse_json_response(body, "Hacker News")
        if data is None:
            return
        hits = data.get("hits", [])
        if not isinstance(hits, list):
            hits = []
        items = []
        for h in hits[:num]:
            if not isinstance(h, dict):
                continue
            items.append({
                "platform": "Hacker News",
                "title": h.get("title", h.get("story_title", "")),
                "url": h.get("url") or "https://news.ycombinator.com/item?id={}".format(h.get("objectID", "")),
                "points": h.get("points", 0),
                "comments": h.get("num_comments", 0),
                "author": h.get("author", ""),
                "hn_url": "https://news.ycombinator.com/item?id={}".format(h.get("objectID", "")),
                "created_at": h.get("created_at", ""),
                "source": "HN Algolia API",
                "status": "ok"
            })
        _output_results("Hacker News", items)
    elif str(code).startswith("unreachable"):
        _output_status("Hacker News", "unreachable", "网络不可达")
    else:
        _output_status("Hacker News", "no-results", "HTTP {}".format(code))


def trending_hackernews(num=10):
    """获取 Hacker News 前条热门帖子（Front Page）。

    BUG-4修复：Firebase REST API 的 limitToFirst 必须配合 orderBy 使用，
    否则返回 HTTP 400（'limitToFirst' requires an 'orderBy'）。
    添加 orderBy="$key" 后按 key 顺序返回前 N 条 topstories。
    """
    num = min(max(num, 1), 30)
    # orderBy="$key" 需要 URL 编码（%22 为引号，%24 为 $）
    url = ("https://hacker-news.firebaseio.com/v0/topstories.json"
           "?orderBy=%22%24key%22&limitToFirst={}").format(num)
    code, body = _http_get(url)

    if code != 200 or not body:
        _output_status("Hacker News", "unreachable" if str(code).startswith("unreachable") else "no-results", "HTTP {}".format(code))
        return

    try:
        ids = json.loads(body)
    except json.JSONDecodeError:
        _output_status("Hacker News", "error", "响应JSON解析失败")
        return
    if not isinstance(ids, list):
        _output_status("Hacker News", "error", "响应格式异常（非JSON数组）")
        return

    def _fetch_hn_item(item_id):
        """获取单个 HN item 详情。"""
        item_url = "https://hacker-news.firebaseio.com/v0/item/{}.json".format(item_id)
        c2, b2 = _http_get(item_url)
        if c2 == 200 and b2:
            try:
                d = json.loads(b2)
            except json.JSONDecodeError:
                return None
            if not isinstance(d, dict):
                return None
            return {
                "platform": "Hacker News",
                "title": d.get("title", ""),
                "url": d.get("url") or "https://news.ycombinator.com/item?id={}".format(item_id),
                "points": d.get("score", 0),
                "comments": d.get("descendants", 0),
                "author": d.get("by", ""),
                "hn_url": "https://news.ycombinator.com/item?id={}".format(item_id),
                "source": "HN Firebase API",
                "status": "ok"
            }
        return None

    items = []
    fetch_ids = ids[:num * 2]
    executor = ThreadPoolExecutor(max_workers=5)
    try:
        future_map = {executor.submit(_fetch_hn_item, iid): iid for iid in fetch_ids}
        for future in as_completed(future_map):
            try:
                result = future.result()
            except Exception:
                result = None
            if result:
                items.append(result)
                if len(items) >= num:
                    for f in future_map:
                        f.cancel()
                    break
    finally:
        executor.shutdown(wait=False)
    _output_results("Hacker News", items)


# ========== V2EX 热门 ==========

def v2ex_hot(num=20):
    """获取 V2EX 热门帖子。"""
    url = "https://www.v2ex.com/api/topics/hot.json"
    code, body = _http_get(url, headers={"User-Agent": USER_AGENT})

    if code == 200 and body:
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            _output_status("V2EX", "error", "响应JSON解析失败")
            return
        if not isinstance(data, list):
            _output_status("V2EX", "error", "响应格式异常（非JSON数组）")
            return
        items = []
        for t in data[:num]:
            if not isinstance(t, dict):
                continue
            items.append({
                "platform": "V2EX",
                "title": t.get("title", ""),
                "url": "https://www.v2ex.com/t/{}".format(t.get("id", "")),
                "replies": t.get("replies", 0),
                "author": t.get("member", {}).get("username", ""),
                "node": t.get("node", {}).get("title", ""),
                "source": "V2EX API",
                "status": "ok"
            })
        _output_results("V2EX", items)
    elif str(code).startswith("unreachable"):
        _output_status("V2EX", "unreachable", "网络不可达")
    elif code == 403:
        _output_status("V2EX", "rate-limited", "V2EX API 限流")
    else:
        _output_status("V2EX", "no-results", "HTTP {}".format(code))


# ========== Jina Reader（网页阅读） ==========

def read_url(target_url):
    """通过 Jina Reader 将网页转为可读文本。"""
    jina_url = "https://r.jina.ai/{}".format(urllib.parse.quote(target_url, safe=':/?&=%'))
    code, body = _http_get(jina_url, timeout=30)

    if code == 200 and body:
        # Jina 返回 Markdown 文本，截断到 3000 字符
        truncated = _truncate(body, 3000)
        result = [{
            "platform": "Jina Reader",
            "url": target_url,
            "content": truncated,
            "source": "Jina Reader API",
            "status": "ok"
        }]
        _output_results("Jina Reader", result)
    elif str(code).startswith("unreachable"):
        _output_status("Jina Reader", "unreachable", "网络不可达或 Jina 服务不可达")
    elif code == 422:
        _output_status("Jina Reader", "no-results", "URL 无法解析: {}".format(target_url))
    else:
        _output_status("Jina Reader", "no-results", "HTTP {}".format(code))


# ========== Doctor 体检 ==========

def doctor():
    """检测所有内置通道是否可用（快速连通性测试）。"""
    checks = [
        ("GitHub",      "https://api.github.com/rate_limit", "GitHub API"),
        ("B站",         "https://api.bilibili.com/x/web-interface/zone", "Bilibili API"),
        ("Reddit",      "https://www.reddit.com/.json?limit=1", "Reddit JSON API"),
        ("Hacker News", "https://hn.algolia.com/api/v1/search?query=test&hitsPerPage=1", "HN Algolia API"),
        ("V2EX",        "https://www.v2ex.com/api/topics/hot.json", "V2EX API"),
        ("Jina Reader", "https://r.jina.ai/https://example.com", "Jina Reader API"),
    ]
    results = []
    for name, url, desc in checks:
        start = time.time()
        code, _ = _http_get(url, timeout=8)
        elapsed = round(time.time() - start, 2)
        if code == 200:
            status = "active"
            message = "OK ({}s)".format(elapsed)
        elif code == 403 or code == 429:
            status = "rate-limited"
            message = "限流 HTTP {} ({}s)".format(code, elapsed)
        elif str(code).startswith("unreachable"):
            status = "unreachable"
            message = "不可达 ({}s)".format(elapsed)
        else:
            status = "error"
            message = "HTTP {} ({}s)".format(code, elapsed)
        results.append({
            "name": name, "desc": desc, "status": status, "message": message
        })
    print(json.dumps(results, ensure_ascii=False, indent=2))


# ========== 主入口 ==========

def main():
    parser = argparse.ArgumentParser(
        description="SuperAgent 内置零配置搜索工具 v{}（GitHub/B站/Reddit/HN/V2EX/Jina）".format(VERSION),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("platform", choices=[
        "github", "bilibili", "reddit", "hackernews", "hackernews-trending",
        "v2ex", "read", "doctor"
    ], help=(
        "github:              搜索 GitHub 仓库\n"
        "bilibili:            搜索 B站视频\n"
        "reddit:              搜索 Reddit 帖子\n"
        "hackernews:          搜索 Hacker News\n"
        "hackernews-trending: 获取 HN 热门\n"
        "v2ex:                获取 V2EX 热门\n"
        "read:                用 Jina Reader 阅读网页\n"
        "doctor:              体检所有通道连通性\n"
    ))
    parser.add_argument("query", nargs="?", default="", help="搜索关键词（v2ex/doctor 不需要）")
    parser.add_argument("-n", "--num", type=int, default=10, help="返回结果数量（默认10）")

    args = parser.parse_args()

    if args.platform == "doctor":
        doctor()
    elif args.platform == "v2ex":
        v2ex_hot(args.num)
    elif args.platform == "hackernews-trending":
        trending_hackernews(args.num)
    elif args.platform == "read":
        if not args.query:
            parser.error("read 需要提供 URL 参数")
        read_url(args.query)
    elif args.platform == "github":
        if not args.query:
            parser.error("github 需要搜索关键词")
        search_github(args.query, args.num)
    elif args.platform == "bilibili":
        if not args.query:
            parser.error("bilibili 需要搜索关键词")
        search_bilibili(args.query, args.num)
    elif args.platform == "reddit":
        if not args.query:
            parser.error("reddit 需要搜索关键词")
        search_reddit(args.query, args.num)
    elif args.platform == "hackernews":
        if not args.query:
            parser.error("hackernews 需要搜索关键词")
        search_hackernews(args.query, args.num)


if __name__ == "__main__":
    main()
