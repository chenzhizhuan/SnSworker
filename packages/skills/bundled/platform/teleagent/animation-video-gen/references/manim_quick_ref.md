---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '970e26a5-0b80-4d6d-b307-e966609ca76e'
  PropagateID: '970e26a5-0b80-4d6d-b307-e966609ca76e'
  ReservedCode1: '57e17a43-65cd-4816-ae9c-7491d91e0af1'
  ReservedCode2: '57e17a43-65cd-4816-ae9c-7491d91e0af1'
---

---
---

# Manim 动画快速参考

## 常用动画类型

### 出场动画
- `FadeIn(mobj, shift=UP, run_time=1)` - 淡入
- `Write(mobj, run_time=1.5)` - 书写效果
- `Create(mobj, run_time=1)` - 创建轮廓
- `DrawBorderThenFill(mobj)` - 描边后填充
- `GrowFromCenter(mobj)` - 从中心放大
- `AddTextLetterByLetter(text)` - 逐字出现

### 变换动画
- `mobj.animate.shift(RIGHT * 2)` - 移动
- `mobj.animate.scale(1.5)` - 缩放
- `Rotate(mobj, angle=PI/4)` - 旋转
- `mobj.animate.set_color(RED)` - 变色
- `Transform(mobj, target)` - 形状变换
- `ReplacementTransform(mobj, target)` - 替换变换

### 退场动画
- `FadeOut(mobj)` - 淡出
- `RemoveTextLetterByLetter(text)` - 逐字消失
- `Uncreate(mobj)` - 反向创建

### 组合
- `AnimationGroup(*anims, lag_ratio=0.2)` - 依次播放
- `self.play(*anims, run_time=2)` - 同时播放
- `self.wait(1)` - 停顿

## 常用图形对象

| 类名 | 说明 | 示例 |
|------|------|------|
| `Circle(radius=1)` | 圆形 | `Circle(radius=1.5, color=BLUE)` |
| `Square(side_length=2)` | 正方形 | `Square(side_length=1, color=RED)` |
| `Rectangle(width, height)` | 矩形 | `Rectangle(width=4, height=2)` |
| `Triangle()` | 三角形 | `Triangle(color=GREEN)` |
| `Star(n=5)` | 星形 | `Star(n=6, color=YELLOW)` |
| `Dot()` | 点 | `Dot(point=ORIGIN, color=RED)` |
| `Line(start, end)` | 线段 | `Line(LEFT, RIGHT)` |
| `Arrow(start, end)` | 箭头 | `Arrow(UP, DOWN)` |
| `Text("文本")` | 文字 | `Text("你好", font="SimHei")` |
| `MathTex(r"x^2")` | 数学公式 | `MathTex(r"E=mc^2")` |
| `ImageMobject(path)` | 图片 | `ImageMobject("photo.jpg")` |
| `VGroup(*mobjs)` | 对象组 | `VGroup(c1, c2, c3)` |

## 位置与布局

```python
mobj.shift(RIGHT * 2)       # 相对移动
mobj.move_to(ORIGIN)        # 移到指定点
mobj.to_edge(UP)            # 贴边
mobj.next_to(other, RIGHT)  # 放在另一对象旁
group.arrange(RIGHT, buff=0.5)  # 水平排列
group.arrange_in_grid(rows=2, cols=3)  # 网格排列
```

## 常量
- 方向: `UP, DOWN, LEFT, RIGHT, ORIGIN, UL, UR, DL, DR`
- 颜色: `RED, BLUE, GREEN, YELLOW, PURPLE, ORANGE, PINK, WHITE, BLACK`
- 数学: `PI, TAU, DEGREES`

## 渲染命令

```powershell
manim -pql script.py SceneName   # 低质量预览(快速)
manim -pqm script.py SceneName   # 中等质量
manim -pqh script.py SceneName   # 高质量 1080p 60fps
manim -pqk script.py SceneName   # 4K
```

## 中文字体
```python
# Windows 中文字体
Text("中文文本", font="SimHei")          # 黑体
Text("中文文本", font="Microsoft YaHei")  # 微软雅黑
Text("中文文本", font="KaiTi")            # 楷体
```

## 图片动画
```python
img = ImageMobject("photo.jpg")
img.height = 4  # 设置高度
self.play(FadeIn(img))
self.play(img.animate.shift(RIGHT * 3))
self.play(img.animate.scale(0.5))  # 缩小
```