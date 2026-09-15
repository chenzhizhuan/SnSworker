#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动画视频生成 - 依赖安装脚本
自动检测并安装 Manim、pycairo、ffmpeg 等依赖
"""

import subprocess
import sys
import shutil
import os
import platform


# pip安装允许列表（安全约束：仅允许以下包）
_ALLOWED_PACKAGES = {
    "manim", "pycairo", "imageio-ffmpeg", "Pillow",
    "edge-tts", "httpx", "requests", "pydub",
    "moviepy", "gTTS", "pyttsx3",
}


def run(args, check=True):
    """执行命令（仅接受list args，避免shell注入）"""
    if isinstance(args, str):
        raise TypeError("run() 仅接受list形式参数以避免shell注入，请使用 run([cmd, arg1, arg2, ...])")
    print(f"[RUN] {' '.join(str(a) for a in args)}")
    result = subprocess.run(args, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"[ERROR] {result.stderr}")
        return False
    return True


def is_installed(name):
    """检查命令行工具是否安装"""
    return shutil.which(name) is not None


def pip_install(package):
    """使用 pip 安装 Python 包（仅允许白名单中的包）"""
    # 验证包名在允许列表中
    for pkg in package.split():
        base_name = pkg.split("==")[0].split(">=")[0].split("<=")[0].strip()
        if base_name not in _ALLOWED_PACKAGES:
            print(f"[ERROR] Package '{base_name}' not in allowlist, rejected for security")
            return False
    return run([sys.executable, "-m", "pip", "install"] + package.split())


def setup_manim():
    """安装 Manim 和 pycairo"""
    print("\n=== 安装 Manim 动画引擎 ===")
    
    try:
        import manim
        print(f"[OK] Manim 已安装: {manim.__version__}")
    except ImportError:
        print("[INFO] 正在安装 manim + pycairo...")
        pip_install("manim pycairo")
        try:
            import manim
            print(f"[OK] Manim 安装成功: {manim.__version__}")
        except ImportError:
            print("[WARN] Manim 安装失败，尝试使用 conda...")
            run(["conda", "install", "-c", "conda-forge", "manim", "pycairo", "-y"], check=False)


def setup_ffmpeg():
    """安装 FFmpeg"""
    print("\n=== 安装 FFmpeg ===")
    
    if is_installed("ffmpeg"):
        print("[OK] FFmpeg 已安装")
        return
    
    # 尝试使用 imageio-ffmpeg 作为后备
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"[OK] imageio-ffmpeg 可用: {ffmpeg_exe}")
        return
    except ImportError:
        pass
    
    # 尝试通过 pip 安装 imageio-ffmpeg
    print("[INFO] 正在安装 imageio-ffmpeg...")
    pip_install("imageio-ffmpeg")
    
    try:
        import imageio_ffmpeg
        print(f"[OK] imageio-ffmpeg 安装成功")
    except ImportError:
        print("[WARN] imageio-ffmpeg 安装失败")
        print("[INFO] 请手动安装 FFmpeg:")
        print("  Windows: choco install ffmpeg")
        print("  或从 https://www.gyan.dev/ffmpeg/builds/ 下载")


def setup_pillow():
    """确保 Pillow 已安装（帧图片处理需要）"""
    try:
        from PIL import Image
        print("[OK] Pillow 已安装")
    except ImportError:
        print("[INFO] 正在安装 Pillow...")
        pip_install("Pillow")


def setup_edge_tts():
    """安装 edge-tts（短剧TTS配音需要）"""
    print("\n=== 安装 edge-tts ===")
    try:
        import edge_tts
        print(f"[OK] edge-tts 已安装")
    except ImportError:
        print("[INFO] 正在安装 edge-tts...")
        pip_install("edge-tts")
        try:
            import edge_tts
            print("[OK] edge-tts 安装成功")
        except ImportError:
            print("[WARN] edge-tts 安装失败，短剧配音功能不可用")
            print("[INFO] 手动安装: pip install edge-tts")


def setup_httpx():
    """安装 httpx（异步HTTP客户端，Seedance API调用需要）"""
    print("\n=== 安装 httpx ===")
    try:
        import httpx
        print(f"[OK] httpx 已安装: {httpx.__version__}")
    except ImportError:
        print("[INFO] 正在安装 httpx...")
        pip_install("httpx")
        try:
            import httpx
            print(f"[OK] httpx 安装成功: {httpx.__version__}")
        except ImportError:
            print("[WARN] httpx 安装失败，将使用 requests 同步模式（性能较差）")


def setup_requests():
    """确保 requests 已安装（httpx 的回退方案）"""
    try:
        import requests
        print("[OK] requests 已安装")
    except ImportError:
        print("[INFO] 正在安装 requests...")
        pip_install("requests")


def setup_pydub():
    """安装 pydub（音频处理需要）"""
    try:
        from pydub import AudioSegment
        print("[OK] pydub 已安装")
    except ImportError:
        print("[INFO] 正在安装 pydub...")
        pip_install("pydub")


def setup_gtts():
    """安装 gTTS（TTS回退链 L2：Google 免费云TTS，无API Key可用）"""
    print("\n=== 安装 gTTS ===")
    try:
        import gtts
        print(f"[OK] gTTS 已安装: {getattr(gtts, '__version__', 'unknown')}")
    except ImportError:
        print("[INFO] 正在安装 gTTS...")
        pip_install("gTTS")
        try:
            import gtts
            print("[OK] gTTS 安装成功")
        except ImportError:
            print("[WARN] gTTS 安装失败，TTS回退链 L2 不可用（不影响 L0/L1）")


def setup_moviepy():
    """安装 moviepy（可选：视频剪辑增强）"""
    try:
        import moviepy
        print(f"[OK] moviepy 已安装: {getattr(moviepy, '__version__', 'unknown')}")
    except ImportError:
        print("[INFO] 正在安装 moviepy...")
        pip_install("moviepy")
        try:
            import moviepy
            print("[OK] moviepy 安装成功")
        except ImportError:
            print("[WARN] moviepy 安装失败（可选依赖，不影响主流程）")


def setup_pyttsx3():
    """安装 pyttsx3（TTS回退链 L3：本地离线TTS）"""
    print("\n=== 安装 pyttsx3 ===")
    try:
        import pyttsx3
        print("[OK] pyttsx3 已安装")
    except ImportError:
        print("[INFO] 正在安装 pyttsx3...")
        pip_install("pyttsx3")
        try:
            import pyttsx3
            print("[OK] pyttsx3 安装成功")
        except ImportError:
            print("[WARN] pyttsx3 安装失败（TTS回退链 L3 不可用）")


def check_chinese_font():
    """检查中文字体可用性"""
    print("\n=== 检查中文字体 ===")
    
    chinese_fonts = ["SimHei", "Microsoft YaHei", "SimSun", "KaiTi"]
    available = False
    
    try:
        from PIL import ImageFont
        for font_name in chinese_fonts:
            try:
                ImageFont.truetype(font_name + ".ttf", 24)
                print(f"[OK] 中文字体可用: {font_name}")
                available = True
                break
            except (OSError, IOError):
                continue
    except ImportError:
        pass
    
    if not available:
        print("[WARN] 未找到常用中文字体，Manim 动画中的中文可能无法正常显示")
        print("[INFO] 请安装 SimHei 或 Microsoft YaHei 字体")


def main():
    print("=" * 50)
    print("  动画视频生成 - 依赖安装工具")
    print("=" * 50)
    print(f"Python: {sys.version}")
    print(f"Platform: {platform.system()} {platform.release()}")
    
    setup_ffmpeg()
    setup_manim()
    setup_pillow()
    setup_httpx()
    setup_requests()
    setup_edge_tts()
    setup_gtts()
    setup_pyttsx3()
    setup_pydub()
    setup_moviepy()
    check_chinese_font()
    
    print("\n" + "=" * 50)
    print("  依赖安装完成")
    print("=" * 50)
    
    # 最终验证
    print("\n=== 最终验证 ===")
    all_ok = True
    
    try:
        import manim
        print(f"[OK] Manim {manim.__version__}")
    except ImportError:
        print("[FAIL] Manim 未安装")
        all_ok = False
    
    try:
        from PIL import Image
        print("[OK] Pillow")
    except ImportError:
        print("[FAIL] Pillow 未安装")
        all_ok = False
    
    if is_installed("ffmpeg"):
        print("[OK] FFmpeg (系统)")
    else:
        try:
            import imageio_ffmpeg
            print(f"[OK] FFmpeg (imageio-ffmpeg)")
        except ImportError:
            print("[FAIL] FFmpeg 未安装")
            all_ok = False
    
    try:
        import httpx
        print(f"[OK] httpx {httpx.__version__}")
    except ImportError:
        print("[WARN] httpx 未安装 (AI视频API异步调用不可用，将用requests同步模式)")

    try:
        import edge_tts
        print("[OK] edge-tts")
    except ImportError:
        print("[FAIL] edge-tts 未安装 (短剧配音不可用)")

    if all_ok:
        print("\n所有依赖已就绪，可以开始生成动画视频！")
    else:
        print("\n部分依赖安装失败，请按提示手动安装。")
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
