// =====================================================================
// TELECOM-PPT-MASTER TELECOM BOILERPLATE — 中国电信风格专用
// v8.0 升级：融合 open-design 设计 token 体系
// 基于1764份电信PPT统计分析 + nexu-io/open-design (81.4K stars) 设计方法论
//
// 使用:
//   $env:NODE_PATH = (npm root -g)   # Windows PowerShell
//   node gen_main.js
// =====================================================================

const pptxgen = require("pptxgenjs");
const path = require("path");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";  // 13.333 x 7.5 英寸

// >>> TODO 1: Deck 元数据
pres.title  = "中国电信标准化运营";
pres.author = "中国电信";

const W = 13.333, H = 7.5;
const TOTAL_PAGES = 1;        // >>> TODO 2: 总页数
const SECTION_NAME = "";      // 如 "运营分析"
const NAV_ITEMS = [];         // 如 ["指标分析", "问题诊断", "工作部署"]
let NAV_ACTIVE = -1;
const FIG_DIR = path.join(__dirname, "figures");
const DECK_TITLE_BAR = pres.title;

// =====================================================================
// THEME: telecom-red（中国电信深红配色体系 · v8.0 Token 化）
// 权威来源: references/design-system.md + references/themes.md
// =====================================================================
const C = {
  // Brand — 电信深红 10 级色阶
  brand: {
    "50":"FFF5F5", "100":"FFE4E4", "200":"F4C2C2", "300":"E8A0A0",
    "400":"D06060", "500":"C00000", "600":"A8001A", "700":"8B0012",
    "800":"6E000A", "900":"4D0004"
  },
  // Accent — 金色 10 级色阶
  accent: {
    "50":"FFFCE0", "100":"FFF8B0", "200":"FFF070", "300":"FFE830",
    "400":"FFD700", "500":"E0C200", "600":"C0A800", "700":"A09000",
    "800":"807000", "900":"605000"
  },
  // Neutral — 统一灰度色阶
  neutral: {
    "50":"FAFAFA", "100":"F5F5F5", "200":"E8E8E8", "300":"D4D4D4",
    "400":"A3A3A3", "500":"888888", "600":"666666", "700":"404040",
    "800":"262626", "900":"171717"
  },
  // Semantic 语义色
  surface:        "FFFFFF",
  surfaceRaised:  "FFFFFF",
  surfaceHeader:  "FFE4E4",     // brand[100]
  surfaceBrand:   "C00000",     // brand[500]
  border:         "E8B4B4",
  borderLight:    "F4C2C2",
  // Text
  textPrimary:    "262626",     // neutral[800] 替代纯黑
  textSecondary:  "888888",     // neutral[500]
  textInverse:    "FFFFFF",
  // 电信特有语义色
  highlight:      "FFFF00",
  warning:        "FF0000",
  // 高程阴影
  elevation: {
    card:      { type:"outer", color:"000000", blur:4,  offset:1,  angle:270, opacity:0.06 },
    overlay:   { type:"outer", color:"000000", blur:8,  offset:2,  angle:270, opacity:0.10 },
    prominent: { type:"outer", color:"000000", blur:12, offset:3,  angle:270, opacity:0.14 },
  },
};

// === 向后兼容别名 ===
C.primary = C.brand[500]; C.primaryDark = C.brand[600]; C.primaryLight = C.brand[400];
C.accentHex = C.accent[400]; C.accentLightHex = C.accent[100]; C.accentPaleHex = C.accent[50];
C.contrast = C.neutral[700]; C.contrastLight = C.neutral[600]; C.contrastPale = C.neutral[100];
C.white = C.surface; C.bg = C.surface; C.ice = C.surface;
C.iceLight = C.brand[100]; C.iceMid = C.surfaceHeader;
C.text = C.neutral[800]; C.textLight = C.neutral[700]; C.muted = C.neutral[500];
C.navy = C.primary; C.navyDark = C.primaryDark; C.navyLight = C.primaryLight;
C.gold = C.accent[400]; C.goldLight = C.accent[100]; C.goldPale = C.accent[50];
C.coral = C.contrast; C.coralLight = C.contrastLight; C.coralPale = C.contrastPale;

const F = { cn: "Microsoft YaHei", en: "Calibri", display: "Microsoft YaHei", number: "Arial", serif: "SimSun" };

// =====================================================================
// 电信风格 HELPERS
// =====================================================================

// 红金渐变装饰线
function addTelecomTitleLine(slide, y) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: y, w: 6.0, h: 0.04,
    fill: { color: C.primary }, line: { type: "none" },
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.4, y: y, w: 2.5, h: 0.04,
    fill: { color: C.accent }, line: { type: "none" },
  });
}

// 电信风格阴影（比通用版更轻）
function makeTelecomShadow() {
  return { type: "outer", color: "000000", blur: 5, offset: 1.5, angle: 270, opacity: 0.08 };
}

// 通用兼容 alias
function makeShadow() {
  return makeTelecomShadow();
}

// 数字目标格式化（红色加粗 + 可选黄色底色）
function fmtNumber(text, withBg) {
  if (withBg) {
    return { text: "  " + text + "  ", options: { bold: true, color: C.primary, highlight: C.highlight, fontSize: 13 } };
  }
  return { text: text, options: { bold: true, color: C.primary, fontSize: 13 } };
}

// =====================================================================
// 电信风格：顶部深红通栏导航（y=0~0.52"）
// =====================================================================
function addNav(slide, active) {
  // 深红通栏
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: W, h: 0.52,
    fill: { color: C.primary }, line: { type: "none" },
  });
  // 红金渐变底线
  addTelecomTitleLine(slide, 0.48);

  if (NAV_ITEMS.length === 0) {
    slide.addText(DECK_TITLE_BAR, {
      x: 0.4, y: 0.05, w: W - 0.8, h: 0.45,
      fontFace: F.cn, fontSize: 14, bold: true,
      color: C.white, align: "left", valign: "middle", margin: 0,
    });
    return;
  }
  // 左侧标题
  slide.addText(DECK_TITLE_BAR, {
    x: 0.4, y: 0.05, w: 6.5, h: 0.45,
    fontFace: F.cn, fontSize: 14, bold: true,
    color: C.white, align: "left", valign: "middle", margin: 0,
  });
  // 右侧导航项
  const itemW = 1.2;
  const startX = W - NAV_ITEMS.length * itemW - 0.3;
  NAV_ITEMS.forEach((item, idx) => {
    const isActive = idx === active;
    slide.addText(item, {
      x: startX + idx * itemW, y: 0.05, w: itemW, h: 0.45,
      fontFace: F.cn, fontSize: 12,
      color: isActive ? C.accent : C.white,
      bold: isActive,
      align: "center", valign: "middle", margin: 0,
    });
    if (isActive) {
      slide.addShape(pres.shapes.RECTANGLE, {
        x: startX + idx * itemW + 0.25, y: 0.44, w: itemW - 0.5, h: 0.04,
        fill: { color: C.accent }, line: { type: "none" },
      });
    }
  });
}

// =====================================================================
// 电信风格：页面标题区（红色竖条 + 红金渐变线）（y=0.55~1.7"）
// =====================================================================
function addTitle(slide, title, sub) {
  // 红色竖条装饰
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 0.65, w: 0.12, h: 0.6,
    fill: { color: C.primary }, line: { type: "none" },
  });
  // 主标题 — 深红色 Bold
  slide.addText(title, {
    x: 0.65, y: 0.60, w: 11.5, h: 0.5,
    fontFace: F.cn, fontSize: 22, bold: true,
    color: C.primary, align: "left", valign: "middle", margin: 0,
  });
  // 副标题
  if (sub) {
    slide.addText(sub, {
      x: 0.65, y: 1.10, w: 11.5, h: 0.3,
      fontFace: F.cn, fontSize: 12,
      color: C.muted, align: "left", valign: "middle", margin: 0,
    });
  }
  // 红金渐变分割线
  addTelecomTitleLine(slide, 1.55);
}

// =====================================================================
// 电信风格：底部红色横幅页脚（y=7.08~7.50"）
// =====================================================================
function addFooter(slide, pageNum) {
  // 底部横幅
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: H - 0.45, w: W, h: 0.45,
    fill: { color: C.primary }, line: { type: "none" },
  });
  // 红金渐变上线
  addTelecomTitleLine(slide, H - 0.48);
  // 左侧
  slide.addText(`${pres.author}  ·  ${SECTION_NAME || pres.title}`, {
    x: 0.4, y: H - 0.4, w: 6, h: 0.3,
    fontFace: F.cn, fontSize: 10,
    color: C.white, align: "left", valign: "middle", margin: 0,
  });
  // 右侧页码
  const right = (pageNum === "—" || pageNum == null)
    ? "—"
    : `${SECTION_NAME ? SECTION_NAME + "  ·  " : ""}${pageNum} / ${TOTAL_PAGES}`;
  slide.addText(right, {
    x: W - 4.4, y: H - 0.4, w: 4, h: 0.3,
    fontFace: F.cn, fontSize: 10,
    color: C.white, align: "right", valign: "middle", margin: 0,
  });
}

// =====================================================================
// 电信风格：卡片构建 helper
// =====================================================================
function drawTelecomCard(slide, x, y, w, h, { header, headerColor, bodyFn }) {
  // 卡片外框
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h,
    fill: { color: C.white }, line: { color: C.border, width: 1.2 },
    shadow: makeTelecomShadow(),
    rectRadius: 0.1,
  });
  // 标题栏
  if (header) {
    slide.addShape(pres.shapes.RECTANGLE, {
      x, y, w, h: 0.45,
      fill: { color: headerColor || C.iceMid }, line: { type: "none" },
      rectRadius: 0.1,
    });
    // 底部覆盖直角
    slide.addShape(pres.shapes.RECTANGLE, {
      x, y: y + 0.35, w, h: 0.1,
      fill: { color: headerColor || C.iceMid }, line: { type: "none" },
    });
    slide.addText(header, {
      x: x + 0.15, y, w: w - 0.3, h: 0.45,
      fontFace: F.cn, fontSize: 14, bold: true,
      color: C.primary, align: "center", valign: "middle", margin: 0,
    });
  }
  // 调用自定义内容
  if (bodyFn) bodyFn(slide, x, y + (header ? 0.45 : 0), w, h - (header ? 0.45 : 0));
}

// =====================================================================
// v7.0 新增：高管座谈会（executive-blue）风格 HELPERS
// 当使用 executive-blue 主题（座谈会/半年会场景）时，替换上面的 telecom-red 函数
// 使用方式：将 C 对象替换为 executive-blue 配色后，调用以下函数
// =====================================================================

// --- executive-blue 配色（座谈会场景使用时取消注释替换 C 对象） ---
// const C_exec = {
//   primary: "0070C0", primaryDark: "0055B8", primaryLight: "5090D0",
//   accent: "C00000", accentLight: "D6001F", accentPale: "FDE8E8",
//   contrast: "333333", contrastLight: "555555", contrastPale: "F0F0F0",
//   white: "FFFFFF", bg: "FFFFFF", ice: "FFFFFF",
//   iceLight: "F5F9FC", iceMid: "E8F0F8", border: "D0D8E0",
//   text: "000000", textLight: "333333", muted: "888888",
//   highlight: "FFFF00", warning: "C00000",
//   positive: "70B040", gold: "FFD700", brandRed: "D6001F",
// };

// 座谈会风格：模块进度标签导航（蓝色标签 + 页面标题 + 品牌Logo）
function addExecutiveNav(slide, moduleLabel, moduleName, brandLogo) {
  // 蓝色通栏导航栏
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: W, h: 0.50,
    fill: { color: C.primary }, line: { type: "none" },
  });
  // 左侧：蓝色模块进度标签（如"总体收入（1/5）"）
  if (moduleLabel) {
    slide.addText(moduleLabel, {
      x: 0.3, y: 0.05, w: 3.5, h: 0.40,
      fontFace: F.cn, fontSize: 12, bold: true,
      color: C.white, align: "left", valign: "middle", margin: 0,
    });
  }
  // 中间：页面标题
  if (moduleName) {
    slide.addText(moduleName, {
      x: 4.0, y: 0.05, w: 6.0, h: 0.40,
      fontFace: F.cn, fontSize: 13, bold: true,
      color: C.white, align: "center", valign: "middle", margin: 0,
    });
  }
  // 右侧：品牌标识（如"天翼AI"）
  if (brandLogo) {
    slide.addText(brandLogo, {
      x: W - 2.5, y: 0.05, w: 2.2, h: 0.40,
      fontFace: F.cn, fontSize: 11,
      color: C.white, align: "right", valign: "middle", margin: 0,
    });
  }
}

// 座谈会风格：底部浅灰页脚（非红色横幅）
function addExecutiveFooter(slide, pageNum) {
  // 底部浅灰横线
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: H - 0.38, w: W, h: 0.02,
    fill: { color: C.border }, line: { type: "none" },
  });
  // 左侧单位+章节
  slide.addText(`${pres.author}  ·  ${SECTION_NAME || pres.title}`, {
    x: 0.4, y: H - 0.33, w: 6, h: 0.28,
    fontFace: F.cn, fontSize: 9,
    color: C.muted, align: "left", valign: "middle", margin: 0,
  });
  // 右侧页码
  const right = (pageNum === "—" || pageNum == null)
    ? "—"
    : `${SECTION_NAME ? SECTION_NAME + "  ·  " : ""}${pageNum} / ${TOTAL_PAGES}`;
  slide.addText(right, {
    x: W - 4.0, y: H - 0.33, w: 3.6, h: 0.28,
    fontFace: F.cn, fontSize: 9,
    color: C.muted, align: "right", valign: "middle", margin: 0,
  });
}

// 座谈会风格：结论先行标题区（蓝色竖条 + 蓝色标题 + 结论条）
function addExecutiveTitle(slide, title, conclusionBar) {
  // 蓝色竖条装饰
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 0.62, w: 0.12, h: 0.55,
    fill: { color: C.primary }, line: { type: "none" },
  });
  // 主标题 — 蓝色 Bold
  slide.addText(title, {
    x: 0.65, y: 0.58, w: 11.5, h: 0.45,
    fontFace: F.cn, fontSize: 20, bold: true,
    color: C.primary, align: "left", valign: "middle", margin: 0,
  });
  // 蓝色细分隔线
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.18, w: W - 0.8, h: 0.02,
    fill: { color: C.primary }, line: { type: "none" },
  });
  // 结论条（蓝色底白字，2-3行核心判断）
  if (conclusionBar) {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.4, y: 1.30, w: W - 0.8, h: 0.55,
      fill: { color: C.primary }, line: { type: "none" },
      rectRadius: 0.05,
    });
    slide.addText(conclusionBar, {
      x: 0.6, y: 1.30, w: W - 1.2, h: 0.55,
      fontFace: F.cn, fontSize: 12, bold: true,
      color: C.white, align: "left", valign: "middle", margin: [0, 6, 0, 6],
    });
  }
}

// 座谈会风格：正负双色数字格式化
function fmtExecutiveNumber(text, isPositive) {
  var color = isPositive ? (C.positive || "70B040") : (C.accent || "C00000");
  return { text: text, options: { bold: true, color: color, fontSize: 13 } };
}

// 座谈会风格：圆形指标卡
function drawExecutiveKPI(slide, x, y, w, h, opts) {
  opts = opts || {};
  slide.addShape(pres.shapes.RECTANGLE, {
    x: x, y: y, w: w, h: h,
    fill: { color: C.white }, line: { color: C.border, width: 1 },
    shadow: makeTelecomShadow(), rectRadius: 0.08,
  });
  // 标签
  if (opts.label) {
    slide.addText(opts.label, {
      x: x + 0.1, y: y + 0.08, w: w - 0.2, h: 0.3,
      fontFace: F.cn, fontSize: 10,
      color: C.muted, align: "center", valign: "middle", margin: 0,
    });
  }
  // 数值
  if (opts.value) {
    slide.addText(opts.value, {
      x: x + 0.1, y: y + 0.35, w: w - 0.2, h: 0.5,
      fontFace: F.cn, fontSize: 24, bold: true,
      color: C.primary, align: "center", valign: "middle", margin: 0,
    });
  }
  // 单位
  if (opts.unit) {
    slide.addText(opts.unit, {
      x: x + 0.1, y: y + 0.80, w: w - 0.2, h: 0.25,
      fontFace: F.cn, fontSize: 9,
      color: C.muted, align: "center", valign: "middle", margin: 0,
    });
  }
  // 变化（正绿负红）
  if (opts.change) {
    slide.addText(opts.change, {
      x: x + 0.1, y: y + h - 0.30, w: w - 0.2, h: 0.25,
      fontFace: F.cn, fontSize: 11, bold: true,
      color: opts.isPositive ? (C.positive || "70B040") : (C.accent || "C00000"),
      align: "center", valign: "middle", margin: 0,
    });
  }
}

// 座谈会风格：卡片构建（白底浅灰描边，非粉色填充）
function drawExecutiveCard(slide, x, y, w, h, opts) {
  opts = opts || {};
  slide.addShape(pres.shapes.RECTANGLE, {
    x: x, y: y, w: w, h: h,
    fill: { color: C.white }, line: { color: C.border, width: 1.2 },
    shadow: makeTelecomShadow(), rectRadius: 0.08,
  });
  if (opts.header) {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: w, h: 0.40,
      fill: { color: opts.headerColor || C.iceMid }, line: { type: "none" },
      rectRadius: 0.08,
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y + 0.30, w: w, h: 0.10,
      fill: { color: opts.headerColor || C.iceMid }, line: { type: "none" },
    });
    slide.addText(opts.header, {
      x: x + 0.12, y: y, w: w - 0.24, h: 0.40,
      fontFace: F.cn, fontSize: 13, bold: true,
      color: C.primary, align: "center", valign: "middle", margin: 0,
    });
  }
  if (opts.bodyFn) {
    opts.bodyFn(slide, x, y + (opts.header ? 0.40 : 0), w, h - (opts.header ? 0.40 : 0));
  }
}

// =====================================================================
// >>> TODO 4: SLIDES — 从 references/page-templates.md 粘贴模板
// 模板中的 addNav / addTitle / addFooter / makeShadow 已自动使用电信风格版本
// =====================================================================

// 示例第 1 页
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addNav(s, NAV_ACTIVE);
  addTitle(s, "示例标题", "示例副标题 / Example Subtitle");
  addFooter(s, 1);

  s.addText("替换为实际内容（使用 T1-T16 模板）", {
    x: 0.4, y: 2.5, w: W - 0.8, h: 0.5,
    fontFace: F.cn, fontSize: 16,
    color: C.muted, align: "center", valign: "middle", margin: 0,
  });
}

// =====================================================================
// SAVE
// =====================================================================
const outDir = path.join(__dirname, "output");
require("fs").mkdirSync(outDir, { recursive: true });
const outPath = path.join(outDir, "deck.pptx");

pres.writeFile({ fileName: outPath })
  .then(name => console.log("DONE:", name))
  .catch(err => { console.error("ERR:", err); process.exit(1); });
