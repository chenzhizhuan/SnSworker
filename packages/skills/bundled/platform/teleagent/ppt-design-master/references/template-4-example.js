// gen_ict_template_part1.js - 复杂ICT自主交付PPT模板 Part1 (封面/背景目标/优势)
const pptxgen = require("pptxgenjs");
const path = require("path");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "China Telecom";
pres.title = "\u590d\u6742ICT\u9879\u76ee\u81ea\u4e3b\u4ea4\u4ed8\u6d41\u7a0b\u6a21\u677f";

// ===== 配色方案（依据截图提取） =====
const C = {
  primary: "C8102E",      // 电信品牌红（主色）
  redDeep: "A82820",      // 暗红棕（内容框边框）
  redDark: "8B0000",      // 深红（渐变起点）
  orange: "F29400",       // 橙色（渐变中段）
  yellow: "FFCC00",       // 明黄（渐变尾段）
  blue: "005AAA",         // 品牌蓝（辅助）
  blueLight: "E3F2FD",    // 浅蓝
  text: "000000",         // 正文黑
  textGray: "666666",     // 次要文字灰
  textLight: "999999",    // 浅灰（页码/系统标注）
  borderLight: "E5E5E5",  // 浅灰边框
  white: "FFFFFF",
  fillGray: "F5F5F5",     // 卡片灰
  green: "009688",        // 绿色（流程线）
  gold: "D4AF37"
};

// ===== 辅助函数 =====

// 右上角5G标识
function addLogo(slide) {
  slide.addText("5", { x: 9.0, y: 0.15, w: 0.45, h: 0.4, fontSize: 20, fontFace: "Arial", bold: true, color: C.blue, align: "right", valign: "middle", margin: 0 });
  slide.addText("G", { x: 9.38, y: 0.15, w: 0.35, h: 0.4, fontSize: 20, fontFace: "Arial", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });
  slide.addShape(pres.shapes.OVAL, { x: 9.72, y: 0.22, w: 0.035, h: 0.035, fill: { color: C.orange } });
  slide.addShape(pres.shapes.OVAL, { x: 9.68, y: 0.13, w: 0.045, h: 0.045, fill: { color: C.orange } });
  slide.addShape(pres.shapes.OVAL, { x: 9.62, y: 0.04, w: 0.06, h: 0.06, fill: { color: C.orange } });
}

// 标题栏：标题 + 红橙黄渐变条 + 右上角logo + 可选副标题
function addTitleBar(slide, title, subtitle) {
  slide.addText(title, { x: 0.4, y: 0.15, w: 8.2, h: 0.5, fontSize: 22, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });
  addLogo(slide);
  var gY = 0.72;
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: gY, w: 3.06, h: 0.035, fill: { color: C.primary } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 3.46, y: gY, w: 3.06, h: 0.035, fill: { color: C.orange } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 6.52, y: gY, w: 3.08, h: 0.035, fill: { color: C.yellow } });
  if (subtitle) {
    slide.addText(subtitle, { x: 0.4, y: 0.82, w: 9.2, h: 0.4, fontSize: 13, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle", margin: 0, wrap: true });
  }
}

// 底部页码
function addPageNum(slide, num) {
  slide.addText(String(num), { x: 9.3, y: 5.2, w: 0.4, h: 0.25, fontSize: 10, fontFace: "Microsoft YaHei", color: C.textLight, align: "right", valign: "middle", margin: 0 });
}

// 半闭合暗红边框（四角留缺口）
function addBrokenBorder(slide, x, y, w, h) {
  var t = 0.014;
  var gap = 0.3;
  var c = C.redDeep;
  slide.addShape(pres.shapes.RECTANGLE, { x: x + gap, y: y, w: w - 2 * gap, h: t, fill: { color: c } });
  slide.addShape(pres.shapes.RECTANGLE, { x: x + gap, y: y + h - t, w: w - 2 * gap, h: t, fill: { color: c } });
  slide.addShape(pres.shapes.RECTANGLE, { x: x, y: y + gap, w: t, h: h - 2 * gap, fill: { color: c } });
  slide.addShape(pres.shapes.RECTANGLE, { x: x + w - t, y: y + gap, w: t, h: h - 2 * gap, fill: { color: c } });
}

function addFlowBox(slide, x, y, w, h, label, opts) {
  opts = opts || {};
  slide.addShape(pres.shapes.RECTANGLE, { x: x, y: y, w: w, h: h, fill: { color: C.white }, line: { color: opts.lineColor || C.blue, width: 1, dash: opts.dash || "solid" } });
  slide.addText(label, { x: x, y: y, w: w, h: h, fontSize: opts.fontSize || 9, fontFace: "Microsoft YaHei", color: opts.color || C.text, align: "center", valign: "middle", margin: 0, wrap: true });
}

function addDashedBox(slide, x, y, w, h, color) {
  slide.addShape(pres.shapes.RECTANGLE, { x: x, y: y, w: w, h: h, fill: { color: C.white }, line: { color: color || C.primary, width: 1, dash: "dash" } });
}

function addArrow(slide, x, y, w, h, color) {
  slide.addShape(pres.shapes.RIGHT_ARROW, { x: x, y: y, w: w, h: h, fill: { color: color || C.blue } });
}

// ========== PAGE 1: 封面 ==========
function page1() {
  const s = pres.addSlide();
  // 底部丝绸流线装饰（AI生成的飘逸绸带，白底融合，作为最底层背景）
  s.addImage({
    path: path.join(__dirname, "ict_ribbon.png"),
    x: 0, y: 0, w: 10, h: 5.625, sizing: { type: "cover", w: 10, h: 5.625 }
  });
  // 顶部浅灰渐变背景
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.35, fill: { color: "F5F5F5" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0.35, w: 10, h: 0.2, fill: { color: "FAFAFA" } });

  // 左上角中国电信logo图片
  s.addImage({
    path: path.join(__dirname, "ict_logo.png"),
    x: 0.25, y: 0.2, w: 1.7, h: 0.55, sizing: { type: "contain", w: 1.7, h: 0.55 }
  });
  // 右上角 5G
  s.addText("5", { x: 8.9, y: 0.25, w: 0.45, h: 0.4, fontSize: 20, fontFace: "Arial", bold: true, color: C.blue, align: "right", valign: "middle", margin: 0 });
  s.addText("G", { x: 9.25, y: 0.25, w: 0.35, h: 0.4, fontSize: 20, fontFace: "Arial", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.OVAL, { x: 9.6, y: 0.3, w: 0.03, h: 0.03, fill: { color: C.orange } });
  s.addShape(pres.shapes.OVAL, { x: 9.56, y: 0.22, w: 0.04, h: 0.04, fill: { color: C.orange } });
  s.addShape(pres.shapes.OVAL, { x: 9.5, y: 0.13, w: 0.05, h: 0.05, fill: { color: C.orange } });

  // 主标题
  s.addText("\u5173\u4e8e\u590d\u6742ICT\u9879\u76ee\u7684\u81ea\u4e3b\u4ea4\u4ed8\u6d41\u7a0b", { x: 0.5, y: 1.6, w: 9.0, h: 1.0, fontSize: 36, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0 });
  // 浅灰分隔线
  s.addShape(pres.shapes.RECTANGLE, { x: 1.5, y: 2.62, w: 7.0, h: 0.012, fill: { color: "D0D0D0" } });
  // 归属信息（两行：部门 / 日期）
  s.addText("\u653f\u4f01\u9879\u76ee\u4ea4\u4ed8\u90e8", { x: 0.5, y: 2.82, w: 9.0, h: 0.4, fontSize: 14, fontFace: "Microsoft YaHei", color: C.textGray, align: "center", valign: "middle", margin: 0 });
  s.addText("2026\u5e747\u6708", { x: 0.5, y: 3.2, w: 9.0, h: 0.4, fontSize: 14, fontFace: "Microsoft YaHei", color: C.textGray, align: "center", valign: "middle", margin: 0 });
}

// ===== PAGE 2: 任务背景及目标 =====
function page2() {
  const s = pres.addSlide();
  addTitleBar(s, "\u4efb\u52a1\u80cc\u666f\u53ca\u76ee\u6807");

  // 内容区外框
  var boxX = 0.4, boxY = 0.95, boxW = 9.2, boxH = 4.35;
  addBrokenBorder(s, boxX, boxY, boxW, boxH);

  // 上模块：集团部署时间线
  var m1Y = 1.15;
  // 红色标识块
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.55, y: m1Y, w: 0.8, h: 0.35, fill: { color: C.primary }, rectRadius: 0.03 });
  s.addText("\u96c6\u56e2\u90e8\u7f72", { x: 0.55, y: m1Y, w: 0.8, h: 0.35, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
  // 说明文字
  s.addText("\u96c6\u56e2\u9886\u5bfc\u8981\u6c42\u4e91\u7f51\u534f\u540c\u653f\u4f01\uff0c\u4f9d\u6258\u96c6\u56e2\u4e91\u7f51ISOC\u961f\u4f0d\uff08\u542b\u88c5\u7ef4\uff09\uff0c\u505a\u5f3a\u4ea7\u6570\u81ea\u4e3b\u4ea4\u4ed8\u80fd\u529b", { x: 1.5, y: m1Y - 0.02, w: 8.0, h: 0.4, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "center", valign: "middle", margin: 0 });
  s.addText("\u653f\u4f01\u6253\u9020\u6d41\u7a0b\uff0c\u8c03\u5ea6\u4e91\u7f51\u5b9e\u65bd\u81ea\u4e3b\u4ea4\u4ed8", { x: 1.55, y: m1Y + 0.3, w: 7.5, h: 0.32, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "center", valign: "middle", margin: 0 });

  // 三个时间节点
  var nodeY = m1Y + 0.72;
  var startX = 0.9;
  var stepX = 2.9;
  var nodes = [
    ["25\u5e747\u6708\u534a\u5e74\u4f1a", "\u63d0\u5347\u4ea7\u6570\u81ea\u4e3b\u4ea4\u4ed8\u80fd\u529b"],
    ["25\u5e749\u6708\u7763\u529e\u4efb\u52a1", "\u7740\u529b\u63d0\u5347\u81ea\u4e3b\u4ea4\u4ed8\u80fd\u529b"],
    ["25\u5e7412\u6708\u6539\u9769\u4e13\u73ed\u4f1a\u8bae", "\u4ea7\u6570\u81ea\u4e3b\u4ea4\u4ed8\u80fd\u529b\u662f\u6cbb\u4f01\u80fd\u529b\u7684\u91cd\u8981\u7ec4\u6210\u90e8\u5206"]
  ];
  for (var i = 0; i < 3; i++) {
    var nx = startX + i * stepX;
    if (i > 0) {
      s.addShape(pres.shapes.RIGHT_ARROW, { x: nx - 0.35, y: nodeY + 0.1, w: 0.25, h: 0.18, fill: { color: C.primary } });
    }
    s.addText(nodes[i][0], { x: nx, y: nodeY, w: 2.7, h: 0.3, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0 });
    var noteW = (i === 2) ? 2.5 : 2.7;
    var noteX = (i === 2) ? nx + 0.1 : nx;
    var noteFs = (i === 2) ? 9 : 10;
    s.addText(nodes[i][1], { x: noteX, y: nodeY + 0.3, w: noteW, h: 0.35, fontSize: noteFs, fontFace: "Microsoft YaHei", color: C.textGray, align: "center", valign: "middle", margin: 0, wrap: true });
  }

  // 上下模块分隔线
  var sepY = 2.9;
  s.addShape(pres.shapes.RECTANGLE, { x: 0.55, y: sepY, w: 8.9, h: 0.01, fill: { color: "D8D8D8" } });

  // 下模块：目标拆解
  var m2Y = 3.0;
  s.addText("\u76ee\u6807\u662f\u5b8c\u5168\u627f\u63a5\u6807\u54c1\u53ca\u6807\u51c6ICT\u7684\u81ea\u4e3b\u4ea4\u4ed8\uff0c", { x: 1.0, y: m2Y, w: 4.6, h: 0.35, fontSize: 13, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "right", valign: "middle", margin: 0 });
  s.addText("\u63d0\u8d28\u589e\u6548", { x: 5.55, y: m2Y, w: 1.2, h: 0.35, fontSize: 13, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });
  s.addText("\uff1b\u68b3\u7406\u590d\u6742ICT\u81ea\u4e3b\u4ea4\u4ed8\u80fd\u529b\uff0c\u6253\u9020\u673a\u5236\u6d41\u7a0b", { x: 2.2, y: m2Y + 0.3, w: 5.6, h: 0.35, fontSize: 13, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "center", valign: "middle", margin: 0 });

  // 三个板块 01/02/03
  var bY = 3.85;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.55, y: bY, w: 0.7, h: 0.35, fill: { color: C.blue }, rectRadius: 0.03 });
  s.addText("01", { x: 0.55, y: bY, w: 0.7, h: 0.35, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
  s.addText("\u6807\u54c1", { x: 1.35, y: bY, w: 1.0, h: 0.35, fontSize: 13, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "left", valign: "middle", margin: 0 });
  s.addText("\u6807\u54c1--\u76ee\u6807100%\u63a5\u5e94\uff0c\u7279\u522b\u662f\u89c6\u8054\u3001\u4e91\u684c\u9762\u7b49\u91cd\u70b9\u4e1a\u52a1", { x: 2.3, y: bY, w: 7.3, h: 0.35, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "left", valign: "middle", margin: 0 });

  var bY2 = bY + 0.42;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.55, y: bY2, w: 0.7, h: 0.35, fill: { color: C.blue }, rectRadius: 0.03 });
  s.addText("02", { x: 0.55, y: bY2, w: 0.7, h: 0.35, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
  s.addText("\u6807\u51c6ICT", { x: 1.35, y: bY2, w: 1.2, h: 0.35, fontSize: 13, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "left", valign: "middle", margin: 0 });
  s.addText("\u6807\u51c6ICT--\u76ee\u6807100%\u63a5\u5e94\uff0c\u5305\u62ec\u57fa\u7840\u7248\u3001\u589e\u5f3a\u7248\u3001\u9ad8\u9636\u7248\u7684\u786c\u4ef6\u5b89\u88c5\u4ee5\u53ca\u5bf9\u5e94\u7684\u63d2\u4ef6\u4ea4\u4ed8", { x: 2.3, y: bY2, w: 7.3, h: 0.35, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "left", valign: "middle", margin: 0 });

  var bY3 = bY2 + 0.42;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.55, y: bY3, w: 0.7, h: 0.35, fill: { color: C.primary }, rectRadius: 0.03 });
  s.addText("03", { x: 0.55, y: bY3, w: 0.7, h: 0.35, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
  s.addText("\u590d\u6742ICT", { x: 1.35, y: bY3, w: 1.2, h: 0.35, fontSize: 13, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "left", valign: "middle", margin: 0 });
  s.addText("\u590d\u6742ICT--\u76ee\u6807\u7ed3\u5408\u4e91\u7f51\u80fd\u529b\u68b3\u7406\u590d\u6742DICT\u9879\u76ee\u573a\u666f\uff0c\u5faa\u5e8f\u6e10\u8fdb\u5c55\u5f00\u81ea\u4e3b\u4ea4\u4ed8", { x: 2.3, y: bY3, w: 7.3, h: 0.35, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "left", valign: "middle", margin: 0 });

  addPageNum(s, 2);
}

// ===== PAGE 3: 自主交付优势 =====
function page3() {
  const s = pres.addSlide();
  addTitleBar(s, "\u300a\u590d\u6742ICT\u81ea\u4e3b\u4ea4\u4ed8\uff1a\u81ea\u4e3b\u4ea4\u4ed8\u4f18\u52bf\u300b");

  // 副标题两行
  s.addText("\u901a\u8fc7\u4e91\u7f51\u81ea\u4e3b\u4ea4\u4ed8\u529b\u91cf\uff0c\u63d0\u5347\u9879\u76ee\u5229\u6da6\uff0c\u4fc3\u8fdb\u653f\u4f01\u6253\u5355\u80fd\u529b", { x: 0.4, y: 0.82, w: 9.2, h: 0.32, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0 });
  s.addText("\u5145\u5206\u8fd0\u7528\u4e91\u7f51\u81ea\u4e3b\u4ea4\u4ed8\u7684\u5168\u56fd\u8986\u76d6\u4f18\u52bf\uff0c\u8fdb\u884c\u7c7b\u6807\u54c1\u7684\u6d41\u7a0b\u5316\u63a8\u5e7f\uff0c\u901a\u8fc7\u804c\u8d23\u673a\u5236\u4fdd\u969c\u6d41\u7a0b\u53ef\u843d\u5730", { x: 0.4, y: 1.14, w: 9.2, h: 0.32, fontSize: 14, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0 });

  // 内容区半闭合边框
  addBrokenBorder(s, 0.4, 1.6, 9.2, 3.6);

  // 四模块：2x2 网格
  var mw = 4.4, mh = 1.55;
  var mx = [0.55, 5.15];
  var my = [1.78, 3.52];
  var mods = [
    { title: "\u63d0\u5347\u5229\u6da6", col: 0, row: 0, lines: [
      "\u76f8\u6bd4\u751f\u6001\u961f\u4f0d\uff0c\u76f4\u63a5\u63d0\u5347\u9879\u76ee\u5229\u6da6",
      "\u7701\u5185\u9879\u76ee\uff08\u5730\u5e02\u5185\u6216\u8de8\u5730\u5e02\uff09\u81ea\u4e3b\u4ea4\u4ed8\uff0c\u4e0d\u6d89\u53ca\u5177\u4f53\u4ed8\u73b0\u652f\u51fa\uff0c\u81ea\u4e3b\u4ea4\u4ed8\u7684\u6536\u5165\u90e8\u5206\u90fd\u662f\u9879\u76ee\u5229\u6da6",
      "\u8de8\u57df\u7684\u7701\u95f4\u7ed3\u7b97\u6210\u672c\u4f4e\u4e8e\u5916\u90e8\u751f\u6001\u961f\u4f0d\uff0c\u7efc\u5408\u4f18\u60e0\u5e45\u5ea6\u572815-30%\u4e4b\u95f4\uff0c\u91c7\u7528\u6536\u5165\u5206\u6210\u65b9\u5f0f\u8fdb\u884c\u7ed3\u7b97"
    ]},
    { title: "\u6d41\u7a0b\u4f18\u52bf", col: 1, row: 0, lines: [
      "\u6253\u9020\u7c7b\u6807\u54c1\u6d41\u7a0b\uff0c\u4e1a\u52a1\u7ecf\u7406\u53ef\u4ece\u96c6\u56e2CRM\u5165\u53e3\u53d7\u7406\uff0c\u76f4\u8fbe\u5404\u7701\u7efc\u8c03\u6d3e\u5355\u5230\u88c5\u7ef4\uff0c\u4e0d\u9700\u8981\u8fdb\u884c\u4e8c\u6b21\u8c03\u5ea6",
      "\u8fdb\u4e00\u6b65\u878d\u5165\u4e3b\u6d41\u6d41\u7a0b\uff0c\u53ef\u7531\u4e2d\u53f0\u5230\u4e91\u7f51\u7684\u4ea4\u4ed8\u5b9e\u65bd\u8c03\u5ea6\u6e20\u9053"
    ]},
    { title: "\u5168\u56fd\u8986\u76d6", col: 0, row: 1, lines: [
      "\u591a\u70b9\u5e76\u53d1\u7684\u672b\u6802\u4ea4\u4ed8\uff0c\u6709\u5168\u56fd\u5e02\u3001\u533a\u53bf\u3001\u4e61\u53ca\u6751\u672b\u6802\u88c5\u7ef4\u81ea\u4e3b\u4ea4\u4ed8\u961f\u4f0d\u505a\u73b0\u573a\u5b9e\u65bd\uff0c\u5bf9\u6bd4\u751f\u6001\u6709\u660e\u663e\u8986\u76d6\u4f18\u52bf",
      "\u9ad8\u7ea7\u4ea4\u4ed8\u7531\u5c5e\u5730\u4e91\u7f51ISOC\u7ec4\u7ec7\u6216\u76f4\u63a5\u5b9e\u65bd"
    ]},
    { title: "\u673a\u5236\u4fdd\u969c", col: 1, row: 1, lines: [
      "\u6218\u7565\u3001\u4e91\u7f51\u3001\u653f\u4f01\u8054\u5408\u53d1\u6587\u843d\u5b9e\u804c\u8d23\uff0c\u96c6\u56e2\u4e91\u7f5130%\u81ea\u4e3b\u4ea4\u4ed8\u8003\u6838\u5404\u7701\u4e91\u7f51\uff0c\u4fdd\u8bc1\u81ea\u4e3b\u4ea4\u4ed8\u5b9e\u65bd\u843d\u5730",
      "\u81ea\u4e3b\u4ea4\u4ed8\u53ef\u4ee5\u5e73\u6ed1\u8fc7\u6e21\u5230\u81ea\u4e3b\u4ea4\u4ed8\u8fd0\u7ef4\uff0c\u89e3\u51b3\u7ef4\u62a4\u804c\u8d23\u4e0d\u6e05\u695a\u7684\u95ee\u9898\uff0c\u4f46\u662f\u9700\u8981\u9002\u5f53\u8003\u8651\u6210\u672c"
    ]}
  ];

  for (var i = 0; i < mods.length; i++) {
    var m = mods[i];
    var cx = mx[m.col];
    var cy = my[m.row];
    s.addShape(pres.shapes.RECTANGLE, { x: cx, y: cy, w: 0.16, h: 0.16, fill: { color: C.primary } });
    s.addText(m.title, { x: cx + 0.22, y: cy - 0.04, w: 2.0, h: 0.25, fontSize: 13, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });
    var ly = cy + 0.28;
    for (var j = 0; j < m.lines.length; j++) {
      s.addText("\u2713", { x: cx, y: ly, w: 0.18, h: 0.2, fontSize: 9, fontFace: "Arial", bold: true, color: C.textGray, align: "center", valign: "middle", margin: 0 });
      s.addText(m.lines[j], { x: cx + 0.2, y: ly, w: mw - 0.2, h: 0.6, fontSize: 8.5, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
      ly += 0.6;
    }
  }

  addPageNum(s, 3);
}

// ========== PAGE 4: 具体流程设计（泳道图） ==========
function page4() {
  const s = pres.addSlide();
  addTitleBar(s, "复杂ICT项目自主交付：具体流程设计");
  s.addText("提供双入口下单流程，方便政企一线或中台派发自主交付任务；由云网ISOC进行施工总集调度，发单人进行验收", { x: 0.4, y: 0.82, w: 9.2, h: 0.35, fontSize: 13, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle", margin: 0 });

  // 内容区外框
  addBrokenBorder(s, 0.4, 1.25, 9.2, 3.95);

  // 泳道数据
  var lanes = [
    { sys: "BPM", name: "政企 解决方案经理" },
    { sys: "线下", name: "项目各参与方（集成/中台/ISOC等）" },
    { sys: "BPM/集团CRM", name: "云中台 项目经理/政企业务经理" },
    { sys: "省公司综调", name: "云网通 ISOC" },
    { sys: "省公司综调", name: "云网通 跨省ISOC/本省高端交付/装维一线" }
  ];

  var laneYs = [1.5, 2.1, 2.7, 3.3, 3.9];

  for (var i = 0; i < 5; i++) {
    var ly = laneYs[i];
    // 泳道左侧标签
    s.addText(lanes[i].sys, { x: 0.55, y: ly - 0.02, w: 1.6, h: 0.18, fontSize: 7, fontFace: "Microsoft YaHei", color: C.textLight, align: "left", valign: "middle", margin: 0 });
    s.addText(lanes[i].name, { x: 0.55, y: ly + 0.16, w: 1.6, h: 0.28, fontSize: 9, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "left", valign: "middle", margin: 0, wrap: true });
  }

  // 泳道1：方案解构
  addFlowBox(s, 2.3, 1.45, 1.5, 0.4, "1·方案解构", { fontSize: 9 });
  s.addText("✓ 明确交付、验收、售后的标准", { x: 4.0, y: 1.45, w: 3.5, h: 0.4, fontSize: 8, fontFace: "Microsoft YaHei", color: C.primary, align: "left", valign: "middle", margin: 0 });

  // 泳道2：制定总体实施方案
  addFlowBox(s, 4.6, 2.05, 1.8, 0.4, "4.0·制定总体实施方案", { fontSize: 8 });
  s.addText("\u2713 入口2：大的集中项目通过业务解构受理（私有云）", { x: 6.55, y: 2.06, w: 2.9, h: 0.2, fontSize: 7, fontFace: "Microsoft YaHei", color: C.primary, align: "left", valign: "middle", margin: 0 });
  s.addText("\u2713 入口1：小的三联单等散点业务，直接从订单受理（连接）", { x: 6.55, y: 2.28, w: 2.9, h: 0.2, fontSize: 7, fontFace: "Microsoft YaHei", color: C.primary, align: "left", valign: "middle", margin: 0 });

  // 跨泳道箭头：1·方案解构 → 4.0·制定总体方案
  s.addShape(pres.shapes.LINE, { x: 3.05, y: 1.85, w: 0, h: 0.2, line: { color: C.primary, width: 1.25 } });
  s.addShape(pres.shapes.LINE, { x: 3.05, y: 2.05, w: 1.5, h: 0, line: { color: C.primary, width: 1.25, endArrowType: "triangle" } });

  // 泳道3：中台把关/业务解构/发起工单/审核/验收
  addFlowBox(s, 2.3, 2.68, 1.35, 0.4, "2·中台把关", { fontSize: 9 });
  addArrow(s, 3.72, 2.8, 0.18, 0.18, C.orange);
  addFlowBox(s, 3.95, 2.68, 1.35, 0.4, "3·业务解构", { fontSize: 9 });
  addArrow(s, 5.37, 2.8, 0.18, 0.18, C.orange);
  addFlowBox(s, 5.6, 2.68, 1.35, 0.4, "4/1·发起工单", { fontSize: 9 });
  // 菱形判断框：中台管理员审核（灰色虚线）
  s.addShape(pres.shapes.DIAMOND, { x: 7.15, y: 2.68, w: 1.2, h: 0.4, fill: { color: C.white }, line: { color: C.textGray, width: 1, dash: "dash" } });
  s.addText("中台管理员审核", { x: 7.15, y: 2.68, w: 1.2, h: 0.4, fontSize: 7.5, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle", margin: 0, wrap: true });
  addArrow(s, 8.42, 2.8, 0.18, 0.18, C.orange);
  addFlowBox(s, 8.65, 2.68, 0.95, 0.4, "4/2·发起工单", { fontSize: 8 });

  // 跨泳道箭头：4.0 → 4/1（下行）
  s.addShape(pres.shapes.LINE, { x: 5.9, y: 2.45, w: 0, h: 0.23, line: { color: C.primary, width: 1.25, endArrowType: "triangle" } });

  // 泳道4：施工总集调度
  s.addText("\u2713 数字交付平台IT接口", { x: 2.3, y: 3.28, w: 2.5, h: 0.2, fontSize: 7.5, fontFace: "Microsoft YaHei", color: C.primary, align: "left", valign: "middle", margin: 0 });
  addFlowBox(s, 4.6, 3.28, 1.5, 0.4, "6·施工总集调度", { fontSize: 9 });

  // 跨泳道箭头：4/2 → 6（折线向下再向左）
  s.addShape(pres.shapes.LINE, { x: 9.12, y: 3.08, w: 0, h: 0.12, line: { color: C.primary, width: 1.25 } });
  s.addShape(pres.shapes.LEFT_ARROW, { x: 6.2, y: 3.12, w: 2.92, h: 0.16, fill: { color: C.primary } });

  // 泳道5：接单施工/报验
  addFlowBox(s, 4.6, 3.9, 1.35, 0.4, "7·接单施工", { fontSize: 9 });
  addArrow(s, 6.02, 4.02, 0.18, 0.18, C.blue);
  addFlowBox(s, 6.25, 3.9, 1.35, 0.4, "8·报验", { fontSize: 9 });
  addArrow(s, 7.67, 4.02, 0.18, 0.18, C.blue);

  // 验收菱形（蓝色）
  s.addShape(pres.shapes.DIAMOND, { x: 8.0, y: 3.9, w: 1.2, h: 0.4, fill: { color: C.white }, line: { color: C.blue, width: 1 } });
  s.addText("验收", { x: 8.0, y: 3.9, w: 1.2, h: 0.4, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle", margin: 0 });

  // 跨泳道箭头：6 → 7（向下）
  s.addShape(pres.shapes.LINE, { x: 5.35, y: 3.68, w: 0, h: 0.22, line: { color: C.primary, width: 1.25, endArrowType: "triangle" } });

  // 泳道分隔线
  for (var k = 0; k < 4; k++) {
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.55 + k * 0.62, w: 9.0, h: 0.01, fill: { color: "D8D8D8" } });
  }

  addPageNum(s, 4);
}

// ========== PAGE 5: 流程入口1 - CRM下单 ==========
function page5() {
  const s = pres.addSlide();
  addTitleBar(s, "流程入口1：直接从集团CRM下单自主交付的方法，配置账号，会下单");

  // 左栏：账号说明+下单说明卡片
  var lx = 0.4, lw = 3.3;
  // 账号卡片（红虚线边框）
  addDashedBox(s, lx, 1.2, lw, 1.85);
  s.addText("\u25a0 账号", { x: lx + 0.1, y: 1.3, w: 1.0, h: 0.3, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "left", valign: "middle", margin: 0 });
  s.addText("\u2713 集团CRM账号分为角色及产品权限，具备直接在集团CRM前台进行下单的角色是项目经理、业务经理、客户经理；需要具备的产品权限为“ICT业务”，账号的角色及产品权限统一由各省的CRM管理员进行配置", { x: lx + 0.1, y: 1.62, w: lw - 0.2, h: 1.35, fontSize: 8, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });

  // 下单卡片（红虚线边框）
  var c2y = 3.2;
  addDashedBox(s, lx, c2y, lw, 2.3);
  s.addText("\u25a0 下单信息:", { x: lx + 0.1, y: c2y + 0.08, w: 1.5, h: 0.28, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "left", valign: "middle", margin: 0 });
  s.addText("\u2713 分订单、业务、资费三部分信息，全集团都在用，部分信息自主交付不需要关注", { x: lx + 0.1, y: c2y + 0.38, w: lw - 0.2, h: 0.32, fontSize: 7.5, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  s.addText("1. 订单信息：大家需要关注是否带出来集团固有客户即可，带不出来就在集团CRM创建一个；结算类型务必选择中国电信；装机地址必须填写清楚", { x: lx + 0.1, y: c2y + 0.72, w: lw - 0.2, h: 0.42, fontSize: 7, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  s.addText("2. 业务信息：项目类型要选择自主交付；对于关联业务号、电路号，填写“无”即可；重点把工作内容、售中及售后要求填写清楚，并上传必要交付及验收的详细标准要求附件", { x: lx + 0.1, y: c2y + 1.16, w: lw - 0.2, h: 0.52, fontSize: 7, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  s.addText("3. 资费信息：分为一次性费用和周期性费用，体现省内自主交付价值及跨域结算；注意的是周期性那里都需要选一下，避免漏填，连锁企业以一次性费用为主", { x: lx + 0.1, y: c2y + 1.7, w: lw - 0.2, h: 0.58, fontSize: 7, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });

  // 右栏：CRM表单界面模拟
  var rx = 4.0, rw = 5.6;
  // 表单外框
  s.addShape(pres.shapes.RECTANGLE, { x: rx, y: 1.2, w: rw, h: 4.25, fill: { color: C.white }, line: { color: "C8C8C8", width: 1 } });
  // 订单信息模块
  s.addText("订单信息", { x: rx + 0.1, y: 1.3, w: 1.0, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "left", valign: "middle", margin: 0 });
  // 橙色渐变标识
  s.addShape(pres.shapes.RECTANGLE, { x: rx + 0.05, y: 1.3, w: 0.04, h: 0.3, fill: { color: C.orange } });
  s.addShape(pres.shapes.RECTANGLE, { x: rx + 0.09, y: 1.3, w: 0.04, h: 0.3, fill: { color: C.yellow } });

  // 输入框模拟（灰色小框）
  var fw = 1.1, fh = 0.22;
  var fxs = [rx + 0.4, rx + 0.4 + 1.15, rx + 0.4 + 2.3, rx + 0.4 + 3.45];
  var fy = 1.7;
  var fLabels = ["客户", "销售人员", "结算类型", "装机地址"];
  for (var i = 0; i < 4; i++) {
    s.addShape(pres.shapes.RECTANGLE, { x: fxs[i], y: fy, w: fw, h: fh, fill: { color: C.white }, line: { color: "C8C8C8", width: 0.75 } });
    s.addText(fLabels[i], { x: fxs[i] + 0.05, y: fy, w: fw - 0.1, h: fh, fontSize: 7, fontFace: "Microsoft YaHei", color: C.textGray, align: "left", valign: "middle", margin: 0 });
  }
  // 红色实线高亮框（订单信息）
  s.addShape(pres.shapes.RECTANGLE, { x: fxs[0] - 0.03, y: fy - 0.03, w: fw + 0.06, h: fh + 0.06, fill: { color: "FFFFFF", transparency: 100 }, line: { color: C.primary, width: 1.5 } });
  s.addText("选择客户账号，一般搜索即可", { x: fxs[0], y: fy + fh + 0.02, w: fw + 0.3, h: 0.18, fontSize: 6.5, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });

  // 业务信息模块
  var b2y = 2.35;
  s.addText("业务信息", { x: rx + 0.1, y: b2y, w: 1.0, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "left", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: rx + 0.05, y: b2y, w: 0.04, h: 0.3, fill: { color: C.orange } });
  s.addShape(pres.shapes.RECTANGLE, { x: rx + 0.09, y: b2y, w: 0.04, h: 0.3, fill: { color: C.yellow } });
  s.addShape(pres.shapes.RECTANGLE, { x: rx + 0.4, y: b2y + 0.4, w: 2.6, h: 0.3, fill: { color: C.white }, line: { color: "C8C8C8", width: 0.75 } });
  s.addText("项目类型：自主交付", { x: rx + 0.45, y: b2y + 0.4, w: 2.5, h: 0.3, fontSize: 8, fontFace: "Microsoft YaHei", color: C.textGray, align: "left", valign: "middle", margin: 0 });
  // 红色高亮
  s.addShape(pres.shapes.RECTANGLE, { x: rx + 0.37, y: b2y + 0.37, w: 2.66, h: 0.36, fill: { color: "FFFFFF" }, transparency: 100, line: { color: C.primary, width: 1.5 } });
  s.addText("此处要选择自主交付", { x: rx + 0.4, y: b2y + 0.72, w: 2.5, h: 0.18, fontSize: 6.5, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });

  // 资费信息模块
  var b3 = 3.3;
  s.addText("资费信息", { x: rx + 0.1, y: b3, w: 1.0, h: 0.3, fontSize: 10, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "left", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: rx + 0.05, y: b3, w: 0.04, h: 0.3, fill: { color: C.orange } });
  s.addShape(pres.shapes.RECTANGLE, { x: rx + 0.09, y: b3, w: 0.04, h: 0.3, fill: { color: C.yellow } });
  s.addShape(pres.shapes.RECTANGLE, { x: rx + 0.4, y: b3 + 0.4, w: 2.6, h: 0.3, fill: { color: C.white }, line: { color: "C8C8C8", width: 0.75 } });
  s.addText("服务费科目", { x: rx + 0.45, y: b3 + 0.4, w: 2.5, h: 0.3, fontSize: 8, fontFace: "Microsoft YaHei", color: C.textGray, align: "left", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: rx + 0.37, y: b3 + 0.37, w: 2.66, h: 0.36, fill: { color: "FFFFFF" }, transparency: 100, line: { color: C.primary, width: 1.5 } });
  s.addText("尽量选择服务费科目，并且时间周期按整年填写", { x: rx + 0.4, y: b3 + 0.72, w: 3.0, h: 0.18, fontSize: 6.5, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });

  // 模块间虚线分隔
  s.addShape(pres.shapes.RECTANGLE, { x: rx + 0.1, y: 2.3, w: rw - 0.2, h: 0.01, fill: { color: "C8C8C8" }, line: { color: "C8C8C8", width: 0.5, dash: "dash" } });
  s.addShape(pres.shapes.RECTANGLE, { x: rx + 0.1, y: 3.25, w: rw - 0.2, h: 0.01, fill: { color: "C8C8C8" }, line: { color: "C8C8C8", width: 0.5, dash: "dash" } });

  addPageNum(s, 5);
}

// ========== PAGE 6: 全国应用情况（表格） ==========
function page6() {
  const s = pres.addSlide();
  addTitleBar(s, "流程入口1：全国陆续已经开展了实质性应用");
  s.addText("集团已经打通从集团CRM-数字交付平台-各省综调的派单能力", { x: 0.4, y: 0.85, w: 9.2, h: 0.3, fontSize: 13, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle", margin: 0 });
  s.addText("目前全国累计派单4839单，其中江苏、广东派单量较多，湖南、广西、湖北有实际的项目应用", { x: 0.4, y: 1.15, w: 9.2, h: 0.3, fontSize: 13, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle", margin: 0 });

  // 左栏：CRM截图模拟（红虚线框）
  var lx = 0.4, lw = 4.0, ly = 1.6, lh = 3.7;
  s.addShape(pres.shapes.RECTANGLE, { x: lx, y: ly, w: lw, h: lh, fill: { color: C.white }, line: { color: C.primary, width: 1, dash: "dash" } });
  s.addText("集团CRM前台受理截图", { x: lx, y: ly - 0.35, w: lw, h: 0.3, fontSize: 12, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle", margin: 0 });
  // 模拟系统界面
  s.addShape(pres.shapes.RECTANGLE, { x: lx + 0.15, y: ly + 0.15, w: lw - 0.3, h: 0.4, fill: { color: "F0F4F8" }, line: { color: "C8C8C8", width: 0.5 } });
  s.addText("业务查询", { x: lx + 0.25, y: ly + 0.2, w: 1.0, h: 0.4, fontSize: 10, fontFace: "Microsoft YaHei", color: C.blue, align: "left", valign: "middle", margin: 0 });
  // 红色高亮框（业务查询）
  s.addShape(pres.shapes.RECTANGLE, { x: lx + 0.12, y: ly + 0.17, w: 1.2, h: 0.46, fill: { color: "FFFFFF" }, transparency: 100, line: { color: C.primary, width: 1.5 } });
  s.addText("这里点业务查询", { x: lx + 0.15, y: ly + 0.65, w: 2.0, h: 0.2, fontSize: 7, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });

  // 三个下拉框模拟
  for (var i = 0; i < 3; i++) {
    s.addShape(pres.shapes.RECTANGLE, { x: lx + 0.15 + i * 1.1, y: ly + 1.1, w: 1.0, h: 0.35, fill: { color: C.white }, line: { color: "C8C8C8", width: 0.75 } });
  }
  s.addText("配置", { x: lx + 0.22, y: ly + 1.1, w: 0.9, h: 0.35, fontSize: 8, fontFace: "Microsoft YaHei", color: C.textGray, align: "left", valign: "middle", margin: 0 });
  s.addText("省份", { x: lx + 1.32, y: ly + 1.1, w: 0.9, h: 0.35, fontSize: 8, fontFace: "Microsoft YaHei", color: C.textGray, align: "left", valign: "middle", margin: 0 });
  s.addText("订单类型", { x: lx + 2.42, y: ly + 1.1, w: 0.9, h: 0.35, fontSize: 8, fontFace: "Microsoft YaHei", color: C.textGray, align: "left", valign: "middle", margin: 0 });
  // 红色高亮框（三个下拉框）
  s.addShape(pres.shapes.RECTANGLE, { x: lx + 0.12, y: ly + 1.07, w: 3.15, h: 0.41, fill: { color: "FFFFFF" }, transparency: 100, line: { color: C.primary, width: 1.5 } });
  s.addText("这里选择查询条件", { x: lx + 0.15, y: ly + 1.52, w: 2.0, h: 0.2, fontSize: 7, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });
  // 提交按钮
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: lx + 0.15, y: ly + 1.85, w: 0.8, h: 0.35, fill: { color: C.blue }, rectRadius: 0.04 });
  s.addText("提交", { x: lx + 0.15, y: ly + 1.85, w: 0.8, h: 0.35, fontSize: 10, fontFace: "Microsoft YaHei", color: C.white, align: "center", valign: "middle", margin: 0 });

  // 右栏：各省派单统计表格
  var rx = 4.7, rw = 4.9;
  s.addText("各省派单情况，数据取自4月底", { x: rx, y: 1.25, w: rw, h: 0.3, fontSize: 12, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle", margin: 0 });

  // 表格数据（26行+总计）
  var headers = ["发起省", "拆机", "非正常变更", "新装", "正常变更", "总计"];
  var rows = [
    ["江苏", "", "128", "3724", "", "3852"],
    ["广东", "", "", "699", "", "699"],
    ["湖南", "3", "3", "25", "2", "33"],
    ["广西", "2", "8", "19", "3", "32"],
    ["山西", "12", "1", "13", "1", "27"],
    ["辽宁", "2", "2", "14", "6", "24"],
    ["四川", "1", "6", "12", "2", "21"],
    ["湖北", "4", "4", "10", "2", "20"],
    ["新疆", "", "", "18", "", "18"],
    ["河北", "1", "3", "7", "1", "12"],
    ["重庆", "1", "3", "6", "2", "12"],
    ["福建", "1", "1", "7", "1", "10"],
    ["云南", "2", "2", "5", "1", "10"],
    ["贵州", "1", "1", "6", "1", "9"],
    ["天津", "1", "2", "4", "2", "9"],
    ["江西", "1", "1", "4", "1", "7"],
    ["西藏", "1", "1", "4", "1", "7"],
    ["海南", "1", "", "3", "2", "6"],
    ["宁夏", "2", "1", "2", "1", "6"],
    ["山东", "1", "1", "4", "", "6"],
    ["甘肃", "1", "1", "2", "1", "5"],
    ["青海", "1", "1", "2", "1", "5"],
    ["上海", "1", "1", "2", "1", "5"],
    ["浙江", "", "", "2", "", "2"],
    ["河南", "", "", "1", "", "1"],
    ["陕西", "", "", "1", "", "1"]
  ];

  var tableData = [headers.map(function(h) {
    return { text: h, options: { fontSize: 7.5, fontFace: "Microsoft YaHei", bold: true, color: C.text, fill: { color: "DCE9F5" }, align: "center", valign: "middle", border: { color: "C8C8C8", pt: 0.5 }, margin: [1, 2, 1, 2] } };
  })];
  rows.forEach(function(row, ri) {
    tableData.push(row.map(function(cell, ci) {
      return { text: cell, options: { fontSize: 7, fontFace: "Microsoft YaHei", color: C.text, fill: { color: C.white }, align: ci === 0 ? "left" : "center", valign: "middle", border: { color: "C8C8C8", pt: 0.5 }, margin: [1, 2, 1, 2] } };
    }));
  });
  // 总计行
  tableData.push(["总计", "40", "171", "4596", "32", "4839"].map(function(cell, ci) {
    return { text: cell, options: { fontSize: 7.5, fontFace: "Microsoft YaHei", bold: true, color: C.text, fill: { color: "DCE9F5" }, align: ci === 0 ? "left" : "center", valign: "middle", border: { color: "C8C8C8", pt: 0.5 }, margin: [1, 2, 1, 2] } };
  }));

  s.addTable(tableData, { x: rx, y: 1.6, w: rw, colW: [0.9, 0.6, 1.1, 0.8, 0.8, 0.7], rowH: 0.12, border: { color: "C8C8C8", pt: 0.5 } });

  addPageNum(s, 6);
}

// ========== PAGE 7: 流程入口2（时间线） ==========
function page7() {
  const s = pres.addSlide();
  addTitleBar(s, "流程入口2：建设中，流程中的出账、售后、结算、计收与入口1一致");

  // 上模块：规划思路（红虚线圆角框）
  var box1 = { x: 0.4, y: 1.2, w: 9.2, h: 2.0 };
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: box1.x, y: box1.y, w: box1.w, h: box1.h, fill: { color: C.white }, line: { color: C.primary, width: 1, dash: "dash" }, rectRadius: 0.05 });
  s.addText("规划思路：以商机为主线，打造融入主流流程的后向实施调度及跨域结算流程，实现业务解构从管理到生产的闭环", { x: 0.5, y: 1.28, w: 9.0, h: 0.35, fontSize: 12, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "center", valign: "middle", margin: 0 });

  // 三个分类标签
  var tags = ["BPM（集团）", "综调（省）", "EDA（集团、省）"];
  var tagX = [1.0, 4.2, 7.3];
  for (var i = 0; i < 3; i++) {
    s.addText(tags[i], { x: tagX[i], y: 1.7, w: 1.5, h: 0.25, fontSize: 9, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle", margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x: tagX[i] + 0.1, y: 1.95, w: 1.3, h: 0.015, fill: { color: C.blue } });
  }

  // 时间轴（红色线 + 箭头）
  s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 2.35, w: 7.55, h: 0.02, fill: { color: C.primary } });
  s.addShape(pres.shapes.RIGHT_ARROW, { x: 8.35, y: 2.3, w: 0.3, h: 0.12, fill: { color: C.primary } });
  // 9个节点（红色前5 + 灰色后4）
  var nodeNames = ["方案解构", "中台把关", "业务解构", "订单调度", "计费下账", "售中交付", "售后维护", "后向结算", "计列收入"];
  var nodeColors = [C.primary, C.primary, C.primary, C.primary, C.primary, "B0B0B0", "B0B0B0", "B0B0B0", "B0B0B0"];
  var nxs = [1.0, 2.0, 3.0, 4.0, 5.0, 5.9, 6.8, 7.7, 8.75];
  for (var n = 0; n < 9; n++) {
    s.addShape(pres.shapes.OVAL, { x: nxs[n] - 0.06, y: 2.29, w: 0.14, h: 0.14, fill: { color: nodeColors[n] } });
    s.addText(nodeNames[n], { x: nxs[n] - 0.45, y: 2.02, w: 0.9, h: 0.25, fontSize: 7, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle", margin: 0 });
  }

  // 节点说明（三行排布）
  var notes1 = [
    "\u2713 售前方案阶段，充分考虑使用自主交付服务",
    "\u2713 把关实现自主交付的应用共享",
    "\u2713 业务解构梳理四类自主交付服务",
    "\u2713 加载业务解构驱动自主交付订单，自动搬运信息",
    "\u2713 在省计费完成算费出账，通过“产数非标集约下账”或原流程",
    "\u2713 省ISOC在省端侧对任务进行直接接应及调度到装维末梢",
    "\u2713 集团、省两级综调实现全国现场调度，关联施工单编码",
    "\u2713 通过集团一站式结算，跨省结算到交付队伍所在利润单位",
    "\u2713 省公司按省内市场/政企管理要求计列收入"
  ];
  var noteX = [0.7, 0.7, 3.7, 3.7, 6.7, 6.7, 0.7, 3.7, 6.7];
  var noteY = [2.6, 2.78, 2.6, 2.78, 2.6, 2.78, 2.96, 2.96, 2.96];
  var noteW = [3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 2.9];
  for (var ni = 0; ni < 9; ni++) {
    s.addText(notes1[ni], { x: noteX[ni], y: noteY[ni], w: noteW[ni], h: 0.2, fontSize: 6.5, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "middle", margin: 0, wrap: true });
  }

  // 下模块：规划节奏（红虚线圆角框）
  var box2 = { x: 0.4, y: 3.35, w: 9.2, h: 1.85 };
  addDashedBox(s, box2.x, box2.y, box2.w, box2.h);
  s.addText("规划节奏：逐步构建复杂ICT自主交付调度体系，", { x: 0.5, y: 3.4, w: 4.5, h: 0.3, fontSize: 11, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "left", valign: "middle", margin: 0 });
  s.addText("先用起来", { x: 5.0, y: 3.4, w: 1.0, h: 0.3, fontSize: 11, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "left", valign: "middle", margin: 0 });
  s.addText("；再将高频“个性化”需求固化为“内部流程”，最终实现“规模化”", { x: 2.2, y: 3.7, w: 6.8, h: 0.3, fontSize: 11, fontFace: "Microsoft YaHei", bold: true, color: C.text, align: "center", valign: "middle", margin: 0 });

  // 左侧橙色块
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 4.1, w: 1.3, h: 0.6, fill: { color: C.orange } });
  s.addText("复杂DICT项目", { x: 0.6, y: 4.1, w: 1.3, h: 0.6, fontSize: 8, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0, wrap: true });
  // 两条分叉箭头（蓝色）
  s.addShape(pres.shapes.RIGHT_ARROW, { x: 2.0, y: 4.15, w: 0.5, h: 0.12, fill: { color: C.blue } });
  s.addShape(pres.shapes.RIGHT_ARROW, { x: 2.0, y: 4.55, w: 0.5, h: 0.12, fill: { color: C.blue } });
  // 灰色块：可标准化的/不可标准化的
  s.addShape(pres.shapes.RECTANGLE, { x: 2.6, y: 4.05, w: 1.3, h: 0.3, fill: { color: "B0B0B0" } });
  s.addText("可标准化的", { x: 2.6, y: 4.05, w: 1.3, h: 0.3, fontSize: 8, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 2.6, y: 4.5, w: 1.3, h: 0.3, fill: { color: "B0B0B0" } });
  s.addText("不可标准化的", { x: 2.6, y: 4.5, w: 1.3, h: 0.3, fontSize: 8, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
  // 右侧箭头
  addArrow(s, 4.0, 4.15, 0.5, 0.12, C.blue);
  addArrow(s, 4.0, 4.55, 0.5, 0.12, C.blue);
  // 内部流程 / 项目个性化
  s.addShape(pres.shapes.RECTANGLE, { x: 4.6, y: 4.05, w: 1.3, h: 0.3, fill: { color: "909090" } });
  s.addText("内部流程", { x: 4.6, y: 4.05, w: 1.3, h: 0.3, fontSize: 8, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 4.6, y: 4.5, w: 1.3, h: 0.3, fill: { color: "909090" } });
  s.addText("项目个性化", { x: 4.6, y: 4.5, w: 1.3, h: 0.3, fontSize: 8, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });

  // 规模化箭头
  s.addShape(pres.shapes.RIGHT_ARROW, { x: 6.0, y: 4.1, w: 0.35, h: 0.18, fill: { color: C.blue } });
  s.addText("规模化", { x: 6.0, y: 4.3, w: 0.35, h: 0.18, fontSize: 7, fontFace: "Microsoft YaHei", bold: true, color: C.primary, align: "center", valign: "middle", margin: 0 });

  // 右侧卡片（内部流程6个）
  var cards = ["售前方案", "中台把关", "业务解构", "调度下单", "结算列收", "售后服务"];
  for (var ci = 0; ci < 6; ci++) {
    var cx2 = 6.6 + (ci % 3) * 1.05;
    var cy2 = 4.05 + Math.floor(ci / 3) * 0.4;
    s.addShape(pres.shapes.RECTANGLE, { x: cx2, y: cy2, w: 0.95, h: 0.28, fill: { color: "E0E8F0" } });
    s.addText(cards[ci], { x: cx2, y: cy2, w: 0.95, h: 0.28, fontSize: 6.5, fontFace: "Microsoft YaHei", color: C.text, align: "center", valign: "middle", margin: 0 });
  }

  addPageNum(s, 7);
}


// ==================== 生成完整7页PPT ====================
page1();
page2();
page3();
page4();
page5();
page6();
page7();

var outPath = path.join(__dirname, "ict_template_full.pptx");
pres.writeFile({ fileName: outPath }).then(function() {
  console.log("PPT saved to:", outPath);
}).catch(function(err) {
  console.error("Error:", err);
});
