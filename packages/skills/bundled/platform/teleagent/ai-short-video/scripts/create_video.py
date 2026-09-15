#!/usr/bin/env python3
"""
Create short video from images + audio + subtitle.

Usage:
    python create_video.py --images_dir ./images --audio ./output/audio.mp3 \
        --segments ./output/segments.json --output ./output/video.mp4 \
        [--resolution 1080x1920] [--fps 24] [--subtitle_srt ./output/subtitle.srt] \
        [--subtitle_font_size 36] [--subtitle_color white] [--subtitle_stroke 2]

Supports:
    - Image sequence with crossfade transitions
    - Audio sync with subtitle overlay
    - Custom resolution (vertical 9:16 or horizontal 16:9)
    - SRT subtitle file export
"""

import argparse
import json
import os
import sys
import math


def parse_resolution(res_str: str):
    """Parse resolution string like '1080x1920' to (width, height)."""
    parts = res_str.lower().split("x")
    if len(parts) != 2:
        raise ValueError(f"Invalid resolution format: {res_str}. Use WxH, e.g. 1080x1920")
    return int(parts[0]), int(parts[1])


def create_video(
    images_dir: str,
    audio_path: str,
    segments_path: str,
    output_path: str,
    resolution: tuple,
    fps: int,
    subtitle_srt: str = None,
    subtitle_font_size: int = 36,
    subtitle_color: str = "white",
    subtitle_stroke: int = 2,
    transition_duration: float = 0.5,
    bg_color: tuple = (0, 0, 0),
):
    """Create video from images + audio + subtitle using moviepy."""
    try:
        from moviepy.editor import (
            ImageClip, AudioFileClip, CompositeVideoClip,
            TextClip, concatenate_videoclips, ColorClip
        )
        from moviepy.video.fx.all import resize
    except ImportError:
        print("ERROR: moviepy not installed. Run: pip install moviepy", file=sys.stderr)
        sys.exit(1)

    try:
        from PIL import Image
    except ImportError:
        print("ERROR: Pillow not installed. Run: pip install Pillow", file=sys.stderr)
        sys.exit(1)

    # Load segments for timing
    with open(segments_path, "r", encoding="utf-8") as f:
        segments = json.load(f)

    total_duration_s = max(s["offset_ms"] + s["duration_ms"] for s in segments) / 1000 if segments else 5.0

    # Load and sort images
    image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    if not os.path.isdir(images_dir):
        print(f"WARNING: Images directory not found: {images_dir}. Creating color-only video.", file=sys.stderr)
        image_files = []
    else:
        image_files = sorted([
            f for f in os.listdir(images_dir)
            if os.path.splitext(f)[1].lower() in image_extensions
        ])

    width, height = resolution

    # Build video clips from images
    if image_files:
        num_images = len(image_files)
        per_image_duration = total_duration_s / num_images

        clips = []
        for i, img_file in enumerate(image_files):
            img_path = os.path.join(images_dir, img_file)
            img = ImageClip(img_path).set_duration(per_image_duration)

            # Resize to fit resolution while maintaining aspect ratio
            img_w, img_h = img.size
            scale = min(width / img_w, height / img_h)
            new_w, new_h = int(img_w * scale), int(img_h * scale)
            img = img.resize((new_w, new_h))

            # Center on canvas with background color
            if new_w != width or new_h != height:
                bg = ColorClip(size=(width, height), color=bg_color).set_duration(per_image_duration)
                img = CompositeVideoClip([bg, img.set_position("center")], size=(width, height))

            clips.append(img)

        video = concatenate_videoclips(clips, method="compose")
    else:
        # No images: create black background
        video = ColorClip(size=(width, height), color=bg_color).set_duration(total_duration_s)

    # Set total duration
    video = video.set_duration(total_duration_s)

    # Add audio
    audio = AudioFileClip(audio_path)
    video = video.set_audio(audio)

    # Add subtitle overlay using SRT file if provided
    if subtitle_srt and os.path.exists(subtitle_srt):
        subtitle_clips = parse_srt_to_clips(
            subtitle_srt, width, height,
            font_size=subtitle_font_size,
            color=subtitle_color,
            stroke_width=subtitle_stroke,
        )
        if subtitle_clips:
            video = CompositeVideoClip([video] + subtitle_clips, size=(width, height))

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Write video
    video.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
        logger=None,
    )

    print(json.dumps({
        "output_path": output_path,
        "resolution": f"{width}x{height}",
        "fps": fps,
        "duration_s": round(total_duration_s, 2),
    }, ensure_ascii=False, indent=2))

    return output_path


def parse_srt_to_clips(srt_path: str, video_width: int, video_height: int,
                       font_size: int = 36, color: str = "white",
                       stroke_width: int = 2):
    """Parse SRT file and create TextClip for each subtitle entry."""
    try:
        from moviepy.editor import TextClip
    except ImportError:
        return []

    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    clips = []
    blocks = re.split(r"\n\n+", content.strip())

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue

        # Parse timestamp line
        time_line = lines[1]
        match = re.match(
            r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})",
            time_line,
        )
        if not match:
            continue

        g = match.groups()
        start_s = int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 1000
        end_s = int(g[4]) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7]) / 1000
        duration = end_s - start_s

        text = "\n".join(lines[2:])

        try:
            txt_clip = (
                TextClip(
                    text,
                    fontsize=font_size,
                    color=color,
                    stroke_color="black",
                    stroke_width=stroke_width,
                    size=(video_width - 80, None),
                    method="caption",
                    font="SimHei",  # Common Chinese font
                )
                .set_start(start_s)
                .set_duration(duration)
                .set_position(("center", video_height - 120))
            )
            clips.append(txt_clip)
        except Exception as e:
            print(f"WARNING: Failed to create subtitle clip: {e}", file=sys.stderr)
            continue

    return clips


def main():
    parser = argparse.ArgumentParser(description="Create short video from images + audio + subtitle")
    parser.add_argument("--images_dir", type=str, default="./images",
                        help="Directory containing image files (sorted by name)")
    parser.add_argument("--audio", type=str, required=True,
                        help="Path to audio file (MP3/WAV)")
    parser.add_argument("--segments", type=str, required=True,
                        help="Path to segments.json from generate_tts.py")
    parser.add_argument("--output", type=str, default="./output/video.mp4",
                        help="Output video path (default: ./output/video.mp4)")
    parser.add_argument("--resolution", type=str, default="1080x1920",
                        help="Video resolution WxH (default: 1080x1920 for 9:16)")
    parser.add_argument("--fps", type=int, default=24,
                        help="Frame rate (default: 24)")
    parser.add_argument("--subtitle_srt", type=str, default=None,
                        help="Path to SRT subtitle file for overlay")
    parser.add_argument("--subtitle_font_size", type=int, default=36,
                        help="Subtitle font size (default: 36)")
    parser.add_argument("--subtitle_color", type=str, default="white",
                        help="Subtitle text color (default: white)")
    parser.add_argument("--subtitle_stroke", type=int, default=2,
                        help="Subtitle stroke width (default: 2)")

    args = parser.parse_args()

    resolution = parse_resolution(args.resolution)
    create_video(
        images_dir=args.images_dir,
        audio_path=args.audio,
        segments_path=args.segments,
        output_path=args.output,
        resolution=resolution,
        fps=args.fps,
        subtitle_srt=args.subtitle_srt,
        subtitle_font_size=args.subtitle_font_size,
        subtitle_color=args.subtitle_color,
        subtitle_stroke=args.subtitle_stroke,
    )


if __name__ == "__main__":
    main()
