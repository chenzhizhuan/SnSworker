#!/usr/bin/env python3
"""
Generate TTS audio and SRT subtitle using edge-tts.

Usage:
    python generate_tts.py --text "你的文案" --voice zh-CN-YunxiNeural --output_dir ./output [--rate "+0%"] [--pitch "+0Hz"]

Output:
    - audio.mp3: synthesized speech
    - subtitle.srt: subtitle file with timestamps
    - segments.json: word-level timing data for video sync
"""

import argparse
import asyncio
import json
import os
import re
import sys


async def generate_tts(text: str, voice: str, output_dir: str, rate: str, pitch: str):
    """Generate TTS audio and subtitle using edge-tts."""
    try:
        import edge_tts
    except ImportError:
        print("ERROR: edge-tts not installed. Run: pip install edge-tts", file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    audio_path = os.path.join(output_dir, "audio.mp3")
    srt_path = os.path.join(output_dir, "subtitle.srt")
    segments_path = os.path.join(output_dir, "segments.json")

    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)

    # Collect word-level timing data
    segments = []
    submaker = edge_tts.SubMaker()

    with open(audio_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                submaker.feed(chunk)
                offset = int(chunk["offset"]) / 10000   # 100ns to ms
                duration = int(chunk["duration"]) / 10000
                segments.append({
                    "text": chunk["text"],
                    "offset_ms": offset,
                    "duration_ms": duration,
                })

    # Write SRT subtitle
    with open(srt_path, "w", encoding="utf-8") as srt_file:
        srt_file.write(submaker.get_srt())

    # Write segments JSON
    with open(segments_path, "w", encoding="utf-8") as seg_file:
        json.dump(segments, seg_file, ensure_ascii=False, indent=2)

    # Calculate total duration
    total_duration_ms = max(s["offset_ms"] + s["duration_ms"] for s in segments) if segments else 0

    result = {
        "audio_path": audio_path,
        "srt_path": srt_path,
        "segments_path": segments_path,
        "total_duration_ms": total_duration_ms,
        "total_duration_s": round(total_duration_ms / 1000, 2),
        "word_count": len(segments),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def list_voices(lang: str = "zh"):
    """List available voices for a language."""
    try:
        import edge_tts
    except ImportError:
        print("ERROR: edge-tts not installed. Run: pip install edge-tts", file=sys.stderr)
        sys.exit(1)

    voices = asyncio.run(edge_tts.list_voices())
    filtered = [v for v in voices if v["Locale"].startswith(lang)]
    for v in filtered:
        print(f"  {v['ShortName']:30s} | {v['Gender']:8s} | {v.get('FriendlyName', '')}")
    return filtered


def main():
    parser = argparse.ArgumentParser(description="Generate TTS audio and SRT subtitle")
    parser.add_argument("--text", type=str, help="Text to synthesize")
    parser.add_argument("--text_file", type=str, help="Read text from file")
    parser.add_argument("--voice", type=str, default="zh-CN-YunxiNeural",
                        help="Voice name (default: zh-CN-YunxiNeural)")
    parser.add_argument("--output_dir", type=str, default="./output",
                        help="Output directory (default: ./output)")
    parser.add_argument("--rate", type=str, default="+0%",
                        help="Speech rate, e.g. '+20%%' or '-10%%' (default: +0%%)")
    parser.add_argument("--pitch", type=str, default="+0Hz",
                        help="Speech pitch, e.g. '+5Hz' or '-3Hz' (default: +0Hz)")
    parser.add_argument("--list_voices", action="store_true",
                        help="List available voices")
    parser.add_argument("--lang", type=str, default="zh",
                        help="Language filter for --list_voices (default: zh)")

    args = parser.parse_args()

    if args.list_voices:
        list_voices(args.lang)
        return

    if not args.text and not args.text_file:
        parser.error("Either --text or --text_file is required")

    text = args.text
    if args.text_file:
        with open(args.text_file, "r", encoding="utf-8") as f:
            text = f.read().strip()

    asyncio.run(generate_tts(text, args.voice, args.output_dir, args.rate, args.pitch))


if __name__ == "__main__":
    main()
