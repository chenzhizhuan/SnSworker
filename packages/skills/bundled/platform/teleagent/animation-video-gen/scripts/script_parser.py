#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频脚本解析器
将各种格式的视频脚本/小说文本/分镜脚本转化为标准短剧剧本JSON

支持的输入格式:
  1. 纯文本脚本: 用空行分隔场景的文本
  2. 对话格式: "角色名：对白内容" 的格式
  3. 分镜脚本: 含镜号/景别/内容的表格文本
  4. 小说章节: 纯叙事文本，自动拆分为场景和对白
  5. Markdown脚本: # 标题分隔场景
  6. SRT字幕文件: 字幕格式
  7. 标准剧本格式: 场景标题 + 角色名 + 对白

用法:
  python script_parser.py --input script.txt --format auto --output drama.json
  python script_parser.py --input chapter1.txt --format novel --output drama.json
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================
# 解析器基类和实现
# ============================================

class BaseParser:
    """脚本解析器基类"""

    def __init__(self, text: str, metadata: Optional[Dict] = None):
        self.text = text
        self.metadata = metadata or {}
        self.lines = text.strip().split("\n")

    def parse(self) -> Dict:
        raise NotImplementedError


class DialogueFormatParser(BaseParser):
    """
    解析对话格式脚本
    格式: 角色名：对白内容 / 角色名: 对白内容
    用空行或 [场景: xxx] 标记场景切换
    """

    def parse(self) -> Dict:
        scenes = []
        current_scene = {"id": 0, "background_prompt": "", "characters": [], "dialogues": [], "narration": "", "transition": "fade_black"}
        all_characters = set()

        for line in self.lines:
            line = line.strip()
            if not line:
                continue

            # 场景标记
            scene_match = re.match(r'\[场景[：:](.+?)\]', line)
            if scene_match:
                # 保存当前场景
                if current_scene["dialogues"] or current_scene["narration"]:
                    current_scene["id"] = len(scenes) + 1
                    scenes.append(current_scene)
                current_scene = {
                    "id": 0,
                    "background_prompt": scene_match.group(1).strip(),
                    "characters": [],
                    "dialogues": [],
                    "narration": "",
                    "transition": "fade_black",
                }
                continue

            # 旁白标记
            narration_match = re.match(r'（旁白[：:](.+?)）|旁白[：:](.+)', line)
            if narration_match:
                narration_text = narration_match.group(1) or narration_match.group(2)
                current_scene["narration"] = narration_text.strip()
                continue

            # 对话格式: 角色名：对白 / 角色名: 对白
            dialogue_match = re.match(r'(.+?)[：:](.+)', line)
            if dialogue_match:
                speaker = dialogue_match.group(1).strip()
                text = dialogue_match.group(2).strip()
                all_characters.add(speaker)
                current_scene["dialogues"].append({
                    "speaker": speaker,
                    "text": text,
                    "emotion": "",
                    "mode": "subtitle",
                })
                continue

            # 纯文本作为旁白
            current_scene["narration"] = (current_scene["narration"] + " " + line).strip()

        # 保存最后一个场景
        if current_scene["dialogues"] or current_scene["narration"]:
            current_scene["id"] = len(scenes) + 1
            scenes.append(current_scene)

        return {
            "title": self.metadata.get("title", "解析生成的短剧"),
            "style": "anime",
            "aspect_ratio": "9:16",
            "resolution": "1080x1920",
            "source_format": "dialogue_format",
            "scenes": scenes,
        }


class MarkdownScriptParser(BaseParser):
    """
    解析Markdown格式脚本
    # 标题 → 场景
    ## 子标题 → 场景分区
    **角色名**: 对白
    > 旁白
    """

    def parse(self) -> Dict:
        scenes = []
        current_scene = None
        all_characters = set()

        for line in self.lines:
            stripped = line.strip()

            # H1/H2 = 新场景
            h_match = re.match(r'^#{1,3}\s+(.+)', stripped)
            if h_match:
                if current_scene and (current_scene["dialogues"] or current_scene["narration"]):
                    current_scene["id"] = len(scenes) + 1
                    scenes.append(current_scene)
                current_scene = {
                    "id": 0,
                    "background_prompt": h_match.group(1).strip(),
                    "characters": [],
                    "dialogues": [],
                    "narration": "",
                    "transition": "fade_black",
                }
                continue

            if current_scene is None:
                current_scene = {
                    "id": 0,
                    "background_prompt": "默认场景",
                    "characters": [],
                    "dialogues": [],
                    "narration": "",
                    "transition": "fade_black",
                }

            # 旁白 (blockquote)
            if stripped.startswith(">"):
                narration = stripped.lstrip(">").strip()
                current_scene["narration"] = (current_scene["narration"] + " " + narration).strip()
                continue

            # 加粗角色名: 对白
            bold_match = re.match(r'\*\*(.+?)\*\*[：:]\s*(.+)', stripped)
            if bold_match:
                speaker = bold_match.group(1).strip()
                text = bold_match.group(2).strip()
                all_characters.add(speaker)
                current_scene["dialogues"].append({
                    "speaker": speaker,
                    "text": text,
                    "emotion": "",
                    "mode": "subtitle",
                })
                continue

            # 普通对话
            dlg_match = re.match(r'(.+?)[：:](.+)', stripped)
            if dlg_match and not stripped.startswith("-") and not stripped.startswith("*"):
                speaker = dlg_match.group(1).strip()
                text = dlg_match.group(2).strip()
                if len(speaker) <= 6:  # 角色名通常很短
                    all_characters.add(speaker)
                    current_scene["dialogues"].append({
                        "speaker": speaker,
                        "text": text,
                        "emotion": "",
                        "mode": "subtitle",
                    })
                    continue

        if current_scene and (current_scene["dialogues"] or current_scene["narration"]):
            current_scene["id"] = len(scenes) + 1
            scenes.append(current_scene)

        return {
            "title": self.metadata.get("title", "解析生成的短剧"),
            "style": "anime",
            "aspect_ratio": "9:16",
            "resolution": "1080x1920",
            "source_format": "markdown",
            "scenes": scenes,
        }


class NovelParser(BaseParser):
    """
    解析小说/纯叙事文本
    自动识别对话（用引号""包裹）和叙述文字
    按段落/对话密度自动拆分场景
    """

    def parse(self) -> Dict:
        # 1. 提取对话和叙述
        segments = []  # [(type, content, speaker?), ...]

        # 匹配中文引号对话
        pattern = r'「(.+?)」|"(.+?)"|"(.+?)"'
        last_end = 0

        for match in re.finditer(pattern, self.text):
            # 匹配之前的叙述文字
            before = self.text[last_end:match.start()].strip()
            if before:
                segments.append(("narration", before, None))

            # 对话内容
            dialogue = match.group(1) or match.group(2) or match.group(3)
            # 尝试提取说话人（"XX道："格式）
            speaker = ""
            if before:
                speaker_match = re.search(r'(.{1,4})[说道喊叫问答咆哮吼笑哭叹][道喊叫着]?\s*[：:]?$', before)
                if speaker_match:
                    speaker = speaker_match.group(1).strip()

            segments.append(("dialogue", dialogue, speaker if speaker else "角色"))
            last_end = match.end()

        # 最后的叙述
        remaining = self.text[last_end:].strip()
        if remaining:
            segments.append(("narration", remaining, None))

        # 2. 按段落密度拆分场景
        scenes = self._split_into_scenes(segments)

        return {
            "title": self.metadata.get("title", "小说改编短剧"),
            "style": "anime",
            "aspect_ratio": "9:16",
            "resolution": "1080x1920",
            "source_format": "novel",
            "scenes": scenes,
        }

    def _split_into_scenes(self, segments: List[Tuple]) -> List[Dict]:
        """按段落数量自动拆分为场景"""
        scenes = []
        current_dialogues = []
        current_narration_parts = []
        dialogue_count = 0

        for seg_type, content, speaker in segments:
            if seg_type == "dialogue":
                current_dialogues.append({
                    "speaker": speaker or "角色",
                    "text": content,
                    "emotion": "",
                    "mode": "subtitle",
                })
                dialogue_count += 1
            elif seg_type == "narration":
                current_narration_parts.append(content)

            # 每4-6句对白或叙述段触发场景切换
            if dialogue_count >= 4 or len(current_narration_parts) >= 3:
                scene = {
                    "id": len(scenes) + 1,
                    "background_prompt": "[待填充] 根据叙述内容推断",
                    "characters": [],
                    "dialogues": current_dialogues,
                    "narration": " ".join(current_narration_parts)[:100],  # 截取前100字
                    "transition": "fade_black",
                }
                scenes.append(scene)
                current_dialogues = []
                current_narration_parts = []
                dialogue_count = 0

        # 剩余内容
        if current_dialogues or current_narration_parts:
            scene = {
                "id": len(scenes) + 1,
                "background_prompt": "[待填充] 根据叙述内容推断",
                "characters": [],
                "dialogues": current_dialogues,
                "narration": " ".join(current_narration_parts)[:100],
                "transition": "fade_black",
            }
            scenes.append(scene)

        return scenes


class SrtParser(BaseParser):
    """解析SRT字幕文件"""

    def parse(self) -> Dict:
        # SRT格式: 序号 → 时间轴 → 字幕文本 → 空行
        entries = re.split(r'\n\n+', self.text.strip())
        dialogues = []

        for entry in entries:
            lines = entry.strip().split("\n")
            if len(lines) >= 3:
                text = " ".join(lines[2:]).strip()
                if text:
                    dialogues.append({
                        "speaker": "角色",
                        "text": text,
                        "emotion": "",
                        "mode": "subtitle",
                    })

        # 每5-8条字幕为一个场景
        scenes = []
        for i in range(0, len(dialogues), 5):
            chunk = dialogues[i:i+5]
            scenes.append({
                "id": len(scenes) + 1,
                "background_prompt": "[待填充]",
                "characters": [],
                "dialogues": chunk,
                "narration": "",
                "transition": "fade_black",
            })

        return {
            "title": self.metadata.get("title", "字幕转换短剧"),
            "style": "anime",
            "aspect_ratio": "9:16",
            "resolution": "1080x1920",
            "source_format": "srt",
            "scenes": scenes,
        }


class StoryboardParser(BaseParser):
    """
    解析分镜脚本
    格式: 镜号 | 景别 | 时长 | 画面内容 | 旁白/对白 | 音效
    """

    def parse(self) -> Dict:
        scenes = []

        for line in self.lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # 尝试竖线分隔
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
            elif "\t" in line:
                parts = [p.strip() for p in line.split("\t")]
            else:
                continue

            # 至少需要画面内容和对白
            if len(parts) < 4:
                continue

            scene = {
                "id": len(scenes) + 1,
                "background_prompt": parts[3] if len(parts) > 3 else "",
                "characters": [],
                "dialogues": [],
                "narration": "",
                "transition": "fade_black",
                "notes": "",
            }

            # 旁白/对白在parts[4]或其他位置
            if len(parts) > 4 and parts[4]:
                dialogue_text = parts[4]
                # 检测是否是角色对白
                dlg_match = re.match(r'(.+?)[：:](.+)', dialogue_text)
                if dlg_match:
                    scene["dialogues"].append({
                        "speaker": dlg_match.group(1),
                        "text": dlg_match.group(2),
                        "emotion": "",
                        "mode": "subtitle",
                    })
                else:
                    scene["narration"] = dialogue_text

            # 备注信息
            if len(parts) > 5:
                scene["notes"] = parts[5]

            scenes.append(scene)

        return {
            "title": self.metadata.get("title", "分镜脚本转换短剧"),
            "style": "anime",
            "aspect_ratio": "9:16",
            "resolution": "1080x1920",
            "source_format": "storyboard",
            "scenes": scenes,
        }


# ============================================
# 自动格式检测
# ============================================

def detect_format(text: str) -> str:
    """自动检测输入文本格式"""
    lines = text.strip().split("\n")

    # SRT: 以数字序号开头，有时间轴
    if re.search(r'\d{2}:\d{2}:\d{2}', text):
        return "srt"

    # Markdown: 有 # 标题
    if any(line.strip().startswith("#") for line in lines):
        return "markdown"

    # 分镜脚本: 有 | 或 tab 分隔，且有镜号
    if any("|" in line for line in lines[:5]) or any("\t" in line for line in lines[:5]):
        return "storyboard"

    # 对话格式: 大量"角色名：对白"
    dialogue_count = sum(1 for line in lines if re.match(r'.+?[：:]', line.strip()))
    if dialogue_count > len(lines) * 0.4:
        return "dialogue"

    # 场景标记
    if re.search(r'\[场景[：:]', text):
        return "dialogue"

    # 小说: 大量引号对话
    quote_count = text.count("「") + text.count('"') + text.count('"')
    if quote_count > 3:
        return "novel"

    # 默认按小说处理
    return "novel"


# ============================================
# 主入口
# ============================================

PARSER_MAP = {
    "dialogue": DialogueFormatParser,
    "markdown": MarkdownScriptParser,
    "novel": NovelParser,
    "srt": SrtParser,
    "storyboard": StoryboardParser,
}


# 画面比例 → 分辨率映射
RATIO_RESOLUTION_MAP = {
    "9:16": "1080x1920",
    "16:9": "1920x1080",
    "4:3": "1440x1080",
    "1:1": "1080x1080",
    "3:4": "1080x1440",
    "21:9": "2560x1080",
}


def parse_script(input_path: str, fmt: str = "auto", title: str = "", output_path: str = "drama_script.json", ratio: str = "9:16") -> Dict:
    """
    解析脚本文件生成短剧剧本JSON

    Args:
        input_path: 输入文件路径
        fmt: 格式 (auto/dialogue/markdown/novel/srt/storyboard)
        title: 短剧标题
        output_path: 输出路径
        ratio: 画面宽高比 (9:16/16:9/4:3/1:1/3:4/21:9)，默认 9:16 竖屏
    """
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    metadata = {"title": title}
    if fmt == "auto":
        fmt = detect_format(text)
        print(f"[INFO] 自动检测格式: {fmt}")

    parser_class = PARSER_MAP.get(fmt, NovelParser)
    parser = parser_class(text, metadata)
    script = parser.parse()

    # 自动补全 voice_mapping
    all_speakers = set()
    for scene in script.get("scenes", []):
        for dlg in scene.get("dialogues", []):
            all_speakers.add(dlg["speaker"])

    voice_mapping = {"旁白": "zh-CN-YunyangNeural"}
    male_voices = ["zh-CN-YunjianNeural", "zh-CN-YunxiNeural"]
    female_voices = ["zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural"]
    mi, fi = 0, 0

    for speaker in all_speakers:
        # 简单规则：名中含"女/姐/妹/姑/太太/婆/嫂"的分配女声
        female_indicators = ["女", "姐", "妹", "姑", "婆", "嫂", "太太", "苏", "晚", "晴", "琳", "梅", "雪", "月", "花"]
        is_female = any(kw in speaker for kw in female_indicators)
        if is_female:
            voice_mapping[speaker] = female_voices[fi % len(female_voices)]
            fi += 1
        else:
            voice_mapping[speaker] = male_voices[mi % len(male_voices)]
            mi += 1

    script["voice_mapping"] = voice_mapping

    # 覆盖画面比例和分辨率（使用 CLI 参数）
    script["aspect_ratio"] = ratio
    script["resolution"] = RATIO_RESOLUTION_MAP.get(ratio, "1080x1920")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    print(f"[OK] 脚本已解析: {output_path}")
    print(f"     格式: {fmt}")
    print(f"     场景数: {len(script['scenes'])}")
    print(f"     角色: {', '.join(all_speakers)}")

    return script


def main():
    import argparse
    parser = argparse.ArgumentParser(description="视频脚本解析器")
    parser.add_argument("--input", required=True, help="输入脚本文件路径")
    parser.add_argument("--format", default="auto", choices=["auto", "dialogue", "markdown", "novel", "srt", "storyboard"])
    parser.add_argument("--title", default="", help="短剧标题")
    parser.add_argument("--ratio", default="9:16",
                        choices=["9:16", "16:9", "4:3", "1:1", "3:4", "21:9"],
                        help="画面宽高比 (默认: 9:16 竷屏，可选 16:9/4:3 等横屏)")
    parser.add_argument("--output", default="drama_script.json", help="输出路径")

    args = parser.parse_args()
    parse_script(args.input, args.format, args.title, args.output, args.ratio)


if __name__ == "__main__":
    main()
