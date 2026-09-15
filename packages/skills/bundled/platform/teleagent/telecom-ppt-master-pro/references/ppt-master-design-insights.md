---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '451a9016-6fb6-4ead-9fb6-5f11bc291af5'
  PropagateID: '451a9016-6fb6-4ead-9fb6-5f11bc291af5'
  ReservedCode1: '884aa96e-d684-443c-ada2-3e1e20dd8048'
  ReservedCode2: '884aa96e-d684-443c-ada2-3e1e20dd8048'
---

# ppt-master 设计方法论 — 对电信PPT的启示

> 提取自 ppt-master (hugohe3, v3.1.0, MIT) 核心设计理念。
> 不做技术栈迁移，只提取可在pptxgenjs框架内应用的设计思想。

---

## 一、双轨设计制（design_spec + spec_lock）

### 问题

长PPT（15页以上）容易出现色彩/字体/间距/卡片风格逐步漂移，因为每页都是独立判断，没有"全局状态"概念。

### ppt-master 方案

```
design_spec.md  ← 人类可读的"Why"（意图、观众、叙事模式）
spec_lock.md    ← 机器可执行的"How"（精确HEX值、字体栈、图表映射）
```

- **design_spec** 回答：这个PPT想达成什么？给谁看？用金字塔结构还是叙事线？
- **spec_lock** 锁定：主色=#C00000、卡片描边=#E8B4B4、卡片填充=#FFF0F0、页脚字号=8pt...

### 可落地改造（v7.2+）

在JS引擎的 Step 3（Slide Contract规划）阶段，生成一份 **全局锁 JSON**：

```json
{
  "theme": "telecom-red",
  "lock": {
    "primary": "#C00000",
    "card_fill": "#FFF0F0",
    "card_stroke": "#E8B4B4",
    "title_bar": "#FFE4E4",
    "title_font_size": 16,
    "body_font_size": 12,
    "min_font_size": 7,
    "card_border_radius": 6,
    "nav_height": 0.52,
    "safe_top": 0.55,
    "safe_bottom": 7.05,
    "column_layout": "three_cards",
    "number_style": "red_bold_yellow_bg",
    "page_number_format": "{current}/{total}"
  },
  "drift_checks": [
    "每页卡片圆角一致",
    "每页标题字号一致",
    "数字目标格式统一（红粗+黄底）",
    "导航栏高度不变",
    "安全区域边界不变"
  ]
}
```

**每页生成前**，代码先读取锁JSON，确保所有参数一致。这是最简单的防漂移机制，不需要SVG管道的复杂度。

---

## 二、逐页上下文投影

### 问题

生成第8页时，AI已经"忘记"第1页用的什么配色、第3页用的什么布局、整体节奏如何。

### ppt-master 方案

每页生成前重建只读 page-context 视图：

```
=== Page 5 Context ===
[全局锁] telecom-red主题，三栏卡片布局
[前三页] P2:KPI指标卡 → P3:数据表格 → P4:2×2矩阵
[节奏] 开局密集数据 → 中段展开分析 → 当前页承上启下
[图表] 本页用堆叠柱状图 ← 与P3不重复
[图片] 本页无配图 ← 相邻页有图，平衡密度
[前一页视觉] 右重左轻 → 本页居中平衡
```

### 可落地改造

在JS引擎的每页代码生成前，注入一段上下文注释，确保页面间视觉节奏一致。

---

## 三、72种图像布局模式

### 问题

图文混排时总是默认"左图右文"或"上图下文"三板斧。

### ppt-master 方案

双层体系：
- **Primary Structures**（#1-#81）：容器/画布/多图组合
- **Modifier Layers**（#20-#72）：非矩形裁剪/叠加/纹理/特效

鼓励组合使用，反对"AI默认布局"倾向。

### 可落地改造

将72种布局翻译为JS参考手册，整合进T1-T34模板系统。电信场景最常用的：

| 编号 | 名称 | 电信场景 |
|------|------|---------|
| #1 | 全幅背景+浮动标题 | 封面页 |
| #2 | 左1/3图+右文 | 策略说明页 |
| #10 | 居中图+径向标注 | 业务流程页 |
| #15 | 多图蒙太奇+跨图大字标题 | 成果展示 |
| #38 | 背景图+标注卡片+贝塞尔引线 | 数据标注页 |
| #40 | 背景图+浮空KPI卡片 | 仪表盘页 |
| #47 | 小倍数并排比较 | 分市场对比 |
| #48 | A/B对比（前后/你我/今昔） | 对标分析 |
| #63 | 贴纸裁剪 | 装饰元素 |

---

## 四、三角色协作模式

### 问题

单一7步流程中，需求分析、视觉设计、质量检查交叉进行，上下文混乱。

### ppt-master 方案

```
Strategist（策略师）  → 12项设计决策→用户确认
Image_Generator       → AI生图/Web搜图
Executor（执行师）    → 逐页手写SVG
```

每个角色有独立的reference文件和明确的输入/输出边界。

### 可落地改造

将现有7步流程分化为：

```
需求分析师（Step 1-2） → 确认主题、预设、内容模式
视觉设计师（Step 3-4） → 生成Slide Contract → 代码生成
QA工程师（Step 5-6）  → QA检查 → 微调执行
```

每个阶段输出明确的产物，下一阶段只读上一阶段的输出，减少上下文交叉污染。

---

## 五、约束合同哲学（SVG→pptxgenjs 平移）

### ppt-master 核心思想

不是"能生成什么"，而是**明确禁止生成什么**。642行的 shared-standards-core.md 定义了：

- 白名单内联样式属性
- XML元素黑名单（mask/style/class/foreignObject/textPath）
- 4级保真度标签（Native-stable / Normalized / Approximate / Bake-required）
- 失败即关闭（fail-closed）：未知属性直接拒绝，不尝试"容错"

### 可落地改造

在JS引擎中建立 **pptxgenjs能力边界表**：

```markdown
| 预期效果 | pptxgenjs支持度 | 替代方案 |
|---------|----------------|---------|
| 图片非矩形裁剪 | 不支持 | 用形状mask模拟 |
| 渐变文字 | 不支持 | 用独立text+渐变rect叠加 |
| 元素入场动画 | 极弱 | 接受静态 | 
| 贝塞尔曲线 | 有限 | 用polyLine近似 |
| 透明度 | 支持 | - |
| 阴影 | 支持（blur≤5最佳） | - |
```

这样每页生成时就知道什么能做、什么需要变通。

---

## 六、颜色语义系统

### ppt-master 方案

使用牌颜色角色（Palette Color Roles）：

```
bg → secondary_bg → primary → accent → secondary_accent → body_text
```

不是自由配色，而是给每种颜色分配"角色"。图像生成也继承牌颜色。

### 可落地改造

电信PPT已有主题系统（7套），但可以正式化色彩角色语义：

```
telecom-red主题色彩角色：
  primary        = #C00000  ← 主标题、数字高亮、导航栏
  dark           = #A8001A  ← 深色变体、页脚
  gold           = #FFD700  ← 金色强调、装饰线
  card_fill      = #FFF0F0  ← 卡片背景
  card_stroke    = #E8B4B4  ← 卡片描边
  title_bar      = #FFE4E4  ← 标题栏底板
  body_text      = #000000  ← 正文
  assist_text    = #888888  ← 辅助文字
  highlight_bg   = #FFFF00  ← 数据高亮底色
```

---

## 融入状态

| 理念 | 状态 | 实现 |
|------|------|------|
| 双轨设计制（全局锁JSON） | 待实现 | Step 3 生成 lock.json → 每页前注入 |
| 逐页上下文投影 | 待实现 | 每页生成前注入context注释 |
| 72种图像布局 | 待实现 | 翻译为 page-templates.md 补充 |
| 三角色协作 | 待实现 | 拆分7步流程为三阶段 |
| pptxgenjs能力边界表 | 待实现 | 新建 references/pptxgenjs-limits.md |
| 色彩角色语义 | 已有基础 | 主题系统已定义，可进一步显式化 |
| Python SVG管道 | 已集成 | python-pipeline/ 独立模块 |
| 双引擎选择指南 | 已集成 | dual-engine-guide.md |