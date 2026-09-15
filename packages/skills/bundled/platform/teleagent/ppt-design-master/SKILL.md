---
name: ppt-design-master
description: PPT设计大师，提供中国电信体系PPT制作的完整设计规范与审美准则。当用户需要制作PPT、生成演示文稿、排版幻灯片、选择PPT配色/字体/版式/图表样式、评估PPT美观度、需要设计指导、或检查PPT设计质量时触发。涵盖配色体系、字体选择、图文排布、图表展示、设计原则、质量检查六大维度，基于7套实战模板（电信风格红金/党课红金/改革汇报/品牌红/ICT交付/AI+文旅/教育产品）提炼。同时内置7套完整模板配置文件与示例脚本、14张AI生图指令、61页版式目录、数据可视化指南及PptxGenJS组件函数库。电信风格PPT为默认首选模板（模板7/C8配色），4种页面类型背景图即用。触发词：PPT设计、PPT审美、PPT配色、PPT排版、PPT字体、幻灯片设计、演示文稿美化、配色方案、版式设计、设计规范、PPT视觉、页面布局、PPT美化、PPT模板选择、素材库、电信风格PPT模板、电信风格红金、党课模板、电信PPT模板、红金风格、党建PPT、品牌配色、电信品牌红、产品介绍PPT、ICT自主交付、AI+文旅、文旅数字化、智能体平台、行业大模型、教育产品培训、教育解决方案、教育AI平台、HTML交互版、HTML幻灯片、网页版PPT。
name_cn: PPT设计大师
description_cn: 中国电信体系PPT设计规范与审美准则（配色/字体/排布/图表/原则/质量评估）+模板/插图/版式目录/数据可视化指南/组件库（含电信风格模板7/C8配色+教育产品模板）
create_source: super-agent-skill-creator
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '4e7af2db-706e-4409-a418-1a1bf3840e18'
  PropagateID: '4e7af2db-706e-4409-a418-1a1bf3840e18'
  ReservedCode1: 'f6641ae0-2d39-4dcd-a5ef-61c108e6c89f'
  ReservedCode2: 'f6641ae0-2d39-4dcd-a5ef-61c108e6c89f'
---

# PPT设计大师

制作中国电信体系PPT时，遵循本设计规范确保视觉质量。所有规范基于7套实战模板提炼，可直接落地到 PptxGenJS 代码。本技能整合了完整的设计规范、模板配置、插图素材、版式目录、数据可视化指南和组件函数库。

> **首选模板**：电信风格PPT默认调用**电信风格PPT模板（模板7/C8配色）**，该模板提取自潘军党课PPT原版，背景图含中国电信Logo+天翼AI Logo(透明)+暖色绸带装饰，4种页面类型背景图即用，所有文字可编辑。详见下方"模板库"章节。

## 素材总览

| 素材类别 | 数量 | 位置 |
|---------|------|------|
| 设计规范参考 | 5份 | `references/color-palette.md` `references/layout-snippets.md` `references/template-comparison.md` `references/layout_catalog.md` `references/data_viz_guide.md` |
| 模板配置文件 | 7套 | `references/template-config-1~7.json` |
| 示例生成脚本 | 3套 | `references/template-1-example.js` `references/template-4-example.js` `references/template-5-example.js` |
| 组件函数库 | 1套 | `scripts/gen_lto_pptx_full.js` |
| AI插图指令 | 14张 | `references/asset-manifest.md` |
| 品牌Logo | 2张 | `assets/china_telecom_logo.png` `assets/tianyi_ai_logo.png` |
| **电信风格模板背景图** | **4张** | **`assets/panjun-template/bg_cover.png` `bg_content.png` `bg_transition.png` `bg_end.png`** |
| 配色方案 | 7套(C2-C8) | `references/color-palette.md` |
| **HTML交互版PPT模板** | **1套** | **`templates/ppt-html-template.html`（浏览器直接打开，支持翻页/缩略图/全屏/主题切换/PDF导出/H5移动端）** |

## 总体设计原则

1. **一主多辅**：每页以1个主色为核心，辅色不超过3个，拒绝彩虹色拼盘
2. **层级分明**：标题大粗色、正文小灰体、强调用主色加粗，三级层次清晰可辨
3. **留白呼吸**：内容区边距≥0.35英寸，卡片间距≥0.15英寸，避免信息堆叠
4. **统一克制**：全PPT使用同一字体族、同一圆角值、同一边框色，保持视觉系统一致
5. **克制装饰**：装饰条/线条只用于标题区和页脚，正文区不加多余装饰
6. **16:9标准**：页面尺寸统一10×5.625英寸，4:3仅用于党课等特殊场景
7. **图文比例**：图片与文字比例建议4:6~6:4，避免纯文字页或纯图片页

## 配色体系

### 主色选择规则

| 场景类型 | 推荐主色 | 色值 | 适用模板 | 配色方案 |
|---------|---------|------|---------|---------|
| **电信风格PPT/党课/党建/内部汇报** | **中国红** | **#C00000** | **模板7(首选)** | **C8 电信风格红金** |
| 党建/党课/政治类 | 中国红 | #C00000 | 模板1 | C2 党政红金 |
| 改革汇报/经营分析 | 深蓝 | #004488 | 模板2 | C3 电信品牌蓝 |
| 产品介绍/技术分享 | 品牌红 | #C8102E | 模板3 | C4 电信品牌红 |
| ICT项目/操作指引 | 品牌红+红棕 | #C8102E+#A82820 | 模板4 | C5 品牌红+红橙黄渐变 |
| AI+行业/科技文旅 | 品牌红+深灰栏 | #C8102E+#2C2C2C | 模板5 | C6 品牌红+马卡龙色系 |
| 教育产品/AI实训 | 深红+深蓝底 | #C00000+#1F2A44 | 模板6 | C7 教育产品深红+深蓝信息底 |

### 辅色搭配规则

- **暖色渐变组**：橙#F29400 → 黄#FFCC00，用于装饰条/进度条/强调标签
- **品牌蓝组**：#005AAA（辅色）/ #DCE9F5（表头淡蓝底），用于数据可视化辅助
- **马卡龙色系**：蓝#0066CC / 绿#4CAF50 / 紫#9C27B0 / 黄#FFC107 / 青#009688，用于多模块区分（每模块一色，共5色即可）
- **金色调**：#D4AF37，仅限党课红金风格使用

### 文字色阶（全模板统一）

| 层级 | 色值 | 用途 |
|------|------|------|
| 标题色 | 主色（红/蓝） | 页面标题、卡片标题加粗 |
| 正文色 | #333333 | 主体内容文字 |
| 次要色 | #666666 | 副标题、说明文字 |
| 辅助色 | #999999 | 页码、脚注、极次要信息 |
| 强调色 | 主色或橙#F29400 | 关键数据、重点标注 |

### 图表配色序列

按数据系列顺序使用，不超过6色：
```
主色 → 橙#F29400 → 黄#FFCC00 → 品牌蓝#005AAA → 绿#4CAF50 → 深红#A82820
```

完整色值速查表详见 → `references/color-palette.md`

## 字体选择

### 字体族

统一使用 **Microsoft YaHei（微软雅黑）** 无衬线黑体，全PPT不混用其他字体。

### 字号层级

| 层级 | 字号 | 字重 | 颜色 |
|------|------|------|------|
| 封面主标题 | 28-40pt | Bold | 主色 |
| 页面标题 | 22-28pt | Bold | 主色 |
| 副标题 | 13-18pt | Regular | #666666 |
| 卡片标题 | 11-14pt | Bold | 主色或#333333 |
| 正文 | 8-10pt | Regular | #333333 |
| 大号数据 | 36-48pt | Bold | 橙#F29400或主色 |
| 页码 | 9-10pt | Regular | #999999 |

### 字重规则

- **加粗场景**：标题、卡片标题、强调数据、表头
- **常规场景**：正文、说明文字、页码
- 禁止使用斜体，中文PPT不适用

## 图文排布

### 页面结构标准

```
┌─────────────────────────────────────┐
│  标题区 (y: 0.12-0.50)              │
│  ─── 装饰条/渐变条 (y: 0.50-0.55)   │
├─────────────────────────────────────┤
│                                     │
│  内容区 (y: 0.65-5.00)              │
│  (边距: 左右0.35-0.70 / 上下0.35-0.50)│
│                                     │
├─────────────────────────────────────┤
│  红色细线 (y: 5.30)  页码 (右下角)   │
└─────────────────────────────────────┘
```

### 常见布局模板

| 布局类型 | 适用场景 | 网格规格 |
|---------|---------|---------|
| 2×2网格 | 四项对比、优势展示 | 每格约4.5×2.0英寸 |
| 2×4网格 | 八项并列、功能清单 | 每格约4.5×1.0英寸 |
| 3列卡片 | 三段式论述、方案对比 | 每列约3.0英寸宽 |
| 左右对比 | 前后对比、优劣分析 | 左右各4.5英寸 |
| 时间线 | 发展历程、里程碑 | 横轴+圆点节点 |
| 流程图 | 业务流程、操作步骤 | 圆角矩形+右箭头 |
| 全幅表格 | 数据统计、清单展示 | 表头彩色+交替行 |

### 61页版式目录

完整的61页版式分类与匹配规则详见 → `references/layout_catalog.md`

快速匹配规则：

| 内容类型 | 推荐版式 | 参考页码 |
|---------|---------|---------|
| 流程/步骤 | 流程图/递进式 | 4,6,8,13,20,22-24,31-34,39-40,44,51 |
| 左右对比 | 左右分栏 | 12,16,19,42,45-49,53-55,58,61 |
| 并列模块 | 网格/模块化 | 7,27,30,37-38,43,56,59 |
| 中心概念 | 辐射/锚点 | 10-11,17-18,25,28,36,50 |
| 目录导航 | 目录页 | 21,41 |
| 要点列表 | 单栏列表 | 9,14,26,29,35 |
| 交叉参考 | 矩阵/总览 | 4,5,39 |
| 章节过渡 | 全屏文字 | 52 |
| 封面 | 标题页 | 1 |
| 流程导航 | 横向流程导航 | 2 |

### 卡片设计规范

- 形状：圆角矩形（rectRadius: 0.04-0.06英寸）
- 背景：白色 #FFFFFF
- 边框：浅灰 #E5E5E5 或 #CCCCCC，线宽1pt
- 内边距：文字距卡片边≥0.15英寸
- 标题居顶，内容居中或居左

### 装饰元素规则

- **标题装饰条**：红色短线（宽0.35英寸，高0.03英寸）或三色渐变条（红-橙-黄各1/3）
- **半闭合边框**：四角留缺口（gap=0.3英寸），颜色#A82820，用于内容区外框
- **红色虚线卡片**：dashed线型，用于模拟截图/表单区域
- **底部线条**：红色细线（宽9.3英寸，高0.015英寸），位于y=5.30
- **页脚页码**：右下角，灰色#999999，9-10pt

## 图表展示

### 数据可视化选型

完整图表选型指南与PptxGenJS实现代码详见 → `references/data_viz_guide.md`

| 数据类型 | 推荐图表 | PptxGenJS方法 |
|---------|---------|-------------|
| 流程/步骤 | 流程图 | `addShape` + `addText` 手动 |
| 对比/排名 | 柱状图 | `addChart(BAR, ...)` 或手动卡片条 |
| 趋势/变化 | 折线图 | `addChart(LINE, ...)` |
| 占比/构成 | 饼图/环形图 | `addChart(PIE, ...)` 或 `addChart(DOUGHNUT, ...)` |
| 多维度评估 | 雷达图 | `addShape` + `addText` 手动 |
| 相关性 | 散点图(手动) | `addShape` 手动 |
| 体量/层级 | 面积图 | `addChart(AREA, ...)` |

### 表格规范

- 表头：主色填充 + 白字加粗
- 数据行：白底 / 浅色交替（如#FFF5F5粉白交替）
- 边框：灰色细线 #CCCCCC
- 对齐：文字左对齐，数字右对齐

### 流程图规范

- 节点：圆角矩形，主色/品牌蓝交替填充
- 箭头：右箭头连接，颜色#666666或主色
- 布局：横向排列为主，纵向分支为辅

### 时间线规范

- 横轴：灰色基线
- 节点：圆点，已完成=主色实心，待完成=灰色空心
- 标签：节点上方/下方交替排列，避免重叠

### 特殊图表

- **雷达图**：多维度能力评估，主色填充半透明
- **S曲线**：增长趋势展示，主色曲线+渐变填充
- **阶梯图**：分阶段对比，每阶不同色块
- **泳道图**：多角色协作流程，每泳道一色

## 模板库（7套完整模板）

制作PPT前，先读取对应配置文件获取配色、字体、布局参数。

> **优先级说明**：当用户提及"电信风格PPT""党课PPT""党建PPT""汇报PPT"等关键词时，**优先使用模板7（电信风格PPT模板）**，该模板含4张即用背景图（封面/内容页/章节过渡/结尾页），背景已内嵌中国电信Logo+天翼AI Logo(透明)+暖色绸带装饰，所有文字为可编辑文本框叠加。

| 模板 | 配置文件 | 场景 | 配色 | 页数 | 示例脚本 |
|------|---------|------|------|------|---------|
| **电信风格PPT模板（首选）** | `references/template-config-7.json` | **电信风格PPT/党课/党建汇报/政治类/电信内部汇报/改革推进汇报** | **中国红C00000+金色** | **可变** | **背景图即用** |
| 党课红金风格 | `references/template-config-1.json` | 支部党课、党建汇报 | 中国红+金色 | 20 | `references/template-1-example.js` |
| 电信改革汇报风格 | `references/template-config-2.json` | 改革汇报、经营分析 | 深蓝品牌色+白底 | 24 | - |
| 电信品牌红风格 | `references/template-config-3.json` | 产品介绍、技术分享、燎原课件 | 电信品牌红+暖色渐变 | 53 | - |
| 复杂ICT项目自主交付 | `references/template-config-4.json` | ICT项目自主交付、售前方案、CRM下单 | 电信品牌红+红橙黄渐变+品牌蓝 | 7 | `references/template-4-example.js` |
| AI+文旅商业模式 | `references/template-config-5.json` | AI+行业融合、文旅数字化、智能体平台 | 电信品牌红+马卡龙色系+深灰标题栏 | 9 | `references/template-5-example.js` |
| 教育产品解决方案风格 | `references/template-config-6.json` | 教育产品培训、教育解决方案宣贯、高校/教育局产品推介、教育AI平台、AI实训方案 | 电信深红+深蓝信息底+金色强调 | 29 | - |

### 电信风格PPT模板（模板7/C8配色）详细规范

**来源**：提取自中国电信内部党课PPT原版，严格复刻原版视觉设计。

**4张背景图（即用，无需额外处理Logo白底问题）**：

| 背景图 | 文件路径 | 用途 | 内含元素 |
|--------|---------|------|----------|
| 封面背景 | `assets/panjun-template/bg_cover.png` | 封面页 | 中国电信Logo+天翼AI Logo(透明)+底部暖色绸带+白色遮盖矩形 |
| 内容页背景 | `assets/panjun-template/bg_content.png` | 目录页/内容页 | 白底+红橙黄装饰分隔线+天翼AI Logo(透明)+底部红线 |
| 章节过渡背景 | `assets/panjun-template/bg_transition.png` | 章节过渡页 | 与封面同（含Logo+绸带装饰） |
| 结尾页背景 | `assets/panjun-template/bg_end.png` | 封底/结尾页 | 白底+中国电信Logo+天翼AI Logo+装饰图+红色谢谢横条 |

**配色方案（C8 电信风格红金）**：

| 色名 | 色值 | 用途 |
|------|------|------|
| 主色 | #C00000 | 标题栏/章节序号/卡片标题/强调 |
| 底部线 | #B91B21 | 底部装饰红线 |
| 浅橙卡片底 | #F8CEA4 | 引用/内容卡片背景 |
| 卡片边框 | #DD1715 | 白底卡片渐变边框 |
| 浅金文字 | #FFF3D7 | 红色卡片上的标题/正文文字 |
| 深棕 | #543100 | 目录页标题/标签文字 |
| 正文黑 | #000000 | 正文内容 |
| 次要灰 | #666666 | 副标题/说明文字 |

**字号字体规范**：

| 层级 | 字号 | 字体 | 字重 | 颜色 |
|------|------|------|------|------|
| 封面主标题 | 54pt | 微软雅黑 | Bold | C00000 |
| 封面副标题 | 24pt | 方正小标宋简体+楷体 | Regular | 黑色 |
| 页面标题 | 22pt | 微软雅黑 | Bold | 白色(红底) |
| 章节序号 | 28pt | 微软雅黑 | Bold | 白色(红椭圆底) |
| 章节大标题 | 48pt | 微软雅黑 | Bold | C00000 |
| 章节副标题 | 18pt | 微软雅黑 | Regular | 666666 |
| 卡片标题 | 20pt | 微软雅黑 | Bold | C00000 |
| 正文 | 14pt | 微软雅黑 | Regular | 000000 |
| 小字 | 11pt | 微软雅黑 | Regular | 000000 |
| 结尾页标题 | 44pt | 微软雅黑 | Bold | 白色(红底) |
| 结尾页总结语 | 24pt | 微软雅黑 | Regular | C00000 |

**页面尺寸**：13.333×7.5英寸（16:9宽屏）

**使用方式**：
```javascript
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.defineLayout({ name: "WIDE", width: 13.333, height: 7.5 });
pres.layout = "WIDE";
// 背景：s.background = { path: "bg_cover.png" }; // 4张图按页面类型选择
// 文字：s.addText(...) 叠加可编辑文本框
```

### 模板设计与辅助函数对照

| 函数名 | 模板1 | 模板3 | 模板4 | 模板5 | 模板6 | 功能 |
|--------|-------|-------|-------|-------|-------|------|
| addBrand | - | 有 | - | - | - | 添加品牌标识(右上角中国电信+5G logo) |
| addTitleBar | - | 有 | - | - | - | 添加标题栏+红橙黄渐变装饰条 |
| addBottomLine | - | 有 | - | - | - | 添加底部红线+页码 |
| addCard | - | 有 | - | - | - | 添加内容卡片 |
| addFlowNode | - | 有 | - | - | - | 添加流程节点 |
| addArrowRight | - | 有 | - | - | - | 添加右箭头 |
| makeTable | - | 有 | - | - | - | 创建交替行表格 |
| addBackLink | - | 有 | - | - | - | 添加返回链接 |
| addHalfBorder | - | - | 有 | - | - | 半闭合边框 |
| addRedDashCard | - | - | 有 | - | - | 红色虚线卡片 |
| addSwimlane | - | - | 有 | - | - | 泳道流程图 |
| addTimeline | - | - | 有 | - | - | 时间线 |
| addPageNum | - | - | - | 有 | - | 页码 |
| addBrokenBorder | - | - | - | 有 | - | 半闭合边框 |
| addRedBarTitle | - | - | - | 有 | - | 红色装饰条标题 |
| addTitle | - | - | - | - | 有 | 标题栏 |
| addWatermark | - | - | - | - | 有 | 右下角水印 |
| addNumberedCard | - | - | - | - | 有 | 编号卡片 |
| addConclusionBar | - | - | - | - | 有 | 深蓝结论栏 |
| addFullScreenshot | - | - | - | - | 有 | 全屏截图+标题 |
| addFAQCard | - | - | - | - | 有 | FAQ问答卡片 |
| addThreeColumnCompare | - | - | - | - | 有 | 三列对比卡片 |
| addMatrixGrid | - | - | - | - | 有 | 多维矩阵网格 |
| addContentsPage | - | - | - | - | 有 | 目录页 |
| addDividerLine | - | - | - | - | 有 | 水平分隔线 |

模板差异详细对照表详见 → `references/template-comparison.md`

### 组件函数库

Telecom PPT 61页模板的完整PptxGenJS组件函数库，可直接复制使用 → `scripts/gen_lto_pptx_full.js`

使用方式：
```javascript
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
// 从 gen_lto_pptx_full.js 复制所需组件函数
// 按材料内容编写页面函数
pres.writeFile({ fileName: "output.pptx" });
```

## 插图素材（14张AI生图指令）

所有插图均使用AI生图，提供经过验证的prompt（已规避政治符号触发安全策略）。

### 党课红金系列 - 章节配图（4:3，5张）

| 名称 | 用途 |
|------|------|
| 封面-红金丝绸主视觉 | 封面页全幅背景 |
| 理论-金光书卷 | 理论学习章节 |
| 初心-金色红心 | 初心使命章节 |
| 治党-金色盾牌 | 从严治党章节 |
| 担当-红绸日出 | 党员担当章节 |

### 党课红金系列 - 装饰矢量素材（1:1，8张）

红色飘带 / 金色五角星 / 华表剪影 / 祥云纹饰 / 长城剪影 / 书卷卷轴 / 麦穗装饰 / 山峰日出

### 电信品牌

| 名称 | 用途 | 来源 |
|------|------|------|
| 中国电信+5G logo | 右上角品牌标识 | `assets/china_telecom_logo.png` |

全部插图的AI生图prompt、尺寸参数和用途说明详见 → `references/asset-manifest.md`

**安全限制**：prompt中不得出现"党旗""党徽""党标"等政治符号词汇，否则生图服务返回400 (OutputImageSensitiveContentDetected)。所有prompt已在asset-manifest.md中预先规避。

## 配色方案速查（C2-C8）

| 方案 | 名称 | 主色 | 特色辅色 | 适用场景 |
|------|------|------|---------|---------|
| **C8** | **电信风格红金（首选）** | **#C00000** | **#FFF3D7浅金/#F8CEA4浅橙/#543100深棕** | **电信风格PPT/党课/党建/电信内部汇报/改革推进** |
| C2 | 党政红金 | #C00000 | #D4AF37金色 | 党课/政治类 |
| C3 | 电信品牌蓝 | #004488 | #0066CC/#4CAF50/#FF6B35 | 改革汇报/经营分析 |
| C4 | 电信品牌红 | #C8102E | #F29400/#FFCC00/#005AAA | 产品介绍/技术分享 |
| C5 | 品牌红+红橙黄渐变 | #C8102E | #A82820/#005AAA/#DCE9F5 | ICT项目/操作指引 |
| C6 | 品牌红+马卡龙色系 | #C8102E | #2C2C2C/5色马卡龙 | AI+行业/科技文旅 |
| C7 | 教育产品深红+深蓝信息底 | #C00000 | #1F2A44深蓝/#F2C14E金色/5色标签 | 教育产品/AI实训 |

完整色值表详见 → `references/color-palette.md` 和 `references/asset-manifest.md` 底部"配色方案速查"

## 调用流程

1. **选模板**：用户提及电信风格PPT时**优先选模板7（电信风格PPT模板）**，读取 `references/template-config-7.json`，按场景选其余模板；**若用户要"HTML交互版/网页版PPT/H5演示"，直接跳到下方"HTML交互版PPT"章节，复制 `templates/ppt-html-template.html` 生成**
2. **定配色**：从 `references/color-palette.md` 选取配色方案
3. **选版式**：从 `references/layout_catalog.md` 匹配每页布局类型
4. **生插图**：从 `references/asset-manifest.md` 查找对应素材prompt，调用AI生图
5. **定图表**：从 `references/data_viz_guide.md` 确定图表类型
6. **组装PPT**：模板7使用背景图+可编辑文本框；其余模板从 `scripts/gen_lto_pptx_full.js` 或示例脚本复制组件函数，用PptxGenJS生成
7. **质检查**：按下方质量检查清单逐项验证

## 常见陷阱

### Unicode 转义错字（高频问题）

在 PptxGenJS 脚本中使用 `\uXXXX` Unicode 转义编写中文时，极易写错码点导致生成的 PPT 出现乱码或错别字。常见错误示例：

| 错误转义 | 实际字符 | 正确转义 | 应为 |
|---------|---------|---------|------|
| `\u6720` | 朠 | `\u672c` | 本 |
| `\u7400` | 珑 | `\u8fdb` | 进 |
| `\u5d38` | 崸 | `\u6263` | 扣 |
| `\u8d0f` | 贏 | `\u8d4f` | 赏 |
| `\u8d56` | 赖 | `\u5212` | 划 |
| `\u56fe\u7247` | 图片 | `\u56fe\u8868` | 图表 |

**根因**：手写 `\uXXXX` 时相邻码点仅差 1~2 位十六进制值（如 `6720` vs `672c`），肉眼难以区分。

**预防与验证方法**：

1. **生成后必须用 python-pptx 提取全量文字校验**，脚本模板：
```python
# -*- coding: utf-8 -*-
from pptx import Presentation
p = Presentation('output.pptx')
for i, slide in enumerate(p.slides, 1):
    for shape in slide.shapes:
        if shape.has_text_frame:
            t = shape.text_frame.text.strip()
            if t:
                print(f'P{i}: {t[:80]}')
```
2. **可疑字扫描**：提取后搜索常见乱码字（朠/珑/崸/贏/崸/珑等），发现即定位修复。
3. **优先用中文字面量**：如果脚本文件以 UTF-8 保存，直接写中文字符（如 `"本周待办"`）而非 `\uXXXX` 转义，可从根本上避免码点错误。仅在文件编码不可控时才用转义。
4. **PowerShell 中运行 python -c 时避免引号嵌套**：多行 Python 校验脚本写入 `.py` 文件再执行，不要内联在 `python -c "..."` 中，否则 PowerShell 引号转义会报错。

### 视觉模型页码判断偏差

使用 image_understanding 检查 PPT 预览图时，视觉模型可能将页码判断错位（如将第7页说成第8页）。**应以 python-pptx 文字提取结果为准**确认页面顺序与内容，视觉模型仅用于辅助检查布局/配色/重叠等视觉问题。

## 设计质量检查清单

生成PPT后逐项检查：

- [ ] 主色统一，全PPT不超1个主色+3个辅色
- [ ] 字体统一微软雅黑，不混用
- [ ] 字号层级清晰（标题>副标题>正文>页码）
- [ ] 每页留白充足，内容不贴边
- [ ] 卡片圆角统一，边框色一致
- [ ] 标题下有装饰线，底部有红线+页码
- [ ] 图表配色按序列使用，不超6色
- [ ] 表格表头彩色填充，数据行交替底色
- [ ] 流程图节点对齐，箭头方向一致
- [ ] 无文字重叠、无元素越界
- [ ] 封面/封底完整，结尾有联系方式或结束语
- [ ] 图片清晰，无拉伸变形
- [ ] **中文文字校验**：用 python-pptx 提取全量文字，确认无乱码/错别字（参见"常见陷阱"章节）

## 详细参考文件索引

| 文件 | 内容 |
|------|------|
| `references/color-palette.md` | 完整色值速查表（C2-C7全部色值） |
| `references/layout-snippets.md` | 版式PptxGenJS代码片段与参数 |
| `references/template-comparison.md` | 6套模板差异对比表 |
| `references/layout_catalog.md` | 61页版式分类目录与匹配规则 |
| `references/data_viz_guide.md` | 数据可视化选型指南与图表代码 |
| `references/asset-manifest.md` | 14张插图AI生图指令+配色方案速查 |
| `references/template-config-7.json` | 电信风格PPT模板配置（首选，含4张背景图） |
| `references/template-config-1.json` | 党课红金风格模板配置（20页） |
| `references/template-config-2.json` | 电信改革汇报风格模板配置（24页） |
| `references/template-config-3.json` | 电信品牌红风格模板配置（53页） |
| `references/template-config-4.json` | ICT项目自主交付模板配置（7页） |
| `references/template-config-5.json` | AI+文旅商业模式模板配置（9页） |
| `references/template-config-6.json` | 教育产品解决方案风格模板配置（29页） |
| `references/template-1-example.js` | 党课红金风格完整生成脚本（20页） |
| `references/template-4-example.js` | ICT项目自主交付完整生成脚本（7页） |
| `references/template-5-example.js` | AI+文旅商业模式完整生成脚本（9页） |
| `scripts/gen_lto_pptx_full.js` | 61页模板PptxGenJS组件函数库 |
| `assets/china_telecom_logo.png` | 中国电信品牌Logo |
| `assets/tianyi_ai_logo.png` | 天翼AI Logo（透明PNG） |
| `assets/panjun-template/bg_cover.png` | 电信风格模板-封面背景图（含Logo+装饰条） |
| `assets/panjun-template/bg_content.png` | 电信风格模板-内容页背景图（白底+装饰线+Logo+底部红线） |
| `assets/panjun-template/bg_transition.png` | 电信风格模板-章节过渡页背景图（与封面同） |
| `assets/panjun-template/bg_end.png` | 电信风格模板-结尾页背景图（含Logo+装饰图+红色谢谢横条） |
| `templates/ppt-html-template.html` | HTML交互版PPT模板（7套配色主题切换+翻页/缩略图/全屏/触屏/打印导出，内置7页示例） |

## HTML交互版PPT（网页演示）

当用户需要"HTML交互版""网页版PPT""HTML幻灯片""H5演示"时，使用 `templates/ppt-html-template.html` 单文件模板生成可交互网页演示。适用场景：无 Office 环境播放、手机/微信分享、需要翻页/缩略图/主题切换等交互、浏览器直接打开零依赖。

### 何时选 HTML 交互版而非 PptxGenJS

| 需求 | 选择 |
|------|------|
| 需要可编辑 .pptx 文件、印刷级尺寸控制 | PptxGenJS（本技能主流程） |
| 网页播放/手机浏览/微信分享/免安装 | **HTML 交互版（本模板）** |
| 需要翻页动画、缩略图导航、一键切配色 | **HTML 交互版（本模板）** |

### 使用流程

1. **复制模板**：以 `templates/ppt-html-template.html` 为基础另存为交付文件
2. **替换内容**：把 `<main id="deck">` 内 7 页示例 `<section class="slide">` 替换为实际内容；每个 `<section>` 带 `data-title`（缩略图标题）；内容页复用 `.x-*` 组件类（`x-titlebar/x-grad/x-body/x-card/x-soft/x-chip/x-kpi/x-flow/x-table/x-page-num/x-bottomline`）
3. **定主题**：`<body data-theme="c8">` 与各 `<section data-theme="c8">` 一行切换，内置 C2~C8 全部 7 套配色（CSS 变量与 `references/color-palette.md` 对齐）；播放时可由控制条下拉切换并记忆到 localStorage
4. **新页面**：复制一页示例 `<section>` 修改即可，脚本自动识别页数（控制条/缩略图/翻页均无需改代码）
5. **质检**：本地起服务验证（见下），按设计质量检查清单核对

### 交互功能（模板已内置，无需开发）

- 翻页：←/→/PageUp/PageDown/Home/End/空格、按钮、触屏左右滑动、手机点按热区（左1/4上页、右3/4下页）
- 缩略图目录（O 键/▦ 按钮，克隆渲染真实缩放预览）；全屏（F）；打印导出 PDF（Ctrl+P，@page 1280×720 逐页分页）
- 深链：`#p3` 直达第 3 页；控制条 3.5s 无操作自动隐藏；手机竖屏自动提示横屏（可跳过并记忆）

### 常见陷阱

- **file:// 协议被拦截**：Playwright 等浏览器工具禁止打开 file:// 页面。本地验证须起临时 HTTP 服务：`python -m http.server 8931 --bind 127.0.0.1 --directory <模板目录>`，再访问 `http://127.0.0.1:8931/文件名.html`
- **控制条截图"消失"是预期行为**：控制条 3.5 秒无操作自动隐藏（opacity 0），截图前移动鼠标或直接用 evaluate 断言 `#pgCur/#pgTotal` 文本，勿误判为 Bug
- **并行会话共享浏览器**：Playwright 浏览器可能被其他并行会话抢占导航。验证前先 `evaluate` 检查 `location.href` 是否是自己的页面；不是则用新标签页（tabs new）打开自己的 URL 再继续，勿在他人页面上断言
- **视觉快照锚定页码**：截图断言前先确认当前 hash（`location.hash`）对应的页码，避免把别的页面截图误当目标页分析
- **长文件分步构建**：单次生成 600+ 行 HTML 容易出现文本污染（注释残渣、错乱 token 如 `body[#;data-theme`）。改为三步构建：先 write 完整 CSS，再 edit 插入 body 骨架，最后 edit 插入脚本；每次写入后 grep 校验残留（如搜 `else key`、`</张>` 等非法片段）
- **配色必须走 CSS 变量**：新增页面禁止写死颜色，统一 `var(--primary)` 等变量，保证主题一键切换全页生效；色值以 `references/color-palette.md` 为准