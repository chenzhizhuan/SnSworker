#!/usr/bin/env python3
"""
通用 MCP 客户端：通过 TeleAgent 动态鉴权直连 mcp-media-hub 服务。

三步鉴权流程：
  1. 首次请求携带请求头 `x-from-teleAgent: true`
  2. 服务端响应头返回 `X-Mcp-Token: <动态token>`
  3. 后续请求携带 `Authorization: Bearer <token>` + `Mcp-Session-Id: <sid>`

支持全部 7 个工具：generate_prompt / text_to_image / image_to_image /
                   text_to_video / image_to_video / query_video / list_models

用法示例：

  # 文生图（4K 海报）
  python mcp_media_client.py text_to_image \
    --intent "电信AI科技宣传海报，未来城市与AI神经网络交汇" \
    --size 2048x2048

  # 文生视频
  python mcp_media_client.py text_to_video \
    --intent "日落海滩，缓慢推进镜头" --duration 5 --size 1280x720

  # 列出可用模型
  python mcp_media_client.py list_models --capability text2image

  # 查询视频任务
  python mcp_media_client.py query_video --video-id task_xxxx

依赖：仅 Python 标准库（urllib），无第三方依赖。
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# ──────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────

DEFAULT_MCP_URL = "https://mcp.bbdict.com/hub/mcp"
DEFAULT_TIMEOUT = 30
VIDEO_TIMEOUT = 900          # 视频生成可能很慢，给 15 分钟
NEGATIVE_PROMPT = "blurry, distorted, low quality, watermark, text artifacts, ugly, deformed"

TOOLS = ["text_to_image", "image_to_image", "text_to_video",
         "image_to_video", "generate_prompt", "query_video", "list_models"]


# ──────────────────────────────────────────────
# 三步鉴权：x-from-teleAgent → X-Mcp-Token → Bearer
# ──────────────────────────────────────────────

def _post_raw(url, body, headers, timeout=DEFAULT_TIMEOUT):
    """发送 JSON-RPC POST，返回 (响应头dict, 响应体文本)。"""
    data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, headers=headers, method="POST")
    with urlopen(req, timeout=timeout) as r:
        return dict(r.headers), r.read().decode("utf-8")


def mcp_handshake(url):
    """
    第一步鉴权：首请求带 `x-from-teleAgent: true`，
    从响应头拿 `Mcp-Session-Id` 和 `X-Mcp-Token`。
    """
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "x-from-teleAgent": "true",
    }
    body = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "mcp_media_client", "version": "1.0"},
        },
    }
    hdrs, _ = _post_raw(url, body, headers, timeout=DEFAULT_TIMEOUT)
    sid = hdrs.get("Mcp-Session-Id") or hdrs.get("mcp-session-id")
    token = hdrs.get("X-Mcp-Token") or hdrs.get("x-mcp-token")
    return sid, token


def mcp_call(url, sid, token, method, params, rid=2, timeout=DEFAULT_TIMEOUT):
    """
    第二/三步鉴权：后续请求带 `Authorization: Bearer <token>` + `Mcp-Session-Id`。
    JSON-RPC 2.0 通知（notifications/*）不带 id。
    """
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if sid:
        headers["Mcp-Session-Id"] = sid
    if token:
        headers["Authorization"] = f"Bearer {token}"

    is_notification = method.startswith("notifications/")
    if is_notification:
        body = {"jsonrpc": "2.0", "method": method, "params": params}
    else:
        body = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params}

    try:
        _, text = _post_raw(url, body, headers, timeout=timeout)
        return _parse_sse(text) if text else ""
    except HTTPError as e:
        return _parse_sse(e.read().decode("utf-8", errors="replace"))


def _parse_sse(text):
    """从 SSE 响应中提取 data: 负载。"""
    out = []
    for line in text.splitlines():
        if line.startswith("data: "):
            out.append(line[6:].strip())
    return "\n".join(out) if out else text


def mcp_connect(url):
    """完整的 MCP 连接：握手 → initialized 通知 → 返回 (sid, token)。"""
    sid, token = mcp_handshake(url)
    if not token:
        raise RuntimeError(
            "握手未拿到 X-Mcp-Token！\n"
            "  可能原因：\n"
            "  1. 服务端 TeleAgent 透明鉴权不可用\n"
            "  2. 网络代理拦截了响应头\n"
            "  3. 服务端返回 403 表示已暂停"
        )
    # 发送 initialized 通知（通知不带 id，符合 JSON-RPC 2.0 规范）
    try:
        mcp_call(url, sid, token, "notifications/initialized", {})
    except Exception:
        pass
    return sid, token


# ──────────────────────────────────────────────
# 工具调用封装
# ──────────────────────────────────────────────

def call_tool(url, sid, token, name, arguments, timeout=DEFAULT_TIMEOUT):
    """调用 MCP tools/call，返回解析后的结果 dict。"""
    raw = mcp_call(url, sid, token, "tools/call",
                   {"name": name, "arguments": arguments}, timeout=timeout)
    return parse_tool_result(raw), raw


def parse_tool_result(raw):
    """解析 tools/call 返回，提取内容文本和 URL。"""
    result = {"ok": True, "is_error": False, "text": "", "url": None,
              "raw": raw, "data": {}}
    try:
        d = json.loads(raw)
        if "result" in d and isinstance(d["result"], dict):
            result["is_error"] = bool(d["result"].get("isError"))
            contents = d["result"].get("content", [])
            for c in contents:
                if isinstance(c, dict) and "text" in c:
                    result["text"] += c["text"]
                    try:
                        inner = json.loads(c["text"])
                        if isinstance(inner, dict):
                            result["data"].update(inner)
                            if inner.get("ok") is False:
                                result["ok"] = False
                            for k in ("url", "video_url", "download_url"):
                                if not result["url"] and inner.get(k):
                                    result["url"] = inner.get(k)
                    except json.JSONDecodeError:
                        pass
                    if not result["url"]:
                        m = re.search(r'https?://[^\s"\'<>]+', c["text"])
                        if m:
                            result["url"] = m.group(0)
    except json.JSONDecodeError:
        m = re.search(r'https?://[^\s"\'<>]+', raw)
        if m:
            result["url"] = m.group(0)
    return result


def list_tools(url, sid, token):
    """列出服务端可用工具。"""
    raw = mcp_call(url, sid, token, "tools/list", {})
    try:
        d = json.loads(raw)
        return [t["name"] for t in d.get("result", {}).get("tools", [])]
    except Exception:
        return []


# ──────────────────────────────────────────────
# 下载
# ──────────────────────────────────────────────

def get_desktop():
    """跨平台获取桌面路径。"""
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
            )
            try:
                value, _ = winreg.QueryValueEx(key, "Desktop")
                if value and Path(value).exists():
                    return Path(value)
            finally:
                winreg.CloseKey(key)
        except Exception:
            pass
        userprofile = os.environ.get("USERPROFILE")
        if userprofile and (Path(userprofile) / "Desktop").exists():
            return Path(userprofile) / "Desktop"
    home = Path.home()
    for name in ("Desktop", "桌面"):
        candidate = home / name
        if candidate.exists():
            return candidate
    return home


def download_file(url, dest=None, timeout=300):
    """下载 URL 到本地。"""
    req = Request(url, headers={"User-Agent": "mcp_media_client/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        if dest is None or not Path(dest).suffix:
            ctype = resp.headers.get("Content-Type", "").lower()
            if not dest:
                ext = "png" if "png" in ctype else "mp4" if "mp4" in ctype else "bin"
                dest = get_desktop() / f"mcp_generated_{int(time.time())}.{ext}"
            elif not Path(dest).suffix:
                ext = "png" if "png" in ctype else "mp4" if "mp4" in ctype else "bin"
                dest = str(dest) + f".{ext}"
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    return dest


# ──────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="通用 MCP 客户端：通过 TeleAgent 动态鉴权直连 mcp-media-hub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="tool", help="要调用的 MCP 工具")

    # text_to_image
    p_img = sub.add_parser("text_to_image", help="文生图")
    p_img.add_argument("--intent", default=None, help="中文意图（推荐主传）")
    p_img.add_argument("--prompt", default=None, help="英文提示词直传")
    p_img.add_argument("--auto-prompt", default="true", help="自动扩写(yes/no)")
    p_img.add_argument("--size", default="1024x1024", help="图片尺寸")
    p_img.add_argument("--style", default=None, help="风格")
    p_img.add_argument("--negative-prompt", default=None, help="负面提示词")

    # image_to_image
    p_i2i = sub.add_parser("image_to_image", help="图生图")
    p_i2i.add_argument("--image-url", required=True, help="源图 URL")
    p_i2i.add_argument("--intent", default=None)
    p_i2i.add_argument("--prompt", default=None)
    p_i2i.add_argument("--auto-prompt", default="true")
    p_i2i.add_argument("--size", default="1024x1024")
    p_i2i.add_argument("--style", default=None)

    # text_to_video
    p_vid = sub.add_parser("text_to_video", help="文生视频")
    p_vid.add_argument("--intent", default=None)
    p_vid.add_argument("--prompt", default=None)
    p_vid.add_argument("--auto-prompt", default="true")
    p_vid.add_argument("--duration", type=int, default=5, help="时长秒数")
    p_vid.add_argument("--size", default="1280x720")
    p_vid.add_argument("--long-video", default="false", help="长视频(yes/no)")
    p_vid.add_argument("--segments", type=int, default=1, help="长视频段数")

    # image_to_video
    p_i2v = sub.add_parser("image_to_video", help="图生视频")
    p_i2v.add_argument("--image-url", required=True, help="首帧图 URL")
    p_i2v.add_argument("--intent", default=None)
    p_i2v.add_argument("--prompt", default=None)
    p_i2v.add_argument("--duration", type=int, default=5)
    p_i2v.add_argument("--size", default="1280x720")

    # generate_prompt
    p_gp = sub.add_parser("generate_prompt", help="提示词扩写")
    p_gp.add_argument("--intent", required=True, help="原始中文想法")
    p_gp.add_argument("--modality", required=True, choices=["image", "video"])
    p_gp.add_argument("--style", default=None)

    # query_video
    p_qv = sub.add_parser("query_video", help="查询视频任务")
    p_qv.add_argument("--video-id", required=True)

    # list_models
    p_lm = sub.add_parser("list_models", help="列出可用模型")
    p_lm.add_argument("--capability", default=None,
                      choices=["text2image", "image2image", "text2video",
                               "image2video", "prompt"])

    # 公共参数
    for p in [p_img, p_i2i, p_vid, p_i2v, p_gp, p_qv, p_lm]:
        p.add_argument("--mcp-url", default=DEFAULT_MCP_URL, help="MCP 端点")
        p.add_argument("--out", default=None, help="下载到本地路径")
        p.add_argument("--no-download", action="store_true", help="不自动下载，只输出 URL")
        p.add_argument("--timeout", type=int, default=None, help="调用超时秒数")

    args = parser.parse_args()

    if not args.tool:
        parser.print_help()
        print(f"\n可用工具: {', '.join(TOOLS)}")
        sys.exit(1)

    url = args.mcp_url

    # ── 三步鉴权 ──
    print(f"[MCP] 连接端点: {url}")
    print("[MCP] 步骤1: 发送 x-from-teleAgent:true 握手请求...")
    try:
        sid, token = mcp_connect(url)
    except Exception as e:
        print(f"[MCP] 握手失败: {e}")
        sys.exit(1)

    if token:
        print(f"[MCP] 步骤2: 获得动态 token (前12位: {token[:12]}...)")
        print(f"[MCP] 步骤3: 后续请求使用 Authorization: Bearer <token>")
    if sid:
        print(f"[MCP] 会话 ID: {sid[:20]}...")
    print()

    # 确认工具可用
    tools = list_tools(url, sid, token)
    if args.tool not in tools:
        print(f"[MCP] 警告: 工具 '{args.tool}' 未在服务端工具列表中")
        print(f"[MCP] 可用工具: {tools}")
        print("[MCP] 继续尝试调用...")
    else:
        print(f"[MCP] 工具 '{args.tool}' 确认可用")

    # ── 构建参数 ──
    def to_bool(s):
        return s.lower() in ("true", "yes", "1")

    arguments = {}
    timeout = args.timeout or DEFAULT_TIMEOUT

    if args.tool == "text_to_image":
        arguments = {
            "intent": args.intent or "",
            "auto_prompt": to_bool(args.auto_prompt) if args.auto_prompt else True,
            "size": args.size,
        }
        if args.prompt:
            arguments["prompt"] = args.prompt
        if args.style:
            arguments["style"] = args.style
        if args.negative_prompt:
            arguments["negative_prompt"] = args.negative_prompt

    elif args.tool == "image_to_image":
        arguments = {
            "image_url": args.image_url,
            "auto_prompt": to_bool(args.auto_prompt) if args.auto_prompt else True,
            "size": args.size,
        }
        if args.intent:
            arguments["intent"] = args.intent
        if args.prompt:
            arguments["prompt"] = args.prompt
        if args.style:
            arguments["style"] = args.style

    elif args.tool == "text_to_video":
        arguments = {
            "intent": args.intent or "",
            "auto_prompt": to_bool(args.auto_prompt) if args.auto_prompt else True,
            "duration": args.duration,
            "size": args.size,
            "long_video": to_bool(args.long_video) if args.long_video else False,
            "segments": args.segments if to_bool(args.long_video) else 1,
        }
        if args.prompt:
            arguments["prompt"] = args.prompt
        if not timeout or timeout == DEFAULT_TIMEOUT:
            timeout = VIDEO_TIMEOUT

    elif args.tool == "image_to_video":
        arguments = {
            "image_url": args.image_url,
            "auto_prompt": True,
            "duration": args.duration,
            "size": args.size,
        }
        if args.intent:
            arguments["intent"] = args.intent
        if args.prompt:
            arguments["prompt"] = args.prompt
        if not timeout or timeout == DEFAULT_TIMEOUT:
            timeout = VIDEO_TIMEOUT

    elif args.tool == "generate_prompt":
        arguments = {"intent": args.intent, "modality": args.modality}
        if args.style:
            arguments["style"] = args.style

    elif args.tool == "query_video":
        arguments = {"video_id": args.video_id}

    elif args.tool == "list_models":
        arguments = {}
        if args.capability:
            arguments["capability"] = args.capability

    # ── 调用工具 ──
    print(f"\n[调用] {args.tool}")
    print(f"  参数: {json.dumps(arguments, ensure_ascii=False)}")
    print()

    result, raw = call_tool(url, sid, token, args.tool, arguments, timeout=timeout)

    if result["is_error"]:
        print(f"[错误] 调用返回错误标志")
        print(f"  原始响应: {raw[:1000]}")
        sys.exit(1)

    # 输出结果
    print("[结果]")
    if result["data"]:
        for k, v in result["data"].items():
            if k not in ("raw",):
                print(f"  {k}: {v}")
    elif result["text"]:
        print(f"  {result['text'][:2000]}")
    else:
        print(f"  原始: {raw[:1000]}")

    # 下载
    if result["url"] and not args.no_download:
        print(f"\n[下载] {result['url']}")
        try:
            dest = download_file(result["url"], dest=args.out)
            size_mb = dest.stat().st_size / 1048576
            if size_mb >= 1:
                size_str = f"{size_mb:.2f} MB"
            else:
                size_str = f"{dest.stat().st_size / 1024:.1f} KB"
            print(f"[完成] 文件已保存: {dest.resolve()}")
            print(f"       文件大小: {size_str}")
        except Exception as e:
            print(f"[下载失败] {e}")
            print(f"  URL: {result['url']}")
    elif result["url"] and args.no_download:
        print(f"\n[URL] {result['url']}")


if __name__ == "__main__":
    main()
