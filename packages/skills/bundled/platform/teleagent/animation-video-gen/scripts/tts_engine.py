#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS 配音引擎 v3 — 六层级回退链 + 指数退避重试 + 片段级降级

回退链（按优先级）:
  L0: 火山引擎 TTS    — 最佳音质，复用 ARK_API_KEY，支持多音色（需配置）
  L1: edge-tts        — 高音质，支持情感调节，但依赖微软API（可能403）
  L2: gTTS (Google)   — 免费云TTS，无需API Key，无情感参数
  L3: pyttsx3         — 本地离线，质量一般，速度较慢
  L4: SAPI5 (Win)     — Windows Speech API，稳定但音色少、无情感参数
  L5: FFmpeg beep     — 极端降级：生成静音占位，确保流程不中断

特性:
  - 每片段独立重试（指数退避，默认3次）
  - 片段级降级：L0失败自动尝试L1→L2→...→L5，不影响其他片段
  - 多服务商独立：微软(edge-tts/pyttsx3/SAPI5) + Google(gTTS) + 火山引擎(TTS)
  - 预检（health_check）：批量生成前探测可用后端
  - 进度回调：每完成一个片段调用 progress_callback(index, total)

音色参考见 references/tts_voices.md
"""

import asyncio
import json
import os
import platform
import subprocess
import sys
import shutil
import time
import traceback
from pathlib import Path
from typing import Callable, Dict, List, Optional


# ═══════════════════════════════════════════════════════
#  角色音色映射预设
# ═══════════════════════════════════════════════════════

VOICE_PRESETS = {
    "male_young": "zh-CN-YunxiNeural",
    "male_deep": "zh-CN-YunjianNeural",
    "male_narrator": "zh-CN-YunyangNeural",
    "male_warm": "zh-CN-YunxiNeural",
    "male_sharp": "zh-CN-YunjianNeural",
    "female_young": "zh-CN-XiaoxiaoNeural",
    "female_gentle": "zh-CN-XiaoyiNeural",
    "female_strong": "zh-CN-XiaoxiaoNeural",       # 原XiaochenNeural已失效(NoAudioReceived)
    "female_mature": "zh-CN-XiaoxiaoNeural",        # 原XiaomoNeural已失效(NoAudioReceived)
    "female_sweet": "zh-CN-XiaoyiNeural",
    "child": "zh-CN-XiaoyiNeural",                  # 原XiaohanNeural已失效(NoAudioReceived)
    "android": "zh-CN-YunxiaNeural",
    "elder_male": "zh-CN-YunjianNeural",
    "elder_female": "zh-CN-YunyangNeural",           # 原XiaomoNeural已失效(NoAudioReceived)
}

# 火山引擎 TTS 音色映射（需要 ARK_API_KEY）
# 文档: https://www.volcengine.com/docs/6561/97465
VOLCANO_VOICE_PRESETS = {
    "male_young": "zh_male_chunhou",
    "male_deep": "zh_male_cancan",
    "male_narrator": "zh_male_jieshuo",
    "female_young": "zh_female_qingxin",
    "female_gentle": "zh_female_wenrou",
    "female_strong": "zh_female_ganlian",
    "female_mature": "zh_female_chengshu",
    "female_sweet": "zh_female_tianmei",
    "child": "zh_female_tongsheng",
    "narrator": "zh_male_jieshuo",
}

# 火山引擎 TTS API 配置
VOLCANO_TTS_CONFIG = {
    "base_url": "https://openspeech.bytedance.com/api/v1/auc",
    "api_key_env": "ARK_API_KEY",
    "default_speaker": "zh_female_qingxin",
    "default_format": "mp3",
}

# edge-tts 情感风格映射
EMOTION_STYLES = {
    "angry": "angry", "cheerful": "cheerful", "sad": "sad",
    "serious": "serious", "friendly": "friendly", "gentle": "gentle",
    "narrative": "narrative", "newscast": "newscast",
    "terrified": "sad", "excited": "cheerful",
    "whisper": "gentle", "shout": "angry",
    "sarcastic": "serious", "romantic": "gentle",
}

# 情感→语速/音高/音量/情感强度 映射
EMOTION_TUNING = {
    "angry":       {"rate": "+30%", "pitch": "+5Hz",  "volume": "+20%", "style_degree": 2.0, "style": "angry"},
    "sad":         {"rate": "-20%", "pitch": "-3Hz",  "volume": "-10%", "style_degree": 1.8, "style": "sad"},
    "cheerful":    {"rate": "+15%", "pitch": "+3Hz",  "volume": "+5%",  "style_degree": 1.5, "style": "cheerful"},
    "serious":     {"rate": "-10%", "pitch": "-1Hz",  "volume": "+0%",  "style_degree": 1.5, "style": "serious"},
    "romantic":    {"rate": "-15%", "pitch": "+1Hz",  "volume": "-5%",  "style_degree": 1.6, "style": "gentle"},
    "calm":        {"rate": "-5%",  "pitch": "+0Hz",  "volume": "+0%",  "style_degree": 1.0, "style": None},
    "surprised":   {"rate": "+25%", "pitch": "+8Hz",  "volume": "+10%", "style_degree": 2.0, "style": "cheerful"},
    "fear":        {"rate": "+20%", "pitch": "+6Hz",  "volume": "-5%",  "style_degree": 1.8, "style": "sad"},
    "excited":     {"rate": "+25%", "pitch": "+4Hz",  "volume": "+10%", "style_degree": 1.8, "style": "cheerful"},
    "whisper":     {"rate": "-25%", "pitch": "-2Hz",  "volume": "-25%", "style_degree": 0.8, "style": "gentle"},
    "shout":       {"rate": "+10%", "pitch": "+3Hz",  "volume": "+30%", "style_degree": 2.0, "style": "angry"},
    "sarcastic":   {"rate": "-15%", "pitch": "-1Hz",  "volume": "+0%",  "style_degree": 1.3, "style": "serious"},
}

# SAPI5 中文音色名称（Windows 注册表中常见的）
SAPI5_ZH_VOICES = [
    "Microsoft Huihui Desktop",        # Windows 8.1+
    "Microsoft Kangkang Desktop",      # Windows 8.1+
    "Microsoft Yaoyao Desktop",        # Windows 8.1+ (移动端风格)
    "Microsoft Zhiwei Desktop",        # Windows 10+
]


# ═══════════════════════════════════════════════════════
#  TTS 后端实现
# ═══════════════════════════════════════════════════════

async def _tts_volcano(
    text: str, output_path: str,
    speaker: str = "", lang: str = "zh-CN",
    speed: float = 1.0, volume: float = 1.0,
) -> str:
    """L0: 火山引擎 TTS — 最佳音质，复用 ARK_API_KEY，支持多音色

    使用火山方舟语音合成 HTTP API，需配置 ARK_API_KEY 环境变量。
    音色列表见 VOLCANO_VOICE_PRESETS。
    """
    api_key = os.environ.get(VOLCANO_TTS_CONFIG["api_key_env"], "").strip()
    if not api_key:
        raise RuntimeError(f'{VOLCANO_TTS_CONFIG["api_key_env"]} not set')

    try:
        import httpx
    except ImportError:
        _pip_install("httpx")
        import httpx

    if not speaker:
        speaker = VOLCANO_TTS_CONFIG["default_speaker"]

    # 火山引擎语音合成 API（OpenSpeech 兼容接口）
    url = VOLCANO_TTS_CONFIG["base_url"] + "/tts"
    headers = {
        "Authorization": f"Bearer;{api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "speaker": speaker,
        "text": text,
        "audio_config": {
            "format": VOLCANO_TTS_CONFIG["default_format"],
            "sample_rate": 24000,
            "speed": speed,
            "volume": volume,
        },
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Volcano TTS HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        # 响应中音频数据可能在 data 或 audio 字段
        audio_b64 = data.get("data") or data.get("audio") or data.get("audio_data")
        if not audio_b64:
            # 可能直接返回二进制
            if resp.headers.get("content-type", "").startswith("audio/"):
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                return output_path
            raise RuntimeError(f"Volcano TTS no audio data in response: {str(data)[:200]}")

        import base64
        audio_bytes = base64.b64decode(audio_b64)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)

    return output_path


async def _tts_edge(
    text: str, voice: str, output_path: str,
    rate: str = "+0%", volume: str = "+0%", pitch: str = "+0Hz",
    style: Optional[str] = None, style_degree: float = 1.0,
) -> str:
    """L1: edge-tts — 最佳音质，支持情感参数"""
    try:
        import edge_tts
    except ImportError:
        _pip_install("edge-tts")
        import edge_tts

    kwargs = {"text": text, "voice": voice, "rate": rate, "volume": volume, "pitch": pitch}
    if style and style in EMOTION_STYLES:
        try:
            comm = edge_tts.Communicate(**kwargs, style=EMOTION_STYLES[style])
        except Exception:
            comm = edge_tts.Communicate(**kwargs)
    else:
        comm = edge_tts.Communicate(**kwargs)

    await comm.save(output_path)
    return output_path


def _tts_pyttsx3(
    text: str, output_path: str,
    rate: int = 180, volume: float = 1.0,
) -> str:
    """L2: pyttsx3 — 本地离线TTS，质量一般但稳定"""
    try:
        import pyttsx3
    except ImportError:
        _pip_install("pyttsx3")
        import pyttsx3

    engine = pyttsx3.init()
    # 查找中文音色
    voices = engine.getProperty("voices")
    zh_voice = None
    for v in voices:
        if "chinese" in v.name.lower() or "zh" in v.id.lower() or "huihui" in v.id.lower():
            zh_voice = v.id
            break
    if zh_voice:
        engine.setProperty("voice", zh_voice)

    engine.setProperty("rate", rate)
    engine.setProperty("volume", volume)
    engine.save_to_file(text, output_path)
    engine.runAndWait()
    return output_path


def _tts_gtts(
    text: str, output_path: str,
    lang: str = "zh-CN", slow: bool = False,
) -> str:
    """L2: gTTS (Google Text-to-Speech) — 免费云TTS，无需API Key

    限制：无情感参数，无多音色选择（每语言一个默认音色），需网络。
    生成为 MP3 格式，音质中等但稳定性好。作为微软系列后端的独立备选。
    """
    try:
        from gtts import gTTS
    except ImportError:
        _pip_install("gTTS")
        from gtts import gTTS

    tts = gTTS(text=text, lang=lang, slow=slow)
    tts.save(output_path)
    return output_path


def _tts_sapi5(
    text: str, output_path: str,
    voice_name: Optional[str] = None, rate: int = 0, volume: int = 100,
) -> str:
    """L3: Windows SAPI5 — PowerShell Speech API，稳定但音色有限"""
    if platform.system() != "Windows":
        raise RuntimeError("SAPI5 only available on Windows")

    # 查找可用中文音色
    if not voice_name:
        voice_name = _find_sapi5_zh_voice()
    if not voice_name:
        raise RuntimeError("No Chinese SAPI5 voice found")

    ps_cmd = (
        "Add-Type -AssemblyName System.Speech; "
        "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "try { $synth.SelectVoice($args[0]) } catch {}; "
        "$synth.Rate = [int]$args[1]; "
        "$synth.Volume = [int]$args[2]; "
        "$synth.SetOutputToWaveFile($args[3]); "
        "$synth.Speak($args[4]); "
        "$synth.Dispose()"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd,
         voice_name, str(rate), str(volume), str(output_path), text],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"SAPI5 failed: {result.stderr}")

    # WAV → MP3 (用 ffmpeg 转码，更兼容后续流程)
    if os.path.exists(output_path) and output_path.endswith(".mp3"):
        wav_path = output_path.replace(".mp3", ".wav")
        os.rename(output_path, wav_path)
        ffmpeg = _find_ffmpeg()
        if ffmpeg:
            subprocess.run(
                [ffmpeg, "-y", "-i", wav_path, "-c:a", "libmp3lame", "-q:a", "4", output_path],
                capture_output=True,
            )
            os.remove(wav_path) if os.path.exists(wav_path) else None
        else:
            os.rename(wav_path, output_path)  # 保留 WAV

    return output_path


def _tts_silence_placeholder(output_path: str, duration: float = 2.0) -> str:
    """L4: 极端降级 — 生成静音占位音频，确保视频合成流程不中断"""
    ffmpeg = _find_ffmpeg()
    if ffmpeg:
        subprocess.run(
            [ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono",
             "-t", str(duration), "-c:a", "libmp3lame", "-q:a", "4", output_path],
            capture_output=True,
        )
    else:
        # 写入最小有效 MP3 头（约 0.1 秒静音）
        with open(output_path, "wb") as f:
            f.write(b'\xff\xfb\x90\x00' + b'\x00' * 8192)
    return output_path


# ═══════════════════════════════════════════════════════
#  核心：带重试和回退的 TTS 生成
# ═══════════════════════════════════════════════════════

class TTSBackend:
    """TTS 后端枚举"""
    VOLCANO = "volcano"
    EDGE_TTS = "edge-tts"
    GTTS = "gTTS"
    PYTTSX3 = "pyttsx3"
    SAPI5 = "sapi5"
    SILENCE = "silence"

    # 回退链顺序（六层级：火山→edge→Google→pyttsx3→SAPI5→静音）
    FALLBACK_CHAIN = [VOLCANO, EDGE_TTS, GTTS, PYTTSX3, SAPI5, SILENCE]

    @classmethod
    def chain_for_platform(cls) -> List[str]:
        """根据平台返回可用的回退链"""
        chain = [cls.VOLCANO, cls.EDGE_TTS, cls.GTTS, cls.PYTTSX3]
        if platform.system() == "Windows":
            chain.append(cls.SAPI5)
        chain.append(cls.SILENCE)
        return chain


def _classify_error(exc: Exception) -> str:
    """对异常进行分类，决定重试策略"""
    msg = str(exc).lower()
    exc_type = type(exc).__name__

    # 认证/授权错误 → 不可重试，应换后端
    if "403" in msg or "forbidden" in msg or "unauthorized" in msg or "token" in msg:
        return "auth_error"

    # 限速 → 可重试，需等待
    if "429" in msg or "rate" in msg or "throttl" in msg or "limit" in msg:
        return "rate_limit"

    # 网络错误 → 可重试
    if any(kw in msg for kw in ["timeout", "connection", "network", "reset", "eof"]):
        return "network_error"

    # 输入错误 → 不可重试
    if "invalid" in msg or "empty" in msg or "no text" in msg:
        return "input_error"

    # 其他 → 尝试重试
    return "unknown_error"


async def generate_tts_with_fallback(
    text: str,
    voice: str,
    output_path: str,
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
    style: Optional[str] = None,
    style_degree: float = 1.0,
    max_retries: int = 3,
    backends: Optional[List[str]] = None,
    skip_backends: Optional[set] = None,
) -> str:
    """
    带回退链的 TTS 生成：按优先级尝试每个后端，每个后端指数退避重试

    Args:
        text: 要转换的文字
        voice: edge-tts 音色名称
        output_path: 输出音频路径
        rate/volume/pitch/style/style_degree: TTS 参数
        max_retries: 每个后端的最大重试次数
        backends: 自定义回退链（默认按平台自动选择）
        skip_backends: 已知不可用的后端集合（从预检中获取）

    Returns:
        生成的音频文件路径
    """
    if skip_backends is None:
        skip_backends = set()
    if backends is None:
        backends = TTSBackend.chain_for_platform()

    last_error = None

    for backend in backends:
        if backend in skip_backends:
            continue

        for attempt in range(1, max_retries + 1):
            try:
                if backend == TTSBackend.VOLCANO:
                    volcano_speaker = VOLCANO_VOICE_PRESETS.get("narrator", "")
                    await _tts_volcano(text, output_path, speaker=volcano_speaker)
                elif backend == TTSBackend.EDGE_TTS:
                    await _tts_edge(text, voice, output_path, rate, volume, pitch, style, style_degree)
                elif backend == TTSBackend.GTTS:
                    _tts_gtts(text, output_path, lang="zh-CN")
                elif backend == TTSBackend.PYTTSX3:
                    # 将百分比参数转换为 pyttsx3 参数
                    py_rate = 180 + int(rate.replace("%", "").replace("+", "").replace("-", "") or 0) * 1.8
                    if rate.startswith("-"):
                        py_rate = 180 - (180 - py_rate)
                    py_rate = int(max(80, min(400, py_rate)))
                    py_volume = 1.0
                    _tts_pyttsx3(text, output_path, rate=py_rate, volume=py_volume)
                elif backend == TTSBackend.SAPI5:
                    sapi_rate = 0
                    if rate.startswith("+"):
                        sapi_rate = int(rate.replace("+", "").replace("%", "")) // 10
                    elif rate.startswith("-"):
                        sapi_rate = -int(rate.replace("-", "").replace("%", "")) // 10
                    _tts_sapi5(text, output_path, rate=sapi_rate)
                elif backend == TTSBackend.SILENCE:
                    dur = max(len(text) * 0.15, 1.5)
                    _tts_silence_placeholder(output_path, duration=dur)

                # 成功
                backend_label = backend if backend != TTSBackend.SILENCE else "silence(placeholder)"
                if attempt > 1:
                    print(f"  [OK] {backend_label} retry#{attempt}: {os.path.basename(output_path)}")
                else:
                    print(f"  [OK] {backend_label}: {os.path.basename(output_path)} ({len(text)} chars)")
                return output_path

            except Exception as exc:
                last_error = exc
                error_type = _classify_error(exc)

                if error_type == "input_error":
                    # 输入错误，任何后端都无法修复
                    print(f"  [ERROR] Input error, skipping all backends: {exc}")
                    _tts_silence_placeholder(output_path, duration=1.5)
                    return output_path

                if error_type == "auth_error":
                    # 认证错误，该后端不可用，跳到下一个
                    print(f"  [WARN] {backend} auth error (attempt {attempt}): {exc}")
                    break  # 跳出重试循环，尝试下一个后端

                # 可重试错误（rate_limit / network / unknown）
                if attempt < max_retries:
                    wait = 2 ** attempt  # 指数退避: 2s, 4s, 8s
                    print(f"  [WARN] {backend} error (attempt {attempt}/{max_retries}), "
                          f"retrying in {wait}s: {exc}")
                    await asyncio.sleep(wait)
                else:
                    print(f"  [WARN] {backend} failed after {max_retries} attempts: {exc}")

        # 当前后端全部重试失败，尝试下一个
        if backend != backends[-1]:
            next_backend = backends[backends.index(backend) + 1]
            if next_backend not in skip_backends:
                print(f"  [FALLBACK] {backend} → {next_backend}")

    # 所有后端都失败，生成静音占位
    print(f"  [ERROR] All TTS backends failed. Generating silence placeholder.")
    _tts_silence_placeholder(output_path, duration=max(len(text) * 0.15, 1.5))
    return output_path


# ═══════════════════════════════════════════════════════
#  预检（health check）
# ═══════════════════════════════════════════════════════

async def tts_health_check() -> Dict[str, bool]:
    """
    预检所有 TTS 后端的可用性

    Returns:
        {"volcano": True, "edge-tts": True, "gTTS": True, "pyttsx3": False, "sapi5": True, "silence": True}
    """
    results = {}
    chain = TTSBackend.chain_for_platform()

    for backend in chain:
        try:
            if backend == TTSBackend.VOLCANO:
                api_key = os.environ.get(VOLCANO_TTS_CONFIG["api_key_env"], "").strip()
                if api_key:
                    # 快速探测：发送极短文本
                    test_path = os.path.join(os.environ.get("TEMP", "/tmp"), "_tts_health_volcano.mp3")
                    await asyncio.wait_for(
                        _tts_volcano("测", test_path, speaker=VOLCANO_TTS_CONFIG["default_speaker"]),
                        timeout=15,
                    )
                    if os.path.exists(test_path):
                        os.remove(test_path)
                    results[backend] = True
                else:
                    results[backend] = False
            elif backend == TTSBackend.EDGE_TTS:
                # 快速测试：尝试初始化 Communicate
                import edge_tts
                comm = edge_tts.Communicate("测试", "zh-CN-YunxiNeural")
                # 不实际生成，只验证能否创建（403 会在 save 时才暴露）
                # 所以做一个最小测试
                test_path = os.path.join(os.environ.get("TEMP", "/tmp"), "_tts_health.mp3")
                await asyncio.wait_for(comm.save(test_path), timeout=10)
                if os.path.exists(test_path):
                    os.remove(test_path)
                results[backend] = True
            elif backend == TTSBackend.GTTS:
                # gTTS: 尝试生成极短音频
                test_path = os.path.join(os.environ.get("TEMP", "/tmp"), "_tts_health_gtts.mp3")
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: _tts_gtts("测", test_path)
                )
                if os.path.exists(test_path):
                    os.remove(test_path)
                results[backend] = True
            elif backend == TTSBackend.PYTTSX3:
                import pyttsx3
                engine = pyttsx3.init()
                engine.stop()
                results[backend] = True
            elif backend == TTSBackend.SAPI5:
                if platform.system() == "Windows":
                    voice = _find_sapi5_zh_voice()
                    results[backend] = voice is not None
                else:
                    results[backend] = False
            elif backend == TTSBackend.SILENCE:
                results[backend] = True  # 静音总是可用
        except Exception as e:
            results[backend] = False
            print(f"  [HEALTH] {backend}: UNAVAILABLE ({e})")

    available = [b for b, ok in results.items() if ok]
    print(f"[HEALTH] TTS backends: {', '.join(available)} available")
    return results


# ═══════════════════════════════════════════════════════
#  批量 TTS 生成（保留旧接口兼容性）
# ═══════════════════════════════════════════════════════

async def generate_tts(
    text: str,
    voice: str,
    output_path: str,
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
    style: Optional[str] = None,
    style_degree: float = 1.0,
):
    """
    单段 TTS 生成（兼容旧接口，内部走回退链）
    """
    return await generate_tts_with_fallback(
        text, voice, output_path,
        rate=rate, volume=volume, pitch=pitch,
        style=style, style_degree=style_degree,
    )


async def generate_drama_tts(
    script_path: str,
    output_dir: str,
    voice_mapping: Optional[Dict[str, str]] = None,
    default_voice: str = "zh-CN-YunxiNeural",
    max_retries: int = 3,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    fast_check: bool = True,
):
    """
    从短剧剧本生成所有对白的 TTS 音频（v3：六层级回退链+重试）

    Args:
        script_path: 剧本JSON路径
        output_dir: 音频输出目录
        voice_mapping: 角色名→音色映射
        default_voice: 默认音色
        max_retries: 每片段最大重试次数
        progress_callback: 进度回调 fn(current, total)
        fast_check: 是否在批量生成前做预检
    """
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    voice_mapping = voice_mapping or {}

    # 预检：探测可用后端
    skip_backends = set()
    if fast_check:
        print("[INFO] Running TTS health check...")
        health = await tts_health_check()
        for backend, available in health.items():
            if not available:
                skip_backends.add(backend)
        available_backends = [b for b in TTSBackend.chain_for_platform() if b not in skip_backends]
        if available_backends:
            print(f"[INFO] Primary TTS backend: {available_backends[0]}")
        else:
            print("[WARN] No TTS backend available, will use silence placeholders")

    # 收集所有 TTS 任务
    tasks_info = []  # (text, voice, output_file, params)

    for scene in script.get("scenes", []):
        scene_id = scene.get("id", 0)

        # 旁白
        narration = scene.get("narration", "")
        if narration:
            narrator_voice = voice_mapping.get("旁白", voice_mapping.get("narrator", "zh-CN-YunyangNeural"))
            audio_file = str(output_path / f"tts_{scene_id:04d}_narration.mp3")
            tasks_info.append((narration, narrator_voice, audio_file, {
                "rate": "-5%", "style": "narrative"
            }))

        # 对白
        for dlg_idx, dlg in enumerate(scene.get("dialogues", [])):
            speaker = dlg.get("speaker", "")
            text = dlg.get("text", "")
            emotion = dlg.get("emotion", "calm")

            voice = voice_mapping.get(speaker, default_voice)
            audio_file = str(output_path / f"tts_{scene_id:04d}_{dlg_idx:03d}.mp3")

            tuning = EMOTION_TUNING.get(emotion, EMOTION_TUNING["calm"])
            tasks_info.append((text, voice, audio_file, {
                "rate": tuning["rate"],
                "pitch": tuning["pitch"],
                "volume": tuning["volume"],
                "style": tuning.get("style"),
                "style_degree": tuning["style_degree"],
            }))

    total = len(tasks_info)
    print(f"\n[INFO] TTS: {total} segments to generate (backends: {TTSBackend.chain_for_platform()})")

    # 逐片段生成（串行，便于回退和进度跟踪）
    results = []
    success_count = 0
    fallback_count = 0
    silence_count = 0

    for idx, (text, voice, audio_file, params) in enumerate(tasks_info):
        try:
            result = await generate_tts_with_fallback(
                text=text,
                voice=voice,
                output_path=audio_file,
                rate=params.get("rate", "+0%"),
                volume=params.get("volume", "+0%"),
                pitch=params.get("pitch", "+0Hz"),
                style=params.get("style"),
                style_degree=params.get("style_degree", 1.0),
                max_retries=max_retries,
                skip_backends=skip_backends,
            )
            results.append(result)
            success_count += 1
        except Exception as e:
            # 极端异常（不应到达这里，因为 generate_tts_with_fallback 自带静音降级）
            print(f"  [ERROR] Segment {idx+1}/{total} failed: {e}")
            _tts_silence_placeholder(audio_file, duration=1.5)
            results.append(audio_file)
            silence_count += 1

        # 进度回调
        if progress_callback:
            progress_callback(idx + 1, total)

        # 简单进度显示
        if (idx + 1) % 5 == 0 or idx + 1 == total:
            print(f"  [PROGRESS] {idx + 1}/{total} segments done")

    # 统计使用的后端
    print(f"\n[OK] TTS generation complete:")
    print(f"  Total: {total} | Success: {success_count} | Silence placeholders: {silence_count}")

    return results


# ═══════════════════════════════════════════════════════
#  辅助函数
# ═══════════════════════════════════════════════════════

def get_audio_duration(audio_path: str) -> float:
    """获取音频时长（秒）"""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(audio_path)
        return len(audio) / 1000.0
    except ImportError:
        pass
    # Fallback: ffprobe
    ffmpeg = _find_ffmpeg()
    if ffmpeg:
        ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")
        result = subprocess.run(
            [ffprobe, "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True,
        )
        try:
            return float(result.stdout.strip())
        except ValueError:
            pass
    return 2.0  # 默认


_ALLOWED_PACKAGES = {"edge-tts", "pyttsx3", "gTTS", "httpx", "imageio-ffmpeg", "moviepy", "Pillow"}

def _pip_install(package: str):
    """自动安装 pip 包（仅允许白名单内的包）"""
    base_name = package.split("==")[0].split(">=")[0].split("<=")[0].strip()
    if base_name not in _ALLOWED_PACKAGES:
        raise RuntimeError(f"Package '{base_name}' not in allowlist, rejected for security")
    print(f"[INFO] Installing {package}...")
    subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)


def _find_ffmpeg() -> Optional[str]:
    """查找 FFmpeg 路径"""
    ffmpeg = os.environ.get("FFMPEG_PATH") or _which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def _which(name: str) -> Optional[str]:
    """跨平台 which（使用 shutil.which，无 subprocess 注入风险）"""
    return shutil.which(name)


def _find_sapi5_zh_voice() -> Optional[str]:
    """查找 Windows SAPI5 中文音色（使用 pyttsx3，无 PowerShell 注入风险）"""
    if platform.system() != "Windows":
        return None

    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        for v in voices:
            if 'zh' in v.id or 'Huihui' in v.name:
                return v.id
        return voices[0].id if voices else None
    except Exception:
        pass

    return SAPI5_ZH_VOICES[0] if SAPI5_ZH_VOICES else None


# ═══════════════════════════════════════════════════════
#  CLI 入口
# ═══════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="短剧TTS配音引擎 v3 (六层级回退)")
    parser.add_argument("--script", required=True, help="剧本JSON路径")
    parser.add_argument("--output-dir", default=".temp/short_drama/audio")
    parser.add_argument("--voices", default=None, help="角色音色映射JSON路径")
    parser.add_argument("--max-retries", type=int, default=3, help="每片段最大重试次数")
    parser.add_argument("--no-health-check", action="store_true", help="跳过预检")
    parser.add_argument("--test", action="store_true", help="测试模式：生成单条TTS")
    parser.add_argument("--health-check", action="store_true", help="仅运行预检")

    args = parser.parse_args()

    voice_mapping = None
    if args.voices and os.path.exists(args.voices):
        with open(args.voices, "r", encoding="utf-8") as f:
            voice_mapping = json.load(f)

    if args.health_check:
        results = asyncio.run(tts_health_check())
        for backend, available in results.items():
            status = "AVAILABLE" if available else "UNAVAILABLE"
            print(f"  {backend}: {status}")
        return

    if args.test:
        asyncio.run(generate_tts_with_fallback(
            "这是一段测试配音", "zh-CN-YunxiNeural", "test_tts.mp3",
        ))
    else:
        asyncio.run(generate_drama_tts(
            args.script, args.output_dir, voice_mapping,
            max_retries=args.max_retries,
            fast_check=not args.no_health_check,
        ))


if __name__ == "__main__":
    main()
