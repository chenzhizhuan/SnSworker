// =====================================================================
// TELECOM-PPT-MASTER BOILERPLATE — 通用多主题启动模板
// 复制此文件到项目中，重命名，填充 TODO 标记的块
//
// 使用:
//   $env:NODE_PATH = (npm root -g)   # Windows PowerShell
//   node gen_main.js
// =====================================================================

const pptxgen = require("pptxgenjs");
const path = require("path");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";  // 13.333 x 7.5 英寸 — 不要改

// >>> TODO 1: Deck 元数据
pres.title  = "My Presentation Title";
pres.author = "Your Name";

const W = 13.333, H = 7.5;
const TOTAL_PAGES = 1;        // >>> TODO 2: 总页数（用于页脚）
const SECTION_NAME = "";      // 如 "Introduction" — 出现在页脚右侧
const NAV_ITEMS = [];         // 如 ["简介", "方法", "结果", "结论"]; [] 表示无导航
const NAV_ACTIVE = -1;        // NAV_ITEMS 索引; -1 = 不突出显示
const FIG_DIR = path.join(__dirname, "figures");
const DECK_TITLE_BAR = pres.title;

// =====================================================================
// >>> TODO 3: THEME — 从 references/themes.md 粘贴一个主题
// =====================================================================
const C = {
  primary:      "A02123",
  primaryDark:  "7A1A1A",
  primaryLight: "B53338",
  accent:       "B89860",
  accentLight:  "D4B87A",
  accentPale:   "F4E8D0",
  contrast:     "2C2C2C",
  contrastLight:"4A4A4A",
  contrastPale: "F0F0F0",
  white:        "FFFFFF",
  bg:           "FFFFFF",
  ice:          "FFFFFF",
  iceLight:     "FAFAFA",
  iceMid:       "E0E0E0",
  border:       "D5D5D5",
  text:         "1A1A1A",
  textLight:    "4A4A4A",
  muted:        "707070",
};
C.navy = C.primary; C.navyDark = C.primaryDark; C.navyLight = C.primaryLight;
C.gold = C.accent; C.goldLight = C.accentLight; C.goldPale = C.accentPale;
C.coral = C.contrast; C.coralLight = C.contrastLight; C.coralPale = C.contrastPale;

const F = { cn: "Microsoft YaHei", en: "Calibri" };

// =====================================================================
// CORE HELPERS — 不要修改，除非你知道自己在做什么
// =====================================================================

function makeShadow() {
  return { type: "outer", color: "000000", blur: 8, offset: 2, angle: 90, opacity: 0.08 };
}

function addNav(slide, active) {
  if (NAV_ITEMS.length === 0) {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0, w: W, h: 0.5,
      fill: { color: C.primary }, line: { type: "none" },
    });
    slide.addText(DECK_TITLE_BAR, {
      x: 0.4, y: 0.05, w: W - 0.8, h: 0.4,
      fontFace: F.cn, fontSize: 12,
      color: C.white, align: "left", valign: "middle", margin: 0,
    });
    return;
  }
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: W, h: 0.5,
    fill: { color: C.primary }, line: { type: "none" },
  });
  slide.addText(DECK_TITLE_BAR, {
    x: 0.4, y: 0.05, w: 6.5, h: 0.4,
    fontFace: F.cn, fontSize: 12,
    color: C.white, align: "left", valign: "middle", margin: 0,
  });
  const itemW = 1.2;
  const startX = W - NAV_ITEMS.length * itemW - 0.3;
  NAV_ITEMS.forEach((item, idx) => {
    const isActive = idx === active;
    slide.addText(item, {
      x: startX + idx * itemW, y: 0.05, w: itemW, h: 0.4,
      fontFace: F.cn, fontSize: 12,
      color: isActive ? C.accentLight : C.white,
      bold: isActive,
      align: "center", valign: "middle", margin: 0,
    });
    if (isActive) {
      slide.addShape(pres.shapes.RECTANGLE, {
        x: startX + idx * itemW + 0.25, y: 0.42, w: itemW - 0.5, h: 0.04,
        fill: { color: C.accentLight }, line: { type: "none" },
      });
    }
  });
}

function addTitle(slide, title, sub) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 0.85, w: 0.12, h: 0.65,
    fill: { color: C.accent }, line: { type: "none" },
  });
  slide.addText(title, {
    x: 0.65, y: 0.78, w: 11.5, h: 0.55,
    fontFace: F.cn, fontSize: 26, bold: true,
    color: C.primary, align: "left", valign: "middle", margin: 0,
  });
  if (sub) {
    slide.addText(sub, {
      x: 0.65, y: 1.32, w: 11.5, h: 0.32,
      fontFace: F.cn, fontSize: 12,
      color: C.muted, align: "left", valign: "middle", margin: 0,
    });
  }
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.7, w: W - 0.8, h: 0.02,
    fill: { color: C.border }, line: { type: "none" },
  });
}

function addFooter(slide, pageNum) {
  slide.addText(`${pres.author}  ·  ${SECTION_NAME || pres.title}`, {
    x: 0.4, y: H - 0.4, w: 6, h: 0.3,
    fontFace: F.cn, fontSize: 12,
    color: C.muted, align: "left", valign: "middle", margin: 0,
  });
  const right = (pageNum === "—" || pageNum == null)
    ? "—"
    : `${SECTION_NAME ? SECTION_NAME + "  ·  " : ""}${pageNum} / ${TOTAL_PAGES}`;
  slide.addText(right, {
    x: W - 4.4, y: H - 0.4, w: 4, h: 0.3,
    fontFace: F.cn, fontSize: 12,
    color: C.muted, align: "right", valign: "middle", margin: 0,
  });
}

// =====================================================================
// >>> TODO 4: SLIDES — 从 references/page-templates.md 粘贴模板
// =====================================================================

// 示例第 1 页 — 替换为你的实际内容
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addNav(s, NAV_ACTIVE);
  addTitle(s, "My First Slide", "subtitle / english version");
  addFooter(s, 1);

  s.addText("Replace this with your slide content.", {
    x: 0.4, y: 3.5, w: W - 0.8, h: 0.5,
    fontFace: F.cn, fontSize: 16,
    color: C.muted, align: "center", valign: "middle", margin: 0,
  });
}

// =====================================================================
// SAVE — 不要修改
// =====================================================================
const outDir = path.join(__dirname, "output");
require("fs").mkdirSync(outDir, { recursive: true });
const outPath = path.join(outDir, "deck.pptx");

pres.writeFile({ fileName: outPath })
  .then(name => console.log("DONE:", name))
  .catch(err => { console.error("ERR:", err); process.exit(1); });
