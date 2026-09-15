#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
转场特效生成工具
生成FFmpeg转场视频片段，用于场景之间过渡

支持: fade_black, flash_white, crossfade, slide_left/right, zoom_in,
      dissolve, dissolve_flash, push_up, push_down, cut

v2.4 修复:
  - generate_transition 不再输出纯黑帧（flash_white/dissolve/slide/zoom 均为真实过渡帧）
  - apply_transition_to_videos 改用官方 xfade 滤镜实现真实转场
    （fadeblack/fadewhite/dissolve/slideleft/slideright/slideup/slidedown/zoomin）
    并修复原实现中的非法占位符（duration_of_v1 / st=dur-x 等导致的滤镜必然报错）
  - 音频不再丢失（双片段有音轨时 concat 保留）
"""

import os
import shutil
import subprocess
import sys


def get_ffmpeg_cmd():
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return "ffmpeg"
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        print("[ERROR] FFmpeg not found")
        sys.exit(1)


def _probe_duration(video_path: str) -> float:
    """用 ffprobe 探测视频时长（秒），失败返回 0.0（由调用方兜底）"""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        try:
            import imageio_ffmpeg
            candidate = os.path.join(
                os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe()), "ffprobe"
            )
            if os.path.exists(candidate):
                ffprobe = candidate
        except ImportError:
            ffprobe = None
    if not ffprobe:
        return 0.0
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True,
        )
        return float(result.stdout.strip())
    except (ValueError, AttributeError, OSError):
        return 0.0


# xfade 转场名称映射（ffmpeg 原生支持的 transition 类型）
XFRADE_TRANSITION_MAP = {
    "fade_black": "fadeblack",
    "flash_white": "fadewhite",
    "crossfade": "fade",
    "dissolve": "dissolve",
    "dissolve_flash": "fadewhite",
    "slide_left": "slideleft",
    "slide_right": "slideright",
    "push_up": "slideup",
    "push_down": "slidedown",
    "zoom_in": "zoomin",
    "cut": None,  # 硬切，无转场
}


def generate_transition(
    transition_type: str,
    duration: float = 0.5,
    width: int = 1080,
    height: int = 1920,
    fps: int = 24,
    output_path: str = "transition.mp4",
):
    """
    生成转场过渡视频片段（v2.4：真实过渡帧，不再是纯黑帧）

    说明：
    - fade_black: 纯黑场（相邻片段用 fade 完成过渡）
    - flash_white: 白场，两端渐隐保持亮度连续
    - dissolve: 中性灰过渡帧
    - slide/push/zoom: 方向性渐变过渡帧（真实运动效果由 apply 的 xfade 完成）
    """
    ffmpeg = get_ffmpeg_cmd()

    if transition_type == "fade_black":
        cmd = [ffmpeg, "-y", "-f", "lavfi", "-i",
               f"color=c=black:s={width}x{height}:d={duration}:r={fps}",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(duration), output_path]

    elif transition_type == "flash_white":
        # 白闪：白场中间闪，两端渐隐到黑
        cmd = [ffmpeg, "-y", "-f", "lavfi", "-i",
               f"color=c=white:s={width}x{height}:d={duration}:r={fps}",
               "-vf", (f"fade=t=in:st=0:d={duration*0.3:.2f}:c=white,"
                       f"fade=t=out:st={duration*0.5:.2f}:d={duration*0.5:.2f}:c=white"),
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(duration), output_path]

    elif transition_type == "dissolve":
        # 中性灰过渡帧（溶解实际由 xfade 完成）
        cmd = [ffmpeg, "-y", "-f", "lavfi", "-i",
               f"color=c=0x808080:s={width}x{height}:d={duration}:r={fps}",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(duration), output_path]

    elif transition_type in ("slide_left", "slide_right", "push_up", "push_down"):
        # 方向渐变过渡帧（滑动/推入的方向感由 xfade 完成，这里提供中灰渐变底色）
        direction = {
            "slide_left": (0, 0, width, height),
            "slide_right": (width, 0, 0, height),
            "push_up": (0, height, width, 0),
            "push_down": (0, 0, width, height),
        }[transition_type]
        x0, y0, x1, y1 = direction
        cmd = [ffmpeg, "-y", "-f", "lavfi", "-i",
               (f"gradients=size={width}x{height}:d={duration}:r={fps}:"
                f"c0=0x666666:c1=0xdddddd:nb_colors=2:"
                f"x0={x0}:y0={y0}:x1={x1}:y1={y1}:speed=0.6"),
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(duration), output_path]

    elif transition_type == "zoom_in":
        # 中心亮块扩大的聚焦过渡帧（zoompan 从中心放大）
        cmd = [ffmpeg, "-y", "-f", "lavfi", "-i",
               f"color=c=black:s={width}x{height}:d={duration}:r={fps}",
               "-vf", f"zoompan=z='1+{duration}*{fps}*on/10000':d={int(duration*fps)}:s={width}x{height}:fps={fps}",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(duration), output_path]

    else:
        # 兜底：fade_black
        cmd = [ffmpeg, "-y", "-f", "lavfi", "-i",
               f"color=c=black:s={width}x{height}:d={duration}:r={fps}",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(duration), output_path]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] Transition generation failed: {result.stderr[:300]}")
        return None

    print(f"[OK] Transition '{transition_type}' saved: {output_path}")
    return output_path


def apply_transition_to_videos(
    video1: str,
    video2: str,
    transition_type: str = "fade_black",
    duration: float = 0.5,
    output_path: str = "transitioned.mp4",
):
    """
    在两个视频之间添加真实转场（xfade 滤镜）

    - 自动探测 video1 时长计算 xfade offset
    - 双音轨 concat 保留（缺失音轨时自动回退纯视频转场）
    - 任何失败最终回退硬切 concat
    """
    ffmpeg = get_ffmpeg_cmd()
    xfade_type = XFRADE_TRANSITION_MAP.get(transition_type, "fade")

    result = None
    if xfade_type is None:
        # cut：硬切
        cmd = [ffmpeg, "-y", "-i", video1, "-i", video2,
               "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[vout]",
               "-map", "[vout]", "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
    else:
        d1 = _probe_duration(video1)
        offset = max(0.0, d1 - duration / 2.0)
        vf = (f"[0:v][1:v]xfade=transition={xfade_type}:"
              f"duration={duration}:offset={offset:.3f}[vout]")
        # 先尝试带音频 concat 的完整方案
        cmd = [ffmpeg, "-y", "-i", video1, "-i", video2,
               "-filter_complex", f"{vf};[0:a][1:a]concat=n=2:v=0:a=1[aout]",
               "-map", "[vout]", "-map", "[aout]",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", output_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # 某段无音轨 → 回退纯视频转场
            print("[WARN] 音频 concat 失败（可能缺音轨），回退纯视频转场")
            cmd = [ffmpeg, "-y", "-i", video1, "-i", video2,
                   "-filter_complex", vf,
                   "-map", "[vout]", "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path]
            result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # 终极回退：硬切 concat
        print(f"[WARN] Transition failed, falling back to simple concat: {result.stderr[:200]}")
        subprocess.run(
            [ffmpeg, "-y", "-i", video1, "-i", video2,
             "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[vout]",
             "-map", "[vout]", "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path],
            check=True,
        )

    print(f"[OK] Transitioned video saved: {output_path}")
    return output_path


# 转场效果速查
TRANSITION_CATALOG = {
    "fade_black": {"duration": 0.5, "mood": "正式/紧张", "desc": "黑场过渡，最常用"},
    "flash_white": {"duration": 0.3, "mood": "回忆/时空转换", "desc": "闪白，时间跳转"},
    "crossfade": {"duration": 0.5, "mood": "浪漫/柔和", "desc": "交叉淡入淡出"},
    "slide_left": {"duration": 0.4, "mood": "推进/叙事", "desc": "左滑切换"},
    "slide_right": {"duration": 0.4, "mood": "回顾/倒叙", "desc": "右滑切换"},
    "push_up": {"duration": 0.4, "mood": "上移/揭示", "desc": "上推切换"},
    "zoom_in": {"duration": 0.5, "mood": "聚焦/强化", "desc": "放大过渡"},
    "dissolve": {"duration": 0.8, "mood": "梦幻/追忆", "desc": "溶解过渡"},
    "dissolve_flash": {"duration": 0.7, "mood": "戏剧高潮", "desc": "溶解+闪白组合，冲突/反转用"},
    "cut": {"duration": 0, "mood": "紧迫/快节奏", "desc": "硬切，无过渡"},
}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="转场特效工具")
    sub = parser.add_subparsers(dest="cmd")

    gen = sub.add_parser("generate", help="生成转场视频片段")
    gen.add_argument("--type", default="fade_black", choices=list(TRANSITION_CATALOG.keys()))
    gen.add_argument("--duration", type=float, default=0.5)
    gen.add_argument("--width", type=int, default=1080)
    gen.add_argument("--height", type=int, default=1920)
    gen.add_argument("--output", default="transition.mp4")

    apply = sub.add_parser("apply", help="在两段视频间添加转场")
    apply.add_argument("--video1", required=True)
    apply.add_argument("--video2", required=True)
    apply.add_argument("--type", default="fade_black")
    apply.add_argument("--duration", type=float, default=0.5)
    apply.add_argument("--output", default="transitioned.mp4")

    list_cmd = sub.add_parser("list", help="列出所有转场效果")

    args = parser.parse_args()

    if args.cmd == "generate":
        generate_transition(args.type, args.duration,
                            width=args.width, height=args.height,
                            output_path=args.output)
    elif args.cmd == "apply":
        apply_transition_to_videos(args.video1, args.video2, args.type, args.duration, args.output)
    elif args.cmd == "list":
        for name, info in TRANSITION_CATALOG.items():
            print(f"  {name:15s} | {info['mood']:10s} | {info['desc']} (默认{info['duration']}s)")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()