#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短剧动画主模板 - 竖屏9:16, 1080x1920
支持: 对白字幕、对话气泡、旁白、场景切换

用法:
  manim -pql short_drama_template.py ShortDramaScene
"""

from manim import *

# 竖屏9:16配置
config.pixel_width = 1080
config.pixel_height = 1920
config.frame_width = 10.8
config.frame_height = 19.2
config.frame_rate = 24


class ShortDramaScene(Scene):
    """
    短剧场景模板
    支持文字对白(字幕模式)、对话气泡模式、旁白
    """

    def construct(self):
        # ===== 配置区 =====
        # 场景设置: 使用AI生成的背景图或纯色背景
        background = "#1a1a2e"  # 默认深色背景
        # 如有关键帧图片,取消注释下一行:
        # self._set_background("scene_0001.png")

        # 对白配置 (speaker, text, emotion, mode="subtitle"|"bubble")
        dialogues = [
            {"speaker": "林墨", "text": "我不甘心！三年了，我不会放弃！", "emotion": "angry", "mode": "subtitle"},
            {"speaker": "苏晚", "text": "有些事，不是坚持就有结果的。", "emotion": "sad", "mode": "bubble"},
            {"speaker": "林墨", "text": "那你当初为什么还要开始？", "emotion": "serious", "mode": "subtitle"},
        ]

        # 旁白
        narration = "雨夜，天台上只剩两个人的对峙。"

        # ===== 渲染流程 =====
        # 1. 旁白
        if narration:
            self._show_narration(narration)

        # 2. 对白
        for dlg in dialogues:
            if dlg.get("mode", "subtitle") == "bubble":
                self._show_bubble_dialogue(
                    dlg["speaker"], dlg["text"], dlg.get("emotion", "")
                )
            else:
                self._show_subtitle_dialogue(
                    dlg["speaker"], dlg["text"], dlg.get("emotion", "")
                )

        self.wait(1)

    def _set_background(self, image_path: str):
        """设置背景图片"""
        bg = ImageMobject(image_path)
        bg.height = config.frame_height
        bg.move_to(ORIGIN)
        self.add(bg)

    def _show_narration(self, text: str, duration: float = 2.5):
        """显示旁白文字（画面中央偏上，半透明黑底）"""
        narration = Text(
            text, font="SimHei", font_size=36, color="#CCCCCC"
        )
        # 自动换行
        if narration.width > config.frame_width * 0.85:
            narration.width = config.frame_width * 0.85

        narration.move_to(UP * 3)

        bg = Rectangle(
            width=narration.width + 0.6,
            height=narration.height + 0.4,
            fill_color=BLACK, fill_opacity=0.7,
            stroke_width=0,
        ).move_to(narration)

        self.play(FadeIn(bg), Write(narration), run_time=1.2)
        self.wait(duration)
        self.play(FadeOut(narration), FadeOut(bg), run_time=0.5)

    def _show_subtitle_dialogue(self, speaker: str, text: str, emotion: str = ""):
        """
        字幕式对白
        画面底部: [角色名] 对白内容
        半透明黑底
        """
        # 角色名（金色）
        speaker_label = Text(
            speaker, font="SimHei", font_size=32, color="#FFD700"
        )

        # 对白内容（白色）
        dialogue_text = Text(
            text, font="SimHei", font_size=40, color=WHITE
        )
        if dialogue_text.width > config.frame_width * 0.85:
            dialogue_text.width = config.frame_width * 0.85

        # 组合
        group = VGroup(speaker_label, dialogue_text).arrange(
            DOWN, buff=0.15, aligned_to=LEFT
        )
        group.to_edge(DOWN, buff=0.8)

        # 背景
        bg = Rectangle(
            width=group.width + 0.8,
            height=group.height + 0.5,
            fill_color=BLACK, fill_opacity=0.75,
            stroke_width=0,
        ).move_to(group)

        # 情感高亮条
        emotion_colors = {
            "angry": "#FF4444",
            "sad": "#6666FF",
            "serious": "#FFAA00",
            "cheerful": "#44FF44",
            "romantic": "#FF88CC",
        }
        highlight_color = emotion_colors.get(emotion, "#FFD700")

        highlight = Rectangle(
            width=bg.width, height=0.06,
            fill_color=highlight_color, fill_opacity=1,
            stroke_width=0,
        ).next_to(bg, UP, buff=0)

        # 动画
        self.play(
            FadeIn(bg), FadeIn(highlight),
            FadeIn(group, shift=UP * 0.2),
            run_time=0.4,
        )
        self.wait(2.0)
        self.play(
            FadeOut(group), FadeOut(bg), FadeOut(highlight),
            run_time=0.3,
        )

    def _show_bubble_dialogue(self, speaker: str, text: str, emotion: str = ""):
        """
        漫画对话气泡式对白
        在画面中央区域显示气泡+文字
        """
        # 创建气泡背景
        bubble = RoundedRectangle(
            corner_radius=0.3,
            width=min(config.frame_width * 0.85, 9),
            height=2.5,
            fill_color=WHITE, fill_opacity=0.95,
            stroke_color="#333333", stroke_width=2,
        )

        # 气泡尾巴
        tail = Triangle(
            color=WHITE, fill_color=WHITE, fill_opacity=0.95,
            stroke_width=0,
        ).scale(0.3).rotate(PI)
        tail.next_to(bubble, DOWN, buff=-0.05)

        # 角色名
        speaker_label = Text(
            speaker, font="SimHei", font_size=32, color="#FF4466"
        )
        speaker_label.move_to(bubble.get_top() + DOWN * 0.4)

        # 对白内容
        dialogue_text = Text(
            text, font="SimHei", font_size=38, color="#222222"
        )
        if dialogue_text.width > bubble.width - 0.8:
            dialogue_text.width = bubble.width - 0.8
        dialogue_text.next_to(speaker_label, DOWN, buff=0.2)

        # 组合
        full_group = VGroup(bubble, tail, speaker_label, dialogue_text)
        full_group.move_to(UP * 1)

        # 动画
        self.play(
            GrowFromCenter(bubble),
            FadeIn(tail),
            run_time=0.3,
        )
        self.play(
            Write(speaker_label),
            Write(dialogue_text),
            run_time=0.8,
        )
        self.wait(2.0)
        self.play(FadeOut(full_group), run_time=0.3)
