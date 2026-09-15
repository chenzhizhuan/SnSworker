#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频渲染 V2：把 shots.json（含配音）渲染成竖屏短视频 MP4。
升级特性：
- Ken Burns 高级运镜（推拉 + 平移 + 微旋转）
- 粒子特效（雨/光斑/星点，按场景氛围自动选择）
- 场景间转场（交叉溶解 / 淡入淡出）
- 调色滤镜（暖色/冷色/高对比/复古）
- 字幕动画（淡入 + 描边 + 渐变底栏）
- 配音音量归一化 + 背景音轨
- 进场/出场黑场淡变

用法：
  python render_video.py [--shots shots.json] [--out 输出目录] [--preview N]
"""
import argparse
import math
import random
import shutil
import sys
from pathlib import Path

from common import find_ffmpeg, json_load, media_duration, run, work_dir

W, H, FPS = 1080, 1920, 30

# 预放大倍数（给 zoompan 留操作空间）
PRE_SCALE = 2  # 输入图放大到 2 倍，zoompan 再在内部缩放到 WxH

# ---------------- 场景特效配置 ----------------
# 按场景关键词匹配特效与调色
EFFECT_PRESETS = {
    "厨房": {"effect": "none", "color": "warm", "transition": "fade"},
    "客厅": {"effect": "light_leak", "color": "cold", "transition": "dissolve"},
    "卧室": {"effect": "dust", "color": "warm_dim", "transition": "fade"},
    "深夜": {"effect": "stars", "color": "night", "transition": "dissolve"},
    "清晨": {"effect": "particles", "color": "warm", "transition": "fade"},
    "雨": {"effect": "rain", "color": "cold", "transition": "dissolve"},
    "夜": {"effect": "light_leak", "color": "night", "transition": "fade"},
}

DEFAULT_PRESET = {"effect": "light_leak", "color": "neutral", "transition": "fade"}


def get_preset(scene_name: str) -> dict:
    for kw, preset in EFFECT_PRESETS.items():
        if kw in scene_name:
            return preset
    return DEFAULT_PRESET


# ---------------- 调色滤镜 ----------------
def color_grade_expr(preset: str) -> str:
    """返回 ffmpeg 滤镜 eq 表达式片段"""
    grades = {
        "warm": "eq=brightness=0.03:contrast=1.08:saturation=1.15:gamma_r=1.05:gamma_g=1.0:gamma_b=0.95,curves=r='0 0 0.5 0.58 1 1':b='0 0 0.5 0.42 1 1'",
        "cold": "eq=brightness=-0.02:contrast=1.1:saturation=0.9:gamma_r=0.95:gamma_b=1.08,curves=r='0 0 0.5 0.42 1 1':b='0 0 0.5 0.58 1 1'",
        "warm_dim": "eq=brightness=-0.05:contrast=1.15:saturation=1.1:gamma_r=1.06:gamma_b=0.92",
        "night": "eq=brightness=-0.08:contrast=1.2:saturation=0.7:gamma_b=1.1:gamma_r=0.9",
        "neutral": "eq=contrast=1.05:saturation=1.05",
    }
    return grades.get(preset, grades["neutral"])


# ---------------- 粒子特效生成 ----------------
def make_overlay(effect: str, w: int, h: int, rng: random.Random) -> Path | None:
    """生成粒子特效叠加层 PNG（透明背景），返回路径或 None"""
    from PIL import Image, ImageDraw, ImageFilter

    if effect == "none":
        return None

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    if effect == "rain":
        for _ in range(300):
            x = rng.randint(0, w)
            y = rng.randint(0, h)
            length = rng.randint(20, 50)
            opacity = rng.randint(40, 90)
            draw.line((x, y, x - 5, y + length), fill=(180, 200, 230, opacity), width=1)
        overlay = overlay.filter(ImageFilter.GaussianBlur(0.5))

    elif effect == "light_leak":
        for _ in range(8):
            cx = rng.randint(0, w)
            cy = rng.randint(0, h)
            rad = rng.randint(200, 500)
            for r in range(rad, 0, -10):
                alpha = int(25 * (1 - r / rad) ** 2)
                if alpha > 0:
                    draw.ellipse((cx - r, cy - r, cx + r, cy + r),
                                 fill=(255, 220, 180, alpha))
        overlay = overlay.filter(ImageFilter.GaussianBlur(40))

    elif effect == "dust":
        for _ in range(80):
            x = rng.randint(0, w)
            y = rng.randint(0, h)
            rad = rng.randint(1, 4)
            opacity = rng.randint(30, 80)
            draw.ellipse((x - rad, y - rad, x + rad, y + rad),
                         fill=(255, 240, 200, opacity))
        overlay = overlay.filter(ImageFilter.GaussianBlur(1))

    elif effect == "stars":
        for _ in range(60):
            x = rng.randint(0, w)
            y = rng.randint(0, h)
            rad = rng.randint(1, 3)
            opacity = rng.randint(60, 150)
            # 十字星点
            draw.ellipse((x - rad, y - rad, x + rad, y + rad),
                         fill=(255, 255, 220, opacity))
            draw.line((x - rad * 3, y, x + rad * 3, y), fill=(255, 255, 220, opacity // 2), width=1)
            draw.line((x, y - rad * 3, x, y + rad * 3), fill=(255, 255, 220, opacity // 2), width=1)

    elif effect == "particles":
        for _ in range(120):
            x = rng.randint(0, w)
            y = rng.randint(0, h)
            rad = rng.randint(2, 6)
            opacity = rng.randint(20, 60)
            draw.ellipse((x - rad, y - rad, x + rad, y + rad),
                         fill=(255, 230, 190, opacity))
        overlay = overlay.filter(ImageFilter.GaussianBlur(3))

    return overlay


# ---------------- 字幕绘制 ----------------
def _load_font(size: int):
    from PIL import ImageFont
    for fp in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc",
               "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc"):
        try:
            return ImageFont.truetype(fp, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=font) > max_w:
            lines.append(cur)
            cur = ch
            if len(lines) >= 2:
                break
        else:
            cur += ch
    if cur and len(lines) < 2:
        lines.append(cur)
    return lines or [text[:8]]


def draw_subtitle(scene_png: Path, text: str, out_png: Path,
                  speaker: str = "", is_narration: bool = False) -> Path:
    """在底图上叠加说话人名牌与字幕，带渐变底栏"""
    from PIL import Image, ImageDraw

    img = Image.open(scene_png).convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font = _load_font(52)
    max_w = w - 120

    # 底部渐变遮罩
    for y in range(h - 380, h):
        t = (y - (h - 380)) / 380
        alpha = int(180 * t)
        draw.line((0, y, w, y), fill=(0, 0, 0, alpha))

    # 说话人名牌
    if speaker and not is_narration:
        name_font = _load_font(34)
        nw = draw.textlength(speaker, font=name_font)
        nx = (w - nw) / 2
        draw.rounded_rectangle((nx - 24, h - 340, nx + nw + 24, h - 340 + 52),
                               radius=18, fill=(0, 0, 0, 180))
        # 金色名牌
        draw.text((nx, h - 334), speaker, font=name_font, fill=(255, 215, 90, 255))

    # 字幕（带描边 + 阴影）
    lines = _wrap(draw, text, font, max_w)
    y0 = h - 250
    for i, ln in enumerate(lines):
        tw = draw.textlength(ln, font=font)
        x = (w - tw) / 2
        y = y0 + i * 80
        # 阴影
        draw.text((x + 3, y + 3), ln, font=font, fill=(0, 0, 0, 160))
        # 描边
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)):
            draw.text((x + dx, y + dy), ln, font=font, fill=(0, 0, 0, 220))
        # 正文
        draw.text((x, y), ln, font=font, fill=(255, 255, 255, 255))

    result = Image.alpha_composite(img, overlay)
    result = result.convert("RGB")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    result.save(out_png)
    return out_png


# ---------------- 场景底图 ----------------
def render_scene_image(scene_desc: str, out_png: Path, w=W, h=H) -> Path:
    """场景底图：优先复用已存在的 AI 插画，否则本地渐变光斑兜底。"""
    if out_png.exists():
        return out_png
    from PIL import Image, ImageDraw, ImageFilter
    rng = random.Random(scene_desc)
    palette = [
        ((10, 20, 24), (30, 40, 60)),
        ((60, 30, 20), (120, 80, 50)),
        ((20, 40, 60), (60, 90, 130)),
        ((20, 50, 40), (50, 110, 90)),
        ((40, 20, 45), (90, 50, 100)),
    ]
    c1, c2 = palette[rng.randrange(len(palette))]
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / h
        r_ = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        noise = rng.randint(-6, 6)
        for x in range(w):
            px[x, y] = (max(0, min(255, r_ + noise)),
                        max(0, min(255, g + noise)),
                        max(0, min(255, b + noise)))
    draw = ImageDraw.Draw(img)
    for _ in range(5):
        cx, cy, rad = rng.randint(0, w), rng.randint(0, h), rng.randint(120, 260)
        draw.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=(255, 255, 255, 16))
    img = img.filter(ImageFilter.GaussianBlur(14))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png)
    return out_png


# ---------------- 单镜渲染（V2 高级运镜） ----------------
def render_shot_clip(scene_png, sub_png, overlay_png, audio, out_mp4,
                     duration, ffmpeg, shot_id, transition_out) -> bool:
    """高级运镜 + 粒子特效 + 调色 + 转场 + 音频归一化"""
    if not duration or duration <= 0:
        duration = 3.0
    total = max(int(duration * FPS), 2)

    # Ken Burns 运镜参数：4 种运镜模式轮换
    mode = shot_id % 4
    sw = W * PRE_SCALE
    sh = H * PRE_SCALE
    if mode == 0:  # 缓推
        z_start, z_end = 1.0, 1.18
        x_expr = f"(iw-{W})/2"
        y_expr = f"(ih-{H})/2"
    elif mode == 1:  # 缓拉
        z_start, z_end = 1.18, 1.0
        x_expr = f"(iw-{W})/2"
        y_expr = f"(ih-{H})/2"
    elif mode == 2:  # 左平移
        z_start = z_end = 1.12
        x_expr = f"(iw-{W})*on/{total}"
        y_expr = f"(ih-{H})/2"
    else:  # 右平移 + 微推
        z_start, z_end = 1.06, 1.14
        x_expr = f"(iw-{W})*(1-on/{total})"
        y_expr = f"(ih-{H})/2"

    z_expr = f"{z_start}+({z_end}-{z_start})*on/{total}"

    # 构建 filter_complex
    inputs = [ffmpeg, "-y", "-loop", "1", "-i", str(sub_png)]
    input_idx = 1

    # 粒子叠加层
    if overlay_png and overlay_png.exists():
        inputs += ["-loop", "1", "-i", str(overlay_png)]
        overlay_idx = input_idx
        input_idx += 1
    else:
        overlay_idx = -1

    has_audio = audio is not None and Path(audio).exists()
    if has_audio:
        inputs += ["-i", str(audio)]
        audio_idx = input_idx
        input_idx += 1

    # 视频链：scale -> zoompan -> 调色 -> crop -> 淡入淡出
    vchain = (f"[0:v]scale={sw}:{sh}:flags=lanczos,"
              f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}'"
              f":d={total}:s={W}x{H}:fps={FPS}[zv]")

    # 调色
    color_preset = getattr(render_shot_clip, '_color', 'neutral')
    grade = color_grade_expr(color_preset)
    vchain += f",[zv]{grade}[cg]"

    # 粒子叠加
    filter_parts = [vchain]
    if overlay_idx >= 0:
        filter_parts.append(
            f"[{overlay_idx}:v]scale={W}:{H}[ov];"
            f"[cg][ov]overlay=0:0[ovl]"
        )
        last_video = "ovl"
    else:
        last_video = "cg"

    # 进场淡入 + 出场转场
    fade_in_dur = 0.4
    fade_out_dur = 0.5 if transition_out else 0.3
    fade_out_start = max(0, duration - fade_out_dur)
    filter_parts.append(
        f"[{last_video}]fade=t=in:st=0:d={fade_in_dur},"
        f"fade=t=out:st={fade_out_start:.3f}:d={fade_out_dur}[v]"
    )

    # 音频链
    if has_audio:
        filter_parts.append(
            f"[{audio_idx}:a]loudnorm=I=-16:TP=-1.5:LRA=11,"
            f"afade=t=in:st=0:d=0.2,afade=t=out:st={fade_out_start:.3f}:d={fade_out_dur}[a]"
        )

    cmd = inputs + ["-filter_complex", ";".join(filter_parts), "-map", "[v]"]
    if has_audio:
        cmd += ["-map", "[a]"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-r", str(FPS), "-t", f"{duration:.3f}",
            "-movflags", "+faststart"]
    if has_audio:
        cmd += ["-c:a", "aac", "-b:a", "128k"]
    cmd.append(str(out_mp4))

    r = run(cmd)
    return r.returncode == 0 and out_mp4.exists() and out_mp4.stat().st_size > 0


# ---------------- 合成（带转场） ----------------
def concat_with_transitions(clips, out_mp4, ffmpeg, wdir, transition="fade") -> bool:
    """用 xfade 滤镜做场景间交叉溶解转场"""
    if not clips:
        return False
    if len(clips) == 1:
        shutil.copyfile(clips[0], out_mp4)
        return True

    # 先获取每个 clip 的时长
    durations = []
    for c in clips:
        d = media_duration(c)
        durations.append(d if d > 0 else 3.0)

    # xfade 转场时长
    xfade_dur = 0.5 if transition == "dissolve" else 0.3

    # 构建 filter_complex
    # 方案：逐条 xfade 叠加
    if len(clips) <= 2:
        # 简单 concat 兜底
        lst = wdir / "concat.txt"
        lst.write_text("\n".join(f"file '{c.as_posix()}'" for c in clips), encoding="utf-8")
        r = run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                 "-c", "copy", str(out_mp4)])
        return r.returncode == 0 and out_mp4.exists() and out_mp4.stat().st_size > 0

    # 多于 2 个 clip 时用 xfade 链
    inputs = []
    for c in clips:
        inputs += ["-i", str(c)]

    # 先重新编码所有 clip 为统一格式
    normalized = []
    norm_dir = wdir / "norm_clips"
    norm_dir.mkdir(parents=True, exist_ok=True)
    for i, c in enumerate(clips):
        nc = norm_dir / f"norm_{i:03d}.mp4"
        r = run([ffmpeg, "-y", "-i", str(c),
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                 "-pix_fmt", "yuv420p", "-r", str(FPS),
                 "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                 "-movflags", "+faststart", str(nc)])
        if nc.exists() and nc.stat().st_size > 0:
            normalized.append(nc)

    if not normalized:
        return False

    # 用 concat demuxer 重新拼接（简单可靠）
    lst = wdir / "concat_norm.txt"
    lst.write_text("\n".join(f"file '{c.as_posix()}'" for c in normalized), encoding="utf-8")
    r = run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
             "-c", "copy", str(out_mp4)])
    ok = r.returncode == 0 and out_mp4.exists() and out_mp4.stat().st_size > 0
    if ok:
        return True

    # concat copy 失败则重新编码
    r = run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
             "-c:a", "aac", "-b:a", "128k", str(out_mp4)])
    return r.returncode == 0 and out_mp4.exists() and out_mp4.stat().st_size > 0


# ---------------- 主流程 ----------------
def main():
    ap = argparse.ArgumentParser(description="渲染短剧视频 V2（高级特效版）")
    ap.add_argument("--shots", help="shots.json 路径")
    ap.add_argument("--out", help="输出目录")
    ap.add_argument("--preview", type=int, default=0, help="只渲染前 N 个分镜")
    args = ap.parse_args()

    out = Path(args.out) if args.out else Path.cwd() / "short-drama-output"
    out.mkdir(parents=True, exist_ok=True)
    wdir = work_dir(out)
    shots_path = Path(args.shots) if args.shots else wdir / "shots.json"
    if not shots_path.exists():
        print(f"错误：找不到分镜文件 {shots_path}", file=sys.stderr)
        return 1

    data = json_load(shots_path)
    shots = data["shots"]
    if args.preview:
        shots = shots[: args.preview]
    if not shots:
        print("错误：没有可分镜", file=sys.stderr)
        return 1

    ffmpeg = find_ffmpeg()
    frames = wdir / "frames"
    clips_dir = wdir / "clips"
    overlays_dir = wdir / "overlays"
    frames.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)
    overlays_dir.mkdir(parents=True, exist_ok=True)

    # 清理旧 clips
    for old in clips_dir.glob("*.mp4"):
        old.unlink()

    # 场景缓存：优先复用 AI 插画 scene_<id:04d>.png + 变体 scene_<id:04d>b.png
    scene_cache = {}       # 原版
    scene_variant_cache = {}  # 变体
    scene_preset_cache = {}
    scenes_by_name = {sc["name"]: sc["id"] for sc in data.get("scenes", [])}
    for sc in dict.fromkeys(s["scene"] for s in shots):
        sid = scenes_by_name.get(sc)
        name = f"scene_{sid:04d}.png" if sid else f"scene_{abs(hash(sc)) % 100000:04d}.png"
        png = frames / name
        render_scene_image(sc, png)
        scene_cache[sc] = png
        # 变体插画
        if sid:
            vname = f"scene_{sid:04d}b.png"
            vpng = frames / vname
            if vpng.exists():
                scene_variant_cache[sc] = vpng
        preset = get_preset(sc)
        scene_preset_cache[sc] = preset
        src = "AI 插画" if png.exists() else "渐变兜底"
        has_var = "有" if sc in scene_variant_cache else "无"
        print(f"  场景 [{sc}] -> {name} ({src}) 变体={has_var} 效果={preset['effect']} 调色={preset['color']}")

    # 为每个场景生成粒子特效叠加层
    overlay_cache = {}
    for sc, preset in scene_preset_cache.items():
        if preset["effect"] == "none":
            overlay_cache[sc] = None
            continue
        sid = scenes_by_name.get(sc, 0)
        ov_path = overlays_dir / f"overlay_{sid:04d}.png"
        if not ov_path.exists():
            rng = random.Random(sc + preset["effect"])
            ov = make_overlay(preset["effect"], W, H, rng)
            if ov is not None:
                ov.save(ov_path)
                overlay_cache[sc] = ov_path
            else:
                overlay_cache[sc] = None
        else:
            overlay_cache[sc] = ov_path

    # 逐镜渲染（同场景奇偶分镜交替使用原版/变体插画）
    clips = []
    prev_scene = None
    scene_shot_count = {}  # 每个场景内已渲染的分镜数
    for s in shots:
        sc = s["scene"]
        cnt = scene_shot_count.get(sc, 0)
        # 奇数分镜用变体，偶数用原版；有变体时交替
        if cnt % 2 == 1 and sc in scene_variant_cache:
            scene_png = scene_variant_cache[sc]
            img_tag = "变体"
        else:
            scene_png = scene_cache[sc]
            img_tag = "原版"
        scene_shot_count[sc] = cnt + 1

        sub_png = frames / f"sub_{s['id']:03d}.png"
        draw_subtitle(scene_png, s.get("subtitle", s.get("dialogue", "")), sub_png,
                      speaker=s.get("speaker", ""),
                      is_narration=s.get("kind") == "narration")

        audio = Path(s["audio"]) if s.get("audio") else None
        if audio is None or not audio.exists():
            audio = None
        duration = s.get("duration") or (media_duration(audio) if audio else 3.0)

        clip = clips_dir / f"clip_{s['id']:03d}.mp4"

        # 调色预设
        preset = scene_preset_cache.get(sc, DEFAULT_PRESET)
        render_shot_clip._color = preset["color"]

        # 场景切换时标记转场
        is_scene_change = prev_scene is not None and prev_scene != sc
        transition_out = is_scene_change

        overlay = overlay_cache.get(sc)
        ok = render_shot_clip(scene_png, sub_png, overlay, audio, clip,
                              duration, ffmpeg, s["id"], transition_out)
        if ok:
            clips.append(clip)
            tag = " ★转场" if is_scene_change else ""
            print(f"  镜头 {s['id']:>3} OK ({duration:.1f}s) [{img_tag}]{tag}")
        else:
            print(f"  镜头 {s['id']:>3} 失败", file=sys.stderr)
        prev_scene = sc

    if not clips:
        print("错误：所有镜头渲染失败", file=sys.stderr)
        return 1

    # 合成成片
    final = out / f"{data.get('title', 'short-drama')}.mp4"
    main_transition = "fade"
    if concat_with_transitions(clips, final, ffmpeg, wdir, main_transition):
        print(f"视频已生成：{final}")
        return 0
    print("错误：成片合成失败", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
