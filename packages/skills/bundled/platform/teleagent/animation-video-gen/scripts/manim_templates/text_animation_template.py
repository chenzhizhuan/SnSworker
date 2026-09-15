#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manim 动画模板 - 文字动画
支持：打字机效果、淡入淡出、书写、逐字出现/消失、缩放

用法:
  1. 修改 CONFIG 区的文字、字体、动画类型
  2. 运行: manim -pql text_animation_template.py TextAnimation
"""

from manim import *


class TextAnimation(Scene):
    """文字动画模板"""

    def construct(self):
        # ===== 配置区 =====
        texts = [
            {"content": "文字动画演示", "font": "SimHei", "size": 48, "animation": "write"},
            {"content": "逐字出现效果", "font": "SimHei", "size": 40, "animation": "letter_by_letter"},
            {"content": "淡入效果", "font": "SimHei", "size": 36, "animation": "fade_in"},
            {"content": "缩放出现", "font": "SimHei", "size": 42, "animation": "scale_in"},
            {"content": "谢谢观看", "font": "SimHei", "size": 54, "animation": "write"},
        ]
        bg_color = BLACK  # 背景色
        text_color = WHITE  # 文字颜色
        stay_duration = 0.8  # 每段文字停留时间

        # ===== 渲染动画 =====
        current = None
        for i, cfg in enumerate(texts):
            txt = Text(
                cfg["content"],
                font=cfg.get("font", "SimHei"),
                font_size=cfg.get("size", 40),
                color=text_color,
            )

            # 根据配置选择动画类型
            anim_type = cfg.get("animation", "fade_in")
            
            if anim_type == "write":
                anim = Write(txt, run_time=1.5)
            elif anim_type == "letter_by_letter":
                anim = AddTextLetterByLetter(txt, run_time=2)
            elif anim_type == "fade_in":
                anim = FadeIn(txt, shift=UP * 0.3, run_time=1)
            elif anim_type == "scale_in":
                anim = FadeIn(txt, scale=1.8, run_time=1)
            elif anim_type == "grow_from_center":
                anim = GrowFromCenter(txt, run_time=1)
            else:
                anim = FadeIn(txt, run_time=1)

            # 播放出现动画
            self.play(anim)
            self.wait(stay_duration)

            # 退场动画
            if i < len(texts) - 1:
                # 非最后一段：淡出后移到上方
                if current is not None:
                    self.play(FadeOut(current), run_time=0.3)
                current = txt
                self.play(txt.animate.shift(UP * 2).set_opacity(0.3), run_time=0.5)
            else:
                # 最后一段：渐隐收尾
                self.play(FadeOut(txt), run_time=0.8)

        # 清理残留
        self.wait(0.5)
