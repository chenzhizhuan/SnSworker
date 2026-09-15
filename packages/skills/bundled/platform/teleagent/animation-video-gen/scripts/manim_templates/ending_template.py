#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短剧片尾模板 - 竖屏9:16
支持: 下集预告、关注提示、结束动画

用法:
  manim -pql ending_template.py DramaEnding
"""

from manim import *

config.pixel_width = 1080
config.pixel_height = 1920
config.frame_width = 10.8
config.frame_height = 19.2
config.frame_rate = 24


class DramaEnding(Scene):
    """短剧片尾模板"""

    def construct(self):
        # ===== 配置区 =====
        preview_text = "下集预告"  # 设为空字符串则跳过
        preview_content = "他终于知道了真相，但代价是……"
        ending_text = "未完待续"
        follow_prompt = "关注追更 不迷路"
        style = "dark"

        colors = {
            "dark": {"bg": "#0A0A1A", "text": "#FFFFFF", "accent": "#FFD700", "hint": "#888888"},
            "bright": {"bg": "#1A1A2E", "text": "#FFFFFF", "accent": "#FF4466", "hint": "#AAAAAA"},
        }
        c = colors.get(style, colors["dark"])

        bg = Rectangle(
            width=config.frame_width + 1,
            height=config.frame_height + 1,
            fill_color=c["bg"], fill_opacity=1,
            stroke_width=0,
        )
        self.add(bg)

        # ===== 下集预告 =====
        if preview_text:
            preview_title = Text(
                preview_text, font="SimHei", font_size=48, color=c["accent"]
            ).move_to(UP * 3)

            preview_content_text = Text(
                preview_content, font="SimHei", font_size=36, color=c["text"]
            )
            if preview_content_text.width > config.frame_width * 0.85:
                preview_content_text.width = config.frame_width * 0.85
            preview_content_text.next_to(preview_title, DOWN, buff=0.5)

            self.play(FadeIn(preview_title), run_time=0.6)
            self.play(Write(preview_content_text), run_time=1)
            self.wait(2)
            self.play(
                FadeOut(preview_title), FadeOut(preview_content_text),
                run_time=0.5,
            )

        # ===== 未完待续 =====
        ending = Text(
            ending_text, font="SimHei", font_size=72, color=c["text"]
        ).move_to(UP * 0.5)

        self.play(FadeIn(ending, scale=1.3), run_time=0.8)
        self.wait(1.0)

        # ===== 关注提示 =====
        follow = Text(
            follow_prompt, font="SimHei", font_size=36, color=c["hint"]
        ).next_to(ending, DOWN, buff=1.5)

        # 闪烁动画
        self.play(FadeIn(follow), run_time=0.5)
        for _ in range(2):
            self.play(follow.animate.set_opacity(0.3), run_time=0.4)
            self.play(follow.animate.set_opacity(1), run_time=0.4)

        self.wait(1.5)

        # ===== 淡出 =====
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.8)
