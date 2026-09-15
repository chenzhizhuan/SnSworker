---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'cca45b57-0311-4a55-a2c3-4e9ecb51082d'
  PropagateID: 'cca45b57-0311-4a55-a2c3-4e9ecb51082d'
  ReservedCode1: '67d5b478-9927-4205-9982-c28fbc723838'
  ReservedCode2: '67d5b478-9927-4205-9982-c28fbc723838'
---

# 模板锚定层 (Layer 2 · Template Anchoring)

> v6.0 新增 | 优先级：Phase 1

## 1. 解决什么问题

用户有现成的企业PPT模板（如省公司下发、品牌规范模板），希望生成的内容**严格按模板位置落位**——不是"看起来差不多"，而是文字、表格、图片精准填入模板预留的占位符位置。

核心矛盾：标准模板（T1-T16）是程序化的绝对坐标布局，而企业模板有自己的占位符体系。模板锚定层解决"框架走模板 + 内容走程序 + 两者缝合"的问题。

## 2. 核心概念

### 2.1 Layout Map

从用户模板中解剖出的结构化描述，记录每个 slide layout 的占位符信息。

```json
{
  "template_name": "省公司经营分析模板",
  "source_file": "template.pptx",
  "slide_width": 13.333,
  "slide_height": 7.5,
  "layouts": [
    {
      "layout_index": 0,
      "layout_name": "封面",
      "placeholders": [
        {
          "idx": 0,
          "name": "标题",
          "type": "TITLE",
          "x": 1.5, "y": 2.0, "w": 10.33, "h": 1.5,
          "font": { "name": "Microsoft YaHei", "size": 32, "bold": true, "color": "#FFFFFF" },
          "alignment": "center"
        },
        {
          "idx": 1,
          "name": "副标题",
          "type": "SUBTITLE",
          "x": 2.0, "y": 3.8, "w": 9.33, "h": 0.8,
          "font": { "name": "Microsoft YaHei", "size": 18, "bold": false, "color": "#FFE4E4" },
          "alignment": "center"
        }
      ],
      "background": {
        "type": "solid",
        "color": "#C00000"
      },
      "decorations": [
        { "type": "shape", "shape_type": "rect", "x": 0, "y": 6.8, "w": 13.333, "h": 0.7, "fill": "#FFD700" }
      ]
    }
  ]
}
```

### 2.2 Template Contract

Slide Contract 的扩展字段，标明每页使用哪个 layout、内容填入哪个占位符。

| 字段 | 含义 | 示例 |
|------|------|------|
| `Layout` | 引用的 layout 索引或名称 | `L0` / `封面` |
| `Anchors` | 内容→占位符的映射 | `标题→idx0, 数据→idx2` |
| `Overrides` | 需要覆盖的样式 | `idx1.font.size=14` |
| `FreeElements` | 不走占位符的额外元素 | `红竖条(y=1.0, h=5.5)` |

### 2.3 锚定模式

| 模式 | 说明 | 使用场景 |
|------|------|---------|
| **全锚定** | 所有位置走 Template Contract | 用户严格要求"跟模板一模一样" |
| **半锚定** | 关键位置（标题区、数据区）走锚定，装饰元素走程序 | 用户要模板骨架但允许美化 |
| **灵感锚定** | 只借用模板的配色、字体、间距风格 | 用户说"参考这个模板的风格" |

## 3. 工作流

### Step 2A: 模板接收与解剖

当用户提供了 .pptx 模板文件时，在 Step 1（需求解析）后插入此步骤。

```
用户提供模板 → 模板解剖 → Layout Map 生成 → 用户确认 → Slide Contract 增强字段
```

**解剖方式**（按优先级）：

1. **自动解剖**（首选）：运行 `assets/template-analyzer.py` 提取占位符信息
   ```bash
   python assets/template-analyzer.py --input template.pptx --output layout-map.json
   ```

2. **手动解剖**（fallback）：Agent 逐页分析模板截图
   - 用 `image_understanding` 识别模板页面结构
   - 人工标注关键区域的位置

3. **混合解剖**：自动提取占位符 + 截图识别装饰元素

### Step 2A-1: Layout Map 确认

生成 Layout Map 后，必须向用户展示并确认：

```
📋 Layout Map 摘要

模板：省公司经营分析模板
共 5 个 Layout：
  L0: 封面 (2个占位符: 标题、副标题)
  L1: 章节页 (2个占位符: 章节编号、章节标题)
  L2: 内容页-左文右图 (3个占位符: 标题、正文、图区)
  L3: 内容页-双栏 (4个占位符: 标题、左栏、右栏、底部备注)
  L4: 数据页 (4个占位符: 标题、KPI区、图表区、结论)

是否确认此 Layout Map？如需调整请说明。
```

### Step 3A: Slide Contract 增强

在标准 Slide Contract 表格基础上增加锚定列：

| Slide | Role | Claim | Proof | Template | **Layout** | **Anchors** | Source | Notes |
|-------|------|-------|-------|----------|-----------|------------|--------|-------|
| 1 | Cover | 封面 | — | T1 | **L0** | **标题→idx0, 副标题→idx1** | 需求 | — |
| 2 | Context | Q3经营概览 | KPI卡x3 | T13 | **L4** | **标题→idx0, KPI区→idx1, 结论→idx3** | Excel | — |

### Step 4A: 锚定代码生成

代码生成时遵循 Template Contract：

```javascript
// 全锚定模式：直接使用模板的slide布局
let slide = pres.addSlide({ masterName: 'L0_封面' }); // 或使用layout索引

// 半锚定模式：关键位置走锚定坐标，装饰走程序
let slide = pres.addSlide();
// 按Layout Map中的坐标放置标题
slide.addText(titleText, {
  x: layoutMap.layouts[0].placeholders[0].x,
  y: layoutMap.layouts[0].placeholders[0].y,
  w: layoutMap.layouts[0].placeholders[0].w,
  h: layoutMap.layouts[0].placeholders[0].h,
  fontSize: layoutMap.layouts[0].placeholders[0].font.size,
  color: layoutMap.layouts[0].placeholders[0].font.color,
  bold: layoutMap.layouts[0].placeholders[0].font.bold,
  align: layoutMap.layouts[0].placeholders[0].alignment
});
// 装饰元素走程序化生成
drawTelecomCard(slide, { ... });
```

## 4. 技术实现

### 4.1 template-analyzer.py

脚本路径：`assets/template-analyzer.py`

功能：读取 .pptx 文件，提取每个 slide layout 的：
- 占位符：名称、类型、位置(x/y/w/h)、字体样式
- 背景：填充色/渐变/图片
- 装饰形状：类型、位置、填充

输出：JSON 格式的 Layout Map

详见 `assets/template-analyzer.py`。

### 4.2 Layout Map 存储

Layout Map 生成后保存在技能目录下的 `layouts/` 子目录：

```
telecom-ppt-master/
├── layouts/                    # v6.0 新增
│   ├── 省公司经营分析模板.json
│   ├── 客户经营汇报模板.json
│   └── ...
```

命名规则：`{模板描述}.json`

### 4.3 坐标系统

Layout Map 中所有坐标使用**英寸**，与 pptxgenjs 保持一致。

关键约束：
- `slide_width` 和 `slide_height` 必须匹配目标画布（默认 13.333" × 7.5"）
- 如果模板是 4:3 比例（10" × 7.5"），需在 Layout Map 中标记，生成时做坐标转换
- 占位符位置为**绝对坐标**，不做响应式布局

### 4.4 字体继承规则

```
1. 占位符有明确字体 → 使用占位符字体
2. 占位符无字体但 Layout 有全局默认 → 使用全局默认
3. 均无 → 回退到 style-guide.md 中的字体规范
4. 用户微调指令 → 最高优先级，覆盖以上所有
```

## 5. 与各层的交互

| 交互层 | 关系 |
|--------|------|
| Layer 1 · 数据智能 | Table Contract 的表格位置从 Layout Map 的占位符坐标获取 |
| Layer 3 · 风格记忆 | 企业规范模板自动沉淀到 CORPORATE_SPEC.md |
| Layer 4 · 创意设计 | 设计思路推荐时尊重模板锚定约束，不推荐破坏模板结构的方案 |
| Layer 5 · 精控执行 | 微调指令在锚定坐标基础上叠加偏移，不重置坐标 |

## 6. 回退规则

1. Layout Map 生成失败 → 回退到标准模板（T1-T16），通知用户
2. 某个 layout 无匹配占位符 → 该页回退到标准模板，其他页维持锚定
3. 锚定代码生成后 QA 失败两次 → 该页回退到标准模板 + 手动调整
4. 用户提供模板但说"参考风格即可" → 自动使用灵感锚定模式

## 7. 使用判定

| 用户说法 | 锚定模式 | 说明 |
|----------|---------|------|
| "按这个模板做PPT" | 全锚定 | 严格按模板位置 |
| "用这个模板，内容可以美化" | 半锚定 | 位置走模板，装饰走程序 |
| "参考这个风格" | 灵感锚定 | 只借配色/字体/间距 |
| 提供模板 + "跟之前做的不太一样" | 半锚定 | 允许调整布局 |
| 无模板 | 不使用本层 | 走标准 T1-T16 |

---

## 8. 内置模板：电信5G原生模板（v8.1 新增 · 代码复刻方案）

> **v8.1 起，电信PPT大师内置一套官方模板底座。每次生成前强制询问是否使用。**
> **v8.2 起本章节描述的 pptxgenjs 代码复刻方案降级为备选，推荐方案见 §9（python-pptx 原生继承）。**

### 8.1 模板概述

文件路径：`assets/电信5G原生模板.pptx`（单页模板，已随技能分发）

模板特征：
- **极简电信商务风格**：红+蓝+白三色，无多余装饰
- **页眉头部**（y=0~0.95"）：左上红色错位方块装饰 + 标题区 + 右上5G品牌logo + 红色全宽分隔线
- **正文区**（y≈1.1"~7.35"）：纯白空白，完全自由排版
- **无页脚**：正文区直达底部，不预留页脚区域

### 8.2 Layout Map（精确坐标 · LAYOUT_WIDE 960×540pt）

```json
{
  "template_name": "电信5G原生模板",
  "source_file": "assets/电信5G原生模板.pptx",
  "slide_width": 13.333,
  "slide_height": 7.5,
  "theme_colors": {
    "brand_red": "C00000",
    "brand_blue": "0070C0",
    "background": "FFFFFF",
    "line_red": "C00000"
  },
  "layouts": [
    {
      "layout_name": "内容页",
      "page_header": {
        "red_blocks": [
          { "x": 0.35, "y": 0.18, "w": 0.35, "h": 0.35 },
          { "x": 0.53, "y": 0.38, "w": 0.18, "h": 0.18 }
        ],
        "title_area": {
          "x": 0.76, "y": 0.25, "w": 9.70, "h": 0.50,
          "prefix": { "text": "（由用户填入）", "color": "C00000", "bold": true, "fontSize": 20 },
          "suffix": { "text": "（由用户填入）", "color": "0070C0", "bold": true, "fontSize": 16 }
        },
        "5g_logo": {
          "x": 11.8, "y": 0.18,
          "digit_5": { "color": "0070C0", "fontSize": 22, "bold": true },
          "letter_g": { "color": "C00000", "fontSize": 22, "bold": true },
          "accent_line": { "color": "0070C0", "x_offset": -0.08, "y_offset": 0.08, "w": 0.15, "h": 0.03 }
        },
        "separator_line": {
          "x": 0.3, "y": 0.95, "w": 12.733, "h": 0.025,
          "color": "C00000"
        }
      },
      "content_area": {
        "x": 0.45, "y": 1.15, "w": 12.433, "h": 6.2
      },
      "background": { "type": "solid", "color": "FFFFFF" }
    }
  ]
}
```

### 8.3 模板风格覆盖规则

使用本模板时，以下电信PPT大师默认行为**被覆盖**：

| 默认行为 | 模板覆盖 |
|---------|---------|
| `addTelecomNav` 深红全宽导航栏（y=0~0.52"） | **不使用**，改为模板页眉（红色方块+标题+logo+红线） |
| `addTelecomFooter` 深红横幅页脚（y=7.05~7.50"） | **不使用**，正文区直达底部无页脚 |
| `addTitle` 红色竖条+红金渐变线标题区 | **不使用**，标题由模板页眉的红色方块+文字承担 |
| 安全区域 y=0.55"~7.05" | **改为** y=1.15"~7.35"（正文区在红线下方） |
| 卡片浅粉填充 `C.iceLight` | **保持**不变 |
| 数字红色加粗高亮 | **保持**不变 |
| 三栏卡片布局 | **保持**不变 |

### 8.4 在 pages 模块中生成模板页眉

```js
// 每个 buildSlides[i](pres, ctx) 中，先绘制模板页眉再画正文
function drawTemplateHeader(s, ctx, titlePrefix, titleSuffix) {
  const { C, F, W } = ctx;
  // 红色方块组
  s.addShape(pres.shapes.RECTANGLE, { x: 0.35, y: 0.18, w: 0.35, h: 0.35, fill: { color: "C00000" }, line: { type: "none" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.53, y: 0.38, w: 0.18, h: 0.18, fill: { color: "C00000" }, line: { type: "none" } });
  // 标题
  s.addText([
    { text: titlePrefix + "：", options: { bold: true, color: "C00000", fontSize: 20, fontFace: F.cn } },
    { text: titleSuffix, options: { bold: true, color: "0070C0", fontSize: 16, fontFace: F.cn } },
  ], { x: 0.76, y: 0.25, w: 9.70, h: 0.50, valign: "middle", margin: 0 });
  // 5G logo
  s.addText([
    { text: "5", options: { bold: true, color: "0070C0", fontSize: 22, fontFace: F.en } },
    { text: "G", options: { bold: true, color: "C00000", fontSize: 22, fontFace: F.en } },
  ], { x: 11.8, y: 0.18, w: 1.0, h: 0.55, valign: "middle", margin: 0 });
  // 蓝色折线装饰
  s.addShape(pres.shapes.RECTANGLE, { x: 11.72, y: 0.38, w: 0.15, h: 0.03, fill: { color: "0070C0" }, line: { type: "none" } });
  // 红色分隔线
  s.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 0.95, w: 12.733, h: 0.025, fill: { color: "C00000" }, line: { type: "none" } });
}
```

### 8.5 与实时预览的兼容

pages 模块中每个 `buildSlides[i]` 调用 `drawTemplateHeader(s, ctx, prefix, suffix)` 作为第一组操作，后续所有正文元素 y 坐标从 1.15" 起始。`deckMeta` 中的 `slideMetas` 正常填写。

### 8.6 使用判定

生成前必须询问，用户确认后本模板即作为本次生成的基础底版。当前仅支持**全锚定**模式（所有页面统一使用此模板页眉，正文区自由排版）。

---

## 9. python-pptx 原生底版继承（v8.2 新增 · 推荐方案）

> **v8.2 起，5G模板底版默认采用 python-pptx 原生继承方案。** 本方案与 §8 代码复刻方案的根本区别：页眉元素（5G logo 图片 + 红色方块 + 红色横线）由 slide layout 原生提供，**非代码绘制**——5G logo 是真实的 image1.png 图片，红色方块和横线是 layout 原生形状。产出 PPT 的页眉 100% 还原官方模板。

### 9.1 为什么需要原生继承

§8 的 pptxgenjs `drawTemplateHeader` 方案存在局限：
- **5G logo 是文字模拟**：用蓝色"5"+红色"G"文字模拟，非官方真实 logo 图片
- **页眉元素是代码绘制**：红色方块、横线均为 addShape 生成，与官方模板原生元素存在像素级差异
- **无法继承模板母版**：pptxgenjs 新建 slide 不携带 layout 装饰元素

原生继承方案直接用 python-pptx 加载官方 `电信5G原生模板1.0.pptx`，新建 slide 时引用含原生页眉的 layout `2019-004`，页眉元素由 layout 自动继承，无需任何代码绘制。

### 9.2 底版模板结构

文件路径：`assets/电信5G原生模板1.0.pptx`（195.5 KB，随技能分发）

| 属性 | 值 |
|------|------|
| 画布尺寸 | 13.333" × 7.5"（16:9，LAYOUT_WIDE） |
| Slide Master | 1 个 |
| Slide Layouts | 12 个（index 0-11） |
| 关键 Layout | index=11，name=`2019-004`（0 占位符 + 4 原生形状） |
| 原始 Slides | 1 个（使用 `2019-004` layout，构建时移除） |

`2019-004` layout 的 4 个原生形状（页眉元素）：

| 形状名 | 类型 | 位置/尺寸 | 说明 |
|--------|------|----------|------|
| `Line 6` | 红色横线 | y=0.83", 宽12.98" | 页眉与正文分隔线，色值 D41224 |
| `矩形10` | 红色方块 | 0.24"/0.26", 0.39"×0.38" | 主红色方块，色值 D41224 |
| `矩形11` | 错位小方块 | 0.43"/0.46", 0.26"×0.25" | 错位小红方块，色值 D41224 |
| `object 4` | 5G logo 图片 | 12.19"/0.0", 0.92"×0.93" | 真实 5G+ logo（image1.png，蓝色5+红色G+加号） |

### 9.3 主题色

原生继承方案沿用模板原红，非 telecom-red 的 #C00000：

```
模板原红: D41224  （红色方块、横线、5G logo 红色部分）
模板蓝:   0070C0  （5G logo 蓝色部分、副标题文字）
背景白:   FFFFFF
```

### 9.4 构建脚本骨架

完整示例脚本：`scripts/build_on_template.py`（FTTR培训12页，已验证通过）。核心模式如下：

```python
# -*- coding: utf-8 -*-
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu, Length
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

SRC = r"assets/电信5G原生模板1.0.pptx"   # 技能内置底版
OUT = r"输出路径/成品.pptx"

# 主题色（模板原红）
RED   = RGBColor(0xD4, 0x12, 0x24)   # 模板原红 D41224
RED2  = RGBColor(0xC0, 0x00, 0x00)   # 标题前缀用
BLUE  = RGBColor(0x00, 0x70, 0xC0)   # 标题后缀用
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT  = "微软雅黑"

# 正文安全区（页眉横线 y=0.83，留呼吸）
SX, SW = Inches(0.45), Inches(12.43)
SY     = Inches(1.15)

# ---- helper 函数 ----
def add_textbox(s, x, y, w, h, runs, align="left", valign="middle", line_spacing=None):
    """runs: list of (text, opts); opts: dict size/bold/color/font"""
    tb = s.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Pt(0); tf.margin_right = Pt(0)
    tf.margin_top = Pt(0); tf.margin_bottom = Pt(0)
    if valign == "middle": tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    elif valign == "top": tf.vertical_anchor = MSO_ANCHOR.TOP
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER if align == "center" else PP_ALIGN.LEFT
    if line_spacing: p.line_spacing = line_spacing
    first = True
    for text, opts in runs:
        if first: p.text = text if text else ""; first = False
        else: p.add_run().text = text
    for i, (text, opts) in enumerate(runs):
        run = p.runs[i]
        run.font.name = opts.get("font", FONT)
        run.font.size = Pt(opts.get("size", 12))
        if opts.get("bold"): run.font.bold = True
        col = opts.get("color")
        if col is not None: run.font.color.rgb = col
    return tb

def add_rect(s, x, y, w, h, fill=None, line=None, line_w=None,
             shape=MSO_SHAPE.RECTANGLE):
    """line_w 支持 None/int/float/Length 四种类型"""
    sp = s.shapes.add_shape(shape, x, y, w, h)
    if fill is not None: sp.fill.solid(); sp.fill.fore_color.rgb = fill
    else: sp.fill.background()
    if line is not None:
        sp.line.color.rgb = line
        if line_w is None: sp.line.width = Pt(1)
        elif isinstance(line_w, Length): sp.line.width = line_w
        elif isinstance(line_w, (int, float)): sp.line.width = Pt(line_w)
        else: sp.line.width = line_w
    else: sp.line.fill.background()
    sp.shadow.inherit = False
    return sp

def add_oval(s, x, y, w, h, fill=None, line=None, line_w=None):
    return add_rect(s, x, y, w, h, fill, line, line_w, MSO_SHAPE.OVAL)

def draw_card(s, x, y, w, h, line=RED2, line_w=1.0, fill=WHITE):
    add_rect(s, x, y, w, h, fill=fill, line=line, line_w=Pt(line_w),
             shape=MSO_SHAPE.ROUNDED_RECTANGLE)

def add_header_title(s, prefix, suffix):
    """页眉标题文字（在原生红色方块右侧、横线上方）"""
    add_textbox(s, Inches(0.80), Inches(0.24), Inches(11.0), Inches(0.46),
                [(prefix+"：", {"size":18,"bold":True,"color":RED2}),
                 (suffix, {"size":16,"bold":True,"color":BLUE})],
                align="left", valign="middle")

# ---- 构建 ----
prs = Presentation(SRC)
# 找到 2019-004 layout
layout = None
for lo in prs.slide_masters[0].slide_layouts:
    if lo.name == "2019-004":
        layout = lo; break
if layout is None:
    raise RuntimeError("找不到 2019-004 layout")

# 移除原 slide1
xml_slides = prs.slides._sldIdLst
xml_slides.remove(list(xml_slides)[0])

def new_slide():
    return prs.slides.add_slide(layout)

def hdr(s, prefix, suffix):
    add_header_title(s, prefix, suffix)

# 逐页构建：new_slide() → hdr(s, 前缀, 后缀) → 正文元素
s = new_slide(); hdr(s, "章节前缀", "页面后缀")
# ... 正文区填内容，y 从 1.15" 起

prs.save(OUT)
```

### 9.5 关键技术要点（避坑指南）

| 要点 | 说明 |
|------|------|
| **Length 类型双重包装陷阱** | `Pt()` 返回的 Length 继承自 int，`isinstance(Pt(1), int)` 为 True，导致 `Pt(Pt(1))` 越界报错。add_rect 的 line_w 参数必须先判断 `isinstance(line_w, Length)` 再判断 int/float。**必须 import Length**。 |
| **移除原 slide 的正确方式** | 用 `prs.slides._sldIdLst.remove(list(xml_slides)[0])` 移除原 slide1，不要用 `prs.slides._sldIdLst[0]` 直接操作。 |
| **Duplicate name 警告** | python-pptx 移除原 slide 时 rels 未完全清理，save 时会出现 `Duplicate name: 'ppt/slides/slide1.xml'` 警告。**不影响 PowerPoint 正常打开和渲染**，可忽略。 |
| **封面页处理** | 封面页通常不画页眉标题文字（`hdr`），保留原生红方块+5G logo+横线作为顶部装饰即可，主标题放在正文区。 |
| **页眉标题文字位置** | `add_header_title` 在 x=0.80", y=0.24" 补标题文字（前缀红:后缀蓝），位于原生红色方块右侧、横线上方区域。 |
| **正文安全区** | y=1.15"~7.35"，x=0.45"~12.88"，正文元素均在此区域内。 |
| **形状阴影关闭** | `sp.shadow.inherit = False` 关闭 python-pptx 默认形状阴影，避免与电信风格冲突。 |

### 9.6 QA 验证方式

原生继承方案产出的 PPT，QA 验证采用宿主提供的受控渲染器输出 PNG 缩略图（非实时预览）：

```text
render_slides(input_pptx, output_directory, width=1280, height=720)
```

然后用 `image_understanding` 工具逐页检查：原生页眉是否显示、5G logo 图片是否清晰、内容是否完整无溢出。

### 9.7 与代码复刻方案（§8）的对比

| 维度 | 原生继承（v8.2 推荐） | 代码复刻（v8.1 备选） |
|------|----------------------|----------------------|
| 引擎 | python-pptx | pptxgenjs (JS) |
| 页眉 5G logo | **真实图片** image1.png | 文字模拟（蓝5+红G） |
| 页眉方块/横线 | layout 原生形状 | addShape 代码绘制 |
| 还原度 | 100% 官方模板 | ~90%（像素级差异） |
| 实时预览 | 由宿主受控渲染器提供 | 支持（pages模块） |
| 依赖 | python-pptx + 宿主渲染能力 | Node.js + pptxgenjs |
| 适用场景 | 正式交付、需完美还原模板 | 快速预览、纯JS工作流 |

### 9.8 使用判定

| 用户需求 | 推荐方案 |
|---------|---------|
| "用5G模板做PPT"（默认） | **原生继承**（v8.2） |
| 需要实时预览生成过程 | 代码复刻（§8） |
| 纯 JS/Node 环境，无 python-pptx | 代码复刻（§8） |
| 5G logo 必须是真实图片 | **原生继承**（v8.2） |
| 正式汇报交付 | **原生继承**（v8.2） |
