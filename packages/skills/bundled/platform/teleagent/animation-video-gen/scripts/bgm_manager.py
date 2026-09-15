#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BGM/音效管理工具
为短剧视频添加背景音乐和音效

功能:
  1. 管理BGM库（本地免版权曲库目录索引，支持 BGM_LIBRARY_DIR 环境变量）
  2. 根据场景情感自动匹配BGM（优先返回库内真实文件路径）
  3. 混合TTS人声和BGM
  4. 合成常用音效（心跳/雨声/雷声/脚步声等，无需外部素材）
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


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


# BGM情感分类映射
BGM_MOOD_MAP = {
    "tense": {"tempo": "fast", "instruments": "strings+drums", "desc": "紧张/悬疑", "keywords": ["tense", "suspense", "thriller", "dark"]},
    "romantic": {"tempo": "slow", "instruments": "piano+strings", "desc": "浪漫/温馨", "keywords": ["romantic", "love", "gentle", "piano"]},
    "epic": {"tempo": "medium-fast", "instruments": "orchestra", "desc": "史诗/壮阔", "keywords": ["epic", "cinematic", "orchestral", "heroic"]},
    "sad": {"tempo": "slow", "instruments": "piano+solo", "desc": "悲伤/感伤", "keywords": ["sad", "emotional", "melancholy", "heartbreak"]},
    "happy": {"tempo": "medium", "instruments": "guitar+light", "desc": "开心/轻快", "keywords": ["happy", "upbeat", "cheerful", "joyful"]},
    "mysterious": {"tempo": "slow-medium", "instruments": "synth+ambient", "desc": "神秘/探索", "keywords": ["mysterious", "ambient", "mystery", "synth"]},
    "action": {"tempo": "fast", "instruments": "drums+brass", "desc": "动作/追逐", "keywords": ["action", "battle", "fight", "intense"]},
    "calm": {"tempo": "slow", "instruments": "ambient+piano", "desc": "平静/日常", "keywords": ["calm", "chill", "lo-fi", "relax"]},
}

# BGM 免版权曲库目录（可通过环境变量 BGM_LIBRARY_DIR 指定，如 D:\bgm_library）
# 目录结构建议：
#   <BGM_LIBRARY_DIR>/tense/dark_theme.mp3
#   <BGM_LIBRARY_DIR>/happy/upbeat_day.wav
#   <BGM_LIBRARY_DIR>/epic_cinematic.mp3   （也支持根目录文件名关键词匹配）
BGM_LIBRARY_DIR = os.environ.get("BGM_LIBRARY_DIR", "")

# 支持的音频扩展名
_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"}

# 常用音效
SOUND_EFFECTS = {
    "door_close": "关门声",
    "footsteps": "脚步声",
    "rain": "雨声",
    "thunder": "雷声",
    "phone_ring": "电话铃声",
    "glass_break": "玻璃碎裂",
    "heartbeat": "心跳声",
    "crowd": "人群嘈杂",
    "car": "汽车声",
    "wind": "风声",
    "clock_tick": "时钟滴答",
    "sword": "刀剑声",
}

# 可用 FFmpeg lavfi 合成器直接生成的音效（无需外部素材）
# 值: (filter_complex 生成链, 说明)
SFX_SYNTHESIZABLE = {
    "heartbeat": ('aevalsrc=exprs=0.8*sin(2*PI*55*t)*exp(-30*mod(t,0.9)):s=44100', "低频双脉冲心跳（可调 0.9s 周期）"),
    "footsteps": ('aevalsrc=exprs=0.6*sin(2*PI*80*t)*exp(-50*mod(t,0.5)):s=44100', "低频短促脚步"),
    "clock_tick": ('aevalsrc=exprs=0.9*sin(2*PI*2000*t)*exp(-120*mod(t,1.0)):s=44100', "清脆钟摆滴答"),
    "phone_ring": ('aevalsrc=exprs=(0.4*sin(2*PI*440*t)+0.4*sin(2*PI*660*t))*lt(mod(t,1.6),0.9):s=44100', "440/660Hz 双音响铃"),
    "rain": ('anoisesrc=color=white:amplitude=0.35:seed=42,lowpass=f=6500,highpass=f=400', "白色噪声+带通≈雨声"),
    "wind": ('anoisesrc=color=pink:amplitude=0.25:seed=7,lowpass=f=450', "粉红噪声低通≈风声"),
    "crowd": ('anoisesrc=color=pink:amplitude=0.18:seed=99,bandpass=f=900:w=600', "粉红噪声带通≈人群嘈杂"),
    "thunder_hit": ('aevalsrc=exprs=0.9*(random(0)-0.5)*exp(-0.8*t):s=44100,lowpass=f=180', "低频轰鸣雷击"),
    "glass_break": ('anoisesrc=color=white:amplitude=0.5:seed=13,highpass=f=2800,afade=t=out:st=1.2:d=0.8', "高频噪声爆发≈玻璃碎裂"),
    "door_close": ('aevalsrc=exprs=0.7*sin(2*PI*70*t)*exp(-22*t)+0.3*(random(0)-0.5)*exp(-15*t):s=44100', "低频撞击+短噪声≈关门"),
}

# 无法可靠合成的音效（建议从免版权库下载）
SFX_EXTERNAL_ONLY = {"car", "sword"}


def mix_audio_tracks(
    voice_path: str,
    bgm_path: str,
    output_path: str,
    voice_volume: float = 1.0,
    bgm_volume: float = 0.3,
    fade_in: float = 1.0,
    fade_out: float = 2.0,
):
    """
    混合TTS人声和BGM

    Args:
        voice_path: 人声音频路径
        bgm_path: BGM音频路径
        output_path: 输出音频路径
        voice_volume: 人声音量（0-1）
        bgm_volume: BGM音量（0-1）
        fade_in: BGM淡入时间（秒）
        fade_out: BGM淡出时间（秒）
    """
    ffmpeg = get_ffmpeg_cmd()

    filter_complex = (
        f'[1:a]volume={bgm_volume},afade=t=in:st=0:d={fade_in},afade=t=out:st=dur-{fade_out}:d={fade_out}[bgm];'
        f'[0:a]volume={voice_volume}[voice];'
        f'[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]'
    )

    result = subprocess.run(
        [ffmpeg, "-y", "-i", voice_path, "-i", bgm_path,
         "-filter_complex", filter_complex,
         "-map", "[aout]", "-c:a", "aac", output_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[ERROR] Audio mixing failed: {result.stderr}")
        # 回退：仅保留人声
        shutil.copy2(voice_path, output_path)
        print(f"[WARN] Fallback: copied voice only -> {output_path}")
        return output_path

    print(f"[OK] Mixed audio saved: {output_path}")
    return output_path


def add_bgm_to_video(
    video_path: str,
    bgm_path: str,
    output_path: str,
    bgm_volume: float = 0.3,
    fade_in: float = 1.0,
    fade_out: float = 2.0,
):
    """
    为视频添加BGM

    Args:
        video_path: 输入视频路径
        bgm_path: BGM音频路径
        output_path: 输出视频路径
        bgm_volume: BGM音量
        fade_in: BGM淡入时间
        fade_out: BGM淡出时间
    """
    ffmpeg = get_ffmpeg_cmd()

    filter_complex = (
        f'[1:a]volume={bgm_volume},afade=t=in:st=0:d={fade_in},afade=t=out:st=dur-{fade_out}:d={fade_out}[bgm];'
        f'[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]'
    )

    result = subprocess.run(
        [ffmpeg, "-y", "-i", video_path, "-i", bgm_path,
         "-filter_complex", filter_complex,
         "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac",
         "-shortest", output_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[ERROR] BGM add failed: {result.stderr}")
        return None

    print(f"[OK] Video with BGM saved: {output_path}")
    return output_path


def generate_silence(duration: float, output_path: str = "silence.mp3"):
    """生成静音文件（用于填充无BGM的段落）"""
    ffmpeg = get_ffmpeg_cmd()
    subprocess.run(
        [ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-t", str(duration), "-c:a", "aac", output_path],
        check=True, capture_output=True
    )
    return output_path


def scan_bgm_library(lib_dir: Optional[str] = None) -> Dict[str, List[str]]:
    """扫描免版权 BGM 曲库目录，按 mood 分类索引

    匹配规则（两级）：
      1. 子目录名 == mood（如 <lib>/tense/*.mp3）
      2. 根目录文件名含该 mood 的关键词（如 epic_cinematic.mp3）

    Args:
        lib_dir: 曲库目录，默认取环境变量 BGM_LIBRARY_DIR

    Returns:
        {mood: [文件路径, ...]}，未配置目录时返回空 dict
    """
    lib_dir = lib_dir or BGM_LIBRARY_DIR
    if not lib_dir or not os.path.isdir(lib_dir):
        return {}

    indexed: Dict[str, List[str]] = {mood: [] for mood in BGM_MOOD_MAP}
    root = Path(lib_dir)

    # 规则1：按 mood 命名的子目录
    for mood in BGM_MOOD_MAP:
        mood_dir = root / mood
        if mood_dir.is_dir():
            for f in sorted(mood_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in _AUDIO_EXTS:
                    indexed[mood].append(str(f))

    # 规则2：根目录文件名关键词匹配
    for f in sorted(root.iterdir()):
        if not (f.is_file() and f.suffix.lower() in _AUDIO_EXTS):
            continue
        fname = f.stem.lower()
        for mood, info in BGM_MOOD_MAP.items():
            if mood in fname or any(k in fname for k in info["keywords"]):
                if str(f) not in indexed[mood]:
                    indexed[mood].append(str(f))

    return {m: paths for m, paths in indexed.items() if paths}


def match_bgm_for_scene(scene_emotion: str, lib_dir: Optional[str] = None) -> Optional[str]:
    """根据场景情感匹配 BGM

    优先级：
      1. 免版权曲库中真实匹配到文件 → 返回文件路径
      2. 未匹配到 → 返回 None，并打印推荐搜索关键词

    Args:
        scene_emotion: 场景情感（angry/sad/happy/serious/romantic/mysterious/calm/epic/action/cheerful）
        lib_dir: 曲库目录，默认取环境变量 BGM_LIBRARY_DIR

    Returns:
        BGM 文件路径或 None
    """
    emotion_to_mood = {
        "angry": "tense",
        "sad": "sad",
        "happy": "happy",
        "cheerful": "happy",
        "serious": "tense",
        "romantic": "romantic",
        "mysterious": "mysterious",
        "calm": "calm",
        "epic": "epic",
        "action": "action",
    }

    mood = emotion_to_mood.get(scene_emotion, "calm")
    bgm_info = BGM_MOOD_MAP.get(mood, BGM_MOOD_MAP["calm"])
    print(f"[INFO] Scene emotion '{scene_emotion}' -> BGM mood: {mood} ({bgm_info['desc']})")

    lib = scan_bgm_library(lib_dir)
    if mood in lib and lib[mood]:
        picked = lib[mood][0]
        print(f"[OK] Matched BGM from library: {picked}")
        return picked

    if not lib:
        print("[INFO] 未配置免版权曲库（可设置环境变量 BGM_LIBRARY_DIR 指向本地曲库目录）")
    print(f"[HINT] 可到免版权站点搜索关键词: {' '.join(bgm_info['keywords'])} (见 references/free_resources.md)")
    return None


def synthesize_sfx(name: str, output_path: str, duration: float = 2.0) -> Optional[str]:
    """用 FFmpeg lavfi 合成常用音效（无需外部素材）

    可合成: heartbeat / footsteps / clock_tick / phone_ring / rain / wind /
            crowd / thunder_hit / glass_break / door_close
    不可合成（需素材库）: car / sword

    Args:
        name: 音效名称（见 SFX_SYNTHESIZABLE）
        output_path: 输出音频路径
        duration: 时长（秒）

    Returns:
        成功返回输出路径，失败返回 None
    """
    if name not in SFX_SYNTHESIZABLE:
        print(f"[ERROR] Unsupported SFX: {name}")
        print(f"        可合成: {', '.join(sorted(SFX_SYNTHESIZABLE))}")
        print(f"        需外部素材: {', '.join(sorted(SFX_EXTERNAL_ONLY))}")
        return None

    ffmpeg = get_ffmpeg_cmd()
    gen, desc = SFX_SYNTHESIZABLE[name]
    result = subprocess.run(
        [ffmpeg, "-y", "-f", "lavfi", "-i", gen,
         "-t", str(duration), "-c:a", "aac", "-b:a", "192k", output_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[ERROR] SFX synth failed ({name}): {result.stderr}")
        return None
    print(f"[OK] Synthesized SFX '{name}' ({desc}): {output_path}")
    return output_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BGM/音效管理")
    sub = parser.add_subparsers(dest="cmd")

    mix = sub.add_parser("mix", help="混合人声和BGM")
    mix.add_argument("--voice", required=True)
    mix.add_argument("--bgm", required=True)
    mix.add_argument("--output", default="mixed_audio.mp3")
    mix.add_argument("--bgm-volume", type=float, default=0.3)

    vid = sub.add_parser("add", help="为视频添加BGM")
    vid.add_argument("--video", required=True)
    vid.add_argument("--bgm", required=True)
    vid.add_argument("--output", default="video_with_bgm.mp4")
    vid.add_argument("--bgm-volume", type=float, default=0.3)

    sub.add_parser("list-moods", help="列出BGM情感分类")

    synth = sub.add_parser("synth", help="合成音效(无需外部素材)")
    synth.add_argument("--name", required=True, help="音效名: " + ", ".join(sorted(SFX_SYNTHESIZABLE)))
    synth.add_argument("--output", default="sfx.mp3", help="输出音频路径")
    synth.add_argument("--duration", type=float, default=5.0, help="时长(秒)")

    lib = sub.add_parser("scan", help="扫描免版权BGM曲库(BGM_LIBRARY_DIR)")
    lib.add_argument("--dir", default=None, help="曲库目录(默认取环境变量 BGM_LIBRARY_DIR)")

    args = parser.parse_args()

    if args.cmd == "mix":
        mix_audio_tracks(args.voice, args.bgm, args.output, bgm_volume=args.bgm_volume)
    elif args.cmd == "add":
        add_bgm_to_video(args.video, args.bgm, args.output, bgm_volume=args.bgm_volume)
    elif args.cmd == "list-moods":
        for mood, info in BGM_MOOD_MAP.items():
            print(f"  {mood:12s} | {info['desc']:8s} | tempo={info['tempo']}, {info['instruments']}")
    elif args.cmd == "synth":
        synthesize_sfx(args.name, args.output, args.duration)
    elif args.cmd == "scan":
        indexed = scan_bgm_library(args.dir)
        if not indexed:
            print("[INFO] 未扫描到 BGM 文件（或未配置 BGM_LIBRARY_DIR）")
            return
        total = 0
        for mood, paths in indexed.items():
            total += len(paths)
            for p in paths:
                print(f"  [{mood:10s}] {p}")
        print(f"[OK] 共索引 {total} 个 BGM 文件，覆盖 {len(indexed)} 个情绪分类")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()