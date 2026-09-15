#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动画视频生成核心脚本
支持两种动画生成模式：
  1. Manim 代码驱动动画（运动/变换/文字动画/场景过渡）
  2. AI 图生视频帧 + FFmpeg 合成（通过图片序列生成动画）

用法:
  python animate_video.py manim --scene <scene_name> --input <manim_script.py> [--quality l/m/h/k] [--output <path>] [--preview]
  python animate_video.py frames --frames-dir <dir> --fps <fps> [--output <path>] [--audio <path>]
  python animate_video.py check_deps
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import json
from pathlib import Path


ALLOWED_PIP_PACKAGES = {"manim", "pycairo"}


def run_cmd(cmd, cwd=None, check=True, capture=False):
    """执行命令行命令（仅接受list形式，避免shell注入）"""
    if isinstance(cmd, str):
        raise TypeError("run_cmd() 仅接受list形式参数以避免shell注入，请使用 run_cmd([cmd, arg1, arg2, ...])")
    print(f"[CMD] {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=capture, text=True
    )
    if check and result.returncode != 0:
        print(f"[ERROR] Command failed with code {result.returncode}")
        if capture:
            print(result.stderr)
        sys.exit(1)
    return result


def check_deps():
    """检查并报告所有依赖项"""
    deps = {
        "python": sys.version.split()[0],
        "ffmpeg": None,
        "manim": None,
        "pycairo": None,
    }

    # Check ffmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        r = run_cmd([ffmpeg_path, "-version"], check=False, capture=True)
        if r.returncode == 0:
            deps["ffmpeg"] = r.stdout.split("\n")[0].strip()
    else:
        # Try imageio-ffmpeg
        try:
            import imageio_ffmpeg
            deps["ffmpeg"] = f"imageio-ffmpeg {imageio_ffmpeg.get_ffmpeg_version()}"
        except ImportError:
            pass

    # Check manim
    try:
        import manim
        deps["manim"] = manim.__version__
    except ImportError:
        pass

    # Check pycairo
    try:
        import cairo
        deps["pycairo"] = cairo.version
    except ImportError:
        pass

    print(json.dumps(deps, indent=2, ensure_ascii=False))

    missing = [k for k, v in deps.items() if v is None and k != "python"]
    if missing:
        print(f"\n[WARN] Missing dependencies: {', '.join(missing)}")
        print("Run: pip install manim pycairo")
        if "ffmpeg" in missing:
            print("Or install FFmpeg and add to PATH")
    else:
        print("\n[OK] All dependencies satisfied")

    return len(missing) == 0


def get_ffmpeg_cmd():
    """获取可用的 FFmpeg 命令路径"""
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return "ffmpeg"
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        print("[ERROR] FFmpeg not found. Install it or: pip install imageio-ffmpeg")
        sys.exit(1)


def render_manim(input_script, scene_name, quality, output_path, preview=False):
    """使用 Manim 渲染动画视频

    Args:
        preview: 是否在渲染后打开播放器预览。默认 False，避免无 GUI 环境卡死
                 （旧版 quality_map 自带 -p 预览参数，无显示环境会阻塞）
    """
    try:
        import manim
    except ImportError:
        print("[INFO] Manim not installed, installing...")
        safe = [p for p in ["manim", "pycairo"] if p in ALLOWED_PIP_PACKAGES]
        run_cmd([sys.executable, "-m", "pip", "install"] + safe)

    # 注意：默认不带 -p（preview）参数，无 GUI 环境会打开播放器卡死
    quality_map = {
        "l": "-ql",   # 480p 15fps
        "m": "-qm",   # 720p 30fps
        "h": "-qh",   # 1080p 60fps
        "k": "-qk",   # 4K 60fps
    }
    q_flag = quality_map.get(quality, "-ql")

    cmd = [sys.executable, "-m", "manim", q_flag, input_script, scene_name]
    if preview:
        cmd.insert(3, "-p")  # 用户显式要求时才打开预览
    print(f"[INFO] Rendering Manim scene: {scene_name}")
    run_cmd(cmd)

    # Find the output file
    input_dir = os.path.dirname(os.path.abspath(input_script))
    media_dir = os.path.join(input_dir, "media")

    # Search for the rendered video
    found = None
    for root, dirs, files in os.walk(media_dir):
        for f in files:
            if f.endswith(".mp4") and scene_name in f:
                found = os.path.join(root, f)
                break
        if found:
            break

    if not found:
        print(f"[ERROR] Could not find rendered video for scene '{scene_name}'")
        sys.exit(1)

    if output_path:
        shutil.copy2(found, output_path)
        print(f"[OK] Video saved to: {output_path}")
    else:
        print(f"[OK] Video saved to: {found}")

    return found


def frames_to_video(frames_dir, fps, output_path, audio_path=None):
    """将图片序列合成视频"""
    ffmpeg_cmd = get_ffmpeg_cmd()

    # Check frames directory
    frames_path = Path(frames_dir)
    if not frames_path.exists():
        print(f"[ERROR] Frames directory not found: {frames_dir}")
        sys.exit(1)

    # Find frame files（去重：frame_*.png 也被 *.png 匹配，避免帧数重复）
    frame_files = sorted(set(frames_path.glob("*.png")))
    if not frame_files:
        print(f"[ERROR] No PNG frames found in: {frames_dir}")
        sys.exit(1)

    print(f"[INFO] Found {len(frame_files)} frames")

    if not output_path:
        output_path = str(frames_path.parent / "animation_output.mp4")

    # 只有全部文件都符合 frame_%04d.png 命名模式时才可直接用序列通配符
    all_sequential = all(
        re.fullmatch(r"frame_\d+\.png", f.name) for f in frame_files
    )
    if all_sequential:
        input_pattern = str(frames_path / "frame_%04d.png")
    else:
        # 命名不规整（含无前缀/非连续编号）时，统一复制到临时目录重命名，
        # 保证帧序正确，避免 glob 顺序依赖
        import tempfile
        tmp_dir = tempfile.mkdtemp(prefix="anim_frames_")
        for i, f in enumerate(frame_files):
            shutil.copy2(str(f), os.path.join(tmp_dir, f"frame_{i:04d}.png"))
        input_pattern = os.path.join(tmp_dir, "frame_%04d.png")

    # Build FFmpeg command
    if audio_path and os.path.exists(audio_path):
        cmd = [ffmpeg_cmd, "-y", "-framerate", str(fps), "-i", input_pattern,
               "-i", audio_path, "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-shortest", output_path]
    else:
        cmd = [ffmpeg_cmd, "-y", "-framerate", str(fps), "-i", input_pattern,
               "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path]

    print(f"[INFO] Encoding video at {fps} fps...")
    run_cmd(cmd)

    # Cleanup temp dir if used
    if not all_sequential and 'tmp_dir' in locals():
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"[OK] Video saved to: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="动画视频生成工具")
    subparsers = parser.add_subparsers(dest="mode", help="运行模式")

    # Manim mode
    manim_parser = subparsers.add_parser("manim", help="Manim 代码驱动动画")
    manim_parser.add_argument("--input", required=True, help="Manim 脚本路径")
    manim_parser.add_argument("--scene", required=True, help="场景类名")
    manim_parser.add_argument("--quality", default="m", choices=["l", "m", "h", "k"])
    manim_parser.add_argument("--output", default=None, help="输出视频路径")
    manim_parser.add_argument("--preview", action="store_true", help="渲染后打开播放器预览（仅在有 GUI 环境时使用）")

    # Frames mode
    frames_parser = subparsers.add_parser("frames", help="图片序列合成视频")
    frames_parser.add_argument("--frames-dir", required=True, help="帧图片目录")
    frames_parser.add_argument("--fps", type=int, default=24, help="帧率")
    frames_parser.add_argument("--output", default=None, help="输出视频路径")
    frames_parser.add_argument("--audio", default=None, help="背景音频路径")

    # Check deps
    subparsers.add_parser("check_deps", help="检查依赖")

    args = parser.parse_args()

    if args.mode == "manim":
        render_manim(args.input, args.scene, args.quality, args.output, args.preview)
    elif args.mode == "frames":
        frames_to_video(args.frames_dir, args.fps, args.output, args.audio)
    elif args.mode == "check_deps":
        check_deps()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()