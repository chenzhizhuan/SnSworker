#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配音合成：为 shots.json 中每个分镜生成配音音频，写入 .work/audio/。
引擎优先级：
  1. edge-tts（微软神经语音，在线，默认，音色自然）
  2. SAPI（Windows 本地语音，离线兜底）

用法：
  python tts.py [--shots shots.json] [--out 输出目录] [--engine edge|sapi|auto] [--force]
"""
import argparse
import asyncio
import sys
from pathlib import Path

from common import ensure_out, json_dump, json_load, media_duration, run, work_dir

AUDIO_SUB = "audio"


def _edge_available() -> bool:
    try:
        import edge_tts  # noqa

        return True
    except Exception:
        return False


def _sapi_available() -> bool:
    try:
        import win32com.client  # noqa

        return True
    except Exception:
        return False


def normalize_voice(voice: str) -> str:
    v = (voice or "").strip()
    if not v:
        return "zh-CN-XiaoxiaoNeural"
    if not v.startswith("zh-"):
        v = f"zh-CN-{v}"
    if not v.endswith("Neural"):
        v += "Neural"
    return v


async def _edge_synth(text: str, voice: str, out_mp3: Path):
    import edge_tts

    c = edge_tts.Communicate(text, normalize_voice(voice))
    await c.save(str(out_mp3))


def _sapi_synth(text: str, out_wav: Path) -> bool:
    """SAPI 生成 wav（需要 ffmpeg 再转 mp3）"""
    try:
        import win32com.client

        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        # 挑选中文语音
        voices = speaker.GetVoices()
        target = None
        for v in voices:
            desc = v.GetDescription()
            if "中文" in desc or "Chinese" in desc:
                target = v
                break
        if target is None and voices.Count:
            target = voices.Item(0)
        if target is not None:
            speaker.Voice = target
        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        stream.Format.Type = 2  # SAPI 44kHz 单声道
        stream.Open(str(out_wav), 3)  # SSFMCreateForWrite
        speaker.AudioOutputStream = stream
        speaker.Speak(text)
        stream.Close()
        return out_wav.exists() and out_wav.stat().st_size > 0
    except Exception as e:
        print(f"  SAPI 合成失败: {e}", file=sys.stderr)
        return False


def synth_shot(text, voice, out_mp3: Path, engine: str, force: bool):
    """生成单个分镜音频，返回是否成功（edge 引擎自动重试 3 次）"""
    if out_mp3.exists() and not force:
        return True
    try:
        if engine in ("edge", "auto") and _edge_available():
            for attempt in range(1, 4):
                try:
                    asyncio.run(_edge_synth(text, voice, out_mp3))
                except Exception as e:
                    print(f"  edge 第{attempt}次尝试失败: {e}", file=sys.stderr)
                    continue
                if out_mp3.exists() and out_mp3.stat().st_size > 0:
                    return True
                if out_mp3.exists():
                    out_mp3.unlink()
            # 三次失败后回退 SAPI
            if engine == "auto" and _sapi_available():
                wav = out_mp3.with_suffix(".wav")
                if _sapi_synth(text, wav):
                    from common import find_ffmpeg

                    r = run([find_ffmpeg(), "-y", "-i", str(wav), "-b:a", "128k", str(out_mp3)])
                    wav.unlink(missing_ok=True)
                    if r.returncode == 0 and out_mp3.exists() and out_mp3.stat().st_size > 0:
                        return True
            return False
        if engine in ("sapi", "auto") and _sapi_available():
            wav = out_mp3.with_suffix(".wav")
            if _sapi_synth(text, wav):
                from common import find_ffmpeg

                r = run([find_ffmpeg(), "-y", "-i", str(wav), "-b:a", "128k", str(out_mp3)])
                wav.unlink(missing_ok=True)
                if r.returncode == 0 and out_mp3.exists() and out_mp3.stat().st_size > 0:
                    return True
        return False
    except Exception as e:
        print(f"  shot 配音异常: {e}", file=sys.stderr)
        return False


def main():
    ap = argparse.ArgumentParser(description="分镜配音")
    ap.add_argument("--shots", help="shots.json 路径（默认 输出目录/.work/shots.json）")
    ap.add_argument("--out", help="输出目录（默认 ./short-drama-output）")
    ap.add_argument("--engine", choices=["auto", "edge", "sapi"], default="auto",
                    help="edge=在线微软语音；sapi=Windows 本地语音；auto=自动优先 edge")
    ap.add_argument("--force", action="store_true", help="强制重新生成所有音频")
    args = ap.parse_args()

    out = Path(args.out) if args.out else Path.cwd() / "short-drama-output"
    out.mkdir(parents=True, exist_ok=True)
    wdir = work_dir(out)
    shots_path = Path(args.shots) if args.shots else wdir / "shots.json"
    if not shots_path.exists():
        print(f"错误：找不到分镜文件 {shots_path}", file=sys.stderr)
        return 1

    data = json_load(shots_path)
    shots = data["shots"]
    audio_dir = wdir / AUDIO_SUB
    audio_dir.mkdir(parents=True, exist_ok=True)

    engine = args.engine
    if engine == "auto" and not _edge_available():
        print("edge-tts 不可用，回退 SAPI 本地语音。", file=sys.stderr)
        engine = "sapi"
    if engine == "edge" and not _edge_available():
        print("错误：edge-tts 未安装（pip install edge-tts），且指定了 edge 引擎。", file=sys.stderr)
        return 1

    ok_cnt = fail_cnt = silent = 0
    for s in shots:
        text = (s.get("dialogue") or "").strip()
        if not text:
            silent += 1
            continue
        mp3 = audio_dir / f"shot_{s['id']:03d}.mp3"
        if synth_shot(text, s.get("voice", ""), mp3, engine, args.force):
            dur = media_duration(mp3)
            s["audio"] = str(mp3)
            s["duration"] = round(dur, 2)
            ok_cnt += 1
            print(f"  [{s['id']:>3}] {dur:6.2f}s  {mp3.name}  {s['speaker']}：{text[:18]}")
        else:
            s["audio"] = None
            s["duration"] = 0.0
            fail_cnt += 1
            print(f"  [{s['id']:>3}] 配音失败：{text[:18]}", file=sys.stderr)

    data["shots"] = shots
    json_dump(data, shots_path)
    print(f"配音完成：成功 {ok_cnt}，失败 {fail_cnt}，无台词 {silent}。")
    return 0 if fail_cnt == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())