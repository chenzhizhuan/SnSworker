#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发布包生成：把成片 + 封面 + 标题/简介/话题打包为可直接上传短剧平台的目录。
- 封面：从成片第一帧截图（可自定义标题文字）
- 信息文件：平台规范（标题长度、简介、话题标签）
- 打包为 zip 可选

用法：
  python publish_pack.py --video 成片.mp4 [--title 剧名] [--desc 简介] [--tags 话题1,话题2] [--zip]
"""
import argparse
import zipfile
from pathlib import Path

from common import ensure_out, find_ffmpeg, run


def make_cover(video: Path, cover: Path, ffmpeg: str, title: str = "") -> bool:
    """截取第一帧作为封面；可选叠加标题文字"""
    r = run([ffmpeg, "-y", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(cover)])
    if r.returncode != 0 or not cover.exists():
        return False
    if title:
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.open(cover).convert("RGB")
            draw = ImageDraw.Draw(img)
            font = None
            for fp in ("C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc",
                       "C:/Windows/Fonts/simhei.ttf"):
                try:
                    font = ImageFont.truetype(fp, 64)
                    break
                except Exception:
                    continue
            if font:
                w, h = img.size
                # 标题分段居中
                lines = []
                cur = ""
                for ch in title:
                    if draw.textlength(cur + ch, font=font) > w - 160:
                        lines.append(cur)
                        cur = ch
                    else:
                        cur += ch
                lines.append(cur)
                y = h // 2 - len(lines) * 45
                for ln in lines[:3]:
                    tw = draw.textlength(ln, font=font)
                    x = (w - tw) / 2
                    for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
                        draw.text((x + dx, y + dy), ln, font=font, fill=(0, 0, 0))
                    draw.text((x, y), ln, font=font, fill=(255, 255, 255))
                    y += 90
                img.save(cover)
        except Exception:
            pass
    return True


def main():
    ap = argparse.ArgumentParser(description="生成发布包")
    ap.add_argument("--video", required=True, help="成片 mp4 路径")
    ap.add_argument("--title", default="", help="剧名/标题")
    ap.add_argument("--desc", default="", help="简介")
    ap.add_argument("--tags", default="", help="话题标签，逗号分隔")
    ap.add_argument("--out", help="输出目录")
    ap.add_argument("--zip", action="store_true", help="同时打包为 zip")
    args = ap.parse_args()

    video = Path(args.video)
    if not video.exists():
        print(f"错误：找不到成片 {video}", file=sys.stderr)
        return 1

    out = ensure_out(Path(args.out) if args.out else video.parent)
    pack_dir = out / "发布包"
    pack_dir.mkdir(parents=True, exist_ok=True)

    # 封面
    cover = pack_dir / "cover.jpg"
    if make_cover(video, cover, find_ffmpeg(), args.title):
        print(f"封面：{cover}")
    else:
        print("封面生成失败（可跳过）", file=sys.stderr)

    # 平台信息文件（抖音/红果短剧通用字段）
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    info = {
        "标题": args.title or video.stem,
        "简介": args.desc or "",
        "话题标签": tags,
        "平台建议": ["抖音", "红果短剧"],
        "文件": video.name,
        "封面": cover.name if cover.exists() else "",
    }
    import json

    (pack_dir / "publish_info.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    # 复制成片
    import shutil

    dst = pack_dir / video.name
    if dst != video:
        shutil.copy2(video, dst)

    # 可选的 zip
    if args.zip:
        zpath = out / f"发布包_{Path(video.stem).name}.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in pack_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(pack_dir))
        print(f"打包：{zpath}")

    print(f"发布包已生成：{pack_dir}")
    print(f"  标题：{info['标题']}")
    print(f"  简介：{info['简介'] or '（未填写）'}")
    print(f"  话题：{'、'.join(tags) or '（未填写）'}")
    print("提示：把成片与文案上传到抖音/红果创作者后台即可发布。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())