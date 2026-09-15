#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剧本分镜导演 — 半自动视频创作流水线

将用户主题/文案拆解为分镜剧本，每个镜头包含:
  - 画面描述 (用于文生图/文生视频)
  - 动态描述 (用于图生视频)
  - 时长、参考要求
  - 过渡效果

支持 5 种分镜模板:
  - narrative  : 叙事型 (品牌故事、人物传记)
  - promotion  : 推宣型 (产品推广、活动宣传)
  - explainer  : 讲解型 (知识科普、技术讲解)
  - showcase   : 展示型 (产品展示、作品集)
  - emotional  : 情感型 (公益宣传、节日祝福)

输出结构化 JSON，LLM 据此逐步引导用户确认后生成。

用法:
  python script_director.py plan --topic "人工智能的发展历程" [选项]
  python script_director.py plan --script article.txt [选项]
  python script_director.py export --project project.json -o output_dir
"""

import argparse
import json
import sys
import os
from datetime import datetime


# ─── 分镜结构模板 ─────────────────────────────────────

SCENE_TEMPLATES = {
    "narrative": {
        "name": "叙事型",
        "structure": ["开场引入", "背景铺垫", "核心展开", "高潮呈现", "总结升华"],
        "desc": "适合: 品牌故事、产品溯源、人物传记"
    },
    "promotion": {
        "name": "推宣型",
        "structure": ["痛点共鸣", "方案揭示", "功能展示", "效果证明", "行动号召"],
        "desc": "适合: 产品推广、活动宣传、课程招生"
    },
    "explainer": {
        "name": "讲解型",
        "structure": ["问题提出", "概念解释", "原理拆解", "案例演示", "要点总结"],
        "desc": "适合: 知识科普、技术讲解、流程说明"
    },
    "showcase": {
        "name": "展示型",
        "structure": ["全景概览", "细节特写", "对比突出", "场景应用", "品质保证"],
        "desc": "适合: 产品展示、作品集、案例集锦"
    },
    "emotional": {
        "name": "情感型",
        "structure": ["氛围营造", "情感连接", "故事深化", "共鸣高潮", "温暖收束"],
        "desc": "适合: 公益宣传、节日祝福、品牌情感"
    },
}

# ─── 视觉风格映射 ─────────────────────────────────────

STYLE_MAP = {
    "business": "商务专业，蓝灰配色，数据可视化元素",
    "tech": "科技未来，深色背景，霓虹光效，粒子流动",
    "warm": "温暖柔和，暖色调，自然光影",
    "creative": "创意跳脱，多彩配色，几何抽象",
    "minimal": "极简现代，大量留白，精致排版",
    "anime": "日系动画风格，赛璐璐上色，鲜艳色彩，角色表情丰富",
    "realistic": "写实电影感，自然光影，浅景深",
    "qcomic": "国漫风格，粗线条，夸张表情，动态构图",
}


# ─── 分镜计划生成 ─────────────────────────────────────

# 画面比例 → 分辨率映射
RATIO_RESOLUTION_MAP = {
    "9:16": "1080x1920",
    "16:9": "1920x1080",
    "4:3": "1440x1080",
    "1:1": "1080x1080",
    "3:4": "1080x1440",
    "21:9": "2560x1080",
}


def build_plan(args):
    """生成分镜计划"""
    topic = args.topic
    template_key = args.template or "narrative"
    template = SCENE_TEMPLATES.get(template_key, SCENE_TEMPLATES["narrative"])

    script_content = None
    if args.script:
        with open(args.script, "r", encoding="utf-8") as f:
            script_content = f.read()

    style_desc = STYLE_MAP.get(args.style, args.style or STYLE_MAP["business"])

    scenes = []
    for i, section_name in enumerate(template["structure"], 1):
        scene = {
            "scene_id": i,
            "section": section_name,
            "duration_sec": args.scene_duration or 5,
            "image_prompt": f"[待填充] {section_name}画面的文生图提示词，风格: {style_desc}",
            "video_prompt": f"[待填充] {section_name}画面的动态效果描述，镜头运动和物体变化",
            "ref_image": None,
            "ref_video": None,
            "transition": "fade" if i > 1 else None,
        }
        scenes.append(scene)

    project = {
        "project_name": topic,
        "template": template_key,
        "template_name": template["name"],
        "style": args.style or "business",
        "style_desc": style_desc,
        "aspect_ratio": args.ratio or "16:9",
        "resolution": args.size or RATIO_RESOLUTION_MAP.get(args.ratio or "16:9", "1920x1080"),
        "total_duration": sum(s["duration_sec"] for s in scenes),
        "script_content": script_content,
        "scenes": scenes,
        "status": "draft",
        "created_at": datetime.now().isoformat(),
    }

    return project


# ─── 导出生成指令 ─────────────────────────────────────

def export_project(args):
    """导出项目: 输出每个场景的生成指令"""
    with open(args.project, "r", encoding="utf-8") as f:
        project = json.load(f)

    output_dir = args.output or "."
    os.makedirs(output_dir, exist_ok=True)

    instructions = []
    for scene in project.get("scenes", []):
        inst = {
            "scene_id": scene["scene_id"],
            "section": scene.get("section", ""),
            "step1_text2img": {
                "tool": "ImageGen / Seedream",
                "prompt": scene["image_prompt"],
                "size": project.get("resolution", "2048x2048"),
                "guidance_scale": 7,
                "seed": -1,
            },
            "step2_img2video": {
                "tool": "ai_video_generator.img2video",
                "prompt": scene["video_prompt"],
                "first_frame": f"scene_{scene['scene_id']}_image.png",
                "ref_image": scene.get("ref_image"),
                "ref_video": scene.get("ref_video"),
                "duration": scene["duration_sec"],
                "ratio": project.get("aspect_ratio", "16:9"),
            },
            "transition": scene.get("transition"),
        }
        instructions.append(inst)

    export_path = os.path.join(output_dir, "generation_instructions.json")
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(instructions, f, ensure_ascii=False, indent=2)

    return {"exported": export_path, "scene_count": len(instructions)}


# ─── CLI ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="剧本分镜导演 - 半自动视频创作流水线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
分镜模板:
  narrative  叙事型 (品牌故事、人物传记)
  promotion  推宣型 (产品推广、活动宣传)
  explainer  讲解型 (知识科普、技术讲解)
  showcase   展示型 (产品展示、作品集)
  emotional  情感型 (公益宣传、节日祝福)

示例:
  python script_director.py plan --topic "AI发展史" --template narrative --style tech
  python script_director.py plan --topic "新品发布" --script article.txt --template promotion
  python script_director.py export --project project.json -o output_dir
        """
    )

    subparsers = parser.add_subparsers(dest="action", required=True)

    # plan 命令
    plan_parser = subparsers.add_parser("plan", help="生成分镜计划")
    plan_parser.add_argument("--topic", required=True, help="视频主题")
    plan_parser.add_argument("--script", help="文案文件路径 (可选)")
    plan_parser.add_argument("--template",
                             choices=list(SCENE_TEMPLATES.keys()),
                             default="narrative",
                             help="分镜模板 (默认: narrative)")
    plan_parser.add_argument("--style",
                             choices=list(STYLE_MAP.keys()),
                             default="business",
                             help="视觉风格 (默认: business)")
    plan_parser.add_argument("--ratio", default="16:9",
                             choices=["9:16", "16:9", "4:3", "1:1", "3:4", "21:9"],
                             help="画面宽高比 (默认: 16:9 横屏，可选 9:16 竖屏等)")
    plan_parser.add_argument("--size", help="分辨率 (默认按比例自动选择)")
    plan_parser.add_argument("--scene-duration", type=int, default=5,
                             help="每场景时长(秒), 默认5")
    plan_parser.add_argument("-o", "--output", help="输出项目 JSON 路径")

    # export 命令
    export_parser = subparsers.add_parser("export", help="导出生成指令")
    export_parser.add_argument("--project", required=True, help="项目 JSON 路径")
    export_parser.add_argument("-o", "--output", help="输出目录")

    args = parser.parse_args()

    if args.action == "plan":
        result = build_plan(args)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(json.dumps({"saved": args.output, "scene_count": len(result["scenes"])},
                             ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.action == "export":
        result = export_project(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
