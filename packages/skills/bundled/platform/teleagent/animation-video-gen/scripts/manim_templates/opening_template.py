#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短剧片头模板 - 竖屏9:16
支持: 标题动画、角色介绍、集数显示

用法:
  manim -pql opening_template.py DramaOpening
"""

from manim import *

config.pixel_width = 1080
config.pixel_height = 1920
config.frame_width = 10.8
config.frame_height = 19.2
config.frame_rate = 24


class DramaOpening(Scene):
    """短剧片头模板"""

    def construct(self):
        # ===== 配置区 =====
        drama_title = "逆光而行"
        subtitle = "当命运给你第二次机会"
        episode = "第一集"
        episode_en = "EP.01"
        style = "dark"  # dark | bright | romantic

        colors = {
            "dark": {"bg": "#0A0A1A", "title": "#FFFFFF", "accent": "#FFD700", "subtitle": "#AAAAAA"},
            "bright": {"bg": "#F5F5F5", "title": "#1A1A2E", "accent": "#FF4466", "subtitle": "#666666"},
            "romantic": {"bg": "#1A0A2E", "title": "#FFD0E0", "accent": "#FF69B4", "subtitle": "#CCAADD"},
        }
        c = colors.get(style, colors["dark"])

        # ===== 背景渐变 =====
        bg = Rectangle(
            width=config.frame_width + 1,
            height=config.frame_height + 1,
            fill_color=c["bg"], fill_opacity=1,
            stroke_width=0,
        )
        self.add(bg)

        # ===== 剧名 =====
        title = Text(
            drama_title, font="SimHei", font_size=96, color=c["title"]
        )
        title.move_to(UP * 2)

        # 装饰线
        line_top = Line(
            LEFT * 3, RIGHT * 3, color=c["accent"], stroke_width=2
        ).next_to(title, UP, buff=0.3)

        line_bottom = Line(
            LEFT * 3, RIGHT * 3, color=c["accent"], stroke_width=2
        ).next_to(title, DOWN, buff=0.3)

        # ===== 副标题 =====
        sub = Text(
            subtitle, font="SimHei", font_size=36, color=c["subtitle"]
        ).next_to(line_bottom, DOWN, buff=0.5)

        # ===== 集数 =====
        ep_label = Text(
            episode, font="SimHei", font_size=40, color=c["accent"]
        )
        ep_en = Text(
            episode_en, font="SimHei", font_size=28, color=c["accent"]
        )
        ep_group = VGroup(ep_label, ep_en).arrange(DOWN, buff=0.1)
        ep_group.next_to(sub, DOWN, buff=1.5)

        # ===== 动画序列 =====
        # 1. 装饰线从中间展开
        self.play(
            GrowFromCenter(line_top, run_time=0.6),
            GrowFromCenter(line_bottom, run_time=0.6),
        )

        # 2. 标题从下方浮现
        self.play(
            FadeIn(title, shift=UP * 0.5),
            run_time=0.8,
        )

        # 3. 副标题淡入
        self.play(FadeIn(sub, shift=UP * 0.3), run_time=0.6)

        # 4. 集数闪入
        self.play(FadeIn(ep_group, scale=1.5), run_time=0.5)

        # 5. 停留
        self.wait(2.0)

        # 6. 淡出过渡到正片
        self.play(
            *[FadeOut(m) for m in self.mobjects],
            run_time=0.8,
        )
