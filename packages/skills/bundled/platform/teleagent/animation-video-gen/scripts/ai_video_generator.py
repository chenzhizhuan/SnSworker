#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 视频/图片生成模块 v3 — 即梦 Seedream/Seedance 满血版

支持 7 种生成模式:
  - text2img     : 文字 → 图片 (Seedream 5.0 Pro/Lite, 4K+联网检索)
  - text2video   : 文字 → 视频 (Seedance 2.0/2.0-fast/2.0-mini/1.5-pro)
  - img2video    : 首帧图片(±尾帧) → 视频
  - ref2video    : 参考图(≤9张) → 视频
  - vivid2video  : 参考视频(≤3段) → 新视频 (运动/运镜复刻)
  - multimodal   : 图片+视频+音频+文本 → 视频 (全能参考融合)
  - video_extend : 视频续写 (return_last_frame 实现多段连续)

即梦 API 特性:
  - 音频同步 (generate_audio): 自动生成与画面同步的音频
  - 返回尾帧 (return_last_frame): 尾帧可作为下一段视频首帧
  - 联网搜索 (web_search): 检索互联网内容提升生成质量
  - Draft 模式 (1.5-pro): 快速样片预览

配置文件: scripts/video_api_config.json
密钥: 环境变量 ARK_API_KEY (火山方舟)

用法:
  python ai_video_generator.py text2img --prompt "..." --model seedream-5.0-lite
  python ai_video_generator.py text2video --prompt "..." --model seedance-2.0
  python ai_video_generator.py img2video --prompt "..." --image first.png --last-frame last.png
  python ai_video_generator.py ref2video --prompt "..." --ref a.png,b.png
  python ai_video_generator.py vivid2video --prompt "..." --ref-video ref.mp4
  python ai_video_generator.py multimodal --prompt "..." --ref a.png,b.png --ref-video v.mp4 --ref_audio a.mp3
  python ai_video_generator.py batch --script drama.json
"""

import asyncio
import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ─── 配置加载 ─────────────────────────────────────────

_SCRIPT_DIR = Path(__file__).parent
_CONFIG_PATH = _SCRIPT_DIR / "video_api_config.json"


def _load_config() -> Dict:
    """加载 API 配置文件"""
    if not _CONFIG_PATH.exists():
        print(f"[ERROR] 配置文件不存在: {_CONFIG_PATH}")
        print("[INFO] 请复制 video_api_config.json 并填写 API 配置")
        raise FileNotFoundError(f"Config not found: {_CONFIG_PATH}")

    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    api_cfg = config.get("video_api", {})
    if not api_cfg.get("base_url"):
        print("[ERROR] video_api_config.json 中 base_url 未配置")
        raise ValueError("base_url not configured in video_api_config.json")

    return config


def _get_api_key(config: Dict) -> str:
    """从环境变量获取 API 密钥"""
    api_cfg = config.get("video_api", {})
    env_var = api_cfg.get("api_key_env", "ARK_API_KEY")
    key = os.environ.get(env_var, "").strip()
    if not key:
        doc_url = api_cfg.get("api_key_doc_url", "")
        print(f"[ERROR] 环境变量 {env_var} 未设置!")
        print(f"  设置方法: set {env_var}=your-key")
        if doc_url:
            print(f"  获取地址: {doc_url}")
        raise ValueError(f"{env_var} not set")
    return key


def _get_model_config(config: Dict, model: str) -> Dict:
    """获取模型配置"""
    models = config.get("models", {})
    if model not in models:
        available = ", ".join(models.keys()) if models else "(none configured)"
        print(f"[ERROR] 模型 '{model}' 未配置，可用: {available}")
        raise ValueError(f"Model '{model}' not in config")
    return models[model]


def _build_urls(config: Dict) -> Dict[str, str]:
    """从配置构建完整 API URL"""
    api_cfg = config["video_api"]
    base = api_cfg["base_url"].rstrip("/")
    return {
        "video_create": f"{base}{api_cfg.get('task_create_path', '/api/v3/contents/generations/tasks')}",
        "video_query": f"{base}{api_cfg.get('task_query_path', '/api/v3/contents/generations/tasks')}",
        "image_create": f"{base}{api_cfg.get('img_create_path', '/api/v3/images/generations')}",
    }


def _build_auth_header(config: Dict, api_key: str) -> Dict[str, str]:
    """构建认证请求头"""
    api_cfg = config["video_api"]
    header_name = api_cfg.get("auth_header", "Authorization")
    prefix = api_cfg.get("auth_prefix", "Bearer")
    return {
        header_name: f"{prefix} {api_key}",
        "Content-Type": "application/json",
    }


# ─── 即梦模型矩阵 ─────────────────────────────────────

JIMENG_MODELS = {
    # 视频生成模型
    "seedance-2.0": {
        "name": "Seedance 2.0",
        "type": "video",
        "features": ["text2video", "img2video", "firstlast2video", "multimodal_ref",
                      "audio_gen", "video_extend", "web_search"],
        "duration_range": [4, 15],
        "max_ref_images": 9,
        "max_ref_videos": 3,
        "max_ref_audios": 3,
    },
    "seedance-2.0-fast": {
        "name": "Seedance 2.0 Fast",
        "type": "video",
        "features": ["text2video", "img2video", "firstlast2video", "multimodal_ref",
                      "audio_gen", "web_search"],
        "duration_range": [4, 15],
        "max_ref_images": 9,
        "max_ref_videos": 3,
        "max_ref_audios": 3,
    },
    "seedance-2.0-mini": {
        "name": "Seedance 2.0 Mini",
        "type": "video",
        "features": ["text2video", "img2video", "firstlast2video"],
        "duration_range": [4, 10],
    },
    "seedance-1.5-pro": {
        "name": "Seedance 1.5 Pro",
        "type": "video",
        "features": ["text2video", "img2video", "firstlast2video", "draft_mode"],
        "duration_range": [4, 12],
    },
    # 图片生成模型
    "seedream-5.0-pro": {
        "name": "Seedream 5.0 Pro",
        "type": "image",
        "features": ["text2img", "img2img", "sequential_img", "web_search", "4k"],
    },
    "seedream-5.0": {
        "name": "Seedream 5.0",
        "type": "image",
        "features": ["text2img", "img2img", "sequential_img", "web_search", "4k"],
    },
    "seedream-5.0-lite": {
        "name": "Seedream 5.0 Lite",
        "type": "image",
        "features": ["text2img", "img2img", "sequential_img"],
    },
}

# 旧别名映射 → 新模型名
_MODEL_ALIASES = {
    "pro": "seedance-2.0",
    "lite": "seedance-2.0-fast",
    "seedance-2.0-pro": "seedance-2.0",
    "seedance-2.0-lite": "seedance-2.0-fast",
}


def _resolve_model(model: str) -> str:
    """解析模型别名，返回标准模型名"""
    return _MODEL_ALIASES.get(model, model)


# ─── 图片转 Base64 ────────────────────────────────────

def image_to_base64(image_path: str, max_size: int = 4096) -> str:
    """将图片转为 base64 字符串，自动缩放到 max_size 以内"""
    try:
        from PIL import Image
    except ImportError:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    img = Image.open(image_path)
    w, h = img.size
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    import io
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _path_to_data_url(path: str) -> str:
    """将本地文件路径转为 data URL (base64)"""
    b64 = image_to_base64(path)
    ext = Path(path).suffix.lower()
    mime = "image/jpeg"
    if ext == ".png":
        mime = "image/png"
    elif ext == ".webp":
        mime = "image/webp"
    return f"data:{mime};base64,{b64}"


def _resolve_media_url(source: str) -> str:
    """将媒体路径转为 URL: 已是 URL 则原样返回，本地文件转 data URL"""
    if source.startswith(("http://", "https://", "data:")):
        return source
    if os.path.exists(source):
        return _path_to_data_url(source)
    # 假设是 URL
    return source


# ─── Scene Prompt Builder ─────────────────────────────

STYLE_PROMPTS = {
    "anime": (
        "anime style, cel shading, vibrant colors, hair and clothes flowing in wind, "
        "fluid character animation, lively expressions, dynamic pose, "
        "9:16 vertical composition, cinematic"
    ),
    "qcomic": (
        "Chinese manhua comic style, bold outlines, dramatic expressions, "
        "exaggerated body language, hand gestures, dynamic action pose, "
        "9:16 vertical, cinematic composition"
    ),
    "realistic": (
        "photorealistic, cinematic lighting, shallow depth of field, "
        "natural micro-expressions, subtle body sway, breathing motion, "
        "hair moving naturally, 9:16 vertical, film grain, movie scene"
    ),
    "cute": (
        "kawaii chibi style, pastel colors, cute proportions, soft shading, "
        "bouncy cheerful movements, head tilts, expressive eyes blinking, "
        "9:16 vertical, warm lighting"
    ),
    "korean_manga": (
        "Korean modern romance manhwa style, low saturation Morandi warm palette, "
        "warm beige and soft brown base, muted gray-green, warm pink skin with peach blush, "
        "no high saturation colors, warm yellow LUT filter, "
        "center-focus close-up composition, protagonist 70% of frame, "
        "face at visual golden point, background slightly blurred, "
        "edges reserved for text overlay, fine white gold floating sparkle particles, "
        "edge cloud mist glow halo, subtle breathing scale oscillation, "
        "slow camera push-in toward face, "
        "4:3 horizontal composition, cinematic"
    ),
}

ACTION_PROMPTS = {
    "close_up": (
        "close-up shot from chest up, face filling frame, "
        "subtle head tilt, eyes moving, lips parting, breathing"
    ),
    "pan": (
        "slow horizontal pan shot, character walking or turning, "
        "tracking movement, environment parallax, wind in hair"
    ),
    "zoom_in": (
        "slow zoom in from wide to medium, character looking up, "
        "gradually focusing on subject, atmosphere building"
    ),
    "zoom_out": (
        "zoom out from close-up revealing wider scene, "
        "character stepping back, environment expanding, dramatic reveal"
    ),
    "static": (
        "medium wide shot, character standing with natural posture, "
        "gentle swaying, hair and clothes affected by ambient wind, "
        "background particles or leaves drifting"
    ),
    "dramatic": (
        "dramatic low angle shot, character stepping forward assertively, "
        "coat billowing, intense gaze, clenched fist, "
        "camera tilting up, dynamic lighting shift"
    ),
    "walking": (
        "full body shot, character walking towards camera, "
        "natural gait, arms swinging, environment scrolling past"
    ),
    "turning": (
        "character slowly turning around to face camera, "
        "hair flowing with the turn, expression changing"
    ),
    "sitting": (
        "character sitting, leaning forward with interest, "
        "hands gesturing, head nodding, natural subtle movements"
    ),
    "confronting": (
        "two characters facing each other tensely, "
        "one stepping closer, fists clenched, "
        "camera slowly pushing in, shadows deepening"
    ),
    "running": (
        "character running urgently, arms pumping, "
        "camera tracking alongside, background motion blur"
    ),
    "emotional": (
        "close-up of face, tears forming or eyes widening, "
        "hand reaching out, body trembling slightly, "
        "slow motion feel, shallow depth of field"
    ),
}

EMOTION_ACTION_HINTS = {
    "angry": "confronting",
    "sad": "emotional",
    "cheerful": "walking",
    "serious": "close_up",
    "romantic": "close_up",
    "calm": "sitting",
    "surprised": "turning",
    "fear": "running",
}

AMBIENT_MOTION = {
    "outdoor_day": "sunlight filtering through leaves, birds in background, gentle breeze",
    "outdoor_night": "moonlit, fireflies or city lights twinkling, cool night wind",
    "indoor_room": "curtains swaying, dust particles in light beam, clock ticking",
    "indoor_dark": "flickering candlelight, shadows shifting on walls",
    "urban": "neon signs flickering, cars passing, rain on window",
    "nature": "grass swaying, water rippling, clouds drifting slowly",
    "battle": "debris falling, energy crackling, wind intensifying",
}


def build_video_prompt(
    background: str,
    characters: List[Dict],
    action: str = "static",
    style: str = "anime",
    emotion: str = "",
    ambient: str = "",
    extra: str = "",
) -> str:
    """构建完整的视频生成提示词（v2: 强调动态感，避免僵硬画面）"""
    parts = []

    if background:
        parts.append(background)
    if ambient and ambient in AMBIENT_MOTION:
        parts.append(AMBIENT_MOTION[ambient])

    for char in characters:
        char_prompt = char.get("prompt", "")
        char_emotion = char.get("emotion", "")
        if char_prompt:
            parts.append(char_prompt)
        if char_emotion == "angry":
            parts.append("clenched fists, furrowed brows, stepping forward aggressively")
        elif char_emotion == "sad":
            parts.append("drooping shoulders, downcast eyes, hand wiping tear")
        elif char_emotion == "cheerful":
            parts.append("bright smile, bouncing slightly, hand gestures animated")
        elif char_emotion == "serious":
            parts.append("firm stance, steady gaze, slight nod")
        elif char_emotion == "romantic":
            parts.append("soft gaze, leaning closer, gentle hand reaching")
        elif char_emotion == "surprised":
            parts.append("eyes widening, mouth open, stepping back")

    effective_action = action
    if emotion and emotion in EMOTION_ACTION_HINTS:
        if action in ("static",):
            effective_action = EMOTION_ACTION_HINTS[emotion]

    action_prompt = ACTION_PROMPTS.get(effective_action, "")
    if action_prompt:
        parts.append(action_prompt)

    style_prompt = STYLE_PROMPTS.get(style, "")
    if style_prompt:
        parts.append(style_prompt)

    if extra:
        parts.append(extra)

    parts.append(
        "smooth natural motion, fluid movement, no stiffness, "
        "no static freeze, high quality animation, no text, no watermark"
    )

    return ", ".join(parts)


# ─── 请求体构建 ────────────────────────────────────────

def _build_video_content(
    prompt: str,
    first_frame: Optional[str] = None,
    last_frame: Optional[str] = None,
    ref_images: Optional[List[str]] = None,
    ref_videos: Optional[List[str]] = None,
    ref_audios: Optional[List[str]] = None,
) -> List[Dict]:
    """构建即梦视频 API 的 content 数组"""
    content = []

    if prompt:
        content.append({"type": "text", "text": prompt})

    if first_frame:
        url = _resolve_media_url(first_frame)
        content.append({
            "type": "image_url",
            "image_url": {"url": url, "role": "first_frame"}
        })

    if last_frame:
        url = _resolve_media_url(last_frame)
        content.append({
            "type": "image_url",
            "image_url": {"url": url, "role": "last_frame"}
        })

    if ref_images:
        for img in ref_images:
            url = _resolve_media_url(img)
            content.append({
                "type": "image_url",
                "image_url": {"url": url, "role": "reference_image"}
            })

    if ref_videos:
        for vid in ref_videos:
            url = _resolve_media_url(vid)
            content.append({
                "type": "video_url",
                "video_url": {"url": url, "role": "reference_video"}
            })

    if ref_audios:
        for aud in ref_audios:
            url = _resolve_media_url(aud)
            content.append({
                "type": "audio_url",
                "audio_url": {"url": url, "role": "reference_audio"}
            })

    return content


def _build_video_request_body(
    model_id: str,
    content: List[Dict],
    duration: float = 5,
    ratio: str = "9:16",
    resolution: Optional[str] = None,
    seed: int = -1,
    generate_audio: bool = True,
    return_last_frame: bool = False,
    web_search: bool = False,
    draft: bool = False,
    service_tier: Optional[str] = None,
) -> Dict:
    """构建即梦视频 API 完整请求体"""
    body = {
        "model": model_id,
        "content": content,
        "ratio": ratio,
        "duration": duration,
        "seed": seed,
        "generate_audio": generate_audio,
        "watermark": False,
        "return_last_frame": return_last_frame,
    }

    if resolution:
        body["resolution"] = resolution

    if web_search:
        body["tools"] = [{"type": "web_search"}]

    if service_tier:
        body["service_tier"] = service_tier

    if draft:
        body["draft"] = True

    return body


def _detect_mode(
    first_frame: Optional[str],
    last_frame: Optional[str],
    ref_images: Optional[List[str]],
    ref_videos: Optional[List[str]],
    ref_audios: Optional[List[str]],
) -> str:
    """根据输入参数自动检测生成模式"""
    has_first = bool(first_frame)
    has_last = bool(last_frame)
    has_ref_img = bool(ref_images)
    has_ref_vid = bool(ref_videos)
    has_ref_aud = bool(ref_audios)

    multi_ref = sum([has_ref_img, has_ref_vid, has_ref_aud]) >= 2
    if multi_ref or (has_ref_img and has_ref_vid) or has_ref_aud:
        return "multimodal"
    if has_ref_vid and not has_first:
        return "vivid2video"
    if has_ref_img and not has_first:
        return "ref2video"
    if has_first and has_last:
        return "firstlast2video"
    if has_first:
        return "img2video"
    return "text2video"


# ─── 视频生成 API 调用 ────────────────────────────────

async def create_video_task(
    prompt: str,
    model: str = "seedance-2.0",
    image_path: Optional[str] = None,
    duration: Optional[float] = None,
    aspect_ratio: str = "9:16",
    seed: int = -1,
    audio_prompt: Optional[str] = None,
    # ── v3 新增参数 ──
    last_frame_path: Optional[str] = None,
    ref_images: Optional[List[str]] = None,
    ref_videos: Optional[List[str]] = None,
    ref_audios: Optional[List[str]] = None,
    generate_audio: bool = True,
    return_last_frame: bool = False,
    web_search: bool = False,
    resolution: Optional[str] = None,
    ratio: Optional[str] = None,
    draft: bool = False,
    service_tier: Optional[str] = None,
) -> str:
    """
    创建视频生成任务，返回 task_id

    向后兼容: image_path/aspect_ratio/audio_prompt 参数保持不变
    v3 新增: last_frame_path/ref_images/ref_videos/ref_audios/generate_audio/return_last_frame/web_search
    """
    model = _resolve_model(model)
    config = _load_config()
    api_key = _get_api_key(config)
    model_cfg = _get_model_config(config, model)
    urls = _build_urls(config)
    headers = _build_auth_header(config, api_key)

    model_id = model_cfg["model_id"]
    if not model_id:
        raise ValueError(f"模型 '{model}' 的 model_id 未配置，请在 video_api_config.json 中填写")

    if duration is None:
        duration = model_cfg.get("default_duration", 5)
    max_dur = model_cfg.get("max_duration", 15)
    duration = min(duration, max_dur)

    # ratio 优先用新参数，否则回退到 aspect_ratio
    effective_ratio = ratio or aspect_ratio or "9:16"

    # 构建 content 数组
    content = _build_video_content(
        prompt=prompt,
        first_frame=image_path,
        last_frame=last_frame_path,
        ref_images=ref_images,
        ref_videos=ref_videos,
        ref_audios=ref_audios,
    )

    # 构建请求体
    payload = _build_video_request_body(
        model_id=model_id,
        content=content,
        duration=duration,
        ratio=effective_ratio,
        resolution=resolution or model_cfg.get("resolution"),
        seed=seed,
        generate_audio=generate_audio,
        return_last_frame=return_last_frame,
        web_search=web_search,
        draft=draft,
        service_tier=service_tier,
    )

    mode = _detect_mode(image_path, last_frame_path, ref_images, ref_videos, ref_audios)

    # 发送请求
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(urls["video_create"], json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except ImportError:
        import requests
        resp = requests.post(urls["video_create"], json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()

    task_id = data.get("id") or data.get("data", {}).get("task_id")
    if not task_id:
        raise ValueError(f"No task_id in response: {data}")

    print(f"[OK] Video task created: {task_id} (mode={mode}, model={model}, duration={duration}s)")
    return task_id


async def query_video_task(task_id: str) -> Dict:
    """查询视频生成任务状态"""
    config = _load_config()
    api_key = _get_api_key(config)
    urls = _build_urls(config)
    headers = _build_auth_header(config, api_key)

    url = f"{urls['video_query']}/{task_id}"

    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except ImportError:
        import requests
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

    status = data.get("status", "").lower()
    if status in ("succeeded", "complete", "completed"):
        output = data.get("output", {})
        if isinstance(output, dict):
            video_url = output.get("video_url") or output.get("url", "")
            last_frame_url = output.get("last_frame_url", "")
        elif isinstance(output, list) and output:
            video_url = output[0].get("video_url") or output[0].get("url", "")
            last_frame_url = output[0].get("last_frame_url", "")
        else:
            video_url = data.get("data", {}).get("video_url", "")
            last_frame_url = ""
        return {"status": "succeeded", "video_url": video_url, "last_frame_url": last_frame_url, "raw": data}
    elif status in ("failed", "error"):
        error_msg = data.get("error", {}).get("message", str(data))
        return {"status": "failed", "error": error_msg, "raw": data}
    else:
        return {"status": "processing", "raw": data}


async def cancel_video_task(task_id: str) -> bool:
    """取消视频生成任务"""
    config = _load_config()
    api_key = _get_api_key(config)
    urls = _build_urls(config)
    headers = _build_auth_header(config, api_key)

    url = f"{urls['video_query']}/{task_id}"

    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(url, headers=headers)
            return resp.status_code in (200, 204)
    except ImportError:
        import requests
        resp = requests.delete(url, headers=headers, timeout=30)
        return resp.status_code in (200, 204)


# ─── 图片生成 API 调用 (Seedream) ─────────────────────

async def create_image_task(
    prompt: str,
    model: str = "seedream-5.0-lite",
    size: str = "2048x2048",
    n: int = 1,
    seed: int = -1,
    ref_image: Optional[str] = None,
    web_search: bool = False,
    guidance_scale: Optional[float] = None,
) -> str:
    """
    创建图片生成任务 (即梦 Seedream)，返回 task_id

    支持:
      - text2img: 文字 → 图片
      - img2img: 参考图 + 文字 → 图片 (需提供 ref_image)
      - web_search: 联网检索增强 (Pro/5.0 版本)
      - 4K 分辨率 (Pro/5.0 版本)
    """
    model = _resolve_model(model)
    config = _load_config()
    api_key = _get_api_key(config)
    model_cfg = _get_model_config(config, model)
    urls = _build_urls(config)
    headers = _build_auth_header(config, api_key)

    model_id = model_cfg["model_id"]
    if not model_id:
        raise ValueError(f"模型 '{model}' 的 model_id 未配置")

    payload = {
        "model": model_id,
        "prompt": prompt,
        "size": size,
        "n": n,
        "seed": seed,
    }

    if ref_image:
        payload["ref_image"] = _resolve_media_url(ref_image)

    if web_search:
        payload["tools"] = [{"type": "web_search"}]

    if guidance_scale is not None:
        payload["guidance_scale"] = guidance_scale

    try:
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(urls["image_create"], json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except ImportError:
        import requests
        resp = requests.post(urls["image_create"], json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()

    # 即梦图片 API 返回格式
    images = data.get("data", {}).get("images", [])
    if images:
        task_id = data.get("id") or images[0].get("id", "")
        print(f"[OK] Image task created: {task_id} (model={model}, size={size})")
        return task_id

    task_id = data.get("id") or data.get("data", {}).get("task_id", "")
    if not task_id:
        raise ValueError(f"No task_id/image in response: {data}")

    print(f"[OK] Image task created: {task_id} (model={model}, size={size})")
    return task_id


async def query_image_task(task_id: str) -> Dict:
    """查询图片生成任务状态"""
    config = _load_config()
    api_key = _get_api_key(config)
    urls = _build_urls(config)
    headers = _build_auth_header(config, api_key)

    # 即梦图片 API 可能直接在 POST 响应中返回结果，也支持查询
    url = f"{urls['image_create']}/{task_id}"

    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except ImportError:
        import requests
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

    status = data.get("status", "").lower()
    if status in ("succeeded", "complete", "completed") or not status:
        images = data.get("data", {}).get("images", [])
        if images:
            urls_list = [img.get("url", "") for img in images if img.get("url")]
            if urls_list:
                return {"status": "succeeded", "image_urls": urls_list, "raw": data}
        return {"status": "processing", "raw": data}
    elif status in ("failed", "error"):
        error_msg = data.get("error", {}).get("message", str(data))
        return {"status": "failed", "error": error_msg, "raw": data}
    else:
        return {"status": "processing", "raw": data}


# ─── 下载 ─────────────────────────────────────────────

async def download_video(url: str, output_path: str) -> str:
    """下载视频文件到本地"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
    except ImportError:
        import requests
        resp = requests.get(url, timeout=120, allow_redirects=True)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(resp.content)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[OK] Video downloaded: {output_path} ({size_mb:.1f} MB)")
    return output_path


async def download_image(url: str, output_path: str) -> str:
    """下载图片文件到本地"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
    except ImportError:
        import requests
        resp = requests.get(url, timeout=60, allow_redirects=True)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(resp.content)

    print(f"[OK] Image downloaded: {output_path}")
    return output_path


async def download_last_frame(url: str, output_path: str) -> str:
    """下载尾帧图片到本地"""
    return await download_image(url, output_path)


# ─── 等待任务完成 ──────────────────────────────────────

async def wait_for_video(
    task_id: str,
    poll_interval: int = None,
    timeout: int = None,
    output_dir: str = ".temp/ai_videos",
    filename: Optional[str] = None,
) -> Optional[str]:
    """等待视频生成完成并下载"""
    config = _load_config()
    poll_cfg = config.get("polling", {})
    if poll_interval is None:
        poll_interval = poll_cfg.get("interval_seconds", 5)
    if timeout is None:
        timeout = poll_cfg.get("timeout_seconds", 600)

    start = time.time()
    output_path_obj = Path(output_dir)
    output_path_obj.mkdir(parents=True, exist_ok=True)

    while time.time() - start < timeout:
        result = await query_video_task(task_id)
        status = result.get("status", "")

        if status == "succeeded":
            video_url = result.get("video_url", "")
            if not video_url:
                return None
            if filename is None:
                filename = f"{task_id}.mp4"
            local_path = str(output_path_obj / filename)
            await download_video(video_url, local_path)

            # 如果有尾帧，也下载
            last_frame_url = result.get("last_frame_url", "")
            if last_frame_url:
                lf_path = str(output_path_obj / filename.replace(".mp4", "_lastframe.png"))
                await download_last_frame(last_frame_url, lf_path)
                print(f"[OK] Last frame saved: {lf_path}")

            return local_path
        elif status == "failed":
            error = result.get("error", "Unknown error")
            print(f"[ERROR] Video generation failed: {error}")
            return None
        else:
            elapsed = int(time.time() - start)
            print(f"[INFO] Task {task_id} processing... ({elapsed}s elapsed)")
            await asyncio.sleep(poll_interval)

    print(f"[ERROR] Timeout waiting for task {task_id} ({timeout}s)")
    return None


async def wait_for_image(
    task_id: str,
    poll_interval: int = None,
    timeout: int = None,
    output_dir: str = ".temp/ai_images",
    filename: Optional[str] = None,
) -> Optional[str]:
    """等待图片生成完成并下载"""
    config = _load_config()
    poll_cfg = config.get("polling", {})
    if poll_interval is None:
        poll_interval = poll_cfg.get("interval_seconds", 5)
    if timeout is None:
        timeout = poll_cfg.get("timeout_seconds", 300)

    start = time.time()
    output_path_obj = Path(output_dir)
    output_path_obj.mkdir(parents=True, exist_ok=True)

    while time.time() - start < timeout:
        result = await query_image_task(task_id)
        status = result.get("status", "")

        if status == "succeeded":
            image_urls = result.get("image_urls", [])
            if not image_urls:
                return None
            if filename is None:
                filename = f"{task_id}.png"
            local_path = str(output_path_obj / filename)
            await download_image(image_urls[0], local_path)
            return local_path
        elif status == "failed":
            error = result.get("error", "Unknown error")
            print(f"[ERROR] Image generation failed: {error}")
            return None
        else:
            elapsed = int(time.time() - start)
            print(f"[INFO] Image task {task_id} processing... ({elapsed}s elapsed)")
            await asyncio.sleep(poll_interval)

    print(f"[ERROR] Timeout waiting for image task {task_id} ({timeout}s)")
    return None


# ─── 便捷函数 ─────────────────────────────────────────

async def text2img(
    prompt: str,
    model: str = "seedream-5.0-lite",
    size: str = "2048x2048",
    output_dir: str = ".temp/ai_images",
    filename: Optional[str] = None,
    web_search: bool = False,
    ref_image: Optional[str] = None,
) -> Optional[str]:
    """文生图便捷函数：文字 → 图片"""
    task_id = await create_image_task(
        prompt=prompt,
        model=model,
        size=size,
        web_search=web_search,
        ref_image=ref_image,
    )
    return await wait_for_image(task_id, output_dir=output_dir, filename=filename)


async def text2video(
    prompt: str,
    model: str = "seedance-2.0",
    duration: float = 5,
    output_dir: str = ".temp/ai_videos",
    filename: Optional[str] = None,
    generate_audio: bool = True,
    web_search: bool = False,
    resolution: Optional[str] = None,
    ratio: str = "9:16",
) -> Optional[str]:
    """文生视频便捷函数"""
    task_id = await create_video_task(
        prompt=prompt,
        model=model,
        duration=duration,
        ratio=ratio,
        generate_audio=generate_audio,
        web_search=web_search,
        resolution=resolution,
    )
    return await wait_for_video(task_id, output_dir=output_dir, filename=filename)


async def img2video(
    prompt: str,
    image_path: str,
    last_frame_path: Optional[str] = None,
    model: str = "seedance-2.0",
    duration: float = 5,
    output_dir: str = ".temp/ai_videos",
    filename: Optional[str] = None,
    generate_audio: bool = True,
    return_last_frame: bool = False,
    resolution: Optional[str] = None,
    ratio: str = "adaptive",
) -> Optional[str]:
    """图生视频便捷函数：首帧(±尾帧) → 视频"""
    task_id = await create_video_task(
        prompt=prompt,
        model=model,
        image_path=image_path,
        last_frame_path=last_frame_path,
        duration=duration,
        ratio=ratio,
        generate_audio=generate_audio,
        return_last_frame=return_last_frame,
        resolution=resolution,
    )
    return await wait_for_video(task_id, output_dir=output_dir, filename=filename)


async def ref2video(
    prompt: str,
    ref_images: List[str],
    model: str = "seedance-2.0",
    duration: float = 5,
    output_dir: str = ".temp/ai_videos",
    filename: Optional[str] = None,
    generate_audio: bool = True,
    return_last_frame: bool = False,
    resolution: Optional[str] = None,
    ratio: str = "adaptive",
) -> Optional[str]:
    """参考图生视频便捷函数：参考图(≤9张) → 视频"""
    task_id = await create_video_task(
        prompt=prompt,
        model=model,
        ref_images=ref_images,
        duration=duration,
        ratio=ratio,
        generate_audio=generate_audio,
        return_last_frame=return_last_frame,
        resolution=resolution,
    )
    return await wait_for_video(task_id, output_dir=output_dir, filename=filename)


async def vivid2video(
    prompt: str,
    ref_videos: List[str],
    model: str = "seedance-2.0",
    duration: float = 5,
    output_dir: str = ".temp/ai_videos",
    filename: Optional[str] = None,
    ref_images: Optional[List[str]] = None,
    generate_audio: bool = True,
    return_last_frame: bool = False,
    resolution: Optional[str] = None,
    ratio: str = "adaptive",
) -> Optional[str]:
    """参考视频复刻便捷函数：参考视频(≤3段) → 新视频"""
    task_id = await create_video_task(
        prompt=prompt,
        model=model,
        ref_videos=ref_videos,
        ref_images=ref_images,
        duration=duration,
        ratio=ratio,
        generate_audio=generate_audio,
        return_last_frame=return_last_frame,
        resolution=resolution,
    )
    return await wait_for_video(task_id, output_dir=output_dir, filename=filename)


async def multimodal_gen(
    prompt: str,
    ref_images: Optional[List[str]] = None,
    ref_videos: Optional[List[str]] = None,
    ref_audios: Optional[List[str]] = None,
    first_frame: Optional[str] = None,
    last_frame: Optional[str] = None,
    model: str = "seedance-2.0",
    duration: float = -1,
    output_dir: str = ".temp/ai_videos",
    filename: Optional[str] = None,
    generate_audio: bool = True,
    return_last_frame: bool = False,
    web_search: bool = False,
    resolution: Optional[str] = None,
    ratio: str = "adaptive",
) -> Optional[str]:
    """多模态参考生视频便捷函数：图片+视频+音频+文本 → 视频"""
    task_id = await create_video_task(
        prompt=prompt,
        model=model,
        image_path=first_frame,
        last_frame_path=last_frame,
        ref_images=ref_images,
        ref_videos=ref_videos,
        ref_audios=ref_audios,
        duration=duration,
        ratio=ratio,
        generate_audio=generate_audio,
        return_last_frame=return_last_frame,
        web_search=web_search,
        resolution=resolution,
    )
    return await wait_for_video(task_id, output_dir=output_dir, filename=filename)


# ─── 批量生成短剧场景视频 ─────────────────────────────

async def generate_scene_videos(
    script_path: str,
    output_dir: str = ".temp/ai_videos",
    model: str = "seedance-2.0",
    style: str = "anime",
    max_concurrent: int = 3,
    ratio: Optional[str] = None,
) -> List[str]:
    """从短剧剧本生成所有场景的AI视频

    Args:
        ratio: 画面宽高比 (16:9/4:3/9:16/1:1/3:4/21:9/adaptive)，
               None 时从剧本 JSON 的 aspect_ratio 字段读取，默认 9:16
    """
    config = _load_config()
    model = _resolve_model(model)
    model_cfg = _get_model_config(config, model)

    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    scenes = script.get("scenes", [])
    title = script.get("title", "short_drama")
    script_style = script.get("style", style)

    # 画面比例：优先用传入参数，其次读剧本字段，默认 9:16
    effective_ratio = ratio or script.get("aspect_ratio", "9:16")

    print(f"\n{'='*60}")
    print(f"  短剧AI视频生成: {title}")
    print(f"  场景数: {len(scenes)} | 模型: {model} | 画质: {model_cfg.get('resolution', '?')}")
    print(f"  画面比例: {effective_ratio}")
    print(f"{'='*60}\n")

    tasks_info = []
    for scene in scenes:
        scene_id = scene.get("id", 0)
        background = scene.get("background_prompt", "")
        characters = scene.get("characters", [])
        action = scene.get("action", "static")
        ref_image = scene.get("ref_image", None)

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
            style=script_style,
            emotion=emotion,
        )

        num_dialogues = len(dialogues)
        narration = scene.get("narration", "")
        duration = max(4, num_dialogues * 3 + (3 if narration else 0))
        duration = min(duration, model_cfg.get("max_duration", 15))

        tasks_info.append({
            "scene_id": scene_id,
            "prompt": prompt,
            "image_path": ref_image,
            "duration": duration,
            "filename": f"scene_{scene_id:04d}.mp4",
        })

    semaphore = asyncio.Semaphore(max_concurrent)
    results = [None] * len(tasks_info)

    async def _generate_one(idx, info):
        async with semaphore:
            task_id = await create_video_task(
                prompt=info["prompt"],
                model=model,
                image_path=info.get("image_path"),
                duration=info["duration"],
                ratio=effective_ratio,
            )
            video_path = await wait_for_video(
                task_id=task_id,
                output_dir=output_dir,
                filename=info["filename"],
            )
            results[idx] = video_path

    coros = [_generate_one(i, info) for i, info in enumerate(tasks_info)]
    await asyncio.gather(*coros, return_exceptions=True)

    print(f"\n[OK] Scene video generation complete: {sum(1 for r in results if r)} / {len(results)} succeeded")
    return results


# ─── 暴露给 short_drama_renderer 用的常量 ─────────────

def get_available_models() -> Dict:
    """获取可用模型列表（从配置文件读取）"""
    try:
        config = _load_config()
        return config.get("models", {})
    except (FileNotFoundError, ValueError):
        return {}


def get_video_models() -> Dict:
    """获取视频生成模型列表"""
    models = get_available_models()
    return {k: v for k, v in models.items() if v.get("type") == "video"}


def get_image_models() -> Dict:
    """获取图片生成模型列表"""
    models = get_available_models()
    return {k: v for k, v in models.items() if v.get("type") == "image"}


def get_model_features(model: str) -> List[str]:
    """获取模型支持的功能列表"""
    model = _resolve_model(model)
    jimeng = JIMENG_MODELS.get(model, {})
    return jimeng.get("features", [])


# 模块级别兼容常量
_AVAILABLE_MODELS_CACHE = None

def _get_available_models_cached() -> Dict:
    global _AVAILABLE_MODELS_CACHE
    if _AVAILABLE_MODELS_CACHE is None:
        _AVAILABLE_MODELS_CACHE = get_available_models()
    return _AVAILABLE_MODELS_CACHE


# ─── CLI 入口 ─────────────────────────────────────────

async def _main():
    import argparse
    parser = argparse.ArgumentParser(
        description="AI视频/图片生成模块 v3 — 即梦 Seedream/Seedance 满血版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
生成模式:
  text2img      文字 → 图片 (Seedream)
  text2video    文字 → 视频 (Seedance)
  img2video     首帧(±尾帧) → 视频
  ref2video     参考图(≤9张) → 视频
  vivid2video   参考视频(≤3段) → 新视频
  multimodal    图片+视频+音频+文本 → 视频
  batch         从短剧剧本JSON批量生成

示例:
  python ai_video_generator.py text2img --prompt "城堡广场" --model seedream-5.0-lite
  python ai_video_generator.py img2video --prompt "女子转身" --image first.png --last-frame last.png
  python ai_video_generator.py multimodal --prompt "[图1]角色 [图2]场景" --ref a.png,b.png --ref-video v.mp4
        """
    )

    subparsers = parser.add_subparsers(dest="mode", required=True)

    # 公共参数
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--prompt", required=True, help="生成描述提示词")
    common.add_argument("--model", help="即梦模型名")
    common.add_argument("--output-dir", default=".temp/ai_videos")
    common.add_argument("--output", help="输出文件名")
    common.add_argument("--duration", type=float, default=5, help="视频时长(秒)")
    common.add_argument("--seed", type=int, default=-1, help="随机种子, -1为随机")

    # 媒体参数
    media = argparse.ArgumentParser(add_help=False)
    media.add_argument("--image", help="首帧图片路径/URL")
    media.add_argument("--last-frame", help="尾帧图片路径/URL")
    media.add_argument("--ref", help="参考图路径/URL(s), 多张逗号分隔(最多9张)")
    media.add_argument("--ref-video", help="参考视频路径/URL(s), 多段逗号分隔(最多3段)")
    media.add_argument("--ref-audio", help="参考音频路径/URL(s), 多段逗号分隔(最多3段)")

    # 即梦特色参数
    jimeng = argparse.ArgumentParser(add_help=False)
    jimeng.add_argument("--generate-audio", action="store_true", default=True,
                        help="生成同步音频 (默认开启)")
    jimeng.add_argument("--no-audio", action="store_false", dest="generate_audio",
                       help="不生成音频")
    jimeng.add_argument("--return-last-frame", action="store_true",
                       help="返回尾帧图像, 用于连续视频生成")
    jimeng.add_argument("--web-search", action="store_true",
                       help="开启联网搜索增强")
    jimeng.add_argument("--resolution", help="分辨率: 480p/720p/1080p")
    jimeng.add_argument("--ratio", default="9:16",
                       help="宽高比: 16:9/4:3/1:1/3:4/9:16/21:9/adaptive")
    jimeng.add_argument("--draft", action="store_true",
                       help="Draft样片模式 (仅1.5-pro)")

    # ── text2img ──
    img_parser = subparsers.add_parser("text2img", parents=[common],
                                        help="文生图: 文字→图片 (Seedream)")
    img_parser.add_argument("--size", default="2048x2048", help="图片分辨率")
    img_parser.add_argument("--n", type=int, default=1, help="生成数量")
    img_parser.add_argument("--ref-image", help="参考图路径 (img2img模式)")
    img_parser.add_argument("--guidance-scale", type=float, help="提示词遵循度 1-10")

    # ── text2video ──
    subparsers.add_parser("text2video", parents=[common, jimeng],
                          help="文生视频: 文字→视频")

    # ── img2video ──
    subparsers.add_parser("img2video", parents=[common, media, jimeng],
                          help="图生视频: 首帧(±尾帧)→视频")

    # ── ref2video ──
    subparsers.add_parser("ref2video", parents=[common, media, jimeng],
                          help="参考图生视频: 参考图(≤9张)→视频")

    # ── vivid2video ──
    subparsers.add_parser("vivid2video", parents=[common, media, jimeng],
                          help="参考视频复刻: 参考视频(≤3段)→新视频")

    # ── multimodal ──
    subparsers.add_parser("multimodal", parents=[common, media, jimeng],
                          help="多模态参考: 图+视频+音频+文本全能融合")

    # ── batch ──
    batch_parser = subparsers.add_parser("batch", help="从短剧剧本JSON批量生成")
    batch_parser.add_argument("--script", required=True, help="剧本JSON路径")
    batch_parser.add_argument("--model", default="seedance-2.0")
    batch_parser.add_argument("--style", default="anime")
    batch_parser.add_argument("--output-dir", default=".temp/ai_videos")
    batch_parser.add_argument("--max-concurrent", type=int, default=3)

    args = parser.parse_args()

    def _parse_list(val):
        if not val:
            return None
        return [v.strip() for v in val.split(",") if v.strip()]

    if args.mode == "text2img":
        result = await text2img(
            prompt=args.prompt,
            model=args.model or "seedream-5.0-lite",
            size=args.size,
            output_dir=args.output_dir,
            filename=args.output,
            web_search=args.web_search if hasattr(args, "web_search") else False,
            ref_image=args.ref_image if hasattr(args, "ref_image") else None,
        )
    elif args.mode == "text2video":
        result = await text2video(
            prompt=args.prompt,
            model=args.model or "seedance-2.0",
            duration=args.duration,
            output_dir=args.output_dir,
            filename=args.output,
            generate_audio=args.generate_audio,
            web_search=args.web_search,
            resolution=args.resolution,
            ratio=args.ratio,
        )
    elif args.mode == "img2video":
        if not args.image:
            print("[ERROR] img2video 模式必须指定 --image")
            sys.exit(1)
        result = await img2video(
            prompt=args.prompt,
            image_path=args.image,
            last_frame_path=args.last_frame,
            model=args.model or "seedance-2.0",
            duration=args.duration,
            output_dir=args.output_dir,
            filename=args.output,
            generate_audio=args.generate_audio,
            return_last_frame=args.return_last_frame,
            resolution=args.resolution,
            ratio=args.ratio,
        )
    elif args.mode == "ref2video":
        refs = _parse_list(args.ref)
        if not refs:
            print("[ERROR] ref2video 模式必须指定 --ref")
            sys.exit(1)
        result = await ref2video(
            prompt=args.prompt,
            ref_images=refs,
            model=args.model or "seedance-2.0",
            duration=args.duration,
            output_dir=args.output_dir,
            filename=args.output,
            generate_audio=args.generate_audio,
            return_last_frame=args.return_last_frame,
            resolution=args.resolution,
            ratio=args.ratio,
        )
    elif args.mode == "vivid2video":
        ref_vids = _parse_list(args.ref_video)
        if not ref_vids:
            print("[ERROR] vivid2video 模式必须指定 --ref-video")
            sys.exit(1)
        result = await vivid2video(
            prompt=args.prompt,
            ref_videos=ref_vids,
            model=args.model or "seedance-2.0",
            duration=args.duration,
            output_dir=args.output_dir,
            filename=args.output,
            ref_images=_parse_list(args.ref),
            generate_audio=args.generate_audio,
            return_last_frame=args.return_last_frame,
            resolution=args.resolution,
            ratio=args.ratio,
        )
    elif args.mode == "multimodal":
        result = await multimodal_gen(
            prompt=args.prompt,
            ref_images=_parse_list(args.ref),
            ref_videos=_parse_list(args.ref_video),
            ref_audios=_parse_list(args.ref_audio),
            first_frame=args.image,
            last_frame=args.last_frame,
            model=args.model or "seedance-2.0",
            duration=args.duration,
            output_dir=args.output_dir,
            filename=args.output,
            generate_audio=args.generate_audio,
            return_last_frame=args.return_last_frame,
            web_search=args.web_search,
            resolution=args.resolution,
            ratio=args.ratio,
        )
    elif args.mode == "batch":
        await generate_scene_videos(
            script_path=args.script,
            output_dir=args.output_dir,
            model=args.model,
            style=args.style,
            max_concurrent=args.max_concurrent,
        )
        return

    if result:
        print(f"\n[DONE] Saved: {result}")
    else:
        print("\n[FAIL] Generation failed")


if __name__ == "__main__":
    asyncio.run(_main())
