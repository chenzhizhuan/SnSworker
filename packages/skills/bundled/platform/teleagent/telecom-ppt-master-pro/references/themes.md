---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '2f2b31b1-af46-438e-bd2a-980777a2fb5e'
  PropagateID: '2f2b31b1-af46-438e-bd2a-980777a2fb5e'
  ReservedCode1: 'bda42983-6849-46ac-bf8b-64a98c592d86'
  ReservedCode2: 'bda42983-6849-46ac-bf8b-64a98c592d86'
---

# Themes

> **v8.0 升级**：融合 nexu-io/open-design (81.4K stars) 设计方法论，全部主题升级为 **10 级色阶 token 体系**。
> 详细设计原理和语义 token 映射见 `references/design-system.md`（权威来源）。
> 旧版三色体系保留向后兼容（`C.primary` 等映射为 `C.brand[500]`），但新代码生成优先使用 token 体系。

每个主题是一个完整的 `C` 颜色对象，复制整个块到 boilerplate 即可使用。

所有主题遵循相同的 **12 角色语义结构**（v8.0 升级）：

| 角色 (v8.0) | 旧版等价 | 用途 |
|-------------|---------|------|
| `brand[50-900]` | `primary` 系列 | 品牌主色 10 级色阶——从浅底到深标题 |
| `accent[50-900]` | `accent` 系列 | 强调互补色 10 级色阶——装饰、金色、特殊标注 |
| `positive[50-900]` | 新增 | 正向/达标色 10 级——正增长、绿色标注（仅 executive-blue） |
| `neutral[50-900]` | `neutral` 系列 | 统一灰度色阶（全部主题共用，见 design-system.md §1.3） |
| `surface` 系列 | `white/bg/ice` 系列 | 表面材质——页底/卡片底/标题栏底/品牌底 |
| `border` 系列 | `border` | 描边色阶 |
| `text` 系列 | `text/textLight/muted` | 正文/辅助灰文字色 |
| `highlight` | `highlight` | 黄色高亮底色（电信传统保留） |
| `warning` | `warning` | 警示/预警色 |
| `elevation` | 新增 | 阴影高程级 (card/overlay/prominent)，见 design-system.md §4 |
| `fontStack` | 新增 | 字体配对栈 (sans/display/number/serif)，见 design-system.md §2 |
| 别名 (`navy`, `gold`, `coral`) | 不变 | 向后兼容的别名（映射到 brand/accent 基准色） |

---

## 主题 1 · `telecom-red`（默认主题 · 中国电信风格）

电信深红 + 金色 + 浅粉 + 黄色高亮。基于1764份中国电信PPT统计分析提取。

> **本技能的默认主题。** 当用户提到"电信PPT"、"中国电信"、"运营分析"、"宣贯材料"、"标准化运营"等关键词时，自动使用此主题。详细视觉规范见 `style-guide.md`。

```js
// === v8.0 Token 化配色 ===
const C = {
  // Brand — 电信深红 10 级色阶 (50=最浅 → 900=最深)
  brand: {
    "50":"FFF5F5", "100":"FFE4E4", "200":"F4C2C2", "300":"E8A0A0",
    "400":"D06060", "500":"C00000", "600":"A8001A", "700":"8B0012",
    "800":"6E000A", "900":"4D0004"
  },
  // Accent — 金色 10 级色阶
  accent: {
    "50":"FFFCE0", "100":"FFF8B0", "200":"FFF070", "300":"FFE830",
    "400":"FFD700", "500":"E0C200", "600":"C0A800", "700":"A09000",
    "800":"807000", "900":"605000"
  },
  // Neutral — 统一灰度色阶（design-system.md §1.3）
  neutral: {
    "50":"FAFAFA", "100":"F5F5F5", "200":"E8E8E8", "300":"D4D4D4",
    "400":"A3A3A3", "500":"888888", "600":"666666", "700":"404040",
    "800":"262626", "900":"171717"
  },
  // Semantic 语义色
  surface:      "FFFFFF",       // 表面基底（不变）
  surfaceRaised:"FFFFFF",       // 卡片面 = 白底+浅粉填充（真正卡片底用 brand[100]）
  surfaceHeader:"FFE4E4",       // 标题栏底 = brand[100]
  surfaceBrand: "C00000",       // 品牌底 = brand[500]
  border:       "E8B4B4",       // 描边 = brand[200] 附近
  borderLight:  "F4C2C2",       // 轻描边
  // Text
  textPrimary:  "262626",       // 正文 = neutral[800]（替代纯黑更柔和）
  textSecondary:"888888",       // 辅助灰 = neutral[500]
  textInverse:  "FFFFFF",       // 反色文字（深底上用）
  // 电信特有语义色
  highlight:    "FFFF00",       // 黄色高亮底色
  warning:      "FF0000",       // 警示红
  // 高程阴影 (design-system.md §4)
  elevation: {
    card:      { type:"outer", color:"000000", blur:4,  offset:1,  angle:270, opacity:0.06 },
    overlay:   { type:"outer", color:"000000", blur:8,  offset:2,  angle:270, opacity:0.10 },
    prominent: { type:"outer", color:"000000", blur:12, offset:3,  angle:270, opacity:0.14 },
  },
  // 字体栈 (design-system.md §2)
  font: {
    sans:    "Microsoft YaHei",
    display: "Microsoft YaHei",
    number:  "Arial",
    serif:   "SimSun",
  },
};

// === v8.0 向后兼容别名（旧代码不报错）===　
C.primary = C.brand[500]; C.primaryDark = C.brand[600]; C.primaryLight = C.brand[400];
C.accentHex = C.accent[400]; C.accentLightHex = C.accent[100]; C.accentPaleHex = C.accent[50];
C.contrast = C.neutral[700]; C.contrastLight = C.neutral[600]; C.contrastPale = C.neutral[100];
C.white = C.surface; C.bg = C.surface; C.ice = C.surface;
C.iceLight = C.brand[100]; C.iceMid = C.surfaceHeader; C.border = C.border;
C.text = C.neutral[800]; C.textLight = C.neutral[700]; C.muted = C.neutral[500];
C.navy = C.primary; C.navyDark = C.primaryDark; C.navyLight = C.primaryLight;
C.gold = C.accent[400]; C.goldLight = C.accent[100]; C.goldPale = C.accent[50];
C.coral = C.contrast; C.coralLight = C.contrastLight; C.coralPale = C.contrastPale;
```

### telecom-red 特有的 helper 函数

电信风格需要以下额外 helpers（在 `telecom-boilerplate.js` 中已定义）：

```js
// 电信风格：标题栏红金渐变线
function addTelecomTitleLine(slide, y) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: y, w: 6.0, h: 0.04,
    fill: { color: C.primary }, line: { type: "none" },
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.4, y: y, w: 2.5, h: 0.04,
    fill: { color: C.accent }, line: { type: "none" },
  });
}

// 电信风格：顶部深红通栏（替代默认 addNav）
function addTelecomNav(slide, active) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: W, h: 0.52,
    fill: { color: C.primary }, line: { type: "none" },
  });
  addTelecomTitleLine(slide, 0.50);
  slide.addText(DECK_TITLE_BAR, {
    x: 0.4, y: 0.05, w: W - 0.8, h: 0.45,
    fontFace: F.cn, fontSize: 14, bold: true,
    color: C.white, align: "left", valign: "middle", margin: 0,
  });
}

// 电信风格：底部红色横幅（替代默认 addFooter）
function addTelecomFooter(slide, pageNum) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: H - 0.45, w: W, h: 0.45,
    fill: { color: C.primary }, line: { type: "none" },
  });
  addTelecomTitleLine(slide, H - 0.48);
  slide.addText(`${pres.author}  ·  ${SECTION_NAME || pres.title}`, {
    x: 0.4, y: H - 0.4, w: 6, h: 0.3,
    fontFace: F.cn, fontSize: 10,
    color: C.white, align: "left", valign: "middle", margin: 0,
  });
  const right = (pageNum === "—" || pageNum == null)
    ? "—"
    : `${SECTION_NAME ? SECTION_NAME + "  ·  " : ""}${pageNum} / ${TOTAL_PAGES}`;
  slide.addText(right, {
    x: W - 4.4, y: H - 0.4, w: 4, h: 0.3,
    fontFace: F.cn, fontSize: 10,
    color: C.white, align: "right", valign: "middle", margin: 0,
  });
}

// 电信风格：圆角卡片阴影（比默认更轻）
function makeTelecomShadow() {
  return { type: "outer", color: "000000", blur: 5, offset: 1.5, angle: 270, opacity: 0.08 };
}

// 电信风格：数字目标高亮（红色加粗 + 可选黄色底色）
function formatTelecomNumber(text, withHighlight) {
  if (withHighlight) {
    return [
      { text: "  " + text + "  ", options: { bold: true, color: C.primary, highlight: C.highlight, fontSize: 13 } }
    ];
  }
  return [
    { text: text, options: { bold: true, color: C.primary, fontSize: 13 } }
  ];
}
```

### 电信风格的金规则覆盖

使用 `telecom-red` 时，以下规则覆盖默认的黄金规则：

1. **页头页尾**：顶部深红通栏 0~0.52"，底部横幅 7.08~7.50"，有效内容区 0.55~7.05"
2. **卡片**：圆角 0.08~0.12"，填充 `C.iceLight`（浅粉），描边 `C.border`（浅红），使用 `makeTelecomShadow()`
3. **数字目标**：红色加粗（`C.primary`），关键数据可用 `C.highlight` 黄底
4. **标题栏**：`C.iceMid`（标题栏浅粉）底板 + 深红加粗文字
5. **红色竖条**：条目层级用 0.12"宽红色竖条装饰（颜色 `C.primary`）

---

## 主题 2 · `academic-red`

学术红 + 暗金 + 炭灰。适用于：论文答辩、学术会议、大学活动。

```js
const C = {
  primary:      "A02123",
  primaryDark:  "7A1A1A",
  primaryLight: "B53338",
  accent:       "B89860",
  accentLight:  "D4B87A",
  accentPale:   "F4E8D0",
  contrast:     "2C2C2C",
  contrastLight:"4A4A4A",
  contrastPale: "F0F0F0",
  white:        "FFFFFF",
  bg:           "FFFFFF",
  ice:          "FFFFFF",
  iceLight:     "FAFAFA",
  iceMid:       "E0E0E0",
  border:       "D5D5D5",
  text:         "1A1A1A",
  textLight:    "4A4A4A",
  muted:        "707070",
};
C.navy = C.primary; C.navyDark = C.primaryDark; C.navyLight = C.primaryLight;
C.gold = C.accent; C.goldLight = C.accentLight; C.goldPale = C.accentPale;
C.coral = C.contrast; C.coralLight = C.contrastLight; C.coralPale = C.contrastPale;
```

---

## 主题 3 · `business-navy`

深海军蓝 + 铜色强调 + 暖灰。适用于：企业汇报、投资人路演、董事会、咨询报告。

```js
const C = {
  primary:      "1B365D",
  primaryDark:  "0F1F38",
  primaryLight: "2E4F7C",
  accent:       "C9A961",
  accentLight:  "E0C68B",
  accentPale:   "F5EBD3",
  contrast:     "8B4513",
  contrastLight:"A0633A",
  contrastPale: "F0E4DA",
  white:        "FFFFFF",
  bg:           "FFFFFF",
  ice:          "FFFFFF",
  iceLight:     "F7F8FA",
  iceMid:       "DEE3EA",
  border:       "C8CFD8",
  text:         "1A1F2E",
  textLight:    "4A5468",
  muted:        "707A8C",
};
C.navy = C.primary; C.navyDark = C.primaryDark; C.navyLight = C.primaryLight;
C.gold = C.accent; C.goldLight = C.accentLight; C.goldPale = C.accentPale;
C.coral = C.contrast; C.coralLight = C.contrastLight; C.coralPale = C.contrastPale;
```

---

## 主题 4 · `tech-cyan`

靛蓝 + 青色强调 + 太空灰。适用于：AI/ML/SaaS、开发者大会、技术演示。

```js
const C = {
  primary:      "2E3192",
  primaryDark:  "1B1D5C",
  primaryLight: "4A4FB8",
  accent:       "00B4D8",
  accentLight:  "48CAE4",
  accentPale:   "CAF0F8",
  contrast:     "E63946",
  contrastLight:"EF6776",
  contrastPale: "FBE3E5",
  white:        "FFFFFF",
  bg:           "FFFFFF",
  ice:          "FFFFFF",
  iceLight:     "F4F6FB",
  iceMid:       "D8DDE8",
  border:       "C0C7D6",
  text:         "0F1729",
  textLight:    "3D4663",
  muted:        "6B7494",
};
C.navy = C.primary; C.navyDark = C.primaryDark; C.navyLight = C.primaryLight;
C.gold = C.accent; C.goldLight = C.accentLight; C.goldPale = C.accentPale;
C.coral = C.contrast; C.coralLight = C.contrastLight; C.coralPale = C.contrastPale;
```

---

## 主题 5 · `warm-amber`

橙色 + 奶油 + 石板灰。适用于：培训课件、教育、内部启动会、品牌故事。

```js
const C = {
  primary:      "C5530A",
  primaryDark:  "8E3A06",
  primaryLight: "E07020",
  accent:       "F4A261",
  accentLight:  "F8C088",
  accentPale:   "FCE7D2",
  contrast:     "264653",
  contrastLight:"3F6072",
  contrastPale: "DCE4E8",
  white:        "FFFFFF",
  bg:           "FFFEFA",
  ice:          "FFFFFF",
  iceLight:     "FBF6EE",
  iceMid:       "EDE2D0",
  border:       "D6CAB5",
  text:         "2A1F12",
  textLight:    "55432B",
  muted:        "8A7559",
};
C.navy = C.primary; C.navyDark = C.primaryDark; C.navyLight = C.primaryLight;
C.gold = C.accent; C.goldLight = C.accentLight; C.goldPale = C.accentPale;
C.coral = C.contrast; C.coralLight = C.contrastLight; C.coralPale = C.contrastPale;
```

---

## 主题 6 · `minimal-mono`

极简黑白 + 黄铜单色强调。适用于：编辑出版、设计作品集、艺术演讲、高端品牌。

```js
const C = {
  primary:      "1A1A1A",
  primaryDark:  "000000",
  primaryLight: "404040",
  accent:       "D4AF37",
  accentLight:  "E6C863",
  accentPale:   "F5EBC8",
  contrast:     "707070",
  contrastLight:"909090",
  contrastPale: "EEEEEE",
  white:        "FFFFFF",
  bg:           "FAFAF7",
  ice:          "FFFFFF",
  iceLight:     "F5F5F2",
  iceMid:       "E0E0DC",
  border:       "C8C8C4",
  text:         "0A0A0A",
  textLight:    "3A3A3A",
  muted:        "6E6E6E",
};
C.navy = C.primary; C.navyDark = C.primaryDark; C.navyLight = C.primaryLight;
C.gold = C.accent; C.goldLight = C.accentLight; C.goldPale = C.accentPale;
C.coral = C.contrast; C.coralLight = C.contrastLight; C.coralPale = C.contrastPale;
```

---

## 主题 7 · `executive-blue`（v7.0 新增 · 高管座谈会蓝）

电信品牌蓝主导 + 红色强调 + 绿色达标。基于2026年安徽公司总经理座谈会三份发言材料深度拆解提取。

> **座谈会/半年会场景专用主题。** 当用户提到"座谈会""半年会""经营复盘""高管发言""发言材料"等关键词时，自动使用此主题。详细视觉规范见 `executive-style-guide.md`。

与 `telecom-red` 的根本性差异：**蓝色主导（非红色主导）**。蓝色=正常/正面（标题/导航/正常增长数据/柱状图主色），红色=异常/负面/核心强调（负增长数据/负拉动指标/核心结论关键词/警示框），绿色=达标/优秀。

```js
// === v8.0 Token 化配色（座谈会蓝）===
const C = {
  // Brand — 电信蓝 10 级色阶
  brand: {
    "50":"F0F7FD", "100":"E0F0FA", "200":"B8D8F0", "300":"88B8E0",
    "400":"5090D0", "500":"0070C0", "600":"0055B8", "700":"004090",
    "800":"003070", "900":"002050"
  },
  // Accent — 电信红 10 级色阶（作为强调色）
  accent: {
    "50":"FFF0F0", "100":"FDE8E8", "200":"F4C2C2", "300":"E89090",
    "400":"D04040", "500":"C00000", "600":"A8001A", "700":"8B0012",
    "800":"6E000A", "900":"4D0004"
  },
  // Positive — 绿色 10 级色阶（达标/正面/标杆）
  positive: {
    "50":"F0FDF4", "100":"DCFCE7", "200":"BBF7D0", "300":"86EFAC",
    "400":"4ADE80", "500":"16A34A", "600":"15803D", "700":"166534",
    "800":"14532D", "900":"052E16"
  },
  // Neutral — 统一灰度色阶
  neutral: {
    "50":"FAFAFA", "100":"F5F5F5", "200":"E8E8E8", "300":"D4D4D4",
    "400":"A3A3A3", "500":"888888", "600":"666666", "700":"404040",
    "800":"262626", "900":"171717"
  },
  // Semantic 语义色
  surface:      "FFFFFF",
  surfaceRaised:"FFFFFF",       // 卡片面（白底）
  surfaceHeader:"E8F0F8",       // 标题栏底 = brand[100] 偏蓝
  surfaceBrand: "0070C0",       // 品牌底 = brand[500]
  border:       "D0D8E0",       // 浅蓝灰描边
  borderLight:  "E0E8F0",
  // Text
  textPrimary:  "262626",       // neutral[800]
  textSecondary:"888888",       // neutral[500]
  textInverse:  "FFFFFF",
  // 座谈会特有语义色
  highlight:    "FFFF00",       // 黄色高亮底色（保留）
  warning:      "C00000",       // 警示红 = accent[500]
  brandRed:     "D6001F",       // 品牌红（封面标题）
  // 高程阴影
  elevation: {
    card:      { type:"outer", color:"000000", blur:4,  offset:1,  angle:270, opacity:0.06 },
    overlay:   { type:"outer", color:"000000", blur:8,  offset:2,  angle:270, opacity:0.10 },
    prominent: { type:"outer", color:"000000", blur:12, offset:3,  angle:270, opacity:0.14 },
  },
  // 字体栈
  font: {
    sans:    "Microsoft YaHei",
    display: "Microsoft YaHei",
    number:  "Arial",
    serif:   "SimSun",
  },
};

// === 向后兼容别名 ===
C.primary = C.brand[500]; C.primaryDark = C.brand[600]; C.primaryLight = C.brand[400];
C.accentHex = C.accent[500]; C.accentLightHex = C.accent[300]; C.accentPaleHex = C.accent[100];
C.contrast = C.neutral[700]; C.contrastLight = C.neutral[600]; C.contrastPale = C.neutral[100];
C.white = C.surface; C.bg = C.surface; C.ice = C.surface;
C.iceLight = C.brand[50]; C.iceMid = C.surfaceHeader;
C.text = C.neutral[800]; C.textLight = C.neutral[700]; C.muted = C.neutral[500];
C.navy = C.primary; C.navyDark = C.primaryDark; C.navyLight = C.primaryLight;
C.gold = C.accent[400]; C.goldLight = C.accent[200]; C.goldPale = C.accent[50];
C.coral = C.contrast; C.coralLight = C.contrastLight; C.coralPale = C.contrastPale;
```

### executive-blue 特有的 helper 函数

座谈会风格需要以下额外 helpers（在 `telecom-boilerplate.js` 底部已定义）：

```js
// 座谈会风格：模块进度标签导航（蓝色标签 + 页面标题 + 品牌Logo）
function addExecutiveNav(slide, moduleLabel, moduleName, brandLogo) {
  // 蓝色通栏导航栏
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: W, h: 0.50,
    fill: { color: C.primary }, line: { type: "none" },
  });
  // 左侧：蓝色模块进度标签（如"总体收入（1/5）"）
  if (moduleLabel) {
    slide.addText(moduleLabel, {
      x: 0.3, y: 0.05, w: 3.5, h: 0.40,
      fontFace: F.cn, fontSize: 12, bold: true,
      color: C.white, align: "left", valign: "middle", margin: 0,
    });
  }
  // 中间：页面标题
  if (moduleName) {
    slide.addText(moduleName, {
      x: 4.0, y: 0.05, w: 6.0, h: 0.40,
      fontFace: F.cn, fontSize: 13, bold: true,
      color: C.white, align: "center", valign: "middle", margin: 0,
    });
  }
  // 右侧：品牌标识（如"天翼AI"）
  if (brandLogo) {
    slide.addText(brandLogo, {
      x: W - 2.5, y: 0.05, w: 2.2, h: 0.40,
      fontFace: F.cn, fontSize: 11,
      color: C.white, align: "right", valign: "middle", margin: 0,
    });
  }
}

// 座谈会风格：底部浅灰页脚（非红色横幅）
function addExecutiveFooter(slide, pageNum) {
  // 底部浅灰横线
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: H - 0.38, w: W, h: 0.02,
    fill: { color: C.border }, line: { type: "none" },
  });
  // 左侧单位+章节
  slide.addText(`${pres.author}  ·  ${SECTION_NAME || pres.title}`, {
    x: 0.4, y: H - 0.33, w: 6, h: 0.28,
    fontFace: F.cn, fontSize: 9,
    color: C.muted, align: "left", valign: "middle", margin: 0,
  });
  // 右侧页码
  const right = (pageNum === "—" || pageNum == null)
    ? "—"
    : `${SECTION_NAME ? SECTION_NAME + "  ·  " : ""}${pageNum} / ${TOTAL_PAGES}`;
  slide.addText(right, {
    x: W - 4.0, y: H - 0.33, w: 3.6, h: 0.28,
    fontFace: F.cn, fontSize: 9,
    color: C.muted, align: "right", valign: "middle", margin: 0,
  });
}

// 座谈会风格：结论先行标题区（蓝色竖条 + 蓝色标题 + 结论条）
function addExecutiveTitle(slide, title, conclusionBar) {
  // 蓝色竖条装饰
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 0.62, w: 0.12, h: 0.55,
    fill: { color: C.primary }, line: { type: "none" },
  });
  // 主标题 — 蓝色 Bold
  slide.addText(title, {
    x: 0.65, y: 0.58, w: 11.5, h: 0.45,
    fontFace: F.cn, fontSize: 20, bold: true,
    color: C.primary, align: "left", valign: "middle", margin: 0,
  });
  // 蓝色细分隔线
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.18, w: W - 0.8, h: 0.02,
    fill: { color: C.primary }, line: { type: "none" },
  });
  // 结论条（蓝色底白字，2-3行核心判断）
  if (conclusionBar) {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.4, y: 1.30, w: W - 0.8, h: 0.55,
      fill: { color: C.primary }, line: { type: "none" },
      rectRadius: 0.05,
    });
    slide.addText(conclusionBar, {
      x: 0.6, y: 1.30, w: W - 1.2, h: 0.55,
      fontFace: F.cn, fontSize: 12, bold: true,
      color: C.white, align: "left", valign: "middle", margin: [0, 6, 0, 6],
    });
  }
}

// 座谈会风格：正负双色数字格式化
function fmtExecutiveNumber(text, isPositive) {
  const color = isPositive ? C.positive : C.accent;
  return { text: text, options: { bold: true, color: color, fontSize: 13 } };
}

// 座谈会风格：圆形指标卡
function drawExecutiveKPI(slide, x, y, w, h, { label, value, unit, change, isPositive }) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h,
    fill: { color: C.white }, line: { color: C.border, width: 1 },
    shadow: makeTelecomShadow(), rectRadius: 0.08,
  });
  // 标签
  slide.addText(label, {
    x: x + 0.1, y: y + 0.08, w: w - 0.2, h: 0.3,
    fontFace: F.cn, fontSize: 10,
    color: C.muted, align: "center", valign: "middle", margin: 0,
  });
  // 数值
  slide.addText(value, {
    x: x + 0.1, y: y + 0.35, w: w - 0.2, h: 0.5,
    fontFace: F.cn, fontSize: 24, bold: true,
    color: C.primary, align: "center", valign: "middle", margin: 0,
  });
  // 单位
  if (unit) {
    slide.addText(unit, {
      x: x + 0.1, y: y + 0.80, w: w - 0.2, h: 0.25,
      fontFace: F.cn, fontSize: 9,
      color: C.muted, align: "center", valign: "middle", margin: 0,
    });
  }
  // 变化（正绿负红）
  if (change) {
    slide.addText(change, {
      x: x + 0.1, y: y + h - 0.30, w: w - 0.2, h: 0.25,
      fontFace: F.cn, fontSize: 11, bold: true,
      color: isPositive ? C.positive : C.accent,
      align: "center", valign: "middle", margin: 0,
    });
  }
}

// 座谈会风格：卡片构建（白底浅灰描边，非粉色填充）
function drawExecutiveCard(slide, x, y, w, h, { header, headerColor, bodyFn }) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h,
    fill: { color: C.white }, line: { color: C.border, width: 1.2 },
    shadow: makeTelecomShadow(), rectRadius: 0.08,
  });
  if (header) {
    slide.addShape(pres.shapes.RECTANGLE, {
      x, y, w, h: 0.40,
      fill: { color: headerColor || C.iceMid }, line: { type: "none" },
      rectRadius: 0.08,
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x, y: y + 0.30, w, h: 0.10,
      fill: { color: headerColor || C.iceMid }, line: { type: "none" },
    });
    slide.addText(header, {
      x: x + 0.12, y, w: w - 0.24, h: 0.40,
      fontFace: F.cn, fontSize: 13, bold: true,
      color: C.primary, align: "center", valign: "middle", margin: 0,
    });
  }
  if (bodyFn) bodyFn(slide, x, y + (header ? 0.40 : 0), w, h - (header ? 0.40 : 0));
}
```

### executive-blue 的金规则覆盖

使用 `executive-blue` 时，以下规则覆盖默认的黄金规则：

1. **页头页尾**：顶部蓝色通栏 0~0.50"，底部浅灰横线 7.12~7.50"，有效内容区 0.55~7.10"
2. **卡片**：圆角 0.08"，白色填充（非粉色），浅蓝灰描边 `C.border`，轻阴影
3. **数字目标**：正增长用绿色加粗 `C.positive`，负增长用红色加粗 `C.accent`，核心结论用蓝色加粗 `C.primary`
4. **标题栏**：浅蓝 `C.iceMid` 底板 + 蓝色加粗文字（非红色）
5. **结论条**：蓝色底 `C.primary` 白字加粗，2-3行核心判断，放在标题区下方
6. **底部判断条**：正面蓝色/负面红色，1行总结判断
7. **正负双色编码**：柱状图蓝色=正增长，红色=负增长，直接标注差值（如+0.53PP）

---

## 品牌色定制

当用户提供自己的品牌色时，按以下规则构建自定义主题：

1. **分类品牌色**：冷色（蓝/青）参考 `business-navy`/`tech-cyan`；暖色（红/橙）参考 `telecom-red`/`academic-red`/`warm-amber`；黑白灰参考 `minimal-mono`
2. **替换 primary 系列**：`primary`=品牌色，`primaryDark`=品牌色亮度x0.7，`primaryLight`=品牌色亮度x1.15
3. **选择互补强调色**：冷主色->暖强调色（金色/琥珀/铜色）；暖主色->冷强调色（石板灰/深青/靛蓝）
4. **保持 neutral 和 contrast 不变**
5. **验证可读性**：白字在主色上、正文在背景上、强调色在主色上——三项都必须清晰可读

## 主题选择速查表

| 用户说 | 使用 |
|--------|------|
| "电信"/"电信风格"/"电信PPT"/"中国电信"/"运营PPT"/"标准化运营" | `telecom-red`（默认） |
| "座谈会"/"半年会"/"经营复盘"/"高管发言"/"发言材料"/"总经理座谈会" | `executive-blue`（v7.0） |
| "毕业答辩"/"thesis defense"/"学术汇报" | `academic-red` |
| "公司汇报"/"投资人 pitch"/"董事会"/"consulting" | `business-navy` |
| "AI/ML/技术分享"/"产品发布"(科技)/"dev conference" | `tech-cyan` |
| "培训"/"教学"/"新员工 onboarding"/"团队 workshop" | `warm-amber` |
| "极简"/"设计作品集"/"艺术展"/"高端品牌" | `minimal-mono` |
| 提供品牌色 hex | 使用定制器 + 最近的基础主题 |
| 没有偏好 | 默认 `telecom-red`（电信PPT大师默认） |