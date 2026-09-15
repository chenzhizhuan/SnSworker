---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '2603d5b7-0c62-4a8f-ac01-6cde30bb221a'
  PropagateID: '2603d5b7-0c62-4a8f-ac01-6cde30bb221a'
  ReservedCode1: 'd0499b41-664a-4891-8812-ac6d5cacc702'
  ReservedCode2: 'd0499b41-664a-4891-8812-ac6d5cacc702'
---

# Page Templates

本文件从皖美一PPT技能移植。所有模板与 `telecom-boilerplate.js` 完全兼容——使用电信启动模板时，`addNav`/`addTitle`/`addFooter`/`makeShadow` 自动替换为电信风格版本。

16 个独立幻灯片原型。每个代码块完全自包含——粘贴、参数化数据，即可得到精美幻灯片。所有模板假设 boilerplate 中的 `addNav`、`addTitle`、`addFooter`、`makeShadow` 以及主题 `C` 和 `F` 已在作用域中。

## 模板选择原则

- **从证明对象选择模板**，而非从审美。图表/结果→T9/T13/T5；流程/方法→T11；对比→T6；密集规格→T10；总结→T15
- 每个内容页一个主要证明对象
- 如果页面信息过载，拆分或换模板，不要缩小字体
- 不要连续 3 页用卡片/网格结构，用锚点页打断节奏

## T1 · 封面

```js
function slideCover(s, { title, subtitle, author, affiliation, date }) {
  s.background = { color: C.bg };
  // 顶部装饰条
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: W, h: 0.5,
    fill: { color: C.primary }, line: { type: "none" },
  });
  // 底部装饰条
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: H - 0.5, w: W, h: 0.5,
    fill: { color: C.primary }, line: { type: "none" },
  });
  // 标题下强调线
  s.addShape(pres.shapes.RECTANGLE, {
    x: W / 2 - 1.5, y: 3.4, w: 3, h: 0.06,
    fill: { color: C.accent }, line: { type: "none" },
  });
  s.addText(title, {
    x: 0.5, y: 2.3, w: W - 1, h: 1.0,
    fontFace: F.cn, fontSize: 36, bold: true, charSpacing: 4,
    color: C.primary, align: "center", valign: "middle", margin: 0,
  });
  if (subtitle) {
    s.addText(subtitle, {
      x: 0.5, y: 3.6, w: W - 1, h: 0.5,
      fontFace: F.cn, fontSize: 16, italic: true,
      color: C.muted, align: "center", valign: "middle", margin: 0,
    });
  }
  s.addText(`${author}    ·    ${affiliation}    ·    ${date}`, {
    x: 0.5, y: 5.2, w: W - 1, h: 0.4,
    fontFace: F.cn, fontSize: 13,
    color: C.text, align: "center", valign: "middle", margin: 0,
  });
}
```

## T2 · 目录

```js
function slideTOC(s, { sections }) {
  // sections: [{ num, title, subtitle, page }]
  s.background = { color: C.bg };
  addNav(s, -1);
  addTitle(s, "目录", "Table of Contents");
  addFooter(s, "—");

  const startY = 2.0;
  const rowH = 5.0 / sections.length;
  sections.forEach((sec, i) => {
    const y = startY + i * rowH;
    s.addText(String(sec.num).padStart(2, "0"), {
      x: 1.0, y, w: 1.2, h: rowH,
      fontFace: F.en, fontSize: 36, bold: true,
      color: C.accent, align: "left", valign: "middle", margin: 0,
    });
    s.addText(sec.title, {
      x: 2.4, y, w: 8.0, h: rowH * 0.55,
      fontFace: F.cn, fontSize: 18, bold: true,
      color: C.text, align: "left", valign: "bottom", margin: 0,
    });
    if (sec.subtitle) {
      s.addText(sec.subtitle, {
        x: 2.4, y: y + rowH * 0.55, w: 8.0, h: rowH * 0.4,
        fontFace: F.en, fontSize: 12, italic: true,
        color: C.muted, align: "left", valign: "top", margin: 0,
      });
    }
    if (sec.page) {
      s.addText(`P.${sec.page}`, {
        x: 11.4, y, w: 1.0, h: rowH,
        fontFace: F.en, fontSize: 12,
        color: C.muted, align: "right", valign: "middle", margin: 0,
      });
    }
  });
}
```

## T3 · 章节分隔

```js
function slideSectionBreak(s, { num, title, subtitle, navIdx }) {
  s.background = { color: C.bg };
  addNav(s, navIdx);
  addFooter(s, "—");

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.5, w: W - 0.8, h: 4.8,
    fill: { color: C.primary }, line: { type: "none" },
    shadow: { type: "outer", color: "000000", blur: 18, offset: 4, angle: 90, opacity: 0.18 },
  });
  s.addText(String(num).padStart(2, "0"), {
    x: 1.2, y: 1.9, w: 3, h: 1.6,
    fontFace: F.en, fontSize: 96, bold: true,
    color: C.accentLight, align: "left", valign: "middle", margin: 0,
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 1.2, y: 3.65, w: 1.0, h: 0.05,
    fill: { color: C.accentLight }, line: { type: "none" },
  });
  s.addText(title, {
    x: 1.2, y: 3.8, w: W - 2.4, h: 0.9,
    fontFace: F.cn, fontSize: 32, bold: true,
    color: C.white, align: "left", valign: "middle", margin: 0,
  });
  if (subtitle) {
    s.addText(subtitle, {
      x: 1.2, y: 4.8, w: W - 2.4, h: 0.5,
      fontFace: F.cn, fontSize: 14, italic: true,
      color: C.accentLight, align: "left", valign: "middle", margin: 0,
    });
  }
}
```

## T4 · 概念定义

```js
function slideConcept(s, { title, subtitle, navIdx, page, definition, points }) {
  // points: [{ title, desc }]  (推荐3个)
  s.background = { color: C.bg };
  addNav(s, navIdx);
  addTitle(s, title, subtitle);
  addFooter(s, page);

  // 定义条
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.95, w: W - 0.8, h: 1.1,
    fill: { color: C.iceLight }, line: { color: C.iceMid, width: 0.5 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.95, w: 0.12, h: 1.1,
    fill: { color: C.accent }, line: { type: "none" },
  });
  s.addText(definition, {
    x: 0.7, y: 1.95, w: W - 1.1, h: 1.1,
    fontFace: F.cn, fontSize: 16, bold: true,
    color: C.primary, valign: "middle", margin: 0,
  });

  // 三张支撑卡片
  const cardW = (W - 0.8 - 0.6) / 3;
  const cardY = 3.3, cardH = 3.5;
  points.slice(0, 3).forEach((p, i) => {
    const x = 0.4 + i * (cardW + 0.3);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: cardY, w: cardW, h: cardH,
      fill: { color: C.white }, line: { color: C.border, width: 0.5 },
      shadow: makeShadow(),
    });
    // 编号圆圈
    s.addShape(pres.shapes.OVAL, {
      x: x + cardW / 2 - 0.35, y: cardY + 0.4, w: 0.7, h: 0.7,
      fill: { color: C.primary }, line: { type: "none" },
    });
    s.addText(String(i + 1), {
      x: x + cardW / 2 - 0.35, y: cardY + 0.4, w: 0.7, h: 0.7,
      fontFace: F.en, fontSize: 22, bold: true,
      color: C.accentLight, align: "center", valign: "middle", margin: 0,
    });
    s.addText(p.title, {
      x: x + 0.2, y: cardY + 1.3, w: cardW - 0.4, h: 0.5,
      fontFace: F.cn, fontSize: 16, bold: true,
      color: C.primary, align: "center", valign: "middle", margin: 0,
    });
    s.addText(p.desc, {
      x: x + 0.3, y: cardY + 1.85, w: cardW - 0.6, h: cardH - 2.0,
      fontFace: F.cn, fontSize: 12,
      color: C.textLight, align: "center", valign: "top", margin: 0,
    });
  });
}
```

## T5 · 主图展示

```js
function slideHero(s, { title, subtitle, navIdx, page, imagePath, caption, points }) {
  s.background = { color: C.bg };
  addNav(s, navIdx);
  addTitle(s, title, subtitle);
  addFooter(s, page);

  const FX = 0.4, FY = 1.95, FW = 8.4, FH = 5.0;
  s.addShape(pres.shapes.RECTANGLE, {
    x: FX, y: FY, w: FW, h: FH,
    fill: { color: C.white }, line: { color: C.border, width: 0.5 },
    shadow: makeShadow(),
  });
  s.addImage({
    path: imagePath,
    x: FX + 0.2, y: FY + 0.2, w: FW - 0.4, h: FH - 0.4,
    sizing: { type: "contain", w: FW - 0.4, h: FH - 0.4 },
  });

  // 右侧标注栏
  const RX = 9.0, RW = W - 9.4;
  s.addShape(pres.shapes.RECTANGLE, {
    x: RX, y: FY, w: 0.08, h: FH,
    fill: { color: C.accent }, line: { type: "none" },
  });
  s.addText(caption, {
    x: RX + 0.2, y: FY, w: RW - 0.2, h: 0.8,
    fontFace: F.cn, fontSize: 14, bold: true,
    color: C.primary, valign: "top", margin: 0,
  });
  const bulletItems = points.map(p => ({
    text: p,
    options: { bullet: { code: "25CF" }, color: C.text, breakLine: true, paraSpaceAfter: 6 },
  }));
  s.addText(bulletItems, {
    x: RX + 0.2, y: FY + 0.9, w: RW - 0.2, h: FH - 1.0,
    fontFace: F.cn, fontSize: 12, color: C.text,
    valign: "top", margin: 0,
  });
}
```

## T6 · 两栏对比

```js
function slideCompare(s, { title, subtitle, navIdx, page, left, right }) {
  // left/right: { header, color, items: [{ title, desc }] }
  s.background = { color: C.bg };
  addNav(s, navIdx);
  addTitle(s, title, subtitle);
  addFooter(s, page);

  const CY = 1.95, CH = 5.0;
  const CW = (W - 0.8 - 0.4) / 2;
  const LX = 0.4, RX = LX + CW + 0.4;

  [[LX, left], [RX, right]].forEach(([x, side]) => {
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: CY, w: CW, h: 0.55,
      fill: { color: side.color }, line: { type: "none" },
    });
    s.addText(side.header, {
      x: x + 0.3, y: CY, w: CW - 0.6, h: 0.55,
      fontFace: F.cn, fontSize: 16, bold: true,
      color: C.white, valign: "middle", margin: 0,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: CY + 0.55, w: CW, h: CH - 0.55,
      fill: { color: C.white }, line: { color: C.border, width: 0.5 },
      shadow: makeShadow(),
    });
    side.items.forEach((it, i) => {
      const py = CY + 0.85 + i * 1.15;
      s.addShape(pres.shapes.OVAL, {
        x: x + 0.3, y: py + 0.05, w: 0.45, h: 0.45,
        fill: { color: side.color === C.contrast ? C.contrastPale : C.accentPale },
        line: { color: side.color, width: 1.5 },
      });
      s.addText(String(i + 1), {
        x: x + 0.3, y: py + 0.05, w: 0.45, h: 0.45,
        fontFace: F.en, fontSize: 14, bold: true,
        color: side.color, align: "center", valign: "middle", margin: 0,
      });
      s.addText(it.title, {
        x: x + 0.85, y: py, w: CW - 1.05, h: 0.4,
        fontFace: F.cn, fontSize: 14, bold: true,
        color: C.text, valign: "middle", margin: 0,
      });
      s.addText(it.desc, {
        x: x + 0.85, y: py + 0.4, w: CW - 1.05, h: 0.6,
        fontFace: F.cn, fontSize: 12,
        color: C.textLight, valign: "top", margin: 0,
      });
    });
  });
}
```

## T7 · 三卡片行

```js
function slideTriple(s, { title, subtitle, navIdx, page, cards }) {
  // cards: [{ headerColor, num, title, subtitle, bullets: [string], kpi: string }]
  s.background = { color: C.bg };
  addNav(s, navIdx);
  addTitle(s, title, subtitle);
  addFooter(s, page);

  const CY = 1.95, CH = 4.6;
  const CW = (W - 0.8 - 0.6) / 3;
  cards.slice(0, 3).forEach((c, i) => {
    const x = 0.4 + i * (CW + 0.3);
    // 头部条带
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: CY, w: CW, h: 1.0,
      fill: { color: c.headerColor || C.primary }, line: { type: "none" },
    });
    s.addText(String(c.num), {
      x: x + 0.2, y: CY + 0.1, w: 0.6, h: 0.8,
      fontFace: F.en, fontSize: 28, bold: true,
      color: C.accentLight, valign: "middle", margin: 0,
    });
    s.addText(c.title, {
      x: x + 0.85, y: CY + 0.15, w: CW - 1.0, h: 0.45,
      fontFace: F.cn, fontSize: 16, bold: true, italic: true,
      color: C.white, valign: "middle", margin: 0,
    });
    s.addText(c.subtitle, {
      x: x + 0.85, y: CY + 0.55, w: CW - 1.0, h: 0.4,
      fontFace: F.cn, fontSize: 12,
      color: C.accentLight, valign: "middle", margin: 0,
    });
    // 卡片主体
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: CY + 1.0, w: CW, h: CH - 1.0,
      fill: { color: C.white }, line: { color: C.border, width: 0.5 },
      shadow: makeShadow(),
    });
    const bulletList = c.bullets.map(b => ({
      text: b,
      options: { bullet: { code: "25CF" }, color: C.text, breakLine: true, paraSpaceAfter: 4 },
    }));
    s.addText(bulletList, {
      x: x + 0.25, y: CY + 1.2, w: CW - 0.5, h: CH - 2.3,
      fontFace: F.cn, fontSize: 12, color: C.text,
      valign: "top", margin: 0,
    });
    // KPI 盒
    if (c.kpi) {
      s.addShape(pres.shapes.RECTANGLE, {
        x: x + 0.25, y: CY + CH - 0.95, w: CW - 0.5, h: 0.75,
        fill: { color: c.headerColor || C.primary }, line: { type: "none" },
      });
      s.addText(c.kpi, {
        x: x + 0.25, y: CY + CH - 0.95, w: CW - 0.5, h: 0.75,
        fontFace: F.cn, fontSize: 13, bold: true,
        color: C.accentLight, align: "center", valign: "middle", margin: 0,
      });
    }
  });
}
```

## T8 · 2×2 矩阵

```js
function slideMatrix(s, { title, subtitle, navIdx, page, quadrants }) {
  // quadrants: [{ num, title, subtitle, gapLabel, gap, nextStep }]  (4项)
  s.background = { color: C.bg };
  addNav(s, navIdx);
  addTitle(s, title, subtitle);
  addFooter(s, page);

  const CW = (W - 0.8 - 0.3) / 2;
  const CH = (5.1 - 0.3) / 2;
  const positions = [
    { x: 0.4, y: 1.95 },
    { x: 0.7 + CW, y: 1.95 },
    { x: 0.4, y: 1.95 + CH + 0.3 },
    { x: 0.7 + CW, y: 1.95 + CH + 0.3 },
  ];
  quadrants.slice(0, 4).forEach((q, i) => {
    const { x, y } = positions[i];
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: CW, h: CH,
      fill: { color: C.white }, line: { color: C.border, width: 0.5 },
      shadow: makeShadow(),
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 0.12, h: CH,
      fill: { color: C.primary }, line: { type: "none" },
    });
    s.addText(String(q.num), {
      x: x + 0.3, y: y + 0.15, w: 0.7, h: 0.7,
      fontFace: F.en, fontSize: 36, bold: true,
      color: C.primary, valign: "middle", margin: 0,
    });
    s.addText(q.title, {
      x: x + 1.1, y: y + 0.2, w: CW - 1.3, h: 0.4,
      fontFace: F.cn, fontSize: 16, bold: true,
      color: C.text, valign: "middle", margin: 0,
    });
    if (q.subtitle) {
      s.addText(q.subtitle, {
        x: x + 1.1, y: y + 0.6, w: CW - 1.3, h: 0.3,
        fontFace: F.en, fontSize: 12, italic: true,
        color: C.muted, valign: "middle", margin: 0,
      });
    }
    s.addText([
      { text: q.gapLabel || "现状", options: { bold: true, color: C.primary, fontSize: 12 } },
      { text: "  " + q.gap, options: { color: C.textLight, fontSize: 12 } },
    ], {
      x: x + 0.3, y: y + 1.1, w: CW - 0.5, h: 0.7,
      fontFace: F.cn, valign: "top", margin: 0,
    });
    if (q.nextStep) {
      s.addShape(pres.shapes.RECTANGLE, {
        x: x + 0.3, y: y + CH - 0.6, w: CW - 0.5, h: 0.4,
        fill: { color: C.accentPale }, line: { color: C.accent, width: 0.5 },
      });
      s.addText("→  " + q.nextStep, {
        x: x + 0.3, y: y + CH - 0.6, w: CW - 0.5, h: 0.4,
        fontFace: F.cn, fontSize: 12, bold: true, italic: true,
        color: C.primary, align: "center", valign: "middle", margin: 0,
      });
    }
  });
}
```

## T9 · 图表/数据

```js
function slideChart(s, { title, subtitle, navIdx, page, chartType, data, takeaway }) {
  s.background = { color: C.bg };
  addNav(s, navIdx);
  addTitle(s, title, subtitle);
  addFooter(s, page);

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.95, w: W - 0.8, h: 4.3,
    fill: { color: C.white }, line: { color: C.border, width: 0.5 },
    shadow: makeShadow(),
  });
  s.addChart(pres.charts[chartType], data, {
    x: 0.6, y: 2.1, w: W - 1.2, h: 4.0,
    chartColors: [C.primary, C.accent, C.contrast, C.primaryLight],
    chartArea: { fill: { color: C.iceLight } },
    plotArea: { fill: { color: C.iceLight } },
    catAxisLabelColor: C.muted, catAxisLabelFontFace: F.cn, catAxisLabelFontSize: 12,
    valAxisLabelColor: C.muted, valAxisLabelFontFace: F.cn, valAxisLabelFontSize: 12,
    valGridLine: { color: C.border, size: 0.5 },
    catGridLine: { style: "none" },
    showLegend: true, legendPos: "b",
    legendFontFace: F.cn, legendFontSize: 12, legendColor: C.text,
    lineSize: 2.5, lineSmooth: true,
  });

  if (takeaway) {
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.4, y: 6.45, w: W - 0.8, h: 0.55,
      fill: { color: C.primary }, line: { type: "none" },
    });
    s.addText([
      { text: "关键发现  ", options: { bold: true, color: C.accentLight, fontSize: 12 } },
      { text: takeaway, options: { color: C.white, fontSize: 12 } },
    ], {
      x: 0.6, y: 6.45, w: W - 1.2, h: 0.55,
      fontFace: F.cn, valign: "middle", margin: 0,
    });
  }
}
```

## T10 · 表格

```js
function slideTable(s, { title, subtitle, navIdx, page, headers, rows, highlightRow, footnote }) {
  s.background = { color: C.bg };
  addNav(s, navIdx);
  addTitle(s, title, subtitle);
  addFooter(s, page);

  const headerStyle = {
    bold: true, color: C.white, fill: { color: C.primaryDark },
    align: "center", valign: "middle", fontFace: F.cn, fontSize: 12,
  };
  const cellBase = {
    color: C.text, align: "center", valign: "middle",
    fontFace: F.cn, fontSize: 12,
  };
  const highlightStyle = {
    bold: true, color: C.white, fill: { color: C.primary },
    align: "center", valign: "middle", fontFace: F.cn, fontSize: 12,
  };

  const tableData = [
    headers.map(h => ({ text: h, options: headerStyle })),
    ...rows.map((row, i) => {
      const style = (i === highlightRow) ? highlightStyle : cellBase;
      return row.map(cell => ({ text: cell, options: style }));
    }),
  ];

  const colCount = headers.length;
  const totalW = W - 0.8;
  const colW = Array(colCount).fill(totalW / colCount);

  s.addTable(tableData, {
    x: 0.4, y: 2.0, w: totalW,
    colW, rowH: 0.4,
    border: { type: "solid", color: C.border, pt: 0.5 },
  });

  if (footnote) {
    s.addText(footnote, {
      x: 0.4, y: H - 1.0, w: W - 0.8, h: 0.4,
      fontFace: F.cn, fontSize: 12, italic: true,
      color: C.muted, align: "left", valign: "middle", margin: 0,
    });
  }
}
```

## T11 · 流程/管道图

```js
function slideFlow(s, { title, subtitle, navIdx, page, steps, summary }) {
  // steps: [{ label, desc }]
  s.background = { color: C.bg };
  addNav(s, navIdx);
  addTitle(s, title, subtitle);
  addFooter(s, page);

  const n = steps.length;
  const arrowW = 0.6;
  const totalAvail = W - 0.8 - (n - 1) * arrowW;
  const stepW = totalAvail / n;
  const stepH = 1.4;
  const yMid = 3.5;
  const yStep = yMid - stepH / 2;

  steps.forEach((st, i) => {
    const x = 0.4 + i * (stepW + arrowW);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: yStep, w: stepW, h: stepH,
      fill: { color: C.primary }, line: { type: "none" },
      shadow: makeShadow(),
    });
    s.addText(String(i + 1), {
      x, y: yStep + 0.1, w: stepW, h: 0.4,
      fontFace: F.en, fontSize: 14, bold: true,
      color: C.accentLight, align: "center", valign: "middle", margin: 0,
    });
    s.addText(st.label, {
      x: x + 0.1, y: yStep + 0.5, w: stepW - 0.2, h: 0.8,
      fontFace: F.cn, fontSize: 13, bold: true,
      color: C.white, align: "center", valign: "middle", margin: 0,
    });
    s.addText(st.desc, {
      x: x - 0.1, y: yMid + stepH / 2 + 0.15, w: stepW + 0.2, h: 0.7,
      fontFace: F.cn, fontSize: 12,
      color: C.textLight, align: "center", valign: "top", margin: 0,
    });
    if (i < n - 1) {
      s.addText("\u2192", {
        x: x + stepW, y: yStep, w: arrowW, h: stepH,
        fontFace: F.en, fontSize: 24, bold: true,
        color: C.accent, align: "center", valign: "middle", margin: 0,
      });
    }
  });

  if (summary) {
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.4, y: 6.0, w: W - 0.8, h: 0.7,
      fill: { color: C.accentPale }, line: { color: C.accent, width: 0.5 },
    });
    s.addText(summary, {
      x: 0.6, y: 6.0, w: W - 1.2, h: 0.7,
      fontFace: F.cn, fontSize: 12, italic: true,
      color: C.text, align: "center", valign: "middle", margin: 0,
    });
  }
}
```

## T12 · 时间线

```js
function slideTimeline(s, { title, subtitle, navIdx, page, milestones }) {
  s.background = { color: C.bg };
  addNav(s, navIdx);
  addTitle(s, title, subtitle);
  addFooter(s, page);

  const yLine = 4.0;
  const xStart = 0.8, xEnd = W - 0.8;
  s.addShape(pres.shapes.RECTANGLE, {
    x: xStart, y: yLine - 0.02, w: xEnd - xStart, h: 0.04,
    fill: { color: C.border }, line: { type: "none" },
  });

  const n = milestones.length;
  const stepX = (xEnd - xStart) / (n - 1);
  milestones.forEach((m, i) => {
    const cx = xStart + i * stepX;
    const above = (i % 2 === 0);
    s.addShape(pres.shapes.OVAL, {
      x: cx - 0.18, y: yLine - 0.18, w: 0.36, h: 0.36,
      fill: { color: C.primary }, line: { color: C.white, width: 3 },
    });
    s.addText(m.date, {
      x: cx - 1.0, y: above ? yLine - 1.6 : yLine + 0.4, w: 2.0, h: 0.3,
      fontFace: F.en, fontSize: 12, bold: true,
      color: C.accent, align: "center", valign: "middle", margin: 0,
    });
    s.addText(m.label, {
      x: cx - 1.2, y: above ? yLine - 1.3 : yLine + 0.7, w: 2.4, h: 0.4,
      fontFace: F.cn, fontSize: 13, bold: true,
      color: C.text, align: "center", valign: "middle", margin: 0,
    });
    s.addText(m.desc, {
      x: cx - 1.3, y: above ? yLine - 0.9 : yLine + 1.1, w: 2.6, h: 0.7,
      fontFace: F.cn, fontSize: 12,
      color: C.textLight, align: "center", valign: "top", margin: 0,
    });
  });
}
```

## T13 · KPI/指标

```js
function slideKPI(s, { title, subtitle, navIdx, page, metrics, narrative }) {
  // metrics: [{ value, unit, label, sub, color }]  (3-4项)
  s.background = { color: C.bg };
  addNav(s, navIdx);
  addTitle(s, title, subtitle);
  addFooter(s, page);

  const n = metrics.length;
  const cardH = 2.4;
  const cardW = (W - 0.8 - (n - 1) * 0.3) / n;
  const cardY = 2.5;

  metrics.forEach((m, i) => {
    const x = 0.4 + i * (cardW + 0.3);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: cardY, w: cardW, h: cardH,
      fill: { color: C.iceLight }, line: { color: C.border, width: 0.5 },
      shadow: makeShadow(),
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: cardY, w: cardW, h: 0.12,
      fill: { color: m.color || C.primary }, line: { type: "none" },
    });
    s.addText(m.value, {
      x: x + 0.2, y: cardY + 0.3, w: cardW - 0.4, h: 1.0,
      fontFace: F.en, fontSize: 56, bold: true,
      color: m.color || C.primary, align: "center", valign: "middle", margin: 0,
    });
    if (m.unit) {
      s.addText(m.unit, {
        x: x + 0.2, y: cardY + 1.25, w: cardW - 0.4, h: 0.3,
        fontFace: F.cn, fontSize: 14, bold: true,
        color: C.muted, align: "center", valign: "middle", margin: 0,
      });
    }
    s.addText(m.label, {
      x: x + 0.2, y: cardY + 1.6, w: cardW - 0.4, h: 0.4,
      fontFace: F.cn, fontSize: 14, bold: true,
      color: C.text, align: "center", valign: "middle", margin: 0,
    });
    if (m.sub) {
      s.addText(m.sub, {
        x: x + 0.2, y: cardY + 2.0, w: cardW - 0.4, h: 0.35,
        fontFace: F.cn, fontSize: 12, italic: true,
        color: C.muted, align: "center", valign: "middle", margin: 0,
      });
    }
  });

  if (narrative) {
    s.addText(narrative, {
      x: 0.6, y: 5.3, w: W - 1.2, h: 1.4,
      fontFace: F.cn, fontSize: 13, italic: true,
      color: C.textLight, align: "center", valign: "middle", margin: 0,
    });
  }
}
```

## T14 · 引用/高亮

```js
function slideQuote(s, { title, subtitle, navIdx, page, quote, attribution }) {
  s.background = { color: C.bg };
  addNav(s, navIdx);
  if (title) addTitle(s, title, subtitle);
  addFooter(s, page);

  const yQ = title ? 2.5 : 1.8;
  s.addText("\u201C", {
    x: 0.8, y: yQ - 0.3, w: 1.5, h: 1.5,
    fontFace: F.en, fontSize: 120, bold: true,
    color: C.accent, valign: "top", margin: 0,
  });
  s.addText(quote, {
    x: 1.5, y: yQ + 0.5, w: W - 3.0, h: 2.5,
    fontFace: F.cn, fontSize: 24, italic: true,
    color: C.primary, align: "left", valign: "middle", margin: 0,
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 1.5, y: yQ + 3.2, w: 2.0, h: 0.04,
    fill: { color: C.accent }, line: { type: "none" },
  });
  if (attribution) {
    s.addText(`\u2014 ${attribution}`, {
      x: 1.5, y: yQ + 3.4, w: W - 3.0, h: 0.4,
      fontFace: F.cn, fontSize: 14,
      color: C.muted, align: "left", valign: "middle", margin: 0,
    });
  }
}
```

## T15 · 总结

```js
function slideSummary(s, { title, subtitle, navIdx, page, takeaways, closing }) {
  // takeaways: [{ label, content }]  (推荐3项)
  s.background = { color: C.bg };
  addNav(s, navIdx);
  addTitle(s, title, subtitle);
  addFooter(s, page);

  const cardW = (W - 0.8 - 0.4) / takeaways.length;
  const cardY = 2.2, cardH = 3.5;
  takeaways.forEach((tk, i) => {
    const x = 0.4 + i * (cardW + 0.2);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: cardY, w: cardW, h: cardH,
      fill: { color: C.white }, line: { color: C.border, width: 0.5 },
      shadow: makeShadow(),
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: cardY, w: cardW, h: 0.6,
      fill: { color: i === 0 ? C.primary : (i === 1 ? C.accent : C.contrast) },
      line: { type: "none" },
    });
    s.addText(tk.label, {
      x: x + 0.2, y: cardY, w: cardW - 0.4, h: 0.6,
      fontFace: F.cn, fontSize: 14, bold: true,
      color: C.white, align: "center", valign: "middle", margin: 0,
    });
    s.addText(tk.content, {
      x: x + 0.3, y: cardY + 0.8, w: cardW - 0.6, h: cardH - 1.0,
      fontFace: F.cn, fontSize: 12,
      color: C.text, align: "left", valign: "top", margin: 0, paraSpaceAfter: 6,
    });
  });

  if (closing) {
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.4, y: cardY + cardH + 0.3, w: W - 0.8, h: 0.7,
      fill: { color: C.primary }, line: { type: "none" },
    });
    s.addText(closing, {
      x: 0.6, y: cardY + cardH + 0.3, w: W - 1.2, h: 0.7,
      fontFace: F.cn, fontSize: 14, bold: true,
      color: C.white, align: "center", valign: "middle", margin: 0,
    });
  }
}
```

## T16 · 致谢/Q&A

```js
function slideThanks(s, { mainText, secondary, contact, navIdx }) {
  s.background = { color: C.bg };
  addNav(s, navIdx);
  addFooter(s, "—");

  s.addText(mainText || "Thank You", {
    x: 0.5, y: 2.5, w: W - 1, h: 1.2,
    fontFace: F.en, fontSize: 60, bold: true, charSpacing: 6,
    color: C.primary, align: "center", valign: "middle", margin: 0,
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: W / 2 - 1.5, y: 3.85, w: 3, h: 0.05,
    fill: { color: C.accent }, line: { type: "none" },
  });
  s.addText(secondary || "Q & A", {
    x: 0.5, y: 4.0, w: W - 1, h: 0.6,
    fontFace: F.cn, fontSize: 22, italic: true,
    color: C.muted, align: "center", valign: "middle", margin: 0,
  });
  if (contact) {
    s.addText(contact, {
      x: 0.5, y: 5.5, w: W - 1, h: 0.4,
      fontFace: F.cn, fontSize: 13,
      color: C.textLight, align: "center", valign: "middle", margin: 0,
    });
  }
}
```

---

# T17-T24 · 高管座谈会高级页面模板（v7.0 新增）

> 以下模板专为总经理座谈会/半年会/经营复盘场景设计，遵循 `executive-style-guide.md` 中的蓝主红辅配色体系。
> 使用 `executive-blue` 主题时，`C` 自动切换为蓝色主色体系，`F` 保持微软雅黑。
> 以下模板假设 boilerplate 中的 `addExecutiveNav`、`addExecutiveFooter` 已在作用域中。
> 也可在 telecom-red 主题下使用（C.primary 为红色），方法内自动适配。

## T17 · 座谈会封面（白底 + 渐变飘带）

```js
function slideExecutiveCover(s, { titleLine1, titleLine2, subtitle, date, style = 'white' }) {
  // style: 'white'（风格A白底渐变带） | 'red'（风格B红底城市剪影）
  if (style === 'red') {
    // 风格B: 深红径向渐变底
    s.background = { color: "A8001A" };
    // 放射光效模拟（中心亮区）
    s.addShape(pres.shapes.OVAL, {
      x: W / 2 - 4, y: 1.5, w: 8, h: 5,
      fill: { color: "C00000" }, line: { type: "none" }
    });
    // 底部城市剪影装饰（简化矩形+三角模拟）
    for (let i = 0; i < 12; i++) {
      const bx = i * (W / 12);
      const bh = 0.3 + Math.abs(Math.sin(i * 1.7)) * 0.6;
      s.addShape(pres.shapes.RECTANGLE, {
        x: bx, y: H - bh - 0.3, w: W / 12 + 0.05, h: bh,
        fill: { color: "1A0000" }, line: { type: "none" }
      });
    }
    // 标题
    s.addText(titleLine1, {
      x: 1, y: 2.2, w: W - 2, h: 0.9,
      fontFace: F.cn, fontSize: 30, bold: true, charSpacing: 4,
      color: "FFD700", align: "center", valign: "middle", margin: 0
    });
    if (titleLine2) {
      s.addText(titleLine2, {
        x: 1, y: 3.1, w: W - 2, h: 0.9,
        fontFace: F.cn, fontSize: 30, bold: true, charSpacing: 4,
        color: "FFD700", align: "center", valign: "middle", margin: 0
      });
    }
    if (subtitle) {
      s.addText(subtitle, {
        x: 1, y: 4.2, w: W - 2, h: 0.5,
        fontFace: F.cn, fontSize: 16,
        color: "FFE4A0", align: "center", valign: "middle", margin: 0
      });
    }
    s.addText(date, {
      x: 1, y: 4.8, w: W - 2, h: 0.4,
      fontFace: F.cn, fontSize: 14,
      color: "FFE4A0", align: "center", valign: "middle", margin: 0
    });
  } else {
    // 风格A: 白底 + 渐变飘带
    s.background = { color: "FFFFFF" };
    // Logo占位（左上）
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 0.4, w: 1.5, h: 0.5,
      fill: { color: "F5F5F5" }, line: { color: "E0E0E0", width: 0.5 }
    });
    s.addText("中国电信", {
      x: 0.5, y: 0.4, w: 1.5, h: 0.5,
      fontFace: F.cn, fontSize: 9, color: "888888",
      align: "center", valign: "middle", margin: 0
    });
    // 右上品牌Logo占位
    s.addShape(pres.shapes.RECTANGLE, {
      x: W - 2.0, y: 0.4, w: 1.5, h: 0.5,
      fill: { color: "F5F5F5" }, line: { color: "E0E0E0", width: 0.5 }
    });
    // 标题第一行
    s.addText(titleLine1, {
      x: 0.5, y: 2.3, w: W - 1, h: 0.8,
      fontFace: F.cn, fontSize: 30, bold: true, charSpacing: 3,
      color: "C00000", align: "center", valign: "bottom", margin: 0
    });
    // 标题第二行
    if (titleLine2) {
      s.addText(titleLine2, {
        x: 0.5, y: 3.1, w: W - 1, h: 0.9,
        fontFace: F.cn, fontSize: 30, bold: true, charSpacing: 3,
        color: "C00000", align: "center", valign: "top", margin: 0
      });
    }
    // 渐变强调线
    s.addShape(pres.shapes.RECTANGLE, {
      x: W / 2 - 2.5, y: 4.15, w: 5, h: 0.06,
      fill: { type: "gradient", stops: [
        { position: 0, color: "C00000" },
        { position: 50, color: "E04040" },
        { position: 100, color: "FFD700" }
      ], angle: 0 },
      line: { type: "none" }
    });
    // 副标题
    if (subtitle) {
      s.addText(subtitle, {
        x: 0.5, y: 4.4, w: W - 1, h: 0.5,
        fontFace: F.cn, fontSize: 16, color: "888888",
        align: "center", valign: "middle", margin: 0
      });
    }
    // 日期
    s.addText(date, {
      x: 0.5, y: 4.9, w: W - 1, h: 0.4,
      fontFace: F.cn, fontSize: 14, color: "AAAAAA",
      align: "center", valign: "middle", margin: 0
    });
    // 底部红橙黄渐变装饰条
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: H - 0.5, w: W, h: 0.5,
      fill: { type: "gradient", stops: [
        { position: 0, color: "C00000" },
        { position: 50, color: "E04040" },
        { position: 100, color: "FFD700" }
      ], angle: 0 },
      line: { type: "none" }
    });
  }
}
```

## T18 · 座谈会目录（大数字 + 章节标题）

```js
function slideExecutiveTOC(s, { sections, navTitle }) {
  // sections: [{ num: "01", title: "上半年工作复盘", subtitle: "" }, ...]
  s.background = { color: "FFFFFF" };
  if (navTitle) addExecutiveNav(s, "", navTitle);

  const startY = navTitle ? 1.5 : 2.0;
  const rowH = (6.5 - startY) / sections.length;

  sections.forEach((sec, i) => {
    const y = startY + i * rowH;
    const isLeft = i % 2 === 0;
    // 大数字
    s.addText(sec.num, {
      x: isLeft ? 1.2 : W / 2 + 0.5,
      y, w: 2.0, h: rowH * 0.7,
      fontFace: F.en, fontSize: 48, bold: true,
      color: "0070C0", align: "left", valign: "middle", margin: 0
    });
    // 章节标题
    s.addText(sec.title, {
      x: isLeft ? 3.0 : W / 2 + 2.3,
      y: y + rowH * 0.15, w: 3.5, h: rowH * 0.5,
      fontFace: F.cn, fontSize: 18, bold: true,
      color: "1A1A1A", align: "left", valign: "middle", margin: 0
    });
    // 副标题
    if (sec.subtitle) {
      s.addText(sec.subtitle, {
        x: isLeft ? 3.0 : W / 2 + 2.3,
        y: y + rowH * 0.55, w: 3.5, h: rowH * 0.3,
        fontFace: F.cn, fontSize: 12,
        color: "888888", align: "left", valign: "top", margin: 0
      });
    }
    // 分隔线
    if (i < sections.length - 1) {
      s.addShape(pres.shapes.RECTANGLE, {
        x: 0.8, y: y + rowH - 0.02, w: W - 1.6, h: 0.01,
        fill: { color: "E8E8E8" }, line: { type: "none" }
      });
    }
  });
  addExecutiveFooter(s, sections.length, 1);
}
```

## T19 · 结论先行数据页（结论 + 双图表 + 底部判断）

座谈会核心模板：顶部结论区 + 中部双图表区 + 底部正负结论条。

```js
function slideExecutiveData(s, {
  moduleLabel,    // "总体收入（1/5）"
  pageTitle,      // "截至6月收入份额企稳回升"
  conclusion,     // { main: "p 截至6月…", subPoints: ["Ø 判断1…", "Ø 判断2…"] }
  chartLeft,      // { title: "收入份额趋势(%)", type: "line|bar", data: null }
  chartRight,     // { title: "分公司份额变化(PP)", type: "bar", data: null }
  bottomBars      // [{ text: "蚌埠、六安份额提升0.5PP以上", type: "pos" }, { text: "淮北、芜湖份额下降", type: "neg" }]
}) {
  s.background = { color: "FFFFFF" };
  addExecutiveNav(s, moduleLabel, pageTitle);

  const safeY = 0.62;
  const safeH = 7.10 - safeY;

  // === 顶部结论区 h≈1.4" ===
  const conclY = safeY;
  const conclH = 1.35;
  // 核心结论
  s.addText(conclusion.main, {
    x: 0.5, y: conclY, w: W - 1, h: 0.45,
    fontFace: F.cn, fontSize: 12, bold: true,
    color: "1A1A1A", align: "left", valign: "top", margin: 0
  });
  // 子判断
  if (conclusion.subPoints && conclusion.subPoints.length > 0) {
    const subText = conclusion.subPoints.join("\n");
    s.addText(subText, {
      x: 0.8, y: conclY + 0.5, w: W - 1.3, h: 0.8,
      fontFace: F.cn, fontSize: 11,
      color: "444444", align: "left", valign: "top", margin: 0, lineSpacingMultiple: 1.3
    });
  }

  // === 中部双图表区 ===
  const chartY = conclY + conclH + 0.1;
  const chartH = safeH - conclH - 0.1 - 0.7; // 0.7 留给底部结论条
  const chartW = (W - 1.2 - 0.3) / 2;

  // 左图
  s.addText(chartLeft.title || "", {
    x: 0.5, y: chartY, w: chartW, h: 0.3,
    fontFace: F.cn, fontSize: 10, bold: true,
    color: "555555", align: "left", valign: "middle", margin: 0
  });
  // 左图占位框
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: chartY + 0.32, w: chartW, h: chartH - 0.32,
    fill: { color: "FAFAFA" }, line: { color: "E8E8E8", width: 0.5 }
  });
  s.addText("[图表：" + (chartLeft.title || "") + "]", {
    x: 0.5, y: chartY + 0.32, w: chartW, h: chartH - 0.32,
    fontFace: F.cn, fontSize: 10, color: "AAAAAA",
    align: "center", valign: "middle", margin: 0
  });

  // 右图
  const rightX = 0.5 + chartW + 0.3;
  s.addText(chartRight.title || "", {
    x: rightX, y: chartY, w: chartW, h: 0.3,
    fontFace: F.cn, fontSize: 10, bold: true,
    color: "555555", align: "left", valign: "middle", margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: rightX, y: chartY + 0.32, w: chartW, h: chartH - 0.32,
    fill: { color: "FAFAFA" }, line: { color: "E8E8E8", width: 0.5 }
  });
  s.addText("[图表：" + (chartRight.title || "") + "]", {
    x: rightX, y: chartY + 0.32, w: chartW, h: chartH - 0.32,
    fontFace: F.cn, fontSize: 10, color: "AAAAAA",
    align: "center", valign: "middle", margin: 0
  });

  // === 底部正负结论条 h≈0.6" ===
  const barY = safeY + safeH - 0.5;
  if (bottomBars && bottomBars.length > 0) {
    const barW = (W - 1.0 - (bottomBars.length - 1) * 0.2) / bottomBars.length;
    bottomBars.forEach((bar, i) => {
      const bx = 0.5 + i * (barW + 0.2);
      const color = bar.type === "neg" ? "C00000" : (bar.type === "pos" ? "0070C0" : "70B040");
      // 左侧竖条
      s.addShape(pres.shapes.RECTANGLE, {
        x: bx, y: barY, w: 0.06, h: 0.45,
        fill: { color: color }, line: { type: "none" }
      });
      s.addText(bar.text, {
        x: bx + 0.12, y: barY, w: barW - 0.12, h: 0.45,
        fontFace: F.cn, fontSize: 10, bold: true,
        color: color, align: "left", valign: "middle", margin: 0
      });
    });
  }

  addExecutiveFooter(s, 1, 1);
}
```

## T20 · 分公司画像 2×2 网格页

座谈会标志性模板：每页4个分公司画像卡片，每卡含趋势图+明细表+一句话结论。

```js
function slideExecutiveProfile(s, {
  moduleLabel,   // "净计费收入（2/4）"
  pageTitle,     // "分公司画像（1/4）"
  profiles       // [{ name: "芜湖", conclusion: "增幅5.1%（全省第1）", change: "2.8PP", changeType: "pos", focus1: "关注重点产品…", focus2: "关注细分市场…", tableData: [["融合","1.0"],["单品","0.9"],["专线","0.1"]] }]
}) {
  s.background = { color: "FFFFFF" };
  addExecutiveNav(s, moduleLabel, pageTitle);

  const safeY = 0.62;
  const safeH = 7.10 - safeY;
  const gapX = 0.3, gapY = 0.2;
  const cardW = (W - 1.0 - gapX) / 2;
  const cardH = (safeH - gapY - 0.5) / 2; // 0.5留给底部汇总

  profiles.forEach((p, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const cx = 0.5 + col * (cardW + gapX);
    const cy = safeY + row * (cardH + gapY);

    // 卡片背景
    s.addShape(pres.shapes.RECTANGLE, {
      x: cx, y: cy, w: cardW, h: cardH,
      fill: { color: "FFFFFF" },
      line: { color: "E0E0E0", width: 0.75 },
      rectRadius: 0.05
    });

    // 公司名称
    s.addText(p.name, {
      x: cx + 0.15, y: cy + 0.08, w: cardW * 0.35, h: 0.35,
      fontFace: F.cn, fontSize: 13, bold: true,
      color: "1A1A1A", align: "left", valign: "middle", margin: 0
    });
    // 增幅排名（蓝/红）
    const rankColor = p.changeType === "pos" ? "0070C0" : "C00000";
    s.addText(p.conclusion + "  ", {
      x: cx + cardW * 0.35, y: cy + 0.08, w: cardW * 0.6, h: 0.35,
      fontFace: F.cn, fontSize: 10, bold: true,
      color: rankColor, align: "right", valign: "middle", margin: 0
    });

    // 结论行
    s.addText("p " + p.conclusion, {
      x: cx + 0.15, y: cy + 0.45, w: cardW - 0.3, h: 0.35,
      fontFace: F.cn, fontSize: 10, bold: true,
      color: "333333", align: "left", valign: "top", margin: 0
    });

    // 关注点
    if (p.focus1) {
      s.addText("• " + p.focus1, {
        x: cx + 0.2, y: cy + 0.8, w: cardW - 0.35, h: 0.3,
        fontFace: F.cn, fontSize: 9,
        color: "666666", align: "left", valign: "top", margin: 0
      });
    }
    if (p.focus2) {
      s.addText("• " + p.focus2, {
        x: cx + 0.2, y: cy + 1.1, w: cardW - 0.35, h: 0.3,
        fontFace: F.cn, fontSize: 9,
        color: "666666", align: "left", valign: "top", margin: 0
      });
    }

    // 趋势图占位区
    const chartAreaY = cy + 1.45;
    const chartAreaH = cardH * 0.35;
    s.addText("逐月收入规模（亿元）", {
      x: cx + 0.15, y: chartAreaY, w: cardW - 0.3, h: 0.22,
      fontFace: F.cn, fontSize: 8, color: "999999",
      align: "left", valign: "middle", margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: cx + 0.15, y: chartAreaY + 0.22, w: cardW - 0.3, h: chartAreaH,
      fill: { color: "FAFAFA" }, line: { color: "EEEEEE", width: 0.5 }
    });

    // 迷你明细表
    if (p.tableData && p.tableData.length > 0) {
      const tblY = chartAreaY + chartAreaH + 0.28;
      const tblH = cardH - (tblY - cy) - 0.1;
      // 表头
      s.addText("套餐/产品", {
        x: cx + 0.15, y: tblY, w: cardW * 0.55, h: 0.25,
        fontFace: F.cn, fontSize: 8, bold: true,
        color: "888888", align: "left", valign: "middle", margin: 0
      });
      s.addText("对增幅贡献(PP)", {
        x: cx + 0.15 + cardW * 0.55, y: tblY, w: cardW * 0.3, h: 0.25,
        fontFace: F.cn, fontSize: 8, bold: true,
        color: "888888", align: "right", valign: "middle", margin: 0
      });
      // 数据行
      p.tableData.forEach((row, ri) => {
        const ry = tblY + 0.25 + ri * 0.22;
        if (ry + 0.22 > cy + cardH - 0.05) return; // 防溢出
        s.addText(row[0], {
          x: cx + 0.15, y: ry, w: cardW * 0.55, h: 0.22,
          fontFace: F.cn, fontSize: 8,
          color: "555555", align: "left", valign: "middle", margin: 0
        });
        const val = parseFloat(row[1]);
        const valColor = val < 0 ? "C00000" : (val > 1 ? "0070C0" : "333333");
        s.addText(row[1], {
          x: cx + 0.15 + cardW * 0.55, y: ry, w: cardW * 0.3, h: 0.22,
          fontFace: F.en, fontSize: 8, bold: true,
          color: valColor, align: "right", valign: "middle", margin: 0
        });
      });
    }
  });

  addExecutiveFooter(s, 1, 1);
}
```

## T21 · 三组纵向分栏页（县公司/区域中心分组）

```js
function slideExecutiveThreeGroup(s, {
  moduleLabel,   // "总体收入（5/5）"
  pageTitle,     // "区域中心收入增幅"
  groups,        // [{ name: "县公司1组", chartTitle: "单位：%", conclusions: ["Ø 结论1…","Ø 结论2…"] }, ...]
  summary        // "全省28个县公司主营收入正增长…"
}) {
  s.background = { color: "FFFFFF" };
  addExecutiveNav(s, moduleLabel, pageTitle);

  const safeY = 0.62;
  const safeH = 7.10 - safeY;
  const gap = 0.3;
  const colW = (W - 1.0 - gap * 2) / 3;
  const chartH = safeH * 0.55;
  const conclH = safeH * 0.25;
  const summH = safeH * 0.15;

  groups.forEach((grp, i) => {
    const gx = 0.5 + i * (colW + gap);

    // 组标题
    s.addText(grp.name, {
      x: gx, y: safeY, w: colW, h: 0.35,
      fontFace: F.cn, fontSize: 12, bold: true,
      color: "0070C0", align: "center", valign: "middle", margin: 0
    });
    // 蓝色下划线
    s.addShape(pres.shapes.RECTANGLE, {
      x: gx + colW / 2 - 1.0, y: safeY + 0.36, w: 2.0, h: 0.03,
      fill: { color: "0070C0" }, line: { type: "none" }
    });

    // 图表占位
    const chartY = safeY + 0.45;
    s.addText(grp.chartTitle || "", {
      x: gx, y: chartY, w: colW, h: 0.22,
      fontFace: F.cn, fontSize: 8, color: "999999",
      align: "right", valign: "middle", margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: gx, y: chartY + 0.22, w: colW, h: chartH - 0.22,
      fill: { color: "FAFAFA" }, line: { color: "E8E8E8", width: 0.5 }
    });
    s.addText("[柱状图：" + grp.name + "]", {
      x: gx, y: chartY + 0.22, w: colW, h: chartH - 0.22,
      fontFace: F.cn, fontSize: 10, color: "AAAAAA",
      align: "center", valign: "middle", margin: 0
    });

    // 结论区
    const conclY = safeY + 0.45 + chartH + 0.15;
    if (grp.conclusions) {
      const conclText = grp.conclusions.join("\n");
      s.addText(conclText, {
        x: gx + 0.05, y: conclY, w: colW - 0.1, h: conclH,
        fontFace: F.cn, fontSize: 10,
        color: "444444", align: "left", valign: "top", margin: 0,
        lineSpacingMultiple: 1.3
      });
    }
  });

  // 底部汇总结论条
  const summY = safeY + safeH - summH;
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: summY, w: W - 1, h: summH - 0.1,
    fill: { color: "F0F4FA" },
    line: { color: "C0D0E0", width: 0.5 },
    rectRadius: 0.04
  });
  s.addText(summary, {
    x: 0.65, y: summY, w: W - 1.3, h: summH - 0.1,
    fontFace: F.cn, fontSize: 10, bold: true,
    color: "333333", align: "left", valign: "middle", margin: 0
  });

  addExecutiveFooter(s, 1, 1);
}
```

## T22 · 多面板仪表盘页（KPI行 + 主图表 + 三关注）

```js
function slideExecutiveDashboard(s, {
  moduleLabel,   // "重点市场（1/4）"
  pageTitle,     // "城市市场"
  kpis,          // [{ value: "56.6亿", label: "净计费规模", sub: "25年规模" }, ...]
  chartMain,     // { title: "城市市场逐月净计费收入趋势（亿元）", type: "line" }
  attentions,    // [{ title: "关注一：增速持续收窄", text: "城市市场净计费增速持续收窄…" }, ...]
  overviewCards  // [{ label: "融合收入增幅", value: "-0.4%" }, ...] — 概况卡片
}) {
  s.background = { color: "FFFFFF" };
  addExecutiveNav(s, moduleLabel, pageTitle);

  const safeY = 0.62;
  const safeH = 7.10 - safeY;

  // === 概况卡片行 h≈0.8" ===
  if (overviewCards && overviewCards.length > 0) {
    const ovCardW = (W - 1.0 - (overviewCards.length - 1) * 0.15) / overviewCards.length;
    overviewCards.forEach((oc, i) => {
      const ox = 0.5 + i * (ovCardW + 0.15);
      s.addShape(pres.shapes.RECTANGLE, {
        x: ox, y: safeY, w: ovCardW, h: 0.75,
        fill: { color: "F8FAFC" }, line: { color: "D0DCE8", width: 0.5 },
        rectRadius: 0.04
      });
      s.addText(oc.value, {
        x: ox + 0.1, y: safeY + 0.05, w: ovCardW - 0.2, h: 0.4,
        fontFace: F.en, fontSize: 18, bold: true,
        color: (oc.value || "").startsWith("-") ? "C00000" : "0070C0",
        align: "left", valign: "middle", margin: 0
      });
      s.addText(oc.label, {
        x: ox + 0.1, y: safeY + 0.42, w: ovCardW - 0.2, h: 0.25,
        fontFace: F.cn, fontSize: 9, color: "888888",
        align: "left", valign: "middle", margin: 0
      });
    });
  }

  // === KPI卡片行 h≈0.9" ===
  const kpiY = safeY + (overviewCards ? 0.85 : 0);
  const kpiH = 0.9;
  if (kpis && kpis.length > 0) {
    const kpiW = (W - 1.0 - (kpis.length - 1) * 0.2) / kpis.length;
    kpis.forEach((k, i) => {
      const kx = 0.5 + i * (kpiW + 0.2);
      s.addShape(pres.shapes.RECTANGLE, {
        x: kx, y: kpiY, w: kpiW, h: kpiH,
        fill: { color: "FFFFFF" }, line: { color: "E0E0E0", width: 0.75 },
        rectRadius: 0.04
      });
      s.addText(k.value, {
        x: kx + 0.1, y: kpiY + 0.08, w: kpiW - 0.2, h: 0.42,
        fontFace: F.en, fontSize: 20, bold: true,
        color: (k.value || "").includes("-") ? "C00000" : "0070C0",
        align: "center", valign: "middle", margin: 0
      });
      s.addText(k.label, {
        x: kx + 0.1, y: kpiY + 0.5, w: kpiW - 0.2, h: 0.25,
        fontFace: F.cn, fontSize: 9, color: "888888",
        align: "center", valign: "middle", margin: 0
      });
      if (k.sub) {
        s.addText(k.sub, {
          x: kx + 0.1, y: kpiY + 0.68, w: kpiW - 0.2, h: 0.18,
          fontFace: F.cn, fontSize: 8, color: "BBBBBB",
          align: "center", valign: "middle", margin: 0
        });
      }
    });
  }

  // === 主图表区 ===
  const chartY = kpiY + (kpis ? kpiH + 0.15 : 0);
  const chartH = (attentions ? safeH * 0.32 : safeH - (chartY - safeY) - 0.1);
  if (chartMain) {
    s.addText(chartMain.title || "", {
      x: 0.5, y: chartY, w: W - 1, h: 0.28,
      fontFace: F.cn, fontSize: 10, bold: true,
      color: "555555", align: "left", valign: "middle", margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: chartY + 0.3, w: W - 1, h: chartH - 0.3,
      fill: { color: "FAFAFA" }, line: { color: "E8E8E8", width: 0.5 }
    });
    s.addText("[图表：" + (chartMain.title || "") + "]", {
      x: 0.5, y: chartY + 0.3, w: W - 1, h: chartH - 0.3,
      fontFace: F.cn, fontSize: 10, color: "AAAAAA",
      align: "center", valign: "middle", margin: 0
    });
  }

  // === 底部三关注区 ===
  if (attentions && attentions.length > 0) {
    const attY = chartY + chartH + 0.1;
    const attW = (W - 1.0 - (attentions.length - 1) * 0.2) / attentions.length;
    attentions.forEach((att, i) => {
      const ax = 0.5 + i * (attW + 0.2);
      // 左侧蓝色竖条
      s.addShape(pres.shapes.RECTANGLE, {
        x: ax, y: attY, w: 0.05, h: safeH - (attY - safeY) - 0.05,
        fill: { color: "0070C0" }, line: { type: "none" }
      });
      s.addText(att.title, {
        x: ax + 0.12, y: attY, w: attW - 0.17, h: 0.3,
        fontFace: F.cn, fontSize: 10, bold: true,
        color: "0070C0", align: "left", valign: "top", margin: 0
      });
      s.addText(att.text, {
        x: ax + 0.12, y: attY + 0.32, w: attW - 0.17, h: safeH - (attY - safeY) - 0.37,
        fontFace: F.cn, fontSize: 9,
        color: "555555", align: "left", valign: "top", margin: 0,
        lineSpacingMultiple: 1.3
      });
    });
  }

  addExecutiveFooter(s, 1, 1);
}
```

## T23 · 四象限矩阵页

```js
function slideExecutiveMatrix(s, {
  moduleLabel,   // "上半年复盘（4/4）"
  pageTitle,     // "分公司基础和产数收入完成分布"
  xAxisLabel,    // "基础完成进度(%)"
  yAxisLabel,    // "产数完成进度(%)"
  threshold,     // { x: 50, y: 50 } — 象限分界值
  quadrants,     // [{ id: "Ⅰ", label: "基础、产数均达时序", pos: "top-right" }, ...]
  conclusion     // "基础、产数均需关注：铜陵 马鞍山 宿州"
}) {
  s.background = { color: "FFFFFF" };
  addExecutiveNav(s, moduleLabel, pageTitle);

  const safeY = 0.62;
  const safeH = 7.10 - safeY;
  const matrixY = safeY + 0.3;
  const matrixH = safeH * 0.72;
  const matrixX0 = 1.2; // 留出Y轴标签
  const matrixW = W - 1.0 - matrixX0;

  // 象限背景色
  const halfW = matrixW / 2;
  const halfH = matrixH / 2;
  // 右上 Ⅰ（双达）— 淡绿
  s.addShape(pres.shapes.RECTANGLE, {
    x: matrixX0 + halfW, y: matrixY, w: halfW, h: halfH,
    fill: { color: "F0F8F0" }, line: { type: "none" }
  });
  // 左上 Ⅳ（基础未达/产数达）— 淡蓝
  s.addShape(pres.shapes.RECTANGLE, {
    x: matrixX0, y: matrixY, w: halfW, h: halfH,
    fill: { color: "F0F4FA" }, line: { type: "none" }
  });
  // 右下 Ⅱ（基础达/产数未达）— 淡黄
  s.addShape(pres.shapes.RECTANGLE, {
    x: matrixX0 + halfW, y: matrixY + halfH, w: halfW, h: halfH,
    fill: { color: "FFFBF0" }, line: { type: "none" }
  });
  // 左下 Ⅲ（双未达）— 淡红
  s.addShape(pres.shapes.RECTANGLE, {
    x: matrixX0, y: matrixY + halfH, w: halfW, h: halfH,
    fill: { color: "FFF5F5" }, line: { type: "none" }
  });

  // 象限标签
  if (quadrants) {
    quadrants.forEach(q => {
      let qx, qy, align;
      switch (q.pos) {
        case "top-left": qx = matrixX0 + 0.1; qy = matrixY + 0.05; align = "left"; break;
        case "top-right": qx = matrixX0 + halfW + 0.1; qy = matrixY + 0.05; align = "left"; break;
        case "bottom-left": qx = matrixX0 + 0.1; qy = matrixY + halfH + 0.05; align = "left"; break;
        case "bottom-right": qx = matrixX0 + halfW + 0.1; qy = matrixY + halfH + 0.05; align = "left"; break;
      }
      s.addText(q.id + "象限：" + q.label, {
        x: qx, y: qy, w: halfW - 0.2, h: 0.3,
        fontFace: F.cn, fontSize: 9, bold: true,
        color: "666666", align: align, valign: "top", margin: 0
      });
    });
  }

  // 十字分界线
  s.addShape(pres.shapes.RECTANGLE, {
    x: matrixX0, y: matrixY + halfH, w: matrixW, h: 0.015,
    fill: { color: "CCCCCC" }, line: { type: "none" }
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: matrixX0 + halfW, y: matrixY, w: 0.015, h: matrixH,
    fill: { color: "CCCCCC" }, line: { type: "none" }
  });

  // 轴标签
  s.addText(yAxisLabel, {
    x: 0.3, y: matrixY, w: 0.8, h: matrixH,
    fontFace: F.cn, fontSize: 9, color: "888888",
    align: "center", valign: "middle", margin: 0
  });
  s.addText(xAxisLabel, {
    x: matrixX0, y: matrixY + matrixH + 0.05, w: matrixW, h: 0.25,
    fontFace: F.cn, fontSize: 9, color: "888888",
    align: "center", valign: "middle", margin: 0
  });

  // 结论
  if (conclusion) {
    const conclY = matrixY + matrixH + 0.35;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: conclY, w: 0.06, h: 0.4,
      fill: { color: "C00000" }, line: { type: "none" }
    });
    s.addText(conclusion, {
      x: 0.65, y: conclY, w: W - 1.3, h: 0.4,
      fontFace: F.cn, fontSize: 11, bold: true,
      color: "C00000", align: "left", valign: "middle", margin: 0
    });
  }

  addExecutiveFooter(s, 1, 1);
}
```

## T24 · 下半年工作部署页（举措列表 + 优秀实践）

```js
function slideExecutiveAction(s, {
  moduleLabel,   // "1.1 筑牢销售阵型（2/4）"
  pageTitle,     // "全业务营业部分类施策做强四级"
  intro,         // "综合地域经济、收入规模…确保净计费3%增长目标"
  actions,       // [{ num: "举措1", title: "该开的开：…", bullets: ["动作1…", "动作2…"] }, ...]
  bestPractice,  // { title: "优秀实践", company: "宿州分公司", text: "通过分类施策…全省第2", metrics: [{ value: "24%", label: "三类达标占比" }] }
  problemBars    // [{ label: "问题1：责任压实欠缺", text: "…" }, ...]
}) {
  s.background = { color: "FFFFFF" };
  addExecutiveNav(s, moduleLabel, pageTitle);

  const safeY = 0.62;
  const safeH = 7.10 - safeY;

  // 引言
  if (intro) {
    s.addText(intro, {
      x: 0.5, y: safeY, w: W - 1, h: 0.5,
      fontFace: F.cn, fontSize: 11, color: "444444",
      align: "left", valign: "top", margin: 0, lineSpacingMultiple: 1.3
    });
  }

  const actionStartY = safeY + (intro ? 0.6 : 0);
  const actionH = safeH - (actionStartY - safeY) - 0.1;

  // 左侧举措列表（占60%宽度）
  const leftW = (W - 1.0 - 0.3) * 0.6;
  if (actions && actions.length > 0) {
    const actItemH = actionH / actions.length;
    actions.forEach((act, i) => {
      const ay = actionStartY + i * actItemH;
      // 举措标签
      s.addShape(pres.shapes.RECTANGLE, {
        x: 0.5, y: ay, w: 1.3, h: 0.32,
        fill: { color: "0070C0" }, line: { type: "none" },
        rectRadius: 0.04
      });
      s.addText(act.num, {
        x: 0.5, y: ay, w: 1.3, h: 0.32,
        fontFace: F.cn, fontSize: 10, bold: true,
        color: "FFFFFF", align: "center", valign: "middle", margin: 0
      });
      // 举措标题
      s.addText(act.title, {
        x: 1.9, y: ay, w: leftW - 1.3, h: 0.32,
        fontFace: F.cn, fontSize: 11, bold: true,
        color: "0070C0", align: "left", valign: "middle", margin: 0
      });
      // 要点列表
      if (act.bullets && act.bullets.length > 0) {
        const bulletText = act.bullets.map(b => "• " + b).join("\n");
        s.addText(bulletText, {
          x: 1.9, y: ay + 0.35, w: leftW - 1.3, h: actItemH - 0.4,
          fontFace: F.cn, fontSize: 10,
          color: "555555", align: "left", valign: "top", margin: 0,
          lineSpacingMultiple: 1.25
        });
      }
      // 分隔线
      if (i < actions.length - 1) {
        s.addShape(pres.shapes.RECTANGLE, {
          x: 0.5, y: ay + actItemH - 0.02, w: leftW + 0.3, h: 0.01,
          fill: { color: "EEEEEE" }, line: { type: "none" }
        });
      }
    });
  }

  // 右侧优秀实践（占40%宽度）
  const rightX = 0.5 + leftW + 0.3;
  const rightW = W - 1.0 - leftW - 0.3;
  if (bestPractice) {
    s.addShape(pres.shapes.RECTANGLE, {
      x: rightX, y: actionStartY, w: rightW, h: actionH * 0.6,
      fill: { color: "F8FAFC" }, line: { color: "C0D0E8", width: 0.75 },
      rectRadius: 0.04
    });
    // 优秀实践标签
    s.addShape(pres.shapes.RECTANGLE, {
      x: rightX, y: actionStartY, w: rightW, h: 0.35,
      fill: { color: "70B040" }, line: { type: "none" },
      rectRadius: 0.04
    });
    s.addText("优秀实践  " + (bestPractice.company || ""), {
      x: rightX + 0.1, y: actionStartY, w: rightW - 0.2, h: 0.35,
      fontFace: F.cn, fontSize: 10, bold: true,
      color: "FFFFFF", align: "left", valign: "middle", margin: 0
    });
    // 实践描述
    s.addText(bestPractice.text, {
      x: rightX + 0.12, y: actionStartY + 0.42, w: rightW - 0.24, h: actionH * 0.6 - 0.7,
      fontFace: F.cn, fontSize: 9,
      color: "555555", align: "left", valign: "top", margin: 0,
      lineSpacingMultiple: 1.3
    });
    // 关键指标
    if (bestPractice.metrics) {
      const mY = actionStartY + actionH * 0.6 - 0.55;
      bestPractice.metrics.forEach((m, i) => {
        const mx = rightX + 0.12 + i * ((rightW - 0.24) / bestPractice.metrics.length);
        const mw = (rightW - 0.24) / bestPractice.metrics.length - 0.1;
        s.addText(m.value, {
          x: mx, y: mY, w: mw, h: 0.3,
          fontFace: F.en, fontSize: 16, bold: true,
          color: "70B040", align: "left", valign: "middle", margin: 0
        });
        s.addText(m.label, {
          x: mx, y: mY + 0.28, w: mw, h: 0.2,
          fontFace: F.cn, fontSize: 8, color: "999999",
          align: "left", valign: "middle", margin: 0
        });
      });
    }
  }

  // 右下问题区
  if (problemBars && problemBars.length > 0) {
    const probY = actionStartY + actionH * 0.62;
    const probH = actionH * 0.38;
    problemBars.forEach((pb, i) => {
      const py = probY + i * (probH / problemBars.length);
      s.addShape(pres.shapes.RECTANGLE, {
        x: rightX, y: py, w: 0.05, h: (probH / problemBars.length) - 0.08,
        fill: { color: "C00000" }, line: { type: "none" }
      });
      s.addText(pb.label + " " + (pb.text || ""), {
        x: rightX + 0.12, y: py, w: rightW - 0.17, h: (probH / problemBars.length) - 0.08,
        fontFace: F.cn, fontSize: 9,
        color: "666666", align: "left", valign: "top", margin: 0,
        lineSpacingMultiple: 1.2
      });
    });
  }

  addExecutiveFooter(s, 1, 1);
}
```

---

## 电信风格适配说明

使用 `assets/telecom-boilerplate.js` 时，以下模板行为自动适配：

| 模板元素 | 通用风格 | 电信风格（自动） |
|---------|---------|----------------|
| 顶部导航 | 主色条 h=0.5" | 深红通栏 h=0.52" + 红金渐变线 |
| 页面标题 | 金色左边栏 + 灰色分割线 | 红色竖条 + 红金渐变线 |
| 页脚 | 灰色底栏 | 深红横幅 + 白字 |
| 卡片阴影 | 标准8blur | 轻阴影5blur |
| 安全区域 | y=1.85~7.1 | y=0.55~7.05 |

### 电信风格额外 helper

`telecom-boilerplate.js` 提供以下额外函数，可在任何模板中使用：

- `drawTelecomCard(slide, x, y, w, h, opts)` — 电信风格卡片（圆角浅粉填充 + 标题栏）
- `fmtNumber(text, withBg)` — 数字目标格式化（红色加粗 + 可选黄底）
- `addTelecomTitleLine(slide, y)` — 红金渐变装饰线
- `makeTelecomShadow()` — 电信风格轻阴影

### 内容模式与模板映射

电信内容模式（见 `content-patterns.md`）与 T1-T16 模板的对应关系：

| 内容模式 | 首选模板 | 说明 |
|---------|---------|------|
| 架构总视图 | 自定义单页 | 不使用T1-T16，纯代码生成 |
| 三栏精要 | T7 | 三卡片行 |
| 宣贯蓝图 | T1+T2+T3+T7+T15 | 多页组合 |
| 经营分析通报 | T1+T13+T10+T9+T15 | KPI+表格+图表 |
| 商机诊断分析 | 自定义三栏 | 非对称布局 |
| 总结收尾 | T15 | 三栏总结+底部横幅 |
| 工具问题对比 | 自定义三栏VS | 绿红对比+差距标签 |
| 风险管控案例 | T6+T8 | 对比+矩阵 |

## 使用方式

每个模板是一个 `function slideX(s, { ... })`。在生成脚本中：

```js
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";

slideCover(pres.addSlide(), { title: "...", subtitle: "...", author: "...", affiliation: "...", date: "..." });
slideTOC(pres.addSlide(), { sections: [...] });
slideSectionBreak(pres.addSlide(), { num: 1, title: "...", subtitle: "...", navIdx: 0 });
slideConcept(pres.addSlide(), { title: "...", subtitle: "...", navIdx: 0, page: 4, definition: "...", points: [...] });
slideThanks(pres.addSlide(), { mainText: "Thank You", secondary: "Q & A", contact: "..." });

pres.writeFile({ fileName: "out.pptx" });
```

---

## T25-T34 · 图形布局模板 (v7.1)

> 以下10种模板使用 `assets/graphic-layouts.js` 引擎，全部基于 pptxgenjs 原生形状，PPT中完全可编辑。
> 与 T1-T24 不同，这些模板不是 `function slideX(s, {...})` 形式，而是通过 graphic-layouts 引擎调用。
> 使用前需引入：`const gl = require('./graphic-layouts.js'); const layouts = gl.create(pres);`

### 引入方式

```javascript
const pptxgen = require("pptxgenjs");
const gl = require("./graphic-layouts.js");
const pres = new pptxgen();
const layouts = gl.create(pres);
// 使用示例：
// layouts.drawTimeline(slide, 0.5, 2.0, 12.3, 4.5, milestones, { theme: 'telecom-red' });
```

### 模板速查

| 模板 | 函数名 | 适用场景 | 内容数量 |
|------|--------|---------|---------|
| T25 时间轴 | `drawTimeline` | 历程、阶段、里程碑 | 3-8节点 |
| T26 流程箭头 | `drawProcessFlow` | 业务流程、处理步骤 | 2-7步骤 |
| T27 金字塔 | `drawPyramid` | 需求层次、分层架构 | 3-6层 |
| T28 循环图 | `drawCycle` | PDCA、持续优化、轮转 | 3-6阶段 |
| T29 总分结构 | `drawTree` | 架构总览、组织分解 | 2-6分支 |
| T30 漏斗图 | `drawFunnel` | 转化分析、流失分析 | 3-6阶段 |
| T31 殿堂框架 | `drawTemple` | 基础+支撑+目标 | 2-5柱子 |
| T32 垂直步骤 | `drawVerticalSteps` | 自上而下推进 | 3-7步骤 |
| T33 阶梯进化 | `drawStaircase` | 能力升级、进阶路径 | 3-6级 |
| T34 价值链 | `drawValueChain` | 上下游链、端到端 | 3-6环节 |

### 智能推荐

```javascript
// 自动分析内容，推荐最合适的图形布局
const rec = layouts.recommendLayout(contentItems);
// 返回: { layout: 'timeline', score: 5, reason: '...' }
// 然后调用对应的 draw 函数
```

### 各模板参数格式

详见 `references/graphic-layout-guide.md` 第3节"使用方式"，包含全部10种模板的参数示例。

### 模板选择原则（v7.1更新）

- **从内容逻辑选模板**，而非从审美：时间序列→T25；流程递进→T26；层级→T27；循环→T28；总分→T29
- **优先使用图形布局**：当内容含时间/流程/层级/循环/总分等逻辑结构时，优先使用T25-T34图形布局，而非T1-T16卡片布局
- **卡片布局仍适用于**：并列要点(T7三卡片)、对比分析(T6两栏)、数据展示(T9/T10/T13)、总结(T15)
- 使用 `recommendLayout()` 自动推荐，也可手动指定