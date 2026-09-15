#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境检查：确认生成短视频所需的运行时与依赖是否就绪。
用法：
    python check_env.py [--install] [--json]
"""
import argparse
import json

from common import ffmpeg_bin, ffprobe_bin, run


def check_py_module(name: str):
    try:
        __import__(name)
        return True, ""
    except ImportError as e:
        return False, str(e)


def check_edge_tts():
    ok, err = check_py_module("edge_tts")
    if ok:
        return True, ""
    # 尝试联网确认在线 TTS 可用性不需要在此做，交给 tts.py 运行时判断
    return False, err


def main():
    ap = argparse.ArgumentParser(description="检查短剧生成环境")
    ap.add_argument("--install", action="store_true", help="自动安装缺失的 Python 依赖")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args()

    results = {}

    # Python 依赖
    deps = [
        ("edge_tts", "在线配音（edge-tts）"),
        ("PIL", "图像处理（Pillow）"),
        ("numpy", "数值计算"),
        ("imageio_ffmpeg", "内置 ffmpeg（imageio-ffmpeg）"),
    ]
    missing = []
    for mod, desc in deps:
        ok, err = check_py_module(mod)
        results[f"python:{mod}"] = {"ok": ok, "desc": desc, "detail": err}
        if not ok:
            missing.append(mod)

    # ffmpeg
    ff = ffmpeg_bin()
    results["ffmpeg"] = {"ok": bool(ff), "desc": "视频合成引擎", "detail": ff or "未找到"}
    fp = ffprobe_bin()
    results["ffprobe"] = {"ok": bool(fp), "desc": "媒体信息工具（可选）", "detail": fp or "未找到（将用 ffmpeg -i 兜底）"}

    # SAPI TTS（Windows 兜底配音）
    try:
        import win32com.client  # noqa
        sapi = True
    except Exception:
        sapi = False
    results["sapi_tts"] = {"ok": sapi, "desc": "Windows 本地配音兜底（可选）", "detail": "" if sapi else "未安装 pywin32，仅影响离线兜底"}

    if args.install:
        mods = [m for m in missing if m not in ("win32com",)]
        if mods:
            print("正在安装缺失依赖:", ", ".join(mods))
            r = run(["python", "-m", "pip", "install", "--quiet"] + mods)
            print("安装完成" if r.returncode == 0 else f"安装失败 rc={r.returncode}")
            for m in list(mods):
                ok, _ = check_py_module(m)
                results[f"python:{m}"]["ok"] = ok
                if ok:
                    missing.remove(m)

    all_ok = results["ffmpeg"]["ok"] and not any(not v["ok"] for k, v in results.items() if k.startswith("python:")) and (results["ffprobe"]["ok"] or True)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("==== 短剧生成环境检查 ====")
        for k, v in results.items():
            mark = "✓" if v["ok"] else "✗"
            print(f"  {mark} {v['desc']:<24} {v['detail']}")
        print("===========================")
        if ff:
            print("环境就绪，可以开始生成短剧。")
        else:
            print("缺少 ffmpeg。可用 --install 安装依赖，或手动安装 ffmpeg 并设置 FFMPEG_BIN。")

    return 0 if (ff and not missing) else 1


if __name__ == "__main__":
    raise SystemExit(main())