---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '4b8c6fad-fa49-4835-b879-8625c84436b6'
  PropagateID: '4b8c6fad-fa49-4835-b879-8625c84436b6'
  ReservedCode1: '2c2ac9df-e1b6-45a9-82eb-db116c31b944'
  ReservedCode2: '2c2ac9df-e1b6-45a9-82eb-db116c31b944'
---

# 精控执行层 (Layer 5 · Refinement Execution)

> v6.0 新增 | 优先级：Phase 1

## 1. 解决什么问题

用户用自然语言描述微调意见（如"标题加粗""前三名标红""柱状图横画"），系统能**精确理解→映射为格式操作→自动执行**，并将重复微调**沉淀为记忆**，越用越精准。

## 2. 核心机制

```
自然语言微调 → 语义解析 → 格式操作映射 → 精确修改代码 → 重新渲染 → 记忆沉淀
```

## 3. 自然语言→格式操作映射表

### 3.1 文字格式类

| 自然语言 | pptxgenjs 操作 | 代码片段 |
|----------|---------------|---------|
| 加粗 / 加粗显示 | `bold: true` | `{ text: str, options: { bold: true } }` |
| 不加粗 / 取消加粗 | `bold: false` | `{ text: str, options: { bold: false } }` |
| 字号加大 / 放大字号 | `fontSize + 2~4pt` | `fontSize: originalSize + 2` |
| 字号缩小 / 缩小字号 | `fontSize - 2pt` | `fontSize: originalSize - 2` |
| 改成红色 / 红色文字 | `color: 'C00000'` | `{ text: str, options: { color: 'C00000' } }` |
| 改成蓝色 / 蓝色文字 | `color: '0070C0'` | `{ text: str, options: { color: '0070C0' } }` |
| 改成XX颜色 / #RRGGBB | `color: targetColor` | `{ text: str, options: { color: targetColor } }` |
| 居中 / 居中对齐 | `align: 'center'` | `{ align: 'center' }` |
| 靠左 / 左对齐 | `align: 'left'` | `{ align: 'left' }` |
| 靠右 / 右对齐 | `align: 'right'` | `{ align: 'right' }` |
| 字体改成XX | `fontName: target` | `{ fontFace: 'Microsoft YaHei' }` |
| 加下划线 | `underline: { style: 'sng' }` | `{ text: str, options: { underline: { style: 'sng' } } }` |
| 加删除线 | `strike: 'sngStrike'` | `{ text: str, options: { strike: 'sngStrike' } }` |
| 斜体 | `italic: true` | `{ text: str, options: { italic: true } }` |

### 3.2 布局调整类

| 自然语言 | pptxgenjs 操作 | 说明 |
|----------|---------------|------|
| 往左移一点 / 往左挪 | `x - 0.2~0.3` | 水平左移 |
| 往右移一点 / 往右挪 | `x + 0.2~0.3` | 水平右移 |
| 往上移一点 / 往上挪 | `y - 0.2~0.3` | 垂直上移 |
| 往下移一点 / 往下挪 | `y + 0.2~0.3` | 垂直下移 |
| 拉宽一点 / 宽一点 | `w + 0.3~0.5` | 增加宽度 |
| 缩窄一点 / 窄一点 | `w - 0.3~0.5` | 减少宽度 |
| 变高一点 / 高一点 | `h + 0.2~0.3` | 增加高度 |
| 变矮一点 / 矮一点 | `h - 0.2~0.3` | 减少高度 |
| 间距大一点 / 行距宽一点 | `lineSpacingMultiple + 0.1~0.2` | 增加行间距 |
| 间距小一点 / 行距紧一点 | `lineSpacingMultiple - 0.1` | 减少行间距 |
| 卡片间距大一点 | `gap + 0.1~0.2` | 卡片间间距 |
| 左右留白更多 | `margin/padding + 0.2` | 内边距增加 |

### 3.3 颜色变更类

| 自然语言 | pptxgenjs 操作 | 说明 |
|----------|---------------|------|
| 背景改成XX色 | `fill: { color: target }` | 元素背景色 |
| 卡片颜色改成XX | 卡片 `fill: target` | 卡片填充色 |
| 边框改成XX色 | `border: { color: target }` | 描边颜色 |
| 标题栏颜色 / 顶栏颜色 | 导航栏/标题栏 `fill: target` | 标题区背景 |
| 数字标红 / 关键数据标红 | `fmtNumber(text, true)` 或 `color: 'C00000'` | 数据强调 |
| 前三名标红 / Top3高亮 | 条件格式：排名≤3时 `color: 'C00000'` | 排名高亮 |
| 倒数标灰 / 后三名灰色 | 条件格式：末3名 `color: '999999'` | 排名弱化 |
| 黄色底色 / 黄色高亮 | `highlight: 'FFFF00'` 或 `fill: 'FFFF00'` | 重点底色 |

### 3.4 数据强调类

| 自然语言 | pptxgenjs 操作 | 说明 |
|----------|---------------|------|
| 数字大一点 / 数字放大 | KPI `fontSize + 8~12pt` | 数字尺寸加大 |
| 最大值标红 / 最高标红 | `Math.max(...values)` 对应项 `color: 'C00000'` | 最大值着色 |
| 最小值标灰 / 最低淡化 | `Math.min(...values)` 对应项 `color: '999999'` | 最小值弱化 |
| 超过XX的标红 | `if val > threshold: color: 'C00000'` | 阈值高亮 |
| 低于XX的标绿 | `if val < threshold: color: '00B050'` | 阈值低亮 |
| 正数绿色负数红色 | `val >= 0 ? '00B050' : 'C00000'` | 涨跌色 |
| 环比/同比箭头 | `↑/↓` + 绿/红色 | 趋势箭头 |

### 3.5 图表样式类

| 自然语言 | pptxgenjs 操作 | 说明 |
|----------|---------------|------|
| 柱状图横画 / 横向柱状图 | `barDir: 'bar'`（默认'col'为纵向） | 横向条形图 |
| 改成折线图 | `chartType: 'line'` | 图表类型切换 |
| 改成饼图 | `chartType: 'pie'` | 饼图 |
| 改成组合图 / 双轴图 | 两个 chart 叠加 + 不同轴 | 主次轴 |
| 加数据标签 | `showValue: true` | 显示数值标签 |
| 不显示数据标签 | `showValue: false` | 隐藏数值 |
| 加图例 / 显示图例 | `showLegend: true, legendPos: 'b'` | 底部图例 |
| Y轴从0开始 | `valAxisMinVal: 0` | Y轴最小值 |
| Y轴最大值XX | `valAxisMaxVal: N` | Y轴上限 |
| 柱子间距大一点 | `barGapWidthPct + 50~100` | 柱间距 |
| 柱子颜色 / 系列颜色 | `chartColors: [...]` | 自定义系列色 |

### 3.6 表格操作类

| 自然语言 | pptxgenjs 操作 | 说明 |
|----------|---------------|------|
| 表头加粗 | header row `bold: true` | 表头强调 |
| 表头底色 / 表头颜色 | header row `fill: targetColor` | 表头背景 |
| 交替行颜色 / 斑马纹 | 奇偶行 `fill` 交替 | 行交替色 |
| 前三名标红 | 条件格式 + `color: 'C00000'` | 排名高亮 |
| 某列加粗 | 指定列 `bold: true` | 列级格式 |
| 单元格合并 | `merge: [startRow, startCol, endRow, endCol]` | 合并单元格 |
| 列宽调整 / 某列宽一点 | `colW: [w1, w2, ...]` | 自定义列宽 |
| 行高调整 / 行高一点 | `rowH: [h1, h2, ...]` | 自定义行高 |

## 4. 微调执行流程

### 4.1 单次微调

```
用户说"第3页标题加粗" 
  → 语义解析：target=slide3.title, operation=bold:true
  → 在已生成代码中定位 slide3 的标题 addText 调用
  → 修改 options 添加 bold: true
  → 重新渲染 slide3
  → 记录到 REFINEMENT_LOG
```

### 4.2 批量微调

```
用户说"所有数字都标红"
  → 语义解析：target=allSlides.numericData, operation=color:'C00000'
  → 遍历所有 slide 的数字相关 addText 调用
  → 批量修改 options.color
  → 重新渲染受影响的 slides
  → 记录到 REFINEMENT_LOG
```

### 4.3 微调歧义处理

当微调指令有歧义时，不猜，主动确认：

| 歧义场景 | 处理方式 |
|----------|---------|
| "加粗"未指明对象 | 列出当前页可加粗的元素让用户选择 |
| "数字放大"不确定哪些数字 | 区分KPI数字/表格数字/图表标签 |
| "颜色"未指明具体色值 | 提供主题色板 + 常用色供选择 |
| "挪一下"方向不明 | 提示选择上下左右 |

## 5. 微调记忆闭环

### 5.1 三级沉淀机制

```
第1次同类微调 → 写入 REFINEMENT_LOG.md（临时记录）
第2次同类微调 → REFINEMENT_LOG.md 条目计数 +1
第3次同类微调 → 自动升级为固定规范，写入对应规范文件：
  - 写作类 → WRITING_STYLE.md
  - 企业规范类 → CORPORATE_SPEC.md  
  - 版面习惯类 → LAYOUT_HABITS.md
```

### 5.2 同类判定规则

| 微调类型 | 同类判定维度 |
|----------|------------|
| 文字格式 | 操作类型相同（如都是"加粗"）+ 目标角色相同（如都是"标题"） |
| 布局调整 | 目标区域相同（如都是"卡片间距"）+ 方向相同 |
| 颜色变更 | 目标位置相同（如都是"KPI数字"）+ 颜色相同 |
| 图表样式 | 图表类型相同 + 属性相同 |
| 表格操作 | 操作类型相同（如都是"交替行色"） |

### 5.3 记忆文件结构

详见 `references/style-memory.md` §3。

REFINEMENT_LOG.md 示例：

```markdown
# 微调记录

## 2026-07-11 | 文字格式 | 标题加粗 | count: 2/3
- 来源：专线经营分析PPT、风控季度汇报PPT
- 操作：所有页面标题 bold:true
- 下次再触发1次将升级为固定规范

## 2026-07-11 | 数据强调 | 前三名标红 | count: 3/3 → 已升级
- 来源：专线经营分析PPT、风控季度汇报PPT、5G-A规模PPT
- 操作：排名≤3时 color:'C00000'
- 已升级到 LAYOUT_HABITS.md §2.4
```

### 5.4 权重衰减

长期未触发的微调记忆逐渐降权：

| 时间 | 权重 |
|------|------|
| 1周内 | 1.0（完全生效） |
| 1-2周 | 0.8 |
| 2-4周 | 0.5 |
| 1-3月 | 0.3 |
| 3月以上 | 0.1（弱提示，不自动执行） |

衰减仅影响自动应用，用户显式要求的微调始终完全执行。

## 6. 与各层的交互

| 交互层 | 关系 |
|--------|------|
| Layer 1 · 数据智能 | 表格微调影响 Table Contract 中的列宽/行高/条件格式 |
| Layer 2 · 模板锚定 | 微调在 Layout Map 坐标基础上叠加偏移量，不重置锚定位置 |
| Layer 3 · 风格记忆 | 微调记忆是风格记忆的输入源之一 |
| Layer 4 · 创意设计 | 创意方案的微调也走本层映射和沉淀 |

## 7. 微调操作速查

用户最常用的5种微调及其完整代码模板：

### 7.1 前三名标红

```javascript
// 在生成表格/排名数据时
rows.forEach((row, i) => {
  if (i > 0 && i <= 3) { // 前3名（跳过表头）
    row.forEach((cell, j) => {
      if (typeof cell === 'object' && cell.options) {
        cell.options.color = 'C00000';
        cell.options.bold = true;
      }
    });
  }
});
```

### 7.2 数字放大 + 标红

```javascript
slide.addText([
  { text: '户均提值 ', options: { fontSize: 12, color: '333333' } },
  { text: '20元', options: { fontSize: 20, color: 'C00000', bold: true } }
], { x, y, w, h });
```

### 7.3 柱状图横画

```javascript
slide.addChart(pres.ChartType.BAR, chartData, {
  x, y, w, h,
  barDir: 'bar',      // 关键：横向
  barGapWidthPct: 80,
  showValue: true,
  valAxisMinVal: 0,
  chartColors: ['C00000']
});
```

### 7.4 黄色底色高亮

```javascript
slide.addText(highlightText, {
  x, y, w, h,
  color: 'C00000',
  bold: true,
  fill: { color: 'FFFF00' },  // 黄底
  fontSize: 12
});
```

### 7.5 正负色（涨绿跌红）

```javascript
const trendColor = value >= 0 ? '00B050' : 'C00000';
const trendArrow = value >= 0 ? '↑' : '↓';
slide.addText([
  { text: `${trendArrow}${Math.abs(value)}%`, options: { color: trendColor, bold: true, fontSize: 12 } }
], { x, y, w, h });
```