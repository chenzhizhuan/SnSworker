// gen_ai_tourism_full.js - AI+文旅主题PPT（9页完整版）
const pptxgen = require("pptxgenjs");
const path = require("path");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "China Telecom";
pres.title = "AI+文旅";

// ===== 配色方案 =====
const C = {
  primary: "C8102E",       // 电信品牌红（主色）
  redBright: "E60012",     // 亮红
  redDark: "8B0000",       // 深红
  blue: "0066CC",          // 蓝色
  blueDark: "005AAA",      // 品牌蓝
  blueBg: "E8F0FE",        // 浅蓝背景
  blueCard: "EDF4FD",      // 浅蓝卡片
  text: "000000",          // 正文黑
  textGray: "666666",      // 次要灰
  textLight: "999999",     // 浅灰
  borderLight: "E5E5E5",   // 浅灰边框
  white: "FFFFFF",
  fillGray: "F5F5F5",
  green: "4CAF50",
  greenBg: "E8F5E9",
  greenCard: "E8F8E8",
  yellow: "FFC107",
  yellowBg: "FFFDE7",
  yellowCard: "FFF8E1",
  purple: "9C27B0",
  purpleBg: "F3E5F5",
  purpleCard: "F5EEF8",
  cyan: "00BCD4",
  cyanBg: "E0F7FA",
  cyanCard: "E0F5F8",
  orange: "F29400",
  pinkLight: "FCE4EC",
  pinkTag: "FFF0F3",
  redDeep: "A82820",
  teal: "009688",
  tealBg: "E0F2F1",
  gray1: "333333",
  gray2: "555555",
  gray3: "888888",
  gray4: "CCCCCC",
  gray5: "E8E8E8",
  titleBgDark: "2C2C2C",   // 深灰标题栏背景
};

// ===== 辅助函数 =====
function addPageNum(slide, num) {
  slide.addText(String(num), {
    x: 9.3, y: 5.2, w: 0.4, h: 0.25,
    fontSize: 10, fontFace: "Microsoft YaHei", color: C.textLight,
    align: "right", valign: "middle", margin: 0
  });
}

function addBrokenBorder(slide, x, y, w, h, color) {
  var t = 0.014, gap = 0.3, c = color || C.redDeep;
  slide.addShape(pres.shapes.RECTANGLE, { x: x + gap, y: y, w: w - 2 * gap, h: t, fill: { color: c } });
  slide.addShape(pres.shapes.RECTANGLE, { x: x + gap, y: y + h - t, w: w - 2 * gap, h: t, fill: { color: c } });
  slide.addShape(pres.shapes.RECTANGLE, { x: x, y: y + gap, w: t, h: h - 2 * gap, fill: { color: c } });
  slide.addShape(pres.shapes.RECTANGLE, { x: x + w - t, y: y + gap, w: t, h: h - 2 * gap, fill: { color: c } });
}

// 顶部红色装饰条+标题
function addRedBarTitle(slide, title, titleSize) {
  slide.addText(title, {
    x: 0.3, y: 0.15, w: 9.4, h: 0.5,
    fontSize: titleSize || 24, fontFace: "Microsoft YaHei", bold: true,
    color: C.text, align: "center", valign: "middle", margin: 0
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0.7, w: 10, h: 0.035, fill: { color: C.primary }
  });
}

// ========== PAGE 1: 政策东风：AI+文旅 ==========
function page1() {
  const s = pres.addSlide();
  // 标题
  s.addText("政策东风：AI + 文旅，促进数字经济与旅游业深度融合", {
    x: 0.3, y: 0.12, w: 9.4, h: 0.5,
    fontSize: 22, fontFace: "Microsoft YaHei", bold: true,
    color: C.text, align: "center", valign: "middle", margin: 0
  });
  // 红色装饰线
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0.66, w: 10, h: 0.035, fill: { color: C.primary } });

  // 导语段（居中，红色高亮关键词）
  s.addText([
    { text: "国家陆续推出一揽子政策，", options: { fontSize: 11, color: C.text } },
    { text: "促进数字经济和旅游业深度融合", options: { fontSize: 11, color: C.primary, bold: true } },
    { text: "。以新质生产力为引擎，引入AI大模型等新技术，提升旅游服务的智能化和个性化水平，成为促进文旅产业质效提升的重要路径", options: { fontSize: 11, color: C.text } }
  ], { x: 0.8, y: 0.78, w: 8.4, h: 0.55, fontFace: "Microsoft YaHei", align: "center", valign: "middle", margin: 0, wrap: true });

  // 粉色时间线 + 4个红色圆点
  var tlY = 1.5, tlX1 = 1.2, tlX2 = 8.8;
  s.addShape(pres.shapes.RECTANGLE, { x: tlX1, y: tlY, w: tlX2 - tlX1, h: 0.02, fill: { color: "F8BBD0" } });
  var dotXs = [1.95, 4.2, 6.45, 8.7];
  var dotLabels = ["2023.09", "2024.01", "2024.05", "2024.08"];
  for (var i = 0; i < 4; i++) {
    s.addShape(pres.shapes.OVAL, { x: dotXs[i] - 0.06, y: tlY - 0.04, w: 0.14, h: 0.14, fill: { color: C.primary } });
    s.addText(dotLabels[i], { x: dotXs[i] - 0.5, y: tlY - 0.32, w: 1.0, h: 0.22, fontSize: 8, fontFace: "Microsoft YaHei", color: C.textGray, align: "center", valign: "middle", margin: 0 });
  }

  // 4张卡片
  var cardData = [
    {
      title: "习近平强调\u201C加快发展新质生产力，扎实推进高质量发展\u201D",
      body: "新质生产力是创新起主导作用，摆脱传统经济增长方式、生产力发展路径，具有高科技、高效能、高质量特征，符合新发展理念的先进生产力质态。新质生产力以全要素生产率大幅提升为核心标志，特点是创新，关键在质优，本质是先进生产力。",
      conclusion: "新质生产力推动文旅产业高质量发展"
    },
    {
      title: "\u201C数据要素\u00D7\u201D三年行动计划（2024-2026年）",
      body: "《行动计划》中提出\u201C数据要素\u00D7文化旅游\u201D行动，希望充分发挥数据要素的乘数效应，赋能文化和旅游高质量发展，要求\u201C提升旅游服务水平，支持旅游经营主体共享气象、交通等数据，在合法合规前提下构建客群画像、城市画像等，优化旅游配套服务、一站式出行服务\u201D。",
      conclusion: "数据要素\u00D7文化旅游列入12个重点行业和领域"
    },
    {
      title: "智慧旅游创新发展行动计划",
      body: "行动计划中提升服务平台运营效能：鼓励和支持云计算、区块链、大数据、通用人工智能等新技术与智慧旅游线上服务相结合，发展智慧旅游动手类应用。",
      conclusion: "直接支持了AI导游导览产品作为智慧旅游类应用的发展"
    },
    {
      title: "《旅游景区质量等级划分》（GB/T 17775\u20142024）",
      body: "新增文旅融合专项，要求文化展示、非遗活化、创意产品深度落地；智慧旅游成核心指标，覆盖预约、数字导览、客流管控、智能运营全链条。",
      conclusion: "新标准推动景区从传统向智慧全面升级，指引文旅高质量发展"
    }
  ];

  var cardW = 2.15, cardH = 3.0, cardY = 1.75;
  var cardGap = 0.15;
  var startX = (10 - (4 * cardW + 3 * cardGap)) / 2;

  for (var i = 0; i < 4; i++) {
    var cx = startX + i * (cardW + cardGap);
    // 卡片背景（白底圆角，浅灰边框）
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: cx, y: cardY, w: cardW, h: cardH,
      fill: { color: C.white }, line: { color: C.gray4, width: 0.75 },
      rectRadius: 0.06
    });
    // 卡片标题
    s.addText(cardData[i].title, {
      x: cx + 0.12, y: cardY + 0.12, w: cardW - 0.24, h: 0.7,
      fontSize: 9.5, fontFace: "Microsoft YaHei", bold: true,
      color: C.text, align: "left", valign: "top", margin: 0, wrap: true
    });
    // 标题下红色短线
    s.addShape(pres.shapes.RECTANGLE, { x: cx + 0.12, y: cardY + 0.85, w: 0.35, h: 0.02, fill: { color: C.primary } });
    // 卡片正文
    s.addText(cardData[i].body, {
      x: cx + 0.12, y: cardY + 0.95, w: cardW - 0.24, h: 1.45,
      fontSize: 7, fontFace: "Microsoft YaHei", color: C.text,
      align: "left", valign: "top", margin: 2, lineSpacing: 10, wrap: true
    });
    // 卡片底部红色结论
    s.addText(cardData[i].conclusion, {
      x: cx + 0.12, y: cardY + 2.45, w: cardW - 0.24, h: 0.45,
      fontSize: 8, fontFace: "Microsoft YaHei", bold: true,
      color: C.primary, align: "left", valign: "top", margin: 0, wrap: true
    });
  }

  // 底部红色弧形块（用圆角矩形模拟弧形上边缘）
  var bottomY = 4.85;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: -0.5, y: bottomY, w: 11, h: 1.0,
    fill: { color: C.primary }, line: { color: C.primary, width: 0 },
    rectRadius: 0.3
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: -0.5, y: bottomY + 0.3, w: 11, h: 0.7,
    fill: { color: C.primary }
  });
  // 底部白色文字
  s.addText("新质生产力在升级旅游服务体验方面，主要通过科技创新和智慧旅游的手段实现。", {
    x: 1, y: bottomY + 0.15, w: 8, h: 0.6,
    fontSize: 13, fontFace: "Microsoft YaHei", bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0
  });

  addPageNum(s, 1);
}

// ========== PAGE 2: 政策东风：实施意见解读 ==========
function page2() {
  const s = pres.addSlide();
  // 深灰色标题栏
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.7, fill: { color: C.titleBgDark } });
  s.addText("政策东风：\u201C人工智能+文化和旅游\u201D 实施意见解读", {
    x: 0.3, y: 0, w: 9.4, h: 0.7,
    fontSize: 20, fontFace: "Microsoft YaHei", bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0
  });
  // 红色分隔线
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0.7, w: 10, h: 0.03, fill: { color: C.primary } });

  // 总目标段（红色高亮关键词）
  s.addText([
    { text: "到2027年底，", options: { fontSize: 11, color: C.text } },
    { text: "建成一批高质量数据集", options: { fontSize: 11, color: C.primary, bold: true } },
    { text: "，初步形成高质量数据供给体系；", options: { fontSize: 11, color: C.text } },
    { text: "推出一批新产品新服务", options: { fontSize: 11, color: C.primary, bold: true } },
    { text: "，积极拓展人工智能应用场景；", options: { fontSize: 11, color: C.text } },
    { text: "部署一批应用试点", options: { fontSize: 11, color: C.primary, bold: true } },
    { text: "，加快构建人工智能应用生态；", options: { fontSize: 11, color: C.text } },
    { text: "研制一批标准规范", options: { fontSize: 11, color: C.primary, bold: true } },
    { text: "，有效提升人工智能应用水平。", options: { fontSize: 11, color: C.text } }
  ], { x: 0.5, y: 0.82, w: 9.0, h: 0.45, fontFace: "Microsoft YaHei", align: "center", valign: "middle", margin: 0, wrap: true });

  // 8个卡片 2行4列
  var cards = [
    { title: "\u2460辅助文化艺术创作生产", items: [
      "提升人工智能技术在音乐、美术、戏曲等领域生成能力",
      "辅助创作更多有中华文化元素和标识的文化内容",
      "探索开展人工智能辅助分析评价"
    ]},
    { title: "\u2461提升公共文化服务水平", items: [
      "动态监测分析公共文化服务供需情况，精准推送优秀文化资源直达基层",
      "运用人工智能技术提供知识问答、讲解引导等创新服务以及智能互动体验项目"
    ]},
    { title: "\u2462助力文化遗产保护传承", items: [
      "加快文物知识图谱建设，构建文物资源大数据库，推动人工智能技术赋能文物价值挖掘与传播，提高文物资源保护利用的智能化水平。"
    ]},
    { title: "\u2463培育文化和旅游新业态", items: [
      "推动人工智能技术与虚拟现实、增强现实等技术融合，构建数字文旅和沉浸式文旅发展业态。"
    ]},
    { title: "\u2464提升旅游服务和治理效能", items: [
      "打造旅游资源精准推荐、行程规划、智能票务预约等创新服务。",
      "提供智能讲解、自动翻译、智能客服等服务。",
      "开展旅游公共信息数据共享整合、挖掘分析、增强客流疏导、突发事件应急处置能力。"
    ]},
    { title: "\u2465加强文化和旅游市场监管", items: [
      "探索行政审批、风险监测预警、服务公众、应急指挥等场景应用",
      "鼓励对重点领域开展现场监管，智能化发现、分析、处置文化和旅游市场违法违规问题线索，优化举报投诉、行政执法业务流程，实现全过程可溯。"
    ]},
    { title: "\u2466加强文化和旅游数据供给", items: [
      "推进文化资源数字化采集，如文物、非物质文化遗产、古籍等",
      "建设行业高质量数据集，如文化创意、旅游、展览展示等，提升数据加工标注能力",
      "加强文化和旅游数据开发利用，鼓励部分地区开展数字资产交易"
    ]},
    { title: "\u2467打造文旅人工智能大模型", items: [
      "增强人工智能通用大模型的文化和旅游服务能力，深化公共数据资源开发利用，加强场景适配",
      "发展文化和旅游垂直大模型，鼓励通过算法改进、数据质量提升、提示词优化等方式不断提高信息检索能力和内容生成质量"
    ]}
  ];

  var cardW = 2.22, cardH = 1.85;
  var gapX = 0.13, gapY = 0.12;
  var startX = (10 - (4 * cardW + 3 * gapX)) / 2;
  var startY = 1.35;

  for (var i = 0; i < 8; i++) {
    var col = i % 4, row = Math.floor(i / 4);
    var cx = startX + col * (cardW + gapX);
    var cy = startY + row * (cardH + gapY);
    // 卡片边框
    s.addShape(pres.shapes.RECTANGLE, {
      x: cx, y: cy, w: cardW, h: cardH,
      fill: { color: C.white }, line: { color: C.gray4, width: 0.75 }
    });
    // 蓝色标题栏
    s.addShape(pres.shapes.RECTANGLE, {
      x: cx, y: cy, w: cardW, h: 0.3,
      fill: { color: C.blueDark }
    });
    s.addText(cards[i].title, {
      x: cx + 0.05, y: cy, w: cardW - 0.1, h: 0.3,
      fontSize: 8.5, fontFace: "Microsoft YaHei", bold: true,
      color: C.white, align: "left", valign: "middle", margin: 0
    });
    // 正文项目符号列表
    var itemY = cy + 0.38;
    for (var j = 0; j < cards[i].items.length; j++) {
      var itemH = (cards[i].items.length <= 1) ? 1.35 : 0.42;
      s.addText("\u2022 " + cards[i].items[j], {
        x: cx + 0.08, y: itemY, w: cardW - 0.16, h: itemH,
        fontSize: 7, fontFace: "Microsoft YaHei", color: C.text,
        align: "left", valign: "top", margin: 2, lineSpacing: 10, wrap: true
      });
      itemY += itemH + 0.02;
    }
  }

  addPageNum(s, 2);
}

// ========== PAGE 3: 技术机遇：从AI集成走向AI原生 ==========
function page3() {
  const s = pres.addSlide();
  addRedBarTitle(s, "技术机遇：为什么我们必须从AI集成 走向 AI 原生？");

  // 左侧55%区域：3个浅红边框卡片
  var leftW = 5.3;
  var cardData = [
    {
      title: "技术演进三阶段：从工具到合伙人",
      items: [
        "通用大模型：全能通用但缺乏深度，难以落地复杂业务。",
        "行业大模型：懂行业术语，但仍需大量二次开发适配。",
        "AI原生智能体：内置知识/流程与长记忆，直接驱动业务闭环。"
      ]
    },
    {
      title: "需求本质变化：从插件到一站式",
      items: [
        "过去：要 \u201C一个 AI 功能\u201D（+AI，插件式）",
        "现在：要 \u201C解决业务问题\u201D（AI 原生，一站式）",
        "业务不再满足\u201C能聊天的导览机器人\u201D，而是能结合偏好/路况/人流的专属深度游规划+全程陪伴+突发处理的智能体"
      ]
    },
    {
      title: "市场定位变化：消费级AI vs 生产级AI",
      items: [
        "豆包 / 千问：面向个人，通用服务，消费级 AI",
        "我们的商用输出：面向政、企，文旅行业智能体 + 平台，生产级 AI（核心壁垒）"
      ]
    }
  ];

  var cardY = 0.9, cardH = 1.4, cardGap = 0.1;
  var cardX = 0.35, cardW = leftW - 0.35;

  for (var i = 0; i < 3; i++) {
    var cy = cardY + i * (cardH + cardGap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: cardX, y: cy, w: cardW, h: cardH,
      fill: { color: C.white }, line: { color: "F48FB1", width: 1 },
      rectRadius: 0.05
    });
    s.addText(cardData[i].title, {
      x: cardX + 0.15, y: cy + 0.08, w: cardW - 0.3, h: 0.3,
      fontSize: 11, fontFace: "Microsoft YaHei", bold: true,
      color: C.text, align: "left", valign: "middle", margin: 0
    });
    var itemY = cy + 0.42;
    for (var j = 0; j < cardData[i].items.length; j++) {
      var lines = cardData[i].items.length;
      var ih = (cardH - 0.5) / lines;
      s.addText(cardData[i].items[j], {
        x: cardX + 0.2, y: itemY, w: cardW - 0.4, h: ih - 0.02,
        fontSize: 8, fontFace: "Microsoft YaHei", color: C.text,
        align: "left", valign: "top", margin: 0, wrap: true
      });
      itemY += ih;
    }
  }

  // 右侧45%区域：3级阶梯示意图
  var rightX = 5.8, rightW = 4.0, rightY = 1.0, rightH = 4.0;
  // 标题"技术演进"
  s.addText("技术演进", {
    x: rightX, y: rightY, w: rightW, h: 0.3,
    fontSize: 13, fontFace: "Microsoft YaHei", bold: true,
    color: C.text, align: "center", valign: "middle", margin: 0
  });

  // 3级阶梯（从低到高：浅蓝→青蓝→淡紫）
  var stepW = 2.8, stepH = 0.8;
  var stepX = rightX + 0.6;
  var step1Y = rightY + 3.0;  // 最低（通用大模型）
  var step2Y = rightY + 2.0;  // 中间（行业大模型）
  var step3Y = rightY + 1.0;  // 最高（AI原生智能体）

  var stepColors = [
    { fill: "BBDEFB", dark: "64B5F6", label: "通用大模型" },
    { fill: "B2DFDB", dark: "4DB6AC", label: "行业大模型" },
    { fill: "D1C4E9", dark: "9575CD", label: "AI原生智能体" }
  ];
  var stepYs = [step1Y, step2Y, step3Y];

  for (var k = 0; k < 3; k++) {
    var sy = stepYs[k];
    // 台阶本体
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: stepX, y: sy, w: stepW, h: stepH,
      fill: { color: stepColors[k].fill }, line: { color: stepColors[k].dark, width: 1 },
      rectRadius: 0.04
    });
    // 台阶标签
    s.addText(stepColors[k].label, {
      x: stepX + 0.1, y: sy + 0.1, w: 1.6, h: 0.3,
      fontSize: 10, fontFace: "Microsoft YaHei", bold: true,
      color: C.text, align: "left", valign: "middle", margin: 0
    });
    // 箭头标注（→在右侧）
    if (k < 2) {
      s.addText("\u2192", {
        x: stepX + 1.7, y: sy + 0.1, w: 0.3, h: 0.3,
        fontSize: 14, fontFace: "Arial", bold: true,
        color: stepColors[k].dark, align: "center", valign: "middle", margin: 0
      });
    }
    // 台阶图标占位（小型圆/方块代表图标）
    var iconColor = stepColors[k].dark;
    if (k === 2) {
      // 最高台阶：AI机器人图标（用圆形+方框模拟）
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: stepX + stepW - 0.65, y: sy + 0.15, w: 0.45, h: 0.5,
        fill: { color: C.white }, line: { color: iconColor, width: 1.5 },
        rectRadius: 0.08
      });
      s.addText("AI", {
        x: stepX + stepW - 0.65, y: sy + 0.15, w: 0.45, h: 0.5,
        fontSize: 11, fontFace: "Arial", bold: true,
        color: iconColor, align: "center", valign: "middle", margin: 0
      });
    } else {
      // 低台阶：数据立方体图标
      s.addShape(pres.shapes.OVAL, {
        x: stepX + stepW - 0.6, y: sy + 0.2, w: 0.4, h: 0.4,
        fill: { color: C.white }, line: { color: iconColor, width: 1.5 }
      });
    }
  }

  // 阶梯间向上箭头
  for (var a = 0; a < 2; a++) {
    var arX = stepX - 0.35;
    var arY = stepYs[a] - 0.35;
    s.addShape(pres.shapes.UP_ARROW, {
      x: arX, y: arY, w: 0.18, h: 0.3,
      fill: { color: "64B5F6" }
    });
  }

  addPageNum(s, 3);
}

// ========== PAGE 4: 技术机遇：大模型通往AGI ==========
function page4() {
  const s = pres.addSlide();
  addRedBarTitle(s, "技术机遇：大模型，通往通用人工智能时代（AGI）", 21);

  // 5张等级卡片
  var levels = [
    { label: "L1", title: "聊天机器人", desc: "具有对话能力的AI。", color: "FFF9C4", dark: "F9A825" },
    { label: "L2", title: "推理者", desc: "像人类一样能够解决问题的AI。", color: "C8E6C9", dark: "43A047" },
    { label: "L3", title: "智能体", desc: "不仅能思考，还可以采取行动的AI系统。", color: "B2DFDB", dark: "00897B", now: true },
    { label: "L4", title: "创新者", desc: "能够协助发明创造的AI。", color: "BBDEFB", dark: "1E88E5" },
    { label: "L5", title: "组织者", desc: "可以完成组织工作的AI。", color: "D1C4E9", dark: "5E35B1" }
  ];

  var lcardW = 1.72, lcardH = 1.6;
  var lgap = 0.12;
  var lstartX = (10 - (5 * lcardW + 4 * lgap)) / 2;
  var lcardY = 0.95;

  for (var i = 0; i < 5; i++) {
    var lx = lstartX + i * (lcardW + lgap);
    // NOW标签（L3上方）
    if (levels[i].now) {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: lx + 0.5, y: lcardY - 0.35, w: 0.7, h: 0.25,
        fill: { color: C.primary }, rectRadius: 0.03
      });
      s.addText("NOW", {
        x: lx + 0.5, y: lcardY - 0.35, w: 0.7, h: 0.25,
        fontSize: 9, fontFace: "Arial", bold: true,
        color: C.white, align: "center", valign: "middle", margin: 0
      });
      // 向下箭头
      s.addShape(pres.shapes.DOWN_ARROW, {
        x: lx + 0.75, y: lcardY - 0.1, w: 0.18, h: 0.15,
        fill: { color: C.primary }
      });
    }
    // 卡片上半部分（白色）
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: lx, y: lcardY, w: lcardW, h: lcardH * 0.45,
      fill: { color: C.white }, line: { color: levels[i].dark, width: 1 },
      rectRadius: 0.06
    });
    // 图标占位（圆形）
    s.addShape(pres.shapes.OVAL, {
      x: lx + lcardW / 2 - 0.22, y: lcardY + 0.12, w: 0.44, h: 0.44,
      fill: { color: levels[i].color }, line: { color: levels[i].dark, width: 1 }
    });
    // L标签
    s.addText(levels[i].label, {
      x: lx + lcardW / 2 - 0.22, y: lcardY + 0.12, w: 0.44, h: 0.44,
      fontSize: 14, fontFace: "Arial", bold: true,
      color: levels[i].dark, align: "center", valign: "middle", margin: 0
    });
    // 卡片下半部分（彩色）
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: lx, y: lcardY + lcardH * 0.45, w: lcardW, h: lcardH * 0.55,
      fill: { color: levels[i].color }, line: { color: levels[i].dark, width: 1 },
      rectRadius: 0.06
    });
    // 标题
    s.addText(levels[i].title, {
      x: lx + 0.05, y: lcardY + lcardH * 0.45 + 0.05, w: lcardW - 0.1, h: 0.25,
      fontSize: 10, fontFace: "Microsoft YaHei", bold: true,
      color: levels[i].dark, align: "center", valign: "middle", margin: 0
    });
    // 描述
    s.addText(levels[i].desc, {
      x: lx + 0.05, y: lcardY + lcardH * 0.45 + 0.32, w: lcardW - 0.1, h: 0.45,
      fontSize: 7.5, fontFace: "Microsoft YaHei", color: C.text,
      align: "center", valign: "top", margin: 0, wrap: true
    });
  }

  // 下半部分：3个阶段 + 红色箭头
  var phaseY = 2.85;

  // 阶段标题文字
  var phases = [
    { name: "看见\u201C吐字\u201D", x: 0.5 },
    { name: "看见\u201C推理\u201D", x: 3.85 },
    { name: "看见\u201C行动\u201D", x: 7.2 }
  ];
  for (var p = 0; p < 3; p++) {
    s.addText(phases[p].name, {
      x: phases[p].x, y: phaseY, w: 2.5, h: 0.35,
      fontSize: 14, fontFace: "Microsoft YaHei", bold: true,
      color: C.primary, align: "center", valign: "middle", margin: 0
    });
    // 红色箭头（连接阶段，非最后一个）
    if (p < 2) {
      s.addText("\u2192", {
        x: phases[p].x + 2.35, y: phaseY, w: 0.5, h: 0.35,
        fontSize: 18, fontFace: "Arial", bold: true,
        color: C.primary, align: "center", valign: "middle", margin: 0
      });
    }
  }

  // 阶段1：看见"吐字" - 2个手机UI模拟
  var p1Y = phaseY + 0.4;
  for (var m1 = 0; m1 < 2; m1++) {
    var m1x = 0.6 + m1 * 1.25;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: m1x, y: p1Y, w: 1.1, h: 1.6,
      fill: { color: C.white }, line: { color: C.gray4, width: 1 },
      rectRadius: 0.06
    });
    // 手机顶部条
    s.addShape(pres.shapes.RECTANGLE, {
      x: m1x, y: p1Y, w: 1.1, h: 0.15,
      fill: { color: C.gray5 }
    });
    // 模拟对话内容线
    for (var ml = 0; ml < 4; ml++) {
      s.addShape(pres.shapes.RECTANGLE, {
        x: m1x + 0.1, y: p1Y + 0.3 + ml * 0.2, w: 0.9 - ml * 0.1, h: 0.08,
        fill: { color: C.gray5 }
      });
    }
  }

  // 阶段2：看见"推理" - 2个模块（深度思考/AI搜索）
  var p2Y = phaseY + 0.4;
  var module2Data = [
    { title: "深度思考", sub: "先思考后回答，解决推理难题", x: 3.6 },
    { title: "AI 搜索", sub: "全网搜索，信息实时准确", x: 4.95 }
  ];
  for (var m2 = 0; m2 < 2; m2++) {
    var m2x = module2Data[m2].x;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: m2x, y: p2Y, w: 1.25, h: 1.6,
      fill: { color: C.white }, line: { color: C.gray4, width: 1 },
      rectRadius: 0.06
    });
    s.addText(module2Data[m2].title, {
      x: m2x, y: p2Y + 0.15, w: 1.25, h: 0.3,
      fontSize: 11, fontFace: "Microsoft YaHei", bold: true,
      color: C.text, align: "center", valign: "middle", margin: 0
    });
    s.addText(module2Data[m2].sub, {
      x: m2x + 0.05, y: p2Y + 0.45, w: 1.15, h: 0.25,
      fontSize: 7.5, fontFace: "Microsoft YaHei", color: C.textGray,
      align: "center", valign: "middle", margin: 0, wrap: true
    });
    // 模拟界面内容线
    for (var ml2 = 0; ml2 < 4; ml2++) {
      s.addShape(pres.shapes.RECTANGLE, {
        x: m2x + 0.1, y: p2Y + 0.75 + ml2 * 0.18, w: 1.05 - ml2 * 0.1, h: 0.06,
        fill: { color: C.gray5 }
      });
    }
  }

  // 阶段3：看见"行动" - 2×2卡片 + 商用标签
  var p3Y = phaseY + 0.4;
  var actionCards = [
    { label: "规划", x: 7.0, y: p3Y, color: "FFE0B2" },
    { label: "执行", x: 8.3, y: p3Y, color: "90CAF9" },
    { label: "归纳", x: 7.0, y: p3Y + 0.85, color: "CE93D8" },
    { label: "交付", x: 8.3, y: p3Y + 0.85, color: "FFF59D" }
  ];
  for (var ac = 0; ac < 4; ac++) {
    var acd = actionCards[ac];
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: acd.x, y: acd.y, w: 1.2, h: 0.75,
      fill: { color: acd.color }, line: { color: C.gray4, width: 0.5 },
      rectRadius: 0.04
    });
    s.addText(acd.label, {
      x: acd.x + 0.05, y: acd.y + 0.05, w: 0.3, h: 0.65,
      fontSize: 10, fontFace: "Microsoft YaHei", bold: true,
      color: C.text, align: "center", valign: "middle", margin: 0, charSpacing: 2
    });
    // 模拟内容
    for (var al = 0; al < 3; al++) {
      s.addShape(pres.shapes.RECTANGLE, {
        x: acd.x + 0.4, y: acd.y + 0.15 + al * 0.18, w: 0.7, h: 0.05,
        fill: { color: "FFFFFF", transparency: 50 }
      });
    }
  }
  // "商用正在抵达"红色标签
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 8.7, y: p3Y + 1.75, w: 1.0, h: 0.35,
    fill: { color: C.primary }, rectRadius: 0.03
  });
  s.addText("商用\n正在抵达", {
    x: 8.7, y: p3Y + 1.75, w: 1.0, h: 0.35,
    fontSize: 7.5, fontFace: "Microsoft YaHei", bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0
  });

  addPageNum(s, 4);
}

// ========== PAGE 5: 技术机遇：AI原生vs AI+ ==========
function page5() {
  const s = pres.addSlide();
  addRedBarTitle(s, "技术机遇：AI 原生，不是\u201CAI + 软件\u201D，而是\u201C软件长在 AI 上\u201D", 19);

  // 左右对比卡片
  var cardY = 1.0, cardH = 3.0;
  var cardW = 4.2, leftX = 0.35, rightX = 5.45;

  // 左卡片：旧世界
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: leftX, y: cardY, w: cardW, h: cardH,
    fill: { color: C.white }, line: { color: C.primary, width: 1 },
    rectRadius: 0.06
  });
  s.addText("旧世界：AI 是被动插件 (+AI)", {
    x: leftX + 0.15, y: cardY + 0.1, w: cardW - 0.3, h: 0.3,
    fontSize: 12, fontFace: "Microsoft YaHei", bold: true,
    color: C.text, align: "left", valign: "middle", margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: leftX + 0.15, y: cardY + 0.42, w: 0.5, h: 0.02, fill: { color: C.primary } });
  // 场景+痛点
  s.addText([
    { text: "场景：", options: { bold: true, fontSize: 10 } },
    { text: "传统景区导览APP\n手动输入目的地，生成文字，用完即走。", options: { fontSize: 10 } }
  ], { x: leftX + 0.15, y: cardY + 0.55, w: cardW - 0.3, h: 0.55, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  s.addText([
    { text: "痛点：", options: { bold: true, fontSize: 10, color: C.primary } },
    { text: "无记忆、无上下文\n无法处理复杂需求，缺乏个性化体验。", options: { fontSize: 10 } }
  ], { x: leftX + 0.15, y: cardY + 1.15, w: cardW - 0.3, h: 0.55, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  // 示意图占位（插件式架构）
  s.addText("AI插件式应用", {
    x: leftX + 0.15, y: cardY + 1.8, w: cardW - 0.3, h: 0.25,
    fontSize: 8, fontFace: "Microsoft YaHei", bold: true,
    color: C.textGray, align: "center", valign: "middle", margin: 0
  });
  // 模拟插件架构示意图（窗口+4个小图标）
  var archY = cardY + 2.1;
  s.addShape(pres.shapes.RECTANGLE, { x: leftX + 0.6, y: archY, w: 3.0, h: 0.35, fill: { color: C.gray5 }, line: { color: C.gray4, width: 0.5 } });
  s.addText("[网页窗口]", { x: leftX + 0.6, y: archY, w: 3.0, h: 0.35, fontSize: 7, fontFace: "Microsoft YaHei", color: C.textGray, align: "center", valign: "middle", margin: 0 });
  for (var pi = 0; pi < 4; pi++) {
    var pix = leftX + 0.65 + pi * 0.72;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: pix, y: archY + 0.45, w: 0.65, h: 0.3, fill: { color: C.white }, line: { color: C.gray4, width: 0.5 }, rectRadius: 0.03 });
    var piLabels = ["文档", "AI", "定位", "行囊"];
    s.addText(piLabels[pi], { x: pix, y: archY + 0.45, w: 0.65, h: 0.3, fontSize: 7, fontFace: "Microsoft YaHei", color: C.textGray, align: "center", valign: "middle", margin: 0 });
  }

  // 右卡片：新世界
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: rightX, y: cardY, w: cardW, h: cardH,
    fill: { color: C.white }, line: { color: C.primary, width: 1 },
    rectRadius: 0.06
  });
  s.addText("新世界：AI 是核心引擎 (AI原生)", {
    x: rightX + 0.15, y: cardY + 0.1, w: cardW - 0.3, h: 0.3,
    fontSize: 12, fontFace: "Microsoft YaHei", bold: true,
    color: C.text, align: "left", valign: "middle", margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: rightX + 0.15, y: cardY + 0.42, w: 0.5, h: 0.02, fill: { color: C.primary } });
  // 示意图（AI核心标识）
  s.addText("AI原生应用", {
    x: rightX + 0.15, y: cardY + 0.55, w: cardW - 0.3, h: 0.25,
    fontSize: 8, fontFace: "Microsoft YaHei", bold: true,
    color: C.textGray, align: "center", valign: "middle", margin: 0
  });
  // AI核心方块
  var aiCoreY = cardY + 0.85;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: rightX + 1.55, y: aiCoreY, w: 1.1, h: 0.4,
    fill: { color: C.gray1 }, rectRadius: 0.04
  });
  s.addText("AI", {
    x: rightX + 1.55, y: aiCoreY, w: 1.1, h: 0.4,
    fontSize: 16, fontFace: "Arial", bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0
  });
  // 下方连线+多个小图标（2行×6个）
  var iconLabels = ["用户", "地球", "编辑", "文档", "图表", "对话", "提醒", "打印", "手机", "服务", "主页", "公文"];
  for (var ri = 0; ri < 2; ri++) {
    for (var rj = 0; rj < 6; rj++) {
      var rix = rightX + 0.2 + rj * 0.65;
      var riy = aiCoreY + 0.5 + ri * 0.32;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: rix, y: riy, w: 0.55, h: 0.25,
        fill: { color: C.white }, line: { color: C.gray4, width: 0.5 },
        rectRadius: 0.03
      });
      s.addText(iconLabels[ri * 6 + rj], {
        x: rix, y: riy, w: 0.55, h: 0.25,
        fontSize: 6.5, fontFace: "Microsoft YaHei",
        color: C.textGray, align: "center", valign: "middle", margin: 0
      });
    }
  }
  // 场景+优势
  s.addText([
    { text: "场景：", options: { bold: true, fontSize: 9 } },
    { text: "行程规划\n位置、天气、人流，主动推送精准服务", options: { fontSize: 9 } }
  ], { x: rightX + 0.15, y: cardY + 2.05, w: cardW - 0.3, h: 0.5, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });
  s.addText([
    { text: "优势：", options: { bold: true, fontSize: 9, color: C.primary } },
    { text: "主动感知与闭环服务\n迷路时主动导航，过敏时自动绕路", options: { fontSize: 9 } }
  ], { x: rightX + 0.15, y: cardY + 2.55, w: cardW - 0.3, h: 0.5, fontFace: "Microsoft YaHei", color: C.text, align: "left", valign: "top", margin: 0, wrap: true });

  // 中间灰色箭头
  s.addShape(pres.shapes.RIGHT_ARROW, {
    x: 4.65, y: cardY + 1.3, w: 0.7, h: 0.3,
    fill: { color: C.gray3 }
  });

  // 底部浅蓝色模块：三大核心变革
  var btmY = 4.2, btmH = 1.1;
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: btmY, w: 10, h: btmH,
    fill: { color: C.blueBg }
  });
  s.addText("AI 原生带来的\n三大核心变革", {
    x: 0.2, y: btmY + 0.15, w: 1.8, h: 0.8,
    fontSize: 11, fontFace: "Microsoft YaHei", bold: true,
    color: C.blueDark, align: "center", valign: "middle", margin: 0, wrap: true
  });
  // 分隔线
  s.addShape(pres.shapes.RECTANGLE, { x: 2.1, y: btmY + 0.1, w: 0.02, h: btmH - 0.2, fill: { color: C.gray4 } });

  var changes = [
    { title: "业务流程变革", desc: "从\u201C人找服务\u201D转变为\u201C服务找人\u201D，实现主动触达。" },
    { title: "软件架构变革", desc: "从\u201C功能堆叠\u201D转变为\u201C智能驱动\u201D，架构更灵活高效。" },
    { title: "价值交付变革", desc: "从\u201C交付功能\u201D转变为\u201C交付业务结果\u201D，直接创造价值。" }
  ];
  for (var ci = 0; ci < 3; ci++) {
    var chx = 2.3 + ci * 2.6;
    s.addText(changes[ci].title, {
      x: chx, y: btmY + 0.15, w: 2.4, h: 0.3,
      fontSize: 11, fontFace: "Microsoft YaHei", bold: true,
      color: C.blueDark, align: "left", valign: "middle", margin: 0
    });
    s.addText(changes[ci].desc, {
      x: chx, y: btmY + 0.45, w: 2.4, h: 0.55,
      fontSize: 9, fontFace: "Microsoft YaHei", color: C.text,
      align: "left", valign: "top", margin: 0, wrap: true
    });
  }

  addPageNum(s, 5);
}

// ========== PAGE 6: 价值重构：人货场 ==========
function page6() {
  const s = pres.addSlide();
  // 标题（"文旅行业"红色）
  s.addText([
    { text: "价值重构：AI 原生如何重塑", options: { fontSize: 22, bold: true, color: C.text } },
    { text: "文旅行业", options: { fontSize: 22, bold: true, color: C.primary } },
    { text: "\u300C人 - 货 - 场\u300D", options: { fontSize: 22, bold: true, color: C.text } }
  ], { x: 0.3, y: 0.12, w: 9.4, h: 0.5, fontFace: "Microsoft YaHei", align: "center", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0.66, w: 10, h: 0.035, fill: { color: C.primary } });

  // 副标题
  s.addText("基于 AI 原生能力，从 G 端、B 端、C 端全面重塑文旅价值", {
    x: 0.5, y: 0.78, w: 9.0, h: 0.3,
    fontSize: 13, fontFace: "Microsoft YaHei", color: C.text,
    align: "center", valign: "middle", margin: 0
  });
  // 引导文字
  s.addText("\u00B7 从典型的场景化智能体开始", {
    x: 0.5, y: 1.1, w: 9.0, h: 0.25,
    fontSize: 12, fontFace: "Microsoft YaHei", color: C.text,
    align: "center", valign: "middle", margin: 0
  });

  // 三列模块
  var cols = [
    {
      title: "G端：风险预警调度",
      past: "过去：人工汇总研判，响应慢、处置粗，缺乏实时性。",
      now: "现在：7\u00D724小时实时感知并分析多维因素，自动预警并推送调度方案，实现秒级响应。",
      sub: "驾驶舱产品\n根据智能体全链路，重新改造应用",
      color: C.blue, bg: C.blueCard, bgLight: "F0F6FF",
      icon: "shield"
    },
    {
      title: "B端：博物助手智能体",
      past: "过去：讲解员培训周期长、成本高，内容同质化严重。",
      now: "现在：实时调取知识画像，定制讲解内容，独立完成高质量服务，降本增效。",
      sub: "数字员工类产品\n根据智能体全链路，信息集约对话窗",
      color: C.teal, bg: C.tealBg, bgLight: "E8F8F6",
      icon: "building"
    },
    {
      title: "C端：行程规划智能体",
      past: "过去：用户耗时查攻略，方案适配性差，难以满足个性化需求。",
      now: "现在：基于画像与预算，1分钟生成专属行程并动态调整，交易闭环一站式解决，实现说走就走。",
      sub: "C端App\n对话窗口解决全部问题，重塑app",
      color: C.purple, bg: C.purpleCard, bgLight: "F5EEF8",
      icon: "list"
    }
  ];

  var colW = 3.0, colGap = 0.15;
  var colStartX = (10 - (3 * colW + 2 * colGap)) / 2;
  var mainCardY = 1.5, mainCardH = 2.5;
  var subCardH = 0.9;

  for (var i = 0; i < 3; i++) {
    var cx = colStartX + i * (colW + colGap);
    var col = cols[i];
    // 主卡片（淡色背景+彩色边框）
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: cx, y: mainCardY, w: colW, h: mainCardH,
      fill: { color: col.bgLight }, line: { color: col.color, width: 1 },
      rectRadius: 0.06
    });
    // 图标占位（彩色圆形）
    s.addShape(pres.shapes.OVAL, {
      x: cx + 0.15, y: mainCardY + 0.12, w: 0.35, h: 0.35,
      fill: { color: col.color }
    });
    // 图标符号
    var iconChar = (i === 0) ? "\u25A0" : (i === 1) ? "\u25A0" : "\u2630";
    s.addText(iconChar, {
      x: cx + 0.15, y: mainCardY + 0.12, w: 0.35, h: 0.35,
      fontSize: 12, fontFace: "Arial", bold: true,
      color: C.white, align: "center", valign: "middle", margin: 0
    });
    // 标题
    s.addText(col.title, {
      x: cx + 0.55, y: mainCardY + 0.12, w: colW - 0.7, h: 0.35,
      fontSize: 11, fontFace: "Microsoft YaHei", bold: true,
      color: col.color, align: "left", valign: "middle", margin: 0
    });
    // 过去
    s.addText([
      { text: "过去：", options: { bold: true, fontSize: 9, color: C.textGray } },
      { text: col.past.replace("过去：", ""), options: { fontSize: 9, color: C.text } }
    ], { x: cx + 0.15, y: mainCardY + 0.55, w: colW - 0.3, h: 0.55, fontFace: "Microsoft YaHei", align: "left", valign: "top", margin: 0, wrap: true });
    // 现在
    s.addText([
      { text: "现在：", options: { bold: true, fontSize: 9, color: col.color } },
      { text: col.now.replace("现在：", ""), options: { fontSize: 9, color: C.text } }
    ], { x: cx + 0.15, y: mainCardY + 1.15, w: colW - 0.3, h: 0.75, fontFace: "Microsoft YaHei", align: "left", valign: "top", margin: 0, wrap: true });
    // 分隔线
    s.addShape(pres.shapes.RECTANGLE, { x: cx + 0.15, y: mainCardY + 1.95, w: colW - 0.3, h: 0.01, fill: { color: C.gray4 } });
    // 产品类型
    s.addText(col.sub, {
      x: cx + 0.15, y: mainCardY + 2.0, w: colW - 0.3, h: 0.45,
      fontSize: 8.5, fontFace: "Microsoft YaHei", color: C.textGray,
      align: "left", valign: "top", margin: 0, wrap: true
    });

    // 附属小卡片
    var subY = mainCardY + mainCardH + 0.1;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: cx, y: subY, w: colW, h: subCardH,
      fill: { color: col.bg }, line: { color: col.color, width: 0.5 },
      rectRadius: 0.04
    });
    // 端口标识
    var portLabel = (i === 0) ? "G端" : (i === 1) ? "B端" : "C端";
    s.addText(portLabel + " 智能体", {
      x: cx + 0.15, y: subY + 0.12, w: colW - 0.3, h: 0.3,
      fontSize: 10, fontFace: "Microsoft YaHei", bold: true,
      color: col.color, align: "left", valign: "middle", margin: 0
    });
    s.addText("\u2192 场景化落地", {
      x: cx + 0.15, y: subY + 0.42, w: colW - 0.3, h: 0.3,
      fontSize: 9, fontFace: "Microsoft YaHei", color: C.textGray,
      align: "left", valign: "middle", margin: 0
    });
  }

  addPageNum(s, 6);
}

// ========== PAGE 7: 核心燃料：高质量数据集 ==========
function page7() {
  const s = pres.addSlide();
  addRedBarTitle(s, "核心燃料：高质量数据集 \u2014\u2014 行业 AI 的核心发动机", 21);

  // 说明正文（红色高亮"价值密度"）
  s.addText([
    { text: "数据价值是规模法则持续扩展的主要因素，数据价值可以用\u201C", options: { fontSize: 11, color: C.text } },
    { text: "价值密度", options: { fontSize: 11, color: C.primary, bold: true } },
    { text: "\u201D来度量（语言能力，知识能力，逻辑能力、以及私域数据，如史料+研究成果+思维链+问答），而公开互联网的数据即将枯竭，深挖细分领域的数据将成为未来竞争的关键", options: { fontSize: 11, color: C.text } }
  ], { x: 0.5, y: 0.82, w: 9.0, h: 0.5, fontFace: "Microsoft YaHei", align: "center", valign: "middle", margin: 0, wrap: true });

  // 左右两个模块（红棕边框）
  var modY = 1.45, modH = 3.65;
  var leftModX = 0.35, leftModW = 4.8;
  var rightModX = 5.35, rightModW = 4.3;

  // 左模块：S曲线图
  addBrokenBorder(s, leftModX, modY, leftModW, modH, C.redDeep);
  // 红色标题条
  s.addShape(pres.shapes.RECTANGLE, {
    x: leftModX, y: modY, w: leftModW, h: 0.35,
    fill: { color: C.primary }
  });
  s.addText("数据价值密度决定了规模法则S曲线的陡峭程度（对模型的增益）", {
    x: leftModX + 0.1, y: modY, w: leftModW - 0.2, h: 0.35,
    fontSize: 8.5, fontFace: "Microsoft YaHei", bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0, wrap: true
  });

  // 生成S曲线数据
  var chartData = [];
  for (var x = -6; x <= 6; x += 0.5) {
    var lang = 1 / (1 + Math.exp(-5 * x));
    var know = 1 / (1 + Math.exp(-1 * x));
    var logic = 1 / (1 + Math.exp(-0.2 * x));
    var llm = (lang + know + logic) / 3;
    chartData.push({ x: x, lang: lang, know: know, logic: logic, llm: llm });
  }

  var chartXValues = chartData.map(function(d) { return d.x; });
  var chartLang = chartData.map(function(d) { return d.lang; });
  var chartKnow = chartData.map(function(d) { return d.know; });
  var chartLogic = chartData.map(function(d) { return d.logic; });
  var chartLLM = chartData.map(function(d) { return d.llm; });

  // 使用pptxgenjs的散点图/折线图
  s.addChart(pres.ChartType.line, [
    { name: "Language:k=5", labels: chartXValues, values: chartLang },
    { name: "Knowledge:k=1", labels: chartXValues, values: chartKnow },
    { name: "Logic:k=0.2", labels: chartXValues, values: chartLogic },
    { name: "LLM Intelligence", labels: chartXValues, values: chartLLM }
  ], {
    x: leftModX + 0.15, y: modY + 0.45, w: leftModW - 0.3, h: modH - 1.0,
    showTitle: false,
    showLegend: true,
    legendPos: "t",
    legendColor: C.text,
    legendFontSize: 7,
    catAxisLabelColor: C.textGray,
    catAxisLabelFontSize: 7,
    valAxisLabelColor: C.textGray,
    valAxisLabelFontSize: 7,
    valAxisTitle: "Intelligence Level of AI",
    valAxisTitleColor: C.textGray,
    valAxisTitleFontSize: 8,
    chartColors: ["2196F3", "FF9800", "4CAF50", "F44336"],
    lineSize: [2, 2, 2, 2.5],
    lineSmooth: true,
    showValue: false,
    catAxisMinVal: -6,
    catAxisMaxVal: 6,
    valAxisMinVal: 0,
    valAxisMaxVal: 1
  });

  // 公式标注
  s.addText("sigmoid(x) = 1/(1+e\u207B\u1D4F\u02E3)", {
    x: leftModX + 0.15, y: modY + modH - 0.35, w: leftModW - 0.3, h: 0.25,
    fontSize: 8, fontFace: "Arial", italic: true,
    color: C.textGray, align: "left", valign: "middle", margin: 0
  });

  // 右模块：3个要点
  addBrokenBorder(s, rightModX, modY, rightModW, modH, C.redDeep);
  s.addShape(pres.shapes.RECTANGLE, {
    x: rightModX, y: modY, w: rightModW, h: 0.35,
    fill: { color: C.primary }
  });
  s.addText("面向细分场景\n高质量私域数据是制胜关键", {
    x: rightModX + 0.1, y: modY, w: rightModW - 0.2, h: 0.35,
    fontSize: 9, fontFace: "Microsoft YaHei", bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0, wrap: true
  });

  var points = [
    "互联网数据的趋同性和开源技术使大模型趋于同质化，若要深入应用场景的落地，需要差异化的数据",
    "深入挖掘细分领域的数据将成为未来竞争的关键",
    "这些数据往往存在于私域，主要以文档、应用APP等形式存在"
  ];

  var ptY = modY + 0.6;
  for (var pi = 0; pi < points.length; pi++) {
    s.addText("\u25B6", {
      x: rightModX + 0.15, y: ptY, w: 0.2, h: 0.3,
      fontSize: 9, fontFace: "Arial", bold: true,
      color: C.primary, align: "left", valign: "top", margin: 0
    });
    s.addText(points[pi], {
      x: rightModX + 0.4, y: ptY, w: rightModW - 0.55, h: 0.9,
      fontSize: 9, fontFace: "Microsoft YaHei", color: C.text,
      align: "left", valign: "top", margin: 2, lineSpacing: 12, wrap: true
    });
    ptY += 1.0;
  }

  addPageNum(s, 7);
}

// ========== PAGE 8: 平台赋能：智能体平台 ==========
function page8() {
  const s = pres.addSlide();
  addRedBarTitle(s, "平台赋能：为智能体和应用提供\u201C无限弹药\u201D", 22);

  // 左侧70%区域
  var leftW = 6.8;

  // 4个粉色标签
  var tagLabels = ["引入先进平台", "行业数据飞轮", "提升交付效率", "AI安全合规"];
  var tagW = 1.5, tagH = 0.32, tagGap = 0.08;
  var tagStartX = 0.35;
  var tagY = 0.9;
  for (var ti = 0; ti < 4; ti++) {
    var tagX = tagStartX + ti * (tagW + tagGap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: tagX, y: tagY, w: tagW, h: tagH,
      fill: { color: C.pinkTag }, line: { color: "F8BBD0", width: 0.5 },
      rectRadius: 0.04
    });
    s.addText(tagLabels[ti], {
      x: tagX, y: tagY, w: tagW, h: tagH,
      fontSize: 9, fontFace: "Microsoft YaHei",
      color: C.text, align: "center", valign: "middle", margin: 0
    });
  }

  // Agent标签（蓝色）
  var agentY = 1.4;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.35, y: agentY, w: 0.8, h: 0.3,
    fill: { color: C.blueBg }, line: { color: C.blue, width: 0.5 },
    rectRadius: 0.04
  });
  s.addText("Agent", {
    x: 0.35, y: agentY, w: 0.8, h: 0.3,
    fontSize: 9, fontFace: "Microsoft YaHei", bold: true,
    color: C.blue, align: "center", valign: "middle", margin: 0
  });

  // 智能体平台大卡片
  var mainCardX = 1.3, mainCardY = 1.35, mainCardW = 5.7, mainCardH = 0.75;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: mainCardX, y: mainCardY, w: mainCardW, h: mainCardH,
    fill: { color: C.white }, line: { color: "F8BBD0", width: 1 },
    rectRadius: 0.04
  });
  // 紫色图标
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: mainCardX + 0.1, y: mainCardY + 0.1, w: 0.5, h: 0.55,
    fill: { color: C.purpleBg }, line: { color: C.purple, width: 0.5 },
    rectRadius: 0.04
  });
  s.addText("AI", {
    x: mainCardX + 0.1, y: mainCardY + 0.1, w: 0.5, h: 0.55,
    fontSize: 14, fontFace: "Arial", bold: true,
    color: C.purple, align: "center", valign: "middle", margin: 0
  });
  // 标题+说明
  s.addText("智能体平台", {
    x: mainCardX + 0.7, y: mainCardY + 0.05, w: 3.0, h: 0.3,
    fontSize: 11, fontFace: "Microsoft YaHei", bold: true,
    color: C.text, align: "left", valign: "middle", margin: 0
  });
  s.addText("提供开发、调试及多渠道发布能力，快速定制专属智能体，缩短交付周期，提升客单价。", {
    x: mainCardX + 0.7, y: mainCardY + 0.32, w: 4.9, h: 0.4,
    fontSize: 8.5, fontFace: "Microsoft YaHei", color: C.textGray,
    align: "left", valign: "top", margin: 0, wrap: true
  });

  // 3个子平台卡片
  var subCards = [
    { title: "智能BI平台", desc: "快速生成文旅数据报告，挖掘业务机会，成为销售打动客户的\u201C数据武器\u201D。", tag: "数据", icon: "BI", color: C.blue, bg: C.blueBg },
    { title: "知识库平台", desc: "内置文旅知识图谱，让智能体\u201C博古通今\u201D，多源知识导入，即可实现可控问答、搜索等", tag: "知识", icon: "KB", color: C.teal, bg: C.tealBg },
    { title: "多模态工具箱", desc: "AI生图、生视频及互动体验搭建，帮助客户快速制作AI创意，制作营销物料。", tag: "多模态内容", icon: "MM", color: C.blue, bg: C.blueBg }
  ];

  var subY = 2.25, subH = 1.2;
  var subW = 1.83, subGap = 0.08;
  var subStartX = 1.3;

  for (var si = 0; si < 3; si++) {
    var sx = subStartX + si * (subW + subGap);
    // 卡片
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: sx, y: subY, w: subW, h: subH,
      fill: { color: C.white }, line: { color: "F8BBD0", width: 1 },
      rectRadius: 0.04
    });
    // 图标
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: sx + 0.1, y: subY + 0.1, w: 0.45, h: 0.4,
      fill: { color: subCards[si].bg }, line: { color: subCards[si].color, width: 0.5 },
      rectRadius: 0.03
    });
    s.addText(subCards[si].icon, {
      x: sx + 0.1, y: subY + 0.1, w: 0.45, h: 0.4,
      fontSize: 10, fontFace: "Arial", bold: true,
      color: subCards[si].color, align: "center", valign: "middle", margin: 0
    });
    // 标题
    s.addText(subCards[si].title, {
      x: sx + 0.6, y: subY + 0.1, w: subW - 0.7, h: 0.3,
      fontSize: 10, fontFace: "Microsoft YaHei", bold: true,
      color: C.text, align: "left", valign: "middle", margin: 0
    });
    // 说明文字
    s.addText(subCards[si].desc, {
      x: sx + 0.1, y: subY + 0.55, w: subW - 0.2, h: 0.6,
      fontSize: 7, fontFace: "Microsoft YaHei", color: C.textGray,
      align: "left", valign: "top", margin: 0, wrap: true
    });
  }

  // 3个蓝色向上箭头 + 标签
  var arrowY = subY + subH + 0.05;
  for (var ai = 0; ai < 3; ai++) {
    var arX = subStartX + ai * (subW + subGap) + subW / 2 - 0.1;
    s.addShape(pres.shapes.UP_ARROW, {
      x: arX, y: arrowY, w: 0.2, h: 0.22,
      fill: { color: C.blue }
    });
    // 标签
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: arX - 0.35, y: arrowY + 0.25, w: 0.9, h: 0.28,
      fill: { color: C.blueBg }, line: { color: C.blue, width: 0.5 },
      rectRadius: 0.03
    });
    s.addText(subCards[ai].tag, {
      x: arX - 0.35, y: arrowY + 0.25, w: 0.9, h: 0.28,
      fontSize: 7.5, fontFace: "Microsoft YaHei",
      color: C.blue, align: "center", valign: "middle", margin: 0
    });
  }

  // 右侧30%区域：3张界面截图占位
  var rightX = 7.3, rightW = 2.5;
  var shotLabels = ["知识库平台", "智能体平台", "AIGC工具箱"];
  for (var ri = 0; ri < 3; ri++) {
    var ry = 0.9 + ri * 1.5;
    // 截图占位框
    s.addShape(pres.shapes.RECTANGLE, {
      x: rightX, y: ry, w: rightW, h: 1.3,
      fill: { color: C.fillGray }, line: { color: C.gray4, width: 0.5 }
    });
    // 灰色半透明标注条
    s.addShape(pres.shapes.RECTANGLE, {
      x: rightX, y: ry + 0.45, w: rightW, h: 0.35,
      fill: { color: C.gray1, transparency: 40 }
    });
    s.addText(shotLabels[ri], {
      x: rightX, y: ry + 0.45, w: rightW, h: 0.35,
      fontSize: 10, fontFace: "Microsoft YaHei", bold: true,
      color: C.white, align: "center", valign: "middle", margin: 0
    });
    // 模拟界面内容线
    for (var sl = 0; sl < 3; sl++) {
      s.addShape(pres.shapes.RECTANGLE, {
        x: rightX + 0.15, y: ry + 0.9 + sl * 0.12, w: rightW - 0.3 - sl * 0.1, h: 0.05,
        fill: { color: C.gray4 }
      });
    }
  }

  addPageNum(s, 8);
}

// ========== PAGE 9: 数据集能力3：标注服务 ==========
function page9() {
  const s = pres.addSlide();
  // 红色标题栏（白字+右上角logo）
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.65, fill: { color: C.primary } });
  s.addText("高质量数据集能力3：以标注基地为基础提供多种标注服务", {
    x: 0.3, y: 0, w: 8.0, h: 0.65,
    fontSize: 16, fontFace: "Microsoft YaHei", bold: true,
    color: C.white, align: "left", valign: "middle", margin: 0
  });
  // 右上角企业标识
  s.addShape(pres.shapes.RECTANGLE, { x: 8.5, y: 0.18, w: 0.35, h: 0.3, fill: { color: C.blue } });
  s.addShape(pres.shapes.RECTANGLE, { x: 8.85, y: 0.18, w: 0.35, h: 0.3, fill: { color: C.primary } });
  s.addText("中电信文宣科技", {
    x: 9.2, y: 0.18, w: 0.75, h: 0.3,
    fontSize: 7, fontFace: "Microsoft YaHei", bold: true,
    color: C.white, align: "left", valign: "middle", margin: 0, wrap: true
  });

  // 副标题（红色高亮）
  s.addText([
    { text: "基于规模化标注服务，打造", options: { fontSize: 11, color: C.text } },
    { text: "领域化、专业化标注能力", options: { fontSize: 11, color: C.primary, bold: true } },
    { text: "，实现\u201C本地文化、本地标注、精准标注\u201D", options: { fontSize: 11, color: C.text } }
  ], { x: 0.3, y: 0.75, w: 9.4, h: 0.32, fontFace: "Microsoft YaHei", align: "center", valign: "middle", margin: 0, wrap: true });

  // 三栏布局
  var colW = 3.1, colGap = 0.15;
  var colStartX = (10 - (3 * colW + 2 * colGap)) / 2;
  var colY = 1.2, colH = 4.0;

  // 橙红色圆角标签
  var tagColor = "E64A19";
  var tagLabels = ["7个中心：正式授牌", "标注服务：领域分标", "队伍建设与行业深耕"];

  for (var ci = 0; ci < 3; ci++) {
    var cx = colStartX + ci * (colW + colGap);
    // 标签
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: cx, y: colY, w: colW, h: 0.35,
      fill: { color: tagColor }, rectRadius: 0.03
    });
    s.addText(tagLabels[ci], {
      x: cx + 0.1, y: colY, w: colW - 0.2, h: 0.35,
      fontSize: 10, fontFace: "Microsoft YaHei", bold: true,
      color: C.white, align: "center", valign: "middle", margin: 0
    });
  }

  // 左栏内容：7个中心
  var lcx = colStartX;
  var leftItems = [
    "\u2022 协助建设国家级数据标注基地-成都、沈阳、保定、合肥",
    "\u2022 集团内部建设\u201C星海数据标注技术研究中心\u201D 七大中心授牌落地",
    "\u2022 文宣：聚焦文化旅游与媒体服务，打造行业高质量数据集；"
  ];
  var liY = colY + 0.45;
  for (var li = 0; li < leftItems.length; li++) {
    s.addText(leftItems[li], {
      x: lcx + 0.1, y: liY, w: colW - 0.2, h: 0.5,
      fontSize: 8, fontFace: "Microsoft YaHei", color: C.text,
      align: "left", valign: "top", margin: 0, wrap: true
    });
    liY += 0.55;
  }
  // 左栏配图占位（授牌实拍图）
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: lcx + 0.1, y: liY + 0.05, w: colW - 0.2, h: 1.6,
    fill: { color: C.blueBg }, line: { color: C.gray4, width: 0.5 },
    rectRadius: 0.04
  });
  s.addText("星海数据标注技术研究中心授牌", {
    x: lcx + 0.1, y: liY + 0.1, w: colW - 0.2, h: 0.25,
    fontSize: 8, fontFace: "Microsoft YaHei", bold: true,
    color: C.blueDark, align: "center", valign: "middle", margin: 0
  });
  // 模拟配图内容（人像占位）
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: lcx + 0.4, y: liY + 0.4, w: colW - 0.8, h: 1.05,
    fill: { color: C.blueDark }, rectRadius: 0.03
  });
  s.addText("星海 智启", {
    x: lcx + 0.4, y: liY + 0.4, w: colW - 0.8, h: 1.05,
    fontSize: 16, fontFace: "Microsoft YaHei", bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0
  });

  // 中栏内容：6个领域卡片 2×3
  var mcx = colStartX + (colW + colGap);
  s.addText("联合头部机构、研究所、高校、出版社等行业外脑，和细分领域生态合作伙伴，打造领域化标注能力", {
    x: mcx + 0.1, y: colY + 0.45, w: colW - 0.2, h: 0.45,
    fontSize: 7.5, fontFace: "Microsoft YaHei", color: C.textGray,
    align: "left", valign: "top", margin: 0, wrap: true
  });
  // 6个领域卡片
  var domains = [
    { name: "音乐", items: "声乐、器乐、歌剧、交响乐" },
    { name: "舞蹈", items: "古典舞、现代舞、芭蕾、桑巴" },
    { name: "旅游", items: "全域、景区、休闲" },
    { name: "文物", items: "陶器、金石、石窟寺" },
    { name: "媒体", items: "时政、科技、体育" },
    { name: "非遗", items: "剪纸、刺绣、木工" }
  ];
  var dY = colY + 0.95;
  var dW = 1.5, dH = 1.3, dGx = 0.05, dGy = 0.08;
  for (var di = 0; di < 6; di++) {
    var dcol = di % 2, drow = Math.floor(di / 2);
    var dx = mcx + 0.05 + dcol * (dW + dGx);
    var dy = dY + drow * (dH + dGy);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: dx, y: dy, w: dW, h: dH,
      fill: { color: C.white }, line: { color: C.gray4, width: 0.75 },
      rectRadius: 0.04
    });
    // 红色标题
    s.addText(domains[di].name, {
      x: dx, y: dy + 0.08, w: dW, h: 0.3,
      fontSize: 11, fontFace: "Microsoft YaHei", bold: true,
      color: C.primary, align: "center", valign: "middle", margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, { x: dx + 0.3, y: dy + 0.38, w: dW - 0.6, h: 0.015, fill: { color: C.gray4 } });
    // 内容
    s.addText(domains[di].items, {
      x: dx + 0.1, y: dy + 0.45, w: dW - 0.2, h: 0.75,
      fontSize: 8, fontFace: "Microsoft YaHei", color: C.text,
      align: "center", valign: "top", margin: 0, wrap: true
    });
  }

  // 右栏内容：队伍建设 + 行业深耕
  var rcx = colStartX + 2 * (colW + colGap);
  // 队伍建设（虚线框）
  var rc1Y = colY + 0.45, rc1H = 1.7;
  s.addShape(pres.shapes.RECTANGLE, {
    x: rcx, y: rc1Y, w: colW, h: rc1H,
    fill: { color: C.white }, line: { color: C.gray3, width: 1, dash: "dash" }
  });
  s.addText("队伍建设", {
    x: rcx + 0.1, y: rc1Y + 0.05, w: 1.0, h: 0.25,
    fontSize: 10, fontFace: "Microsoft YaHei", bold: true,
    color: C.primary, align: "left", valign: "middle", margin: 0
  });
  var teamItems = [
    "\u2460 自有队伍：专注于产品设计、机器预标注、项目管理、规范制定、样本预标",
    "\u2461 联合省市兄弟公司人才队伍，以\u201C创新场景示范基地\u201D等牵引，实现本地文化本地标注",
    "\u2462 通过技术平台技术手段，聚合在校学生、文化爱好者等社会力量"
  ];
  var tY = rc1Y + 0.32;
  for (var tii = 0; tii < teamItems.length; tii++) {
    s.addText(teamItems[tii], {
      x: rcx + 0.1, y: tY, w: colW - 0.2, h: 0.4,
      fontSize: 7, fontFace: "Microsoft YaHei", color: C.text,
      align: "left", valign: "top", margin: 0, wrap: true
    });
    tY += 0.42;
  }

  // 行业深耕（虚线框）
  var rc2Y = rc1Y + rc1H + 0.12, rc2H = 1.6;
  s.addShape(pres.shapes.RECTANGLE, {
    x: rcx, y: rc2Y, w: colW, h: rc2H,
    fill: { color: C.white }, line: { color: C.gray3, width: 1, dash: "dash" }
  });
  s.addText("行业深耕", {
    x: rcx + 0.1, y: rc2Y + 0.05, w: 1.0, h: 0.25,
    fontSize: 10, fontFace: "Microsoft YaHei", bold: true,
    color: C.primary, align: "left", valign: "middle", margin: 0
  });
  var deepItems = [
    "\u2460 聚焦目标行业，深挖垂类数据标注专业知识，创新升级行业标注模型等技术能力",
    "\u2461 建设丰富场景的行业高质量数据集",
    "\u2462 共创多场景数据产品，助力知识活化，资产活用"
  ];
  var dY2 = rc2Y + 0.32;
  for (var dii = 0; dii < deepItems.length; dii++) {
    s.addText(deepItems[dii], {
      x: rcx + 0.1, y: dY2, w: colW - 0.2, h: 0.4,
      fontSize: 7, fontFace: "Microsoft YaHei", color: C.text,
      align: "left", valign: "top", margin: 0, wrap: true
    });
    dY2 += 0.4;
  }

  addPageNum(s, 9);
}

// ==================== 生成完整9页PPT ====================
page1();
page2();
page3();
page4();
page5();
page6();
page7();
page8();
page9();

var outPath = path.join(__dirname, "AI+文旅_完整版.pptx");
pres.writeFile({ fileName: outPath }).then(function() {
  console.log("PPT saved to:", outPath);
}).catch(function(err) {
  console.error("Error:", err);
});
