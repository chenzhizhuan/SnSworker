#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短剧剧本生成器
从简短提示词或创意描述自动生成完整的短剧剧本JSON

三种输入模式:
  1. 纯提示词: "霸道总裁爱上灰姑娘的都市短剧"
  2. 关键词组合: 题材+角色+冲突+结局
  3. 大纲扩展: 用户给出粗略大纲，扩展为完整剧本

生成规则:
  - 每集5-8个场景
  - 开头3秒悬念钩子
  - 结尾下集预告钩子
  - 每场景5-15秒
  - 对白精炼，旁白补充节奏

用法:
  python script_generator.py --prompt "一个霸道总裁..." --output drama.json
  python script_generator.py --outline outline.json --output drama.json
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional


# ============================================
# 短剧类型模板库
# ============================================

GENRE_TEMPLATES = {
    "都市爱情": {
        "mood": "romantic",
        "bgm_mood": "romantic",
        "typical_conflicts": ["身份差距", "误会", "前任纠缠", "家族反对", "职场竞争"],
        "opening_hooks": ["雨中相遇", "意外亲吻", "身份错位", "重逢"],
        "character_archetypes": {
            "男主": "霸道总裁/温暖学长/神秘大佬",
            "女主": "独立女性/灰姑娘/才女",
            "配角1": "白月光/前女友",
            "配角2": "闺蜜/兄弟",
        },
    },
    "古装宫斗": {
        "mood": "tense",
        "bgm_mood": "mysterious",
        "typical_conflicts": ["后宫争宠", "权谋暗算", "身世之谜", "家国大义"],
        "opening_hooks": ["选秀入宫", "意外封妃", "前世记忆", "替嫁"],
        "character_archetypes": {
            "女主": "聪慧妃嫔/冷面女官/重生之人",
            "男主": "帝王/将军/暗卫",
            "配角1": "贵妃/皇后",
            "配角2": "忠仆/奸臣",
        },
    },
    "悬疑推理": {
        "mood": "tense",
        "bgm_mood": "tense",
        "typical_conflicts": ["连环案件", "卧底身份", "真相陷阱", "时间倒计时"],
        "opening_hooks": ["凶案现场", "神秘来电", "消失的记忆", "倒计时"],
        "character_archetypes": {
            "主角": "侦探/法医/记者/卧底",
            "搭档": "助手/搭档/嫌疑人",
            "反派": "幕后黑手/连环杀手",
        },
    },
    "校园青春": {
        "mood": "happy",
        "bgm_mood": "happy",
        "typical_conflicts": ["暗恋", "学业压力", "友情危机", "梦想与现实"],
        "opening_hooks": ["转学生", "意外同桌", "社团邂逅", "毕业季"],
        "character_archetypes": {
            "男主": "学霸/校草/运动健将",
            "女主": "学渣逆袭/才艺少女/转学生",
            "配角1": "情敌/校花",
            "配角2": "死党/老师",
        },
    },
    "逆袭爽文": {
        "mood": "epic",
        "bgm_mood": "epic",
        "typical_conflicts": ["被看不起", "真假身份", "实力碾压", "复仇"],
        "opening_hooks": ["被退婚", "被赶出家门", "意外觉醒", "身份暴露"],
        "character_archetypes": {
            "主角": "隐藏大佬/重生者/逆袭者",
            "对手": "嚣张反派/白眼狼/傲慢者",
            "伙伴": "忠实跟班/红颜知己",
        },
    },
    "玄幻修仙": {
        "mood": "epic",
        "bgm_mood": "mysterious",
        "typical_conflicts": ["夺宝", "飞升劫难", "师门争斗", "正邪之战"],
        "opening_hooks": ["废材觉醒", "奇遇传承", "仙门试炼", "前世记忆"],
        "character_archetypes": {
            "主角": "废材逆袭/天才少年/转世修仙",
            "对手": "宗门天才/魔道强者",
            "伙伴": "灵兽/师兄妹/道侣",
        },
    },
}


# ============================================
# 剧本结构模板
# ============================================

# 单集结构（5-8场景）
EPISODE_STRUCTURE = {
    "opening_hook": {
        "desc": "开头钩子场景 - 3秒内抓住注意力",
        "duration": "3-5秒",
        "elements": ["悬念画面", "情绪冲击", "关键台词"],
    },
    "setup": {
        "desc": "背景铺垫 - 建立人物关系和场景",
        "duration": "10-20秒",
        "scene_count": "1-2",
        "elements": ["角色登场", "关系介绍", "世界观建立"],
    },
    "conflict_introduction": {
        "desc": "冲突引出 - 核心矛盾浮现",
        "duration": "10-15秒",
        "scene_count": "1-2",
        "elements": ["冲突事件", "对立关系", "情感漩涡"],
    },
    "escalation": {
        "desc": "冲突升级 - 矛盾激化，达到高潮",
        "duration": "15-25秒",
        "scene_count": "2-3",
        "elements": ["反击/对抗", "意外转折", "情感爆发"],
    },
    "climax": {
        "desc": "高潮/反转 - 最强冲击",
        "duration": "5-10秒",
        "scene_count": "1",
        "elements": ["真相揭露", "身份暴露", "命运抉择"],
    },
    "cliffhanger": {
        "desc": "悬念结尾 - 留钩子给下集",
        "duration": "3-5秒",
        "scene_count": "1",
        "elements": ["震惊画面", "未解之谜", "新威胁"],
    },
}

# 转场效果匹配规则
TRANSITION_RULES = {
    ("setup", "conflict_introduction"): "fade_black",     # 平静→冲突：黑场过渡
    ("conflict_introduction", "escalation"): "slide_left", # 冲突→升级：推进
    ("escalation", "climax"): "flash_white",               # 升级→高潮：闪白
    ("climax", "cliffhanger"): "fade_black",               # 高潮→悬念：渐黑
    ("opening_hook", "setup"): "dissolve",                  # 钩子→铺垫：溶解
}


# ============================================
# 分镜细化映射（v2 增强，与 ai_video_generator 的
# ACTION_PROMPTS / AMBIENT_MOTION 对齐，供 build_video_prompt 直接消费）
# ============================================

# 结构阶段 → 默认运镜（action，与 ai_video_generator.ACTION_PROMPTS 键一致）
STRUCTURE_ACTION = {
    "opening_hook": "dramatic",
    "setup": "static",
    "conflict_introduction": "confronting",
    "escalation": "dramatic",
    "climax": "emotional",
    "cliffhanger": "zoom_in",
}

# 结构阶段 → 默认环境氛围（ambient，与 ai_video_generator.AMBIENT_MOTION 键一致）
STRUCTURE_AMBIENT = {
    "opening_hook": "outdoor_night",
    "setup": "indoor_room",
    "conflict_introduction": "urban",
    "escalation": "urban",
    "climax": "nature",
    "cliffhanger": "outdoor_night",
}

# 结构阶段 → 默认情绪（供 TTS 情感调参与角色表情）
STRUCTURE_EMOTION = {
    "opening_hook": "surprised",
    "setup": "calm",
    "conflict_introduction": "serious",
    "escalation": "angry",
    "climax": "excited",
    "cliffhanger": "fear",
}

# 景别候选
SHOT_TYPES = ["特写", "近景", "中景", "全景", "过肩", "俯拍", "仰拍"]

# 机位候选
CAMERA_ANGLES = ["平视", "低角度", "高角度", "侧面", "背后", "过肩视角"]

# 角色原型 → TTS 音色（仅使用已验证有效的音色，避免失效音色）
# 有效集: zh-CN-YunxiNeural / YunjianNeural / YunyangNeural / YunxiaNeural /
#         XiaoxiaoNeural / XiaoyiNeural （Xiaochen/Xiaomo/Xiaohan 已失效，勿用）
ARCHETYPE_VOICES = {
    # 男性（深沉/强势/反派 → Yunjian）
    "霸道总裁": "zh-CN-YunjianNeural",
    "神秘大佬": "zh-CN-YunjianNeural",
    "帝王": "zh-CN-YunjianNeural",
    "将军": "zh-CN-YunjianNeural",
    "暗卫": "zh-CN-YunjianNeural",
    "侦探": "zh-CN-YunjianNeural",
    "法医": "zh-CN-YunjianNeural",
    "记者": "zh-CN-YunjianNeural",
    "卧底": "zh-CN-YunjianNeural",
    "反派": "zh-CN-YunjianNeural",
    "幕后黑手": "zh-CN-YunjianNeural",
    "连环杀手": "zh-CN-YunjianNeural",
    "隐藏大佬": "zh-CN-YunjianNeural",
    "重生者": "zh-CN-YunjianNeural",
    "逆袭者": "zh-CN-YunjianNeural",
    "嚣张反派": "zh-CN-YunjianNeural",
    "白眼狼": "zh-CN-YunjianNeural",
    "傲慢者": "zh-CN-YunjianNeural",
    "宗门天才": "zh-CN-YunjianNeural",
    "魔道强者": "zh-CN-YunjianNeural",
    "奸臣": "zh-CN-YunjianNeural",
    "嫌疑人": "zh-CN-YunjianNeural",
    # 男性（年轻/温暖/亲和 → Yunxi）
    "温暖学长": "zh-CN-YunxiNeural",
    "学霸": "zh-CN-YunxiNeural",
    "校草": "zh-CN-YunxiNeural",
    "运动健将": "zh-CN-YunxiNeural",
    "废材逆袭": "zh-CN-YunxiNeural",
    "天才少年": "zh-CN-YunxiNeural",
    "转世修仙": "zh-CN-YunxiNeural",
    "搭档": "zh-CN-YunxiNeural",
    "助手": "zh-CN-YunxiNeural",
    "死党": "zh-CN-YunxiNeural",
    "忠实跟班": "zh-CN-YunxiNeural",
    "红颜知己": "zh-CN-YunxiNeural",
    "灵兽": "zh-CN-YunxiNeural",
    "师兄妹": "zh-CN-YunxiNeural",
    "道侣": "zh-CN-YunxiNeural",
    # 女性（成熟/独立/强势 → Xiaoxiao）
    "独立女性": "zh-CN-XiaoxiaoNeural",
    "灰姑娘": "zh-CN-XiaoxiaoNeural",
    "聪慧妃嫔": "zh-CN-XiaoxiaoNeural",
    "重生之人": "zh-CN-XiaoxiaoNeural",
    "前女友": "zh-CN-XiaoxiaoNeural",
    "贵妃": "zh-CN-XiaoxiaoNeural",
    "皇后": "zh-CN-XiaoxiaoNeural",
    "情敌": "zh-CN-XiaoxiaoNeural",
    "校花": "zh-CN-XiaoxiaoNeural",
    # 女性（温柔/清纯/少女 → Xiaoyi）
    "才女": "zh-CN-XiaoyiNeural",
    "冷面女官": "zh-CN-XiaoyiNeural",
    "学渣逆袭": "zh-CN-XiaoyiNeural",
    "才艺少女": "zh-CN-XiaoyiNeural",
    "转学生": "zh-CN-XiaoyiNeural",
    "白月光": "zh-CN-XiaoyiNeural",
    "闺蜜": "zh-CN-XiaoyiNeural",
}

# 兜底音色池（避免角色冲突时全部落到同一音色）
_FALLBACK_VOICES = [
    "zh-CN-YunxiNeural", "zh-CN-YunjianNeural",
    "zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural",
    "zh-CN-YunxiaNeural",
]


# 画面比例 → 分辨率映射
RATIO_RESOLUTION_MAP = {
    "9:16": "1080x1920",
    "16:9": "1920x1080",
    "4:3": "1440x1080",
    "1:1": "1080x1080",
    "3:4": "1080x1440",
    "21:9": "2560x1080",
}


def generate_from_prompt(
    prompt: str,
    genre: Optional[str] = None,
    episode: int = 1,
    duration_minutes: float = 1.5,
    ratio: str = "9:16",
) -> Dict:
    """
    从简要提示词生成完整剧本

    Args:
        prompt: 创意描述，如 "霸道总裁爱上灰姑娘"
        genre: 类型（都市爱情/古装宫斗/悬疑推理等），None则自动推断
        episode: 集数
        duration_minutes: 目标时长（分钟）
        ratio: 画面宽高比 (9:16/16:9/4:3/1:1/3:4/21:9)，默认 9:16 竖屏
    """
    # 1. 推断类型
    if not genre:
        genre = infer_genre(prompt)

    template = GENRE_TEMPLATES.get(genre, GENRE_TEMPLATES["都市爱情"])

    # 2. 生成剧本骨架
    total_seconds = duration_minutes * 60
    scene_count = estimate_scene_count(total_seconds)

    # 3. 构建剧本JSON
    # 注意：这里生成的是骨架/模板，具体对白需要LLM在运行时填充
    script = {
        "title": extract_title(prompt),
        "genre": genre,
        "style": infer_style(genre),
        "episode": episode,
        "duration_target": f"{duration_minutes}分钟",
        "aspect_ratio": ratio,
        "resolution": RATIO_RESOLUTION_MAP.get(ratio, "1080x1920"),
        "voice_mapping": generate_voice_mapping(template),
        "bgm_mood": template["bgm_mood"],
        "prompt_source": prompt,
        "structure_note": "此剧本由提示词自动生成骨架，对白和画面描述需要LLM运行时填充完善",
        "scenes": [],
    }

    # 4. 按剧集结构生成场景
    structure_keys = list(EPISODE_STRUCTURE.keys())
    for i, key in enumerate(structure_keys):
        struct = EPISODE_STRUCTURE[key]
        scene_count_for_part = int(scene_count / len(structure_keys))
        if i == 0:
            scene_count_for_part = max(1, scene_count_for_part)

        for j in range(scene_count_for_part):
            scene_id = len(script["scenes"]) + 1
            transition = "fade_black"

            # 推断转场
            if i < len(structure_keys) - 1:
                next_key = structure_keys[i + 1]
                transition = TRANSITION_RULES.get(
                    (key, next_key), "fade_black"
                )

            scene = {
                "id": scene_id,
                "structure_role": key,
                "structure_desc": struct["desc"],
                "background_prompt": f"[待填充] {key}阶段的场景{scene_id}，基于提示词: {prompt}",
                "characters": [],
                "dialogues": [],
                "narration": "",
                # ── 分镜细化字段（v2.4，供 build_video_prompt 直接消费）──
                "action": STRUCTURE_ACTION.get(key, "static"),
                "shot_type": "中景",
                "camera": "平视",
                "ambient": STRUCTURE_AMBIENT.get(key, "indoor_room"),
                "emotion": STRUCTURE_EMOTION.get(key, "calm"),
                "duration_seconds": 6,
                "transition": transition,
                "notes": f"此场景属于'{struct['desc']}'，需要包含: {', '.join(struct['elements'])}",
            }
            script["scenes"].append(scene)

    return script


def infer_genre(prompt: str) -> str:
    """从提示词推断短剧类型"""
    keyword_map = {
        "都市爱情": ["爱情", "恋爱", "总裁", "灰姑娘", "甜宠", "霸道", "豪门", "求婚", "初恋"],
        "古装宫斗": ["宫斗", "皇帝", "妃子", "朝堂", "将军", "武侠", "皇后", "太子", "替嫁"],
        "悬疑推理": ["悬疑", "推理", "侦探", "谋杀", "凶案", "卧底", "密室", "死亡"],
        "校园青春": ["校园", "学生", "老师", "高考", "暗恋", "同桌", "青春", "毕业"],
        "逆袭爽文": ["逆袭", "打脸", "装逼", "废材", "废物", "重生", "穿越", "实力", "碾压"],
        "玄幻修仙": ["修仙", "仙侠", "飞升", "灵气", "丹药", "宗门", "道友", "法宝"],
    }

    for genre, keywords in keyword_map.items():
        for kw in keywords:
            if kw in prompt:
                return genre

    return "都市爱情"  # 默认


def infer_style(genre: str) -> str:
    """根据类型推断画风"""
    style_map = {
        "都市爱情": "anime",
        "古装宫斗": "qcomic",
        "悬疑推理": "realistic",
        "校园青春": "cute",
        "逆袭爽文": "qcomic",
        "玄幻修仙": "anime",
    }
    return style_map.get(genre, "anime")


def extract_title(prompt: str) -> str:
    """从提示词提取标题"""
    # 简单逻辑：取前8个字作为标题
    clean = prompt.strip().replace("短剧", "").replace("故事", "").strip()
    if len(clean) > 8:
        return clean[:8]
    return clean or "未命名短剧"


def estimate_scene_count(total_seconds: float) -> int:
    """根据目标时长估算场景数"""
    # 平均每场景8-12秒
    return max(5, int(total_seconds / 10))


def generate_voice_mapping(template: Dict) -> Dict:
    """
    根据角色原型自动分配TTS音色

    修复：支持斜杠多选原型（如"霸道总裁/温暖学长"），按序匹配第一个
    命中的原型；避免角色间音色冲突（同音色自动换下一个可用音色）。
    仅使用有效音色（XiaochenNeural 等已失效，勿用）。
    """
    voice_map = {"旁白": "zh-CN-YunyangNeural"}  # 旁白固定
    used = {voice_map["旁白"]}

    for role, archetype in template.get("character_archetypes", {}).items():
        # 拆解斜杠多选原型
        candidates = [a.strip() for a in archetype.split("/") if a.strip()]
        voice = None
        for cand in candidates:
            if cand in ARCHETYPE_VOICES:
                voice = ARCHETYPE_VOICES[cand]
                break

        if voice is None or voice in used:
            # 未命中或已占用：从兜底池选一个未使用的音色
            voice = next(
                (v for v in _FALLBACK_VOICES if v not in used),
                "zh-CN-YunxiNeural",
            )
        used.add(voice)
        voice_map[role] = voice

    return voice_map


def expand_outline(outline: Dict, ratio: str = "9:16") -> Dict:
    """
    扩展粗略大纲为完整剧本
    大纲格式:
    {
      "title": "...",
      "genre": "都市爱情",
      "outline": [
        {"scene": "开头", "desc": "雨夜天台对峙"},
        {"scene": "回忆", "desc": "三年前的相遇"},
        ...
      ]
    }

    Args:
        ratio: 画面宽高比 (9:16/16:9/4:3/1:1/3:4/21:9)，默认 9:16 竖屏
    """
    genre = outline.get("genre", "都市爱情")
    template = GENRE_TEMPLATES.get(genre, GENRE_TEMPLATES["都市爱情"])

    script = {
        "title": outline.get("title", "未命名短剧"),
        "genre": genre,
        "style": infer_style(genre),
        "episode": outline.get("episode", 1),
        "aspect_ratio": ratio,
        "resolution": RATIO_RESOLUTION_MAP.get(ratio, "1080x1920"),
        "voice_mapping": generate_voice_mapping(template),
        "bgm_mood": template["bgm_mood"],
        "outline_source": outline,
        "scenes": [],
    }

    for i, item in enumerate(outline.get("outline", [])):
        scene_id = i + 1

        # 推断转场
        default_transitions = ["fade_black", "fade_black", "flash_white", "dissolve", "fade_black"]
        transition = default_transitions[i % len(default_transitions)]

        scene = {
            "id": scene_id,
            "background_prompt": f"[待填充] {item.get('desc', '')}",
            "characters": [],
            "dialogues": [],
            "narration": "",
            # ── 分镜细化字段（v2.4）──
            "action": item.get("action", "static"),
            "shot_type": item.get("shot_type", "中景"),
            "camera": item.get("camera", "平视"),
            "ambient": item.get("ambient", "indoor_room"),
            "emotion": item.get("emotion", "calm"),
            "duration_seconds": item.get("duration_seconds", 6),
            "transition": transition,
            "notes": item.get("desc", ""),
        }
        script["scenes"].append(scene)

    return script


def main():
    import argparse
    parser = argparse.ArgumentParser(description="短剧剧本生成器")
    parser.add_argument("--prompt", default=None, help="创意提示词")
    parser.add_argument("--genre", default=None, help="指定类型")
    parser.add_argument("--outline", default=None, help="大纲JSON路径")
    parser.add_argument("--episode", type=int, default=1, help="集数")
    parser.add_argument("--duration", type=float, default=1.5, help="目标时长(分钟)")
    parser.add_argument("--ratio", default="9:16",
                        choices=["9:16", "16:9", "4:3", "1:1", "3:4", "21:9"],
                        help="画面宽高比 (默认: 9:16 竖屏，可选 16:9/4:3 等横屏)")
    parser.add_argument("--output", default="drama_script.json", help="输出路径")
    parser.add_argument("--list-genres", action="store_true", help="列出所有类型模板")

    args = parser.parse_args()

    if args.list_genres:
        print("可用的短剧类型模板:")
        for genre, tmpl in GENRE_TEMPLATES.items():
            archetypes = ", ".join(
                f"{role}:{a}" for role, a in tmpl["character_archetypes"].items()
            )
            print(f"  {genre}: {tmpl['mood']} | 开场: {', '.join(tmpl['opening_hooks'])}")
            print(f"    角色原型: {archetypes}")
        return

    if args.prompt:
        script = generate_from_prompt(
            args.prompt, args.genre, args.episode, args.duration, args.ratio
        )
    elif args.outline:
        with open(args.outline, "r", encoding="utf-8") as f:
            outline = json.load(f)
        script = expand_outline(outline, ratio=args.ratio)
    else:
        print("请提供 --prompt 或 --outline")
        parser.print_help()
        return

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    print(f"[OK] 剧本已生成: {args.output}")
    print(f"     标题: {script['title']}")
    print(f"     类型: {script.get('genre', '未知')}")
    print(f"     场景数: {len(script['scenes'])}")
    print(f"     注意: 场景内的background_prompt/dialogues/narration需要LLM运行时填充")


if __name__ == "__main__":
    main()
