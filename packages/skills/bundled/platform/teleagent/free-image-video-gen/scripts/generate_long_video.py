#!/usr/bin/env python3
"""
长视频分段生成与合并脚本

将长视频需求拆分为多个5秒分镜，逐段调用 media-hub MCP 服务生成，
然后使用 ffmpeg 合并为一个完整的长视频文件。

用法：
  # 方式一：通过分镜JSON文件
  python generate_long_video.py --storyboard storyboard.json --output output.mp4

  # 方式二：命令行直接传入分镜
  python generate_long_video.py \
    --segments 3 \
    --prompt-1 "镜头1描述" \
    --prompt-2 "镜头2描述" \
    --prompt-3 "镜头3描述" \
    --aspect-ratio 16:9 \
    --output output.mp4

  # 方式三：统一提示词，自动拆分
  python generate_long_video.py \
    --unified-prompt "一段完整的视频描述..." \
    --segments 4 \
    --output output.mp4

  # 可选：覆盖 MCP 服务地址
  python generate_long_video.py --storyboard sb.json --mcp-url <url>

依赖：
  - mcp (MCP Python SDK)
  - requests
  - imageio-ffmpeg (自动获取 ffmpeg 二进制)
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
import subprocess
from pathlib import Path

import requests

# MCP 客户端
try:
    from mcp.client.streamable_http import streamable_http_client
    from mcp.client.session import ClientSession
    # 统一命名为 streamablehttp_client（代码中使用）
    streamablehttp_client = streamable_http_client
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

# ffmpeg 路径
try:
    from imageio_ffmpeg import get_ffmpeg_exe
    FFMPEG_PATH = get_ffmpeg_exe()
except Exception:
    FFMPEG_PATH = None

# 默认 MCP 服务配置（开箱即用）
DEFAULT_MCP_URL = "https://mcp.bbdict.com/hub"
MAX_RETRIES = 6
RETRY_WAIT = 35  # seconds
DEFAULT_NEGATIVE = "blurry, distorted, flickering, low quality, watermark, text artifacts, ugly, deformed"


def _get_config_dir() -> Path:
    """获取 TeleAgent 配置目录"""
    env = os.environ.get("TELEAGENT_CONFIG_DIR")
    if env:
        return Path(env)
    if sys.platform == "win32":
        return Path(os.environ.get("USERPROFILE", "")) / ".config" / "TeleAgent"
    return Path.home() / ".config" / "TeleAgent"


def _read_mcp_config() -> dict:
    """从 .mcp.json 读取 media-hub 的配置

    返回:
        {"url": "...", "trace": "..."}  # trace 可能为 None（静态密文，fallback 用）
    """
    config_dir = _get_config_dir()
    mcp_json = config_dir / ".mcp.json"

    if not mcp_json.exists():
        return {}

    try:
        with open(mcp_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        servers = data.get("mcpServers", {})
        hub = servers.get("media-hub", {})
        if isinstance(hub, dict):
            return {
                "url": hub.get("url", ""),
                "trace": (hub.get("headers", {}) or {}).get("X-Request-Trace"),
            }
    except Exception:
        pass

    return {}


def _get_trace_from_config() -> str | None:
    """从 .mcp.json 读取 media-hub 的 X-Request-Trace 静态密文。

    鉴权凭证由 get_auth 工具获取后写入 .mcp.json，此处运行时读取。
    返回 None 表示未配置（首次使用需先调 get_auth 获取）。
    """
    config = _read_mcp_config()
    return config.get("trace")


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def get_desktop() -> Path:
    """跨平台获取用户桌面路径"""
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
        if userprofile:
            desktop = Path(userprofile) / "Desktop"
            if desktop.exists():
                return desktop
    home = Path.home()
    for name in ("Desktop", "桌面"):
        candidate = home / name
        if candidate.exists():
            return candidate
    return home


def parse_mcp_result(result):
    """解析 MCP 工具调用结果，提取 video_url, raw_text"""
    video_url = None
    raw_text = ""

    for content in result.content:
        if hasattr(content, 'text'):
            raw_text += content.text
            try:
                data = json.loads(content.text)
                if isinstance(data, dict):
                    for k in ("url", "video_url", "download_url"):
                        if not video_url:
                            video_url = data.get(k)
                    if not video_url and isinstance(data.get("data"), dict):
                        inner = data["data"]
                        for k in ("url", "video_url", "download_url"):
                            if not video_url:
                                video_url = inner.get(k)
            except json.JSONDecodeError:
                pass

    if not video_url:
        m = re.search(r'https?://[^\s"\'<>]+', raw_text)
        if m:
            video_url = m.group(0)

    return video_url, raw_text


def download_file(url: str, dest: Path, timeout: int = 180) -> bool:
    """下载文件到本地"""
    try:
        resp = requests.get(url, stream=True, timeout=timeout)
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        return dest.exists() and dest.stat().st_size > 0
    except Exception as e:
        print(f"    下载失败: {e}")
        return False


def merge_videos(segment_paths: list, output_path: Path) -> bool:
    """使用 ffmpeg 合并多个视频片段"""
    if not segment_paths:
        print("  没有可合并的视频片段")
        return False

    if len(segment_paths) == 1:
        import shutil
        shutil.copy2(segment_paths[0], output_path)
        return True

    if not FFMPEG_PATH:
        print("  错误: ffmpeg 不可用，请安装 imageio-ffmpeg: pip install imageio-ffmpeg")
        return False

    list_file = output_path.parent / "concat_list.txt"
    with open(list_file, 'w', encoding='utf-8') as f:
        for seg in segment_paths:
            safe_path = str(seg).replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")

    print(f"  ffmpeg 合并 {len(segment_paths)} 个片段...")

    cmd = [
        FFMPEG_PATH, '-y',
        '-f', 'concat', '-safe', '0',
        '-i', str(list_file),
        '-c', 'copy',
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        print(f"  直接合并失败，尝试重编码合并...")
        cmd_reencode = [
            FFMPEG_PATH, '-y',
            '-f', 'concat', '-safe', '0',
            '-i', str(list_file),
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
            '-pix_fmt', 'yuv420p', '-an',
            str(output_path)
        ]
        result = subprocess.run(cmd_reencode, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"  ffmpeg 合并失败: {result.stderr[:500]}")
            list_file.unlink(missing_ok=True)
            return False

    list_file.unlink(missing_ok=True)
    return output_path.exists() and output_path.stat().st_size > 0


# ──────────────────────────────────────────────
# MCP 调用
# ──────────────────────────────────────────────

async def generate_single_segment(session, prompt, aspect_ratio, duration, seed):
    """生成单个视频片段（通过 media-hub generate_video，同步返回）"""
    call_args = {
        "provider": "auto",
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "seed": seed if seed is not None else -1,
    }
    result = await session.call_tool("generate_video", call_args)
    video_url, raw_text = parse_mcp_result(result)
    return video_url, raw_text


async def generate_long_video(storyboard: dict, output_path: Path,
                              mcp_url: str = None, mcp_trace: str = None):
    """长视频分段生成与合并主流程"""
    segments = storyboard.get("segments", [])
    aspect_ratio = storyboard.get("aspect_ratio", storyboard.get("size", "16:9"))

    if not segments:
        print("错误: 分镜列表为空")
        return None

    total_duration = sum(s.get("duration", 5) for s in segments)
    print(f"\n{'='*60}")
    print(f"长视频分段生成")
    print(f"{'='*60}")
    print(f"  总段数: {len(segments)}")
    print(f"  预计总时长: {total_duration} 秒")
    print(f"  宽高比: {aspect_ratio}")
    print(f"  输出路径: {output_path}")
    print()

    if not HAS_MCP:
        print("错误: MCP SDK 不可用，请安装: pip install mcp")
        return None

    # 确定 MCP 服务地址和认证（优先命令行参数 > .mcp.json > 内置默认值）
    mcp_config = _read_mcp_config()
    url = mcp_url or mcp_config.get("url") or DEFAULT_MCP_URL
    # trace 仅从 .mcp.json 读取（由 get_auth 工具写入），或命令行显式传入
    trace = mcp_trace or _get_trace_from_config()

    # 临时目录存放各段视频
    temp_dir = output_path.parent / f".temp_segments_{int(time.time())}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    segment_paths = []
    failed_segments = []

    for attempt in range(1, MAX_RETRIES + 1):
        all_success = True

        headers_dict = {}
        if trace:
            headers_dict["X-Request-Trace"] = trace

        try:
            # 新版 MCP SDK (2.0) 需要通过 httpx2.AsyncClient 传递 headers
            try:
                import httpx2
                http_client = httpx2.AsyncClient(headers=headers_dict)
                async with streamablehttp_client(url, http_client=http_client) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        tool_names = [t.name for t in tools.tools]

                        if "generate_video" not in tool_names:
                            print(f"错误: generate_video 工具不可用")
                            print(f"  可用工具: {tool_names}")
                            return None

                        print(f"  使用 media-hub generate_video (provider=auto)")

                        for idx, seg in enumerate(segments):
                            seg_prompt = seg.get("prompt", "")
                            seg_duration = seg.get("duration", 5)
                            seg_seed = seg.get("seed", -1)

                            if idx < len(segment_paths):
                                print(f"\n  [段 {idx+1}/{len(segments)}] 已完成，跳过")
                                continue

                            print(f"\n  [段 {idx+1}/{len(segments)}] 生成中...")
                            print(f"    提示词: {seg_prompt[:80]}...")
                            print(f"    时长: {seg_duration}s")

                            try:
                                video_url, raw_text = await generate_single_segment(
                                    session, seg_prompt, aspect_ratio,
                                    seg_duration, seg_seed
                                )

                                if video_url:
                                    seg_path = temp_dir / f"segment_{idx:03d}.mp4"
                                    print(f"    下载片段到: {seg_path}")
                                    if download_file(video_url, seg_path):
                                        segment_paths.append(seg_path)
                                        size_mb = seg_path.stat().st_size / 1048576
                                        print(f"    完成! 文件大小: {size_mb:.2f} MB")
                                    else:
                                        print(f"    下载失败!")
                                        failed_segments.append(idx)
                                        all_success = False
                                else:
                                    print(f"    生成失败: {raw_text[:200]}")
                                    if "queue_full" in raw_text or "503" in raw_text:
                                        all_success = False
                                    else:
                                        failed_segments.append(idx)

                            except Exception as e:
                                print(f"    异常: {e}")
                                failed_segments.append(idx)
                                all_success = False

                            if idx < len(segments) - 1:
                                print(f"    等待5秒后生成下一段...")
                                await asyncio.sleep(5)

            except ImportError:
                # httpx2 不可用，使用默认客户端
                async with streamablehttp_client(url) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        tool_names = [t.name for t in tools.tools]

                        if "generate_video" not in tool_names:
                            print(f"错误: generate_video 工具不可用")
                            print(f"  可用工具: {tool_names}")
                            return None

                        print(f"  使用 media-hub generate_video (provider=auto, 无httpx2)")

                        for idx, seg in enumerate(segments):
                            seg_prompt = seg.get("prompt", "")
                            seg_duration = seg.get("duration", 5)
                            seg_seed = seg.get("seed", -1)

                            if idx < len(segment_paths):
                                print(f"\n  [段 {idx+1}/{len(segments)}] 已完成，跳过")
                                continue

                            print(f"\n  [段 {idx+1}/{len(segments)}] 生成中...")
                            print(f"    提示词: {seg_prompt[:80]}...")
                            print(f"    时长: {seg_duration}s")

                            try:
                                video_url, raw_text = await generate_single_segment(
                                    session, seg_prompt, aspect_ratio,
                                    seg_duration, seg_seed
                                )

                                if video_url:
                                    seg_path = temp_dir / f"segment_{idx:03d}.mp4"
                                    print(f"    下载片段到: {seg_path}")
                                    if download_file(video_url, seg_path):
                                        segment_paths.append(seg_path)
                                        size_mb = seg_path.stat().st_size / 1048576
                                        print(f"    完成! 文件大小: {size_mb:.2f} MB")
                                    else:
                                        print(f"    下载失败!")
                                        failed_segments.append(idx)
                                        all_success = False
                                else:
                                    print(f"    生成失败: {raw_text[:200]}")
                                    if "queue_full" in raw_text or "503" in raw_text:
                                        all_success = False
                                    else:
                                        failed_segments.append(idx)

                            except Exception as e:
                                print(f"    异常: {e}")
                                failed_segments.append(idx)
                                all_success = False

                            if idx < len(segments) - 1:
                                print(f"    等待5秒后生成下一段...")
                                await asyncio.sleep(5)

        except Exception as conn_err:
            print(f"  连接失败: {conn_err}")
            all_success = False

        if len(segment_paths) == len(segments):
            break

        if not all_success and attempt < MAX_RETRIES:
            retry_msg = f"\n  第 {attempt} 轮未全部完成，{len(segment_paths)}/{len(segments)} 段成功"
            if failed_segments:
                retry_msg += f"，失败段: {[f+1 for f in failed_segments]}"
            retry_msg += f"，等待 {RETRY_WAIT} 秒后重试..."
            print(retry_msg)
            await asyncio.sleep(RETRY_WAIT)
            failed_segments = []

    print(f"\n{'='*60}")
    print(f"生成阶段完成: {len(segment_paths)}/{len(segments)} 段成功")

    if not segment_paths:
        print("错误: 没有成功生成任何片段")
        return None

    print(f"\n开始合并 {len(segment_paths)} 个视频片段...")
    if merge_videos(segment_paths, output_path):
        file_size = output_path.stat().st_size / 1048576
        print(f"\n合并成功!")
        print(f"  文件路径: {output_path}")
        print(f"  文件大小: {file_size:.2f} MB")
        print(f"  片段数量: {len(segment_paths)}")
        if len(segment_paths) < len(segments):
            print(f"  警告: 有 {len(segments) - len(segment_paths)} 段未生成，最终视频可能不完整")
        return output_path
    else:
        print("合并失败!")
        print(f"  分段文件保留在: {temp_dir}")
        return None


# ──────────────────────────────────────────────
# 命令行入口
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="长视频分段生成与合并",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 通过分镜JSON文件
  python generate_long_video.py --storyboard storyboard.json --output output.mp4

  # 命令行直接传入
  python generate_long_video.py --segments 3 \\
    --prompt-1 "镜头1描述" --prompt-2 "镜头2描述" --prompt-3 "镜头3描述" \\
    --output output.mp4

  # 统一提示词自动拆分
  python generate_long_video.py --unified-prompt "完整视频描述" --segments 4 --output output.mp4
        """
    )
    parser.add_argument("--storyboard", help="分镜JSON文件路径")
    parser.add_argument("--segments", type=int, help="分段数量")
    parser.add_argument("--unified-prompt", help="统一提示词，自动按分句拆分")
    parser.add_argument("--aspect-ratio", default="16:9",
                        help="视频宽高比（如 16:9, 9:16, 1:1），默认 16:9")
    parser.add_argument("--output", help="输出文件路径（默认桌面）")
    parser.add_argument("--negative-prompt", default=DEFAULT_NEGATIVE, help="负面提示词")
    parser.add_argument("--mcp-url", default=None,
                        help="覆盖 MCP 服务地址（默认从 .mcp.json 读取）")
    parser.add_argument("--mcp-trace", default=None,
                        help="覆盖 MCP 鉴权 Trace（由 get_auth 获取，默认从 .mcp.json 读取）")

    if '--help' in sys.argv or '-h' in sys.argv:
        parser.print_help()
        sys.exit(0)

    args, remaining = parser.parse_known_args()
    prompts = {}
    i = 0
    while i < len(remaining):
        token = remaining[i]
        if token.startswith("--prompt-"):
            try:
                idx = int(token.replace("--prompt-", ""))
                if i + 1 < len(remaining):
                    prompts[idx] = remaining[i + 1]
                    i += 2
                    continue
            except ValueError:
                pass
        i += 1

    if args.storyboard:
        with open(args.storyboard, 'r', encoding='utf-8') as f:
            storyboard = json.load(f)
    elif prompts:
        seg_list = []
        for idx in sorted(prompts.keys()):
            seg_list.append({
                "prompt": prompts[idx],
                "duration": 5,
                "negative_prompt": args.negative_prompt,
                "seed": -1,
            })
        storyboard = {"aspect_ratio": args.aspect_ratio, "segments": seg_list}
    elif args.unified_prompt and args.segments:
        parts = re.split(r'[。；;\n]', args.unified_prompt)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) < args.segments:
            while len(parts) < args.segments:
                parts.append(parts[-1] if parts else "")
        seg_list = []
        for i in range(args.segments):
            seg_list.append({
                "prompt": parts[i] if i < len(parts) else parts[-1],
                "duration": 5,
                "negative_prompt": args.negative_prompt,
                "seed": -1,
            })
        storyboard = {"aspect_ratio": args.aspect_ratio, "segments": seg_list}
    else:
        parser.print_help()
        print("\n错误: 需要提供 --storyboard, --prompt-N 或 --unified-prompt+--segments")
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = get_desktop() / f"long_video_{int(time.time())}.mp4"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = asyncio.run(generate_long_video(
        storyboard, output_path,
        mcp_url=args.mcp_url,
        mcp_trace=args.mcp_trace,
    ))
    if result:
        print(f"\n{'='*60}")
        print(f"长视频生成完成!")
        print(f"  文件: {result}")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print(f"长视频生成失败")
        print(f"{'='*60}")
        sys.exit(1)


if __name__ == "__main__":
    main()
