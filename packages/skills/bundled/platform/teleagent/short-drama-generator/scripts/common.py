#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公共配置与工具模块：所有 short-drama-generator 脚本共享。
"""
import json
import os
import re
import subprocess
from pathlib import Path

# ---------------- 工作目录规则 ----------------
# 所有渲染中间产物（分镜、音频、临时视频）输出到 输出目录/.work/ 下
# 最终交付（成片 mp4、封面、发布包）输出到 输出目录 根下
WORK_SUB = ".work"


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_output_dir(cli_out: str | None) -> Path:
    """输出目录：CLI 参数优先，否则为当前工作目录下 short-drama-output"""
    if cli_out:
        return Path(cli_out).resolve()
    return Path.cwd() / "short-drama-output"


def work_dir(out_dir: Path) -> Path:
    w = out_dir / WORK_SUB
    w.mkdir(parents=True, exist_ok=True)
    return w


def ensure_out(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def json_dump(obj, path: Path):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def json_load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(cmd, cwd=None, quiet=False):
    """运行外部命令，返回 subprocess.CompletedProcess"""
    kwargs = {"cwd": cwd}
    if quiet:
        kwargs.update({"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL})
    else:
        kwargs.update({
            "capture_output": True, "text": True,
            "encoding": "utf-8", "errors": "replace",
        })
    return subprocess.run(cmd, **kwargs)


def _ff_in_path(name: str) -> bool:
    # Windows 下 CreateProcess 找不到文件会抛异常，先判断 PATH
    for d in os.environ.get("PATH", "").split(os.pathsep):
        cand = Path(d) / name
        if cand.exists():
            return True
        cand_exe = Path(d) / (name + ".exe")
        if cand_exe.exists():
            return True
    return False


def _ffmpeg(name: str) -> bool:
    return _ff_in_path(name)


def ffmpeg_bin() -> str | None:
    """定位 ffmpeg：环境变量 FFMPEG_BIN > imageio-ffmpeg 自带 > 系统 PATH"""
    env = os.environ.get("FFMPEG_BIN")
    if env and Path(env).exists():
        return env
    try:
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).exists():
            return exe
    except Exception:
        pass
    if _ffmpeg("ffmpeg"):
        return "ffmpeg"
    return None


def ffprobe_bin() -> str | None:
    """定位 ffprobe（可选工具，找不到时用 ffmpeg -i 兜底）"""
    if _ffmpeg("ffprobe"):
        return "ffprobe"
    return None


def find_ffmpeg() -> str:
    b = ffmpeg_bin()
    if b:
        return b
    raise RuntimeError("找不到 ffmpeg，请安装 ffmpeg 或设置环境变量 FFMPEG_BIN")


def media_duration(path) -> float:
    """获取媒体时长（秒）；ffprobe 优先，ffmpeg -i 兜底"""
    p = Path(path)
    if not p.exists():
        return 0.0
    fp = ffprobe_bin()
    if fp:
        r = run([fp, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(p)])
        if r.returncode == 0 and r.stdout.strip():
            try:
                return float(r.stdout.strip().splitlines()[0])
            except ValueError:
                pass
    ff = ffmpeg_bin()
    if ff:
        r = run([ff, "-i", str(p)])
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", r.stderr or "")
        if m:
            h, mi, s = m.groups()
            return int(h) * 3600 + int(mi) * 60 + float(s)
    return 0.0