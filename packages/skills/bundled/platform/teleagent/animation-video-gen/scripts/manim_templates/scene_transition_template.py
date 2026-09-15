#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manim 动画模板 - 场景过渡动画
支持：多幕场景切换、变换过渡、组合动画

用法:
  1. 配置 SCENES 列表中的各幕内容
  2. 运行: manim -pql scene_transition_template.py SceneTransition
"""

from manim import *


class SceneTransition(Scene):
    """场景过渡动画模板"""

    def construct(self):
        # ===== 配置区 =====
        # 每幕配置：title + 内容动画函数名
        scenes = [
            {"title": "第一幕：开始", "anim": "act1_shapes"},
            {"title": "第二幕：变换", "anim": "act2_transform"},
            {"title": "第三幕：收尾", "anim": "act3_finale"},
        ]
        title_font = "SimHei"

        for i, scene_cfg in enumerate(scenes):
            # 显示幕标题
            title = Text(scene_cfg["title"], font=title_font, font_size=42)
            title.to_edge(UP)
            self.play(FadeIn(title, shift=DOWN * 0.3), run_time=0.8)
            self.wait(0.5)

            # 执行该幕动画
            anim_name = scene_cfg.get("anim", "")
            if hasattr(self, anim_name):
                getattr(self, anim_name)()
            else:
                self.wait(1)

            # 过渡到下一幕
            if i < len(scenes) - 1:
                self.play(
                    FadeOut(title),
                    *[
                        FadeOut(m)
                        for m in self.mobjects
                        if m != title
                    ],
                    run_time=0.8
                )

        # 最终清理
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.8)
        self.wait(0.5)

    def act1_shapes(self):
        """第一幕：图形展示"""
        circle = Circle(radius=1.2, color=BLUE)
        square = Square(side_length=1.5, color=YELLOW).shift(LEFT * 2.5)
        triangle = Triangle(color=GREEN).shift(RIGHT * 2.5)

        self.play(
            DrawBorderThenFill(circle),
            DrawBorderThenFill(square),
            DrawBorderThenFill(triangle),
            run_time=1.5,
        )
        self.wait(0.5)

        # 集合到中央
        self.play(
            square.animate.move_to(LEFT * 1.8),
            triangle.animate.move_to(RIGHT * 1.8),
            run_time=0.8,
        )

    def act2_transform(self):
        """第二幕：形状变换"""
        circle = Circle(radius=1, color=BLUE)
        self.play(Create(circle), run_time=0.8)

        # 圆→方→星→三角 循环变换
        square = Square(side_length=1.5, color=YELLOW)
        star = Star(n=5, color=PURPLE).scale(1.2)
        triangle = Triangle(color=RED).scale(1.3)

        targets = [square, star, triangle]
        for target in targets:
            self.play(Transform(circle, target), run_time=1.2)
            self.wait(0.3)

    def act3_finale(self):
        """第三幕：组合动画收尾"""
        shapes = VGroup(
            Circle(radius=0.5, color=RED),
            Square(side_length=0.8, color=BLUE),
            Triangle(color=GREEN).scale(0.6),
            Star(n=5, color=YELLOW).scale(0.4),
            Dot(color=PURPLE),
        )
        shapes.arrange_in_grid(rows=1, cols=5, buff=1)

        self.play(
            AnimationGroup(
                *[GrowFromCenter(s) for s in shapes],
                lag_ratio=0.2,
            ),
            run_time=2,
        )
        self.wait(0.5)

        # 同时旋转
        self.play(
            *[Rotate(s, angle=2 * PI) for s in shapes],
            run_time=1.5,
        )
