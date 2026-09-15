#!/usr/bin/env python3
"""
旁白配音与字幕合成脚本

为已生成的视频添加旁白配音和字幕：
1. 读取旁白文本（每行一段），用 TTS 生成逐段音频
2. 根据每段音频实际时长，自动对齐生成 SRT 字幕
3. 拼接音频为完整旁白
4. 用 ffmpeg 将音频混入视频，并按需烧录字幕
5. 输出带声字幕的最终视频 + SRT 字幕文件

支持双 TTS 引擎：
  - edge-tts（在线，音质自然，男/女多声色，默认优先）
  - Windows SAPI（离线，系统自带，中文女声 Huihui，断网回退）

用法：
  # 基本用法（自动选择引擎，烧录字幕进画面）
  python add_voice_subtitle.py --video input.mp4 --narration narration.txt --output out.mp4

  # 直接传文本（用 | 分段）
  python add_voice_subtitle.py --video input.mp4 --narration-text "第一段|第二段" --output out.mp4

  # 指定引擎和声音
  python add_voice_subtitle.py --video input.mp4 --narration n.txt --engine edge --voice zh-CN-YunxiNeural --output out.mp4

  # 烧录字幕 + 单独输出 SRT 备份（文件名加后缀，避免播放器自动加载叠加）
  python add_voice_subtitle.py --video input.mp4 --narration n.txt --subtitle-mode both --output out.mp4

  # 仅软字幕（不烧录）
  python add_voice_subtitle.py --video input.mp4 --narration n.txt --subtitle-mode subtitle --output out.mp4

依赖：
  - edge-tts（在线，pip install edge-tts）
  - pywin32（SAPI，通常系统已带 win32com）
  - imageio-ffmpeg（获取 ffmpeg）
"""

import argparse
import asyncio
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# 获取 ffmpeg
try:
    from imageio_ffmpeg import get_ffmpeg_exe
    FFMPEG = get_ffmpeg_exe()
except Exception:
    FFMPEG = None

# edge-tts（可选）
try:
    import edge_tts
    HAS_EDGE = True
except ImportError:
    HAS_EDGE = False

# ──────────────────────────────────────────────
# 常量
# ──────────────────────────────────────────────

# edge-tts 推荐声音（中文）
EDGE_VOICES = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",   # 女，温和，默认
    "xiaoyi":   "zh-CN-XiaoyiNeural",     # 女，活泼
    "yunxi":    "zh-CN-YunxiNeural",      # 男，沉稳
    "yunyang":  "zh-CN-YunxiNeural",      # 男，专业
    "yunjian":  "zh-CN-YunjianNeural",    # 男，运动
}

# SAPI 声音
SAPI_VOICES = {
    "huihui": "Microsoft Huihui Desktop - Chinese (Simplified)",
    "zira":   "Microsoft Zira Desktop - English (United States)",
}

DEFAULT_EDGE_VOICE = EDGE_VOICES["xiaoxiao"]
DEFAULT_SAPI_VOICE = "huihui"

# Windows 中文字体路径
WINDOWS_FONTS = [
    ("Microsoft YaHei", r"C:\Windows\Fonts\msyh.ttc"),
    ("SimHei",          r"C:\Windows\Fonts\simhei.ttf"),
    ("SimSun",          r"C:\Windows\Fonts\simsun.ttc"),
]

# 字幕样式（ASS force_style 参数）
SUBTITLE_STYLE = (
    "FontName={font},FontSize={size},"
    "PrimaryColour=&H00FFFFFF,"        # 白色字幕
    "OutlineColour=&H00000000,"        # 黑色描边
    "BackColour=&H80000000,"           # 半透明背景
    "Bold=1,BorderStyle=1,Outline=2,Shadow=1,"
    "Alignment=2,MarginV={margin}"      # 底部居中
)


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def get_desktop() -> Path:
    """跨平台获取桌面路径"""
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
    home = Path.home()
    for name in ("Desktop", "桌面"):
        candidate = home / name
        if candidate.exists():
            return candidate
    return home


def find_font() -> str:
    """查找可用的中文字体名"""
    for font_name, font_path in WINDOWS_FONTS:
        if Path(font_path).exists():
            return font_name
    return "SimHei"


def get_audio_duration(path: Path) -> float:
    """用 ffmpeg 获取音频时长（秒）"""
    if not FFMPEG:
        # 回退：直接读 wav
        try:
            import wave
            with wave.open(str(path), 'rb') as f:
                return f.getnframes() / f.getframerate()
        except Exception:
            return 0.0
    cmd = [FFMPEG, '-i', str(path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        text = result.stderr or result.stdout or ""
        m = re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)', text)
        if m:
            h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
            return h * 3600 + mi * 60 + s
    except Exception:
        pass
    # 最后回退 wav
    try:
        import wave
        with wave.open(str(path), 'rb') as f:
            return f.getnframes() / f.getframerate()
    except Exception:
        return 0.0


def fmt_srt_time(seconds: float) -> str:
    """秒数转 SRT 时间格式 HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def smart_wrap(text: str, max_chars: int = 16) -> str:
    """长文本智能断句为多行，用 libass 的 \\N 强制换行符连接。

    避免长文本被 libass 不可控地随意折行产生视觉错乱。
    优先在标点（，。；！？、）处断开；无标点则按字数硬切。

    Args:
        text: 单段字幕文本
        max_chars: 单行最大字符数，默认 16

    Returns:
        可能含 \\N 的多行文本
    """
    text = text.strip()
    if len(text) <= max_chars:
        return text

    # 按标点分段，标点作为分隔符保留
    parts = re.split(r'([，。；！？、,.!?;])', text)
    chunks = []
    buf = ""
    for p in parts:
        buf += p
        if p in "，。；！？、,.!?;" and len(buf) >= max_chars * 0.6:
            chunks.append(buf)
            buf = ""
    if buf:
        chunks.append(buf)

    # 仍超长的行硬切
    final = []
    for c in chunks:
        while len(c) > max_chars:
            final.append(c[:max_chars])
            c = c[max_chars:]
        if c:
            final.append(c)

    return "\\N".join(final)


# ──────────────────────────────────────────────
# TTS 引擎
# ──────────────────────────────────────────────

async def _tts_edge(text: str, voice: str, out_path: Path) -> bool:
    """用 edge-tts 生成音频（mp3）"""
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(out_path))
        return out_path.exists() and out_path.stat().st_size > 0
    except Exception as e:
        print(f"    edge-tts 生成失败: {e}")
        return False


def tts_edge(text: str, voice: str, out_path: Path) -> bool:
    """同步封装 edge-tts"""
    return asyncio.run(_tts_edge(text, voice, out_path))


def tts_sapi(text: str, voice_key: str, out_path: Path) -> bool:
    """用 Windows SAPI 生成音频（wav）"""
    try:
        import win32com.client
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        # 选择声音
        target_name = SAPI_VOICES.get(voice_key, "")
        if target_name:
            voices = speaker.GetVoices()
            for i in range(voices.Count):
                desc = voices.Item(i).GetDescription()
                if target_name in desc:
                    speaker.Voice = voices.Item(i)
                    break
        # 输出流
        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        # 3 = SSFMCreateForWrite
        stream.Open(str(out_path), 3, False)
        speaker.AudioOutputStream = stream
        speaker.Speak(text)
        stream.Close()
        return out_path.exists() and out_path.stat().st_size > 0
    except Exception as e:
        print(f"    SAPI 生成失败: {e}")
        return False


def generate_segment_tts(text: str, engine: str, voice: str,
                         out_path: Path, segment_idx: int) -> bool:
    """生成单段音频，按引擎选择"""
    print(f"  [段 {segment_idx+1}] TTS 生成中 ({engine})...")

    if engine == "edge":
        ok = tts_edge(text, voice, out_path)
        if not ok:
            print(f"    edge-tts 失败，尝试回退 SAPI...")
            ok = tts_sapi(text, DEFAULT_SAPI_VOICE, out_path)
        return ok
    elif engine == "sapi":
        return tts_sapi(text, voice if voice in SAPI_VOICES else DEFAULT_SAPI_VOICE, out_path)
    else:  # auto
        if HAS_EDGE:
            ok = tts_edge(text, voice, out_path)
            if ok:
                return True
            print(f"    edge-tts 不可用，回退 SAPI...")
        return tts_sapi(text, DEFAULT_SAPI_VOICE, out_path)


# ──────────────────────────────────────────────
# 核心流程
# ──────────────────────────────────────────────

def load_narration(narration_file: str = None, narration_text: str = None) -> list:
    """加载旁白文本，返回段落列表"""
    if narration_file:
        with open(narration_file, 'r', encoding='utf-8') as f:
            content = f.read()
        # 按换行分段，空行跳过
        segments = [line.strip() for line in content.splitlines() if line.strip()]
    elif narration_text:
        # 支持 | 分段
        segments = [s.strip() for s in re.split(r'[|｜]', narration_text) if s.strip()]
    else:
        segments = []

    # 过滤空段
    return [s for s in segments if s]


def generate_narration(segments: list, engine: str, voice: str,
                       temp_dir: Path) -> tuple:
    """逐段生成 TTS 音频，返回 (音频路径列表, 各段时长列表)"""
    audio_paths = []
    durations = []

    for idx, text in enumerate(segments):
        ext = "mp3" if (engine != "sapi" and HAS_EDGE) else "wav"
        seg_path = temp_dir / f"narration_{idx:03d}.{ext}"

        ok = generate_segment_tts(text, engine, voice, seg_path, idx)
        if not ok:
            print(f"  [段 {idx+1}] 生成失败，跳过")
            audio_paths.append(None)
            durations.append(0.0)
            continue

        dur = get_audio_duration(seg_path)
        audio_paths.append(seg_path)
        durations.append(dur)
        print(f"  [段 {idx+1}] 完成，时长 {dur:.2f}s")

    return audio_paths, durations


def generate_srt(segments: list, durations: list, srt_path: Path,
                 max_segment_disp: float = 6.0, max_chars: int = 16) -> Path:
    """根据旁白段落和音频时长生成 SRT 字幕。

    - 长文本用 smart_wrap 智能断句（\\N 换行），避免 libass 随意折行
    - 超长音频段落（>max_segment_disp 秒）拆分为多条字幕，每条时长均分
    - 时间轴严格连续，无重叠
    """
    lines = []
    idx = 1
    current = 0.0

    for text, dur in zip(segments, durations):
        if dur <= 0:
            continue

        wrapped = smart_wrap(text, max_chars)

        # 超长段落拆为多条字幕
        if dur > max_segment_disp and "\\N" in wrapped:
            sub_lines = wrapped.split("\\N")
            n = len(sub_lines)
            sub_dur = dur / n
            for i, sl in enumerate(sub_lines):
                start = current + i * sub_dur
                end = current + (i + 1) * sub_dur
                lines.append(str(idx))
                lines.append(f"{fmt_srt_time(start)} --> {fmt_srt_time(end)}")
                lines.append(sl)
                lines.append("")
                idx += 1
        else:
            start = current
            end = current + dur
            lines.append(str(idx))
            lines.append(f"{fmt_srt_time(start)} --> {fmt_srt_time(end)}")
            lines.append(wrapped)
            lines.append("")
            idx += 1

        current = current + dur

    srt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print(f"  字幕生成完成: {srt_path}")
    return srt_path


def concat_audio(audio_paths: list, output: Path) -> bool:
    """拼接多段音频为一个完整音频文件（统一转 wav）"""
    valid = [p for p in audio_paths if p and Path(p).exists()]
    if not valid:
        return False
    if len(valid) == 1:
        # 单段也转 wav 统一
        cmd = [FFMPEG, '-y', '-i', str(valid[0]), '-ac', '1', '-ar', '44100',
               str(output)]
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        return output.exists() and output.stat().st_size > 0

    # 用 concat demuxer
    list_file = output.parent / "audio_concat.txt"
    with open(list_file, 'w', encoding='utf-8') as f:
        for p in valid:
            f.write(f"file '{p}'\n")

    cmd = [FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', str(list_file),
           '-ac', '1', '-ar', '44100', str(output)]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    list_file.unlink(missing_ok=True)
    return output.exists() and output.stat().st_size > 0


def compose_video(video: Path, narration_wav: Path, srt_path: Path,
                  output: Path, subtitle_mode: str,
                  font: str, font_size: int, margin_v: int) -> bool:
    """用 ffmpeg 合成最终视频：混入旁白音频 + 字幕处理"""
    if not FFMPEG:
        print("错误: ffmpeg 不可用")
        return False

    cmd = [FFMPEG, '-y', '-i', str(video), '-i', str(narration_wav)]

    style = SUBTITLE_STYLE.format(font=font, size=font_size, margin=margin_v)

    if subtitle_mode in ("burn", "both"):
        # 烧录字幕：subtitles 滤镜作用于视频流，输出需用 [vout] 标签映射
        # Windows 路径转义：反斜杠→正斜杠，冒号转义
        srt_escaped = str(srt_path).replace('\\', '/').replace(':', '\\:')
        fonts_dir = "C\\:/Windows/Fonts"
        filter_str = (
            f"[0:v]subtitles='{srt_escaped}':"
            f"fontsdir='{fonts_dir}':"
            f"force_style='{style}'[vout]"
        )
        cmd = [FFMPEG, '-y', '-i', str(video), '-i', str(narration_wav),
               '-filter_complex', filter_str,
               '-map', '[vout]', '-map', '1:a',
               '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
               '-pix_fmt', 'yuv420p',
               '-c:a', 'aac', '-b:a', '128k',
               '-shortest', str(output)]
    elif subtitle_mode == "subtitle":
        # 软字幕：SRT 作为 mov_text 轨道
        cmd += ['-map', '0:v', '-map', '1:a',
                '-c:v', 'copy',
                '-c:a', 'aac', '-b:a', '128k',
                '-i', str(srt_path),
                '-c:s', 'mov_text',
                '-metadata:s:s:0', 'language=chi',
                '-shortest', str(output)]
        # 注意：软字幕需要重新编排参数
        cmd = [FFMPEG, '-y', '-i', str(video), '-i', str(narration_wav),
               '-i', str(srt_path),
               '-map', '0:v', '-map', '1:a', '-map', '2:s',
               '-c:v', 'copy',
               '-c:a', 'aac', '-b:a', '128k',
               '-c:s', 'mov_text',
               '-metadata:s:s:0', 'language=chi',
               '-shortest', str(output)]
    else:
        # 无字幕（仅音频）
        cmd += ['-map', '0:v', '-map', '1:a',
                '-c:v', 'copy',
                '-c:a', 'aac', '-b:a', '128k',
                '-shortest', str(output)]

    print(f"  ffmpeg 合成中...")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        print(f"  ffmpeg 合成失败:")
        print(r.stderr[-800:] if r.stderr else "(无错误输出)")
        return False
    return output.exists() and output.stat().st_size > 0


# ──────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────

def run(video: str, narration_file: str, narration_text: str,
        engine: str, voice: str, subtitle_mode: str,
        output: str, srt_output: str,
        font_size: int = 22, margin_v: int = 40):
    """主流程"""
    video_path = Path(video)
    if not video_path.exists():
        print(f"错误: 视频文件不存在: {video_path}")
        return None

    # 加载旁白
    segments = load_narration(narration_file, narration_text)
    if not segments:
        print("错误: 旁白文本为空")
        return None

    print(f"\n{'='*60}")
    print(f"旁白配音与字幕合成")
    print(f"{'='*60}")
    print(f"  视频源: {video_path}")
    print(f"  旁白段数: {len(segments)}")
    print(f"  TTS 引擎: {engine}" + ("（edge-tts 优先，SAPI 回退）" if engine == "auto" else ""))
    print(f"  字幕模式: {subtitle_mode}")
    print(f"  字体字号: {font_size}px")
    print()

    # 字体
    font = find_font()

    # 输出路径
    if output:
        output_path = Path(output)
    else:
        stem = video_path.stem
        output_path = get_desktop() / f"{stem}_配音字幕.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if srt_output:
        srt_path = Path(srt_output)
    else:
        # SRT 文件名加后缀，避免与视频同名被播放器自动加载导致字幕重复叠加
        srt_path = output_path.with_name(f"{output_path.stem}_字幕.srt")

    # 临时目录
    temp_dir = Path(tempfile.mkdtemp(prefix="voice_sub_"))

    try:
        # 1. 生成各段 TTS
        print(f"{'='*60}")
        print(f"步骤 1/4: TTS 配音生成")
        print(f"{'='*60}")
        audio_paths, durations = generate_narration(
            segments, engine, voice, temp_dir
        )
        success_count = sum(1 for p in audio_paths if p)
        print(f"  成功: {success_count}/{len(segments)} 段")
        if success_count == 0:
            print("错误: 没有成功生成任何音频段")
            return None

        # 2. 生成 SRT 字幕
        print(f"\n{'='*60}")
        print(f"步骤 2/4: SRT 字幕生成")
        print(f"{'='*60}")
        generate_srt(segments, durations, srt_path)
        total_audio_dur = sum(durations)
        print(f"  旁白总时长: {total_audio_dur:.2f}s")

        # 3. 拼接音频
        print(f"\n{'='*60}")
        print(f"步骤 3/4: 音频拼接")
        print(f"{'='*60}")
        narration_wav = temp_dir / "narration_full.wav"
        if concat_audio(audio_paths, narration_wav):
            wsize = narration_wav.stat().st_size / 1048576
            print(f"  拼接完成: {wsize:.2f} MB")
        else:
            print("错误: 音频拼接失败")
            return None

        # 4. ffmpeg 合成
        print(f"\n{'='*60}")
        print(f"步骤 4/4: 视频合成")
        print(f"{'='*60}")
        if compose_video(video_path, narration_wav, srt_path, output_path,
                         subtitle_mode, font, font_size, margin_v):
            fsize = output_path.stat().st_size / 1048576
            print(f"\n合成成功!")
            print(f"  视频文件: {output_path}")
            print(f"  视频大小: {fsize:.2f} MB")
            print(f"  字幕文件: {srt_path}")
            return output_path
        else:
            print("合成失败!")
            return None

    finally:
        # 清理临时目录
        import shutil
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


# ──────────────────────────────────────────────
# 命令行入口
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="为视频添加旁白配音和字幕",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python add_voice_subtitle.py --video in.mp4 --narration n.txt --output out.mp4
  python add_voice_subtitle.py --video in.mp4 --narration-text "第一段|第二段" --output out.mp4
  python add_voice_subtitle.py --video in.mp4 --narration n.txt --engine edge --voice zh-CN-YunxiNeural --output out.mp4
  python add_voice_subtitle.py --video in.mp4 --narration n.txt --subtitle-mode subtitle --output out.mp4

可用声音:
  edge-tts: xiaoxiao(默认女), xiaoyi(女), yunxi(男), yunyang(男), yunjian(男)
            或直接传完整 voice id 如 zh-CN-XiaoxiaoNeural
  SAPI:     huihui(中文女), zira(英文女)
        """
    )
    parser.add_argument("--video", required=True, help="输入视频路径")
    parser.add_argument("--narration", help="旁白文本文件路径（每行一段）")
    parser.add_argument("--narration-text", help="旁白文本（用 | 分段）")
    parser.add_argument("--engine", choices=["auto", "edge", "sapi"],
                        default="auto", help="TTS 引擎（默认 auto）")
    parser.add_argument("--voice", default=None,
                        help="声音（edge: xiaoxiao/yunxi等; sapi: huihui/zira）")
    parser.add_argument("--subtitle-mode", choices=["burn", "subtitle", "both", "none"],
                        default="burn",
                        help="字幕模式（默认 burn: 仅烧录进画面；both: 烧录+SRT备份；"
                             "subtitle: 仅软字幕轨；none: 仅配音）")
    parser.add_argument("--output", help="输出视频路径（默认桌面）")
    parser.add_argument("--srt-output", help="SRT 字幕输出路径（both模式下默认加_字幕后缀）")
    parser.add_argument("--font-size", type=int, default=22, help="字幕字号（默认22）")
    parser.add_argument("--margin-v", type=int, default=40, help="字幕底部边距（默认40）")

    args = parser.parse_args()

    # 解析 voice
    voice = args.voice
    if voice and voice in EDGE_VOICES:
        voice = EDGE_VOICES[voice]

    result = run(
        video=args.video,
        narration_file=args.narration,
        narration_text=args.narration_text,
        engine=args.engine,
        voice=voice or DEFAULT_EDGE_VOICE,
        subtitle_mode=args.subtitle_mode,
        output=args.output,
        srt_output=args.srt_output,
        font_size=args.font_size,
        margin_v=args.margin_v,
    )

    if result:
        print(f"\n{'='*60}")
        print(f"配音字幕合成完成!")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print(f"合成失败")
        print(f"{'='*60}")
        sys.exit(1)


if __name__ == "__main__":
    main()
