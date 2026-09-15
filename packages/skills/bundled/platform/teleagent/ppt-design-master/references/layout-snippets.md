---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '72438e8b-a819-4d9f-bb70-bb5977c8864f'
  PropagateID: '72438e8b-a819-4d9f-bb70-bb5977c8864f'
  ReservedCode1: 'e53dc9ce-f35c-43f5-a723-2accd1449ea8'
  ReservedCode2: 'e53dc9ce-f35c-43f5-a723-2accd1449ea8'
---

# PptxGenJS 版式代码片段

本文件提供各版式的 PptxGenJS 参数配置，供生成PPT时直接参考。

## 页面基础设置

```javascript
const pptx = new PptxGenJS();
pptx.defineLayout({ name: ' Custom', width: 10, height: 5.625 });
pptx.layout = 'Custom';  // 16:9
// 4:3 场景: width: 10, height: 7.5
```

## 标题区

```javascript
// 标题文字
slide.addText('页面标题', {
  x: 0.5, y: 0.12, w: 9.0, h: 0.38,
  fontSize: 22, fontFace: 'Microsoft YaHei',
  color: 'C8102E', bold: true,
  align: 'left', valign: 'middle'
});

// 标题下红色装饰短线
slide.addShape(pptx.shapes.RECTANGLE, {
  x: 0.5, y: 0.50, w: 0.35, h: 0.03,
  fill: { color: 'C8102E' }, line: { type: 'none' }
});

// 或：三色渐变条（红-橙-黄）
slide.addShape(pptx.shapes.RECTANGLE, {
  x: 0.5, y: 0.50, w: 1.05, h: 0.03,
  fill: { color: 'C8102E' }, line: { type: 'none' }
});
slide.addShape(pptx.shapes.RECTANGLE, {
  x: 0.85, y: 0.50, w: 0.35, h: 0.03,
  fill: { color: 'F29400' }, line: { type: 'none' }
});
slide.addShape(pptx.shapes.RECTANGLE, {
  x: 1.20, y: 0.50, w: 0.35, h: 0.03,
  fill: { color: 'FFCC00' }, line: { type: 'none' }
});
```

## 底部线条与页码

```javascript
// 底部红色细线
slide.addShape(pptx.shapes.RECTANGLE, {
  x: 0.35, y: 5.30, w: 9.30, h: 0.015,
  fill: { color: 'C8102E' }, line: { type: 'none' }
});

// 右下角页码
slide.addText(`${pageNum}`, {
  x: 9.0, y: 5.30, w: 0.65, h: 0.25,
  fontSize: 9, fontFace: 'Microsoft YaHei',
  color: '999999', align: 'right', valign: 'middle'
});
```

## 卡片通用函数

```javascript
function addCard(slide, x, y, w, h, title, body, mainColor) {
  // 圆角矩形背景
  slide.addShape(pptx.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h,
    fill: { color: 'FFFFFF' },
    line: { color: 'E5E5E5', width: 1 },
    rectRadius: 0.05
  });
  // 卡片标题
  if (title) {
    slide.addText(title, {
      x: x + 0.15, y: y + 0.10, w: w - 0.30, h: 0.30,
      fontSize: 11, fontFace: 'Microsoft YaHei',
      color: mainColor || '333333', bold: true
    });
  }
  // 卡片正文
  if (body) {
    slide.addText(body, {
      x: x + 0.15, y: y + 0.42, w: w - 0.30, h: h - 0.52,
      fontSize: 9, fontFace: 'Microsoft YaHei',
      color: '333333', valign: 'top'
    });
  }
}
```

## 2×2 网格布局

```javascript
const grid = {
  startX: 0.35, startY: 0.65,
  cardW: 4.55, cardH: 2.05,
  gapX: 0.20, gapY: 0.15
};
// 4张卡片位置
const positions = [
  { x: grid.startX,                          y: grid.startY },
  { x: grid.startX + grid.cardW + grid.gapX, y: grid.startY },
  { x: grid.startX,                          y: grid.startY + grid.cardH + grid.gapY },
  { x: grid.startX + grid.cardW + grid.gapX, y: grid.startY + grid.cardH + grid.gapY }
];
```

## 3列卡片布局

```javascript
const cols = {
  startX: 0.35, startY: 0.65,
  cardW: 3.00, cardH: 3.80,
  gapX: 0.15
};
const colPositions = [
  { x: cols.startX + i * (cols.cardW + cols.gapX), y: cols.startY }
  // i = 0, 1, 2
];
```

## 表格

```javascript
slide.addTable(rows, {
  x: 0.35, y: 0.65, w: 9.30,
  border: { type: 'solid', color: 'CCCCCC', pt: 1 },
  fontFace: 'Microsoft YaHei',
  fontSize: 9,
  align: 'left',
  // 表头行
  rowHeadH: 0.35,
  colW: [3.0, 2.0, 2.0, 2.3],  // 按内容分配
  autoPage: false,
  // 表头样式（rows[0]需单独设置）
  // 数据行交替底色：白/粉白交替
});
```

## 流程图节点与箭头

```javascript
function addFlowNode(slide, x, y, w, h, text, fillColor) {
  slide.addShape(pptx.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h,
    fill: { color: fillColor },
    line: { type: 'none' },
    rectRadius: 0.05
  });
  slide.addText(text, {
    x, y, w, h,
    fontSize: 10, fontFace: 'Microsoft YaHei',
    color: 'FFFFFF', bold: true,
    align: 'center', valign: 'middle'
  });
}

// 右箭头连接
function addArrowRight(slide, x, y, w, color) {
  slide.addShape(pptx.shapes.RIGHT_ARROW, {
    x, y, w: w || 0.40, h: 0.20,
    fill: { color: color || '666666' },
    line: { type: 'none' }
  });
}
```

## 时间线

```javascript
// 横轴基线
slide.addShape(pptx.shapes.LINE, {
  x: 0.5, y: 3.0, w: 9.0, h: 0,
  line: { color: 'CCCCCC', width: 1.5 }
});

// 节点圆点（已完成=实心红色，待完成=空心灰色）
function addTimelineDot(slide, x, y, completed) {
  slide.addShape(pptx.shapes.OVAL, {
    x: x - 0.08, y: y - 0.08, w: 0.16, h: 0.16,
    fill: { color: completed ? 'C8102E' : 'FFFFFF' },
    line: { color: completed ? 'C8102E' : 'CCCCCC', width: 2 }
  });
}
```

## 半闭合边框（C5/C6 特有）

```javascript
// 四角留缺口的边框，用于内容区外框装饰
// 实现：4条短线，每条留出两端 gap=0.3 英寸的缺口
function addHalfBorder(slide, x, y, w, h, gap, color) {
  const g = gap || 0.3;
  // 上边（左右各留gap）
  slide.addShape(pptx.shapes.RECTANGLE, {
    x: x + g, y: y, w: w - 2 * g, h: 0.01,
    fill: { color: color || 'A82820' }, line: { type: 'none' }
  });
  // 下边
  slide.addShape(pptx.shapes.RECTANGLE, {
    x: x + g, y: y + h, w: w - 2 * g, h: 0.01,
    fill: { color: color || 'A82820' }, line: { type: 'none' }
  });
  // 左边
  slide.addShape(pptx.shapes.RECTANGLE, {
    x: x, y: y + g, w: 0.01, h: h - 2 * g,
    fill: { color: color || 'A82820' }, line: { type: 'none' }
  });
  // 右边
  slide.addShape(pptx.shapes.RECTANGLE, {
    x: x + w, y: y + g, w: 0.01, h: h - 2 * g,
    fill: { color: color || 'A82820' }, line: { type: 'none' }
  });
}
```

## 红色虚线卡片（C5 特有，模拟截图区）

```javascript
slide.addShape(pptx.shapes.RECTANGLE, {
  x, y, w, h,
  fill: { color: 'FFFFFF' },
  line: { color: 'C8102E', width: 1, dashType: 'dash' }
});
```

## 深灰标题栏（C6 特有）

```javascript
// 页面顶部深灰色横条 + 白色标题
slide.addShape(pptx.shapes.RECTANGLE, {
  x: 0, y: 0, w: 10, h: 0.55,
  fill: { color: '2C2C2C' }, line: { type: 'none' }
});
slide.addText('页面标题', {
  x: 0.5, y: 0, w: 9.0, h: 0.55,
  fontSize: 20, fontFace: 'Microsoft YaHei',
  color: 'FFFFFF', bold: true,
  align: 'left', valign: 'middle'
});
```

## 封面页标准设计

```javascript
// 全页主色背景或白底+大标题
// 白底方案：
slide.addText('PPT主标题', {
  x: 1.0, y: 1.5, w: 8.0, h: 1.0,
  fontSize: 36, fontFace: 'Microsoft YaHei',
  color: 'C8102E', bold: true,
  align: 'center', valign: 'middle'
});
slide.addText('副标题 / 汇报日期', {
  x: 1.0, y: 2.6, w: 8.0, h: 0.5,
  fontSize: 16, fontFace: 'Microsoft YaHei',
  color: '666666', align: 'center'
});
// 底部渐变装饰条
slide.addShape(pptx.shapes.RECTANGLE, {
  x: 0, y: 5.2, w: 10, h: 0.425,
  fill: { color: 'C8102E' }, line: { type: 'none' }
});
```

> AI生成