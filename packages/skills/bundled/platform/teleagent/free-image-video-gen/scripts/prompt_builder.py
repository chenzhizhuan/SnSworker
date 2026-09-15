#!/usr/bin/env python3
"""
提示词智能构建工具

将用户的简单描述自动增强为高质量的图像/视频生成提示词。
内置风格预设、中英双语映射、运镜模板和通用负面词库。

用法：
  # 交互式构建
  python prompt_builder.py --interactive

  # 命令行直接构建
  python prompt_builder.py --content "城市夜景" --style cyberpunk --type video

  # 仅输出英文增强提示词
  python prompt_builder.py --content "产品展示" --style product --type image --lang en

  # 列出所有可用风格
  python prompt_builder.py --list-styles
"""

import argparse
import json
import sys
from pathlib import Path

# ──────────────────────────────────────────────
# 风格预设库
# ──────────────────────────────────────────────

STYLE_PRESETS = {
    # ── 图像 & 视频通用风格 ──
    "cinematic": {
        "name_cn": "电影感",
        "name_en": "Cinematic",
        "type": "both",
        "keywords": "cinematic lighting, shallow depth of field, film grain, color grading, dramatic shadows, golden hour, anamorphic lens flare, 8K, hyper-detailed",
        "camera": "cinematic camera movement, slow dolly shot",
        "color_tone": "teal and orange color grade",
        "negative": "flat lighting, overexposed, washed out, low contrast",
    },
    "realistic": {
        "name_cn": "写实摄影",
        "name_en": "Realistic Photography",
        "type": "both",
        "keywords": "photorealistic, ultra-detailed, natural lighting, high resolution, DSLR quality, sharp focus, raw photo, 8K UHD",
        "camera": "steady handheld, natural movement",
        "color_tone": "natural colors, true-to-life",
        "negative": "cartoon, anime, illustration, painting, 3D render, CGI",
    },
    "cyberpunk": {
        "name_cn": "赛博朋克",
        "name_en": "Cyberpunk",
        "type": "both",
        "keywords": "neon lights, rain-soaked streets, holographic signs, futuristic megacity, flying vehicles, volumetric fog, blade runner aesthetic, ultra-detailed, 8K",
        "camera": "slow tracking shot through neon alley",
        "color_tone": "magenta and cyan neon glow, dark shadows",
        "negative": "daytime, bright sunlight, rural, nature, vintage",
    },
    "chinese_ink": {
        "name_cn": "中国水墨",
        "name_en": "Chinese Ink Painting",
        "type": "both",
        "keywords": "traditional Chinese ink painting, sumi-e style, brush stroke texture, negative space, misty mountains, elegant, zen atmosphere, rice paper texture",
        "camera": "slow horizontal scroll pan, ink diffusion animation",
        "color_tone": "monochrome ink, subtle color accents",
        "negative": "colorful, neon, modern, industrial, 3D render",
    },
    "flat_illustration": {
        "name_cn": "扁平插画",
        "name_en": "Flat Illustration",
        "type": "image",
        "keywords": "flat design, vector style, clean shapes, bold colors, minimal detail, modern illustration, geometric composition",
        "camera": "",
        "color_tone": "vibrant flat colors, limited palette",
        "negative": "realistic, 3D, gradient, shadow, texture, photograph",
    },
    "3d_render": {
        "name_cn": "3D渲染",
        "name_en": "3D Render",
        "type": "both",
        "keywords": "3D render, C4D style, Blender, octane render, soft shadows, subsurface scattering, material textures, studio lighting, 8K",
        "camera": "smooth orbital rotation, depth of field",
        "color_tone": "soft pastel or vibrant studio colors",
        "negative": " photograph, 2D, flat, sketch, painting",
    },
    "oil_painting": {
        "name_cn": "油画质感",
        "name_en": "Oil Painting",
        "type": "image",
        "keywords": "oil painting, visible brush strokes, rich texture, classical lighting, canvas texture, baroque, impressionist, masterpiece",
        "camera": "",
        "color_tone": "warm earth tones, chiaroscuro",
        "negative": "photograph, 3D, digital, flat, cartoon",
    },
    "minimalist": {
        "name_cn": "极简主义",
        "name_en": "Minimalist",
        "type": "both",
        "keywords": "minimalist composition, negative space, limited color palette, clean, simple, elegant, zen, geometric",
        "camera": "slow static shot, minimal movement",
        "color_tone": "monochrome or duotone",
        "negative": "cluttered, busy, ornate, detailed, complex",
    },
    # ── 视频专用风格 ──
    "tech_promo": {
        "name_cn": "科技宣传",
        "name_en": "Tech Promotional",
        "type": "video",
        "keywords": "deep space background, digital particles, data streams, holographic interface, blue and gold color palette, smooth transitions, futuristic, professional, 4K",
        "camera": "slow orbit, push-in, smooth gimbal movement",
        "color_tone": "deep blue and gold tech palette",
        "negative": "blurry, distorted, flickering, low quality, watermark",
    },
    "product_showcase": {
        "name_cn": "产品展示",
        "name_en": "Product Showcase",
        "type": "video",
        "keywords": "clean studio background, soft box lighting, product on pedestal, floating particles, premium feel, macro detail, 8K",
        "camera": "360 degree rotation, slow zoom-in, macro close-up",
        "color_tone": "white/gray studio with accent colors",
        "negative": "cluttered background, harsh shadows, low quality",
    },
    "nature_landscape": {
        "name_cn": "自然风光",
        "name_en": "Nature Landscape",
        "type": "video",
        "keywords": "breathtaking landscape, golden hour light, misty mountains, flowing water, time-lapse clouds, aerial drone shot, 8K nature photography",
        "camera": "aerial drone, sweeping panorama, time-lapse",
        "color_tone": "natural warm golden tones, vibrant greens",
        "negative": "urban, city, buildings, artificial, CGI",
    },
    "urban_night": {
        "name_cn": "城市夜景",
        "name_en": "Urban Night",
        "type": "video",
        "keywords": "night city skyline, light trails, neon reflections on wet streets, traffic flow, skyscrapers, cinematic night, 8K",
        "camera": "slow tracking, helicopter aerial, time-lapse traffic",
        "color_tone": "deep blue night, warm street lights, neon",
        "negative": "daytime, rural, empty streets, low quality",
    },
    "abstract_art": {
        "name_cn": "抽象艺术",
        "name_en": "Abstract Art",
        "type": "video",
        "keywords": "abstract fluid animation, color gradient morphing, geometric transformation, particle system, flowing shapes, mesmerizing, 4K",
        "camera": "slow zoom, rotation, morphing transition",
        "color_tone": "vibrant gradient, iridescent",
        "negative": "realistic, photograph, text, watermark",
    },
    "portrait_dynamic": {
        "name_cn": "人物动态",
        "name_en": "Portrait Dynamic",
        "type": "video",
        "keywords": "portrait close-up, natural skin texture, soft hair movement, micro expressions, bokeh background, cinematic portrait, 8K",
        "camera": "slow push-in, shallow depth of field, slight orbit",
        "color_tone": "warm natural skin tones, soft bokeh",
        "negative": "distorted face, deformed, blurry, low quality",
    },
    "anime_style": {
        "name_cn": "动漫风格",
        "name_en": "Anime Style",
        "type": "both",
        "keywords": "anime style, cel shading, vibrant colors, detailed background, studio Ghibli inspired, key visual, 4K",
        "camera": "dynamic anime camera, parallax background",
        "color_tone": "vibrant saturated colors",
        "negative": "realistic, 3D, photograph, western cartoon",
    },
    "vintage_film": {
        "name_cn": "复古胶片",
        "name_en": "Vintage Film",
        "type": "both",
        "keywords": "vintage film aesthetic, 35mm grain, light leaks, faded colors, analog warmth, nostalgic, retro, 8mm",
        "camera": "handheld, slight camera shake, vintage zoom",
        "color_tone": "faded warm, sepia, muted",
        "negative": "digital, sharp, modern, clean, bright",
    },
    "fantasy": {
        "name_cn": "奇幻史诗",
        "name_en": "Fantasy Epic",
        "type": "both",
        "keywords": "epic fantasy landscape, magical atmosphere, ethereal light, floating islands, mystical creatures, volumetric god rays, 8K concept art",
        "camera": "sweeping aerial, slow majestic pan",
        "color_tone": "ethereal gold and deep blue, magical glow",
        "negative": "modern, urban, mundane, simple",
    },
    "watercolor": {
        "name_cn": "水彩画",
        "name_en": "Watercolor",
        "type": "image",
        "keywords": "watercolor painting, soft color bleeding, paper texture, delicate brush work, artistic, dreamy, flowing colors",
        "camera": "",
        "color_tone": "soft pastel, transparent washes",
        "negative": "photograph, 3D, sharp edges, digital, CGI",
    },
    "pixel_art": {
        "name_cn": "像素艺术",
        "name_en": "Pixel Art",
        "type": "image",
        "keywords": "pixel art, 16-bit retro game style, limited color palette, dithering, crisp pixels, nostalgic",
        "camera": "",
        "color_tone": "retro game palette",
        "negative": "realistic, 3D, smooth gradients, photograph",
    },
    "isometric": {
        "name_cn": "等距视角",
        "name_en": "Isometric",
        "type": "image",
        "keywords": "isometric illustration, 2.5D perspective, clean vector style, miniature scene, top-down angle, detailed small objects",
        "camera": "",
        "color_tone": "clean modern colors",
        "negative": "realistic photo, first-person, blurry",
    },
}

# ──────────────────────────────────────────────
# 中英文常用词映射表
# ──────────────────────────────────────────────

CN_EN_MAP = {
    # 主体
    "城市": "city", "街道": "street", "夜景": "night scene", "日落": "sunset",
    "日出": "sunrise", "森林": "forest", "海洋": "ocean", "山脉": "mountains",
    "沙漠": "desert", "天空": "sky", "星空": "starry sky", "雪景": "snow scene",
    "人物": "person", "少女": "young woman", "男孩": "boy", "老人": "elderly",
    "猫": "cat", "狗": "dog", "马": "horse", "鸟": "bird",
    "花": "flowers", "树": "trees", "建筑": "architecture", "机器人": "robot",
    "车": "car", "飞机": "airplane", "宇宙飞船": "spaceship",
    # 风格
    "电影感": "cinematic", "写实": "realistic", "梦幻": "dreamy",
    "科技感": "futuristic tech", "复古": "vintage retro",
    "未来": "futuristic", "古典": "classical", "现代": "modern",
    # 光影
    "逆光": "backlit", "侧光": "side lighting", "柔光": "soft light",
    "硬光": "hard light", "自然光": "natural light", "霓虹": "neon",
    # 构图
    "特写": "close-up", "广角": "wide angle", "鸟瞰": "bird's eye view",
    "全景": "panoramic", "远景": "wide shot", "中景": "medium shot",
    # 质量词
    "高清": "high definition", "4K": "4K", "8K": "8K",
    "超细节": "ultra-detailed", "超高清": "ultra HD",
    # 运镜
    "推镜头": "push-in / dolly-in", "拉镜头": "pull-back / dolly-out",
    "环绕": "orbit / arc shot", "平移": "pan",
    "变焦": "zoom", "航拍": "aerial drone shot",
    "缓慢": "slow", "快速": "fast",
}

# 通用负面词库
DEFAULT_NEGATIVE = "blurry, distorted, deformed, disfigured, low quality, watermark, text artifacts, extra limbs, bad anatomy, blurry background, flickering, jpeg artifacts, overexposed, underexposed, washed out"

# ──────────────────────────────────────────────
# 视频运镜模板
# ──────────────────────────────────────────────

CAMERA_MOVES = {
    "push_in": "camera slowly pushes in, dolly forward, gradual zoom",
    "pull_back": "camera slowly pulls back, dolly backward, reveal wider scene",
    "orbit": "camera orbits around the subject, arc shot, 360 degree rotation",
    "pan_left": "camera pans slowly from right to left",
    "pan_right": "camera pans slowly from left to right",
    "crane_up": "camera cranes up, rising, bird's eye reveal",
    "crane_down": "camera descends, lowering, ground level approach",
    "aerial": "aerial drone shot, sweeping flyover, bird's eye view",
    "handheld": "subtle handheld camera, natural slight shake",
    "static": "static camera, fixed shot, no movement",
    "rotation": "slow rotational pan, panoramic sweep",
    "tracking": "tracking shot following the subject, smooth gimbal movement",
}

# ──────────────────────────────────────────────
# 构建逻辑
# ──────────────────────────────────────────────

def translate_cn_to_en(text: str) -> str:
    """简单的中英关键词映射"""
    result = text
    for cn, en in sorted(CN_EN_MAP.items(), key=lambda x: -len(x[0])):
        result = result.replace(cn, en)
    return result


def build_prompt(content: str, style: str = None, media_type: str = "image",
                 camera_move: str = None, lang: str = "en") -> dict:
    """
    构建增强提示词

    Args:
        content: 用户原始描述
        style: 风格ID（STYLE_PRESETS 的 key）
        media_type: "image" 或 "video"
        camera_move: 运镜模板 key（仅视频）
        lang: 输出语言 "en" 或 "zh"

    Returns:
        dict: {prompt, negative_prompt, style_name}
    """
    # 获取风格预设
    preset = STYLE_PRESETS.get(style, {})

    # 主体描述：中文转英文
    subject_en = translate_cn_to_en(content)

    # 组装提示词
    parts = []

    if lang == "en":
        # 英文提示词
        parts.append(subject_en if not _is_english(content) else content)
        if preset.get("keywords"):
            parts.append(preset["keywords"])
        if media_type == "video":
            if camera_move and camera_move in CAMERA_MOVES:
                parts.append(CAMERA_MOVES[camera_move])
            elif preset.get("camera"):
                parts.append(preset["camera"])
        if preset.get("color_tone"):
            parts.append(preset["color_tone"])
        prompt = ", ".join(parts)
    else:
        # 中文提示词（保留原始，附加风格说明）
        parts.append(content)
        if preset.get("name_cn"):
            parts.append(f"风格：{preset['name_cn']}")
        prompt = "，".join(parts)

    # 负面提示词
    neg_parts = [DEFAULT_NEGATIVE]
    if preset.get("negative"):
        neg_parts.append(preset["negative"])
    negative = ", ".join(neg_parts)

    return {
        "prompt": prompt,
        "negative_prompt": negative,
        "style_name": preset.get("name_cn", "默认"),
        "style_id": style or "default",
    }


def _is_english(text: str) -> bool:
    """判断文本是否主要是英文"""
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    return ascii_chars / max(len(text), 1) > 0.7


# ──────────────────────────────────────────────
# 交互模式
# ──────────────────────────────────────────────

def interactive_mode():
    """交互式提示词构建"""
    print("=" * 60)
    print("提示词智能构建工具")
    print("=" * 60)

    # 1. 输入内容
    content = input("\n请输入你想生成的内容描述: ").strip()
    if not content:
        print("内容不能为空！")
        return

    # 2. 选择类型
    print("\n生成类型:")
    print("  1. 图片 (image)")
    print("  2. 视频 (video)")
    type_choice = input("选择 (1/2，默认1): ").strip() or "1"
    media_type = "video" if type_choice == "2" else "image"

    # 3. 选择风格
    print(f"\n可用风格（{'视频' if media_type == 'video' else '图片'}推荐）:")
    available = []
    idx = 1
    for key, preset in STYLE_PRESETS.items():
        if media_type == "image" and preset["type"] == "video":
            continue
        if media_type == "video" and preset["type"] == "image":
            preset_type = "both"
            if preset["type"] == "image":
                continue
        available.append(key)
        print(f"  {idx}. {preset['name_cn']} ({key})", end="")
        if preset["type"] == "both":
            print(" [图+视频]")
        else:
            print(f" [{preset['type']}]")
        idx += 1
    print(f"  {idx}. 不使用风格预设 (default)")

    style_choice = input(f"\n选择风格编号 (1-{idx}，默认{idx}): ").strip() or str(idx)
    try:
        choice_idx = int(style_choice)
        style = available[choice_idx - 1] if 1 <= choice_idx <= len(available) else None
    except ValueError:
        style = None

    # 4. 运镜（视频）
    camera_move = None
    if media_type == "video":
        print("\n运镜模板:")
        cam_keys = list(CAMERA_MOVES.keys())
        for i, k in enumerate(cam_keys, 1):
            print(f"  {i}. {k}: {CAMERA_MOVES[k][:50]}...")
        print(f"  {len(cam_keys)+1}. 不指定 (auto)")
        cam_choice = input(f"选择 (1-{len(cam_keys)+1}，默认{len(cam_keys)+1}): ").strip()
        try:
            cam_idx = int(cam_choice)
            if 1 <= cam_idx <= len(cam_keys):
                camera_move = cam_keys[cam_idx - 1]
        except ValueError:
            pass

    # 5. 构建
    result = build_prompt(content, style, media_type, camera_move, lang="en")

    print(f"\n{'='*60}")
    print(f"构建结果")
    print(f"{'='*60}")
    print(f"\n风格: {result['style_name']} ({result['style_id']})")
    print(f"\n提示词 (prompt):")
    print(f"  {result['prompt']}")
    print(f"\n负面提示词 (negative_prompt):")
    print(f"  {result['negative_prompt']}")
    print(f"\n{'='*60}")

    # 6. 输出 JSON
    output_choice = input("\n保存为JSON文件? (y/N): ").strip().lower()
    if output_choice == "y":
        out_path = input("保存路径 (默认 prompt_output.json): ").strip() or "prompt_output.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"已保存到: {out_path}")


def list_styles():
    """列出所有可用风格"""
    print(f"\n{'='*60}")
    print(f"风格预设库 ({len(STYLE_PRESETS)} 种)")
    print(f"{'='*60}\n")

    # 按类型分组
    for category, type_filter in [("图片+视频", "both"), ("仅图片", "image"), ("仅视频", "video")]:
        items = [(k, v) for k, v in STYLE_PRESETS.items() if v["type"] == type_filter]
        if items:
            print(f"【{category}】")
            for key, preset in items:
                print(f"  {key:20s} | {preset['name_cn']:8s} | {preset['name_en']}")
            print()

    print(f"\n运镜模板 ({len(CAMERA_MOVES)} 种):")
    for key, desc in CAMERA_MOVES.items():
        print(f"  {key:15s} | {desc}")

    print(f"\n中英映射词 ({len(CN_EN_MAP)} 组):")
    for cn, en in list(CN_EN_MAP.items())[:10]:
        print(f"  {cn:8s} -> {en}")
    print(f"  ... 共 {len(CN_EN_MAP)} 组")


# ──────────────────────────────────────────────
# 命令行入口
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="提示词智能构建工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--content", "-c", help="内容描述")
    parser.add_argument("--style", "-s", help="风格ID (如 cinematic, cyberpunk)")
    parser.add_argument("--type", "-t", choices=["image", "video"], default="image", help="生成类型")
    parser.add_argument("--camera", help="运镜模板 (仅视频，如 push_in, orbit, aerial)")
    parser.add_argument("--lang", "-l", choices=["en", "zh"], default="en", help="输出语言")
    parser.add_argument("--output", "-o", help="输出JSON文件路径")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互式模式")
    parser.add_argument("--list-styles", action="store_true", help="列出所有可用风格")

    args = parser.parse_args()

    if args.list_styles:
        list_styles()
        return

    if args.interactive:
        interactive_mode()
        return

    if not args.content:
        parser.print_help()
        print("\n错误: 请提供 --content 或使用 --interactive / --list-styles")
        sys.exit(1)

    result = build_prompt(
        content=args.content,
        style=args.style,
        media_type=args.type,
        camera_move=args.camera,
        lang=args.lang,
    )

    print(f"风格: {result['style_name']} ({result['style_id']})")
    print(f"\n提示词:")
    print(f"  {result['prompt']}")
    print(f"\n负面提示词:")
    print(f"  {result['negative_prompt']}")

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n已保存到: {args.output}")


if __name__ == "__main__":
    main()
