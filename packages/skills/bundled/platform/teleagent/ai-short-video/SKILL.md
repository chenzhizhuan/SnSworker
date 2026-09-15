---
name: ai-short-video
description: "AI short video creation with subtitles and voiceover. Use when user wants to create short videos, make video from text/script, generate videos with dubbing, add subtitles to video, or produce content for social media platforms (Douyin, Kuaishou, Bilibili, Xiaohongshu). Supports two modes: (1) text-to-video: script to AI images + TTS audio + subtitles to MP4, (2) image-to-video: user images + TTS audio + subtitles to MP4. Outputs MP4 video + SRT subtitle file."
name_cn: AI短视频制作
description_cn: 根据文案或图片自动生成带字幕和配音的短视频，支持抖音/快手竖屏等多种规格
create_source: super-agent-skill-creator
---

# AI Short Video

Create short videos with AI-generated voiceover and subtitles. Two modes supported:

1. **Text-to-Video**: Provide a script/text → generate AI images as visuals → TTS voiceover → subtitle overlay → MP4
2. **Image-to-Video**: Provide your own images → TTS voiceover → subtitle overlay → MP4

Both modes output an MP4 video file and an independent SRT subtitle file.

## Workflow

### Mode 1: Text-to-Video

1. **Receive user script**: Get the text content for the video. If the user only provides a topic, help write a short script (typically 100-500 words for 30s-3min video).
2. **Generate images**: Use image generation tool (ImageGen) to create visuals for each segment. Match image count to content pacing (roughly 1 image per 5-10 seconds).
3. **Generate TTS**: Run `scripts/generate_tts.py` with the script text to produce audio.mp3, subtitle.srt, and segments.json.
4. **Create video**: Run `scripts/create_video.py` combining images, audio, and subtitles into the final MP4.

### Mode 2: Image-to-Video

1. **Receive user images**: Get image file paths from the user.
2. **Write narration text**: Based on images or user instructions, compose narration text.
3. **Generate TTS**: Same as Mode 1 step 3.
4. **Create video**: Same as Mode 1 step 4, using user-provided images.

## Prerequisites

Install dependencies before first use:

```bash
pip install edge-tts moviepy Pillow
```

FFmpeg must also be installed and available in PATH. On Windows, download from https://ffmpeg.org/download.html.

## Scripts

### generate_tts.py — TTS Audio + Subtitle Generation

```bash
python scripts/generate_tts.py \
  --text "你的视频文案内容" \
  --voice zh-CN-YunxiNeural \
  --output_dir ./output \
  --rate "+10%"
```

Key parameters:
- `--text`: Text to synthesize (or use `--text_file` to read from file)
- `--voice`: Edge-TTS voice name (see references/video_styles.md for recommendations)
- `--rate`: Speed adjustment, e.g. "+20%", "-10%"
- `--pitch`: Pitch adjustment, e.g. "+5Hz", "-3Hz"
- `--list_voices`: List all available voices

Output files: `audio.mp3`, `subtitle.srt`, `segments.json`

### create_video.py — Video Assembly

```bash
python scripts/create_video.py \
  --images_dir ./images \
  --audio ./output/audio.mp3 \
  --segments ./output/segments.json \
  --subtitle_srt ./output/subtitle.srt \
  --output ./output/video.mp4 \
  --resolution 1080x1920 \
  --fps 24
```

Key parameters:
- `--images_dir`: Directory with images (sorted by filename)
- `--resolution`: Video size, default `1080x1920` (9:16 vertical)
- `--subtitle_srt`: SRT file for subtitle overlay
- `--subtitle_font_size`: Font size (default 36)
- `--subtitle_color`: Text color (default white)
- `--subtitle_stroke`: Stroke width (default 2)

## Resolution Presets

| Platform | Resolution | Command |
|----------|-----------|---------|
| 抖音/快手 | 1080x1920 | `--resolution 1080x1920` |
| 小红书 | 1080x1440 | `--resolution 1080x1440` |
| B站 | 1920x1080 | `--resolution 1920x1080` |
| 微信视频号 | 1080x1080 | `--resolution 1080x1080` |

For voice and style options, see [references/video_styles.md](references/video_styles.md).

## Notes

- If ImageGen is unavailable for text-to-video mode, create solid-color background cards with text overlay instead.
- Always deliver both the MP4 video and the SRT subtitle file to the user.
- For long scripts (>3 minutes), consider splitting into segments and asking the user if they want to trim.
- All intermediate files (audio, segments.json) should be saved in `.temp/` within the working directory.
