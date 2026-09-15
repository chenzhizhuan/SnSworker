#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剧本解析：分镜（.txt/.md）与人物设定（.json）解析为分镜结构 shots.json，
供 tts.py 与 render_video.py 消费。

剧本格式（一行一个元素，空行分隔）：
  # 标题
  【场景】场景描述          （如 【场景：城市夜景】）
  角色名：台词              （如 林小满：我真的要走了）
  旁白：文字                （不显示说话人前缀）
  字幕：文字                （只出字幕，不配音）
  其他文本                  （动作/描述，配音为旁白并显示字幕）

人物设定 JSON（可选）：
  {"characters": {"林小满": {"voice": "zh-CN-XiaoxiaoNeural", "desc": "..."}}}

用法：
  python parse_script.py 剧本.txt [--characters 人物.json] [--out 输出目录]
"""
import argparse
import json
import re
import sys
from pathlib import Path

from common import ensure_out, json_dump, work_dir

# AIGC 水印注入的不可见字符（​ 零宽空格、‍ 零宽连字符等）
INVISIBLE = re.compile(
    r"[\u200b-\u200f\u2060-\u206f\ufeff\u00ad\u202a-\u202e\u00a0\u3000]"
)
# 水印明文标记行（如“AI生成”等单独成行）
WATERMARK_LINE = re.compile(r"^(AI生成|AIGC|AI[\s_]*Generated|AI Generated Content)$", re.I)


def clean_invisible(text: str) -> str:
    """移除水印/不可见字符，保留正常文本"""
    text = INVISIBLE.sub("", text)
    lines = [
        ln for ln in text.splitlines()
        if ln.strip() and not WATERMARK_LINE.match(ln.strip())
    ]
    return "\n".join(lines)


def load_characters(path):
    """读取人物设定 JSON，无则返回默认旁白设定"""
    if path and Path(path).exists():
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data.get("characters", data) if isinstance(data, dict) else {}
    return {}


def parse_lines(text):
    """把剧本文本拆成元素列表 [(type, ...)]"""
    items = []
    skip_section = False  # 是否处于 "## 人物" 等元数据段落
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        # 标题/章节标记
        if line.startswith("#"):
            # ## 人物 / ## 角色 / 人物设定 等段落整体跳过
            if re.match(r"^#{2,}\s*(人物|角色|演员|设定|cast|characters|info|配置)\s*$", line, re.I):
                skip_section = True
                continue
            skip_section = False
            if re.match(r"^#\s+.+", line):
                continue  # 一级标题（剧名）
            continue
        if skip_section:
            continue
        # 场景行：【场景】xxx 或 【场景：xxx】或 【xxx】
        m = re.match(r"^【场景(?:[：:]\s*)?(.+?)】\s*$", line)
        if m:
            items.append(("scene", m.group(1).strip()))
            continue
        m = re.match(r"^【(.+?)】\s*$", line)
        if m and len(m.group(1)) <= 14:
            items.append(("scene", m.group(1).strip()))
            continue
        # 旁白/字幕标签
        m = re.match(r"^(旁白|字幕|画外音)[：:]\s*(.+)$", line)
        if m:
            items.append(("line", m.group(1), m.group(2).strip()))
            continue
        # 角色：台词
        m = re.match(r"^([^：:]{1,12})[：:]\s*(.+)$", line)
        if m:
            items.append(("line", m.group(1).strip(), m.group(2).strip()))
            continue
        # 动作/描述
        line = line.lstrip("#>-* ").strip()
        if line:
            items.append(("action", line))
    return items


def split_by_scene(items):
    """按场景行分组"""
    groups, cur = [], None
    for it in items:
        if it[0] == "scene":
            cur = {"scene": it[1], "blocks": []}
            groups.append(cur)
        else:
            if cur is None:
                cur = {"scene": "", "blocks": []}
                groups.append(cur)
            cur["blocks"].append(it)
    return groups


def build_scene_prompt(scene: str, speakers: list, characters: dict) -> str:
    """为场景生成插画提示词（英文，适配文生图模型）"""
    scene_en = {
        "深夜客厅": "modern living room at night, warm dim lighting",
        "老宅厨房": "old chinese house kitchen, warm morning light, wok and vegetables",
        "老宅客厅": "old chinese house living room, family photos on wall, cold atmosphere",
        "卧室门口": "bedroom doorway, tense atmosphere, dim night light",
        "雨夜街头": "rainy city street at night, neon reflections on wet road",
        "清晨江边": "riverside at dawn, soft morning light, gentle breeze",
        "清晨卧室": "bedroom at early morning, soft sunlight through window",
        "老公客厅": "living room at night, old photo album on coffee table",
        "深夜写字楼天台": "office rooftop at night, city skyline lights",
        "城市夜景": "city night view, blue tones",
    }
    env = scene_en.get(scene, f"{scene}, cinematic short drama still")
    people = []
    for sp in speakers:
        ch = characters.get(sp, {})
        g = ch.get("gender", "女")
        age = ch.get("age", "35岁" if g == "女" else "40岁")
        people.append(f"a {age} {g} in chinese style, {ch.get('desc', '')}")
    ppl = ", ".join(people) if people else "two people talking"
    return (f"vertical 9:16 short drama still, {env}, {ppl}, emotional conflict scene, "
            "cinematic lighting, high quality illustration, chinese web drama style")


def build_shots(groups, characters):
    """把分组转成 shots 列表；同时为每个场景生成插画提示词"""
    shots = []
    scenes = []
    idx = 0
    scene_idx = 0
    for g in groups:
        scene = g["scene"] or "城市夜景"
        blocks = g["blocks"] or [("action", "（转场）")]
        scene_idx += 1
        speakers = [b[1] for b in blocks if b[0] == "line" and b[1] not in ("旁白", "字幕")]
        scenes.append({
            "id": scene_idx,
            "name": scene,
            "prompt": build_scene_prompt(scene, speakers, characters),
            "speakers": speakers,
        })
        for blk in blocks:
            idx += 1
            if blk[0] == "line":
                who, words = blk[1], blk[2]
                ch = characters.get(who, {})
                voice = ch.get("voice", "zh-CN-XiaoxiaoNeural")
                subtitle = words if who in ("旁白", "字幕") else f"{who}：{words}"
                shot = {
                    "id": idx,
                    "scene": scene,
                    "speaker": who,
                    "dialogue": words,
                    "voice": voice,
                    "subtitle": subtitle,
                    "kind": "narration" if who == "旁白" else "dialogue",
                    "mood": "calm",
                }
            else:
                words = blk[1]
                ch = characters.get("旁白", {})
                shot = {
                    "id": idx,
                    "scene": scene,
                    "speaker": "旁白",
                    "dialogue": words,
                    "voice": ch.get("voice", "zh-CN-YunxiNeural"),
                    "subtitle": words,
                    "kind": "narration",
                    "mood": "calm",
                }
            shots.append(shot)
    return shots, scenes


def main():
    ap = argparse.ArgumentParser(description="剧本 -> 分镜")
    ap.add_argument("script", help="剧本文件路径（.txt/.md）")
    ap.add_argument("--characters", help="人物设定 JSON 路径（可选）")
    ap.add_argument("--out", help="输出目录（默认 ./short-drama-output）")
    args = ap.parse_args()

    src = Path(args.script)
    if not src.exists():
        print(f"错误：剧本文件不存在 {src}", file=sys.stderr)
        return 1

    out = ensure_out(Path(args.out) if args.out else Path.cwd() / "short-drama-output")
    wdir = work_dir(out)
    characters = load_characters(args.characters)

    text = clean_invisible(src.read_text(encoding="utf-8-sig"))
    items = parse_lines(text)
    if not items:
        print("错误：剧本为空或无法解析", file=sys.stderr)
        return 1
    groups = split_by_scene(items)
    shots, scenes = build_shots(groups, characters)

    title = src.stem
    result = {
        "title": title,
        "characters": characters,
        "shots": shots,
        "scenes": scenes,
        "config": {"fps": 30, "size": [1080, 1920]},
    }
    out_json = wdir / "shots.json"
    json_dump(result, out_json)
    print(f"解析完成：{len(shots)} 个分镜、{len(scenes)} 个场景 -> {out_json}")
    for sc in scenes:
        print(f"  场景 {sc['id']}: {sc['name']}  出场:{'/'.join(sc['speakers']) or '—'}")
    for s in shots[:6]:
        print(f"  [{s['id']:>3}] {s['kind']:<9} {s['scene'][:12]:<12} {s['dialogue'][:16]}")
    if len(shots) > 6:
        print(f"  ... 共 {len(shots)} 个分镜")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())