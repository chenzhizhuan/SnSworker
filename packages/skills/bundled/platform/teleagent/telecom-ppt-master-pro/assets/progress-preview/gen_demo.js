// =====================================================================
// 示例生成脚本 · 5 页电信红 deck，演示"实时进度预览"工具集成
//
// 运行（首次会自动启动 server 并打开浏览器）:
//   $env:NODE_PATH = (npm root -g)
//   node gen_demo.js
//
// 关键约定:
//   1. module.exports 导出 { deckMeta, setup, buildSlides }
//   2. 用 `if (require.main === module)` 守卫 run() 调用，避免被渲染子进程 require 时递归
//   3. 每个 buildSlides[i](pres, ctx) 必须能独立调用——只往传入的 pres 加一页
// =====================================================================

const { run } = require("./runner");
const { setup } = require("./lib/themes");
const path = require("path");

const NAV = ["指标速览", "重点举措", "展望"];
const TOTAL = 5;

const deckMeta = {
  title: "滁州分公司 · 7月经营简报",
  author: "中国电信滁州分公司",
  theme: "telecom-red",
  totalPages: TOTAL,
  slideMetas: [
    { title: "封面",                 template: "T1-Cover" },
    { title: "指标速览 · 章节扉页",  template: "T2-SectionBreak" },
    { title: "核心KPI",              template: "T14-KPI" },
    { title: "三大重点举措",         template: "T7-3Card" },
    { title: "下一阶段展望",         template: "T16-Summary" },
  ],
};

function pagesSetup(pres) {
  pres.title = deckMeta.title;
  pres.author = deckMeta.author;
  return setup(pres, "telecom-red");
}

// =====================================================================
const buildSlides = [
  // -------- SLIDE 1 — Cover --------
  (pres, ctx) => {
    const { C, F, W, H } = ctx;
    const s = pres.addSlide();
    s.background = { color: C.bg };
    s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: W, h: 0.52, fill: { color: C.brand[500] }, line: { type: "none" } });
    s.addShape(pres.shapes.RECTANGLE, { x: 0, y: H - 0.52, w: W, h: 0.52, fill: { color: C.brand[500] }, line: { type: "none" } });
    s.addShape(pres.shapes.RECTANGLE, { x: W / 2 - 1.5, y: 3.35, w: 3, h: 0.06, fill: { color: C.accent }, line: { type: "none" } });
    s.addText("7月经营简报", {
      x: 0.5, y: 2.2, w: W - 1, h: 1.0,
      fontFace: F.cn, fontSize: 40, bold: true, color: C.brand[500],
      align: "center", valign: "middle", margin: 0,
    });
    s.addText("存量经营 · 主动进攻 · 守土有责", {
      x: 0.5, y: 3.5, w: W - 1, h: 0.5,
      fontFace: F.cn, fontSize: 16, italic: true, color: C.muted,
      align: "center", valign: "middle", margin: 0,
    });
    s.addText("中国电信滁州分公司  ·  客户经营中心  ·  2026年7月", {
      x: 0.5, y: 5.2, w: W - 1, h: 0.4,
      fontFace: F.cn, fontSize: 13, color: C.text,
      align: "center", valign: "middle", margin: 0,
    });
  },

  // -------- SLIDE 2 — Section Break --------
  (pres, ctx) => {
    const { C, F, W, H, addTelecomFooter } = ctx;
    const s = pres.addSlide();
    s.background = { color: C.bg };
    s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: W, h: 0.52, fill: { color: C.brand[500] }, line: { type: "none" } });
    addTelecomFooter(s, "—", TOTAL);
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.4, y: 1.5, w: W - 0.8, h: 4.8,
      fill: { color: C.brand[500] }, line: { type: "none" },
      shadow: { type: "outer", color: "000000", blur: 18, offset: 4, angle: 90, opacity: 0.18 },
    });
    s.addText("01", {
      x: 1.2, y: 1.9, w: 3, h: 1.6,
      fontFace: F.en, fontSize: 96, bold: true, color: C.accentLight, valign: "middle", margin: 0,
    });
    s.addShape(pres.shapes.RECTANGLE, { x: 1.2, y: 3.65, w: 1.0, h: 0.05, fill: { color: C.accentLight }, line: { type: "none" } });
    s.addText("指标速览", {
      x: 1.2, y: 3.8, w: W - 2.4, h: 0.9,
      fontFace: F.cn, fontSize: 32, bold: true, color: C.white, valign: "middle", margin: 0,
    });
    s.addText("核心指标完成情况速览", {
      x: 1.2, y: 4.8, w: W - 2.4, h: 0.5,
      fontFace: F.cn, fontSize: 14, italic: true, color: C.accentLight, valign: "middle", margin: 0,
    });
  },

  // -------- SLIDE 3 — KPI --------
  (pres, ctx) => {
    const { C, F, W, H, addTelecomNav, addTelecomFooter, addTitle, makeShadow } = ctx;
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTelecomNav(s, 0, NAV);
    addTitle(s, "核心KPI · 7月完成", "环比上月同期");
    addTelecomFooter(s, 3, TOTAL);

    const metrics = [
      { value: "+18", unit: "%",  label: "收入增幅",   sub: "全省第3",     color: C.brand[500] },
      { value: "92",  unit: "分", label: "保有NPS",    sub: "环比+4",      color: C.accent  },
      { value: "76",  unit: "%",  label: "续约率",     sub: "超目标",      color: C.brand[500] },
      { value: "100", unit: "%",  label: "派单闭环",   sub: "连续3月达成", color: C.accent  },
    ];
    const n = metrics.length;
    const cardH = 2.6, cardW = (W - 0.8 - (n - 1) * 0.3) / n, cardY = 2.4;
    metrics.forEach((m, i) => {
      const x = 0.4 + i * (cardW + 0.3);
      s.addShape(pres.shapes.RECTANGLE, { x, y: cardY, w: cardW, h: cardH, fill: { color: C.iceLight }, line: { color: C.border, width: 0.5 }, shadow: makeShadow() });
      s.addShape(pres.shapes.RECTANGLE, { x, y: cardY, w: cardW, h: 0.14, fill: { color: m.color }, line: { type: "none" } });
      s.addText(m.value, { x: x + 0.2, y: cardY + 0.35, w: cardW - 0.4, h: 1.05, fontFace: F.en, fontSize: 56, bold: true, color: m.color, align: "center", valign: "middle", margin: 0 });
      s.addText(m.unit,  { x: x + 0.2, y: cardY + 1.35, w: cardW - 0.4, h: 0.3,  fontFace: F.cn, fontSize: 14, bold: true, color: C.muted, align: "center", valign: "middle", margin: 0 });
      s.addText(m.label, { x: x + 0.2, y: cardY + 1.7,  w: cardW - 0.4, h: 0.4,  fontFace: F.cn, fontSize: 14, bold: true, color: C.text,  align: "center", valign: "middle", margin: 0 });
      s.addText(m.sub,   { x: x + 0.2, y: cardY + 2.1,  w: cardW - 0.4, h: 0.35, fontFace: F.cn, fontSize: 11, italic: true, color: C.muted, align: "center", valign: "middle", margin: 0 });
    });
    s.addText("实现存量营收正增长，主动进攻打法见效。", {
      x: 0.6, y: 5.4, w: W - 1.2, h: 1.0,
      fontFace: F.cn, fontSize: 13, italic: true, color: C.textLight,
      align: "center", valign: "middle", margin: 0,
    });
  },

  // -------- SLIDE 4 — 三大举措 --------
  (pres, ctx) => {
    const { C, F, W, H, addTelecomNav, addTelecomFooter, addTitle, makeShadow } = ctx;
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTelecomNav(s, 1, NAV);
    addTitle(s, "三大重点举措", "存量经营攻坚打法");
    addTelecomFooter(s, 4, TOTAL);

    const cards = [
      { title: "到期续约", desc: "责任体系双轮驱动\n一单一闭环\n续约率 76%", num: "76%" },
      { title: "权益续约", desc: "权益替代+流量扩容\n高券值降档兜底\n低券值以替促升", num: "+5%" },
      { title: "异动预警", desc: "主动预警看住\n被动处置把紧\n有单必接触", num: "100%" },
    ];
    const n = cards.length;
    const cardW = (W - 0.8 - (n - 1) * 0.3) / n, cardY = 2.0, cardH = 4.4;
    cards.forEach((c, i) => {
      const x = 0.4 + i * (cardW + 0.3);
      s.addShape(pres.shapes.RECTANGLE, { x, y: cardY, w: cardW, h: cardH, fill: { color: C.iceLight }, line: { color: C.border, width: 0.5 }, shadow: makeShadow() });
      s.addShape(pres.shapes.RECTANGLE, { x, y: cardY, w: cardW, h: 0.55, fill: { color: C.brand[500] }, line: { type: "none" } });
      s.addText(c.title, { x: x + 0.2, y: cardY, w: cardW - 0.4, h: 0.55, fontFace: F.cn, fontSize: 15, bold: true, color: C.white, valign: "middle", margin: 0 });
      s.addText(c.num, { x: x + 0.2, y: cardY + 0.75, w: cardW - 0.4, h: 0.9, fontFace: F.en, fontSize: 42, bold: true, color: C.brand[500], align: "center", valign: "middle", margin: 0 });
      s.addText(c.desc, { x: x + 0.3, y: cardY + 1.8, w: cardW - 0.6, h: 2.4, fontFace: F.cn, fontSize: 12, color: C.text, align: "center", valign: "top", margin: 0 });
    });
  },

  // -------- SLIDE 5 — Summary --------
  (pres, ctx) => {
    const { C, F, W, H, addTelecomNav, addTelecomFooter, addTitle, makeShadow } = ctx;
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTelecomNav(s,  2, NAV);
    addTitle(s, "下一阶段展望", "持续主动进攻");
    addTelecomFooter(s, 5, TOTAL);

    const points = [
      { num: "01", title: "强化责任体系", desc: "到期续约责任到人，逐单跟进闭环" },
      { num: "02", title: "深化权益运营", desc: "权益替代+流量扩容 = 提值" },
      { num: "03", title: "守住异动底线", desc: "主动预警看住，被动处置把紧" },
    ];
    const cardW = (W - 0.8 - 2 * 0.3) / 3, cardY = 2.2, cardH = 3.8;
    points.forEach((p, i) => {
      const x = 0.4 + i * (cardW + 0.3);
      s.addShape(pres.shapes.RECTANGLE, { x, y: cardY, w: cardW, h: cardH, fill: { color: C.white }, line: { color: C.border, width: 0.5 }, shadow: makeShadow() });
      s.addShape(pres.shapes.RECTANGLE, { x, y: cardY, w: 0.12, h: cardH, fill: { color: C.brand[500] }, line: { type: "none" } });
      s.addText(p.num,   { x: x + 0.35, y: cardY + 0.4,  w: cardW - 0.6, h: 0.8,  fontFace: F.en, fontSize: 40, bold: true, color: C.accent,  valign: "middle", margin: 0 });
      s.addText(p.title, { x: x + 0.35, y: cardY + 1.3,  w: cardW - 0.6, h: 0.5,  fontFace: F.cn, fontSize: 18, bold: true, color: C.brand[500], valign: "middle", margin: 0 });
      s.addText(p.desc,  { x: x + 0.35, y: cardY + 1.95, w: cardW - 0.6, h: 1.5,  fontFace: F.cn, fontSize: 13, color: C.text, valign: "top", margin: 0 });
    });
    // 底部结论条
    s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 6.3, w: W - 0.8, h: 0.5, fill: { color: C.brand[500] }, line: { type: "none" } });
    s.addText("主动进攻就是防守 · 到期续约+责任体系双轮驱动 · 破解融合大进大出", {
      x: 0.4, y: 6.3, w: W - 0.8, h: 0.5,
      fontFace: F.cn, fontSize: 13, bold: true, color: C.white,
      align: "center", valign: "middle", margin: 0,
    });
  },
];

module.exports = { deckMeta, setup: pagesSetup, buildSlides };

if (require.main === module) {
  run({ pages: module.exports, outputPath: path.join(__dirname, "demo_电信红预览.pptx") })
    .then((r) => {
      console.log("\n[gen_demo] 全部完成:", r);
      // 给 SSE 一点时间把 deck_done 推送到浏览器
      setTimeout(() => process.exit(0), 1500);
    })
    .catch((e) => {
      console.error("\n[gen_demo] 失败:", e);
      process.exit(1);
    });
}
