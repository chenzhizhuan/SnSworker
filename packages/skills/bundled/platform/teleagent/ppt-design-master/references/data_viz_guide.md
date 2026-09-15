---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '79373c69-2e16-47e3-b672-2fc97d19d417'
  PropagateID: '79373c69-2e16-47e3-b672-2fc97d19d417'
  ReservedCode1: 'b396f885-4743-4df5-87ec-dcda32621604'
  ReservedCode2: 'b396f885-4743-4df5-87ec-dcda32621604'
---

# Data Visualization Guide for Telecom PPT

## Chart Type Selection

| Data Pattern | Chart Type | When to Use |
|-------------|-----------|-------------|
| Process / steps | Flowchart | Sequential workflow, phased execution |
| Comparison / ranking | Bar chart | Category comparison, ranking data |
| Trend / change | Line chart | Time series, growth/decline trends |
| Proportion / composition | Pie / Doughnut | Market share, budget allocation, composition |
| Multi-dimension evaluation | Radar chart | Capability assessment, KPI dimensions |
| Correlation | Scatter (manual) | Two-variable relationship |
| Volume / hierarchy | Area chart | Cumulative trends |

## PptxGenJS Implementation

### Bar Chart (addChart)

```javascript
slide.addChart(pres.charts.BAR, [
  { name: "Revenue", labels: ["Q1","Q2","Q3","Q4"], values: [120,150,180,210] },
  { name: "Cost", labels: ["Q1","Q2","Q3","Q4"], values: [80,90,95,100] }
], {
  x: 0.5, y: 1.3, w: 9.0, h: 3.8,
  barDir: "col",        // vertical bars; "bar" for horizontal
  barGapWidthPct: 80,
  chartColors: ["C8102E", "005AAA", "0066CC", "F29400"],
  showValue: true,
  valueFontSize: 8,
  catAxisLabelFontSize: 9,
  valAxisLabelFontSize: 8,
  fontFace: "Microsoft YaHei"
});
```

### Line Chart (addChart)

```javascript
slide.addChart(pres.charts.LINE, [
  { name: "Growth Rate", labels: ["Jan","Feb","Mar","Apr","May","Jun"], values: [5,8,12,15,18,22] }
], {
  x: 0.5, y: 1.3, w: 9.0, h: 3.8,
  lineDataSymbol: "circle",
  lineDataSymbolSize: 6,
  chartColors: ["C8102E"],
  showValue: true,
  valueFontSize: 8,
  catAxisLabelFontSize: 9,
  valAxisLabelFontSize: 8,
  fontFace: "Microsoft YaHei"
});
```

### Pie / Doughnut Chart (addChart)

```javascript
slide.addChart(pres.charts.PIE, [
  { name: "Share", labels: ["Product A","Product B","Product C","Others"], values: [45,25,20,10] }
], {
  x: 1.5, y: 1.3, w: 7.0, h: 3.8,
  showPercent: true,
  showTitle: false,
  chartColors: ["C8102E", "005AAA", "0066CC", "F29400", "FFCC00"],
  dataLabelFontSize: 10,
  fontFace: "Microsoft YaHei"
});
```

### Radar Chart (manual — addShape + addText)

PptxGenJS does not natively support radar charts. Build manually:

```javascript
// Draw concentric polygons for grid rings (3-5 levels)
// Draw axis lines from center to each vertex
// Plot data polygon using addShape(FREEFORM) or line segments
// Label each axis with addText
```

Simplified alternative: use a styled table or multi-bar chart to convey the same multi-dimensional comparison.

### Flowchart (addShape + addText)

```javascript
// Use addFlowNode() + addArrowRight() from component library
addFlowNode(slide, x, y, w, h, "Step Name", { bg: "C8102E" });
addArrowRight(slide, x + w, y + h/2 - 0.1, 0.25, 0.2, "C8102E");
```

## Brand Color Palette for Charts

```javascript
const chartColors = [
  "C8102E",  // primary red — first data series
  "005AAA",  // brand blue — second series
  "0066CC",  // accent blue — third series
  "F29400",  // orange — fourth series
  "FFCC00",  // yellow — fifth series
  "009688",  // green — sixth series
  "8B0000",  // dark red — accent
  "6A1B9A"  // purple — accent
];
```

## Chart Design Standards

- **Font**: Microsoft YaHei, all labels 8-10pt
- **Data labels**: Always show values; key data bold or larger font
- **Bar charts**: Support increment/decrement annotations (arrow + percentage)
- **Consistency**: Same PPT uses same color order for same categories
- **Background**: White or light pink (#FFF5F5) for chart areas
- **Border**: Light gray (#E5E5E5) 0.5pt if needed
- **Title**: Use `addTitleBar()` above chart, not chart's built-in title

> AI生成