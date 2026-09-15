---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '20376649-9ecb-4004-92a9-72d00cba666d'
  PropagateID: '20376649-9ecb-4004-92a9-72d00cba666d'
  ReservedCode1: '11495c05-3819-4aad-82f3-e380176cf46e'
  ReservedCode2: '11495c05-3819-4aad-82f3-e380176cf46e'
---

# 设计系统 (Design System)

> v8.0 新增 · 融合 nexu-io/open-design (81.4K stars) 设计方法论
> 本文件是电信PPT大师的「品牌契约」——所有视觉决策的单一事实来源。
> 类比 open-design 的 DESIGN.md，每次生成 PPT 时自动注入本系统作为视觉约束。

---

## 设计理念

电信PPT大师设计系统遵循三个核心原则：

1. **Token 替代魔法数字**：所有颜色、字号、间距、圆角必须有语义token名，禁止硬编码 hex/px
2. **色阶替代三色调**：每个主题色提供 10 级色阶（50-900），告别 "深/中/浅" 三色困境
3. **材质赋予深度**：表面/卡片/浮层有明确的高程层级，用阴影+背景色组合表达空间关系

---

## 一、颜色系统 (Color Tokens)

### 1.1 色阶命名规则

采用工业标准 10 级色阶（参考 Tailwind CSS + Material Design），每级有明确用途：

| 色阶 | 亮度特征 | 典型用途 |
|------|---------|---------|
| 50 | 最浅, ~95% 白 | 区块底色、大面积底板 |
| 100 | 极浅 | 卡片背景、禁用态 |
| 200 | 浅色 | 分隔线、描边、hover 态 |
| 300 | 中浅 | 次要描边、图标色 |
| 400 | 中色 | 弱化文字、辅助图标 |
| 500 | **基准色 (原色)** | 主按钮、主图标、核心强调 |
| 600 | 中深 | hover 加深、次要标题 |
| 700 | 深色 | 正文标题、深色模式背景 |
| 800 | 极深 | 大标题底板、强调通栏 |
| 900 | 最深 | 文字色、深色底板 |

### 1.2 语义色彩角色

传统方案只区分 "primary/accent/contrast"，open-design 风格扩展到 12 个语义角色：

| 角色 Token | 语义 | 作用域 |
|------------|------|--------|
| `brand` | 品牌主色 | 导航栏、Logo、主按钮、核心数据强调 |
| `brand-vivid` | 品牌亮色 | 封面标题、特殊高亮、品牌飘带起点 |
| `brand-muted` | 品牌淡色 | 卡片底板、区块底色、表格隔行 |
| `accent` | 强调互补色 | 装饰线渐变、特殊标注、金色点缀 |
| `positive` | 正向/达标 | 正增长数据、达标标记、绿色竖条 |
| `negative` | 负向/预警 | 负增长数据、警示框、红色竖条 |
| `surface` | 表面基底 | 页面背景、全局底色 |
| `surface-raised` | 抬高表面 | 卡片底色、面板底色 |
| `surface-header` | 标题栏表面 | 卡片标题栏、模块标签底板 |
| `border` | 描边 | 卡片边框、分隔线、表格线 |
| `text-primary` | 正文色 | 正文、标题、标签 |
| `text-secondary` | 辅助灰色 | 副标题、注释、页脚、数据来源 |

### 1.3 通用色阶（主题无关 · 全部主题共用）

以下色阶与品牌色无关，所有主题保持一致：

```
// Neutral 灰度色阶 — 全局统一
neutral-50:  "FAFAFA"    // 近白底
neutral-100: "F5F5F5"    // 区块灰底
neutral-200: "E8E8E8"    // 分隔线
neutral-300: "D4D4D4"    // 禁用描边
neutral-400: "A3A3A3"    // 占位文字
neutral-500: "888888"    // 辅助文字
neutral-600: "666666"    // 次级正文
neutral-700: "404040"    // 标题文字
neutral-800: "262626"    // 正文文字 (替代纯黑)
neutral-900: "171717"    // 强化标题 (接近纯黑)

// Semantic 语义色 — 全局统一
success:      "16A34A"    // 达标/正面绿色
success-light:"DCFCE7"    // 达标浅底
warning:      "F59E0B"    // 预警/注意黄色
warning-light:"FEF3C7"    // 预警浅底  
danger:       "DC2626"    // 严重警示红
danger-light: "FEE2E2"    // 警示浅底
highlight:    "FFFF00"    // 黄色高亮（保留电信传统）
```

---

## 二、字体系统 (Typography Tokens)

### 2.1 字体配对方案

告别"全篇微软雅黑"的单一字体。引入字体配对增强设计感：

```
// 全局字体栈 (Font Stack)
FONT_SANS:     "Microsoft YaHei", "PingFang SC", "Helvetica Neue", "Arial", sans-serif
FONT_DISPLAY:  "Microsoft YaHei", "PingFang SC", sans-serif  // 大标题/封面
FONT_NUMBER:   "SF Pro Display", "Helvetica Neue", "Arial", sans-serif  // 数据/数字
FONT_SERIF:    "SimSun", "STSong", "Times New Roman", serif  // 引用/公文

// 字体配对使用原则
封面标题 → FONT_DISPLAY (Bold, 32-48pt, letter-spacing: -0.5px)
页标题   → FONT_DISPLAY (Bold, 18-24pt)
正文     → FONT_SANS (Regular, 11-12pt, line-height: 1.6)
数据数字 → FONT_NUMBER (Bold, 13-20pt, tabular-nums)
引用/公文 → FONT_SERIF (Regular, 10-11pt, italic)
```

### 2.2 字号排版档位 (Type Scale)

采用 modular scale (1.125 ratio) 生成完整档位：

| Token | 字号 | 行高 | 字重 | 用途 |
|-------|------|------|------|------|
| `text-xs` | 8pt | 1.4 | Regular | 脚注、数据来源、超小标注 |
| `text-sm` | 9pt | 1.5 | Regular | 图表标签、表格正文、注释 |
| `text-base` | 11pt | 1.6 | Regular | 正文、列表项、卡片描述 |
| `text-lg` | 12pt | 1.5 | Regular | 强调正文、结论句 |
| `text-xl` | 14pt | 1.4 | Bold | 小标题、卡片标题 |
| `text-2xl` | 16pt | 1.3 | Bold | 模块标题、章节标题 |
| `text-3xl` | 20pt | 1.2 | Bold | 页面主标题 |
| `text-4xl` | 24pt | 1.2 | Bold | KPI 数值、大标题 |
| `text-5xl` | 28pt | 1.1 | Bold | 封面副标题 |
| `text-6xl` | 32pt | 1.1 | Bold | 封面主标题 |
| `text-7xl` | 40pt | 1.0 | Bold | 章节过渡页数字 |
| `text-8xl` | 48pt | 1.0 | Bold | 超大封面标题 |

### 2.3 KPI 数字特殊处理

```
// 数据数字要求等宽数字 (tabular-nums)，确保列对齐
fontFace: FONT_NUMBER
fontSize: 根据数值大小自适应:
  - ≥5 位数 (万/亿级): text-4xl (24pt)
  - 3-4 位数: text-3xl (20pt)
  - ≤2 位数: text-2xl (16pt)
  - 百分比: text-xl (14pt) + 单位 text-xs (8pt)
```

---

## 三、间距系统 (Spacing Tokens)

### 3.1 基准间距格 (4px 基准)

所有间距基于 4px 网格，确保像素级对齐：

| Token | 英寸 | px 等价 | 用途 |
|-------|------|---------|------|
| `space-1` | 0.04" | 4px | 超紧密间距（图标-文字） |
| `space-2` | 0.08" | 8px | 内容内边距、紧凑间距 |
| `space-3` | 0.12" | 12px | 卡片内部间距、列表项间距 |
| `space-4` | 0.16" | 16px | 标准间距、段落间距 |
| `space-5` | 0.20" | 20px | 卡片间距、模块间距 |
| `space-6` | 0.25" | 24px | 布局间距、栏目间距 |
| `space-8` | 0.32" | 32px | 大模块间距 |
| `space-10` | 0.40" | 40px | 章节间距、页面边距 |
| `space-12` | 0.50" | 48px | 页面大间距 |
| `space-16` | 0.65" | 64px | 封面元素间距 |

### 3.2 全局边距约束

```
// 页面安全区 (所有主题通用)
PAGE_MARGIN_X: 0.45"       // 左右安全边距
PAGE_MARGIN_TOP: 0.08"     // 内容区最小顶部余量
PAGE_MARGIN_BOTTOM: 0.08"  // 内容区最小底部余量

// 卡片内部内边距
CARD_PADDING_X: 0.14"      // 卡片左右内边距
CARD_PADDING_Y: 0.12"      // 卡片上下内边距
CARD_GAP: 0.25"             // 卡片间间距

// 三栏布局
THREE_COL_GAP: 0.28"        // 三栏间距
THREE_COL_WIDTH: (safeW - 2 * THREE_COL_GAP) / 3

// 2×2 网格
GRID_2x2_GAP_X: 0.30"       // 水平网格间距
GRID_2x2_GAP_Y: 0.22"       // 垂直网格间距
```

---

## 四、表面层级系统 (Elevation / Surface Tokens)

### 4.1 高程定义

| 层级 | Token | 背景色 | 阴影配置 | 用途 |
|------|-------|--------|---------|------|
| L0 | `surface-ground` | `neutral-50` | 无 | 页面背景 |
| L1 | `surface-default` | `white` | 无 | 默认内容区 |
| L2 | `surface-raised` | `white` / 主题卡片色 | `elevation-1` | 卡片、面板 |
| L3 | `surface-header` | 主题标题栏色 | 无 | 卡片内标题栏 |
| L4 | `surface-overlay` | `white` + 60% opacity | `elevation-2` | 浮层、弹窗 |
| L5 | `surface-brand` | 品牌色 500 | 无 | 结论条、导航栏、页脚横幅 |

### 4.2 阴影高程档位

```
// 三级阴影 (从近到远)
elevation-1 (卡片):
  { type:"outer", color:"000000", blur:4, offset:1, angle:270, opacity:0.06 }

elevation-2 (浮层):
  { type:"outer", color:"000000", blur:8, offset:2, angle:270, opacity:0.10 }

elevation-3 (重点突出):
  { type:"outer", color:"000000", blur:12, offset:3, angle:270, opacity:0.14 }

elevation-brand (品牌色阴影 - 电信特有):
  { type:"outer", color:"C00000", blur:6, offset:2, angle:270, opacity:0.12 }
```

---

## 五、圆角系统 (Border Radius Tokens)

```
radius-none:  0         // 直角
radius-sm:    0.04"     // 小圆角（标签、徽章、小按钮）
radius-md:    0.08"     // 标准圆角（卡片、面板、表格单元格）
radius-lg:    0.12"     // 大圆角（封面元素、大卡片）
radius-xl:    0.16"     // 超大圆角（胶囊形状）
radius-full:  9999px    // 圆形（头像、图标容器）
```

---

## 六、各主题色阶完整定义

### 6.1 telecom-red 主题色阶

```
// Brand — 电信深红 (从浅粉到深酒红)
brand-50:  "FFF5F5"    // 极浅粉底（页面底色变化）
brand-100: "FFE4E4"    // 浅粉（卡片底板、标题栏）
brand-200: "F4C2C2"    // 中浅粉（分隔线、hover区域）
brand-300: "E8A0A0"    // 中粉（次要描边、禁用图标）
brand-400: "D06060"    // 偏红（次要文字强调）
brand-500: "C00000"    // 电信深红（主色·导航/标题/核心强调）
brand-600: "A8001A"    // 深红暗色（大标题底板）
brand-700: "8B0012"    // 更深红（hover加深、强调通栏）
brand-800: "6E000A"    // 极深红（深色模式背景）
brand-900: "4D0004"    // 最深红（少用·极端对比）

// Accent — 金色 (从浅金到深金)
accent-50:  "FFFCE0"   // 极浅金
accent-100: "FFF8B0"   // 浅金（装饰底色）
accent-200: "FFF070"   // 暖金（图标、标签）
accent-300: "FFE830"   // 亮金
accent-400: "FFD700"   // 标准金（装饰线渐变接续·基准）
accent-500: "E0C200"   // 偏暗金
accent-600: "C0A800"   // 暗金（强调文字）
accent-700: "A09000"   // 深金
accent-800: "807000"   // 极深金
accent-900: "605000"   // 最深金（少用）
```

### 6.2 executive-blue 主题色阶

```
// Brand — 电信蓝 (从浅蓝白到深蓝)
brand-50:  "F0F7FD"    // 极浅蓝底
brand-100: "E0F0FA"    // 浅蓝（卡片底板）
brand-200: "B8D8F0"    // 中浅蓝（分隔线、hover）
brand-300: "88B8E0"    // 中蓝（次要描边）
brand-400: "5090D0"    // 亮蓝（辅助图标）
brand-500: "0070C0"    // 电信蓝（主色·导航/标题·基准）
brand-600: "0055B8"    // 深蓝（大标题底板）
brand-700: "004090"    // 更深蓝（hover加深）
brand-800: "003070"    // 极深蓝
brand-900: "002050"    // 最深蓝

// Accent — 红色 (保持电信红作为强调色)
accent-50:  "FFF0F0"   // 浅粉
accent-100: "FDE8E8"   // 极浅红
accent-200: "F4C2C2"   // 偏粉
accent-300: "E89090"   // 中红
accent-400: "D04040"   // 亮红
accent-500: "C00000"   // 电信红（强调色·基准）
accent-600: "A8001A"   // 深红
accent-700: "8B0012"   // 更深红
accent-800: "6E000A"   // 极深红
accent-900: "4D0004"   // 最深红

// Positive — 绿色（达标/正面）
positive-50:  "F0FDF4"
positive-100: "DCFCE7"
positive-200: "BBF7D0"
positive-300: "86EFAC"
positive-400: "4ADE80"
positive-500: "16A34A"   // 标准绿·基准
positive-600: "15803D"
positive-700: "166534"
positive-800: "14532D"
positive-900: "052E16"
```

### 6.3-6.7 其他主题快速色阶

**business-navy**:
```
brand-50: "F0F4FA" ... brand-500: "1B365D" (海军蓝基准) ... brand-900: "0A1628"
accent-50: "FFF9F0" ... accent-500: "C9A961" (铜色基准) ... accent-900: "604800"
```

**tech-cyan**:
```
brand-50: "F0F3FF" ... brand-500: "2E3192" (靛蓝基准) ... brand-900: "12145A"
accent-50: "ECFEFF" ... accent-500: "00B4D8" (青色基准) ... accent-900: "004050"
```

**academic-red**:
```
brand-50: "FFF5F5" ... brand-500: "A02123" (学术红基准) ... brand-900: "4A0A0C"
accent-50: "FFFAF0" ... accent-500: "B89860" (古铜金基准) ... accent-900: "584020"
```

**warm-amber**:
```
brand-50: "FFF7ED" ... brand-500: "C5530A" (暖橙基准) ... brand-900: "582000"
accent-50: "FFF5EB" ... accent-500: "F4A261" (奶油橙基准) ... accent-900: "603000"
```

**minimal-mono**:
```
brand-50: "FAFAF7" ... brand-500: "1A1A1A" (极简黑基准) ... brand-900: "000000"
accent-50: "FFFDF0" ... accent-500: "D4AF37" (黄铜基准) ... accent-900: "604800"
```

---

## 七、设计 Token 注入规则

### 7.1 生成时的强制约束

每次通过 JS 引擎生成 PPT 时，必须从本文件提取以下 token 作为全局常量：

```js
// 强制从 design-system.md 提取
const TOKEN = {
  // 颜色 — 从 §六 提取对应主题的完整色阶
  brand:     { 50:"...", 100:"...", ..., 900:"..." },
  accent:    { 50:"...", 100:"...", ..., 900:"..." },
  positive:  { 50:"...", 100:"...", ..., 900:"..." },
  neutral:   { 50:"...", 100:"...", ..., 900:"..." },  // §1.3 通用灰度

  // 语义色 — 从 §1.2 提取
  surface:          TOKEN.neutral[50],   // 页面背景
  surfaceRaised:    "FFFFFF",             // 卡片底面
  surfaceHeader:    TOKEN.brand[100],    // 卡片标题栏底板
  surfaceBrand:     TOKEN.brand[500],    // 品牌色底板
  border:           TOKEN.brand[200],    // 卡片描边
  textPrimary:      TOKEN.neutral[800],  // 正文
  textSecondary:    TOKEN.neutral[500],  // 辅助
  highlight:        "FFFF00",            // 黄底高亮

  // 字体 — 从 §2 提取
  fontSans:         "Microsoft YaHei",
  fontDisplay:      "Microsoft YaHei",
  fontNumber:       "Arial",
  fontSerif:        "SimSun",

  // 字号 — 从 §2.2 提取
  fontSize: {
    xs:8, sm:9, base:11, lg:12, xl:14,
    "2xl":16, "3xl":20, "4xl":24, "5xl":28, "6xl":32, "7xl":40, "8xl":48
  },

  // 间距 — 从 §3 提取
  space: { 1:0.04, 2:0.08, 3:0.12, 4:0.16, 5:0.20, 6:0.25, 8:0.32, 10:0.40, 12:0.50, 16:0.65 },

  // 圆角 — 从 §5 提取
  radius: { sm:0.04, md:0.08, lg:0.12, xl:0.16 },

  // 高程 — 从 §4 提取
  elevation: {
    card:      { type:"outer", blur:4, offset:1, angle:270, opacity:0.06, color:"000000" },
    overlay:   { type:"outer", blur:8, offset:2, angle:270, opacity:0.10, color:"000000" },
    prominent: { type:"outer", blur:12, offset:3, angle:270, opacity:0.14, color:"000000" },
  },
};
```

### 7.2 颜色协调性自动校验规则

生成每页时，AI 必须确保：

1. **文字与背景对比度 ≥ 4.5:1** (正文) / ≥ 3:1 (大标题)
   - brand-500 上的白字 → ✓ (对比度 7.5:1)
   - brand-100 上的 brand-800 文字 → ✓ (对比度 9:1)
   - neutral-400 上的白字 → ✗ (对比度 2.5:1，不通过)

2. **同屏颜色不超过 4 种语义色** (brand / accent / positive / neutral)

3. **色阶跳跃规则**：相邻元素色阶差 ≥ 300 (如 brand-100 底板 + brand-500 文字)

4. **正负双色必须有明确语义区分**：
   - positive-500 (绿) = 达标/正向
   - accent-500 (红) = 未达标/负向
   - brand-500 (蓝/红) = 中性/核心

---

## 八、与 open-design 的对齐说明

| open-design 概念 | 本系统的对应 | 落地形式 |
|-----------------|-------------|---------|
| `DESIGN.md` 品牌契约 | `design-system.md` (本文件) | 所有视觉决策的单一事实来源 |
| 71 套品牌级设计系统 | 7 套主题 × 10 级色阶 = 70 种配色组合 | `themes.md` —— 每套主题展开为完整 token |
| 字体配对方案 | §2 字体系统 | `FONT_SANS` + `FONT_DISPLAY` + `FONT_NUMBER` |
| 设计 token 语义化 | §1.2 语义角色 + §7.1 Token 常量 | 生成 JS 代码中禁止出现裸 hex |
| 表面材质层级 | §4 高程系统 (L0-L5) | 卡片/导航/浮层/结论条各有对应表面 |

---

> **版本**: v8.0 | **日期**: 2026-07-25
> **来源**: nexu-io/open-design (81.4K stars) 设计系统方法论 + Material Design 3 色阶体系 + Tailwind CSS 色阶命名
> **与旧版的关系**: 本文件是 style-guide.md §1 配色体系 + themes.md 的 token 化升级版。旧版三色体系 (primary/primaryDark/primaryLight) 映射为 brand-500/brand-700/brand-300。所有旧 references 文件保留向后兼容，但新代码生成必须优先使用本文件的 token 体系。