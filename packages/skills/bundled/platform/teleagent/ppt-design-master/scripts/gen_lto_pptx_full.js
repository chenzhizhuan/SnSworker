/**
 * 产数项目全流程管理 — 61页可编辑PPT
 * PptxGenJS, LAYOUT_16x9 (10" x 5.625")
 * 每页根据原始PDF布局独立设计
 */
const pptxgen = require("pptxgenjs");
const path = require("path");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "China Telecom";
pres.title = "\u4ea7\u6570\u9879\u76ee\u5168\u6d41\u7a0b\u7ba1\u7406";

// ========== 颜色 ==========
const C = {
  primary: "C8102E",       // 电信品牌红
  accentDark: "8B0000",    // 深红
  accentLight: "FFF0E5",   // 浅橙暖色
  text: "333333",          // 正文黑
  textSec: "666666",       // 正文灰
  textLight: "999999",     // 浅灰文字
  borderLight: "E5E5E5",  // 浅灰边框
  cardBg: "F5F5F5",        // 浅灰模块底色
  brandBlue: "005AAA",     // 品牌蓝
  blue: "0066CC",          // 辅助蓝
  blueLight: "E3F2FD",     // 浅蓝
  white: "FFFFFF",
  black: "000000",
  orange: "F29400",        // 渐变橙
  yellow: "FFCC00",        // 渐变黄
  pinkLight: "FFF5F5",     // 浅粉
  grayLight: "F0F0F0",     // 极浅灰
  purpleLight: "F3E8FF",   // 浅紫
  green: "009688",         // 绿色
  greenLight: "E8F5E9",    // 浅绿
  teal: "008080",          // 青绿
};

// ========== 中国电信+5G品牌标识 ==========
function addBrand(slide) {
  const logoPath = path.join(__dirname, "china_telecom_logo.png");
  const lw = 1.3, lh = 0.4;
  const lx = 10 - 0.25 - lw, ly = 0.12;
  slide.addImage({ path: logoPath, x: lx, y: ly, w: lw, h: lh, sizing: { type: "contain", w: lw, h: lh } });
}

// ========== 标题栏（通用）==========
function addTitleBar(slide, title, subtitle) {
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.5, w: 0.22, h: 0.22, fill: { color: C.primary } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.76, y: 0.56, w: 0.22, h: 0.22, fill: { color: C.accentDark } });
  slide.addText(title, { x: 1.05, y: 0.45, w: 7.0, h: 0.45, fontSize: 20, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });
  // 红→橙→黄渐变装饰条
  const gradY = 0.98;
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: gradY, w: 2.87, h: 0.03, fill: { color: C.primary } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 3.57, y: gradY, w: 2.87, h: 0.03, fill: { color: C.orange } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 6.44, y: gradY, w: 2.86, h: 0.03, fill: { color: C.yellow } });
  if (subtitle) {
    slide.addText(subtitle, { x: 0.7, y: 1.05, w: 8.6, h: 0.35, fontSize: 10, fontFace: "Microsoft YaHei", color: C.textSec, align: "left", margin: 0, wrap: true });
  }
}

// ========== 底部品牌线 ==========
function addBottomLine(slide, pageNum) {
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.35, w: 10, h: 0.025, fill: { color: C.primary } });
  if (pageNum) {
    slide.addText(String(pageNum), { x: 9.2, y: 5.1, w: 0.5, h: 0.25, fontSize: 9, fontFace: "Microsoft YaHei", color: C.textLight, align: "right", valign: "middle", margin: 0 });
  }
}

// ========== 通用卡片 ==========
function addCard(slide, x, y, w, h, title, body, opts) {
  opts = opts || {};
  const titleBg = opts.titleBg || C.primary;
  const titleColor = opts.titleColor || C.white;
  const borderColor = opts.borderColor || null;
  const lineOpts = borderColor ? { line: { color: borderColor, width: 0.75 } } : {};
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: C.white }, ...lineOpts });
  if (title) {
    slide.addText(title, { x, y, w, h: 0.35, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: titleColor, fill: { color: titleBg }, align: "center", valign: "middle", margin: [0, 4, 0, 4] });
  }
  if (body) {
    const by = title ? y + 0.35 : y;
    const bh = title ? h - 0.35 : h;
    slide.addText(body, { x: x + 0.08, y: by, w: w - 0.16, h: bh, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: opts.align || "left", valign: opts.valign || "top", margin: [4, 4, 4, 4], wrap: true });
  }
}

// ========== 流程箭头节点 ==========
function addFlowNode(slide, x, y, w, h, label, opts) {
  opts = opts || {};
  const bgColor = opts.bg || C.primary;
  const fontColor = opts.color || C.white;
  const fontSize = opts.fontSize || 9;
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: bgColor }, rectRadius: 0.05 });
  slide.addText(label, { x, y, w, h, fontSize, fontFace: "Microsoft YaHei", bold: true, color: fontColor, align: "center", valign: "middle", margin: [2, 4, 2, 4], wrap: true });
}

// ========== 右箭头 ==========
function addArrowRight(slide, x, y, w, h, color) {
  slide.addShape(pres.shapes.RIGHT_ARROW, { x, y, w: w || 0.25, h: h || 0.2, fill: { color: color || C.primary } });
}

// ========== 通用表格 ==========
function makeTable(slide, headers, rows, opts) {
  opts = opts || {};
  var tableData = [headers.map(function(h) { return { text: h, options: { fontSize: opts.headerFontSize || 8, fontFace: "Microsoft YaHei", bold: true, color: C.white, fill: { color: C.primary }, align: "center", valign: "middle", border: { color: C.borderLight, pt: 0.5 } } }; })];
  rows.forEach(function(row, ri) {
    tableData.push(row.map(function(cell, ci) {
      return { text: cell, options: { fontSize: opts.rowFontSize || 7, fontFace: "Microsoft YaHei", color: C.text, fill: { color: ri % 2 === 0 ? C.pinkLight : C.white }, align: ci === 0 ? "center" : "left", valign: "middle", border: { color: C.borderLight, pt: 0.5 }, margin: [2, 4, 2, 4], wrap: true } };
    }));
  });
  slide.addTable(tableData, { x: opts.x || 0.3, y: opts.y || 1.3, w: opts.w || 9.4, colW: opts.colW, rowH: opts.rowH, border: { color: C.borderLight, pt: 0.5 } });
}

// ========== 返回链接（附录页） ==========
function addBackLink(slide) {
  slide.addText("\u8fd4\u56de", { x: 8.8, y: 0.5, w: 0.8, h: 0.35, fontSize: 11, fontFace: "Microsoft YaHei", bold: true, color: C.blue, align: "center", valign: "middle", margin: 0 });
}

// ================================================================
// PAGE 1: 封面
// ================================================================
function page1() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  // 底部渐变丝带装饰（简化为渐变色条）
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 4.7, w: 3.33, h: 0.93, fill: { color: C.yellow }, rectRadius: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 3.33, y: 4.7, w: 3.34, h: 0.93, fill: { color: C.orange }, rectRadius: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 6.67, y: 4.7, w: 3.33, h: 0.93, fill: { color: C.primary }, rectRadius: 0 });
  // 主标题
  s.addText("\u4ea7\u6570\u9879\u76ee\u5168\u6d41\u7a0b\u7ba1\u7406", { x: 0.7, y: 1.8, w: 8.6, h: 1.0, fontSize: 40, fontFace: "Microsoft YaHei", bold: true, color: C.brandBlue, align: "center", valign: "middle", margin: 0 });
  // 副标题
  s.addText("\uff08\u71ce\u539f\u8ba1\u5212\u2014\u5929\u7ffc\u7269\u8054\u73ed\uff09", { x: 0.7, y: 2.8, w: 8.6, h: 0.5, fontSize: 20, fontFace: "Microsoft YaHei", color: C.brandBlue, align: "center", valign: "middle", margin: 0 });
  // 日期
  s.addText("2026\u5e746\u670817\u65e5", { x: 0.7, y: 3.5, w: 8.6, h: 0.4, fontSize: 14, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle", margin: 0 });
}

// ================================================================
// PAGE 2: 产数项目流程（售前/售中/售后三行流程）
// ================================================================
function page2() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "\u4ea7\u6570\u9879\u76ee\u6d41\u7a0b");
  // 三行标签
  const rows = [
    { label: "\u552e\u524d", items: ["\u6807\u524d\u9636\u6bb5", "\u6295\u6807\u7b7e\u7ea6\u9636\u6bb5"], colors: [C.primary, C.orange], output: { text: "\u300a\u5408\u540c\u300b", x: 7.5 } },
    { label: "\u552e\u4e2d", items: ["\u65b9\u6848\u89c4\u5212\u9636\u6bb5", "\u5b9e\u65bd\u9636\u6bb5", "\u9a8c\u6536\u4ea4\u4ed8\u9636\u6bb5"], colors: [C.teal, C.blue, C.green], output: { text: "\u300a\u9a8c\u6536\u62a5\u544a\u300b", x: 7.5 } },
    { label: "\u552e\u540e", items: ["\u8fd0\u8425\u9636\u6bb5"], colors: ["6A1B9A"] }
  ];
  const startY = 1.4;
  rows.forEach((row, ri) => {
    const ry = startY + ri * 1.2;
    // 阶段标签
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: ry, w: 0.7, h: 0.8, fill: { color: C.brandBlue }, rectRadius: 0.05 });
    s.addText(row.label, { x: 0.5, y: ry, w: 0.7, h: 0.8, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
    // 流程节点
    row.items.forEach((item, ii) => {
      const nx = 1.5 + ii * 2.0;
      addFlowNode(s, nx, ry + 0.15, 1.7, 0.5, item, { bg: row.colors[ii] });
      if (ii < row.items.length - 1) addArrowRight(s, nx + 1.7, ry + 0.3, 0.3, 0.2, row.colors[ii]);
    });
    // 输出物
    if (row.output) {
      s.addText(row.output.text, { x: row.output.x, y: ry + 0.2, w: 1.5, h: 0.4, fontSize: 11, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0, border: { color: C.primary, pt: 1, dashType: "dash" } });
    }
  });
  addBottomLine(s, 2);
}

// ================================================================
// PAGE 3: LTO项目全流程视图
// ================================================================
function page3() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "LTO\u9879\u76ee\u5168\u6d41\u7a0b\u89c6\u56fe");
  // 三条纲领
  const goals = [
    { kw: "\u5546\u673a\u7ba1\u7406", desc: "\u505a\u597d\u5546\u673a\u7ba1\u7406\uff0c\u5b9e\u73b0\u201c\u4e94\u65e9\u201d\uff1a\u5546\u673a\u98ce\u9669\u65e9\u5904\u7f6e\uff0c\u81ea\u6709\u80fd\u529b\u65e9\u5361\u4f4d\uff0c\u540e\u5411\u91c7\u8d2d\u65e9\u89c4\u5212\uff0c\u6536\u652f\u6784\u6210\u65e9\u660e\u6670\uff0c\u5efa\u8bbe\u5b9e\u65bd\u65e9\u8ba1\u5212" },
    { kw: "\u9879\u76ee\u7ba1\u7406", desc: "\u505a\u597d\u9879\u76ee\u7ba1\u7406\uff0c\u5b9e\u73b0\u7b7e\u7ea6\u5373\u79bb\u573a\uff1a\u4e1a\u8d22\u878d\u5408\u628a\u5173\uff0c\u63d0\u5347\u81ea\u4e3b\u4ea4\u4ed8\u80fd\u529b\uff0c\u552e\u4e2d\u8fc7\u7a0b\u89c4\u8303\u7ba1\u7406\uff0c\u63d0\u8d28\u63d0\u6548\u63d0\u901f" },
    { kw: "\u8fd0\u8425\u7ba1\u7406", desc: "\u505a\u597d\u8fd0\u8425\u7ba1\u7406\uff0c\u5b9e\u73b0\u4ece\u8fd0\u7ef4\u5230\u8fd0\u8425\u7684\u8f6c\u578b\uff1a\u8fd0\u8425\u7ecf\u7406\u4e3b\u5bfc\uff0c\u5206\u6790\u8fd0\u7ef4\u6570\u636e\uff0c\u6316\u6398\u9700\u6c42\uff0c\u5f15\u5bfc\u4e8c\u6b21\u8425\u9500" }
  ];
  goals.forEach((g, i) => {
    const gy = 1.15 + i * 0.28;
    s.addText([
      { text: "\u25b6 " + g.kw + "\uff1a", options: { fontSize: 9, bold: true, color: C.primary } },
      { text: g.desc, options: { fontSize: 9, color: C.text } }
    ], { x: 0.7, y: gy, w: 8.6, h: 0.26, fontFace: "Microsoft YaHei", valign: "middle", margin: 0, wrap: true });
  });
  // 主流程时间轴
  const nodes = ["\u7ebf\u7d22\u5f55\u5165", "\u5546\u673a\u521b\u5efa", "\u7ec4\u5efa\u56e2\u961f", "\u5546\u673a\u7814\u5224", "\u65b9\u6848\u5236\u5b9a", "\u4e2d\u53f0\u628a\u5173", "\u5e94\u6807\u7b7e\u7ea6", "\u6ee1\u610f\u5ea6\u8bc4\u4ef7", "\u9879\u76ee\u542f\u52a8", "\u9879\u76ee\u91c7\u8d2d", "\u9879\u76ee\u5b9e\u65bd", "\u9879\u76ee\u9a8c\u6536", "\u9a7b\u573a\u8fd0\u8425"];
  const subItems = [
    "\u00b7\u5ba2\u6237\u8d70\u8bbf\n\u00b7\u884c\u4e1a\u6d1e\u5bdf\n\u00b7\u7f51\u7edc\u722c\u866b",
    "\u00b7\u5546\u673a\u5ba1\u6838\n\u00b7\u5546\u673a\u5206\u7ea7\n\u00b7\u5236\u5b9a\u7b2c\u4e00\u8d23\u4efb\u4eba",
    "\u00b7\u5ba2\u6237\u7ecf\u7406\n\u00b7\u4ea7\u54c1\u7ecf\u7406\n\u00b7\u65b9\u6848\u7ecf\u7406\n\u00b7\u6280\u672f\u7ecf\u7406\n\u00b7\u9879\u76ee\u7ecf\u7406",
    "\u00b7\u5546\u673a\u89e3\u6784\n\u00b7\u878d\u4e91\u878d\u6570\u878d\u9a7b\u573a\n\u00b7\u6846\u67b6\u90e8\u7f72",
    "\u00b7\u878d\u4e91\u878d\u6570\n\u00b7\u80fd\u529b\u5361\u4f4d\n\u00b7\u65b9\u6848\u8bc4\u5ba1\n\u00b7\u65b9\u6848\u4f18\u5316\n\u00b7\u65b9\u6848\u89e3\u6784",
    "\u00b7\u65b9\u6848\u628a\u5173\n\u00b7\u5e94\u878d\u5c3d\u878d\n\u00b7\u8d44\u6e90\u786e\u8ba4\n\u00b7\u5546\u4e1a\u6a21\u5f0f\n\u00b7\u5229\u6da6\u6bdb\u5229\u7387\n\u00b7\u91c7\u8d2d\u51b3\u7b56\u524d\u7f6e\n\u00b7\u95ed\u73af\u7ba1\u7406",
    "\u00b7\u6807\u524d\u6c9f\u901a\n\u00b7\u5e94\u6295\u5c3d\u6295\n\u00b7\u5f03\u6807\u5ba1\u6279\n\u00b7\u4e22\u6807\u590d\u76d8\n\u00b7\u5408\u540c\u7b7e\u7ea6\n\u00b7\u552e\u524d\u552e\u4e2d\u4ea4\u5e95",
    "\u00b7\u652f\u6491\u6ee1\u610f\u5ea6\n\u00b7\u5173\u8054\u6fc0\u52b1",
    "\u00b7\u4e1a\u52a1\u89e3\u6784\n\u00b7\u5b9e\u65bd\u65b9\u6848\n\u00b7\u8fdb\u5ea6\u8ba1\u5212\n\u00b7\u542f\u52a8\u4f1a\u8bae\n\u00b7\u552e\u4e2d\u56e2\u961f",
    "\u00b7\u91c7\u8d2d\u9700\u6c42\n\u00b7\u91c7\u8d2d\u5b9e\u65bd\n\u00b7\u540e\u5411\u7b7e\u7ea6\n\u00b7\u6846\u67b6\u4e0b\u8ba2\u5355",
    "\u00b7\u878d\u5408\u4ea4\u4ed8\n\u00b7\u53d7\u7406\u5f00\u901a\n\u00b7\u539f\u5b50\u80fd\u529b\u8c03\u7528\u53ca\u4e8c\u5f00\n\u00b7\u5e73\u53f0\u5f00\u53d1\u90e8\u7f72\n\u00b7\u7cfb\u7edf\u96c6\u6210\n\u00b7\u8fc7\u7a0b\u7ba1\u63a7",
    "\u00b7\u9879\u76ee\u521d\u9a8c\n\u00b7\u8bd5\u8fd0\u884c\n\u00b7\u9879\u76ee\u7ec8\u9a8c",
    "\u00b7\u9a7b\u573a\u670d\u52a1\n\u00b7\u8fd0\u7ef4\u4fdd\u969c\n\u00b7\u6570\u636e\u5206\u6790\n\u00b7\u9700\u6c42\u6316\u6398\n\u00b7\u8fd0\u8425\u62d3\u5c55"
  ];
  // 时间轴线
  const tlY = 2.55;
  s.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: tlY, w: 9.4, h: 0.03, fill: { color: C.primary } });
  // 节点
  const nodeW = 0.68;
  const gap = (9.2 - nodeW * 13) / 12;
  nodes.forEach((nd, i) => {
    const nx = 0.4 + i * (nodeW + gap);
    // 圆形节点
    const isRed = i % 2 === 0;
    s.addShape(pres.shapes.OVAL, { x: nx + 0.17, y: tlY - 0.07, w: 0.34, h: 0.34, fill: { color: isRed ? C.primary : C.textSec } });
    s.addText(String(i + 1), { x: nx + 0.17, y: tlY - 0.07, w: 0.34, h: 0.34, fontSize: 7, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
    // 节点名称
    s.addText(nd, { x: nx - 0.05, y: tlY + 0.35, w: nodeW + 0.1, h: 0.35, fontSize: 7, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "top", margin: 0, wrap: true });
    // 子项
    s.addText(subItems[i], { x: nx - 0.05, y: tlY + 0.7, w: nodeW + 0.1, h: 1.6, fontSize: 5, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  });
  // 上方标注
  s.addText("\u4e8c\u6b21\u8425\u9500\u4fc3\u6210\u590d\u8d2d", { x: 1.0, y: 2.2, w: 2.0, h: 0.25, fontSize: 8, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", margin: 0 });
  s.addText("\u9a7b\u573a\u8fd0\u8425\uff0c\u53c2\u4e0e\u5ba2\u6237\u751f\u4ea7\u6d41\u7a0b", { x: 6.5, y: 2.2, w: 2.5, h: 0.25, fontSize: 8, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", margin: 0 });
  // LTO标识
  s.addText("LTO", { x: 4.2, y: 1.95, w: 1.6, h: 0.5, fontSize: 20, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0 });
  addBottomLine(s, 3);
}

// ================================================================
// PAGE 4: LTO管理总体视图（7×5矩阵）
// ================================================================
function page4() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "LTO\u7ba1\u7406\u603b\u4f53\u89c6\u56fe");
  // 表格型矩阵
  const headers = ["\u5546\u673a\u83b7\u53d6", "\u65b9\u6848\u652f\u6491", "\u6295\u6807\u7b7e\u7ea6", "\u9879\u76ee\u542f\u52a8", "\u9879\u76ee\u91c7\u8d2d", "\u5b9e\u65bd\u4ea4\u4ed8", "\u670d\u52a1\u8fd0\u8425"];
  const rows = [
    { label: "\u63a7\u5236\u70b9", items: ["\u5546\u673a\u7814\u5224", "\u65b9\u6848\u89e3\u6784", "\u4e2d\u53f0\u628a\u5173", "\u6807\u524d\u51b3\u7b56", "\u4e1a\u52a1\u89e3\u6784", "\u65b9\u6848\u8bc4\u5ba1", "\u91c7\u8d2d\u7ba1\u7406", "\u9a8c\u6536\u4ea4\u7ef4", "\u8fd0\u7ef4\u8fd0\u8425"] },
    { label: "\u89d2\u8272", items: ["\u5546\u673a\u7ba1\u7406\u5458\n\u5ba2\u6237\u7ecf\u7406\n\u5546\u673a\u7b2c\u4e00\u8d23\u4efb\u4eba", "\u9879\u76ee\u8d1f\u8d23\u4eba\n\u89e3\u51b3\u65b9\u6848\u7ecf\u7406\n\u4ea7\u54c1\u7ecf\u7406\n\u5546\u52a1\u7ecf\u7406", "\u9879\u76ee\u7ecf\u7406\n\u6280\u672f\u4e13\u5bb6\n\u9879\u76ee\u8d22\u52a1\u7ecf\u7406\n\u91c7\u8d2d\u7ecf\u7406\n\u5408\u540c\u89e3\u6790\u4eba\u5458", "\u8fd0\u8425\u7ecf\u7406"] },
    { label: "\u673a\u5236\u4fdd\u969c", items: ["\u5546\u673a\u7ba1\u7406\u529e\u6cd5\n\u6218\u7565\u89e3\u7801\n\u884c\u4e1a\u89e3\u51b3\u65b9\u6848\u6307\u5f15\n\u7b7e\u7ea6\u53ca\u4e22\u6807\u8003\u6838\n\u653f\u4f01\u5ba2\u6237\u9879\u76ee\u6295\u6807\u5de5\u4f5c\u89c4\u8303\u6307\u5f15\nICT\u9879\u76ee\u5168\u6d41\u7a0b\u7ba1\u7406\u529e\u6cd5", "\u539f\u5b50\u80fd\u529b\u8c03\u7528\u89c4\u8303\n\u4e1a\u52a1\u89e3\u6784\u89c4\u8303\n\u4ea7\u6570\u96c6\u91c7\u5bfb\u6e90\n\u4ea7\u6570\u9879\u76ee\u91c7\u8d2d\u7ba1\u7406\u89c4\u8303\n\u77ed\u540d\u5355", "\u4ea7\u54c1\u4ea4\u4ed8\u89c4\u8303\n\u6807\u51c6ICT\u7ba1\u7406\u89c4\u8303\n\u8f6f\u4ef6\u9879\u76ee\u89c4\u8303\n\u4e3b\u5b9e\u534f\u540c\u5de5\u4f5c\u673a\u5236\n\u7701\u4e13\u534f\u540c\u5de5\u4f5c\u673a\u5236\n\u9879\u76ee\u540e\u8bc4\u4f30", "\u552e\u540e\u8fd0\u7ef4\u89c4\u8303\n\u6545\u969c\u7ba1\u7406\u529e\u6cd5\n\u5e73\u53f0\u8fd0\u8425\u89c4\u8303\n\u4e8c\u6b21\u8425\u9500"] },
    { label: "\u80fd\u529b\u8981\u6c42", items: ["\u9886\u5bfc\u80fd\u529b\n\u6c9f\u901a\u534f\u8c03\u80fd\u529b\n\u5206\u6790\u7814\u5224\u80fd\u529b\n\u7edf\u7b79\u8c03\u5ea6\u80fd\u529b\n\u98ce\u9669\u9632\u8303\u80fd\u529b"] },
    { label: "IT\u652f\u6491", items: ["\u6570\u5b57\u5316\u539f\u5b50\u80fd\u529b\u5e73\u53f0\n\u4e94\u5e93\u77e5\u8bc6\u5e73\u53f0\nMSS\u57df / OSS\u57df\n\u4eba\u624d\u4e91\u5e73\u53f0\n1+N+X\n\u76d1\u63a7\u8fd0\u8425\u5e73\u53f0\nBPM\u96c6\u56e2\u653f\u4f01\u5546\u673a\u53ca\u9879\u76ee\u7ba1\u7406\u7cfb\u7edf"] }
  ];
  // 渲染表头
  const colW = 1.2, rowH = 0.55;
  const startX = 1.5, startY = 1.3;
  headers.forEach((h, i) => {
    addFlowNode(s, startX + i * colW, startY, colW - 0.05, rowH, h, { bg: C.primary, fontSize: 8 });
  });
  // 渲染行
  rows.forEach((row, ri) => {
    const ry = startY + (ri + 1) * rowH + 0.05;
    // 行标签
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.4, y: ry, w: 1.0, h: rowH, fill: { color: C.brandBlue }, rectRadius: 0.03 });
    s.addText(row.label, { x: 0.4, y: ry, w: 1.0, h: rowH, fontSize: 8, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 2, wrap: true });
    // 行内容
    const cellText = row.items.join("\n");
    s.addText(cellText, { x: startX, y: ry, w: 7.2, h: rowH, fontSize: 6, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: [2, 4, 2, 4], wrap: true, fill: { color: ri % 2 === 0 ? C.pinkLight : C.white } });
  });
  addBottomLine(s, 4);
}

// ================================================================
// PAGE 5: 电信产数能力体系框架地图
// ================================================================
function page5() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "\u7535\u4fe1\u4ea7\u6570\u80fd\u529b\u4f53\u7cfb\u6846\u67b6\u5730\u56fe");
  // 左侧模块
  const leftX = 0.3, leftW = 1.8;
  // 全流程集成服务体系
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: leftX, y: 1.3, w: leftW, h: 2.8, line: { color: C.borderLight, width: 0.75, dashType: "dash" }, rectRadius: 0.05 });
  s.addText("\u7535\u4fe1\u4ea7\u6570\u80fd\u529b\u4f53\u7cfb", { x: leftX + 0.1, y: 1.35, w: leftW - 0.2, h: 0.3, fontSize: 8, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", margin: 0 });
  s.addText("\u5168\u6d41\u7a0b\u96c6\u6210\u670d\u52a1\u4f53\u7cfb", { x: leftX + 0.1, y: 1.65, w: leftW - 0.2, h: 0.25, fontSize: 7, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", margin: 0 });
  s.addText("\u63d0\u4f9b\u4ece\u89c4\u5212\u5230\u6700\u540e\u8fd0\u8425\u843d\u5730\u7684\u7aef\u5230\u7aef\u7684\u80fd\u529b\u652f\u6491\u4f53\u7cfb\u3002", { x: leftX + 0.1, y: 1.9, w: leftW - 0.2, h: 0.35, fontSize: 6, fontFace: "Microsoft YaHei", color: C.text, align: "center", margin: 0, wrap: true });
  const flowSteps = ["\u54a8\u8be2\u8bbe\u8ba1", "\u4ea4\u4ed8\u5b9e\u65bd", "\u8fd0\u8425\u8fd0\u7ef4", "\u5b89\u5168\u4fdd\u969c"];
  flowSteps.forEach((step, i) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: leftX + 0.2, y: 2.35 + i * 0.42, w: leftW - 0.4, h: 0.35, fill: { color: C.pinkLight }, rectRadius: 0.03 });
    s.addText(step, { x: leftX + 0.2, y: 2.35 + i * 0.42, w: leftW - 0.4, h: 0.35, fontSize: 7, fontFace: "Microsoft YaHei", color: C.primary, align: "center", valign: "middle", margin: 0 });
  });
  // 协同体系
  s.addText("\u534f\u540c\u4f53\u7cfb", { x: leftX + 0.1, y: 4.15, w: leftW - 0.2, h: 0.25, fontSize: 8, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", margin: 0 });
  s.addText("\u96c6\u56e2\u7701\u5e02\u53bf\u56db\u7ea7\u8054\u52a8\n\u56fd\u9645\u5efa\u8fd0\u7ba1\u4f53\u7cfb\u534f\u540c", { x: leftX + 0.1, y: 4.4, w: leftW - 0.2, h: 0.5, fontSize: 6, fontFace: "Microsoft YaHei", color: C.text, align: "center", margin: 0, wrap: true });

  // 中间核心金字塔（4层）
  const midX = 2.3, midW = 5.4;
  const layers = [
    { y: 1.3, h: 0.7, label: "\u884c\u4e1a\u72ec\u6709\u4ea7\u54c1\u80fd\u529b", desc: "\u57fa\u4e8e15\u4e2a\u884c\u4e1a\u7ec6\u5206\u9886\u57df\u6210\u7acb\u76f8\u5e94\u7684BG/\u884c\u4e1a\u516c\u53f8\uff0c\u5efa\u8bbe\u5f62\u6210\u884c\u4e1a\u81ea\u6709\u4ea7\u54c1\u80fd\u529b\u3002", items: "\u653f\u52a1/\u653f\u6cd5\u516c\u5b89/\u536b\u5065/\u5e94\u6025/\u519c\u4e1a\u519c\u6751/\u4f4f\u5efa/\u4ea4\u901a\u7269\u6d41/\u5de5\u4e1a/\u91d1\u878d/\u80fd\u6e90\u5316\u5de5/\u6559\u80b2/\u6587\u5ba3/\u8981\u5ba2/\u6c7d\u8f66/\u4e92\u8054\u7f51..." },
    { y: 2.1, h: 0.7, label: "\u4ea7\u54c1\u5e73\u53f0", desc: "\u6807\u51c6\u5316\u4ea7\u54c1 \u00b7 \u6570\u5b57\u5316\u5e73\u53f0", items: "" },
    { y: 2.9, h: 0.7, label: "\u6280\u672f\u80fd\u529b", desc: "\u5b89\u5168 \u00b7 \u91cf\u5b50 \u00b7 \u5927\u6570\u636e \u00b7 \u4eba\u5de5\u667a\u80fd", items: "" },
    { y: 3.7, h: 0.85, label: "\u57fa\u7840\u8d44\u6e90", desc: "", items: "" }
  ];
  layers.forEach((l, i) => {
    const inset = i * 0.3;
    const lw = midW - inset * 2;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: midX + inset, y: l.y, w: lw, h: l.h, fill: { color: i === 3 ? C.brandBlue : C.primary }, rectRadius: 0.05 });
    s.addText(l.label, { x: midX + inset + 0.1, y: l.y, w: lw - 0.2, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
    if (l.desc) s.addText(l.desc, { x: midX + inset + 0.1, y: l.y + 0.3, w: lw - 0.2, h: 0.3, fontSize: 6, fontFace: "Microsoft YaHei", color: C.white, align: "center", valign: "top", margin: 0, wrap: true });
    if (l.items) s.addText(l.items, { x: midX + inset + 0.1, y: l.y + 0.5, w: lw - 0.2, h: 0.3, fontSize: 5, fontFace: "Microsoft YaHei", color: C.white, align: "center", valign: "top", margin: 0, wrap: true });
  });
  // 基础资源子项
  s.addText("\u7f51\uff1a\u56fa\u79fb\u878d\u5408\u3001\u5929\u5730\u4e00\u4f53\uff0c\u63d0\u4f9b\u57fa\u7840\u8fde\u63a5\u548c\u901a\u4fe1\u529f\u80fd\n\u536b\u661f\u3001\u8bed\u97f3\u3001\u6d88\u606f\u3001\u89c6\u8054\u7f51\u3001\u7ec4\u7f51\u3001\u4e92\u8054\u7f51\u3001\u7269\u8054\u7f51\u30015G", { x: midX + 0.2, y: 4.0, w: 2.2, h: 0.5, fontSize: 5, fontFace: "Microsoft YaHei", color: C.white, align: "left", valign: "top", margin: 0, wrap: true });
  s.addText("\u4e91\uff1a\u5b89\u5168\u53ef\u4fe1\u3001\u4e13\u4eab\u5b9a\u5236\u3001\u4e91\u667a\u878d\u5408\u3001\u5c5e\u5730\u670d\u52a1\n\u5929\u7ffc\u4e91\u3001\u7b97\u529b\u3001\u6570\u636e\u4e2d\u5fc3", { x: midX + 2.7, y: 4.0, w: 2.2, h: 0.5, fontSize: 5, fontFace: "Microsoft YaHei", color: C.white, align: "left", valign: "top", margin: 0, wrap: true });

  // 右侧模块
  const rightX = 8.0, rightW = 1.7;
  const rightMods = [
    { title: "\u80fd\u529b\u5e93", desc: "\u63d0\u4f9b\u7535\u4fe1\u8d44\u8d28\u53ca\u5185\u90e8\u80fd\u529b", items: "\u4e13\u4e1a\u516c\u53f8\u80fd\u529b\n\u4e13\u4e1a\u516c\u53f8\u8d44\u8d28\n\u539f\u5b50\u80fd\u529b\n\u81ea\u6709\u80fd\u529b" },
    { title: "\u77e5\u8bc6\u5e93", desc: "\u63d0\u4f9b\u884c\u4e1a\u6807\u6746\u6848\u4f8b\u9009\u53d6\u539f\u5219\u53ca\u65b9\u6cd5", items: "\u884c\u4e1a\u4e13\u533a\n\u6218\u65b0\u4e13\u533a\n\u5927\u6a21\u578bAI\n\u79fb\u52a8\u7aef" },
    { title: "\u5de5\u4f5c\u673a\u5236", desc: "\u63d0\u4f9b\u8d44\u6e90\u8c03\u7528\u673a\u5236\u6d41\u7a0b\u53ca\u5e73\u53f0\u5de5\u5177", items: "\u5546\u673a\u7ba1\u7406\n\u70b9\u5c06\u53f0\n\u80fd\u529b\u6d3e\u5355\n\u7f3a\u9677\u7ba1\u7406" }
  ];
  rightMods.forEach((mod, i) => {
    const my = 1.3 + i * 1.35;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: rightX, y: my, w: rightW, h: 1.2, line: { color: C.borderLight, width: 0.5 }, rectRadius: 0.05 });
    s.addText(mod.title, { x: rightX + 0.1, y: my + 0.05, w: rightW - 0.2, h: 0.25, fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", margin: 0 });
    s.addText(mod.desc, { x: rightX + 0.1, y: my + 0.3, w: rightW - 0.2, h: 0.25, fontSize: 6, fontFace: "Microsoft YaHei", color: C.textSec, align: "center", margin: 0, wrap: true });
    s.addText(mod.items, { x: rightX + 0.1, y: my + 0.55, w: rightW - 0.2, h: 0.6, fontSize: 6, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "top", margin: 0, wrap: true });
  });
  addBottomLine(s, 5);
}

// ================================================================
// PAGE 6: 售前环节流程
// ================================================================
function page6() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "\u552e\u524d\u73af\u8282\u6d41\u7a0b", "\u5546\u673a\u5168\u91cf\u8986\u76d6\uff0c\u65e0\u5546\u673a\u4e0d\u7b7e\u7ea6\uff0c\u786e\u4fdd\u9879\u76ee\u5168\u7eb3\u7ba1\uff1b\u65b9\u6848\u5168\u89e3\u6784\uff0c\u89e3\u6784\u5fc5\u628a\u5173\uff0c\u786e\u4fdd\u81ea\u6709\u80fd\u529b\u5e94\u7528\u5c3d\u7528\uff0c\u5e94\u878d\u5c3d\u878d\uff1b\u6807\u524d\u51b3\u7b56\u591a\u4f1a\u5408\u4e00\uff0c\u51cf\u5c11\u51b3\u7b56\u8282\u70b9\uff0c\u63d0\u5347\u6548\u7387");
  // 流程图：商机管理→方案编写→应标管理→前向合同签约
  const flowSteps = [
    { label: "\u5546\u673a\u7ba1\u7406", sub: "\u5546\u673a\u7ebf\u7d22\u641c\u96c6\u2192\u7ec4\u5efa\u5546\u673a\u56e2\u961f" },
    { label: "\u65b9\u6848\u7f16\u5199\u4e0e\u4f18\u5316\u3001\u65b9\u6848\u89e3\u6784", sub: "\u89e3\u51b3\u65b9\u6848\u7f16\u5236\u4e0e\u4f18\u5316" },
    { label: "\u5e94\u6807\u7ba1\u7406", sub: "\u552e\u524d\u552e\u4e2d\u5de5\u4f5c\u4ea4\u63a5" },
    { label: "\u524d\u5411\u5408\u540c\u7b7e\u7ea6", sub: "" }
  ];
  const sy = 2.0;
  flowSteps.forEach((step, i) => {
    const sx = 0.5 + i * 2.3;
    addFlowNode(s, sx, sy, 1.9, 0.55, step.label, { bg: C.primary, fontSize: 9 });
    s.addText(step.sub, { x: sx, y: sy + 0.65, w: 1.9, h: 0.5, fontSize: 7, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "top", margin: 0, wrap: true });
    if (i < flowSteps.length - 1) addArrowRight(s, sx + 1.9, sy + 0.15, 0.4, 0.25, C.primary);
  });
  // 判断分支
  const branches = [
    { label: "\u5546\u673a\u7814\u5224", x: 1.6, y: 3.3 },
    { label: "POC\u6d4b\u8bd5", x: 3.5, y: 3.3 },
    { label: "\u6b63\u5f0f\u6295\u6807", x: 5.4, y: 3.3 }
  ];
  branches.forEach(b => {
    s.addShape(pres.shapes.DIAMOND, { x: b.x, y: b.y, w: 1.0, h: 0.7, fill: { color: C.orange } });
    s.addText(b.label, { x: b.x, y: b.y + 0.1, w: 1.0, h: 0.5, fontSize: 7, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0, wrap: true });
  });
  s.addText("\u5426\u2192\u8bc4\u5ba1\u901a\u8fc7\u2192\u662f", { x: 1.6, y: 4.1, w: 1.0, h: 0.25, fontSize: 7, fontFace: "Microsoft YaHei", color: C.textSec, align: "center", margin: 0 });
  s.addText("\u5426\u2192\u5426\u9700\u8981\u2192\u662f", { x: 3.5, y: 4.1, w: 1.0, h: 0.25, fontSize: 7, fontFace: "Microsoft YaHei", color: C.textSec, align: "center", margin: 0 });
  s.addText("\u5426\u2192\u9700\u8981\u2192\u662f", { x: 5.4, y: 4.1, w: 1.0, h: 0.25, fontSize: 7, fontFace: "Microsoft YaHei", color: C.textSec, align: "center", margin: 0 });
  addBottomLine(s, 6);
}

// ================================================================
// PAGE 7: 商机阶段——如何提升商机储备率
// ================================================================
function page7() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "1.1 \u5546\u673a\u9636\u6bb5\u2014\u2014\u5982\u4f55\u63d0\u5347\u5546\u673a\u50a8\u5907\u7387", "\u5546\u673a\u83b7\u53d6\u8def\u5f84\u53ca\u63aa\u65bd");
  // 5个途径卡片
  const paths = [
    { title: "\u91cd\u5927\u653f\u7b56\u4fe1\u606f\u89e3\u8bfb", items: "\u00b7\u884c\u4e1a\u6d1e\u5bdf\u4fe1\u606f\n\u00b7\u6781\u901f\u5148\u950b\u57ce\u5e02\n\u00b7\u6570\u5b57\u5b5a\u751f\u57ce\u5e02\n\u00b7\u4ea7\u4e1a\u96c6\u7fa4" },
    { title: "\u91cd\u70b9\u5ba2\u6237\u6df1\u5ea6\u6316\u6398", items: "\u00b7\u5b58\u91cf\u9879\u76ee\u4e8c\u6b21\u5546\u673a\n\u00b7\u5173\u6ce8\u975e\u516c\u5f00\u5e02\u573a\n\u00b7\u7eb5\u5411\u4e00\u4f53\u91cd\u70b9\u5ba2\u6237\n\u00b7\u5ba2\u52e4\u6e05\u5355" },
    { title: "\u751f\u6001\u4f19\u4f34\u4fe1\u606f\u5171\u4eab", items: "\u00b7\u6708\u5ea6\u5546\u673a\u534f\u540c\u4f1a\n\u00b7\u91cd\u5927\u5546\u673a\u5bf9\u63a5\u4eba" },
    { title: "\u5916\u90e8\u4fe1\u606f\u5206\u6790\u83b7\u53d6", items: "\u00b7\u5916\u90e8AI\u9884\u6d4b\u5546\u673a\n\u00b7\u5386\u53f2\u91c7\u8d2d\u6570\u636e\u5efa\u6a21\n\u00b7\u5546\u673a\u6001\u52bf\u611f\u77e5\u5e73\u53f0\uff08\u6df1\u5733\u7535\u4fe1\uff09" },
    { title: "\u5168\u5458\u5546\u673a\u7ebf\u7d22\u6536\u96c6", items: "\u00b7\u4e13\u9879\u6fc0\u52b1\u914d\u7f6e\n\u00b7\u7eb3\u5165\u52b3\u52a8\u7ade\u8d5b" }
  ];
  const cw = 1.65, ch = 2.5, startX = 0.4, startY = 1.4;
  paths.forEach((p, i) => {
    const cx = startX + i * (cw + 0.15);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx, y: startY, w: cw, h: ch, fill: { color: C.pinkLight }, rectRadius: 0.05 });
    s.addText(p.title, { x: cx + 0.1, y: startY + 0.1, w: cw - 0.2, h: 0.4, fontSize: 8, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0, wrap: true });
    s.addText(p.items, { x: cx + 0.1, y: startY + 0.55, w: cw - 0.2, h: ch - 0.65, fontSize: 6, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  });
  // 底部三个关键词
  const bottomKws = ["\u5546\u673a\u6316\u6398", "\u5ba2\u6237\u89e6\u8fbe", "\u751f\u6001\u7ba1\u7406"];
  bottomKws.forEach((kw, i) => {
    const bx = 1.5 + i * 2.8;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: bx, y: 4.3, w: 1.8, h: 0.35, fill: { color: C.primary }, rectRadius: 0.03 });
    s.addText(kw, { x: bx, y: 4.3, w: 1.8, h: 0.35, fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
  });
  addBottomLine(s, 7);
}

// ================================================================
// PAGE 8: 商机阶段——商机研判评估
// ================================================================
function page8() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "1.1 \u5546\u673a\u9636\u6bb5\u2014\u2014\u5546\u673a\u7814\u5224\u8bc4\u4f30", "\u201c\u516d\u95ee\u56db\u660e\u201d\u5546\u673a\u8bc4\u4f30\u6cd5");
  // 六问
  const questions = [
    { title: "\u5ba2\u6237\u4e1a\u52a1\u9700\u6c42/\u75db\u70b9/\u89c4\u5212/\u8feb\u5207\u9700\u6c42", result: "\u5224\u5b9a\u662f\u5426\u4e3a\u6709\u6548\u5546\u673a\n\u5236\u5b9a\u9879\u76ee\u63a8\u8fdb\u8ba1\u5212" },
    { title: "\u5ba2\u6237\u9879\u76ee\u9884\u7b97/\u8d44\u91d1\u6765\u6e90/\u8d44\u91d1\u4e13\u7528\u6027/\u63d0\u4f9b\u670d\u52a1\u65b9\u5f0f", result: "\u660e\u8d44\u6e90\u9700\u6c42\uff0c\u63d0\u524d\u5907\u8d27\n\u660e\u5546\u52a1\u6a21\u5f0f\uff0c\u63d0\u524d\u8d70\u6d41\u7a0b" },
    { title: "\u5173\u952e\u51b3\u7b56\u90e8\u95e8/\u53c2\u4e0e\u90e8\u95e8/\u51b3\u7b56\u94fe\u4fe1\u606f/\u9879\u76ee\u5f15\u5bfc\u65b9\u5f0f", result: "\u660e\u5408\u4f5c\u4f19\u4f34\uff0c\u63d0\u524d\u6c9f\u901a\u5408\u4f5c\n\u786e\u8ba4\u5408\u4f5c\u610f\u5411" },
    { title: "\u9879\u76ee\u4ea4\u4ed8\u8981\u6c42/\u5b9e\u65bd\u8ba1\u5212/\u5b9e\u65bd\u73af\u8282/\u5339\u914d\u8d44\u6e90", result: "\u660e\u4ea4\u4ed8\u8981\u6c42\uff0c\u63d0\u524d\u5012\u6392\u9879\u76ee\u8fdb\u5ea6\u8ba1\u5212" },
    { title: "\u6f5c\u5728\u7ade\u4e89\u5bf9\u624b/\u5168\u65b9\u4f4d\u4e86\u89e3\u7ade\u4e89\u5bf9\u624b", result: "\u77e5\u5df1\u77e5\u5f7c\uff0c\u767e\u6218\u4e0d\u6b86\n\u5efa\u7acb\u4f18\u52bf\u3001\u6392\u9664\u4e89\u8bae" },
    { title: "\u5df2\u4f7f\u7528\u54ea\u4e9b\u4ea7\u54c1\u548c\u670d\u52a1/\u63d0\u4f9b\u65b9\u662f\u4f55\u516c\u53f8/\u662f\u5426\u5408\u4f5c\u4f19\u4f34", result: "\u4e3a\u653b\u575a\u63d0\u4f9b\u51b3\u7b56\u4f9d\u636e\n\u8f93\u51fa\u5546\u4e1a\u6a21\u5f0f\n\u8f93\u51fa\u6982\u7b97\u6210\u672c\n\u786e\u5b9a\u9879\u76ee\u8fd0\u4f5c\u65b9\u5f0f\u53ca\u76ee\u6807" }
  ];
  const startY = 1.3, rowH = 0.65;
  questions.forEach((q, i) => {
    const ry = startY + i * rowH;
    // 序号
    s.addShape(pres.shapes.OVAL, { x: 0.4, y: ry + 0.05, w: 0.35, h: 0.35, fill: { color: C.primary } });
    s.addText(String(i + 1), { x: 0.4, y: ry + 0.05, w: 0.35, h: 0.35, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
    // 问题
    s.addText(q.title, { x: 0.85, y: ry, w: 4.5, h: rowH, fontSize: 7, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "middle", margin: 0, wrap: true });
    // 结果
    s.addText(q.result, { x: 5.5, y: ry, w: 3.8, h: rowH, fontSize: 7, fontFace: "Microsoft YaHei", color: C.primary, align: "left", valign: "middle", margin: 0, wrap: true });
  });
  addBottomLine(s, 8);
}

// ================================================================
// PAGE 9: 商机阶段——商机分级管理
// ================================================================
function page9() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "1.1 \u5546\u673a\u9636\u6bb5\u2014\u2014\u5546\u673a\u5206\u7ea7\u7ba1\u7406", "\u5546\u673a\u7ba1\u7406\u4e09\u5927\u5173\u952e\u4efb\u52a1\uff1a\u6269\u5927\u5546\u673a\u50a8\u5907 \u00b7 \u5b9e\u65bd\u5206\u7ea7\u7eb3\u7ba1 \u00b7 \u805a\u7126\u4e22\u5f03\u6807\u590d\u76d8");
  // 分级表格
  const levels = [
    { amount: "\u2265500\u4e07", person: "\u5e02\u516c\u53f8\u603b\u7ecf\u7406", color: C.primary },
    { amount: "[100\u4e07,500\u4e07)", person: "\u5e02\u516c\u53f8\u526f\u603b\u7ecf\u7406", color: C.accentDark },
    { amount: "[50\u4e07,100\u4e07)", person: "\u653f\u4f01\u90e8\u603b\u7ecf\u7406", color: C.orange },
    { amount: "\u226450\u4e07", person: "\u5e02\u516c\u53f8\u6216\u533a\u5206\u516c\u53f8\u653f\u4f01\u90e8\u7ecf\u7406", color: C.textSec }
  ];
  // 四步法
  const steps = [
    { num: "\u2460", title: "\u7ec4\u5efa\u56e2\u961f", desc: "\u5546\u673a\u8fdb\u884c\u603b\u4f53\u7814\u5224\uff0c\u7ec4\u7ec7\u5546\u673a\u8bc4\u5ba1\uff0c\u7ec4\u5efa\u5546\u673a\u56e2\u961f\uff0c\u5b9e\u65bd\u519b\u56e2\u5316\u56e2\u961f\u4f5c\u6218" },
    { num: "\u2461", title: "\u76ef\u62dc\u8bbf", desc: "\u9488\u5bf9\u7eb3\u7ba1\u5546\u673a\u7ec4\u7ec7\u5bf9\u5e94\u62dc\u8bbf\uff0c\u6df1\u5165\u6d1e\u5bdf\u9879\u76ee\u60c5\u51b5\uff0c\u9501\u5b9a\u5ba2\u6237\u9700\u6c42\u53ca\u75db\u70b9" },
    { num: "\u2462", title: "\u76ef\u65b9\u6848", desc: "\u6839\u636e\u5ba2\u6237\u4ea4\u6d41\u9700\u6c42\u60c5\u51b5\u9488\u5bf9\u6027\u8f93\u51fa\u5b9a\u5236\u5316\u89e3\u51b3\u65b9\u6848\uff0c\u4e0e\u5ba2\u6237\u9762\u5bf9\u9762\u65b9\u6848\u4ea4\u6d41" },
    { num: "\u2463", title: "\u76ef\u8c03\u5ea6", desc: "\u6bcf\u5468\u7ec4\u7ec7\u5546\u673a\u5206\u6790\u4f1a\u548c\u63a8\u8fdb\u4f1a\uff0c\u786e\u5b9a\u7a81\u7834\u7b56\u7565\uff0c\u63a8\u8fdb\u9879\u76ee\u653b\u575a" }
  ];
  const sy = 1.4;
  // 左侧：分级表
  s.addText("\u5546\u673a\u9884\u6d4b\u91d1\u989d", { x: 0.5, y: sy, w: 1.8, h: 0.3, fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0 });
  s.addText("\u5546\u673a\u7b2c\u4e00\u8d23\u4efb\u4eba", { x: 2.4, y: sy, w: 2.5, h: 0.3, fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0 });
  levels.forEach((lv, i) => {
    const ly = sy + 0.35 + i * 0.4;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: ly, w: 1.8, h: 0.35, fill: { color: lv.color }, rectRadius: 0.03 });
    s.addText(lv.amount, { x: 0.5, y: ly, w: 1.8, h: 0.35, fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
    s.addText(lv.person, { x: 2.4, y: ly, w: 2.5, h: 0.35, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle", margin: 0, fill: { color: i % 2 === 0 ? C.pinkLight : C.white } });
  });
  // 右侧：四盯法
  steps.forEach((step, i) => {
    const stepY = sy + i * 0.9;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.2, y: stepY, w: 0.4, h: 0.4, fill: { color: C.primary }, rectRadius: 0.03 });
    s.addText(step.num, { x: 5.2, y: stepY, w: 0.4, h: 0.4, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
    s.addText(step.title, { x: 5.7, y: stepY, w: 1.5, h: 0.4, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });
    s.addText(step.desc, { x: 5.7, y: stepY + 0.4, w: 3.5, h: 0.45, fontSize: 7, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  });
  addBottomLine(s, 9);
}

// ================================================================
// PAGE 10: 方案阶段——AUSER原则
// ================================================================
function page10() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "2.1 \u65b9\u6848\u9636\u6bb5\u2014\u2014\u8bbe\u8ba1\u539f\u5219\uff1a\u5ba2\u6237\u89c6\u89d2\u7684AUSER\u539f\u5219");
  const principles = [
    { letter: "A", title: "\u5148\u8fdb\u6027", en: "Advanced", desc: "\u91c7\u7528\u5f53\u4e0b\u6d41\u884c\u7684\u6280\u672f\u6807\u51c6\u548c\u6846\u67b6\u8fdb\u884c\u89e3\u51b3\u65b9\u6848\u8bbe\u8ba1\uff0c\u6280\u672f\u65b9\u6848\u5177\u6709\u4e00\u5b9a\u5148\u8fdb\u6027" },
    { letter: "U", title: "\u5b9e\u7528\u6027", en: "Usable", desc: "\u89e3\u51b3\u65b9\u6848\u5e94\u56f4\u7ed5\u5ba2\u6237\u9700\u6c42\u8fdb\u884c\u8bbe\u8ba1\uff0c\u5207\u5b9e\u89e3\u51b3\u5ba2\u6237\u75db\u70b9" },
    { letter: "S", title: "\u53ef\u5ef6\u5c55\u6027", en: "Extensibility", desc: "\u9879\u76ee\u53ef\u5212\u5206\u9636\u6bb5\u63a8\u8fdb\uff0c\u6839\u636e\u5b9e\u9645\u9700\u8981\u4e00\u671f\u53ea\u5b9e\u73b0\u90e8\u5206\u529f\u80fd\uff0c\u7559\u6709\u63a5\u53e3\uff0c\u4e3a\u4e8c\u671f\u505a\u51c6\u5907" },
    { letter: "E", title: "\u7ecf\u6d4e\u6027", en: "Economical", desc: "\u8003\u8651\u9879\u76ee\u9884\u7b97\u9650\u5236\uff0c\u4ee5\u6700\u5408\u9002\u7684\u6280\u672f\u89e3\u51b3\u65b9\u6848\u8fdb\u884c\u8bbe\u8ba1" },
    { letter: "R", title: "\u53ef\u9760\u6027", en: "Reliable", desc: "\u89e3\u51b3\u65b9\u6848\u771f\u5b9e\u53ef\u9760\uff0c\u80fd\u591f\u7ecf\u5f97\u8d77\u6d4b\u8bd5\uff0c\u907f\u514d\u5f15\u8d77\u4e0d\u5fc5\u8981\u7684\u9879\u76ee\u98ce\u9669" }
  ];
  const startY = 1.3;
  principles.forEach((p, i) => {
    const py = startY + i * 0.75;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: py, w: 0.65, h: 0.55, fill: { color: C.primary }, rectRadius: 0.05 });
    s.addText(p.letter, { x: 0.5, y: py, w: 0.65, h: 0.55, fontSize: 22, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
    s.addText(p.title, { x: 1.3, y: py, w: 1.5, h: 0.3, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });
    s.addText("(" + p.en + ")", { x: 1.3, y: py + 0.25, w: 2.0, h: 0.25, fontSize: 8, fontFace: "Microsoft YaHei", color: C.textSec, align: "left", valign: "middle", margin: 0 });
    s.addText(p.desc, { x: 3.2, y: py, w: 6.0, h: 0.55, fontSize: 9, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "middle", margin: 0, wrap: true });
  });
  addBottomLine(s, 10);
}

// ================================================================
// PAGE 11: 方案阶段——电信视角
// ================================================================
function page11() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "2.1 \u65b9\u6848\u9636\u6bb5\u2014\u2014\u8bbe\u8ba1\u539f\u5219\uff1a\u7535\u4fe1\u89c6\u89d2");
  const items = [
    { letter: "A", title: "\u5173\u6ce8\u957f\u77ed\u671f\u6548\u76ca", desc: "\u89e3\u51b3\u65b9\u6848\u8bbe\u8ba1\u65f6\uff0c\u5c3d\u53ef\u80fd\u5c06\u80fd\u7ed9\u4f01\u4e1a\u5e26\u6765\u8f83\u591a\u6548\u76ca\u7684\u4ea7\u54c1\u7eb3\u5165\u8bbe\u8ba1\u65b9\u6848\uff0c\u4e0e\u5ba2\u6237\u9700\u6c42\u5339\u914d\u8d77\u6765" },
    { letter: "B", title: "\u7b26\u5408\u96c6\u56e2\u5021\u5bfc\u65b9\u5411", desc: "\u90e8\u5206\u4ea7\u54c1\u8bbe\u8ba1\u65f6\uff0c\u5728\u591a\u79cd\u5907\u9009\u65b9\u6848\u5747\u53ef\u9009\u7684\u60c5\u51b5\u4e0b\uff0c\u5e94\u4f18\u5148\u9009\u7528\u7b26\u5408\u96c6\u56e2\u5021\u5bfc\u65b9\u5411\u7684\u4ea7\u54c1" },
    { letter: "C", title: "\u7a81\u51fa\u7535\u4fe1\u4f18\u52bf", desc: "\u89e3\u51b3\u65b9\u6848\u8bbe\u8ba1\u65f6\uff0c\u5e94\u5145\u5206\u4f53\u73b0\u4e2d\u56fd\u7535\u4fe1\u5728\u901a\u4fe1\u3001\u7f51\u7edc\u3001\u96c6\u6210\u7b49\u65b9\u9762\u7684\u6838\u5fc3\u4f18\u52bf\uff0c\u8d62\u5f97\u5ba2\u6237\u4fe1\u8d56\u611f" }
  ];
  const sy = 1.5;
  items.forEach((item, i) => {
    const iy = sy + i * 1.2;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: iy, w: 9.0, h: 1.0, fill: { color: i % 2 === 0 ? C.pinkLight : C.grayLight }, rectRadius: 0.05 });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.7, y: iy + 0.15, w: 0.7, h: 0.7, fill: { color: C.primary }, rectRadius: 0.05 });
    s.addText(item.letter, { x: 0.7, y: iy + 0.15, w: 0.7, h: 0.7, fontSize: 26, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
    s.addText(item.title, { x: 1.6, y: iy + 0.1, w: 3.0, h: 0.4, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });
    s.addText(item.desc, { x: 1.6, y: iy + 0.5, w: 7.5, h: 0.45, fontSize: 9, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  });
  addBottomLine(s, 11);
}

// ================================================================
// PAGE 12: SAR公式 - 场景化方案描述
// ================================================================
function page12() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "2.1 \u65b9\u6848\u9636\u6bb5\u2014\u2014\u89e3\u51b3\u65b9\u6848\u8be6\u7ec6\u8bbe\u8ba1", "\u5de5\u5177\uff1aSAR\u516c\u5f0f - \u573a\u666f\u5316\u65b9\u6848\u63cf\u8ff0");
  // SAR三列
  s.addText("S", { x: 1.5, y: 1.4, w: 1.5, h: 0.8, fontSize: 36, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0 });
  s.addText("A", { x: 4.0, y: 1.4, w: 1.5, h: 0.8, fontSize: 36, fontFace: "Microsoft YaHei", bold: true, color: C.orange, align: "center", valign: "middle", margin: 0 });
  s.addText("R", { x: 6.5, y: 1.4, w: 1.5, h: 0.8, fontSize: 36, fontFace: "Microsoft YaHei", bold: true, color: C.brandBlue, align: "center", valign: "middle", margin: 0 });
  s.addText("\u573a\u666f Situation", { x: 1.2, y: 2.2, w: 2.1, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", margin: 0 });
  s.addText("\u884c\u4e3a Action", { x: 3.7, y: 2.2, w: 2.1, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.orange, align: "center", margin: 0 });
  s.addText("\u4ef7\u503c Result", { x: 6.2, y: 2.2, w: 2.1, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.brandBlue, align: "center", margin: 0 });
  // SAR表格
  const tableRows = [
    ["\u7ef4\u5ea6", "\u63cf\u8ff0", "\u8bc1\u636e"],
    ["\u573a\u666f S", "\u80fd\u529b1", "\u4ef7\u503c R"],
    ["\u573a\u666f S", "\u80fd\u529b2", "\u4ef7\u503c R"]
  ];
  const tableData = tableRows.map((row, ri) => row.map((cell, ci) => ({
    text: cell,
    options: { fontSize: 9, fontFace: "Microsoft YaHei", bold: ri === 0, color: ri === 0 ? C.white : C.text, fill: { color: ri === 0 ? C.primary : (ci === 0 ? C.pinkLight : C.white) }, align: "center", valign: "middle", border: { color: C.borderLight, pt: 0.5 } }
  })));
  s.addTable(tableData, { x: 0.7, y: 2.8, w: 8.6, colW: [2.87, 2.87, 2.87], rowH: [0.4, 0.6, 0.6] });
  addBottomLine(s, 12);
}

// ================================================================
// PAGE 13: 场景化方案描述
// ================================================================
function page13() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "\u573a\u666f\u5316\u65b9\u6848\u63cf\u8ff0", "\u6587\u4e0d\u5982\u6570\uff0c\u6570\u4e0d\u5982\u8868\uff0c\u8868\u4e0d\u5982\u56fe");
  // 大字提示
  s.addText("\u6587\u4e0d\u5982\u6570\uff0c\u6570\u4e0d\u5982\u8868\uff0c\u8868\u4e0d\u5982\u56fe", { x: 1.0, y: 2.5, w: 8.0, h: 1.0, fontSize: 28, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0 });
  addBottomLine(s, 13);
}

// ================================================================
// PAGE 14: 技术方案评审（中台把关）要点
// ================================================================
function page14() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "1.2 \u65b9\u6848\u9636\u6bb5\u2014\u2014\u6280\u672f\u65b9\u6848\u8bc4\u5ba1\uff08\u4e2d\u53f0\u628a\u5173\uff09\u8981\u70b9");
  s.addText("\u7ec4\u7ec7\u6280\u672f\u65b9\u6848\u8bc4\u5ba1\u3002\u5546\u673a\u56e2\u961f\u7684\u6280\u672f\u4e13\u5bb6\u7275\u5934\uff0c\u5546\u673a\u56e2\u961f\u5176\u4ed6\u6210\u5458\u53ca\u91c7\u8d2d\u3001\u8d22\u52a1\u3001\u4e91\u7f51\u53d1\u3001\u4e91\u7f51\u8fd0\u7b49\u76f8\u5173\u90e8\u95e8\u6d3e\u4eba\u53c2\u4e0e\uff0c\u5bf9\u6574\u4f53\u65b9\u6848\u8fdb\u884c\u628a\u5173\u3002", { x: 0.7, y: 1.15, w: 8.6, h: 0.35, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  // 4步流程
  const steps = [
    { title: "\u7ec4\u5efa\u8bc4\u5ba1\u7ec4", items: "\u00fc \u4e91\u4e2d\u53f0\uff08\u7ec4\u7ec7\uff09\n\u00fc \u6280\u672f\u4e13\u5bb6\n\u00fc \u5546\u673a\u56e2\u961f\n\u00fc \u91c7\u8d2d\n\u00fc \u8d22\u52a1\n\u00fc \u4e91\u7f51\u53d1\n\u00fc \u4e91\u7f51\u8fd0" },
    { title: "\u65b9\u6848\u6c47\u62a5", items: "n \u5ba2\u6237\u7ecf\u7406\u4ecb\u7ecd\uff1a\u9879\u76ee\u7684\u80cc\u666f\u60c5\u51b5\u3001\u5efa\u8bbe\u65b9\u6848\u7684\u60f3\u6cd5\u548c\u9700\u6c42\u3001\u9879\u76ee\u516c\u5173\u8fc7\u7a0b\u7b49\nn \u89e3\u51b3\u65b9\u6848\u7ecf\u7406\u4ecb\u7ecd\uff1a\u5177\u4f53\u7684\u65b9\u6848\u8bbe\u8ba1\u3001\u76f8\u5173\u5173\u952e\u70b9" },
    { title: "\u6280\u672f\u8bc4\u5ba1", items: "n \u5173\u952e\u6280\u672f\u53ef\u884c\u6027\u8bc4\u5ba1\nn \u81ea\u6709\u80fd\u529b\u5e94\u7528\u628a\u5173\nn \u5b8c\u5168\u5f15\u5165\u7b2c\u4e09\u65b9\u4ea7\u54c1\u548c\u80fd\u529b\uff0c\u9700\u8bf4\u660e\u5177\u4f53\u539f\u56e0\uff0c\u8981\u91cd\u70b9\u628a\u5173\nn \u80fd\u81ea\u7814\u7684\u7528\u81ea\u7814\uff0c\u4f46\u8981\u7ba1\u63a7\u628a\u5173\u7814\u53d1\u8d39\u7528\nn \u52a0\u5927\u5bf9\u7ecf\u8fc7\u4e8c\u6b21\u5f00\u53d1\u540e\u80fd\u6ee1\u8db3\u5ba2\u6237\u9700\u6c42\u7684\u539f\u5b50\u80fd\u529b\u7684\u91c7\u8d2d" },
    { title: "\u8bc4\u5ba1\u7ed3\u679c\u8f93\u51fa", items: "n \u8bc4\u5ba1\u7ed3\u679c\nn \u628a\u5173\u8981\u70b9" }
  ];
  steps.forEach((step, i) => {
    const sx = 0.4 + i * 2.35;
    const sw = 2.15;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: sx, y: 1.65, w: sw, h: 3.4, fill: { color: C.white }, line: { color: C.borderLight, width: 0.5 }, rectRadius: 0.05 });
    s.addText(step.title, { x: sx, y: 1.7, w: sw, h: 0.35, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.white, fill: { color: C.primary }, align: "center", valign: "middle", margin: 0 });
    s.addText(step.items, { x: sx + 0.1, y: 2.1, w: sw - 0.2, h: 2.85, fontSize: 7, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: [4, 4, 4, 4], wrap: true });
  });
  addBottomLine(s, 14);
}

// ================================================================
// PAGE 15: 应标签约阶段——多会合一提效率
// ================================================================
function page15() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "1.3 \u5e94\u6807\u7b7e\u7ea6\u9636\u6bb5\u2014\u2014\u591a\u4f1a\u5408\u4e00\u63d0\u6548\u7387");
  // 决策链
  s.addText("\u51b3\u7b56 \u2192 \u51b3\u7b56 \u2192 \u51b3\u7b56 \u2192 \u51b3\u7b56", { x: 0.7, y: 1.3, w: 8.6, h: 0.3, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0 });
  const keyPoints = [
    "\u6807\u524d\u51b3\u7b56\u76ee\u7684\uff1a\u51cf\u5c11\u51b3\u7b56\u8282\u70b9\uff0c\u63d0\u5347\u6548\u7387",
    "\u7275\u5934\u4eba\uff1a\u9879\u76ee\u8d1f\u8d23\u4eba\uff08\u5546\u673a\u7b2c\u4e00\u8d23\u4efb\u4eba\uff09",
    "\u53c2\u4e0e\u90e8\u95e8\uff1a\u552e\u524d\u3001\u552e\u4e2d\u3001\u8fd0\u7ef4\u3001\u8d22\u52a1\u3001\u6cd5\u52a1\u3001\u91c7\u8d2d\u7b49",
    "\u51b3\u7b56\u5185\u5bb9\uff1a\u4e1a\u52a1\u6a21\u5f0f\u3001\u5229\u6da6\u6536\u652f\u60c5\u51b5\u3001\u5efa\u8bbe\u65b9\u6848\u3001\u4e03\u878d\u80fd\u529b\u4f7f\u7528\u60c5\u51b5\u3001\u539f\u5b50\u80fd\u529b\u4e8c\u5f00\u3001\u91c7\u8d2d\u4e8b\u9879\u51b3\u7b56",
    "\u51b3\u7b56\u539f\u5219\uff1a\u5728\u6ee1\u8db3\u5185\u63a7\u7ba1\u7406\u8981\u6c42\u60c5\u51b5\u4e0b\uff0c\u51b3\u7b56\u7ed3\u679c\u53ef\u4f5c\u4e3a\u4e2d\u6807\u540e\u4f9d\u636e\uff0c\u65e0\u9700\u91cd\u590d\u51b3\u7b56\n\uff08\u7b7e\u7ea6\u91d1\u989d100\u4e07\u5143\u4ee5\u4e0a\u7684\u5546\u673a\uff0c\u9879\u76ee\u8d22\u52a1\u7ecf\u7406\u5fc5\u987b\u53c2\u4f1a\uff09"
  ];
  keyPoints.forEach((point, i) => {
    const py = 1.8 + i * 0.6;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: py, w: 0.3, h: 0.3, fill: { color: C.primary }, rectRadius: 0.02 });
    s.addText(point, { x: 0.9, y: py, w: 8.5, h: 0.5, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  });
  addBottomLine(s, 15);
}

// ================================================================
// PAGE 16: ICT项目真实性认定
// ================================================================
function page16() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "1.3 \u5e94\u6807\u7b7e\u7ea6\u9636\u6bb5\u2014\u2014ICT\u9879\u76ee\u771f\u5b9e\u6027\u8ba4\u5b9a");
  // 左侧：十不准
  s.addText("\u56fd\u8d44\u59d4\u201c\u5341\u4e0d\u51c6\u201d\u8981\u6c42", { x: 0.5, y: 1.3, w: 4.2, h: 0.3, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", margin: 0 });
  const tenRules = [
    "\u4e0d\u51c6\u5f00\u5c55\u80cc\u79bb\u4e3b\u4e1a\u7684\u8d38\u6613\u4e1a\u52a1",
    "\u4e0d\u51c6\u53c2\u4e0e\u7279\u5b9a\u5229\u76ca\u5173\u7cfb\u4f01\u4e1a\u95f4\u5f00\u5c55\u65e0\u5546\u4e1a\u76ee\u7684\u7684\u8d38\u6613\u4e1a\u52a1",
    "\u4e0d\u51c6\u5728\u8d38\u6613\u4e1a\u52a1\u4e2d\u4eba\u4e3a\u589e\u52a0\u4e0d\u5fc5\u8981\u7684\u4ea4\u6613\u73af\u8282",
    "\u4e0d\u51c6\u5f00\u5c55\u4efb\u4f55\u5f62\u5f0f\u7684\u878d\u8d44\u6027\u8d38\u6613",
    "\u4e0d\u51c6\u5f00\u5c55\u5bf9\u4ea4\u6613\u6807\u7684\u6ca1\u6709\u63a7\u5236\u6743\u7684\u7a7a\u8f6c\u3001\u8d70\u5355\u7b49\u8d38\u6613\u4e1a\u52a1",
    "\u4e0d\u51c6\u5f00\u5c55\u65e0\u5546\u4e1a\u5b9e\u8d28\u7684\u5faa\u73af\u8d38\u6613",
    "\u4e0d\u51c6\u5f00\u5c55\u6709\u6096\u4e8e\u4ea4\u6613\u5e38\u8bc6\u7684\u5f02\u5e38\u8d38\u6613\u4e1a\u52a1",
    "\u4e0d\u51c6\u5f00\u5c55\u98ce\u9669\u8f83\u9ad8\u7684\u975e\u6807\u4ed3\u5355\u4ea4\u6613",
    "\u4e0d\u51c6\u8fdd\u53cd\u4f1a\u8ba1\u51c6\u5219\u89c4\u5b9a\u786e\u8ba4\u4ee3\u7406\u8d38\u6613\u6536\u5165",
    "\u4e0d\u51c6\u5728\u5185\u63a7\u673a\u5236\u7f3a\u4e4f\u7684\u60c5\u51b5\u4e0b\u5f00\u5c55\u8d38\u6613\u4e1a\u52a1"
  ];
  tenRules.forEach((rule, i) => {
    s.addText("(" + (i + 1 <= 9 ? String.fromCharCode(0x2460 + i) : String.fromCharCode(0x2460 + 9)) + ") " + rule, { x: 0.5, y: 1.7 + i * 0.33, w: 4.5, h: 0.3, fontSize: 6, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "middle", margin: 0, wrap: true });
  });
  // 右侧：六到位
  s.addText("\u201c\u516d\u5230\u4f4d\u201d\u5230\u4f4d\u8ba4\u5b9a", { x: 5.2, y: 1.3, w: 4.2, h: 0.3, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.brandBlue, align: "center", margin: 0 });
  s.addText("\u4e2d\u56fd\u7535\u4fe1\u30102023\u3011321\u53f7\u6587\n\u4e2d\u56fd\u7535\u4fe1\u5de5\u4f5c\u901a\u62a52024\u5e74\u7b2c111\u671f\n\n\u575a\u51b3\u843d\u5b9e\u201c\u5341\u4e0d\u51c6\u201d\u8981\u6c42\uff0c\u675c\u7edd\u865a\u5047\u4e1a\u52a1\uff0c\u771f\u5b9e\u4e1a\u52a1\u5e94\u505a\u5c3d\u505a\uff0c\u5408\u7406\u6536\u5165\u5e94\u5217\u5c3d\u5217\uff0c\u63a8\u8fdbICT\u4e1a\u52a1\u9ad8\u8d28\u91cf\u53d1\u5c55\n\n\u793a\u4f8b\uff1a\u865a\u5047\u4e1a\u7ee9\u201c\u7ea2\u7ebf\u201d\u4e0d\u80fd\u78b0", { x: 5.2, y: 1.7, w: 4.2, h: 2.5, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  addBottomLine(s, 16);
}

// ================================================================
// PAGE 17: 投标策略与竞合
// ================================================================
function page17() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "1.3 \u5e94\u6807\u7b7e\u7ea6\u9636\u6bb5\u2014\u2014\u6295\u6807\u7b56\u7565\u4e0e\u7ade\u5408");
  // 中心：投标主体选择
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 3.5, y: 2.2, w: 3.0, h: 0.8, fill: { color: C.primary }, rectRadius: 0.1 });
  s.addText("\u6295\u6807\u4e3b\u4f53\u9009\u62e9", { x: 3.5, y: 2.2, w: 3.0, h: 0.8, fontSize: 16, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
  // 四种战术
  const tactics = [
    { title: "\u6258\u5e95\u6218\u672f", desc: "\u690d\u5165\u7b2c\u4e09\u65b9\u4f18\u52bf", x: 0.5, y: 1.5 },
    { title: "\u5168\u9762\u5360\u4f18\u6218\u672f", desc: "\u4e0e\u4f18\u52bf\u751f\u6001\u8054\u76df", x: 7.0, y: 1.5 },
    { title: "\u5e9f\u6807\u3001\u6d41\u6807\u6218\u672f", desc: "", x: 0.5, y: 3.5 },
    { title: "\u7ade\u5408\u5e73\u8861", desc: "\u5408\u4f5c+\u7ade\u4e89", x: 7.0, y: 3.5 }
  ];
  tactics.forEach(t => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: t.x, y: t.y, w: 2.5, h: 0.8, fill: { color: C.blueLight }, line: { color: C.primary, width: 0.75 }, rectRadius: 0.05 });
    s.addText(t.title, { x: t.x, y: t.y, w: 2.5, h: 0.5, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0 });
    if (t.desc) s.addText(t.desc, { x: t.x, y: t.y + 0.5, w: 2.5, h: 0.3, fontSize: 7, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle", margin: 0 });
  });
  addBottomLine(s, 17);
}

// ================================================================
// PAGE 18: 履约风险预评估及应对
// ================================================================
function page18() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "1.3 \u5e94\u6807\u7b7e\u7ea6\u9636\u6bb5\u2014\u2014\u5c65\u7ea6\u98ce\u9669\u9884\u8bc4\u4f30\u53ca\u5e94\u5bf9");
  // 4大风险
  const risks = [
    { title: "\u4ea4\u4ed8\u98ce\u9669", items: "\u00b7\u9879\u76ee\u8303\u56f4\uff08\u5f00\u53e3/\u95ed\u53e3\uff09\n\u00b7\u5408\u4f5c\u65b9\u4ea4\u4ed8\u80fd\u529b\n\u00b7\u8bbe\u5907\u4ea7\u6743\n\u00b7\u9700\u6c42\u53d8\u66f4\u98ce\u9669\n\u00b7\u9a8c\u6536\u6807\u51c6\n\u00b7\u9879\u76ee\u5de5\u671f\n\u00b7\u8bd5\u8fd0\u884c\u65f6\u957f", bg: C.primary },
    { title: "\u5408\u540c\u98ce\u9669", items: "\u00b7\u8bc4\u4f30\u786e\u5b9a\u5408\u540c\u5185\u5bb9\n\u00b7\u786e\u4fdd\u8303\u56f4\u660e\u786e\u3001\u6807\u51c6\u5177\u4f53\n\u00b7\u907f\u514d\u98ce\u9669\n\u00b7\u5bf9\u5408\u540c\u65b9\u8fdb\u884c\u8d44\u683c\u5ba1\u6838", bg: C.brandBlue },
    { title: "\u5b89\u5168\u98ce\u9669", items: "\u00b7\u7f51\u4fe1\u5b89\u5168\u3001\u6570\u636e\u5b89\u5168\n\u00b7\u5e73\u53f0\u5907\u6848\u3001\u7b49\u4fdd\u6d4b\u8bc4\n\u00b7\u7528\u6237\u9690\u79c1\u4fe1\u606f\u4fdd\u62a4", bg: C.orange },
    { title: "\u8fd0\u8425\u98ce\u9669", items: "\u00b7\u5ef6\u671f\u9a8c\u6536\u7684\u98ce\u9669\n\u00b7SLA\u670d\u52a1\u6807\u51c6\n\u00b7\u8fd0\u8425\u7ef4\u62a4\u4fdd\u969c", bg: C.teal }
  ];
  risks.forEach((r, i) => {
    const rx = 0.4 + i * 2.4;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: rx, y: 1.4, w: 2.2, h: 2.5, fill: { color: C.white }, line: { color: r.bg, width: 1 }, rectRadius: 0.05 });
    s.addText(r.title, { x: rx, y: 1.4, w: 2.2, h: 0.4, fontSize: 11, fontFace: "Microsoft YaHei", bold: true, color: C.white, fill: { color: r.bg }, align: "center", valign: "middle", margin: 0 });
    s.addText(r.items, { x: rx + 0.1, y: 1.85, w: 2.0, h: 2.0, fontSize: 7, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  });
  // 底部：前向合同签订
  s.addText("\u524d\u5411\u5408\u540c\u7b7e\u8ba2", { x: 0.5, y: 4.2, w: 9.0, h: 0.35, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });
  s.addText("n \u5ba2\u6237\u7ecf\u7406\u4e3b\u5bfc\uff0c\u591a\u90e8\u95e8\u8bc4\u4f30\u5408\u540c\u5185\u5bb9   n \u786e\u4fdd\u8303\u56f4\u660e\u786e\u3001\u6807\u51c6\u5177\u4f53\uff0c\u907f\u514d\u98ce\u9669   n \u5bf9\u5408\u540c\u65b9\u8fdb\u884c\u8d44\u683c\u5ba1\u6838\nn \u5ba2\u6237\u7ecf\u7406\u9700\u63d0\u4f9b\u4f9d\u636e\uff0c\u586b\u5199\u5408\u540c\u5173\u952e\u4fe1\u606f\u8868\uff0c\u542f\u52a8\u5ba1\u6279\u6d41\u7a0b   n \u786e\u4fdd\u5408\u540c\u6b63\u5411\u7b7e\u8ba2\uff0c\u907f\u514d\u5012\u7b7e   n \u5408\u540c\u4e2d\u5e94\u660e\u786e\u7279\u6b8a\u4ea7\u54c1\u5236\u9020\u53ca\u4f9b\u5e94\u8981\u6c42", { x: 0.5, y: 4.55, w: 9.0, h: 0.7, fontSize: 7, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  addBottomLine(s, 18);
}

// ================================================================
// PAGE 19: 售前售中交接
// ================================================================
function page19() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "1.3 \u6295\u6807\u7b7e\u7ea6\u9636\u6bb5\u2014\u2014\u552e\u524d\u552e\u4e2d\u4ea4\u63a5");
  s.addText("\u9879\u76ee\u8d1f\u8d23\u4eba\u7275\u5934\u7ec4\u7ec7\u552e\u524d\u552e\u4e2d\u5de5\u4f5c\u4ea4\u63a5\uff0c\u5bf9\u4ea4\u63a5\u7684\u5b8c\u6574\u6027\u4e0e\u53ca\u65f6\u6027\u8d1f\u8d23\u3002\u539f\u5219\u4e0a\u9879\u76ee\u7b7e\u7ea6\u6216\u9886\u53d6\u4e2d\u6807\u901a\u77e5\u4e66\u540e3\u65e5\u5185\u5b8c\u6210\u4ea4\u63a5\u3002", { x: 0.7, y: 1.15, w: 8.6, h: 0.3, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "left", margin: 0, wrap: true });
  // 交接表格
  const tableData = [
    [{ text: "\u68c0\u67e5\u9879", options: { fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.white, fill: { color: C.primary }, align: "center", valign: "middle" } },
     { text: "\u6807\u51c6", options: { fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.white, fill: { color: C.primary }, align: "center", valign: "middle" } },
     { text: "\u7ba1\u7406\u52a8\u4f5c", options: { fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.white, fill: { color: C.primary }, align: "center", valign: "middle" } },
     { text: "\u5de5\u5177\u5173\u8054", options: { fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.white, fill: { color: C.primary }, align: "center", valign: "middle" } }],
    [{ text: "\u4ea4\u63a5\u65f6\u6548\u6027", options: { fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, fill: { color: C.pinkLight }, align: "center", valign: "middle" } },
     { text: "\u7b7e\u7ea6\u540e3\u65e5\u5185\u5b8c\u6210", options: { fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, fill: { color: C.pinkLight }, align: "center", valign: "middle" } },
     { text: "\u9879\u76ee\u8d1f\u8d23\u4eba\u7275\u5934\u4ea4\u63a5\u4f1a", options: { fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, fill: { color: C.pinkLight }, align: "center", valign: "middle" } },
     { text: "\u5546\u673a\u8f6c\u5316\u81ea\u52a8\u63a8\u9001\uff08\u96c6\u56e2BPM\u7cfb\u7edf\uff09", options: { fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, fill: { color: C.pinkLight }, align: "center", valign: "middle" } }],
    [{ text: "\u4fe1\u606f\u5b8c\u6574\u6027", options: { fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle" } },
     { text: "\u9879\u76ee\u8303\u56f4\u3001\u4e0e\u5176\u4ed6\u5e73\u53f0\u754c\u9762\u3001\u9a8c\u6536\u6807\u51c6\u3001\u7b2c\u4e09\u65b9\u9a8c\u8bc1\u8981\u6c42", options: { fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle" } },
     { text: "\u53cc\u65b9\u7b7e\u5b57\u786e\u8ba4\u79fb\u4ea4", options: { fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle" } },
     { text: "\u552e\u524d\u552e\u4e2d\u4ea4\u63a5\u6e05\u5355", options: { fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle" } }],
    [{ text: "\u98ce\u9669\u70b9\u4f20\u9012", options: { fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, fill: { color: C.pinkLight }, align: "center", valign: "middle" } },
     { text: "\u5ba2\u6237\u7279\u6b8a\u8981\u6c42\u3001\u5546\u52a1\u98ce\u9669", options: { fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, fill: { color: C.pinkLight }, align: "center", valign: "middle" } },
     { text: "\u8fd0\u8425\u7ecf\u7406\u53c2\u4e0e\u98ce\u9669\u8bc4\u4f30", options: { fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, fill: { color: C.pinkLight }, align: "center", valign: "middle" } },
     { text: "\u98ce\u9669\u7684\u5ba1\u6838\u8981\u70b9", options: { fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, fill: { color: C.pinkLight }, align: "center", valign: "middle" } }]
  ];
  s.addTable(tableData, { x: 0.5, y: 1.6, w: 9.0, colW: [1.8, 2.8, 2.5, 1.9], rowH: [0.4, 0.8, 0.8, 0.8], border: { color: C.borderLight, pt: 0.5 } });
  addBottomLine(s, 19);
}

// ================================================================
// PAGE 20: 售前篇要点回顾
// ================================================================
function page20() {
  const s = pres.addSlide();
  s.background = { color: C.white };
  addBrand(s);
  addTitleBar(s, "\u552e\u524d\u7bc7\u2014\u2014\u8981\u70b9\u56de\u987e");
  s.addText("\u552e\u524d\u5546\u673a\u7ba1\u7406\u673a\u5236", { x: 3.5, y: 1.5, w: 3.0, h: 0.4, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", margin: 0 });
  // SAR公式回顾
  const keywords = ["\u5546\u673a", "\u89e3\u51b3\u65b9\u6848", "\u5408\u540c", "S", "A", "R", "\u56db\u6b65", "\u56db\u65b9\u6848\u7f16\u5236", "\u5ba1\u6838\u8981\u70b9", "\u5ba1\u6838\u8981\u70b9"];
  // 简化为关键词云
  const kwGroups = [
    { label: "S \u5546\u673a", items: ["\u56db\u6b65", "\u56db\u76ef"] },
    { label: "A \u89e3\u51b3\u65b9\u6848", items: ["\u65b9\u6848\u7f16\u5236", "\u5ba1\u6838\u8981\u70b9"] },
    { label: "R \u5408\u540c", items: ["\u5ba1\u6838\u8981\u70b9", "\u591a\u4f1a\u5408\u4e00\u51b3\u7b56"] }
  ];
  kwGroups.forEach((g, i) => {
    const gx = 1.0 + i * 3.0;
    s.addText(g.label, { x: gx, y: 2.2, w: 2.5, h: 0.4, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0 });
    g.items.forEach((item, j) => {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: gx + 0.3, y: 2.8 + j * 0.5, w: 1.9, h: 0.35, fill: { color: i % 2 === 0 ? C.pinkLight : C.blueLight }, rectRadius: 0.03 });
      s.addText(item, { x: gx + 0.3, y: 2.8 + j * 0.5, w: 1.9, h: 0.35, fontSize: 9, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle", margin: 0 });
    });
  });
  // 底部总结
  s.addText("\u672c\u7bc7\u4e3b\u8981\u5bf9\u552e\u524d3\u4e2a\u9636\u6bb512\u4e2a\u73af\u8282\u8fdb\u884c\u4e86\u4ecb\u7ecd\uff0c\u5f3a\u8c03\u4e86\u5546\u673a\u4fe1\u606f\u7684\u5b8c\u6574\u6027\u3001\u5546\u673a\u7684\u5168\u6d41\u7a0b\u7ba1\u7406\u3001\u65b9\u6848\u7684\u5408\u7406\u6027\u548c\u53ef\u843d\u5730\u6027\u3001\u5546\u52a1\u6a21\u5f0f\u7684\u7ecf\u6d4e\u53ef\u884c\u6027\u3001\u4ee5\u53ca\u5408\u540c\u5185\u5bb9\u7684\u660e\u786e\u6027\u7b49\u5173\u952e\u8981\u7d20\u3002", { x: 0.7, y: 4.2, w: 8.6, h: 0.8, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  addBottomLine(s, 20);
}

// ================================================================
// 生成PPT

// ================================================================
// 第21-40页函数（从Part2合并）
// ================================================================
// ============================================================
// PAGE 21: 目录页（售中篇）
// ============================================================
function page21() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "\u76ee\u5f55");

  var items = [
    { num: "01", title: "\u552e\u524d\u7bc7", desc: "\u4ece\u83b7\u53d6\u5230\u8f6c\u5316", active: false },
    { num: "02", title: "\u552e\u4e2d\u7bc7", desc: "\u4ece\u843d\u5355\u5230\u843d\u6536", active: true,
      subs: ["\u9879\u76ee\u542f\u52a8", "\u540e\u5411\u91c7\u8d2d", "\u5b9e\u65bd\u7ba1\u63a7", "\u9a8c\u6536\u4ea4\u4ed8"] },
    { num: "03", title: "\u552e\u540e\u7bc7", desc: "\u4ece\u8fd0\u7ef4\u5230\u8fd0\u8425", active: false }
  ];

  var startY = 1.7;
  var itemH = 0.85;
  for (var i = 0; i < items.length; i++) {
    var it = items[i];
    var y = startY + i * (itemH + 0.15);
    // 编号圆
    slide.addShape(pres.shapes.OVAL, {
      x: 1.2, y: y, w: 0.55, h: 0.55,
      fill: { color: it.active ? C.primary : C.borderLight }
    });
    slide.addText(it.num, {
      x: 1.2, y: y, w: 0.55, h: 0.55, fontSize: 16, fontFace: "Microsoft YaHei",
      bold: true, color: it.active ? C.white : C.textSec, align: "center", valign: "middle"
    });
    // 标题
    slide.addText(it.title, {
      x: 2.0, y: y, w: 2.0, h: 0.55, fontSize: 16, fontFace: "Microsoft YaHei",
      bold: true, color: it.active ? C.primary : C.text, align: "left", valign: "middle"
    });
    // 破折号+描述
    slide.addText("\u2014\u2014" + it.desc, {
      x: 4.0, y: y, w: 3.5, h: 0.55, fontSize: 12, fontFace: "Microsoft YaHei",
      color: it.active ? C.text : C.textLight, align: "left", valign: "middle"
    });
    // 子项
    if (it.subs) {
      var subW = 1.55;
      var subGap = 0.1;
      var subStartX = 2.0;
      var subY = y + 0.6;
      for (var j = 0; j < it.subs.length; j++) {
        var sx = subStartX + j * (subW + subGap);
        slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
          x: sx, y: subY, w: subW, h: 0.35,
          fill: { color: C.accentLight }, line: { color: C.primary, width: 1 }, rectRadius: 0.03
        });
        slide.addText(it.subs[j], {
          x: sx, y: subY, w: subW, h: 0.35, fontSize: 9, fontFace: "Microsoft YaHei",
          bold: true, color: C.primary, align: "center", valign: "middle"
        });
      }
    }
    // 连接线
    if (i < items.length - 1) {
      slide.addShape(pres.shapes.RECTANGLE, {
        x: 1.45, y: y + 0.55, w: 0.02, h: 0.15, fill: { color: C.borderLight }
      });
    }
  }

  // 右侧装饰
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 8.5, y: 1.7, w: 0.8, h: 2.8, fill: { color: C.accentLight }
  });
  slide.addText("\u552e\u4e2d\u7bc7", {
    x: 8.5, y: 2.6, w: 0.8, h: 1.0, fontSize: 14, fontFace: "Microsoft YaHei",
    bold: true, color: C.primary, align: "center", valign: "middle", rotate: 270
  });

  addBottomLine(slide, 21);
}

// ============================================================
// PAGE 22: DICT项目流程（简版）
// ============================================================
function page22() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.1 DICT\u9879\u76ee\u6d41\u7a0b\uff08\u7b80\u7248\uff09", "\u5546\u673a\u2192\u5e94\u6807\u7b7e\u7ea6\u2192\u552e\u4e2d\u5b9e\u65bd\u2192\u6536\u4ed8\u6b3e\u2192\u8fd0\u7ef4\u8fd0\u8425");

  var stages = [
    { name: "\u5546\u673a\u9636\u6bb5", color: C.primary, subs: ["\u5546\u673a\u7ebf\u7d22\u5f55\u5165", "\u5546\u673a\u8ddf\u8e2a\u8f6c\u5316", "\u5546\u673a\u8bc4\u4f30\u5ba1\u6279"] },
    { name: "\u5e94\u6807\u7b7e\u7ea6\u9636\u6bb5", color: C.brandBlue, subs: ["\u65b9\u6848\u5236\u5b9a", "\u62a5\u4ef7\u6295\u6807", "\u5408\u540c\u7b7e\u8ba2"] },
    { name: "\u552e\u4e2d\u5b9e\u65bd\u9636\u6bb5", color: C.orange, subs: ["\u9879\u76ee\u542f\u52a8", "\u540e\u5411\u91c7\u8d2d", "\u5b9e\u65bd\u7ba1\u63a7", "\u9a8c\u6536\u4ea4\u4ed8"] },
    { name: "\u6536\u4ed8\u6b3e", color: C.green, subs: ["\u5f00\u7968\u6536\u6b3e", "\u8d26\u671f\u7ba1\u7406"] },
    { name: "\u8fd0\u7ef4\u8fd0\u8425\u9636\u6bb5", color: C.teal, subs: ["\u4ea4\u8d44\u4ea4\u7ef4", "\u8fd0\u7ef4\u670d\u52a1", "\u6301\u7eed\u8fd0\u8425"] }
  ];

  var startX = 0.5;
  var stageW = 1.65;
  var stageGap = 0.22;
  var stageY = 1.6;
  var stageH = 0.5;

  for (var i = 0; i < stages.length; i++) {
    var sx = startX + i * (stageW + stageGap);
    addFlowNode(slide, sx, stageY, stageW, stageH, stages[i].name, { bg: stages[i].color, fontSize: 11 });
    // 子项
    var subY = stageY + stageH + 0.08;
    for (var j = 0; j < stages[i].subs.length; j++) {
      var subH = 0.32;
      slide.addShape(pres.shapes.RECTANGLE, {
        x: sx, y: subY + j * (subH + 0.05), w: stageW, h: subH,
        fill: { color: C.white }, line: { color: stages[i].color, width: 1, dashType: "dash" }
      });
      slide.addText(stages[i].subs[j], {
        x: sx, y: subY + j * (subH + 0.05), w: stageW, h: subH,
        fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle"
      });
    }
    // 箭头
    if (i < stages.length - 1) {
      addArrowRight(slide, sx + stageW + 0.01, stageY + stageH / 2 - 0.1, stageGap - 0.02, 0.2, C.textLight);
    }
  }

  // 底部分类型说明
  var types = [
    { name: "\u6295\u8d44\u578b", color: C.primary },
    { name: "\u6df7\u5408\u578b", color: C.brandBlue },
    { name: "\u6210\u672c\u578b", color: C.orange },
    { name: "\u5206\u6210\u578b", color: C.green }
  ];
  var typeY = 4.3;
  slide.addText("\u9879\u76ee\u7c7b\u578b\uff1a", {
    x: 0.5, y: typeY, w: 1.2, h: 0.35, fontSize: 10, fontFace: "Microsoft YaHei",
    bold: true, color: C.text, align: "left", valign: "middle"
  });
  for (var k = 0; k < types.length; k++) {
    var tx = 1.7 + k * 1.8;
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: tx, y: typeY, w: 1.5, h: 0.35, fill: { color: types[k].color }, rectRadius: 0.03
    });
    slide.addText(types[k].name, {
      x: tx, y: typeY, w: 1.5, h: 0.35, fontSize: 10, fontFace: "Microsoft YaHei",
      bold: true, color: C.white, align: "center", valign: "middle"
    });
  }

  addBottomLine(slide, 22);
}

// ============================================================
// PAGE 23: DICT项目流程（售中）- 详细流程
// ============================================================
function page23() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.1 DICT\u9879\u76ee\u6d41\u7a0b\uff08\u552e\u4e2d\uff09", "\u4ece\u9879\u76ee\u4ea4\u5e95\u5230\u5b9e\u65bd\u65b9\u6848\u7f16\u5236\u4e0e\u5ba1\u6279");

  // 变更管理横条
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.5, w: 9.0, h: 0.35,
    fill: { color: C.pinkLight }, line: { color: C.primary, width: 1, dashType: "dash" }
  });
  slide.addText("\u53d8\u66f4\u7ba1\u7406\u8d2f\u7a7f\u5168\u6d41\u7a0b", {
    x: 0.5, y: 1.5, w: 9.0, h: 0.35, fontSize: 10, fontFace: "Microsoft YaHei",
    bold: true, color: C.primary, align: "center", valign: "middle"
  });

  // 主流程节点
  var mainNodes = [
    { name: "\u9879\u76ee\u4ea4\u5e95", nums: "1.1 / 1.2 / 1.3", color: C.primary, sub: "\u4ea4\u5e95\u4f1a\u8bae\u53ec\u5f00\u3001\u4ea4\u5e95\u8bb0\u5f55\u3001\u8d44\u6599\u79fb\u4ea4" },
    { name: "\u9879\u76ee\u542f\u52a8", nums: "2 / 3 / 4 / 5 / 6", color: C.brandBlue, sub: "\u56e2\u961f\u7ec4\u5efa\u3001\u80fd\u529b\u914d\u7f6e\u3001\u4ea4\u4ed8\u8ba1\u5212\u3001\u5b50\u9879\u76ee\u62c6\u5206\u3001\u5f00\u5de5\u4f1a" },
    { name: "\u5b9e\u65bd\u65b9\u6848\u7f16\u5236", nums: "7-1 ~ 9-4 \u5ba1\u6279", color: C.orange, sub: "\u65b9\u6848\u5236\u5b9a\u2192\u5185\u90e8\u5ba1\u6838\u2192\u5916\u90e8\u5ba1\u6838\u2192\u9884\u7b97\u7f16\u5236\u2192\u5ba1\u6279\u6d41\u7a0b" },
    { name: "\u9879\u76ee\u5b9e\u65bd", nums: "\u540e\u5411\u91c7\u8d2d + \u5b9e\u65bd\u7ba1\u63a7", color: C.green, sub: "\u91c7\u8d2d\u6267\u884c\u3001\u8fc7\u7a0b\u7ba1\u63a7\u3001\u8d28\u91cf\u7ba1\u7406\u3001\u98ce\u9669\u7ba1\u7406\u3001\u53d8\u66f4\u7ba1\u7406" }
  ];

  var mx = 0.5;
  var mw = 2.05;
  var mGap = 0.2;
  var my = 2.15;
  var mH = 0.6;

  for (var i = 0; i < mainNodes.length; i++) {
    var sx = mx + i * (mw + mGap);
    // 主节点
    addFlowNode(slide, sx, my, mw, mH, mainNodes[i].name, { bg: mainNodes[i].color, fontSize: 12 });
    // 编号标注
    slide.addShape(pres.shapes.RECTANGLE, {
      x: sx, y: my + mH + 0.02, w: mw, h: 0.25,
      fill: { color: C.grayLight }
    });
    slide.addText(mainNodes[i].nums, {
      x: sx, y: my + mH + 0.02, w: mw, h: 0.25, fontSize: 8, fontFace: "Microsoft YaHei",
      color: C.textSec, align: "center", valign: "middle"
    });
    // 子项说明
    slide.addShape(pres.shapes.RECTANGLE, {
      x: sx, y: my + mH + 0.3, w: mw, h: 1.4,
      fill: { color: C.white }, line: { color: mainNodes[i].color, width: 1 }
    });
    slide.addText(mainNodes[i].sub, {
      x: sx + 0.08, y: my + mH + 0.35, w: mw - 0.16, h: 1.3, fontSize: 8.5,
      fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", wrap: true, lineSpacingMultiple: 1.3
    });
    // 箭头
    if (i < mainNodes.length - 1) {
      addArrowRight(slide, sx + mw + 0.01, my + mH / 2 - 0.1, mGap - 0.02, 0.2, C.textLight);
    }
  }

  // 底部时间线标注
  var timeY = 4.55;
  var timeLabels = [
    { label: "T+0 \u4ea4\u5e95", x: 0.5 },
    { label: "T+5\u5929 \u542f\u52a8", x: 2.75 },
    { label: "T+15\u5929 \u65b9\u6848\u5ba1\u6279", x: 5.0 },
    { label: "T+30\u5929 \u5b9e\u65bd\u5f00\u59cb", x: 7.25 }
  ];
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: timeY - 0.05, w: 8.75, h: 0.02, fill: { color: C.borderLight } });
  for (var t = 0; t < timeLabels.length; t++) {
    slide.addShape(pres.shapes.OVAL, { x: timeLabels[t].x + 0.8, y: timeY - 0.08, w: 0.1, h: 0.1, fill: { color: C.primary } });
    slide.addText(timeLabels[t].label, {
      x: timeLabels[t].x, y: timeY + 0.05, w: 1.8, h: 0.3, fontSize: 8, fontFace: "Microsoft YaHei",
      color: C.textSec, align: "center", valign: "middle"
    });
  }

  addBottomLine(slide, 23);
}

// ============================================================
// PAGE 24: DICT项目流程（售中）- 实施阶段
// ============================================================
function page24() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.1 DICT\u9879\u76ee\u6d41\u7a0b\uff08\u552e\u4e2d\uff09", "\u65b9\u6848\u7f16\u5236 \u2192 \u9879\u76ee\u5b9e\u65bd \u2192 \u6d4b\u8bd5\u9a8c\u6536 \u2192 \u4ea4\u8d44\u4ea4\u7ef4");

  // 变更管理横条
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.5, w: 9.0, h: 0.3,
    fill: { color: C.pinkLight }, line: { color: C.primary, width: 1, dashType: "dash" }
  });
  slide.addText("\u53d8\u66f4\u7ba1\u7406", {
    x: 0.5, y: 1.5, w: 9.0, h: 0.3, fontSize: 9, fontFace: "Microsoft YaHei",
    bold: true, color: C.primary, align: "center", valign: "middle"
  });

  // 主流程4阶段
  var phases = [
    { name: "\u65b9\u6848\u7f16\u5236", color: C.primary },
    { name: "\u9879\u76ee\u5b9e\u65bd", color: C.brandBlue },
    { name: "\u6d4b\u8bd5\u9a8c\u6536", color: C.orange },
    { name: "\u4ea4\u8d44\u4ea4\u7ef4", color: C.green }
  ];
  var phx = 0.5, phw = 2.05, phGap = 0.2, phy = 1.95, phh = 0.45;
  for (var i = 0; i < phases.length; i++) {
    var sx = phx + i * (phw + phGap);
    addFlowNode(slide, sx, phy, phw, phh, phases[i].name, { bg: phases[i].color, fontSize: 11 });
    if (i < phases.length - 1) {
      addArrowRight(slide, sx + phw + 0.01, phy + phh / 2 - 0.08, phGap - 0.02, 0.16, C.textLight);
    }
  }

  // 建采流程区域
  var procY = 2.65;
  slide.addText("\u540e\u5411\u91c7\u8d2d\u6d41\u7a0b\uff1a", {
    x: 0.5, y: procY, w: 2.0, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei",
    bold: true, color: C.text, align: "left", valign: "middle"
  });
  var procSteps = ["\u91c7\u8d2d\u9700\u6c42", "\u91c7\u8d2d\u65b9\u6848", "\u4f9b\u5546\u9009\u62e9", "\u5408\u540c\u7b7e\u8ba2", "\u5230\u8d27\u9a8c\u6536"];
  var psx = 2.5, psw = 1.25, psGap = 0.12;
  for (var j = 0; j < procSteps.length; j++) {
    var px = psx + j * (psw + psGap);
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: px, y: procY, w: psw, h: 0.3, fill: { color: C.blueLight },
      line: { color: C.brandBlue, width: 1 }, rectRadius: 0.03
    });
    slide.addText(procSteps[j], {
      x: px, y: procY, w: psw, h: 0.3, fontSize: 8, fontFace: "Microsoft YaHei",
      bold: true, color: C.brandBlue, align: "center", valign: "middle"
    });
    if (j < procSteps.length - 1) {
      addArrowRight(slide, px + psw, procY + 0.05, psGap, 0.2, C.brandBlue);
    }
  }

  // 各子项目时间线
  var subItems = [
    { name: "\u6807\u54c1\u4ea4\u4ed8", color: C.primary, start: 3.0, duration: 1.5 },
    { name: "\u539f\u5b50\u80fd\u529b", color: C.brandBlue, start: 3.5, duration: 2.0 },
    { name: "\u786c\u4ef6\u91c7\u8d2d", color: C.orange, start: 2.0, duration: 2.5 },
    { name: "\u8f6f\u4ef6\u5f00\u53d1", color: C.green, start: 4.0, duration: 2.0 },
    { name: "\u5176\u4ed6\u670d\u52a1", color: C.teal, start: 4.5, duration: 1.5 }
  ];

  var tlY = 3.3;
  var tlStartX = 2.5;
  var tlW = 6.8;
  var tlEndX = tlStartX + tlW;
  // 时间轴底线
  slide.addShape(pres.shapes.RECTANGLE, { x: tlStartX, y: tlY, w: tlW, h: 0.02, fill: { color: C.borderLight } });
  // 时间刻度
  var ticks = ["T+0", "T+2\u5468", "T+4\u5468", "T+6\u5468", "T+8\u5468"];
  for (var t = 0; t < ticks.length; t++) {
    var tickX = tlStartX + (tlW / (ticks.length - 1)) * t;
    slide.addShape(pres.shapes.RECTANGLE, { x: tickX, y: tlY - 0.03, w: 0.01, h: 0.08, fill: { color: C.textLight } });
    slide.addText(ticks[t], { x: tickX - 0.4, y: tlY + 0.05, w: 0.8, h: 0.2, fontSize: 7, fontFace: "Microsoft YaHei", color: C.textLight, align: "center" });
  }

  for (var s = 0; s < subItems.length; s++) {
    var si = subItems[s];
    var barY = tlY + 0.35 + s * 0.32;
    // 标签
    slide.addText(si.name, {
      x: 0.5, y: barY, w: 1.8, h: 0.28, fontSize: 9, fontFace: "Microsoft YaHei",
      bold: true, color: C.text, align: "right", valign: "middle"
    });
    // 进度条
    var barX = tlStartX + (si.start / 8.0) * tlW;
    var barW = (si.duration / 8.0) * tlW;
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: barX, y: barY, w: barW, h: 0.25, fill: { color: si.color }, rectRadius: 0.03
    });
    slide.addText(si.duration + "\u5468", {
      x: barX, y: barY, w: barW, h: 0.25, fontSize: 7, fontFace: "Microsoft YaHei",
      color: C.white, align: "center", valign: "middle"
    });
  }

  addBottomLine(slide, 24);
}

// ============================================================
// PAGE 25: 项目经理 & 交付经理（PMO）
// ============================================================
function page25() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.1 \u9879\u76ee\u7ecf\u7406 & \u4ea4\u4ed8\u7ecf\u7406\uff08PMO\uff09", "\u7edf\u7b79\u534f\u8c03 \u00b7 \u63a8\u8fdb\u7763\u4fc3 \u00b7 \u68c0\u9a8c\u8bc4\u4f30");

  var leftTitle = "\u9879\u76ee\u7ecf\u7406\uff08PM\uff09";
  var rightTitle = "\u4ea4\u4ed8\u7ecf\u7406\uff08DM\uff09";

  var leftItems = [
    { head: "\u7edf\u7b79\u534f\u8c03", body: "\u7edf\u7b00\u9879\u76ee\u5168\u5c40\uff0c\u534f\u8c03\u552e\u524d\u3001\u552e\u4e2d\u3001\u552e\u540e\u5404\u73af\u8282\uff0c\u786e\u4fdd\u9879\u76ee\u6309\u8ba1\u5212\u63a8\u8fdb" },
    { head: "\u8d44\u6e90\u8c03\u914d", body: "\u7edf\u7b00\u5185\u5916\u90e8\u8d44\u6e90\uff0c\u534f\u8c03\u5404\u5b50\u9879\u76ee\u8d1f\u8d23\u4eba\uff0c\u786e\u4fdd\u4ea4\u4ed8\u80fd\u529b\u5145\u8db3" },
    { head: "\u63a8\u8fdb\u7763\u4fc3", body: "\u76d1\u63a7\u9879\u76ee\u8fdb\u5ea6\uff0c\u7763\u4fc3\u5404\u5b50\u9879\u76ee\u6309\u8282\u70b9\u5b8c\u6210\uff0c\u53ca\u65f6\u53d1\u73b0\u5e76\u89e3\u51b3\u5361\u70b9" },
    { head: "\u68c0\u9a8c\u8bc4\u4f30", body: "\u7ec4\u7ec7\u9636\u6bb5\u6027\u9a8c\u6536\u8bc4\u4f30\uff0c\u786e\u4fdd\u4ea4\u4ed8\u8d28\u91cf\u7b26\u5408\u6807\u51c6\u548c\u5408\u540c\u7ea6\u5b9a" }
  ];

  var rightItems = [
    { head: "\u4ea4\u4ed8\u7ba1\u63a7", body: "\u5236\u5b9a\u4ea4\u4ed8\u8ba1\u5212\uff0c\u7ba1\u63a7\u4ea4\u4ed8\u8fc7\u7a0b\uff0c\u786e\u4fdd\u53ef\u9a8c\u6536\u6210\u679c\u6309\u671f\u4ea4\u4ed8" },
    { head: "\u8d28\u91cf\u63a7\u5236", body: "\u5236\u5b9a\u8d28\u91cf\u6807\u51c6\uff0c\u7ba1\u63a7\u5b9e\u65bd\u8fc7\u7a0b\uff0c\u786e\u4fdd\u4ea7\u54c1\u8d28\u91cf\u6ee1\u8db3\u5ba2\u6237\u9700\u6c42" },
    { head: "\u98ce\u9669\u7ba1\u7406", body: "\u8bc6\u522b\u4ea4\u4ed8\u98ce\u9669\uff0c\u5236\u5b9a\u5e94\u5bf9\u63aa\u65bd\uff0c\u964d\u4f4e\u4ea4\u4ed8\u8fc7\u7a0b\u4e2d\u7684\u4e0d\u786e\u5b9a\u6027" },
    { head: "\u9a8c\u6536\u7ec4\u7ec7", body: "\u7ec4\u7ec7\u9884\u9a8c\u6536\u548c\u6b63\u5f0f\u9a8c\u6536\uff0c\u7ef4\u62a4\u4ea4\u4ed8\u6210\u679c\u6e05\u5355\uff0c\u786e\u4fdd\u9879\u76ee\u987a\u5229\u7ed3\u9879" }
  ];

  var colW = 4.2;
  var colGap = 0.3;
  var colY = 1.7;

  // 左栏
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: colY, w: colW, h: 0.45, fill: { color: C.primary } });
  slide.addText(leftTitle, { x: 0.5, y: colY, w: colW, h: 0.45, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });

  for (var i = 0; i < leftItems.length; i++) {
    var iy = colY + 0.55 + i * 0.75;
    slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: iy, w: colW, h: 0.7, fill: { color: i % 2 === 0 ? C.accentLight : C.white }, line: { color: C.borderLight, width: 0.5 } });
    slide.addText(leftItems[i].head, { x: 0.6, y: iy + 0.05, w: colW - 0.2, h: 0.25, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle" });
    slide.addText(leftItems[i].body, { x: 0.6, y: iy + 0.3, w: colW - 0.2, h: 0.38, fontSize: 8.5, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", wrap: true, lineSpacingMultiple: 1.2 });
  }

  // 右栏
  var rx = 0.5 + colW + colGap;
  slide.addShape(pres.shapes.RECTANGLE, { x: rx, y: colY, w: colW, h: 0.45, fill: { color: C.brandBlue } });
  slide.addText(rightTitle, { x: rx, y: colY, w: colW, h: 0.45, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });

  for (var j = 0; j < rightItems.length; j++) {
    var jy = colY + 0.55 + j * 0.75;
    slide.addShape(pres.shapes.RECTANGLE, { x: rx, y: jy, w: colW, h: 0.7, fill: { color: j % 2 === 0 ? C.blueLight : C.white }, line: { color: C.borderLight, width: 0.5 } });
    slide.addText(rightItems[j].head, { x: rx + 0.1, y: jy + 0.05, w: colW - 0.2, h: 0.25, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.brandBlue, align: "left", valign: "middle" });
    slide.addText(rightItems[j].body, { x: rx + 0.1, y: jy + 0.3, w: colW - 0.2, h: 0.38, fontSize: 8.5, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", wrap: true, lineSpacingMultiple: 1.2 });
  }

  // 中间 VS 圆
  slide.addShape(pres.shapes.OVAL, { x: 0.5 + colW + colGap / 2 - 0.2, y: 2.5, w: 0.4, h: 0.4, fill: { color: C.orange } });
  slide.addText("&", { x: 0.5 + colW + colGap / 2 - 0.2, y: 2.5, w: 0.4, h: 0.4, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });

  addBottomLine(slide, 25);
}

// ============================================================
// PAGE 26: 项目启动——售中交付能力配置
// ============================================================
function page26() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.1 \u9879\u76ee\u542f\u52a8\u2014\u2014\u552e\u4e2d\u4ea4\u4ed8\u80fd\u529b\u914d\u7f6e", "\u4ecePMO\u5230\u5b50\u9879\u76ee\u8d1f\u8d23\u4eba\u7684\u80fd\u529b\u914d\u7f6e\u67b6\u6784");

  // 顶部层级流程
  var topNodes = [
    { name: "PMO", sub: "\u7edf\u7b79\u7ba1\u7406", color: C.primary, w: 1.3 },
    { name: "\u9879\u76ee\u7ecf\u7406", sub: "\u6574\u4f53\u4ea4\u4ed8\u7b2c\u4e00\u8d23\u4efb\u4eba", color: C.brandBlue, w: 1.6 },
    { name: "\u5b50\u9879\u76ee\u8d1f\u8d23\u4eba", sub: "\u7f51\u7edc/\u91c7\u8d2d/\u81ea\u6709\u80fd\u529b/\u5408\u4f5c\u4f19\u4f34", color: C.orange, w: 2.8 }
  ];

  var tx = 0.8, ty = 1.55;
  for (var i = 0; i < topNodes.length; i++) {
    var nx = tx;
    addFlowNode(slide, nx, ty, topNodes[i].w, 0.45, topNodes[i].name, { bg: topNodes[i].color, fontSize: 11 });
    slide.addText(topNodes[i].sub, { x: nx, y: ty + 0.47, w: topNodes[i].w, h: 0.25, fontSize: 8, fontFace: "Microsoft YaHei", color: C.textSec, align: "center", valign: "middle" });
    if (i < topNodes.length - 1) {
      addArrowRight(slide, nx + topNodes[i].w + 0.02, ty + 0.12, 0.28, 0.2, C.textLight);
      tx = nx + topNodes[i].w + 0.32;
    }
  }

  // 左右分栏
  var colY = 2.5;
  var colH = 2.5;
  var colW = 4.2;

  // 左栏：项目经理职责
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: colY, w: colW, h: 0.4, fill: { color: C.primary } });
  slide.addText("\u9879\u76ee\u7ecf\u7406\u804c\u8d23", { x: 0.5, y: colY, w: colW, h: 0.4, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });

  var pmDuties = [
    "\u6574\u4f53\u9879\u76ee\u4ea4\u4ed8\u7b2c\u4e00\u8d23\u4efb\u4eba\uff0c\u5bf9\u4ea4\u4ed8\u6210\u679c\u8d1f\u603b\u8d23",
    "\u7edf\u7b39\u5404\u5b50\u9879\u76ee\u8fdb\u5ea6\uff0c\u786e\u4fdd\u6574\u4f53\u4ea4\u4ed8\u8ba1\u5212\u8fbe\u6210",
    "\u534f\u8c03\u5185\u5916\u90e8\u8d44\u6e90\uff0c\u89e3\u51b3\u8de8\u90e8\u95e8\u534f\u4f5c\u95ee\u9898",
    "\u5411\u5ba2\u6237\u5c65\u884c\u9879\u76ee\u8d23\u4efb\uff0c\u53ca\u65f6\u6c9f\u901a\u9879\u76ee\u8fdb\u5c55",
    "\u7ba1\u63a7\u9879\u76ee\u98ce\u9669\uff0c\u53ca\u65f6\u4e0a\u62a5\u548c\u5904\u7f6e\u91cd\u5927\u95ee\u9898"
  ];
  for (var p = 0; p < pmDuties.length; p++) {
    var py = colY + 0.45 + p * 0.4;
    slide.addShape(pres.shapes.OVAL, { x: 0.65, y: py + 0.05, w: 0.12, h: 0.12, fill: { color: C.primary } });
    slide.addText(pmDuties[p], { x: 0.85, y: py, w: colW - 0.45, h: 0.35, fontSize: 9, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "middle", wrap: true, lineSpacingMultiple: 1.2 });
  }

  // 右栏：子项目实施交付责任人职责
  var rx = 0.5 + colW + 0.3;
  slide.addShape(pres.shapes.RECTANGLE, { x: rx, y: colY, w: colW, h: 0.4, fill: { color: C.brandBlue } });
  slide.addText("\u5b50\u9879\u76ee\u5b9e\u65bd\u4ea4\u4ed8\u8d23\u4efb\u4eba\u804c\u8d23", { x: rx, y: colY, w: colW, h: 0.4, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });

  var subDuties = [
    "\u5b50\u9879\u76ee\u4ea4\u4ed8\u7b2c\u4e00\u8d23\u4efb\u4eba\uff0c\u5bf9\u5b50\u9879\u76ee\u6210\u679c\u8d1f\u8d23",
    "\u5236\u5b9a\u5b50\u9879\u76ee\u5b9e\u65bd\u8ba1\u5212\uff0c\u6309\u8282\u70b9\u63a8\u8fdb\u4ea4\u4ed8",
    "\u7ba1\u63a7\u5b50\u9879\u76ee\u8d28\u91cf\u3001\u8fdb\u5ea6\u548c\u6210\u672c",
    "\u53ca\u65f6\u5411\u9879\u76ee\u7ecf\u7406\u62a5\u544a\u5b50\u9879\u76ee\u72b6\u6001\u548c\u98ce\u9669",
    "\u914d\u5408\u96c6\u6210\u6d4b\u8bd5\uff0c\u786e\u4fdd\u5b50\u9879\u76ee\u987a\u5229\u4ea4\u4ed8"
  ];
  for (var s = 0; s < subDuties.length; s++) {
    var sy = colY + 0.45 + s * 0.4;
    slide.addShape(pres.shapes.OVAL, { x: rx + 0.15, y: sy + 0.05, w: 0.12, h: 0.12, fill: { color: C.brandBlue } });
    slide.addText(subDuties[s], { x: rx + 0.35, y: sy, w: colW - 0.45, h: 0.35, fontSize: 9, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "middle", wrap: true, lineSpacingMultiple: 1.2 });
  }

  addBottomLine(slide, 26);
}

// ============================================================
// PAGE 27: 项目启动——售中团队组建
// ============================================================
function page27() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.1 \u9879\u76ee\u542f\u52a8\u2014\u2014\u552e\u4e2d\u56e2\u961f\u7ec4\u5efa", "\u4e94\u5927\u6838\u5fc3\u89d2\u8272\u53ca\u5176\u804c\u8d23");

  var roles = [
    { name: "\u5ba2\u6237\u7ecf\u7406", color: C.primary, icon: "\u2605",
      duties: ["\u5ba2\u6237\u5173\u7cfb\u7ef4\u62a4", "\u9700\u6c42\u5bf9\u63a5", "\u9879\u76ee\u56de\u6b3e\u8ddf\u8e2a", "\u5ba2\u6237\u6ee1\u610f\u5ea6\u7ba1\u7406"] },
    { name: "\u9879\u76ee\u8d1f\u8d23\u4eba", color: C.brandBlue, icon: "\u25c6",
      duties: ["\u9879\u76ee\u6574\u4f53\u7b56\u5212", "\u8d44\u6e90\u534f\u8c03\u5206\u914d", "\u8fdb\u5ea6\u8d28\u91cf\u7ba1\u63a7", "\u56e2\u961f\u7ec4\u5efa\u5e26\u9886"] },
    { name: "\u89e3\u51b3\u65b9\u6848\u7ecf\u7406", color: C.orange, icon: "\u25b2",
      duties: ["\u6280\u672f\u65b9\u6848\u8bbe\u8ba1", "\u5b9e\u65bd\u65b9\u6848\u7f16\u5236", "\u6280\u672f\u96be\u70b9\u89e3\u51b3", "\u65b9\u6848\u5ba1\u6838\u5ba1\u6279"] },
    { name: "\u8fd0\u8425\u7ecf\u7406", color: C.green, icon: "\u25cf",
      duties: ["\u8fd0\u8425\u65b9\u6848\u5236\u5b9a", "\u670d\u52a1\u4f53\u7cfb\u642d\u5efa", "\u7eaf\u8425\u6307\u6807\u8bbe\u8ba1", "\u6301\u7eed\u8fd0\u8425\u4f18\u5316"] },
    { name: "\u5546\u52a1/\u91c7\u8d2d\u7ecf\u7406", color: C.teal, icon: "\u25a0",
      duties: ["\u5408\u540c\u7ba1\u7406", "\u91c7\u8d2d\u6267\u884c", "\u6210\u672c\u7ba1\u63a7", "\u4f9b\u5546\u7ba1\u7406"] }
  ];

  var cardW = 1.7;
  var cardGap = 0.15;
  var cardX = 0.5;
  var cardY = 1.65;
  var cardH = 3.3;

  for (var i = 0; i < roles.length; i++) {
    var cx = cardX + i * (cardW + cardGap);
    var r = roles[i];
    // 卡片背景
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: cardY, w: cardW, h: cardH, fill: { color: C.white }, line: { color: r.color, width: 1.5 } });
    // 顶部色块
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: cardY, w: cardW, h: 0.7, fill: { color: r.color } });
    // 图标
    slide.addText(r.icon, { x: cx, y: cardY + 0.05, w: cardW, h: 0.3, fontSize: 16, fontFace: "Microsoft YaHei", color: C.white, align: "center", valign: "middle" });
    // 角色名
    slide.addText(r.name, { x: cx, y: cardY + 0.35, w: cardW, h: 0.3, fontSize: 11, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });
    // 职责列表
    for (var j = 0; j < r.duties.length; j++) {
      var dy = cardY + 0.85 + j * 0.58;
      slide.addShape(pres.shapes.OVAL, { x: cx + 0.1, y: dy + 0.06, w: 0.08, h: 0.08, fill: { color: r.color } });
      slide.addText(r.duties[j], { x: cx + 0.25, y: dy, w: cardW - 0.35, h: 0.5, fontSize: 8.5, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", wrap: true, lineSpacingMultiple: 1.2 });
    }
  }

  addBottomLine(slide, 27);
}

// ============================================================
// PAGE 28: 项目启动——售中团队组建（续）
// ============================================================
function page28() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.1 \u9879\u76ee\u542f\u52a8\u2014\u2014\u552e\u4e2d\u56e2\u961f\u7ec4\u5efa", "\u4e09\u7c7b\u56e2\u961f\u67b6\u6784\uff1a\u5546\u673a\u56e2\u961f \u00b7 \u5185\u90e8\u652f\u6491 \u00b7 \u5916\u90e8\u5408\u4f5c");

  var teams = [
    {
      title: "\u5546\u673a\u56e2\u961f", color: C.primary, sub: "\u5185\u90e8\u4eba\u5458",
      members: ["\u5ba2\u6237\u7ecf\u7406\uff1a\u5ba2\u6237\u5173\u7cfb\u5bf9\u63a5", "\u9879\u76ee\u7ecf\u7406\uff1a\u9879\u76ee\u7b56\u5212\u7ba1\u63a7", "\u89e3\u51b3\u65b9\u6848\u7ecf\u7406\uff1a\u6280\u672f\u65b9\u6848\u8bbe\u8ba1", "\u5546\u52a1\u7ecf\u7406\uff1a\u5408\u540c\u4e0e\u62a5\u4ef7", "\u8fd0\u8425\u7ecf\u7406\uff1a\u540e\u671f\u8fd0\u8425\u89c4\u5212"]
    },
    {
      title: "\u5185\u90e8\u652f\u6491", color: C.brandBlue, sub: "\u804c\u80fd\u90e8\u95e8\u534f\u8c03",
      members: ["\u6cd5\u52a1\uff1a\u5408\u540c\u5ba1\u67e5\u3001\u6cd5\u5f8b\u98ce\u9669\u8bc4\u4f30", "\u8d22\u52a1\uff1a\u9884\u7b97\u5ba1\u6838\u3001\u6210\u672c\u6838\u7b97\u3001\u56de\u6b3e\u7ba1\u7406", "\u8fd0\u7ef4\uff1a\u4ea4\u7ef4\u63a5\u53e3\u3001\u8fd0\u7ef4\u670d\u52a1\u4fdd\u969c", "\u91c7\u8d2d\uff1a\u91c7\u8d2d\u6d41\u7a0b\u6267\u884c\u3001\u4f9b\u5546\u7ba1\u7406", "\u5b89\u5168\uff1a\u7b49\u7ea7\u4fdd\u62a4\u3001\u5b89\u5168\u5ba1\u67e5"]
    },
    {
      title: "\u5916\u90e8\u5408\u4f5c", color: C.orange, sub: "\u5408\u4f5c\u751f\u6001\u4f53\u7cfb",
      members: ["\u4e13\u4e1a\u516c\u53f8\uff1a\u4e13\u4e1a\u80fd\u529b\u8865\u5145\u3001\u9879\u76ee\u534f\u540c\u4ea4\u4ed8", "\u751f\u6001\u4f19\u4f34\uff1a\u4e0a\u4e0b\u6e38\u4f9b\u5e94\u5546\u3001\u6280\u672f\u96c6\u6210\u5546", "\u8bbe\u5907\u4f9b\u5e94\u5546\uff1a\u786c\u4ef6\u8bbe\u5907\u4f9b\u5e94\u3001\u552e\u540e\u670d\u52a1", "\u8f6f\u4ef6\u4f9b\u5e94\u5546\uff1a\u8f6f\u4ef6\u6388\u6743\u3001\u6280\u672f\u652f\u6301", "\u670d\u52a1\u5916\u5305\uff1a\u4eba\u529b\u5916\u5305\u3001\u8fd0\u7ef4\u5916\u5305\u670d\u52a1"]
    }
  ];

  var colW = 2.8;
  var colGap = 0.25;
  var colX = 0.5;
  var colY = 1.65;
  var colH = 3.4;

  for (var i = 0; i < teams.length; i++) {
    var cx = colX + i * (colW + colGap);
    var t = teams[i];
    // 卡片
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: colY, w: colW, h: colH, fill: { color: C.white }, line: { color: t.color, width: 1.5 } });
    // 顶部
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: colY, w: colW, h: 0.6, fill: { color: t.color } });
    slide.addText(t.title, { x: cx, y: colY + 0.03, w: colW, h: 0.35, fontSize: 13, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });
    slide.addText(t.sub, { x: cx, y: colY + 0.35, w: colW, h: 0.22, fontSize: 9, fontFace: "Microsoft YaHei", color: C.white, align: "center", valign: "middle" });
    // 成员列表
    for (var j = 0; j < t.members.length; j++) {
      var my = colY + 0.75 + j * 0.5;
      slide.addShape(pres.shapes.RECTANGLE, { x: cx + 0.1, y: my, w: colW - 0.2, h: 0.45, fill: { color: i % 2 === 0 ? C.cardBg : C.accentLight }, line: { color: C.borderLight, width: 0.5 } });
      slide.addText(t.members[j], { x: cx + 0.15, y: my, w: colW - 0.3, h: 0.45, fontSize: 8.5, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "middle", wrap: true, lineSpacingMultiple: 1.15 });
    }
  }

  addBottomLine(slide, 28);
}

// ============================================================
// PAGE 29: 项目启动——子项目管控
// ============================================================
function page29() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.1 \u9879\u76ee\u542f\u52a8\u2014\u2014\u5b50\u9879\u76ee\u7ba1\u63a7", "\u516d\u6b65\u9aa4\u7f16\u53f7\u6d41\u7a0b\uff1a\u4ece\u660e\u786e\u76ee\u6807\u5230\u96c6\u6210\u6d4b\u8bd5\u4ea4\u4ed8");

  var steps = [
    { num: "1", name: "\u660e\u786e\u76ee\u6807", desc: "\u660e\u786e\u5b50\u9879\u76ee\u5efa\u8bbe\u76ee\u6807\u3001\u4ea4\u4ed8\u6807\u51c6\u53ca\u9a8c\u6536\u6761\u4ef6", color: C.primary },
    { num: "2", name: "\u62c6\u89e3WBS", desc: "\u5c06\u5b50\u9879\u76ee\u62c6\u89e3\u4e3a\u53ef\u7ba1\u7406\u7684\u5de5\u4f5c\u5305\uff0c\u660e\u786e\u6bcf\u4e2a\u5305\u7684\u4ea4\u4ed8\u7269", color: C.brandBlue },
    { num: "3", name: "\u5236\u5b9a\u8ba1\u5212", desc: "\u5236\u5b9a\u5b50\u9879\u76ee\u5b9e\u65bd\u8ba1\u5212\uff0c\u660e\u786e\u65f6\u95f4\u8282\u70b9\u3001\u91cc\u7a0b\u7891\u548c\u4f9d\u8d56\u5173\u7cfb", color: C.orange },
    { num: "4", name: "\u5206\u914d\u8d44\u6e90\u7ba1\u7406\u98ce\u9669", desc: "\u5408\u7406\u5206\u914d\u4eba\u529b\u3001\u7269\u529b\u8d44\u6e90\uff0c\u8bc6\u522b\u5e76\u5236\u5b9a\u98ce\u9669\u5e94\u5bf9\u63aa\u65bd", color: C.green },
    { num: "5", name: "\u6267\u884c\u76d1\u63a7", desc: "\u6309\u8ba1\u5212\u6267\u884c\uff0c\u5b9e\u65bd\u8fc7\u7a0b\u4e2d\u7684\u8d28\u91cf\u3001\u8fdb\u5ea6\u3001\u6210\u672c\u76d1\u63a7", color: C.teal },
    { num: "6", name: "\u96c6\u6210\u6d4b\u8bd5\u4ea4\u4ed8", desc: "\u5b50\u9879\u76ee\u96c6\u6210\u3001\u8054\u5408\u6d4b\u8bd5\u3001\u9a8c\u6536\u4ea4\u4ed8\u3001\u8d44\u6599\u79fb\u4ea4", color: C.accentDark }
  ];

  var sx = 0.5;
  var sy = 1.7;
  var sw = 1.42;
  var sh = 2.8;
  var sGap = 0.12;

  for (var i = 0; i < steps.length; i++) {
    var cx = sx + i * (sw + sGap);
    var s = steps[i];
    // 卡片
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: sy, w: sw, h: sh, fill: { color: C.white }, line: { color: s.color, width: 1.5 } });
    // 编号圆
    slide.addShape(pres.shapes.OVAL, { x: cx + sw / 2 - 0.3, y: sy + 0.15, w: 0.6, h: 0.6, fill: { color: s.color } });
    slide.addText(s.num, { x: cx + sw / 2 - 0.3, y: sy + 0.15, w: 0.6, h: 0.6, fontSize: 20, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });
    // 步骤名
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: sy + 0.85, w: sw, h: 0.5, fill: { color: s.color } });
    slide.addText(s.name, { x: cx + 0.05, y: sy + 0.85, w: sw - 0.1, h: 0.5, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", wrap: true });
    // 描述
    slide.addText(s.desc, { x: cx + 0.1, y: sy + 1.45, w: sw - 0.2, h: 1.25, fontSize: 8.5, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", wrap: true, lineSpacingMultiple: 1.3 });
    // 箭头
    if (i < steps.length - 1) {
      addArrowRight(slide, cx + sw + 0.005, sy + sh / 2 - 0.1, sGap - 0.01, 0.2, C.textLight);
    }
  }

  addBottomLine(slide, 29);
}

// ============================================================
// PAGE 30: 项目启动——子项目规划常见问题
// ============================================================
function page30() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.1 \u9879\u76ee\u542f\u52a8\u2014\u2014\u5b50\u9879\u76ee\u89c4\u5212\u5e38\u89c1\u95ee\u9898", "\u4e09\u5927\u5e38\u89c1\u95ee\u9898\u53ca\u89e3\u51b3\u601d\u8def");

  var problems = [
    {
      num: "01", title: "\u5982\u4f55\u786e\u8ba4\u5b50\u9879\u76ee\u95f4\u7684\u5efa\u8bbe\u4f18\u5148\u7ea7", color: C.primary,
      q: "\u591a\u4e2a\u5b50\u9879\u76ee\u5e76\u884c\u542f\u52a8\uff0c\u5982\u4f55\u786e\u5b9a\u5efa\u8bbe\u5e8f\u5217\uff1f",
      a: [
        "\u6309\u4e1a\u52a1\u4f9d\u8d56\u5173\u7cfb\u6392\u5e8f\uff1a\u57fa\u7840\u8bbe\u65bd\u4f18\u5148\uff0c\u4e1a\u52a1\u7cfb\u7edf\u6b21\u4e4b",
        "\u6309\u5ba2\u6237\u4f18\u5148\u7ea7\u6392\u5e8f\uff1a\u5ba2\u6237\u5173\u6ce8\u7684\u6838\u5fc3\u529f\u80fd\u4f18\u5148\u5efa\u8bbe",
        "\u6309\u6280\u672f\u53ef\u884c\u6027\u6392\u5e8f\uff1a\u6210\u719f\u5ea6\u9ad8\u7684\u4f18\u5148\uff0c\u63a2\u7d22\u6027\u7684\u540e\u7f6e"
      ]
    },
    {
      num: "02", title: "\u5b50\u9879\u76ee\u4f9d\u8d56\u5173\u7cfb\u5982\u4f55\u786e\u8ba4", color: C.brandBlue,
      q: "\u5b50\u9879\u76ee\u95f4\u5b58\u5728\u524d\u540e\u4f9d\u8d56\uff0c\u5982\u4f55\u68b3\u7406\u548c\u7ba1\u7406\uff1f",
      a: [
        "\u7ed8\u5236\u4f9d\u8d56\u5173\u7cfb\u77e9\u9635\uff0c\u660e\u786e\u5404\u5b50\u9879\u76ee\u7684\u524d\u7f6e\u548c\u540e\u7f6e\u6761\u4ef6",
        "\u5236\u5b9a\u4f9d\u8d56\u7ba1\u7406\u8ba1\u5212\uff0c\u5173\u952e\u8def\u5f84\u4e0a\u8bbe\u7f6e\u7f13\u51b2\u533a\u548c\u56de\u9000\u65b9\u6848",
        "\u5efa\u7acb\u4f9d\u8d56\u53d8\u66f4\u673a\u5236\uff0c\u4f9d\u8d56\u53d8\u66f4\u65f6\u53ca\u65f6\u8bc4\u4f30\u5f71\u54cd\u8303\u56f4"
      ]
    },
    {
      num: "03", title: "\u5b50\u9879\u76ee\u62c6\u89e3\u8fc7\u4e8e\u590d\u6742", color: C.orange,
      q: "\u5b50\u9879\u76ee\u62c6\u89e3\u7c92\u5ea6\u592a\u7ec6\uff0c\u5bfc\u81f4\u7ba1\u7406\u6210\u672c\u9ad8\uff0c\u5982\u4f55\u5e73\u8861\uff1f",
      a: [
        "\u9075\u5faa\u201c\u5141\u8bb8\u5185\u90e8\u805a\u5408\u3001\u7981\u6b62\u8de8\u5c42\u4f9d\u8d56\u201d\u539f\u5219\uff0c\u9ad8\u5185\u805a\u5408\u5ea6\u4f18\u5148\u62c6\u5206",
        "\u5236\u5b9a\u62c6\u89e3\u7c92\u5ea6\u6807\u51c6\uff1a\u5355\u4e2a\u5b50\u9879\u76ee\u5e94\u53ef\u72ec\u7acb\u9a8c\u6536\u548c\u4ea4\u4ed8",
        "\u5b9a\u671f\u590d\u76d8\u62c6\u89e3\u5408\u7406\u6027\uff0c\u6839\u636e\u5b9e\u9645\u6267\u884c\u60c5\u51b5\u52a8\u6001\u8c03\u6574\u7c92\u5ea6"
      ]
    }
  ];

  var cardW = 2.8;
  var cardGap = 0.25;
  var cardX = 0.5;
  var cardY = 1.65;
  var cardH = 3.4;

  for (var i = 0; i < problems.length; i++) {
    var cx = cardX + i * (cardW + cardGap);
    var p = problems[i];
    // 卡片
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: cardY, w: cardW, h: cardH, fill: { color: C.white }, line: { color: p.color, width: 1.5 } });
    // 编号
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: cardY, w: cardW, h: 0.6, fill: { color: p.color } });
    slide.addText(p.num, { x: cx + 0.15, y: cardY, w: 0.8, h: 0.6, fontSize: 24, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "left", valign: "middle" });
    slide.addText(p.title, { x: cx + 0.9, y: cardY, w: cardW - 1.0, h: 0.6, fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "left", valign: "middle", wrap: true, lineSpacingMultiple: 1.15 });
    // 问题
    slide.addShape(pres.shapes.RECTANGLE, { x: cx + 0.1, y: cardY + 0.7, w: cardW - 0.2, h: 0.65, fill: { color: C.pinkLight }, line: { color: p.color, width: 0.5, dashType: "dash" } });
    slide.addText("Q: " + p.q, { x: cx + 0.15, y: cardY + 0.72, w: cardW - 0.3, h: 0.6, fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "left", valign: "middle", wrap: true, lineSpacingMultiple: 1.2 });
    // 解答
    slide.addText("A:", { x: cx + 0.15, y: cardY + 1.45, w: 0.3, h: 0.25, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: p.color, align: "left", valign: "top" });
    for (var j = 0; j < p.a.length; j++) {
      var ay = cardY + 1.45 + j * 0.62;
      slide.addShape(pres.shapes.OVAL, { x: cx + 0.35, y: ay + 0.06, w: 0.08, h: 0.08, fill: { color: p.color } });
      slide.addText(p.a[j], { x: cx + 0.5, y: ay, w: cardW - 0.65, h: 0.55, fontSize: 8.5, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", wrap: true, lineSpacingMultiple: 1.2 });
    }
  }

  addBottomLine(slide, 30);
}

// ============================================================
// PAGE 31: 项目启动——项目开工会
// ============================================================
function page31() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.1 \u9879\u76ee\u542f\u52a8\u2014\u2014\u9879\u76ee\u5f00\u5de5\u4f1a", "\u660e\u786e\u76ee\u6807 \u00b7 \u7edf\u4e00\u8ba4\u8bc6 \u00b7 \u5206\u5de5\u5e03\u7f6e \u00b7 \u8d44\u6e90\u5c31\u4f4d");

  var sections = [
    {
      title: "\u5f00\u5de5\u4f1a\u76ee\u7684", color: C.primary, icon: "\u2460",
      points: ["\u660e\u786e\u9879\u76ee\u76ee\u6807\u4e0e\u8303\u56f4\uff0c\u786e\u4fdd\u5168\u5458\u7edf\u4e00\u8ba4\u8bc6", "\u5ba3\u8d2f\u9879\u76ee\u5b9e\u65bd\u65b9\u6848\uff0c\u660e\u786e\u5404\u9636\u6bb5\u4ea4\u4ed8\u7269", "\u7edf\u4e00\u9879\u76ee\u7ba1\u7406\u89c4\u8303\u4e0e\u6c9f\u901a\u673a\u5236"]
    },
    {
      title: "\u53c2\u4f1a\u4eba\u5458", color: C.brandBlue, icon: "\u2461",
      points: ["\u5ba2\u6237\u4ee3\u8868\u53ca\u9879\u76ee\u76f8\u5173\u65b9", "\u9879\u76ee\u7ecf\u7406\u53ca\u6838\u5fc3\u56e2\u961f\u6210\u5458", "\u5b50\u9879\u76ee\u8d1f\u8d23\u4eba\u53ca\u5173\u952e\u804c\u80fd\u90e8\u95e8", "\u5916\u90e8\u5408\u4f5c\u4f19\u4f34\u4ee3\u8868"]
    },
    {
      title: "\u4f1a\u8bae\u8bae\u7a0b", color: C.orange, icon: "\u2462",
      points: ["\u9879\u76ee\u80cc\u666f\u4ecb\u7ecd\u4e0e\u76ee\u6807\u5ba3\u8d2f", "\u9879\u76ee\u8303\u56f4\u4e0e\u4ea4\u4ed8\u6210\u679c\u8bf4\u660e", "\u5b9e\u65bd\u8ba1\u5212\u53ca\u65f6\u95f4\u8282\u70b9\u5b89\u6392", "\u89d2\u8272\u5206\u5de5\u4e0e\u804c\u8d23\u5212\u5206", "\u98ce\u9669\u8bc6\u522b\u4e0e\u5e94\u5bf9\u63aa\u65bd", "\u6c9f\u901a\u673a\u5236\u4e0e\u5468\u62a5\u5236\u5ea6"]
    },
    {
      title: "\u4f1a\u8bae\u8f93\u51fa", color: C.green, icon: "\u2463",
      points: ["\u9879\u76ee\u5f00\u5de5\u4f1a\u7eaa\u8981\uff08\u4f1a\u8bae\u8bb0\u5f55\uff09", "\u9879\u76ee\u7ba1\u7406\u8ba1\u5212\u786e\u8ba4\u7248", "\u9879\u76ee\u8d23\u4efb\u5206\u5de5\u8868\u786e\u8ba4", "\u4e0b\u4e00\u6b65\u5de5\u4f5c\u5b89\u6392\u53ca\u8d23\u4efb\u4eba"]
    }
  ];

  var colW = 4.2;
  var colGap = 0.3;
  var cardY = 1.6;
  var cardH = 1.6;

  for (var i = 0; i < sections.length; i++) {
    var col = i % 2;
    var row = Math.floor(i / 2);
    var cx = 0.5 + col * (colW + colGap);
    var cy = cardY + row * (cardH + 0.15);
    var s = sections[i];

    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: cy, w: colW, h: cardH, fill: { color: C.white }, line: { color: s.color, width: 1.5 } });
    // 标题栏
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: cy, w: colW, h: 0.4, fill: { color: s.color } });
    slide.addText(s.icon + "  " + s.title, { x: cx + 0.1, y: cy, w: colW - 0.2, h: 0.4, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "left", valign: "middle" });
    // 要点
    for (var j = 0; j < s.points.length; j++) {
      var py = cy + 0.5 + j * 0.26;
      slide.addShape(pres.shapes.OVAL, { x: cx + 0.15, y: py + 0.05, w: 0.08, h: 0.08, fill: { color: s.color } });
      slide.addText(s.points[j], { x: cx + 0.3, y: py, w: colW - 0.45, h: 0.24, fontSize: 9, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "middle", wrap: true, lineSpacingMultiple: 1.15 });
    }
  }

  addBottomLine(slide, 31);
}

// ============================================================
// PAGE 32: 启动阶段——实施方案制定和内外部审核
// ============================================================
function page32() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.1 \u542f\u52a8\u9636\u6bb5\u2014\u2014\u5b9e\u65bd\u65b9\u6848\u5236\u5b9a\u548c\u5185\u5916\u90e8\u5ba1\u6838", "\u4e94\u6b65\u6d41\u7a0b\uff1a\u9700\u6c42\u786e\u8ba4 \u2192 \u65b9\u6848\u5236\u5b9a \u2192 \u65b9\u6848\u5ba1\u6838 \u2192 \u9884\u7b97\u7f16\u5236 \u2192 \u9879\u76ee\u542f\u52a8");

  var steps = [
    { name: "\u9700\u6c42\u786e\u8ba4", color: C.primary, details: ["\u5ba2\u6237\u9700\u6c42\u590d\u6838\u786e\u8ba4", "\u529f\u80fd\u6e05\u5355\u68b3\u7406", "\u975e\u529f\u80fd\u9700\u6c42\u660e\u786e", "\u9700\u6c42\u53d8\u66f4\u63a7\u5236"] },
    { name: "\u5b9e\u65bd\u65b9\u6848\u5236\u5b9a", color: C.brandBlue, details: ["\u6280\u672f\u67b6\u6784\u8bbe\u8ba1", "\u5b50\u9879\u76ee\u62c6\u5206\u4e0e\u4f9d\u8d56\u5173\u7cfb", "\u5b9e\u65bd\u8def\u7ebf\u56fe\u4e0e\u65f6\u95f4\u8ba1\u5212", "\u8d44\u6e90\u9700\u6c42\u4e0e\u6210\u672c\u9884\u4f30"] },
    { name: "\u5b9e\u65bd\u65b9\u6848\u5ba1\u6838", color: C.orange, details: ["\u5185\u90e8\u6280\u672f\u5ba1\u6838", "\u5185\u90e8\u5546\u52a1\u5ba1\u6838", "\u5916\u90e8\u5ba2\u6237\u5ba1\u6838", "\u5ba1\u6838\u610f\u89c1\u6574\u6539\u8ffd\u8e2a"] },
    { name: "\u9879\u76ee\u9884\u7b97\u7f16\u5236", color: C.green, details: ["\u6210\u672c\u660e\u7ec6\u7f16\u5236", "\u9884\u7b97\u5ba1\u6279\u6d41\u7a0b", "\u5408\u540c\u5bf9\u7167\u6838\u67e5", "\u9884\u7b97\u786e\u8ba4\u7b7e\u6279"] },
    { name: "\u9879\u76ee\u6b63\u5f0f\u542f\u52a8", color: C.teal, details: ["\u5f00\u5de5\u4f1a\u53ec\u5f00", "\u56e2\u961f\u5c31\u4f4d", "\u8d44\u6e90\u5c31\u7eea", "\u5b9e\u65bd\u8fdb\u5165\u6267\u884c\u9636\u6bb5"] }
  ];

  var sx = 0.4;
  var sy = 1.6;
  var sw = 1.72;
  var sh = 3.0;
  var sGap = 0.15;

  for (var i = 0; i < steps.length; i++) {
    var cx = sx + i * (sw + sGap);
    var s = steps[i];
    // 卡片
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: sy, w: sw, h: sh, fill: { color: C.white }, line: { color: s.color, width: 1.5 } });
    // 顶部
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: sy, w: sw, h: 0.5, fill: { color: s.color } });
    slide.addText("Step " + (i + 1), { x: cx, y: sy + 0.02, w: sw, h: 0.2, fontSize: 8, fontFace: "Microsoft YaHei", color: C.white, align: "center", valign: "middle" });
    slide.addText(s.name, { x: cx, y: sy + 0.22, w: sw, h: 0.25, fontSize: 11, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });
    // 要点
    for (var j = 0; j < s.details.length; j++) {
      var dy = sy + 0.6 + j * 0.55;
      slide.addShape(pres.shapes.RECTANGLE, { x: cx + 0.08, y: dy, w: sw - 0.16, h: 0.5, fill: { color: j % 2 === 0 ? C.cardBg : C.white }, line: { color: C.borderLight, width: 0.5 } });
      slide.addShape(pres.shapes.OVAL, { x: cx + 0.12, y: dy + 0.08, w: 0.08, h: 0.08, fill: { color: s.color } });
      slide.addText(s.details[j], { x: cx + 0.25, y: dy, w: sw - 0.37, h: 0.5, fontSize: 8.5, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "middle", wrap: true, lineSpacingMultiple: 1.2 });
    }
    // 箭头
    if (i < steps.length - 1) {
      addArrowRight(slide, cx + sw + 0.005, sy + 0.2, sGap - 0.01, 0.16, C.textLight);
    }
  }

  addBottomLine(slide, 32);
}

// ============================================================
// PAGE 33: 后向采购——采购流程优化
// ============================================================
function page33() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.2 \u540e\u5411\u91c7\u8d2d\u2014\u2014\u91c7\u8d2d\u6d41\u7a0b\u4f18\u5316", "\u4ece\u7ebf\u7d22\u5f55\u5165\u5230\u9879\u76ee\u9a8c\u6536\u7684\u5168\u6d41\u7a0b\u4f18\u5316");

  // 主流程节点
  var flowNodes = [
    { name: "\u7ebf\u7d22\u5f55\u5165", key: false },
    { name: "\u5546\u673a\u521b\u5efa", key: true, tag: "\u4e2d\u53f0\u628a\u5173" },
    { name: "\u7ec4\u5efa\u56e2\u961f", key: false },
    { name: "\u65b9\u6848\u5236\u5b9a", key: true, tag: "\u4e1a\u52a1\u89e3\u6784" },
    { name: "\u5e94\u6807\u7b7e\u7ea6", key: false },
    { name: "\u9879\u76ee\u542f\u52a8", key: true, tag: "\u4ea4\u5e95\u548c\u603b\u8bbe" },
    { name: "\u9879\u76ee\u91c7\u8d2d", key: false },
    { name: "\u9879\u76ee\u5b9e\u65bd", key: false },
    { name: "\u9879\u76ee\u9a8c\u6536", key: false }
  ];

  var fx = 0.3;
  var fy = 1.65;
  var fw = 0.98;
  var fh = 0.5;
  var fGap = 0.09;

  for (var i = 0; i < flowNodes.length; i++) {
    var cx = fx + i * (fw + fGap);
    var n = flowNodes[i];
    var bgColor = n.key ? C.primary : C.brandBlue;
    addFlowNode(slide, cx, fy, fw, fh, n.name, { bg: bgColor, fontSize: 9 });
    if (n.key) {
      // 关键节点标签
      slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: fy - 0.3, w: fw, h: 0.25, fill: { color: C.orange } });
      slide.addText(n.tag, { x: cx, y: fy - 0.3, w: fw, h: 0.25, fontSize: 7.5, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });
      // 连接竖线
      slide.addShape(pres.shapes.RECTANGLE, { x: cx + fw / 2 - 0.005, y: fy - 0.05, w: 0.01, h: 0.05, fill: { color: C.orange } });
    }
    if (i < flowNodes.length - 1) {
      addArrowRight(slide, cx + fw + 0.005, fy + fh / 2 - 0.08, fGap - 0.01, 0.16, C.textLight);
    }
  }

  // 下方优化说明
  var optY = 2.7;
  slide.addText("\u6d41\u7a0b\u4f18\u5316\u8981\u70b9\uff1a", { x: 0.5, y: optY, w: 2.0, h: 0.35, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle" });

  var opts = [
    { title: "\u4e2d\u53f0\u628a\u5173", desc: "\u5546\u673a\u5f55\u5165\u4e2d\u53f0\u7edf\u4e00\u7ba1\u7406\uff0c\u786e\u4fdd\u5546\u673a\u8d28\u91cf\u53ca\u683c\u7387\u8fbe\u6807", color: C.primary },
    { title: "\u4e1a\u52a1\u89e3\u6784", desc: "\u65b9\u6848\u5236\u5b9a\u9636\u6bb5\u8fdb\u884c\u4e1a\u52a1\u89e3\u6784\uff0c\u660e\u786e\u91c7\u8d2d\u9700\u6c42\u548c\u4ea4\u4ed8\u6807\u51c6", color: C.brandBlue },
    { title: "\u4ea4\u5e95\u548c\u603b\u8bbe", desc: "\u9879\u76ee\u542f\u52a8\u65f6\u5b8c\u6210\u4ea4\u5e95\u548c\u603b\u4f53\u8bbe\u8ba1\uff0c\u786e\u4fdd\u4ea4\u4ed8\u8def\u5f84\u660e\u786e", color: C.orange }
  ];

  var ocardW = 2.85;
  var ocardGap = 0.2;
  for (var k = 0; k < opts.length; k++) {
    var ox = 0.5 + k * (ocardW + ocardGap);
    slide.addShape(pres.shapes.RECTANGLE, { x: ox, y: optY + 0.4, w: ocardW, h: 1.6, fill: { color: C.white }, line: { color: opts[k].color, width: 1.5 } });
    slide.addShape(pres.shapes.RECTANGLE, { x: ox, y: optY + 0.4, w: ocardW, h: 0.4, fill: { color: opts[k].color } });
    slide.addText(opts[k].title, { x: ox, y: optY + 0.4, w: ocardW, h: 0.4, fontSize: 11, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });
    slide.addText(opts[k].desc, { x: ox + 0.12, y: optY + 0.85, w: ocardW - 0.24, h: 1.1, fontSize: 9, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", wrap: true, lineSpacingMultiple: 1.3 });
  }

  addBottomLine(slide, 33);
}

// ============================================================
// PAGE 34: 后向采购——分场景采购流程
// ============================================================
function page34() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.2 \u540e\u5411\u91c7\u8d2d\u2014\u2014\u5206\u573a\u666f\u91c7\u8d2d\u6d41\u7a0b", "\u56db\u7c7b\u91c7\u8d2d\u573a\u666f\u4e0e\u4e09\u9879\u4f18\u5316\u63aa\u65bd");

  // 4个采购场景
  var scenarios = [
    { num: "\u573a\u666f1", name: "\u901a\u7528\u96c6\u91c7", color: C.primary, desc: "\u91c7\u8d2d\u76ee\u5f55\u5185\u7684\u6807\u51c6\u4ea7\u54c1\uff0c\u7edf\u4e00\u96c6\u4e2d\u91c7\u8d2d\uff0c\u7f29\u77ed\u6d41\u7a0b\u3001\u964d\u4f4e\u6210\u672c", flow: ["\u9700\u6c42\u786e\u8ba4", "\u76ee\u5f55\u67e5\u8be2", "\u4e0b\u5355\u91c7\u8d2d", "\u5230\u8d27\u9a8c\u6536"] },
    { num: "\u573a\u666f2", name: "\u5408\u4f5c\u4f19\u4f34\u9009\u62e9", color: C.brandBlue, desc: "\u9700\u9009\u62e9\u5408\u4f5c\u4f19\u4f34\u7684\u9879\u76ee\uff0c\u901a\u8fc7\u62db\u6807\u6216\u8c08\u5224\u786e\u5b9a\u5408\u4f5c\u65b9", flow: ["\u9700\u6c42\u53d1\u5e03", "\u62db\u6807/\u8c08\u5224", "\u8bc4\u5ba1\u9009\u62e9", "\u5408\u540c\u7b7e\u8ba2"] },
    { num: "\u573a\u666f3", name: "\u5355\u4e00\u6765\u6e90", color: C.orange, desc: "\u6280\u672f\u4e13\u5229\u6216\u552f\u4e00\u4f9b\u5e94\uff0c\u7ecf\u8bba\u8bc1\u540e\u91c7\u7528\u5355\u4e00\u6765\u6e90\u91c7\u8d2d", flow: ["\u4e13\u5229\u8bba\u8bc1", "\u5ba1\u6279\u7533\u8bf7", "\u5355\u4e00\u6765\u6e90\u8c08\u5224", "\u5408\u540c\u7b7e\u8ba2"] },
    { num: "\u573a\u666f4", name: "\u7ade\u4e89\u6027\u91c7\u8d2d", color: C.green, desc: "\u9700\u591a\u4e2a\u4f9b\u5e94\u5546\u7ade\u4e89\u7684\u9879\u76ee\uff0c\u901a\u8fc7\u7ade\u4e89\u6027\u8c08\u5224\u6216\u62db\u6807\u786e\u5b9a", flow: ["\u9700\u6c42\u53d1\u5e03", "\u7ade\u4e89\u6027\u8c08\u5224", "\u8bc4\u5ba1\u9009\u62e9", "\u5408\u540c\u7b7e\u8ba2"] }
  ];

  var sx = 0.3;
  var sy = 1.55;
  var sw = 2.3;
  var sh = 2.45;
  var sGap = 0.12;

  for (var i = 0; i < scenarios.length; i++) {
    var cx = sx + i * (sw + sGap);
    var s = scenarios[i];
    // 卡片
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: sy, w: sw, h: sh, fill: { color: C.white }, line: { color: s.color, width: 1.5 } });
    // 顶部
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: sy, w: sw, h: 0.55, fill: { color: s.color } });
    slide.addText(s.num, { x: cx, y: sy + 0.03, w: sw, h: 0.22, fontSize: 8, fontFace: "Microsoft YaHei", color: C.white, align: "center", valign: "middle" });
    slide.addText(s.name, { x: cx, y: sy + 0.24, w: sw, h: 0.28, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });
    // 描述
    slide.addText(s.desc, { x: cx + 0.1, y: sy + 0.62, w: sw - 0.2, h: 0.55, fontSize: 8.5, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", wrap: true, lineSpacingMultiple: 1.25 });
    // 流程步骤
    for (var j = 0; j < s.flow.length; j++) {
      var fy = sy + 1.25 + j * 0.28;
      slide.addShape(pres.shapes.RECTANGLE, { x: cx + 0.1, y: fy, w: sw - 0.2, h: 0.25, fill: { color: s.color }, line: { color: s.color, width: 0.5 } });
      slide.addText((j + 1) + ". " + s.flow[j], { x: cx + 0.15, y: fy, w: sw - 0.3, h: 0.25, fontSize: 8, fontFace: "Microsoft YaHei", color: C.white, align: "left", valign: "middle" });
    }
  }

  // 底部三项措施
  var measures = [
    { name: "\u63aa\u65bd1\uff1a\u5206\u7c7b\u5206\u7ea7\u7ba1\u7406", desc: "\u6309\u91c7\u8d2d\u91d1\u989d\u548c\u590d\u6742\u5ea6\u5206\u7ea7\u5ba1\u6279\uff0c\u63d0\u9ad8\u91c7\u8d2d\u6548\u7387" },
    { name: "\u63aa\u65bd2\uff1a\u91c7\u8d2d\u524d\u7f6e\u5ba1\u67e5", desc: "\u91c7\u8d2d\u9700\u6c42\u53d1\u5e03\u524d\u5b8c\u6210\u6280\u672f\u5ba1\u67e5\u548c\u9884\u7b97\u5ba1\u6838" },
    { name: "\u63aa\u65bd3\uff1a\u5408\u540c\u8054\u52a8\u7ba1\u7406", desc: "\u91c7\u8d2d\u5408\u540c\u4e0e\u524d\u5411\u5408\u540c\u8054\u52a8\uff0c\u786e\u4fdd\u4e00\u81f4\u6027" }
  ];
  var mY = 4.25;
  var mW = 2.85;
  var mGap = 0.2;
  for (var m = 0; m < measures.length; m++) {
    var mx = 0.5 + m * (mW + mGap);
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: mx, y: mY, w: mW, h: 0.7, fill: { color: C.accentLight }, line: { color: C.primary, width: 1 }, rectRadius: 0.03 });
    slide.addText(measures[m].name, { x: mx + 0.1, y: mY + 0.03, w: mW - 0.2, h: 0.25, fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle" });
    slide.addText(measures[m].desc, { x: mx + 0.1, y: mY + 0.28, w: mW - 0.2, h: 0.4, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", wrap: true, lineSpacingMultiple: 1.2 });
  }

  addBottomLine(slide, 34);
}

// ============================================================
// PAGE 35: 过程管控——自主可控、交付主导
// ============================================================
function page35() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.3 \u8fc7\u7a0b\u7ba1\u63a7\u2014\u2014\u81ea\u4e3b\u53ef\u63a7\u3001\u4ea4\u4ed8\u4e3b\u5bfc", "\u6293\u4f4f\u4ea4\u4ed8\u5173\u952e\u70b9\uff0c\u201c\u4ea4\u201d\u4e0e\u201c\u4ed8\u201d\u53cc\u8f6e\u9a71\u52a8");

  // 左栏"交"
  var leftX = 0.5;
  var colW = 4.2;
  var colY = 1.6;
  var colH = 2.7;

  slide.addShape(pres.shapes.RECTANGLE, { x: leftX, y: colY, w: colW, h: colH, fill: { color: C.white }, line: { color: C.primary, width: 1.5 } });
  slide.addShape(pres.shapes.RECTANGLE, { x: leftX, y: colY, w: colW, h: 0.5, fill: { color: C.primary } });
  slide.addText("\u4ea4\uff1a\u53ef\u9a8c\u6536\u6210\u679c\u76f8\u5173\u95ee\u9898", { x: leftX, y: colY, w: colW, h: 0.5, fontSize: 13, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });

  var leftItems = [
    { q: "\u4ea4\u4ec0\u4e48", a: "\u660e\u786e\u53ef\u9a8c\u6536\u6210\u679c\u6e05\u5355\uff0c\u786e\u4fdd\u4ea4\u4ed8\u7269\u7b26\u5408\u5408\u540c\u7ea6\u5b9a\u548c\u5ba2\u6237\u671f\u5f85" },
    { q: "\u6267\u884c\u4ec0\u4e48\u6807\u51c6", a: "\u9075\u5faa\u884c\u4e1a\u6807\u51c6\u3001\u4f01\u4e1a\u89c4\u8303\u548c\u5408\u540c\u7ea6\u5b9a\uff0c\u786e\u4fdd\u4ea4\u4ed8\u8d28\u91cf\u53ef\u91cf\u5316\u3001\u53ef\u9a8c\u8bc1" },
    { q: "\u627f\u8bfa\u7684\u670d\u52a1\u8c01\u6765\u63d0\u4f9b", a: "\u660e\u786e\u670d\u52a1\u63d0\u4f9b\u65b9\u548cSLA\u6807\u51c6\uff0c\u81ea\u6709\u80fd\u529b\u4e0e\u5916\u90e8\u8d44\u6e90\u5404\u53f8\u5176\u804c" }
  ];
  for (var i = 0; i < leftItems.length; i++) {
    var iy = colY + 0.6 + i * 0.68;
    slide.addText("Q " + (i + 1) + "\uff1a" + leftItems[i].q, { x: leftX + 0.15, y: iy, w: colW - 0.3, h: 0.28, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle" });
    slide.addText(leftItems[i].a, { x: leftX + 0.15, y: iy + 0.28, w: colW - 0.3, h: 0.38, fontSize: 8.5, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", wrap: true, lineSpacingMultiple: 1.2 });
  }

  // 右栏"付"
  var rightX = 0.5 + colW + 0.3;
  slide.addShape(pres.shapes.RECTANGLE, { x: rightX, y: colY, w: colW, h: colH, fill: { color: C.white }, line: { color: C.brandBlue, width: 1.5 } });
  slide.addShape(pres.shapes.RECTANGLE, { x: rightX, y: colY, w: colW, h: 0.5, fill: { color: C.brandBlue } });
  slide.addText("\u4ed8\uff1a\u4ea4\u4ed8\u7ef4\u62a4\u76f8\u5173\u95ee\u9898", { x: rightX, y: colY, w: colW, h: 0.5, fontSize: 13, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });

  var rightItems = [
    { q: "\u4ef7\u683c\u6210\u672c\u6388\u6743", a: "\u660e\u786e\u4ea4\u4ed8\u6210\u672c\u548c\u5b9a\u4ef7\u6388\u6743\uff0c\u786e\u4fdd\u4ea4\u4ed8\u5728\u9884\u7b97\u8303\u56f4\u5185" },
    { q: "\u5408\u89c4\u5ba1\u6279", a: "\u4ea4\u4ed8\u65b9\u6848\u7ecf\u6cd5\u52a1\u3001\u8d22\u52a1\u3001\u5b89\u5168\u7b49\u804c\u80fd\u5ba1\u6279\uff0c\u786e\u4fdd\u5408\u89c4\u6027" },
    { q: "\u7ef4\u62a4\u5355\u4f4d\u4e0e\u9a8c\u6536\u6807\u51c6", a: "\u660e\u786e\u540e\u671f\u7ef4\u62a4\u8d23\u4efb\u4e3b\u4f53\u53ca\u9a8c\u6536\u6807\u51c6\uff0c\u786e\u4fdd\u8fd0\u7ef4\u4ea4\u63a5\u987a\u5229" },
    { q: "\u5408\u540c\u8d26\u671f", a: "\u6309\u5408\u540c\u7ea6\u5b9a\u8d26\u671f\u7ba1\u7406\uff0c\u786e\u4fdd\u56de\u6b3e\u53ca\u65f6\u3001\u8d26\u671f\u5408\u89c4" }
  ];
  for (var j = 0; j < rightItems.length; j++) {
    var jy = colY + 0.6 + j * 0.52;
    slide.addText("Q " + (j + 1) + "\uff1a" + rightItems[j].q, { x: rightX + 0.15, y: jy, w: colW - 0.3, h: 0.22, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.brandBlue, align: "left", valign: "middle" });
    slide.addText(rightItems[j].a, { x: rightX + 0.15, y: jy + 0.22, w: colW - 0.3, h: 0.28, fontSize: 8.5, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", wrap: true, lineSpacingMultiple: 1.15 });
  }

  // 底部总结条
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 4.5, w: 9.0, h: 0.55, fill: { color: C.accentLight }, line: { color: C.primary, width: 1 } });
  slide.addText("\u6293\u4f4f\u4ea4\u4ed8\u5173\u952e\u70b9\uff1a\u4ece\u201c\u4ea4\u201d\u7684\u6210\u679c\u660e\u786e\u5230\u201c\u4ed8\u201d\u7684\u7ef4\u62a4\u5230\u4f4d\uff0c\u5f62\u6210\u95ed\u73af\u7ba1\u63a7\uff0c\u786e\u4fdd\u9879\u76ee\u81ea\u4e3b\u53ef\u63a7\u3001\u4ea4\u4ed8\u4e3b\u5bfc", {
    x: 0.6, y: 4.5, w: 8.8, h: 0.55, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle"
  });

  addBottomLine(slide, 35);
}

// ============================================================
// PAGE 36: 过程管控（环形流程）
// ============================================================
function page36() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.3 \u8fc7\u7a0b\u7ba1\u63a7", "\u5341\u5927\u7ba1\u63a7\u9886\u57df\u73af\u5f62\u95ed\u73af\uff1a\u8303\u56f4 \u2192 \u8fdb\u5ea6 \u2192 \u8d28\u91cf \u2192 \u6548\u76ca \u2192 \u6c9f\u901a \u2192 \u53d8\u66f4 \u2192 \u611f\u77e5 \u2192 \u98ce\u9669 \u2192 \u95ee\u9898 \u2192 \u6587\u6863");

  var nodes = [
    { name: "\u8303\u56f4\u7ba1\u7406", desc: "\u660e\u786e\u9879\u76ee\u8fb9\u754c\u4e0e\u4ea4\u4ed8\u7269", color: C.primary },
    { name: "\u8fdb\u5ea6\u7ba1\u7406", desc: "\u76d1\u63a7\u65f6\u95f4\u8282\u70b9\u4e0e\u91cc\u7a0b\u7891", color: C.brandBlue },
    { name: "\u8d28\u91cf\u7ba1\u7406", desc: "\u5236\u5b9a\u6807\u51c6\u3001\u68c0\u9a8c\u9a8c\u6536", color: C.orange },
    { name: "\u6548\u76ca\u7ba1\u7406", desc: "\u6210\u672c\u63a7\u5236\u4e0e\u4ef7\u503c\u8bc4\u4f30", color: C.green },
    { name: "\u6c9f\u901a\u7ba1\u7406", desc: "\u5efa\u7acb\u6c9f\u901a\u673a\u5236\u4e0e\u62a5\u544a\u4f53\u7cfb", color: C.teal },
    { name: "\u53d8\u66f4\u7ba1\u7406", desc: "\u53d8\u66f4\u8bc6\u522b\u3001\u8bc4\u4f30\u4e0e\u6267\u884c", color: C.accentDark },
    { name: "\u670d\u52a1\u611f\u77e5\u7ba1\u7406", desc: "\u5ba2\u6237\u4f53\u9a8c\u4e0e\u6ee1\u610f\u5ea6", color: C.purpleLight === "F3E8FF" ? "8E24AA" : C.primary },
    { name: "\u98ce\u9669\u7ba1\u7406", desc: "\u98ce\u9669\u8bc6\u522b\u3001\u8bc4\u4f30\u4e0e\u5e94\u5bf9", color: "D32F2F" },
    { name: "\u95ee\u9898\u7ba1\u7406", desc: "\u95ee\u9898\u8bb0\u5f55\u3001\u8ffd\u8e2a\u4e0e\u89e3\u51b3", color: "F57C00" },
    { name: "\u6587\u6863\u7ba1\u7406", desc: "\u4ea4\u4ed8\u6587\u6863\u7f16\u5236\u4e0e\u5f52\u6863", color: "1565C0" }
  ];

  // 中心圆
  var centerX = 5.0;
  var centerY = 3.1;
  slide.addShape(pres.shapes.OVAL, { x: centerX - 0.65, y: centerY - 0.65, w: 1.3, h: 1.3, fill: { color: C.primary } });
  slide.addText("\u8fc7\u7a0b\u7ba1\u63a7\n\u5341\u5927\u9886\u57df", { x: centerX - 0.65, y: centerY - 0.65, w: 1.3, h: 1.3, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", lineSpacingMultiple: 1.2 });

  // 环形节点
  var radiusX = 2.3;
  var radiusY = 1.85;
  var ovalW = 1.15;
  var ovalH = 0.5;

  for (var i = 0; i < nodes.length; i++) {
    var angle = -90 + i * 36;
    var rad = angle * Math.PI / 180;
    var px = centerX + radiusX * Math.cos(rad) - ovalW / 2;
    var py = centerY + radiusY * Math.sin(rad) - ovalH / 2;

    // 连接线
    slide.addShape(pres.shapes.LINE, {
      x: centerX, y: centerY, w: radiusX * Math.cos(rad), h: radiusY * Math.sin(rad),
      line: { color: C.borderLight, width: 1, dashType: "dash" }
    });

    // 节点椭圆
    slide.addShape(pres.shapes.OVAL, { x: px, y: py, w: ovalW, h: ovalH, fill: { color: nodes[i].color }, line: { color: C.white, width: 2 } });
    slide.addText(nodes[i].name, { x: px, y: py, w: ovalW, h: ovalH, fontSize: 8, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });

    // 外围说明文字
    var descX = centerX + (radiusX + 0.65) * Math.cos(rad) - 0.6;
    var descY = centerY + (radiusY + 0.5) * Math.sin(rad) - 0.12;
    // 根据角度调整文字对齐
    var align = "center";
    if (Math.cos(rad) > 0.3) align = "left";
    else if (Math.cos(rad) < -0.3) align = "right";
    if (Math.abs(Math.cos(rad)) > 0.3) {
      descX = descX + (align === "left" ? 0.1 : -0.1);
    }
    slide.addText(nodes[i].desc, { x: descX, y: descY, w: 1.3, h: 0.24, fontSize: 7, fontFace: "Microsoft YaHei", color: C.textSec, align: align, valign: "middle" });
  }

  addBottomLine(slide, 36);
}

// ============================================================
// PAGE 37: 过程管控——重点关注
// ============================================================
function page37() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.3 \u8fc7\u7a0b\u7ba1\u63a7\u2014\u2014\u91cd\u70b9\u5173\u6ce8", "\u8303\u56f4\u7ba1\u7406 \u00b7 \u8fdb\u5ea6\u7ba1\u7406 \u00b7 \u8d28\u91cf\u7ba1\u7406 \u4e09\u5927\u91cd\u70b9\u9886\u57df");

  var cols = [
    {
      title: "\u8303\u56f4\u7ba1\u7406", color: C.primary, icon: "\u25cf",
      points: [
        { head: "\u8303\u56f4\u5b9a\u4e49", body: "\u660e\u786e\u9879\u76ee\u8fb9\u754c\u3001\u4ea4\u4ed8\u7269\u548c\u9a8c\u6536\u6807\u51c6\uff0c\u7981\u6b62\u8303\u56f4\u8410\u5ef6" },
        { head: "\u53d8\u66f4\u63a7\u5236", body: "\u5efa\u7acb\u53d8\u66f4\u63a7\u5236\u673a\u5236\uff0c\u53d8\u66f4\u7ecf\u8bc4\u4f30\u540e\u6267\u884c\uff0c\u907f\u514d\u8303\u56f4\u6f2b\u5ef6" },
        { head: "\u9884\u8b66\u5347\u7ea7", body: "\u8303\u56f4\u504f\u79bb\u8d85\u8fc7\u9608\u503c\u65f6\u89e6\u53d1\u9884\u8b66\uff0c\u53ca\u65f6\u5347\u7ea7\u7ba1\u7406\u5c42\u5904\u7406" }
      ]
    },
    {
      title: "\u8fdb\u5ea6\u7ba1\u7406", color: C.brandBlue, icon: "\u25cf",
      points: [
        { head: "\u8ba1\u5212\u76d1\u63a7", body: "\u5236\u5b9a\u8be6\u7ec6\u91cc\u7a0b\u7891\u8ba1\u5212\uff0c\u5b9e\u65f6\u8ddf\u8e2a\u5b9e\u9645\u8fdb\u5ea6\uff0c\u53d1\u73b0\u504f\u5dee\u53ca\u65f6\u7ea0\u504f" },
        { head: "\u98ce\u9669\u7ba1\u7406", body: "\u5efa\u7acb\u98ce\u9669\u767b\u8bb0\u518c\uff0c\u5b9a\u671f\u8bc4\u4f30\u9879\u76ee\u98ce\u9669\uff0c\u5236\u5b9a\u5e94\u5bf9\u63aa\u65bd\u548c\u5907\u9009\u65b9\u6848" },
        { head: "\u8d44\u6e90\u4fdd\u969c", body: "\u786e\u4fdd\u4eba\u529b\u3001\u7269\u529b\u8d44\u6e90\u53ca\u65f6\u5c31\u4f4d\uff0c\u907f\u514d\u8d44\u6e90\u74f6\u9888\u5bfc\u81f4\u8fdb\u5ea6\u5ef6\u8bef" }
      ]
    },
    {
      title: "\u8d28\u91cf\u7ba1\u7406", color: C.orange, icon: "\u25cf",
      points: [
        { head: "\u8d28\u91cf\u6807\u51c6", body: "\u5236\u5b9a\u660e\u786e\u7684\u8d28\u91cf\u6807\u51c6\u548c\u9a8c\u6536\u6761\u4ef6\uff0c\u786e\u4fdd\u4ea4\u4ed8\u8d28\u91df\u53ef\u91cf\u5316" },
        { head: "\u98ce\u9669\u9632\u8303\u5e94\u5bf9", body: "\u5efa\u7acb\u8d28\u91cf\u98ce\u9669\u6e05\u5355\uff0c\u5236\u5b9a\u9884\u9632\u63aa\u65bd\uff0c\u51fa\u73b0\u8d28\u91cf\u95ee\u9898\u65f6\u5feb\u901f\u54cd\u5e94" },
        { head: "\u6301\u7eed\u6539\u8fdb", body: "\u5b9a\u671f\u7ec4\u7ec7\u8d28\u91cf\u8bc4\u5ba1\uff0c\u6301\u7eed\u4f18\u5316\u4ea4\u4ed8\u6d41\u7a0b\uff0c\u63d0\u5347\u4ea4\u4ed8\u8d28\u91cf" }
      ]
    }
  ];

  var colW = 2.8;
  var colGap = 0.25;
  var colX = 0.5;
  var colY = 1.6;
  var colH = 3.5;

  for (var i = 0; i < cols.length; i++) {
    var cx = colX + i * (colW + colGap);
    var c = cols[i];
    // 卡片
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: colY, w: colW, h: colH, fill: { color: C.white }, line: { color: c.color, width: 1.5 } });
    // 顶部
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: colY, w: colW, h: 0.5, fill: { color: c.color } });
    slide.addText(c.icon + "  " + c.title, { x: cx, y: colY, w: colW, h: 0.5, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });
    // 要点
    for (var j = 0; j < c.points.length; j++) {
      var py = colY + 0.6 + j * 0.95;
      // 分隔线
      if (j > 0) {
        slide.addShape(pres.shapes.RECTANGLE, { x: cx + 0.1, y: py - 0.05, w: colW - 0.2, h: 0.01, fill: { color: C.borderLight } });
      }
      slide.addShape(pres.shapes.RECTANGLE, { x: cx + 0.1, y: py, w: colW - 0.2, h: 0.25, fill: { color: i === 0 ? C.accentLight : i === 1 ? C.blueLight : C.yellow } });
      slide.addText(c.points[j].head, { x: cx + 0.15, y: py, w: colW - 0.3, h: 0.25, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: c.color, align: "left", valign: "middle" });
      slide.addText(c.points[j].body, { x: cx + 0.15, y: py + 0.28, w: colW - 0.3, h: 0.6, fontSize: 8.5, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", wrap: true, lineSpacingMultiple: 1.25 });
    }
  }

  addBottomLine(slide, 37);
}

// ============================================================
// PAGE 38: 验收交付
// ============================================================
function page38() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.4 \u9a8c\u6536\u4ea4\u4ed8", "\u9884\u9a8c\u6536 \u2192 \u6b63\u5f0f\u9a8c\u6536 \u2192 \u56de\u6b3e\uff0c\u540e\u5411\u5b9e\u65bd\u4ea4\u4ed8\u8bc4\u4ef7\u4e94\u7ef4\u5ea6");

  // 3阶段流程
  var stages = [
    {
      name: "\u9884\u9a8c\u6536", color: C.primary,
      input: ["\u5b9e\u65bd\u5b8c\u6210\u62a5\u544a", "\u81ea\u6d4b\u7ed3\u679c", "\u4ea4\u4ed8\u6e05\u5355"],
      actions: ["\u7ec4\u7ec7\u9884\u9a8c\u6536\u8bc4\u5ba1", "\u68c0\u67e5\u4ea4\u4ed8\u7269\u5b8c\u6574\u6027", "\u8bc6\u522b\u5f85\u6574\u6539\u9879\u76ee"],
      output: ["\u9884\u9a8c\u6536\u62a5\u544a", "\u7f3a\u9677\u5217\u8868", "\u6574\u6539\u8ba1\u5212"]
    },
    {
      name: "\u6b63\u5f0f\u9a8c\u6536", color: C.brandBlue,
      input: ["\u7f3a\u9677\u6574\u6539\u62a5\u544a", "\u9884\u9a8c\u6536\u901a\u8fc7\u8bb0\u5f55", "\u9a8c\u6536\u6587\u6863"],
      actions: ["\u5ba2\u6237\u53c2\u4e0e\u6b63\u5f0f\u9a8c\u6536", "\u6839\u636e\u5408\u540c\u6807\u51c6\u68c0\u9a8c", "\u7b7e\u7f72\u9a8c\u6536\u62a5\u544a"],
      output: ["\u6b63\u5f0f\u9a8c\u6536\u62a5\u544a", "\u9a8c\u6536\u8bc1\u4e66", "\u4ea4\u8d44\u4ea4\u7ef4\u5355"]
    },
    {
      name: "\u56de\u6b3e", color: C.green,
      input: ["\u9a8c\u6536\u8bc1\u4e66", "\u5f00\u7968\u7533\u8bf7", "\u5408\u540c\u4ed8\u6b3e\u6761\u6b3e"],
      actions: ["\u63d0\u4ea4\u5f00\u7968\u8d44\u6599", "\u8ddf\u8e2a\u5ba2\u6237\u5ba1\u6279", "\u786e\u8ba4\u56de\u6b3e\u91d1\u989d"],
      output: ["\u5f00\u7968\u5b8c\u6210", "\u56de\u6b3e\u5230\u8d26", "\u9879\u76ee\u7ed3\u9879\u62a5\u544a"]
    }
  ];

  var sx = 0.5;
  var sy = 1.55;
  var sw = 2.85;
  var sh = 2.75;
  var sGap = 0.25;

  for (var i = 0; i < stages.length; i++) {
    var cx = sx + i * (sw + sGap);
    var s = stages[i];
    // 卡片
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: sy, w: sw, h: sh, fill: { color: C.white }, line: { color: s.color, width: 1.5 } });
    // 顶部
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: sy, w: sw, h: 0.45, fill: { color: s.color } });
    slide.addText(s.name, { x: cx, y: sy, w: sw, h: 0.45, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });

    var rows = [
      { label: "\u8f93\u5165", items: s.input, bg: C.cardBg },
      { label: "\u6807\u51c6\u52a8\u4f5c", items: s.actions, bg: C.accentLight },
      { label: "\u8f93\u51fa", items: s.output, bg: C.greenLight }
    ];
    var rowY = sy + 0.55;
    var rowH = 0.7;
    for (var r = 0; r < rows.length; r++) {
      var ry = rowY + r * (rowH + 0.05);
      // 标签
      slide.addShape(pres.shapes.RECTANGLE, { x: cx + 0.08, y: ry, w: 0.7, h: rowH, fill: { color: s.color } });
      slide.addText(rows[r].label, { x: cx + 0.08, y: ry, w: 0.7, h: rowH, fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", wrap: true });
      // 内容
      slide.addShape(pres.shapes.RECTANGLE, { x: cx + 0.8, y: ry, w: sw - 0.9, h: rowH, fill: { color: rows[r].bg }, line: { color: C.borderLight, width: 0.5 } });
      for (var k = 0; k < rows[r].items.length; k++) {
        slide.addShape(pres.shapes.OVAL, { x: cx + 0.88, y: ry + 0.1 + k * 0.2, w: 0.06, h: 0.06, fill: { color: s.color } });
        slide.addText(rows[r].items[k], { x: cx + 0.98, y: ry + 0.05 + k * 0.2, w: sw - 1.08, h: 0.2, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "middle" });
      }
    }
    // 箭头
    if (i < stages.length - 1) {
      addArrowRight(slide, cx + sw + 0.02, sy + sh / 2 - 0.15, sGap - 0.04, 0.3, C.textLight);
    }
  }

  // 底部5维度评价
  var dimY = 4.55;
  slide.addText("\u540e\u5411\u5b9e\u65bd\u4ea4\u4ed8\u8bc4\u4ef7\u4e94\u7ef4\u5ea6\uff1a", { x: 0.5, y: dimY, w: 2.5, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle" });
  var dims = [
    { name: "\u5408\u89c4\u53ca\u65f6", color: C.primary },
    { name: "\u6210\u679c\u8d28\u91cf", color: C.brandBlue },
    { name: "\u9690\u60a3\u98ce\u9669", color: C.orange },
    { name: "\u7528\u6237\u6ee1\u610f", color: C.green },
    { name: "\u6301\u7eed\u53d1\u5c55", color: C.teal }
  ];
  var dW = 1.25;
  var dGap = 0.08;
  var dStartX = 3.0;
  for (var d = 0; d < dims.length; d++) {
    var dx = dStartX + d * (dW + dGap);
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: dx, y: dimY, w: dW, h: 0.35, fill: { color: dims[d].color }, rectRadius: 0.03 });
    slide.addText(dims[d].name, { x: dx, y: dimY, w: dW, h: 0.35, fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });
  }

  addBottomLine(slide, 38);
}

// ============================================================
// PAGE 39: 强化"交付即运营"能力
// ============================================================
function page39() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "2.4 \u5f3a\u5316\u201c\u4ea4\u4ed8\u5373\u8fd0\u8425\u201d\u80fd\u529b", "\u4ece\u552e\u4e2d\u5230\u552e\u540e\uff0c\u4ece\u201c\u7528\u8d77\u6765\u201d\u5230\u201c\u7528\u5f97\u597d\u201d\u5230\u201c\u6301\u7eed\u63d0\u5347\u201d");

  // 左栏：售中阶段
  var leftX = 0.5;
  var colW = 4.2;
  var colY = 1.6;
  var colH = 3.0;

  slide.addShape(pres.shapes.RECTANGLE, { x: leftX, y: colY, w: colW, h: colH, fill: { color: C.white }, line: { color: C.primary, width: 1.5 } });
  slide.addShape(pres.shapes.RECTANGLE, { x: leftX, y: colY, w: colW, h: 0.5, fill: { color: C.primary } });
  slide.addText("\u552e\u4e2d\u9636\u6bb5", { x: leftX, y: colY, w: colW, h: 0.5, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });

  // 实施行
  var impY = colY + 0.6;
  slide.addShape(pres.shapes.RECTANGLE, { x: leftX + 0.1, y: impY, w: colW - 0.2, h: 0.3, fill: { color: C.accentLight } });
  slide.addText("\u5b9e\u65bd", { x: leftX + 0.15, y: impY, w: 0.8, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle" });
  var implPoints = ["\u4ea4\u4ed8\u65f6\u5c31\u5eFA\u7ACB\u8FD0\u8425\u4F53\u7CFB", "\u5B9E\u65BD\u8FC7\u7A0B\u4E2D\u6CE8\u5165\u8FD0\u8425\u9700\u6C42", "\u4EA4\u4ED8\u6210\u679C\u53EF\u8FD0\u8425\u5316\u8BBE\u8BA1"];
  for (var a = 0; a < implPoints.length; a++) {
    var ay = impY + 0.35 + a * 0.28;
    slide.addShape(pres.shapes.OVAL, { x: leftX + 0.2, y: ay + 0.05, w: 0.08, h: 0.08, fill: { color: C.primary } });
    slide.addText(implPoints[a], { x: leftX + 0.35, y: ay, w: colW - 0.55, h: 0.25, fontSize: 9, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "middle" });
  }

  // 运营行
  var optY = impY + 1.25;
  slide.addShape(pres.shapes.RECTANGLE, { x: leftX + 0.1, y: optY, w: colW - 0.2, h: 0.3, fill: { color: C.pinkLight } });
  slide.addText("\u8fd0\u8425", { x: leftX + 0.15, y: optY, w: 0.8, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.accentDark, align: "left", valign: "middle" });
  var optPoints = ["\u4EA4\u4ED8\u5373\u5F00\u59CB\u8FD0\u8425\u9A8C\u8BC1", "\u5FEB\u901F\u54CD\u5E94\u5BA2\u6237\u53CD\u9988", "\u6301\u7EED\u4F18\u5316\u8FD0\u8425\u65B9\u6848"];
  for (var b = 0; b < optPoints.length; b++) {
    var by = optY + 0.35 + b * 0.28;
    slide.addShape(pres.shapes.OVAL, { x: leftX + 0.2, y: by + 0.05, w: 0.08, h: 0.08, fill: { color: C.accentDark } });
    slide.addText(optPoints[b], { x: leftX + 0.35, y: by, w: colW - 0.55, h: 0.25, fontSize: 9, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "middle" });
  }

  // 右栏：售后阶段
  var rightX = 0.5 + colW + 0.3;
  slide.addShape(pres.shapes.RECTANGLE, { x: rightX, y: colY, w: colW, h: colH, fill: { color: C.white }, line: { color: C.brandBlue, width: 1.5 } });
  slide.addShape(pres.shapes.RECTANGLE, { x: rightX, y: colY, w: colW, h: 0.5, fill: { color: C.brandBlue } });
  slide.addText("\u552e\u540e\u9636\u6bb5", { x: rightX, y: colY, w: colW, h: 0.5, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });

  // 实施行
  slide.addShape(pres.shapes.RECTANGLE, { x: rightX + 0.1, y: impY, w: colW - 0.2, h: 0.3, fill: { color: C.blueLight } });
  slide.addText("\u5b9e\u65bd", { x: rightX + 0.15, y: impY, w: 0.8, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.brandBlue, align: "left", valign: "middle" });
  var implPoints2 = ["\u8FD0\u7EF4\u4F53\u7CFB\u5EFA\u7ACB\u4E0E\u4EA4\u63A5", "\u670D\u52A1\u7B49\u7EA7\u534F\u8BAE\u843D\u5730", "\u6545\u969C\u54CD\u5E94\u673A\u5236\u5EFA\u7ACB"];
  for (var c = 0; c < implPoints2.length; c++) {
    var cy = impY + 0.35 + c * 0.28;
    slide.addShape(pres.shapes.OVAL, { x: rightX + 0.2, y: cy + 0.05, w: 0.08, h: 0.08, fill: { color: C.brandBlue } });
    slide.addText(implPoints2[c], { x: rightX + 0.35, y: cy, w: colW - 0.55, h: 0.25, fontSize: 9, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "middle" });
  }

  // 运营行
  slide.addShape(pres.shapes.RECTANGLE, { x: rightX + 0.1, y: optY, w: colW - 0.2, h: 0.3, fill: { color: C.greenLight } });
  slide.addText("\u8fd0\u8425", { x: rightX + 0.15, y: optY, w: 0.8, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.green, align: "left", valign: "middle" });
  var optPoints2 = ["\u7528\u5F97\u597D\uff1a\u6301\u7EED\u63D0\u5347\u4F7F\u7528\u4F53\u9A8C", "\u6301\u7EED\u63D0\u5347\uff1a\u6570\u636E\u9A71\u52A8\u8FD0\u8425\u4F18\u5316", "\u4EA7\u751F\u4E8C\u6B21\u5546\u673A\u4E0E\u589E\u503C\u670D\u52A1"];
  for (var d = 0; d < optPoints2.length; d++) {
    var dy = optY + 0.35 + d * 0.28;
    slide.addShape(pres.shapes.OVAL, { x: rightX + 0.2, y: dy + 0.05, w: 0.08, h: 0.08, fill: { color: C.green } });
    slide.addText(optPoints2[d], { x: rightX + 0.35, y: dy, w: colW - 0.55, h: 0.25, fontSize: 9, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "middle" });
  }

  // 中间箭头
  addArrowRight(slide, 0.5 + colW + 0.05, colY + colH / 2 - 0.15, 0.2, 0.3, C.orange);

  // 底部关键词
  var kwY = 4.75;
  var keywords = [
    { text: "\u7528\u8d77\u6765", color: C.primary },
    { text: "\u7528\u5f97\u597d", color: C.brandBlue },
    { text: "\u6301\u7eed\u63d0\u5347", color: C.green }
  ];
  var kwStartX = 1.5;
  var kwW = 2.0;
  var kwGap = 0.5;
  for (var k = 0; k < keywords.length; k++) {
    var kx = kwStartX + k * (kwW + kwGap);
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: kx, y: kwY, w: kwW, h: 0.4, fill: { color: keywords[k].color }, rectRadius: 0.05 });
    slide.addText(keywords[k].text, { x: kx, y: kwY, w: kwW, h: 0.4, fontSize: 13, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle" });
    if (k < keywords.length - 1) {
      slide.addText("\u2192", { x: kx + kwW, y: kwY, w: kwGap, h: 0.4, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.textLight, align: "center", valign: "middle" });
    }
  }

  addBottomLine(slide, 39);
}

// ============================================================
// PAGE 40: 售中篇要点回顾
// ============================================================
function page40() {
  var slide = pres.addSlide();
  addBrand(slide);
  addTitleBar(slide, "\u552e\u4e2d\u7bc7\u2014\u2014\u8981\u70b9\u56de\u987e", "\u4ece\u843d\u5355\u5230\u843d\u6536\uff0c\u5168\u6d41\u7a0b\u7ba1\u63a7\u8981\u70b9\u6c47\u603b");

  // 关键词云区域
  var cloudY = 1.6;
  var cloudH = 2.5;

  // 背景框
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: cloudY, w: 9.0, h: cloudH, fill: { color: C.accentLight }, line: { color: C.primary, width: 1, dashType: "dash" } });

  var keywords = [
    { text: "\u4e1a\u52a1\u89e3\u6784", size: 16, color: C.primary, x: 1.2, y: 1.85, w: 1.8, h: 0.5 },
    { text: "\u56e2\u961f\u7ec4\u5efa", size: 14, color: C.brandBlue, x: 3.3, y: 1.75, w: 1.6, h: 0.45 },
    { text: "\u91c7\u8d2d\u6d41\u7a0b\u4f18\u5316", size: 15, color: C.orange, x: 5.2, y: 1.9, w: 2.0, h: 0.5 },
    { text: "\u91c7\u8d2d\u65b9\u5f0f\u5dee\u5f02", size: 13, color: C.green, x: 7.5, y: 1.8, w: 1.8, h: 0.45 },
    { text: "\u91c7\u8d2d\u65b9\u5f0f\u9009\u62e9", size: 12, color: C.teal, x: 1.0, y: 2.55, w: 1.8, h: 0.4 },
    { text: "\u8fc7\u7a0b\u7ba1\u63a7", size: 16, color: C.primary, x: 3.2, y: 2.5, w: 1.5, h: 0.5 },
    { text: "\u98ce\u9669\u7ba1\u7406", size: 14, color: "D32F2F", x: 5.0, y: 2.6, w: 1.5, h: 0.45 },
    { text: "\u53d8\u66f4\u7ba1\u7406", size: 13, color: C.accentDark, x: 6.8, y: 2.5, w: 1.5, h: 0.45 },
    { text: "\u552e\u540e\u95ee\u9898\u7ba1\u7406", size: 12, color: C.brandBlue, x: 1.2, y: 3.15, w: 2.0, h: 0.4 },
    { text: "\u5ba2\u6237\u4ea4\u4ed8", size: 15, color: C.primary, x: 3.5, y: 3.1, w: 1.5, h: 0.45 },
    { text: "\u4ea4\u4ed8\u5373\u8fd0\u8425", size: 14, color: C.green, x: 5.3, y: 3.15, w: 2.0, h: 0.45 },
    { text: "\u9879\u76ee\u7ba1\u7406\u7cfb\u7edfPMS", size: 12, color: C.brandBlue, x: 7.2, y: 3.1, w: 2.2, h: 0.4 }
  ];

  for (var i = 0; i < keywords.length; i++) {
    var kw = keywords[i];
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: kw.x, y: kw.y, w: kw.w, h: kw.h, fill: { color: C.white }, line: { color: kw.color, width: 1 }, rectRadius: 0.05 });
    slide.addText(kw.text, { x: kw.x, y: kw.y, w: kw.w, h: kw.h, fontSize: kw.size, fontFace: "Microsoft YaHei", bold: true, color: kw.color, align: "center", valign: "middle" });
  }

  // 底部总结
  var sumY = 4.3;
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: sumY, w: 9.0, h: 0.85, fill: { color: C.primary } });
  slide.addText("\u552e\u4e2d\u9636\u6bb5\u6838\u5fc3\u601d\u8def", { x: 0.7, y: sumY + 0.05, w: 8.6, h: 0.25, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.yellow, align: "left", valign: "middle" });
  slide.addText("\u4ee5\u4e1a\u52a1\u89e3\u6784\u4e3a\u8d77\u70b9\uff0c\u7ec4\u5efa\u4e13\u4e1a\u56e2\u961f\uff0c\u4f18\u5316\u540e\u5411\u91c7\u8d2d\u6d41\u7a0b\uff0c\u5b9e\u65bd\u5168\u8fc7\u7a0b\u7ba1\u63a7\uff08\u8303\u56f4/\u8fdb\u5ea6/\u8d28\u91cf/\u98ce\u9669/\u53d8\u66f4\uff09\uff0c\u786e\u4fdd\u9a8c\u6536\u4ea4\u4ed8\u8d28\u91cf\uff0c\u5f3a\u5316\u201c\u4ea4\u4ed8\u5373\u8fd0\u8425\u201d\u80fd\u529b\uff0c\u5b9e\u73b0\u4ece\u843d\u5355\u5230\u843d\u6536\u7684\u5168\u6d41\u7a0b\u95ed\u73af\u7ba1\u7406\u3002", {
    x: 0.7, y: sumY + 0.3, w: 8.6, h: 0.5, fontSize: 9, fontFace: "Microsoft YaHei", color: C.white, align: "left", valign: "top", wrap: true, lineSpacingMultiple: 1.3
  });

  addBottomLine(slide, 40);
}

// ============================================================
// 执行所有页面生成

// ================================================================
// 第41-61页函数（从Part3合并）
// ================================================================
// ============================================================
// PAGE 41: 目录页（售后篇）
// ============================================================
function page41() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  s.addText("\u76ee\u5f55", { x: 0.7, y: 1.0, w: 3.5, h: 1.0, fontSize: 48, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "bottom", margin: 0 });
  s.addText("CONTENTS", { x: 0.7, y: 2.1, w: 3.5, h: 0.45, fontSize: 14, fontFace: "Microsoft YaHei", color: C.textSec, align: "left", charSpacing: 4, margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 2.75, w: 0.08, h: 1.8, fill: { color: C.primary } });
  var toc = [
    { num: "1", label: "\u552e\u524d\u7bc7\u2014\u2014\u4ece\u83b7\u53d6\u5230\u8f6c\u5316", color: C.textLight },
    { num: "2", label: "\u552e\u4e2d\u7bc7\u2014\u2014\u4ece\u843d\u5355\u5230\u843d\u6536", color: C.textLight },
    { num: "3", label: "\u552e\u540e\u7bc7\u2014\u2014\u4ece\u8fd0\u7ef4\u5230\u8fd0\u8425", color: C.primary }
  ];
  toc.forEach(function(item, i) {
    var ty = 1.2 + i * 0.95;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.2, y: ty, w: 0.65, h: 0.65, fill: { color: item.color }, rectRadius: 0.05 });
    s.addText(item.num, { x: 5.2, y: ty, w: 0.65, h: 0.65, fontSize: 22, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
    s.addText(item.label, { x: 6.05, y: ty, w: 3.3, h: 0.65, fontSize: 15, fontFace: "Microsoft YaHei", bold: true, color: i === 2 ? C.text : C.textLight, align: "left", valign: "middle", margin: 0, wrap: true });
  });
  // 子项
  s.addText("\u8fd0\u8425\u5bf9\u63a5  \u00b7  \u8fd0\u8425\u5b9e\u65bd  \u00b7  \u4e8c\u6b21\u8425\u9500", { x: 6.05, y: 3.15, w: 3.3, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", color: C.textSec, align: "left", valign: "top", margin: 0 });
  addBottomLine(s, 41);
}

// ============================================================
// PAGE 42: 为什么要开展售后运营
// ============================================================
function page42() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "\u4e3a\u4ec0\u4e48\u8981\u5f00\u5c55\u552e\u540e\u8fd0\u8425");
  // 左栏：运维
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.4, y: 1.3, w: 4.4, h: 3.6, fill: { color: C.white }, line: { color: C.primary, width: 0.75 }, rectRadius: 0.05 });
  s.addText("\u8fd0\u7ef4", { x: 0.4, y: 1.3, w: 4.4, h: 0.4, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.white, fill: { color: C.primary }, align: "center", valign: "middle", margin: 0 });
  s.addText([{ text: "\u73b0\u72b6\uff1a", options: { bold: true, fontSize: 8, color: C.primary } }, { text: "\u9879\u76ee\u8fd0\u7ef4\u4e3b\u8981\u4f9d\u9760\u751f\u6001\u4e0e\u4e13\u4e1a\u516c\u53f8\uff0c\u81ea\u8eab\u9a7b\u573a\u8fd0\u7ef4\u5c11\uff0c\u5ba2\u6237\u611f\u77e5\u4e0d\u4e00\u81f4", options: { fontSize: 8, color: C.text } }], { x: 0.6, y: 1.85, w: 4.0, h: 0.8, fontFace: "Microsoft YaHei", valign: "top", margin: 0, wrap: true });
  s.addText([{ text: "\u4e3e\u63aa\uff1a", options: { bold: true, fontSize: 8, color: C.primary } }, { text: "\u5b9e\u65bd\u7edf\u4e00\u8fd0\u7ef4\uff0c\u4f18\u5316\u6a21\u5f0f\uff0c\u91cd\u8981\u5ba2\u6237\u91cd\u5927\u9879\u76ee\u9a7b\u573a\u8fd0\u7ef4\n\u00b7 \u8fd0\u7ef4\u7edf\u4e00\u7ba1\u7406\uff0c\u4f18\u5316\u8fd0\u7ef4\u6807\u51c6\n\u00b7 \u4f18\u5316\u8fd0\u7ef4\u6a21\u5f0f\uff0c\u6316\u6398\u8fd0\u7ef4\u4ef7\u503c\n\u00b7 \u6301\u7eed\u63d0\u5347\u91cd\u5927\u3001\u91cd\u70b9\u9879\u76ee\u8fd0\u7ef4\u7535\u4fe1\u81ea\u8eab\u53c2\u4e0e\u6bd4\u91cd", options: { fontSize: 8, color: C.text } }], { x: 0.6, y: 2.7, w: 4.0, h: 2.0, fontFace: "Microsoft YaHei", valign: "top", margin: 0, wrap: true });
  // 右栏：运营
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.1, y: 1.3, w: 4.4, h: 3.6, fill: { color: C.white }, line: { color: C.brandBlue, width: 0.75 }, rectRadius: 0.05 });
  s.addText("\u8fd0\u8425", { x: 5.1, y: 1.3, w: 4.4, h: 0.4, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.white, fill: { color: C.brandBlue }, align: "center", valign: "middle", margin: 0 });
  s.addText([{ text: "\u73b0\u72b6\uff1a", options: { bold: true, fontSize: 8, color: C.brandBlue } }, { text: "\u7f3a\u7edf\u4e00\u6570\u5b57\u8d44\u4ea7\u7ba1\u7406\u5e73\u53f0\uff0c\u65e0\u6cd5\u957f\u671f\u8fed\u4ee3\u8fd0\u8425\uff0c\u4e3b\u52a8\u6027\u8fd0\u8425\u670d\u52a1\u4e0d\u8db3\uff0c\u57fa\u4e8e\u8fd0\u8425\u7684\u65b0\u5546\u673a\u6316\u6398\u4e0d\u8db3", options: { fontSize: 8, color: C.text } }], { x: 5.3, y: 1.85, w: 4.0, h: 0.8, fontFace: "Microsoft YaHei", valign: "top", margin: 0, wrap: true });
  s.addText([{ text: "\u4e3e\u63aa\uff1a", options: { bold: true, fontSize: 8, color: C.brandBlue } }, { text: "\u5efa\u8bbe\u6570\u5b57\u8d44\u4ea7\u7ba1\u7406\u5e73\u53f0\uff0c\u5f00\u5c55\u6570\u636e\u5206\u6790\uff0c\u6316\u6398\u65b0\u9700\u6c42\n\u00b7 \u8d44\u4ea7\u8fd0\u8425(\u65b0\u5347\u7ea7)\n\u00b7 \u6570\u636e\u8fd0\u8425(\u65b0\u529f\u80fd)\n\u00b7 \u5ba2\u6237\u8fd0\u8425(\u65b0\u5546\u673a)", options: { fontSize: 8, color: C.text } }], { x: 5.3, y: 2.7, w: 4.0, h: 2.0, fontFace: "Microsoft YaHei", valign: "top", margin: 0, wrap: true });
  addBottomLine(s, 42);
}

// ============================================================
// PAGE 43: 交付即运营开始
// ============================================================
function page43() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "\u4ea4\u4ed8\u5373\u8fd0\u8425\u5f00\u59cb\uff0c\u8fd0\u8425\u662f\u6301\u7eed\u7684\u4ea4\u4ed8", "\u5b9e\u73b0\u8d44\u4ea7\u6570\u5b57\u5316\uff0c\u652f\u6491\u7cbe\u51c6\u8fd0\u7ef4\u3001\u7cbe\u7ec6\u8fd0\u8425\u6316\u6398\u7528\u6237\u9700\u6c42\uff0c\u5b9e\u73b0\u9879\u76ee\u8fed\u4ee3\u6216\u9879\u76ee\u590d\u5236");
  var steps = [
    { num: "1", title: "\u6c47\u805a\u5173\u952e\u4fe1\u606f", desc: "\u9879\u76ee\u4ea4\u4ed8\u5173\u952e\u4fe1\u606f+\u5ba2\u6237\u8fd0\u7ef4\u5173\u952e\u4fe1\u606f" },
    { num: "2", title: "\u9a7b\u573a\u4eba\u5458\u590d\u7528", desc: "\u660e\u786e\u7ed3\u7b97\u4e0e\u8003\u6838\u89c4\u5219\uff0c\u5f00\u5c55\u9a7b\u573a\u4eba\u5458\u590d\u7528\u673a\u5236\u8bd5\u70b9" },
    { num: "3", title: "\u5f00\u5c55\u7edf\u4e00\u76d1\u63a7", desc: "\u8054\u5408\u4e91\u516c\u53f8\u3001\u6570\u667a\u79d1\u6280\u3001\u5408\u4f5c\u4f19\u4f34\u7b49\u8bd5\u70b9\u7edf\u4e00\u7eb3\u7ba1" },
    { num: "4", title: "\u5e73\u53f0\u5347\u7ea7\u66ff\u4ee3", desc: "\u4e3b\u52a8\u63d0\u51fa\u5df2\u6709\u5e73\u53f0\u5347\u7ea7\u4e0e\u66ff\u4ee3\u65b9\u6848\uff0c\u5e76\u5411\u653f\u4f01\u4e0e\u96c6\u6210\u505a\u597d\u5546\u673a\u4e0e\u5b9e\u65bd\u7684\u6d3e\u5355" },
    { num: "5", title: "\u8bd5\u70b9\u6570\u636e\u8fd0\u8425", desc: "\u5229\u7528\u5927\u6570\u636e\u3001\u5b89\u5168\u3001\u884c\u4e1a\u65b0\u80fd\u529b\u7b49\u4e3b\u52a8\u8bd5\u70b9\u5e2e\u52a9\u5ba2\u6237\u5f00\u5c55\u6570\u636e\u8fd0\u8425\u4e0e\u6570\u5b57\u5316\u6cbb\u7406" }
  ];
  steps.forEach(function(step, i) {
    var sx = 0.3 + i * 1.9;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: sx, y: 1.5, w: 1.75, h: 3.3, fill: { color: C.white }, line: { color: C.primary, width: 0.75 }, rectRadius: 0.05 });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: sx + 0.45, y: 1.6, w: 0.85, h: 0.5, fill: { color: C.primary }, rectRadius: 0.05 });
    s.addText(step.num, { x: sx + 0.45, y: 1.6, w: 0.85, h: 0.5, fontSize: 20, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
    s.addText(step.title, { x: sx + 0.1, y: 2.2, w: 1.55, h: 0.5, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0, wrap: true });
    s.addText(step.desc, { x: sx + 0.1, y: 2.75, w: 1.55, h: 1.9, fontSize: 7, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: [4, 4, 4, 4], wrap: true });
  });
  addBottomLine(s, 43);
}

// ============================================================
// PAGE 44: 实现运维运营一体化
// ============================================================
function page44() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "\u5b9e\u73b0\u8fd0\u7ef4\u8fd0\u8425\u4e00\u4f53\u5316\uff0c\u63d0\u5347\u5ba2\u6237\u9700\u6c42\u4e8c\u6b21\u6316\u6398", "\u5b9e\u73b0\u4ea4\u4ed8\u8fd0\u8425\u4e00\u4f53\u5316\uff0c\u63d0\u5347\u5ba2\u6237\u8fd0\u8425\u4ef7\u503c\uff0c\u4ece\u201c\u4ea4\u4ed8\u5373\u4e86\u7ed3\u201d\u8f6c\u53d8\u4e3a\u4ee5\u53ef\u6301\u7eed\u8fd0\u8425\u4ea7\u751f\u957f\u6548\u6536\u76ca");
  // 3阶段流程
  var phases = [
    { title: "\u7ef4\u62a4\u4ea4\u63a5", items: "\u00b7 \u8fd0\u7ef4\u65b9\u6848\u7f16\u5236\n\u00b7 \u8fd0\u7ef4\u542f\u52a8\u4f1a\n\u00b7 \u5408\u4f5c\u4f19\u4f34\u80fd\u529b\u8bc4\u4f30" },
    { title: "\u9879\u76ee\u8fd0\u7ef4", items: "\u00b7 \u521d\u6b65\u5f00\u5c55\u8fc7\u6e21\u671f\u8fd0\u7ef4\n\u00b7 \u8fd0\u7ef4\u670d\u52a1\u65b9\u6848\u53d1\u5e03\n\u00b7 \u65e5\u5e38\u8fd0\u8425\u8fd0\u7ef4\u5de5\u4f5c" },
    { title: "\u9879\u76ee\u8fd0\u8425", items: "\u00b7 \u6570\u636e\u5206\u6790\n\u00b7 \u9700\u6c42\u6316\u6398\n\u00b7 \u5546\u673a\u7ebf\u7d22\u6d3e\u5355\n\u00b7 \u65b0\u5546\u673a" }
  ];
  phases.forEach(function(p, i) {
    var px = 0.5 + i * 3.1;
    addFlowNode(s, px, 1.5, 2.8, 0.5, p.title, { bg: i === 0 ? C.brandBlue : (i === 1 ? C.primary : C.orange) });
    s.addText(p.items, { x: px + 0.1, y: 2.1, w: 2.6, h: 1.5, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true, fill: { color: C.pinkLight }, border: { color: C.borderLight, pt: 0.5 } });
    if (i < 2) addArrowRight(s, px + 2.8, 1.6, 0.3, 0.25, C.primary);
  });
  // 关键节点
  s.addText("\u5173\u952e\u8282\u70b9", { x: 0.5, y: 3.8, w: 1.2, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });
  s.addText("1 \u8fd0\u7ef4\u65b9\u6848\u7f16\u5236/\u8fd0\u7ef4\u542f\u52a8\u4f1a   2 \u521d\u6b65\u5f00\u5c55\u8fc7\u6e21\u671f\u8fd0\u7ef4   3 \u8fd0\u7ef4\u670d\u52a1\u65b9\u6848\u53d1\u5e03   4 \u9700\u6c42\u6316\u6398/\u5546\u673a\u7ebf\u7d22", { x: 0.5, y: 4.1, w: 9.0, h: 0.4, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  addBottomLine(s, 44);
}

// ============================================================
// PAGE 45-46: 维护交接——目标（合并两页简化）
// ============================================================
function page45() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "3.1 \u7ef4\u62a4\u4ea4\u63a5\u2014\u2014\u76ee\u6807");
  makeTable(s,
    ["\u5e8f\u53f7", "\u5de5\u4f5c\u9879", "\u5de5\u4f5c\u8981\u70b9", "\u8d23\u4efb\u4eba", "\u4ea4\u4ed8\u4ef6"],
    [
      ["1", "\u5185\u90e8\u786e\u8ba4", "\u521d\u6b65\u660e\u786e\u9879\u76ee\u8fd0\u8425\u670d\u52a1\u8303\u56f4", "\u8fd0\u8425\u7ecf\u7406\n\u4ea4\u4ed8\u7ecf\u7406", "\u9879\u76ee\u8fd0\u8425\u5de5\u4f5c\u8bf4\u660e\u4e66"],
      ["2", "\u7ef4\u62a4\u8d44\u6599\u79fb\u4ea4", "\u5b8c\u6210\u6240\u6709\u7ef4\u62a4\u8d44\u6599\u63a5\u6536\u5165\u6863", "\u8fd0\u8425\u7ecf\u7406\n\u4ea4\u4ed8\u7ecf\u7406", "\u7ef4\u62a4\u8d44\u6599\u4ea4\u63a5\u8868"],
      ["3", "\u8fd0\u8425\u670d\u52a1\u65b9\u6848\n\u521d\u6b65\u786e\u5b9a", "\u521d\u6b65\u7f16\u5236\u8fd0\u8425\u670d\u52a1\u65b9\u6848", "\u8fd0\u8425\u7ecf\u7406\n\u5ba2\u6237\u7ecf\u7406\n\u4ea4\u4ed8\u7ecf\u7406", "\u9879\u76ee\u8fd0\u8425\u670d\u52a1\n\u521d\u6b65\u65b9\u6848"],
      ["4", "\u8fd0\u7ef4\u670d\u52a1\u56e2\u961f\u7ec4\u5efa", "\u5408\u7406\u7ec4\u5efa\u8fd0\u8425\u56e2\u961f", "\u8fd0\u8425\u7ecf\u7406", "\u8fd0\u8425\u56e2\u961f\u4eba\u5458\u6e05\u5355"],
      ["5", "\u8fd0\u7ef4\uff08\u8fd0\u8425\uff09\n\u670d\u52a1\u542f\u52a8\u4f1a", "\u660e\u786e\u8fd0\u8425\u76ee\u6807\u548c\u5404\u65b9\u804c\u8d23", "\u8fd0\u8425\u7ecf\u7406", "\u542f\u52a8\u4f1a\u4f1a\u8bae\u7eaa\u8981"],
      ["6", "\u8fd0\u8425\u670d\u52a1\u5bf9\u63a5", "\u4e0e\u5ba2\u6237\u786e\u8ba4\u670d\u52a1\u9700\u6c42\u3001\u6807\u51c6\u53ca\u8fd0\u8425\u65b9\u6848", "\u8fd0\u8425\u7ecf\u7406\n\u4ea4\u4ed8\u7ecf\u7406", "\u5ba2\u6237\u8fd0\u8425\u670d\u52a1\u9700\u6c42\n\u73b0\u573a\u8c03\u7814\u62a5\u544a"],
      ["7", "\u670d\u52a1\u9700\u6c42\u53ca\u6807\u51c6\n\u5ba2\u6237\u786e\u8ba4", "\u786e\u8ba4\u8fd0\u7ef4\u4eba\u6570\u3001\u6545\u969c\u54cd\u5e94\u5904\u7406\u65f6\u9650\u7b49", "\u8fd0\u8425\u7ecf\u7406", "\u670d\u52a1\u8981\u6c42\u53ca\u6807\u51c6\u62a5\u544a"],
      ["8", "\u5b8c\u5584\u8fd0\u8425\u670d\u52a1\u65b9\u6848\n\u5e76\u786e\u8ba4\u53d1\u5e03", "\u5b8c\u5584\u8fd0\u8425\u670d\u52a1\u65b9\u6848\u4e0e\u5ba2\u6237\u786e\u8ba4\u53d1\u5e03", "\u8fd0\u8425\u7ecf\u7406", "\u8fd0\u8425\u670d\u52a1\u65b9\u6848"]
    ],
    { colW: [0.5, 1.5, 3.5, 1.5, 2.0], rowH: [0.35, 0.45, 0.45, 0.45, 0.35, 0.45, 0.45, 0.45, 0.4] }
  );
  addBottomLine(s, 45);
}

function page46() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "3.1 \u7ef4\u62a4\u4ea4\u63a5\u2014\u2014\u76ee\u6807\uff08\u7eed\uff09");
  s.addText("\u5173\u952e\u8282\u70b9\uff1a\u8fd0\u8425\u670d\u52a1\u65b9\u6848\u786e\u8ba4\u53d1\u5e03", { x: 0.5, y: 1.3, w: 9.0, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });
  s.addText("\u00b7 \u8d44\u6599\u79fb\u4ea4\u5165\u6863\n\u00b7 \u8fd0\u8425\u670d\u52a1\u65b9\u6848\u521d\u6b65\u786e\u8ba4\n\u00b7 \u8fd0\u8425\u670d\u52a1\u56e2\u961f\u7ec4\u5efa\n\u00b7 \u8fd0\u7ef4\u542f\u52a8\u4f1a\n\u00b7 \u8fd0\u8425\u670d\u52a1\u65b9\u6848\u786e\u8ba4\u53d1\u5e03", { x: 0.7, y: 1.8, w: 8.6, h: 2.5, fontSize: 10, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  addBottomLine(s, 46);
}

// ============================================================
// PAGE 47-48: 项目运维——目标
// ============================================================
function page47() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "3.2 \u9879\u76ee\u8fd0\u7ef4\u2014\u2014\u76ee\u6807");
  makeTable(s,
    ["\u5e8f\u53f7", "\u5de5\u4f5c\u9879", "\u5de5\u4f5c\u8981\u70b9", "\u8d23\u4efb\u4eba", "\u4ea4\u4ed8\u4ef6"],
    [
      ["1", "\u8fd0\u8425\u56e2\u961f\u5165\u573a", "\u5b8c\u6210\u6587\u6863\u5b66\u4e60\uff0c\u5f00\u5c55\u8fc7\u6e21\u671f\u8fd0\u7ef4", "\u8fd0\u8425\u7ecf\u7406", "\u8bd5\u8fd0\u8425\u670d\u52a1\u62a5\u544a"],
      ["2", "\u4efb\u52a1\u4f5c\u4e1a\u6e05\u5355\u5206\u89e3", "\u7ec6\u5316\u4efb\u52a1\uff0c\u660e\u786e\u8d23\u4efb\u548c\u8981\u6c42", "\u8fd0\u8425\u7ecf\u7406", "\u4efb\u52a1\u4f5c\u4e1a\u6e05\u5355"],
      ["3", "\u6545\u969c\u7ba1\u63a7", "\u843d\u5b9e\u6545\u969c\u95ed\u73af\u673a\u5236\uff0c\u5b9e\u65bd\u6545\u969c\u5347\u7ea7\u4f20\u62a5\u8bc4\u4f30\u6574\u6539", "\u6545\u969c\u7ba1\u63a7\u8d1f\u8d23\u4eba", "\u6545\u969c\u5206\u6790\u62a5\u544a"],
      ["4", "\u8fd0\u8425\u5206\u6790", "\u5206\u6790\u5ba2\u6237\u4e1a\u52a1\u8fd0\u8425\u60c5\u51b5\u53ca\u670d\u52a1\u8d28\u91cf", "\u8fd0\u8425\u5206\u6790\u8d1f\u8d23\u4eba", "\u8fd0\u8425\u5206\u6790\u62a5\u544a"],
      ["5", "\u9a7b\u573a\u7ba1\u7406", "\u7ec4\u7ec7\u7ba1\u7406\u3001\u4efb\u52a1\u7ba1\u7406\u3001\u503c\u73ed\u7ba1\u7406", "\u9a7b\u573a\u8fd0\u7ef4\u8d1f\u8d23\u4eba", "\u9a7b\u573a\u5b9a\u671f\u68c0\u67e5"],
      ["6", "\u5b89\u5168\u7ba1\u7406", "\u5b89\u5168\u627f\u8bfa\u4e66\u3001\u5b89\u5168\u8d23\u4efb\u4e66\u3001\u5b9a\u8d23\u4e0e\u8003\u6838", "\u7ef4\u62a4\u5404\u65b9\u8d1f\u8d23\u4eba", "\u5b89\u5168\u5b9a\u671f\u68c0\u67e5"],
      ["7", "\u5ba2\u6237\u54cd\u5e94", "\u5408\u7406\u54cd\u5e94\u5ba2\u6237\u9700\u6c42\uff0c\u843d\u5b9e\u5404\u65b9\u8d23\u4efb\u90e8\u95e8", "\u8fd0\u8425\u7ecf\u7406", "\u5ba2\u6237\u9700\u6c42\u5de5\u5355"]
    ],
    { colW: [0.5, 1.5, 3.5, 1.5, 2.0], rowH: [0.35, 0.42, 0.42, 0.42, 0.42, 0.42, 0.42, 0.42], y: 1.2 }
  );
  addBottomLine(s, 47);
}

function page48() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "3.2 \u9879\u76ee\u8fd0\u7ef4\u2014\u2014\u76ee\u6807\uff08\u7eed\uff09");
  makeTable(s,
    ["\u5e8f\u53f7", "\u5de5\u4f5c\u9879", "\u5de5\u4f5c\u8981\u70b9", "\u8d23\u4efb\u4eba", "\u4ea4\u4ed8\u4ef6"],
    [
      ["1", "\u9879\u76ee\u8fd0\u8425\u8d28\u91cf\u5206\u6790", "\u5bf9\u8fd0\u8425\u670d\u52a1\u8d28\u91cf\u3001\u4e1a\u52a1\u8fd0\u884c\u8d28\u91cf\u53ca\u6545\u969c\u60c5\u51b5\u5206\u6790", "\u8fd0\u8425\u7ecf\u7406", "\u8fd0\u8425\u8d28\u91cf\u5206\u6790\u62a5\u544a"],
      ["2", "\u4e1a\u52a1\u6545\u969c\u7edf\u8ba1\u5206\u6790", "\u91cd\u5927\u6545\u969c\u3001\u5178\u578b\u6545\u969c\u5206\u6790\u548c\u6545\u969c\u5206\u6790\u4f8b\u4f1a", "\u5206\u6790\u8d1f\u8d23\u4eba", "\u4e1a\u52a1\u6545\u969c\u5206\u6790\u62a5\u544a"],
      ["3", "\u8bbe\u5907\u6027\u80fd\u5206\u6790", "\u5bf9\u8fd0\u7ef4\u60c5\u51b5\u3001\u8bbe\u5907\u6027\u80fd\u8fdb\u884c\u5206\u6790", "\u7ef4\u62a4\u5404\u65b9\u8d1f\u8d23\u4eba", "\u8bbe\u5907\u6027\u80fd\u5206\u6790\u62a5\u544a"],
      ["4", "\u5408\u4f5c\u4f19\u4f34\u670d\u52a1\u8d28\u91cf\u5206\u6790", "\u5bf9\u5408\u4f5c\u4f19\u4f34\u670d\u52a1\u652f\u6491\u60c5\u51b5\u7efc\u5408\u8bc4\u4ef7", "\u8fd0\u8425\u7ecf\u7406", "\u5408\u4f5c\u4f19\u4f34\u670d\u52a1\u8d28\u91cf\u62a5\u544a"],
      ["5", "\u5c65\u7ea6\u8bc4\u4f30\u8003\u6838", "\u7ef4\u62a4\u8d28\u91cf\u8003\u6838\u3001\u9a7b\u573a\u670d\u52a1\u8003\u6838\u3001\u4e13\u4e1a\u80fd\u529b\u8003\u6838\u7b49", "\u8fd0\u8425\u7ecf\u7406", "\u5c65\u7ea6\u8003\u8bc4\u8868"]
    ],
    { colW: [0.5, 1.5, 3.5, 1.5, 2.0], rowH: [0.35, 0.55, 0.55, 0.55, 0.55, 0.55], y: 1.2 }
  );
  addBottomLine(s, 48);
}

// ============================================================
// PAGE 49: 项目运营——目标
// ============================================================
function page49() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "3.3 \u9879\u76ee\u8fd0\u8425\u2014\u2014\u76ee\u6807");
  makeTable(s,
    ["\u5e8f\u53f7", "\u5de5\u4f5c\u9879", "\u5de5\u4f5c\u8981\u70b9", "\u8d23\u4efb\u4eba", "\u4ea4\u4ed8\u4ef6"],
    [
      ["1", "\u6570\u636e\u5206\u6790\u6316\u6398", "\u901a\u8fc7\u6570\u636e\u5206\u6790\uff0c\u6316\u6398\u5ba2\u6237\u65b0\u9700\u6c42\uff0c\u8fdb\u884c\u65b0\u5546\u673a\u7ebf\u7d22\u6d3e\u5355", "\u6570\u636e\u5206\u6790\u8d1f\u8d23\u4eba", "\u6570\u636e\u5206\u6790\u62a5\u544a"],
      ["2", "\u663e\u6027\u9700\u6c42\u6316\u6398", "\u57fa\u4e8e\u65e5\u5e38\u9a7b\u573a\u4eba\u5458\u4e0e\u5ba2\u6237\u4ea4\u4e92\u4e86\u89e3\u53ca\u5e73\u53f0\u5bb9\u91cf\u3001\u6545\u969c\u76d1\u63a7\u7b49", "\u8fd0\u8425\u7ecf\u7406", "\u5546\u673a\u9700\u6c42\u62a5\u544a"],
      ["3", "\u9690\u6027\u9700\u6c42\u6316\u6398", "\u57fa\u4e8e\u5ba2\u6237\u7cfb\u7edf\u5173\u952e\u4fe1\u606f\u3001\u884c\u4e1a\u9700\u6c42\u53d1\u5c55\u8d8b\u52bf\u53ca\u65e5\u5e38\u8fd0\u7ef4\u4fe1\u606f", "\u8fd0\u8425\u7ecf\u7406", "\u5546\u673a\u9700\u6c42\u62a5\u544a"],
      ["4", "\u5546\u673a\u8bc4\u4f30\u5bf9\u63a5", "\u79ef\u6781\u5bf9\u63a5\u5ba2\u6237\u7ecf\u7406\uff0c\u534f\u540c\u63a8\u52a8\u9879\u76ee\u4e8c\u6b21\u4ef7\u503c\u6316\u6398", "\u8fd0\u8425\u7ecf\u7406\n\u5ba2\u6237\u7ecf\u7406", "\u5546\u673a\u6c9f\u901a\u4f1a\u8bae\u7eaa\u8981"]
    ],
    { colW: [0.5, 1.5, 3.5, 1.5, 2.0], rowH: [0.35, 0.6, 0.6, 0.6, 0.6], y: 1.2 }
  );
  s.addText("\u5173\u952e\u8282\u70b9\uff1a\u6570\u636e\u5206\u6790\u62a5\u544a  \u00b7  \u5546\u673a\u8bc4\u4f30\u62a5\u544a", { x: 0.5, y: 4.3, w: 9.0, h: 0.3, fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });
  addBottomLine(s, 49);
}

// ============================================================
// PAGE 50: 售后服务调度机制
// ============================================================
function page50() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "3.4 \u552e\u540e\u670d\u52a1\u8c03\u5ea6\u673a\u5236", "\u660e\u786e\u4ea7\u6570\u9879\u76ee\u7eb3\u7ba1\u6807\u51c6\uff0c\u5b8c\u5584DICT\u9879\u76ee\u8fd0\u7ef4\u4f53\u7cfb\uff0c\u63a8\u8fdb\u8fd0\u7ef4\u80fd\u529b\u6709\u5e8f\u63d0\u5347\uff0c\u4fdd\u969c\u4ea7\u6570\u9879\u76ee\u7a33\u5b9a\u8fd0\u884c");
  // 中心圆
  s.addShape(pres.shapes.OVAL, { x: 3.5, y: 2.0, w: 3.0, h: 1.8, fill: { color: C.primary } });
  s.addText("DICT\u9879\u76ee\n\u7a33\u5b9a\u8fd0\u884c", { x: 3.5, y: 2.3, w: 3.0, h: 1.2, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
  s.addText("\u5ba2\u6237\u4f53\u9a8c\u597d  \u65e0\u6295\u8bc9  \u8fd0\u884c\u7a33  \u670d\u52a1\u597d", { x: 3.5, y: 3.5, w: 3.0, h: 0.3, fontSize: 7, fontFace: "Microsoft YaHei", color: C.white, align: "center", valign: "middle", margin: 0 });
  // 外围三环
  var rings = [
    { title: "\u7ef4\u62a4\u89c4\u7a0b", items: "\u901a\u7528\u7ef4\u62a4\u89c4\u7a0b | \u4e13\u4e1a\u7ef4\u62a4\u89c4\u7a0b | DICT\u7ef4\u62a4\u89c4\u7a0b", x: 0.3, y: 1.3, bg: C.brandBlue },
    { title: "\u8fd0\u7ef4\u6d41\u7a0b", items: "\u7ef4\u62a4\u4f5c\u4e1a | \u670d\u52a1\u4f5c\u4e1a | \u8fd0\u884c\u76d1\u63a7 | \u5ba2\u6237\u9700\u6c42\u627f\u63a5 | \u5b89\u5168\u7ba1\u7406 | \u5347\u7ea7\u7ba1\u7406", x: 0.3, y: 3.5, bg: C.teal },
    { title: "\u8fd0\u7ef4\u961f\u4f0d", items: "\u5ba2\u6237\u670d\u52a1\u5de5\u7a0b\u5e08 | \u670d\u52a1\u89e6\u70b9 | \u8fc7\u7a0b\u7edf\u7b79\u56e2\u961f | \u603b\u96c6\u5355\u4f4d | \u7ef4\u62a4\u5355\u5143", x: 7.0, y: 2.3, bg: C.orange }
  ];
  rings.forEach(function(r) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: r.x, y: r.y, w: 2.8, h: 1.2, fill: { color: r.bg }, rectRadius: 0.05 });
    s.addText(r.title, { x: r.x + 0.1, y: r.y + 0.05, w: 2.6, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
    s.addText(r.items, { x: r.x + 0.1, y: r.y + 0.35, w: 2.6, h: 0.75, fontSize: 7, fontFace: "Microsoft YaHei", color: C.white, align: "center", valign: "top", margin: 0, wrap: true });
  });
  addBottomLine(s, 50);
}

// ============================================================
// PAGE 51: 售后篇要点回顾
// ============================================================
function page51() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "\u552e\u540e\u7bc7\u2014\u2014\u8981\u70b9\u56de\u987e");
  s.addText("\u552e\u540e\u670d\u52a1\u8c03\u5ea6\u673a\u5236", { x: 3.0, y: 1.4, w: 4.0, h: 0.4, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", margin: 0 });
  var kw = [
    ["\u8fd0\u7ef4\u65b9\u6848", "\u521d\u6b65\u65b9\u6848"],
    ["\u8fd0\u8425\u56e2\u961f\u7ec4\u5efa", "\u65b9\u6848\u53d1\u5e03", "\u5b89\u5168\u7ba1\u7406"],
    ["\u5c65\u7ea6\u8bc4\u4f30", "\u6570\u636e\u5206\u6790", "\u5546\u673a\u8bc4\u4f30"]
  ];
  kw.forEach(function(row, ri) {
    row.forEach(function(k, ki) {
      var kw_x = 1.5 + ki * 2.5;
      var kw_y = 2.0 + ri * 0.65;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: kw_x, y: kw_y, w: 2.0, h: 0.45, fill: { color: ri === 0 ? C.pinkLight : (ri === 1 ? C.blueLight : C.greenLight) }, rectRadius: 0.03 });
      s.addText(k, { x: kw_x, y: kw_y, w: 2.0, h: 0.45, fontSize: 9, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle", margin: 0 });
    });
  });
  s.addText("\u76d1\u63a7\u8fd0\u8425\u7ba1\u7406\u5e73\u53f0", { x: 3.0, y: 4.0, w: 4.0, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.brandBlue, align: "center", margin: 0 });
  s.addText("\u672c\u7bc7\u4e3b\u8981\u4ecb\u7ecd\u4e86\u552e\u540e\u8fd0\u8425\uff1a\u4e00\u4e2a\u673a\u5236\u3001\u4e00\u5957\u4f53\u7cfb\u3001\u4e09\u4e2a\u73af\u8282\u3001\u5341\u4e2a\u5173\u952e\u70b9\uff0c\u5e2e\u52a9\u5927\u5bb6\u901a\u8fc7\u7ef4\u62a4\u8fc7\u7a0b\u7ba1\u63a7\u3001\u8d28\u91cf\u63d0\u5347\u63aa\u65bd\u3001\u5408\u4f5c\u4f19\u4f34\u8fd0\u7ef4\u80fd\u529b\u540e\u8bc4\u4f30\u3001\u8fd0\u7ef4\u670d\u52a1\u6570\u636e\u5206\u6790\u3001\u5546\u673a\u6316\u6398\u4e0e\u8f6c\u6362\u7b49\u65b9\u6cd5\uff0c\u4ece\u800c\u8fbe\u5230\u9879\u76ee\u5feb\u901f\u627f\u63a5\u3001\u8d28\u91cf\u7ba1\u63a7\u5230\u4f4d\u3001\u751f\u6001\u505a\u7cbe\u505a\u5f3a\u3001\u670d\u52a1\u589e\u503c\u589e\u6548\u7b49\u8fd0\u8425\u670d\u52a1\u76ee\u6807\u3002", { x: 0.7, y: 4.4, w: 8.6, h: 0.7, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  addBottomLine(s, 51);
}

// ============================================================
// PAGE 52: 转场页——提能提质 提效提速
// ============================================================
function page52() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  // 底部渐变装饰
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 4.7, w: 3.33, h: 0.93, fill: { color: C.yellow } });
  s.addShape(pres.shapes.RECTANGLE, { x: 3.33, y: 4.7, w: 3.34, h: 0.93, fill: { color: C.orange } });
  s.addShape(pres.shapes.RECTANGLE, { x: 6.67, y: 4.7, w: 3.33, h: 0.93, fill: { color: C.primary } });
  // 大字标题
  s.addText("\u63d0\u80fd\u63d0\u8d28", { x: 0.5, y: 1.5, w: 9.0, h: 1.2, fontSize: 56, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0 });
  s.addText("\u63d0\u6548\u63d0\u901f", { x: 0.5, y: 2.7, w: 9.0, h: 1.2, fontSize: 56, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0 });
  addBottomLine(s, 52);
}

// ============================================================
// PAGE 53: 附：虚假业绩"红线"不能碰
// ============================================================
function page53() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "\u9644\uff1a\u865a\u5047\u4e1a\u7ee9\u201c\u7ea2\u7ebf\u201d\u4e0d\u80fd\u78b0"); addBackLink(s);
  var cases = [
    { title: "\u865a\u5047\u8d38\u6613", desc: "\u9879\u76ee\u4e0a\u4e0b\u6e38\u5b58\u5728\u7279\u5b9a\u5229\u76ca\u5173\u7cfb\uff0c\u8f6f\u4ef6\u5b9e\u9645\u5747\u4e0d\u53ef\u7528\uff0c\u9879\u76ee\u4e0d\u5177\u5907\u4e1a\u52a1\u5b9e\u8d28\uff0c\u4e3a\u201c\u7a7a\u8f6c\u201d\u201c\u8d70\u5355\u201d\u4e1a\u52a1" },
    { title: "\u865a\u8d2d\u4e1a\u52a1", desc: "\u5c06B\u5ba2\u6237\u66f4\u540d\u4e3aA\u5ba2\u6237\u5e76\u66f4\u6539\u51fa\u8d26\u91d1\u989d\uff0c\u8fbe\u5230\u5c06A\u5ba2\u6237\u56de\u6b3e\u8f6c\u4e3a\u65b0\u589e\u6536\u5165\u7684\u76ee\u7684\u3002\u865a\u6784\u4e1a\u52a1\u53ca\u6d41\u7a0b\uff0c\u4ea7\u751f\u865a\u589e\u6536\u5165\u3002" },
    { title: "\u4eba\u4e3a\u8c03\u8282\u6536\u5165", desc: "\u79fb\u52a8OA\u5e73\u53f0\u7684ICT\u6210\u672c\u578b\u9879\u76ee\u4e2d\uff0c\u5c06\u624b\u673a\u7ec8\u7aef\u5305\u88c5\u6210\u6280\u672f\u670d\u52a1\u6536\u5165\uff0c\u8fdd\u53cd\u8ba1\u6536\u89c4\u5219\uff0c\u4ece\u800c\u4ea7\u751f\u865a\u589e\u4e3b\u8425\u6536\u5165\u3002" }
  ];
  cases.forEach(function(c, i) {
    var cy = 1.3 + i * 1.3;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: cy, w: 9.0, h: 1.1, fill: { color: C.pinkLight }, rectRadius: 0.05 });
    s.addText(c.title, { x: 0.7, y: cy + 0.1, w: 2.5, h: 0.35, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });
    s.addText(c.desc, { x: 0.7, y: cy + 0.45, w: 8.5, h: 0.55, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  });
  addBottomLine(s, 53);
}

// ============================================================
// PAGE 54-61: 附录表格页（统一模板）
// ============================================================
function page54() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "\u9644\uff1a\u6280\u672f\u65b9\u6848\u8bc4\u5ba1\u8981\u70b9"); addBackLink(s);
  makeTable(s, ["\u5e8f\u53f7", "\u8bc4\u5ba1\u8981\u70b9", "\u628a\u5173\u70b9"],
    [["1", "\u81ea\u6709\u80fd\u529b", "\u81ea\u6709\u80fd\u529b\u662f\u5426\u5e94\u7528\u5c3d\u7528"],
     ["2", "\u4e03\u878d", "\u4e0d\u91c7\u7528\u4e03\u878d\u7684\u7406\u7531"],
     ["3", "\u9879\u76ee\u5de5\u671f", "\u627f\u8bfa\u5de5\u671f/\u8d28\u4fdd\u671f\u9650"],
     ["4", "\u4ea4\u4ed8\u5185\u5bb9", "\u627f\u8bfa\u5185\u5bb9\u662f\u5426\u5305\u542b\u6240\u6709\u8bbe\u5907\u548c\u670d\u52a1"],
     ["5", "\u4f1a\u8bae\u7eaa\u8981", "\u4f1a\u8bae\u7eaa\u8981\u7684\u771f\u5b9e\u6027"],
     ["6", "\u751f\u6001\u4f19\u4f34", "\u751f\u6001\u4f19\u4f34\u7684\u6765\u6e90\u3001\u540e\u5411\u91c7\u8d2d\u7684\u5408\u89c4\u6027"],
     ["7", "\u8bbe\u5907\u9009\u578b", "\u6838\u5fc3\u8bbe\u5907\u9009\u578b\u548c\u76f8\u5173\u8981\u6c42"],
     ["8", "\u6280\u672f\u65b9\u6848", "\u8bc4\u5ba1\u6df1\u5ea6\u662f\u5426\u5408\u9002"],
     ["9", "\u70b9\u5c06\u9700\u6c42", "\u5185\u5916\u90e8\u6280\u672f\u4e13\u5bb6\u652f\u6491\u9700\u6c42"],
     ["10", "\u8fd0\u7ef4\u9700\u6c42", "\u8fd0\u7ef4\u671f\u9650/\u9a7b\u70b9\u8981\u6c42/\u8fd0\u7ef4\u8d39\u7528"],
     ["11", "\u98ce\u9669\u8bc4\u4f30", "\u65bd\u5de5\u5b89\u5168/\u7f51\u7edc\u5b89\u5168/\u5176\u4ed6\u98ce\u9669"],
     ["12", "\u5176\u4ed6\u56e0\u7d20", "\u9a8c\u6536\u65b9\u5f0f\u53ca\u6807\u51c6\u7b49"]],
    { colW: [0.6, 2.0, 6.4], rowH: [0.3, 0.33, 0.33, 0.33, 0.33, 0.33, 0.33, 0.33, 0.33, 0.33, 0.33, 0.33, 0.33], y: 1.2 }
  );
  addBottomLine(s, 54);
}

function page55() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "\u9644\uff1a\u6807\u524d\u591a\u4f1a\u5408\u4e00\u7684\u51b3\u7b56\u8981\u70b9"); addBackLink(s);
  makeTable(s, ["\u5e8f\u53f7", "\u8bc4\u5ba1\u8981\u70b9", "\u628a\u5173\u70b9"],
    [["1", "\u4e1a\u52a1\u6a21\u5f0f", "\u5546\u4e1a\u6a21\u5f0f/\u6210\u672c\u6216\u6295\u8d44\u4f7f\u7528\u65b9\u5f0f/\u6536\u5165\u786e\u8ba4\u65b9\u5f0f"],
     ["2", "\u6982\u7b97\u8bc4\u4f30", "\u524d\u5411\u6536\u5165\u9884\u6d4b/\u540e\u5411\u652f\u51fa\u9884\u6d4b/\u6210\u672c\u578b\u6bdb\u5229\u7387/\u6295\u8d44\u578bIRR"],
     ["3", "\u4ea4\u4ed8\u53ef\u884c\u6027\u8bc4\u4f30", "\u9879\u76ee\u6280\u672f\u53ef\u5b9e\u65bd\u6027/\u4ea4\u4ed8\u65f6\u95f4\u8981\u6c42/\u9a7b\u573a\u4ea4\u4ed8/\u8fd0\u8425\u7ef4\u4fdd"],
     ["4", "\u81ea\u6709\u80fd\u529b\u4f7f\u7528", "\u9879\u76ee\u6574\u4f53\u4e03\u878d/\u81ea\u6709\u80fd\u529b\u5360\u6bd4\u60c5\u51b5"],
     ["5", "\u91c7\u8d2d\u4e8b\u9879\u51b3\u7b56", "\u91c7\u8d2d\u65b9\u5f0f/\u7269\u8d44\u4e0e\u670d\u52a1\u5177\u4f53\u5185\u5bb9/\u91c7\u8d2d\u4ef7\u683c/\u5408\u540c\u4e3b\u8981\u6761\u6b3e"],
     ["6", "\u6295\u6807\u4e3b\u4f53", "\u4f01\u4e1a\u53ca\u4eba\u5458\u8d44\u8d28\u4e1a\u7ee9\u53ca\u63a7\u5206\u70b9"]],
    { colW: [0.6, 2.0, 6.4], rowH: [0.35, 0.45, 0.45, 0.55, 0.45, 0.55, 0.4], y: 1.3 }
  );
  addBottomLine(s, 55);
}

function page56() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "\u9644\uff1a\u6295\u6807\u4e3b\u4f53\u9009\u62e9");
  var cols = [
    { title: "\u603b\u96c6", desc: "\u4f5c\u4e3a\u9879\u76ee\u4e3b\u5bfc\u65b9\uff0c\u6574\u5408\u4e0a\u4e0b\u6e38\u8d44\u6e90\uff0c\u63d0\u4f9b\u6574\u4f53\u89e3\u51b3\u65b9\u6848", kw: "\u4f18\u52bf\u805a\u7126\u00b7\u751f\u6001\u7ed1\u5b9a\u00b7\u95e8\u69db\u8bbe\u7f6e\u00b7\u98ce\u9669\u8f6c\u5ac1" },
    { title: "\u88ab\u96c6\u6210", desc: "\u805a\u7126\u7ec6\u5206\u9886\u57df\u4f18\u52bf\uff0c\u6210\u4e3a\u603b\u96c6\u6210\u5546\u751f\u6001\u94fe\u4e2d\u7684\u5173\u952e\u4e00\u73af", kw: "\u6280\u672f\u5361\u4f4d\u00b7\u7075\u6d3b\u9002\u914d\u00b7\u98ce\u9669\u89c4\u907f\u00b7\u591a\u751f\u6001\u5e03\u5c40" },
    { title: "\u8054\u5408\u4f53", desc: "\u901a\u8fc7\u4f18\u52bf\u4e92\u8865\u63d0\u5347\u7efc\u5408\u7ade\u4e89\u529b\uff0c\u9002\u7528\u4e8e\u5927\u578b\u590d\u6742\u9879\u76ee", kw: "\u4f19\u4f34\u9009\u62e9\u00b7\u5206\u5de5\u673a\u5236\u00b7\u5229\u76ca\u7ed1\u5b9a\u00b7\u534f\u8bae\u4fdd\u969c" }
  ];
  cols.forEach(function(c, i) {
    var cx = 0.4 + i * 3.2;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx, y: 1.3, w: 3.0, h: 3.8, fill: { color: C.white }, line: { color: i === 0 ? C.primary : (i === 1 ? C.brandBlue : C.teal), width: 1 }, rectRadius: 0.05 });
    s.addText(c.title, { x: cx, y: 1.35, w: 3.0, h: 0.45, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.white, fill: { color: i === 0 ? C.primary : (i === 1 ? C.brandBlue : C.teal) }, align: "center", valign: "middle", margin: 0 });
    s.addText("\u6838\u5fc3\u5b9a\u4f4d", { x: cx + 0.15, y: 1.9, w: 2.7, h: 0.25, fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", margin: 0 });
    s.addText(c.desc, { x: cx + 0.15, y: 2.15, w: 2.7, h: 0.8, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
    s.addText("\u5173\u952e\u7b56\u7565", { x: cx + 0.15, y: 3.0, w: 2.7, h: 0.25, fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", margin: 0 });
    s.addText(c.kw, { x: cx + 0.15, y: 3.25, w: 2.7, h: 1.6, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  });
  addBottomLine(s, 56);
}

function page57() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "\u9644\uff1a\u524d\u5411\u5408\u540c\u7684\u5ba1\u6838\u8981\u70b9"); addBackLink(s);
  makeTable(s, ["\u5e8f\u53f7", "\u8981\u70b9", "\u8bc4\u5ba1\u5185\u5bb9"],
    [["1", "\u9879\u76ee\u5de5\u671f\u548c\u9a8c\u6536\u6761\u4ef6", "\u5305\u62ec\u4ea4\u4ed8\u8fdb\u5ea6\u3001\u4ea4\u4ed8\u6761\u4ef6\u3001\u4ea4\u4ed8\u5730\u70b9\u7b49"],
     ["2", "\u670d\u52a1\u5185\u5bb9", "\u91cd\u70b9\u5173\u6ce8\u5f00\u653e\u6027\u63cf\u8ff0\u3001\u65e0\u660e\u786e\u8981\u6c42\u3001\u201c\u514d\u8d39\u63d0\u4f9b\u201d\u7b49"],
     ["3", "\u552e\u540e\u670d\u52a1\u5185\u5bb9", "\u8bbe\u5907\u53ca\u670d\u52a1\u8d28\u4fdd\u671f\u8d77\u6b62\u65f6\u95f4\u3001\u670d\u52a1\u9891\u6b21\u3001\u670d\u52a1\u8303\u56f4"],
     ["4", "\u5408\u540c\u91d1\u989d\u53ca\u7a0e\u8d39", "\u786e\u4fdd\u5408\u540c\u91d1\u989d\u51c6\u786e\u65e0\u8bef\uff0c\u7a0e\u8d39\u6761\u6b3e\u6e05\u6670"],
     ["5", "\u5408\u540c\u652f\u4ed8\u6761\u6b3e", "\u4ed8\u6b3e\u65b9\u5f0f\u3001\u4ed8\u6b3e\u6761\u4ef6\u3001\u4ed8\u6b3e\u91d1\u989d\u7b49"],
     ["6", "\u8fdd\u7ea6\u8d23\u4efb\u3001\u5408\u540c\u7279\u522b\u7ea6\u5b9a", "\u8fdd\u7ea6\u91d1\u8ba1\u7b97\u65b9\u5f0f\u53ca\u8d54\u507f\u8303\u56f4"],
     ["7", "\u5408\u540c\u7ec8\u6b62\u6761\u4ef6", "\u786e\u4fdd\u5408\u540c\u7ec8\u6b62\u6761\u4ef6\u6e05\u6670\u660e\u786e"]],
    { colW: [0.6, 2.2, 6.2], rowH: [0.35, 0.55, 0.55, 0.45, 0.45, 0.45, 0.55, 0.45], y: 1.2 }
  );
  addBottomLine(s, 57);
}

function page58() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "\u9644\uff1a\u552e\u524d\u552e\u4e2d\u4ea4\u63a5\u6e05\u5355\uff08\u793a\u4f8b\uff09"); addBackLink(s);
  s.addText("\u89e3\u51b3\u65b9\u6848\u7ecf\u7406\u901a\u8fc7\u96c6\u56e2BPM\u7cfb\u7edf\u4e0a\u4f20\u9879\u76ee\u552e\u524d\u6587\u6863\uff0c\u9879\u76ee\u7ecf\u7406\u4f9d\u636e\u6a21\u677f\u9010\u4e00\u6e05\u6807\u5f0f\u63a5\u6536\u3002", { x: 0.5, y: 1.2, w: 9.0, h: 0.3, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "left", margin: 0, wrap: true });
  makeTable(s, ["\u5e8f\u53f7", "\u4ea4\u63a5\u4e8b\u9879", "\u4ea4\u63a5\u5185\u5bb9", "\u4ea4\u63a5\u786e\u8ba4\u4fe1\u606f", "\u4ea4\u5e95\u8d23\u4efb\u4eba", "\u63a5\u6536\u8d23\u4efb\u4eba"],
    [["1", "\u9879\u76ee\u80cc\u666f", "\u5efa\u8bbe\u76ee\u6807/\u89c4\u6a21/\u8986\u76d6\u8303\u56f4", "\u9a8c\u6536\u6807\u51c6", "\u89e3\u51b3\u65b9\u6848\u7ecf\u7406", "\u9879\u76ee\u7ecf\u7406"],
     ["2", "\u5efa\u8bbe\u8303\u56f4\u786e\u8ba4\u5355", "\u673a\u623f\u673a\u67dc/\u7535\u8def/\u7f51\u7edc\u8bbe\u5907", "\u9a8c\u6536\u6807\u51c6", "\u89e3\u51b3\u65b9\u6848\u7ecf\u7406", "\u9879\u76ee\u7ecf\u7406"],
     ["3", "\u5de5\u7a0b\u8981\u6c42\u786e\u8ba4\u5355", "\u6d4b\u8bd5\u73af\u5883/\u521d\u9a8c/\u8bd5\u8fd0\u884c/\u7ec8\u9a8c\u8981\u6c42", "\u9a8c\u6536\u6807\u51c6", "\u89e3\u51b3\u65b9\u6848\u7ecf\u7406", "\u9879\u76ee\u7ecf\u7406"],
     ["4", "\u552e\u524d\u6587\u4ef6\u6c47\u603b", "\u8be2\u4ef7\u51fd/\u96c6\u91c7\u9002\u914d/\u89e3\u51b3\u65b9\u6848\u89e3\u6784\u4e09\u5f20\u8868", "\u9a8c\u6536\u6807\u51c6", "\u89e3\u51b3\u65b9\u6848\u7ecf\u7406", "\u9879\u76ee\u7ecf\u7406"]],
    { colW: [0.5, 1.5, 2.8, 1.5, 1.5, 1.5], rowH: [0.35, 0.55, 0.55, 0.55, 0.55], y: 1.6 }
  );
  addBottomLine(s, 58);
}

function page59() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "\u9644\uff1a\u552e\u524d\u552e\u4e2d\u4ea4\u5e95\u98ce\u9669\u7684\u5ba1\u6838\u8981\u70b9"); addBackLink(s);
  var items = [
    { title: "\u4ea4\u4ed8\u5185\u5bb9\u786e\u8ba4", desc: "\u786e\u8ba4\u9700\u8981\u4ea4\u4ed8\u7684\u5185\u5bb9\u662f\u5426\u5168\u90e8\u54cd\u5e94\u5ba2\u6237\u9700\u6c42" },
    { title: "\u9a8c\u6536\u6807\u51c6\u786e\u8ba4", desc: "\u660e\u786e\u529f\u80fd\u6027\u6307\u6807\u3001\u6027\u80fd\u6027\u6307\u6807\uff0c\u6211\u65b9\u662f\u5426\u80fd\u63d0\u4f9b\u8bc1\u660e\u6750\u6599" },
    { title: "\u5de5\u671f\u786e\u8ba4", desc: "\u786e\u8ba4\u5de5\u671f\u8d77\u59cb\u65f6\u95f4\uff0c\u540e\u5411\u5efa\u8bbe\u7acb\u9879\u5ba1\u6279\u6d41\u7a0b\u6240\u9700\u65f6\u95f4" },
    { title: "\u8fd0\u7ef4\u670d\u52a1\u786e\u8ba4", desc: "\u786e\u8ba4\u8fd0\u7ef4\u9700\u6c42\u3001\u8fd0\u7ef4\u5f00\u59cb\u65e5\u671f\u3001\u8fd0\u7ef4\u8d23\u4efb\u4eba\u662f\u5426\u660e\u786e" },
    { title: "\u9879\u76ee\u534f\u8c03\u673a\u5236", desc: "\u660e\u786e\u9879\u76ee\u7ec4\u5185\u90e8\u5b9a\u671f\u6027\u4f8b\u4f1a\u53ca\u6c9f\u901a\u673a\u5236" }
  ];
  items.forEach(function(it, i) {
    var iy = 1.3 + i * 0.75;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: iy, w: 9.0, h: 0.65, fill: { color: i % 2 === 0 ? C.pinkLight : C.white }, rectRadius: 0.03 });
    s.addText(it.title, { x: 0.7, y: iy + 0.05, w: 2.0, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });
    s.addText(it.desc, { x: 0.7, y: iy + 0.32, w: 8.5, h: 0.3, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  });
  addBottomLine(s, 59);
}

function page60() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "\u9644\uff1a\u5b9e\u65bd\u65b9\u6848\u5ba1\u6838\u8868"); addBackLink(s);
  makeTable(s, ["\u5e8f\u53f7", "\u7c7b\u522b", "\u5ba1\u6838\u9879", "\u5ba1\u6838\u9879\u8bf4\u660e"],
    [["1", "\u9879\u76ee\u80cc\u666f", "\u9879\u76ee\u80cc\u666f", "\u771f\u5b9e\u6027/\u5173\u8054\u6027"],
     ["2", "\u9879\u76ee\u76ee\u6807", "\u9879\u76ee\u76ee\u6807", "\u660e\u786e\u6027/\u53ef\u8861\u91cf\u6027"],
     ["3", "\u9879\u76ee\u6982\u8ff0", "\u9879\u76ee\u9700\u6c42\u5206\u6790", "\u5b8c\u6574\u6027/\u5408\u7406\u6027"],
     ["4", "\u5de5\u4f5c\u8303\u56f4\u53ca\u5185\u5bb9", "\u5de5\u4f5c\u8303\u56f4\u53ca\u5185\u5bb9", "\u5168\u9762\u6027/\u5408\u7406\u6027"],
     ["5", "\u9879\u76ee\u5b9e\u65bd\u9636\u6bb5\u5212\u5206", "\u9879\u76ee\u5b9e\u65bd\u9636\u6bb5\u5212\u5206", "\u903b\u8f91\u6027/\u5408\u7406\u6027"],
     ["6", "\u91cc\u7a0b\u7891\u8ba1\u5212", "\u91cc\u7a0b\u7891\u8ba1\u5212\u53ca\u9879\u76ee\u4ea4\u4ed8\u6210\u679c", "\u91cd\u8981\u6027/\u660e\u786e\u6027"],
     ["7", "\u9879\u76ee\u4f1a\u8bae\u7ba1\u7406", "\u9879\u76ee\u4f1a\u8bae\u7ba1\u7406", "\u5fc5\u8981\u6027/\u6709\u6548\u6027"],
     ["8", "\u9879\u76ee\u95ee\u9898\u7ba1\u7406", "\u9879\u76ee\u95ee\u9898\u7ba1\u7406", "\u53ca\u65f6\u6027/\u6d41\u7a0b\u89c4\u8303\u6027"],
     ["9", "\u9879\u76ee\u98ce\u9669\u7ba1\u7406", "\u9879\u76ee\u98ce\u9669\u7ba1\u7406", "\u8bc6\u522b\u5168\u9762\u6027/\u8bc4\u4f30\u51c6\u786e\u6027"],
     ["10", "\u9879\u76ee\u53d8\u66f4\u7ba1\u7406", "\u9879\u76ee\u53d8\u66f4\u7ba1\u7406", "\u6d41\u7a0b\u89c4\u8303\u6027/\u5f71\u54cd\u8bc4\u4f30"],
     ["11", "\u9879\u76ee\u6587\u6863\u7ba1\u7406", "\u9879\u76ee\u6587\u6863\u7ba1\u7406", "\u5206\u7c7b\u5408\u7406\u6027/\u53ca\u65f6\u6027/\u5b89\u5168\u6027"],
     ["12", "\u9879\u76ee\u542f\u52a8", "\u9879\u76ee\u542f\u52a8\u51c6\u5907", "\u52a8\u5458\u5206/\u5145\u5206\u6027"],
     ["13", "\u9879\u76ee\u7ba1\u7406\u7ec4\u7ec7\u67b6\u6784", "\u9879\u76ee\u7ba1\u7406\u7ec4\u7ec7\u67b6\u6784", "\u5408\u7406\u6027/\u6c9f\u901a\u673a\u5236"],
     ["14", "\u9879\u76ee\u4eba\u5458\u804c\u80fd", "\u9879\u76ee\u4eba\u5458\u804c\u80fd", "\u660e\u786e\u6027/\u80fd\u529b\u9002\u914d"],
     ["15", "\u9879\u76ee\u4eba\u5458\u5217\u8868", "\u9879\u76ee\u4eba\u5458\u5217\u8868", "\u5b8c\u6574\u6027/\u8d44\u8d28\u5ba1\u6838"],
     ["16", "\u9879\u76ee\u51c6\u5907", "\u9879\u76ee\u51c6\u5907", "\u8d44\u6e90\u5145\u8db3\u6027/\u6280\u672f\u53ef\u884c\u6027"],
     ["17", "\u5177\u4f53\u5b9e\u65bd\u65b9\u6848", "\u5177\u4f53\u5b9e\u65bd\u65b9\u6848", "\u8be6\u7ec6\u7a0b\u5ea6/\u7075\u6d3b\u6027"],
     ["18", "\u6d4b\u8bd5\u76ee\u6807\u4e0e\u539f\u5219", "\u6d4b\u8bd5\u76ee\u6807\u4e0e\u539f\u5219", "\u660e\u786e\u6027/\u5408\u7406\u6027"],
     ["19", "\u6d4b\u8bd5\u65b9\u6848", "\u6d4b\u8bd5\u65b9\u6848", "\u573a\u666f\u771f\u5b9e\u6027/\u6307\u6807\u5408\u7406\u6027"],
     ["20", "\u7cfb\u7edf\u6027\u6d4b\u8bd5", "\u7cfb\u7edf\u6027\u6d4b\u8bd5", "\u5168\u9762\u6027/\u79d1\u5b66\u6027"],
     ["21", "\u7cfb\u7edf\u90e8\u7f72\u6c47\u603b", "\u7cfb\u7edf\u90e8\u7f72\u6c47\u603b", "\u8ba1\u5212\u5b8c\u6574\u6027/\u89c4\u8303\u6027"],
     ["22", "\u4fe1\u606f\u5b89\u5168\u65b9\u6848", "\u4fe1\u606f\u5b89\u5168\u65b9\u6848", "\u660e\u786e\u6027/\u6709\u6548\u6027"],
     ["23", "\u9a8c\u6536\u5185\u5bb9\u53ca\u6807\u51c6", "\u9a8c\u6536\u5185\u5bb9\u53ca\u6807\u51c6", "\u5168\u9762\u6027/\u53ef\u64cd\u4f5c\u6027"],
     ["24", "\u9a8c\u6536\u5c0f\u7ec4\u53ca\u804c\u8d23", "\u9a8c\u6536\u5c0f\u7ec4\u53ca\u804c\u8d23", "\u4e13\u4e1a\u6027/\u804c\u8d23\u6e05\u6670\u6027"],
     ["25", "\u552e\u540e\u670d\u52a1\u4f53\u7cfb", "\u552e\u540e\u670d\u52a1\u4f53\u7cfb", "\u5b8c\u6574\u6027/\u53ef\u9760\u6027"],
     ["26", "\u552e\u540e\u670d\u52a1\u5185\u5bb9", "\u552e\u540e\u670d\u52a1\u5185\u5bb9", "\u660e\u786e\u6027/\u9488\u5bf9\u6027"],
     ["27", "\u57f9\u8bad\u76ee\u6807", "\u57f9\u8bad\u76ee\u6807", "\u660e\u786e\u6027/\u5b9e\u7528\u6027"],
     ["28", "\u57f9\u8bad\u65b9\u6848", "\u57f9\u8bad\u65b9\u6848", "\u5bf9\u8c61\u51c6\u786e\u6027"],
     ["29", "\u57f9\u8bad\u5185\u5bb9", "\u57f9\u8bad\u5185\u5bb9", "\u9488\u5bf9\u6027/\u5b9e\u7528\u6027"]],
    { colW: [0.5, 1.5, 2.5, 4.5], rowH: [0.28], y: 1.15, rowFontSize: 6, headerFontSize: 7 }
  );
  addBottomLine(s, 60);
}

function page61() {
  var s = pres.addSlide(); s.background = { color: C.white }; addBrand(s);
  addTitleBar(s, "\u9644\uff1a\u4e3b\u5b9e\u534f\u540c\u3001\u7701\u4e13\u534f\u540c\u5de5\u4f5c\u673a\u5236"); addBackLink(s);
  // 左栏：省专协同
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.4, y: 1.3, w: 4.4, h: 3.6, fill: { color: C.white }, line: { color: C.primary, width: 0.75 }, rectRadius: 0.05 });
  s.addText("\u7701\u4e13\u534f\u540c", { x: 0.4, y: 1.3, w: 4.4, h: 0.4, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.white, fill: { color: C.primary }, align: "center", valign: "middle", margin: 0 });
  s.addText([{ text: "\u4ea7\u54c1\u8fd0\u8425\u534f\u540c\uff085\u573a\u666f\uff09\n", options: { bold: true, fontSize: 8, color: C.primary } }, { text: "\u4e91\u7535\u8111 \u00b7 AI5\u573a\u666f \u00b7 \u5b89\u5168\u5927\u8111 \u00b7 \u7269\u8054\u7f51 \u00b7 \u5929\u7ffc\u89c6\u8054 \u00b7 \u91cf\u5b50\u5bc6\u8bdd\n\n", options: { fontSize: 7, color: C.text } }, { text: "\u57fa\u7840\u7ef4\u62a4\u534f\u540c\uff086\u573a\u666f\uff09\n", options: { bold: true, fontSize: 8, color: C.primary } }, { text: "\u667a\u6167\u793e\u533a \u00b7 \u71c3\u6c14\u4e3a\u5e08 \u00b7 \u6570\u5b57\u4e61\u6751\n\n", options: { fontSize: 7, color: C.text } }, { text: "\u6570\u636e\u548c\u80fd\u529b\u5f00\u653e\uff083\u573a\u666f\uff09\n", options: { bold: true, fontSize: 8, color: C.primary } }, { text: "\u63d0\u8fd0\u8425 \u00b7 \u592f\u57fa\u7ef4 \u00b7 \u5f3a\u80fd\u529b", options: { fontSize: 7, color: C.text } }], { x: 0.6, y: 1.85, w: 4.0, h: 2.8, fontFace: "Microsoft YaHei", valign: "top", margin: 0, wrap: true });
  // 右栏：主实协同
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.1, y: 1.3, w: 4.4, h: 3.6, fill: { color: C.white }, line: { color: C.brandBlue, width: 0.75 }, rectRadius: 0.05 });
  s.addText("\u4e3b\u5b9e\u4e1a\u534f\u540c", { x: 5.1, y: 1.3, w: 4.4, h: 0.4, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.white, fill: { color: C.brandBlue }, align: "center", valign: "middle", margin: 0 });
  s.addText([{ text: "\u534f\u540c\u672c\u8d28\n", options: { bold: true, fontSize: 8, color: C.brandBlue } }, { text: "\u6218\u7565\u3001\u4e1a\u52a1\u3001\u6280\u672f\u5c42\u9762\u7684\u6df1\u5ea6\u7ed1\u5b9a\n\u8d44\u6e90\u4e92\u8865\u3001\u80fd\u529b\u5171\u4eab\n\u6280\u672f\u8d44\u6e90\u4e92\u8865\u3001\u8d44\u91d1\u6760\u6746\u3001\u4eba\u624d\u5171\u4eab\n\n", options: { fontSize: 7, color: C.text } }, { text: "\u843d\u5b9e\u65b9\u6848\n", options: { bold: true, fontSize: 8, color: C.brandBlue } }, { text: "\u7ec4\u7ec7\u4fdd\u969c\uff1a\u6210\u7acb\u5de5\u4f5c\u4e13\u73ed\n\u660e\u786e\u804c\u8d23\u5206\u5de5\n\n", options: { fontSize: 7, color: C.text } }, { text: "\u5efa\u8bbe\u89c4\u8303\n", options: { bold: true, fontSize: 8, color: C.brandBlue } }, { text: "\u89c4\u5212\u5efa\u8bbe\u534f\u540c\n\u63d0\u5347\u52a0\u8f7d\u6548\u7387\n\u7eb3\u5165\u5927\u7f51\u4f53\u7cfb\n\u5efa\u7acb\u552e\u540e\u89c4\u8303", options: { fontSize: 7, color: C.text } }], { x: 5.3, y: 1.85, w: 4.0, h: 2.8, fontFace: "Microsoft YaHei", valign: "top", margin: 0, wrap: true });
  // 底部关键词
  var bottomKw = ["\u63d0\u8fd0\u8425", "\u592f\u57fa\u7ef4", "\u5f3a\u80fd\u529b", "\u63d0\u6548\u7387", "\u4fc3\u53d1\u5c55", "\u62b5\u98ce\u9669"];
  bottomKw.forEach(function(kw, i) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5 + i * 1.55, y: 5.0, w: 1.4, h: 0.3, fill: { color: i % 2 === 0 ? C.primary : C.brandBlue }, rectRadius: 0.03 });
    s.addText(kw, { x: 0.5 + i * 1.55, y: 5.0, w: 1.4, h: 0.3, fontSize: 8, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
  });
  addBottomLine(s, 61);
}

// ============================================================
// 生成PPT

// ================================================================
// 生成全部61页
// ================================================================
page1(); page2(); page3(); page4(); page5();
page6(); page7(); page8(); page9(); page10();
page11(); page12(); page13(); page14(); page15();
page16(); page17(); page18(); page19(); page20();
page21(); page22(); page23(); page24(); page25();
page26(); page27(); page28(); page29(); page30();
page31(); page32(); page33(); page34(); page35();
page36(); page37(); page38(); page39(); page40();
page41(); page42(); page43(); page44(); page45();
page46(); page47(); page48(); page49(); page50();
page51(); page52(); page53(); page54(); page55();
page56(); page57(); page58(); page59(); page60();
page61();

const outPath = path.join(__dirname, "产数项目全流程管理.pptx");
pres.writeFile({ fileName: outPath }).then(() => {
  console.log('PPT generated: ' + outPath);
}).catch(err => {
  console.error('Error:', err);
});
