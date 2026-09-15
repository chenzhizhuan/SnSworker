#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短剧渲染主脚本 (v2 — AI视频驱动)

将剧本JSON渲染为竖屏短剧动画视频（1080x1920, 9:16）

核心流程:
  1. 解析剧本 → 2. AI视频模型生成场景片段 → 3. TTS配音 → 4. FFmpeg合成

与 v1 的区别:
  - v1: ImageGen静态图 → Manim叠加动画层 → 配音 → 合成（图片配音拼贴）
  - v2: AI视频生成API → 真正的AI动画视频片段 → 配音 → 合成（角色能动）

回退策略:
  - 如果 API 未配置或调用失败，回退到 v1 的 ImageGen + Ken Burns 模式
"""

import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# 同目录下的模块（确保能import本技能的本地模块，优先级高于系统包）
sys.path.insert(0, str(Path(__file__).parent))
from ai_video_generator import (
    generate_scene_videos,
    build_video_prompt,
    STYLE_PROMPTS,
    get_available_models,
)


def run_cmd(args, cwd=None, check=True, capture=False):
    """执行命令（仅接受list args，避免shell注入）"""
    if isinstance(args, str):
        raise TypeError("run_cmd() 仅接受list形式参数以避免shell注入，请使用 run_cmd([cmd, arg1, arg2, ...])")
    print(f"[CMD] {' '.join(str(a) for a in args)}")
    result = subprocess.run(args, cwd=cwd, capture_output=capture, text=True)
    if check and result.returncode != 0:
        print(f"[ERROR] Command failed: {result.stderr}")
        sys.exit(1)
    return result


def _validate_concat_paths(file_list_path: str, allowed_dir: str) -> None:
    """验证concat列表中的文件路径未逃逸到预期目录之外"""
    allowed = Path(allowed_dir).resolve()
    with open(file_list_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("file "):
                quoted = line[5:].strip().strip("'\"")
                resolved = Path(quoted).resolve()
                if not str(resolved).startswith(str(allowed)):
                    raise ValueError(
                        f"Concat path escapes allowed directory: {resolved} "
                        f"(allowed: {allowed})"
                    )


def get_ffmpeg_cmd():
    """获取 FFmpeg 路径"""
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return "ffmpeg"
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        print("[ERROR] FFmpeg not found")
        sys.exit(1)


# ─── ASS 字幕工具 ─────────────────────────────────────

def _text_auto_wrap(text: str, max_chars_per_line: int = 18) -> str:
    """
    中文自动换行：按字数截断，避免字幕溢出画面
    英文按空格断行，中文按字数硬断
    """
    if len(text) <= max_chars_per_line:
        return text

    lines = []
    current_line = ""
    for ch in text:
        current_line += ch
        # 中文/全角字符算1，英文空格处可断
        if len(current_line) >= max_chars_per_line:
            # 尝试在最近的空格/标点处断行
            split_pos = -1
            for j in range(len(current_line) - 1, max(0, len(current_line) - 6), -1):
                if current_line[j] in (" ", "\u3000", "\uff0c", "\u3002", "\uff01",
                                       "\uff1f", "\uff1b", "\uff1a", "\u2014"):
                    split_pos = j
                    break
            if split_pos > 0:
                lines.append(current_line[:split_pos + 1])
                current_line = current_line[split_pos + 1:]
            else:
                lines.append(current_line)
                current_line = ""
    if current_line:
        lines.append(current_line)

    return "\\N".join(lines)


def _calc_font_size(text: str, base_size: int = 44) -> int:
    """
    根据文本长度自适应字号：
    - 短文本(<=12字): 原始大小
    - 中文本(13-20字): 缩小到 0.85
    - 长文本(>20字): 缩小到 0.7
    """
    char_count = len(text)
    if char_count <= 12:
        return base_size
    elif char_count <= 20:
        return max(int(base_size * 0.85), 28)
    else:
        return max(int(base_size * 0.7), 24)


def _format_ass_time(seconds: float) -> str:
    """将秒数转为 ASS 时间格式 H:MM:SS.CC"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_ass_subtitle(
    script_path: str,
    output_path: str,
    video_width: int = 1080,
    video_height: int = 1920,
    base_font_size: int = 44,
    style: str = "modern",
    mode: str = "subtitle",
    seconds_per_char: float = 0.35,
    min_duration: float = 1.5,
    gap_between: float = 0.3,
) -> str:
    """
    从剧本JSON生成ASS字幕文件

    Args:
        script_path: 剧本JSON路径
        output_path: ASS字幕输出路径
        video_width: 视频宽度
        video_height: 视频高度
        base_font_size: 基础字号
        style: 字幕样式 (modern/comic/dramatic)
        mode: 显示模式 (subtitle=底部字幕 / bubble=气泡)
        seconds_per_char: 每个字的显示时长(秒)
        min_duration: 最短显示时长
        gap_between: 两个字幕之间的间隔(秒)

    Returns:
        ASS文件路径
    """
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    # 安全边距 (像素)
    margin_h = 60   # 左右边距
    margin_v = 80   # 上下边距
    max_chars = int((video_width - 2 * margin_h) / (base_font_size * 0.55))  # 粗估每行字数

    # 字幕样式
    style_configs = {
        "modern": {
            "fontname": "Microsoft YaHei",
            "primary_color": "&H00FFFFFF",    # 白色
            "outline_color": "&H00000000",    # 黑色描边
            "back_color": "&H80000000",       # 半透明黑底
            "border_style": 3,                # 不透明底框
            "outline": 1,
            "shadow": 1,
            "alignment": 2,                   # 底部居中
            "margin_v": margin_v,
        },
        "comic": {
            "fontname": "Microsoft YaHei",
            "primary_color": "&H00000000",    # 黑色
            "outline_color": "&H00FFFFFF",    # 白色描边
            "back_color": "&H00000000",
            "border_style": 1,                # 描边+阴影
            "outline": 3,
            "shadow": 0,
            "alignment": 2,
            "margin_v": margin_v,
        },
        "dramatic": {
            "fontname": "Microsoft YaHei",
            "primary_color": "&H00E94560",    # 红色
            "outline_color": "&H00000000",
            "back_color": "&H80000000",
            "border_style": 3,
            "outline": 2,
            "shadow": 2,
            "alignment": 5,                   # 画面中间偏下
            "margin_v": int(video_height * 0.35),
        },
        # 韩式现言漫风格：白字+细黑描边，无底框，4层文字
        "korean_manga": {
            "fontname": "Microsoft YaHei",
            "primary_color": "&H00FFFFFF",    # 白色
            "outline_color": "&H00000000",    # 细黑描边
            "back_color": "&H00000000",       # 透明底
            "border_style": 1,                # 描边+阴影
            "outline": 2,                     # 中等描边
            "shadow": 0,
            "alignment": 2,                   # 底部居中
            "margin_v": margin_v,
        },
    }

    cfg = style_configs.get(style, style_configs["modern"])

    # ASS 头部
    ass_lines = [
        "[Script Info]",
        f"Title: {script.get('title', 'Short Drama')}",
        "ScriptType: v4.00+",
        f"PlayResX: {video_width}",
        f"PlayResY: {video_height}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        # 说话人标签样式（小字号，金色）
        f"Style: Speaker,{cfg['fontname']},{max(base_font_size - 10, 24)},"
        f"&H00FFD700,&H000000FF,{cfg['outline_colour']},{cfg['back_colour']},"
        f"-1,0,0,0,100,100,0,0,{cfg['border_style']},{cfg['outline']},{cfg['shadow']},"
        f"{cfg['alignment']},{margin_h},{margin_h},{cfg['margin_v']},1",
        # 对白文本样式（大字号，自适应）
        f"Style: Dialogue,{cfg['fontname']},{base_font_size},"
        f"{cfg['primary_colour']},&H000000FF,{cfg['outline_colour']},{cfg['back_colour']},"
        f"-1,0,0,0,100,100,0,0,{cfg['border_style']},{cfg['outline']},{cfg['shadow']},"
        f"{cfg['alignment']},{margin_h},{margin_h},{cfg['margin_v']},1",
        # 旁白样式（斜体，浅色）
        f"Style: Narration,{cfg['fontname']},{max(base_font_size - 6, 28)},"
        f"&H00CCCCCC,&H000000FF,{cfg['outline_colour']},{cfg['back_colour']},"
        f"-1,-1,0,0,100,100,0,0,{cfg['border_style']},{cfg['outline']},{cfg['shadow']},"
        f"8,{margin_h},{margin_h},{int(video_height * 0.25)},1",
        # Tier2: 提示信息（左上角"全文X分钟"、右侧竖排合规声明）
        f"Style: Tier2Hint,{cfg['fontname']},{max(base_font_size - 16, 20)},"
        f"&H80FFFFFF,&H000000FF,&H00000000,&H00000000,"
        f"-1,0,0,0,100,100,0,0,1,1,0,"
        f"7,{margin_h},{margin_h},{int(video_height * 0.08)},1",
        # Tier2右侧竖排合规声明
        f"Style: Tier2Compliance,{cfg['fontname']},{max(base_font_size - 14, 22)},"
        f"&H80FFFFFF,&H000000FF,&H00000000,&H00000000,"
        f"-1,0,0,0,100,100,0,0,1,1,0,"
        f"6,{int(video_width * 0.92)},{margin_h},{margin_v},1",
        # Tier3: 水印（角色胸部位置，浅粉半透明）
        f"Style: Tier3Watermark,{cfg['fontname']},{max(base_font_size - 12, 24)},"
        f"&H80FFB6C1,&H000000FF,&H00000000,&H00000000,"
        f"-1,0,0,0,100,100,0,0,1,0,0,"
        f"5,{margin_h},{margin_h},{int(video_height * 0.45)},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    # 生成字幕事件
    current_time = 0.0
    events = []

    for scene in script.get("scenes", []):
        scene_id = scene.get("id", 0)

        # 旁白
        narration = scene.get("narration", "")
        if narration:
            dur = max(len(narration) * seconds_per_char, min_duration)
            wrapped = _text_auto_wrap(narration, max_chars)
            events.append({
                "start": current_time,
                "end": current_time + dur,
                "style": "Narration",
                "name": "旁白",
                "text": wrapped,
            })
            current_time += dur + gap_between

        # 对白
        for dlg in scene.get("dialogues", []):
            speaker = dlg.get("speaker", "")
            text = dlg.get("text", "")
            if not text:
                continue

            # 字号自适应
            font_size = _calc_font_size(text, base_font_size)
            # 自适应行宽
            adaptive_max_chars = int((video_width - 2 * margin_h) / (font_size * 0.55))

            duration = max(len(text) * seconds_per_char, min_duration)

            # 说话人标签
            if speaker:
                speaker_dur = 0.6
                events.append({
                    "start": current_time,
                    "end": current_time + speaker_dur,
                    "style": "Speaker",
                    "name": speaker,
                    "text": speaker,
                })

            # 对白文本（自动换行）
            wrapped = _text_auto_wrap(text, adaptive_max_chars)

            # 如果字号不是默认，在文本中内嵌覆盖字号
            if font_size != base_font_size:
                wrapped = f"{{\\fs{font_size}}}{wrapped}"

            events.append({
                "start": current_time,
                "end": current_time + duration,
                "style": "Dialogue",
                "name": speaker,
                "text": wrapped,
            })
            current_time += duration + gap_between

    # 写入事件
    for ev in events:
        start = _format_ass_time(ev["start"])
        end = _format_ass_time(ev["end"])
        # ASS 文本中 \N 是换行
        text = ev["text"].replace("\\N", "\\N")
        ass_lines.append(
            f"Dialogue: 0,{start},{end},{ev['style']},{ev['name']},"
            f"0,0,0,,{text}"
        )

    # ── korean_manga 4层文字：Tier2提示 + Tier3水印（贯穿全片）──
    if style == "korean_manga":
        total_end = events[-1]["end"] if events else 60.0
        # Tier2: 左上角"全文X分钟"提示
        total_min = int(total_end // 60)
        if total_min > 0:
            ass_lines.append(
                f"Dialogue: 1,0:00:00.00,{_format_ass_time(total_end)},Tier2Hint,Hint,"
                f"0,0,0,,全文{total_min}分钟"
            )
        # Tier2: 右侧竖排合规声明（从剧本compliance字段读取）
        compliance = script.get("compliance", {})
        if compliance.get("enabled", True):
            comp_text = compliance.get("text", "内容虚拟演绎 切勿带入现实")
            # 竖排文字：每个字之间用\N换行
            vertical_text = "\\N".join(list(comp_text))
            ass_lines.append(
                f"Dialogue: 1,0:00:00.00,{_format_ass_time(total_end)},Tier2Compliance,Compliance,"
                f"0,0,0,,{vertical_text}"
            )
        # Tier3: 水印（从剧本watermark字段读取）
        watermark = script.get("watermark", {})
        if watermark.get("enabled", False):
            wm_text = watermark.get("text", "")
            if wm_text:
                ass_lines.append(
                    f"Dialogue: 2,0:00:00.00,{_format_ass_time(total_end)},Tier3Watermark,Watermark,"
                    f"0,0,0,,{wm_text}"
                )

    with open(output_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(ass_lines))

    print(f"[OK] ASS subtitle generated: {output_path} ({len(events)} events)")
    return output_path


class ShortDramaRenderer:
    """短剧动画渲染器 (v2 — AI视频驱动)"""

    # 竖屏9:16参数（默认）
    WIDTH = 1080
    HEIGHT = 1920
    FPS = 24

    # 横屏4:3参数
    HORIZONTAL_WIDTH = 1440
    HORIZONTAL_HEIGHT = 1080

    # 对白字幕样式预设
    SUBTITLE_STYLES = {
        "modern": {
            "bg_color": "#000000CC",
            "text_color": "#FFFFFF",
            "font_size": 48,
            "position": "bottom",
        },
        "comic": {
            "bg_color": "#FFFFFFEE",
            "text_color": "#000000",
            "font_size": 44,
            "position": "bottom",
        },
        "dramatic": {
            "bg_color": "#1A1A2ECC",
            "text_color": "#E94560",
            "font_size": 52,
            "position": "center",
        },
    }

    def __init__(
        self,
        script_path: str,
        output_dir: str = ".temp/short_drama",
        model: str = "seedance-2.0-pro",
        fallback: bool = True,
        ratio: Optional[str] = None,
    ):
        """
        Args:
            script_path: 剧本JSON路径
            output_dir: 输出目录
            model: AI视频模型 (seedance-2.0-pro / seedance-2.0-lite)
            fallback: API不可用时是否回退到 ImageGen 模式
            ratio: 画面宽高比覆盖 (9:16/16:9/4:3/1:1/3:4/21:9)，None 时读剧本JSON
        """
        self.script_path = script_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model = model
        self.fallback = fallback

        # 子目录
        self.frames_dir = self.output_dir / "frames"
        self.frames_dir.mkdir(exist_ok=True)
        self.audio_dir = self.output_dir / "audio"
        self.audio_dir.mkdir(exist_ok=True)
        self.scenes_dir = self.output_dir / "scene_videos"
        self.scenes_dir.mkdir(exist_ok=True)
        self.ai_videos_dir = self.output_dir / "ai_videos"
        self.ai_videos_dir.mkdir(exist_ok=True)

        # 加载剧本
        with open(script_path, "r", encoding="utf-8") as f:
            self.script = json.load(f)

        self.title = self.script.get("title", "短剧")
        self.style = self.script.get("style", "anime")
        self.scenes = self.script.get("scenes", [])

        # 画面比例自适应（CLI 参数优先于剧本 JSON）
        aspect_ratio = ratio or self.script.get("aspect_ratio", "9:16")
        if aspect_ratio == "4:3":
            self.WIDTH = self.HORIZONTAL_WIDTH
            self.HEIGHT = self.HORIZONTAL_HEIGHT
        elif aspect_ratio == "16:9":
            self.WIDTH = 1920
            self.HEIGHT = 1080
        elif aspect_ratio == "1:1":
            self.WIDTH = 1080
            self.HEIGHT = 1080
        elif aspect_ratio == "3:4":
            self.WIDTH = 1080
            self.HEIGHT = 1440
        elif aspect_ratio == "21:9":
            self.WIDTH = 2560
            self.HEIGHT = 1080
        else:
            # 默认 9:16 (1080x1920)
            self.WIDTH = 1080
            self.HEIGHT = 1920

        self.aspect_ratio = aspect_ratio

        # korean_manga 画风自动配置
        if self.style == "korean_manga":
            self.script.setdefault("compliance", {
                "enabled": True,
                "text": "内容虚拟演绎 切勿带入现实",
                "position": "right_vertical",
                "color": "#FFFFFF80",
            })
            self.script.setdefault("particles", {
                "enabled": True,
                "type": "sparkle",
                "color": "white_gold",
                "density": 30,
                "speed": 0.5,
            })

    # ─── 主流程 ─────────────────────────────────────────

    def generate_all(self, bgm_path: str = None, output_path: str = "short_drama_output.mp4") -> str:
        """
        完整渲染流程:
          ① AI视频片段生成
          ② TTS配音
          ③ FFmpeg合并视频+音频
          ④ 片头/片尾/转场/BGM
          ⑤ 最终合成
        """
        print(f"\n{'='*60}")
        print(f"  短剧渲染: {self.title}")
        print(f"  场景数: {len(self.scenes)} | 模型: {self.model}")
        print(f"  画风: {self.style}")
        print(f"{'='*60}\n")

        # ① AI视频片段
        video_paths = self._generate_ai_videos()

        # ② TTS配音
        audio_paths = self._generate_tts()

        # ③ 片头片尾
        opening_path = self._generate_opening()
        ending_path = self._generate_ending()

        # ④ 合成
        final = self._compose_final(
            video_paths=video_paths,
            audio_paths=audio_paths,
            opening_path=opening_path,
            ending_path=ending_path,
            bgm_path=bgm_path,
            output_path=output_path,
        )

        print(f"\n{'='*60}")
        print(f"  渲染完成: {final}")
        print(f"{'='*60}")
        return final

    # ─── ① AI视频生成 ─────────────────────────────────

    def _generate_ai_videos(self) -> List[str]:
        """调用AI视频生成API生成动画视频片段"""
        # 通过尝试加载配置来检测 API 是否可用
        try:
            from ai_video_generator import _load_config, _get_api_key
            config = _load_config()
            api_key = _get_api_key(config)
        except (FileNotFoundError, ValueError, ImportError) as e:
            api_key = ""

        if not api_key:
            if self.fallback:
                print("[WARN] API Key 未配置，回退到 ImageGen 模式")
                return self._generate_ai_videos_fallback()
            else:
                raise ValueError("API Key 未配置，且未启用回退模式")

        try:
            import asyncio
            video_paths = asyncio.run(generate_scene_videos(
                script_path=self.script_path,
                output_dir=str(self.ai_videos_dir),
                model=self.model,
                style=self.style,
                max_concurrent=3,
                ratio=self.aspect_ratio,
            ))

            # 检查是否所有场景都成功
            missing = []
            for scene in self.scenes:
                scene_id = scene.get("id", 0)
                expected = self.ai_videos_dir / f"scene_{scene_id:04d}.mp4"
                if not expected.exists():
                    missing.append(scene_id)

            if missing and self.fallback:
                print(f"[WARN] {len(missing)} 场景AI视频生成失败，使用回退模式: {missing}")
                for scene_id in missing:
                    self._generate_fallback_scene(scene_id)

            # 收集所有场景视频路径
            result = []
            for scene in self.scenes:
                scene_id = scene.get("id", 0)
                path = str(self.ai_videos_dir / f"scene_{scene_id:04d}.mp4")
                if os.path.exists(path):
                    result.append(path)
                else:
                    # 回退图片合成视频
                    fb_path = str(self.ai_videos_dir / f"scene_{scene_id:04d}_fallback.mp4")
                    if os.path.exists(fb_path):
                        result.append(fb_path)
                    else:
                        print(f"[ERROR] Scene {scene_id} 没有可用视频，跳过")

            return result

        except Exception as e:
            print(f"[ERROR] AI视频生成异常: {e}")
            if self.fallback:
                print("[WARN] 回退到 ImageGen 模式")
                return self._generate_ai_videos_fallback()
            raise

    def _generate_ai_videos_fallback(self) -> List[str]:
        """
        回退模式: 使用 ImageGen 生成关键帧图片 + Ken Burns 效果制作伪动画
        这不是真正的动画视频，仅在 API 不可用时作为降级方案
        """
        ffmpeg = get_ffmpeg_cmd()
        video_paths = []

        for scene in self.scenes:
            scene_id = scene.get("id", 0)
            image_path = str(self.frames_dir / f"scene_{scene_id:04d}.png")

            # 检查是否已有图片
            if not os.path.exists(image_path):
                # 生成图使用 Pillow 创建占位图
                self._create_placeholder_image(scene, image_path)

            # Ken Burns 效果: 缓慢缩放 + 平移
            output = str(self.ai_videos_dir / f"scene_{scene_id:04d}_fallback.mp4")

            # 计算时长: 基于对白数量
            num_dlg = len(scene.get("dialogues", []))
            narration = scene.get("narration", "")
            duration = max(4, num_dlg * 3 + (3 if narration else 0))

            zoompan = (
                f"zoompan=z='min(zoom+0.001,1.3)':x='iw/2-(iw/zoom/2)'"
                f":y='ih/2-(ih/zoom/2)':d={duration*25}:s={self.WIDTH}x{self.HEIGHT}:fps=25"
            )
            run_cmd([
                ffmpeg, "-y", "-loop", "1", "-i", image_path,
                "-vf", zoompan,
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-t", str(duration), output,
            ], check=False)
            video_paths.append(output)
            print(f"[OK] Fallback video: scene {scene_id} -> {output}")

        return video_paths

    def _generate_fallback_scene(self, scene_id: int):
        """为单个失败场景生成回退视频"""
        scene = next((s for s in self.scenes if s.get("id") == scene_id), None)
        if not scene:
            return

        image_path = str(self.frames_dir / f"scene_{scene_id:04d}.png")
        if not os.path.exists(image_path):
            self._create_placeholder_image(scene, image_path)

        ffmpeg = get_ffmpeg_cmd()
        output = str(self.ai_videos_dir / f"scene_{scene_id:04d}_fallback.mp4")

        num_dlg = len(scene.get("dialogues", []))
        narration = scene.get("narration", "")
        duration = max(4, num_dlg * 3 + (3 if narration else 0))

        zoompan = (
            f"zoompan=z='min(zoom+0.001,1.3)':x='iw/2-(iw/zoom/2)'"
            f":y='ih/2-(ih/zoom/2)':d={duration*25}:s={self.WIDTH}x{self.HEIGHT}:fps=25"
        )
        run_cmd([
            ffmpeg, "-y", "-loop", "1", "-i", image_path,
            "-vf", zoompan,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-t", str(duration), output,
        ], check=False)

    def _create_placeholder_image(self, scene: Dict, output_path: str):
        """创建场景占位图 (当 ImageGen 不可用时)"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new("RGB", (self.WIDTH, self.HEIGHT), "#1a1a2e")
            draw = ImageDraw.Draw(img)

            # 场景ID
            text = f"Scene {scene.get('id', 0)}"
            try:
                font = ImageFont.truetype("arial.ttf", 72)
            except (OSError, IOError):
                font = ImageFont.load_default()

            draw.text((self.WIDTH // 2, self.HEIGHT // 2 - 100), text, fill="white", font=font, anchor="mm")

            background = scene.get("background_prompt", "")
            if background:
                try:
                    small_font = ImageFont.truetype("arial.ttf", 36)
                except (OSError, IOError):
                    small_font = ImageFont.load_default()
                draw.text((self.WIDTH // 2, self.HEIGHT // 2 + 100), background[:50], fill="#aaaaaa", font=small_font, anchor="mm")

            img.save(output_path)
        except ImportError:
            # PIL不可用时，写入最小合法PNG（1x1黑色）
            import struct, zlib
            def _write_minimal_png(path):
                sig = b'\x89PNG\r\n\x1a\n'
                def _chunk(ctype, data):
                    c = ctype + data
                    return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
                ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
                raw = zlib.compress(b'\x00\x00\x00')
                with open(path, 'wb') as f:
                    f.write(sig + _chunk(b'IHDR', ihdr) + _chunk(b'IDAT', raw) + _chunk(b'IEND', b''))
            _write_minimal_png(output_path)

    # ─── ② TTS配音 ─────────────────────────────────────

    def _generate_tts(
        self,
        max_retries: int = 3,
        tts_backend: str = "auto",
    ) -> List[str]:
        """
        生成所有对白的 TTS 音频（v2：四层级回退链 + 预检 + 重试）

        Args:
            max_retries: 每片段最大重试次数（指数退避）
            tts_backend: 指定后端 ("auto"/"edge-tts"/"pyttsx3"/"sapi5"/"silence")
        """
        import asyncio
        from tts_engine import generate_drama_tts, TTSBackend, tts_health_check

        # 自定义回退链
        custom_backends = None
        if tts_backend != "auto":
            if tts_backend in [TTSBackend.EDGE_TTS, TTSBackend.PYTTSX3,
                               TTSBackend.SAPI5, TTSBackend.SILENCE]:
                custom_backends = [tts_backend, TTSBackend.SILENCE]
            else:
                print(f"[WARN] Unknown TTS backend '{tts_backend}', using auto")

        try:
            # 预检
            print("[INFO] TTS pre-flight check...")
            health = asyncio.run(tts_health_check())
            available = [b for b, ok in health.items() if ok]
            if not available or available == [TTSBackend.SILENCE]:
                print("[WARN] No audio TTS backend available! Video will have silence only.")
                print("[TIP] Possible fixes:")
                print("  - edge-tts: pip install edge-tts (may need fresh MS token)")
                print("  - pyttsx3: pip install pyttsx3")
                print("  - sapi5:    Ensure Windows has Chinese voice installed")
            else:
                print(f"[INFO] Available TTS backends: {', '.join(available)}")
                print(f"[INFO] Primary: {available[0]}")

            # 批量生成
            results = asyncio.run(generate_drama_tts(
                script_path=self.script_path,
                output_dir=str(self.audio_dir),
                max_retries=max_retries,
                fast_check=False,  # 已在上面做过预检
            ))

            # 收集音频文件
            audio_files = sorted(str(p) for p in self.audio_dir.glob("tts_*.mp3"))

            # 统计
            total_expected = 0
            for scene in self.scenes:
                if scene.get("narration"):
                    total_expected += 1
                total_expected += len(scene.get("dialogues", []))

            if len(audio_files) < total_expected:
                missing = total_expected - len(audio_files)
                print(f"[WARN] {missing}/{total_expected} TTS segments missing (silence placeholders used)")

            return audio_files

        except Exception as e:
            print(f"[ERROR] TTS generation failed: {e}")
            print(f"[TIP] Run 'python tts_engine.py --health-check' to diagnose")
            # 尝试极端降级：为每个场景生成静音占位
            return self._generate_silence_fallback()

    def _generate_silence_fallback(self) -> List[str]:
        """极端降级：为所有场景生成静音占位音频"""
        from tts_engine import _tts_silence_placeholder
        audio_files = []
        for scene in self.scenes:
            scene_id = scene.get("id", 0)
            # 旁白占位
            if scene.get("narration"):
                path = str(self.audio_dir / f"tts_{scene_id:04d}_narration.mp3")
                _tts_silence_placeholder(path, duration=2.0)
                audio_files.append(path)
            # 对白占位
            for dlg_idx, dlg in enumerate(scene.get("dialogues", [])):
                path = str(self.audio_dir / f"tts_{scene_id:04d}_{dlg_idx:03d}.mp3")
                dur = max(len(dlg.get("text", "")) * 0.15, 1.5)
                _tts_silence_placeholder(path, duration=dur)
                audio_files.append(path)
        print(f"[WARN] Generated {len(audio_files)} silence placeholders")
        return audio_files

    # ─── ③ 片头片尾 ────────────────────────────────────

    def _generate_opening(self) -> Optional[str]:
        """生成片头动画（标题+集数）"""
        ffmpeg = get_ffmpeg_cmd()
        output = str(self.scenes_dir / "opening.mp4")

        # 使用 Pillow 创建片头帧
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new("RGB", (self.WIDTH, self.HEIGHT), "#000000")
            draw = ImageDraw.Draw(img)

            try:
                title_font = ImageFont.truetype("arial.ttf", 80)
                sub_font = ImageFont.truetype("arial.ttf", 48)
            except (OSError, IOError):
                title_font = ImageFont.load_default()
                sub_font = ImageFont.load_default()

            draw.text((self.WIDTH // 2, self.HEIGHT // 2 - 100), self.title, fill="#FFD700", font=title_font, anchor="mm")
            episode = self.script.get("episode", 1)
            draw.text((self.WIDTH // 2, self.HEIGHT // 2 + 50), f"Episode {episode}", fill="#FFFFFF", font=sub_font, anchor="mm")

            frame_path = str(self.scenes_dir / "opening_frame.png")
            img.save(frame_path)

            # 3秒片头
            run_cmd([
                ffmpeg, "-y", "-loop", "1", "-i", frame_path,
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-t", "3", "-r", str(self.FPS), output,
            ], check=False)
            return output if os.path.exists(output) else None
        except Exception as e:
            print(f"[WARN] 片头生成失败: {e}")
            return None

    def _generate_ending(self) -> Optional[str]:
        """生成片尾（"未完待续"）"""
        ffmpeg = get_ffmpeg_cmd()
        output = str(self.scenes_dir / "ending.mp4")

        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new("RGB", (self.WIDTH, self.HEIGHT), "#000000")
            draw = ImageDraw.Draw(img)

            try:
                font = ImageFont.truetype("arial.ttf", 80)
                small_font = ImageFont.truetype("arial.ttf", 48)
            except (OSError, IOError):
                font = ImageFont.load_default()
                small_font = ImageFont.load_default()

            draw.text((self.WIDTH // 2, self.HEIGHT // 2 - 100), "未完待续", fill="#FFFFFF", font=font, anchor="mm")
            draw.text((self.WIDTH // 2, self.HEIGHT // 2 + 50), "To Be Continued...", fill="#888888", font=small_font, anchor="mm")

            frame_path = str(self.scenes_dir / "ending_frame.png")
            img.save(frame_path)

            # 3秒片尾
            run_cmd([
                ffmpeg, "-y", "-loop", "1", "-i", frame_path,
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-t", "3", "-r", str(self.FPS), output,
            ], check=False)
            return output if os.path.exists(output) else None
        except Exception as e:
            print(f"[WARN] 片尾生成失败: {e}")
            return None

    # ─── ④ 合成 ────────────────────────────────────────

    def _compose_final(
        self,
        video_paths: List[str],
        audio_paths: List[str],
        opening_path: Optional[str] = None,
        ending_path: Optional[str] = None,
        bgm_path: Optional[str] = None,
        output_path: str = "short_drama_output.mp4",
    ) -> str:
        """合成最终视频（含字幕烧录）"""
        ffmpeg = get_ffmpeg_cmd()

        # 1. 给每个AI视频片段配音（如果AI视频有原生音频则混合）
        synced_videos = []
        for i, vp in enumerate(video_paths):
            synced = str(self.scenes_dir / f"synced_{i:04d}.mp4")

            # 查找对应的TTS音频
            scene = self.scenes[i] if i < len(self.scenes) else {}
            scene_id = scene.get("id", i)

            # 收集该场景的所有TTS
            scene_audios = sorted(
                str(p) for p in self.audio_dir.glob(f"tts_{scene_id:04d}*.mp3")
            )

            if scene_audios:
                # 合并该场景的TTS音频
                merged_audio = str(self.audio_dir / f"scene_{scene_id:04d}_merged.mp3")
                if len(scene_audios) > 1:
                    # 用 ffmpeg concat 合并音频
                    concat_file = str(self.audio_dir / f"concat_{scene_id:04d}.txt")
                    with open(concat_file, "w", encoding="utf-8") as f:
                        for ap in scene_audios:
                            f.write(f"file '{ap}'\n")
                    _validate_concat_paths(concat_file, str(self.audio_dir))
                    run_cmd([
                        ffmpeg, "-y", "-f", "concat", "-safe", "1",
                        "-i", concat_file, "-c", "copy", merged_audio,
                    ], check=False)
                else:
                    merged_audio = scene_audios[0]

                # 合并视频+音频
                run_cmd([
                    ffmpeg, "-y",
                    "-i", vp, "-i", merged_audio,
                    "-c:v", "libx264", "-c:a", "aac",
                    "-shortest", "-pix_fmt", "yuv420p",
                    "-vf", f"scale={self.WIDTH}:{self.HEIGHT}:force_original_aspect_ratio=decrease,pad={self.WIDTH}:{self.HEIGHT}:(ow-iw)/2:(oh-ih)/2",
                    synced,
                ], check=False)
            else:
                # 无TTS音频，直接转码
                run_cmd([
                    ffmpeg, "-y", "-i", vp,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an",
                    "-vf", f"scale={self.WIDTH}:{self.HEIGHT}:force_original_aspect_ratio=decrease,pad={self.WIDTH}:{self.HEIGHT}:(ow-iw)/2:(oh-ih)/2",
                    synced,
                ], check=False)

            if os.path.exists(synced):
                synced_videos.append(synced)
            else:
                print(f"[WARN] Scene {i} sync failed, using original")
                synced_videos.append(vp)

        # 2. 拼接: 片头 + 场景 + 片尾
        all_videos = []
        if opening_path and os.path.exists(opening_path):
            all_videos.append(opening_path)
        all_videos.extend(synced_videos)
        if ending_path and os.path.exists(ending_path):
            all_videos.append(ending_path)

        concat_list = self.output_dir / "concat_list.txt"
        with open(concat_list, "w", encoding="utf-8") as f:
            for vp in all_videos:
                f.write(f"file '{vp}'\n")

        _validate_concat_paths(str(concat_list), str(self.output_dir))

        merged = str(self.output_dir / "merged_no_bgm.mp4")
        run_cmd([
            ffmpeg, "-y", "-f", "concat", "-safe", "1",
            "-i", str(concat_list),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-r", str(self.FPS), merged,
        ])

        # 3. 生成 ASS 字幕并烧录
        subtitle_style = self.script.get("subtitle_style", self.style)
        subtitle_mode = self.script.get("subtitle_mode", "subtitle")
        ass_path = str(self.output_dir / "subtitles.ss")

        generate_ass_subtitle(
            script_path=self.script_path,
            output_path=ass_path,
            video_width=self.WIDTH,
            video_height=self.HEIGHT,
            base_font_size=44,
            style=subtitle_style,
            mode=subtitle_mode,
        )

        # 构建视频滤镜链
        vf_parts = []
        # 粒子特效叠加（korean_manga 画风的 sparkle 效果）
        particles = self.script.get("particles", {})
        if particles.get("enabled", False) and self.style == "korean_manga":
            p_type = particles.get("type", "sparkle")
            p_density = particles.get("density", 30)
            # 使用FFmpeg的随机星点叠加（drawbox模拟sparkle粒子）
            # 实际sparkle通过overlay静态粒子图实现更自然
            sparkle_img = str(self.output_dir / "sparkle_overlay.png")
            self._create_sparkle_overlay(sparkle_img, p_density)
            if os.path.exists(sparkle_img):
                # 先不烧录粒子，放在最终合成阶段
                pass  # 粒子将在最终步骤overlay

        # ASS字幕烧录
        ass_path_escaped = ass_path.replace("\\", "/").replace(":", "\\:")
        vf_parts.append(f"ass={ass_path_escaped}")
        vf_chain = ",".join(vf_parts)

        # 烧录字幕到视频
        burnt = str(self.output_dir / "merged_with_sub.mp4")

        result = run_cmd([
            ffmpeg, "-y", "-i", merged,
            "-vf", vf_chain,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "copy", burnt,
        ], check=False)

        # 如果 ASS 烧录失败（编码/路径问题），回退到简单 drawtext
        if not os.path.exists(burnt):
            print("[WARN] ASS subtitle burn failed, video saved without subtitles")
            burnt = merged

        # 4. 添加BGM
        if bgm_path and os.path.exists(bgm_path):
            filter_complex = (
                "[1:a]volume=0.3,afade=t=in:st=0:d=2,afade=t=out:st=main_dur-3:d=3[bgm];"
                "[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )
            run_cmd([
                ffmpeg, "-y",
                "-i", burnt, "-i", bgm_path,
                "-filter_complex", filter_complex,
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "copy", "-c:a", "aac",
                "-shortest", output_path,
            ])
        else:
            shutil.copy2(burnt, output_path)

        # 4. 粒子叠加（korean_manga sparkle）
        sparkle_img = str(self.output_dir / "sparkle_overlay.png")
        if os.path.exists(sparkle_img) and self.style == "korean_manga":
            sparkle_burnt = str(self.output_dir / "with_sparkle.mp4")
            run_cmd([
                ffmpeg, "-y", "-i", output_path if os.path.exists(output_path) else burnt,
                "-i", sparkle_img,
                "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto[vout]",
                "-map", "[vout]", "-map", "0:a?",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "copy", sparkle_burnt,
            ], check=False)
            if os.path.exists(sparkle_burnt):
                shutil.move(sparkle_burnt, output_path)

        print(f"[OK] Short drama video saved: {output_path}")
        return output_path

    # ─── 生成视频提示词 (供外部调用) ──────────────────

    def generate_scene_video_prompts(self) -> List[Dict]:
        """为每个场景生成AI视频提示词（含情绪推断动作）"""
        prompts = []
        for scene in self.scenes:
            scene_id = scene.get("id", 0)
            background = scene.get("background_prompt", "")
            characters = scene.get("characters", [])
            action = scene.get("action", "static")
            ambient = scene.get("ambient", "")

            # 从对白中推断场景主导情绪
            emotion = ""
            dialogues = scene.get("dialogues", [])
            if dialogues:
                last_emotion = dialogues[-1].get("emotion", "")
                if last_emotion:
                    emotion = last_emotion

            prompt = build_video_prompt(
                background=background,
                characters=characters,
                action=action,
                style=self.style,
                emotion=emotion,
                ambient=ambient,
            )

            prompts.append({
                "scene_id": scene_id,
                "prompt": prompt,
                "duration": max(4, len(scene.get("dialogues", [])) * 3 +
                                (3 if scene.get("narration") else 0)),
            })

        return prompts

    # ─── Sparkle 粒子叠加图 ─────────────────────────────

    def _create_sparkle_overlay(self, output_path: str, density: int = 30):
        """创建星点粒子叠加透明PNG（korean_manga sparkle效果）"""
        try:
            from PIL import Image, ImageDraw
            import random
            random.seed(42)  # 固定种子保证可复现

            img = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            for _ in range(density * 5):
                x = random.randint(0, self.WIDTH)
                y = random.randint(0, self.HEIGHT)
                # 星点大小1-3px
                size = random.randint(1, 3)
                # 白金色，透明度40-120
                alpha = random.randint(40, 120)
                # 偏暖色
                r = random.randint(255, 255)
                g = random.randint(240, 255)
                b = random.randint(180, 220)
                color = (r, g, b, alpha)
                draw.ellipse([x, y, x + size, y + size], fill=color)

            # 边缘云雾辉光
            for side in ["left", "right"]:
                for i in range(5):
                    if side == "left":
                        x = random.randint(0, int(self.WIDTH * 0.08))
                    else:
                        x = random.randint(int(self.WIDTH * 0.92), self.WIDTH)
                    y = random.randint(0, self.HEIGHT)
                    rx = random.randint(30, 80)
                    ry = random.randint(40, 100)
                    alpha = random.randint(15, 40)
                    draw.ellipse([x - rx, y - ry, x + rx, y + ry],
                                fill=(255, 255, 240, alpha))

            img.save(output_path)
            print(f"[OK] Sparkle overlay created: {output_path}")
        except ImportError:
            print("[WARN] PIL not available, skipping sparkle overlay")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="短剧动画渲染器 (v2 — AI视频驱动)")
    parser.add_argument("--script", required=True, help="剧本JSON路径")
    parser.add_argument("--output-dir", default=".temp/short_drama")
    # 动态获取可用模型列表
    available = get_available_models()
    model_choices = list(available.keys()) if available else ["pro", "lite"]
    parser.add_argument("--model", default=model_choices[0], choices=model_choices,
                        help="AI视频模型别名")
    parser.add_argument("--no-fallback", action="store_true",
                        help="API不可用时不回退到ImageGen模式")
    parser.add_argument("--action", choices=["prompts", "videos", "compose", "all"], default="all")
    parser.add_argument("--ratio", default=None,
                        choices=["9:16", "16:9", "4:3", "1:1", "3:4", "21:9"],
                        help="画面宽高比覆盖 (默认读剧本JSON，可选 16:9/4:3 等横屏)")
    parser.add_argument("--bgm", default=None, help="BGM音频路径")
    parser.add_argument("--output", default="short_drama_output.mp4", help="最终视频输出路径")

    args = parser.parse_args()
    renderer = ShortDramaRenderer(
        args.script, args.output_dir,
        model=args.model,
        fallback=not args.no_fallback,
        ratio=args.ratio,
    )

    if args.action == "prompts":
        prompts = renderer.generate_scene_video_prompts()
        prompts_path = Path(args.output_dir) / "video_prompts.json"
        with open(prompts_path, "w", encoding="utf-8") as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)
        print(f"[OK] Generated {len(prompts)} video prompts -> {prompts_path}")

    elif args.action == "videos":
        renderer._generate_ai_videos()

    elif args.action == "compose":
        video_paths = sorted(str(p) for p in renderer.ai_videos_dir.glob("scene_*.mp4"))
        renderer._compose_final(
            video_paths=video_paths,
            audio_paths=[],
            bgm_path=args.bgm,
            output_path=args.output,
        )

    elif args.action == "all":
        renderer.generate_all(bgm_path=args.bgm, output_path=args.output)


if __name__ == "__main__":
    main()
