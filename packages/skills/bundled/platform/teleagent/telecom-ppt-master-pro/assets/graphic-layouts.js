// =====================================================================
// GRAPHIC-LAYOUTS.JS — 电信PPT大师 v7.1 图形布局引擎
// 将 mck-ppt-design 的设计逻辑用 pptxgenjs 原生重写
// 10种图形布局，全部使用 pptxgenjs 原生形状，PPT中可编辑
// =====================================================================
//
// 用法:
//   const gl = require('./graphic-layouts.js');
//   const layouts = gl.create(pres);
//   layouts.drawTimeline(slide, x, y, w, h, milestones, opts);
//
// 支持主题:
//   'telecom-red'      — 电信深红配色（默认）
//   'executive-blue'   — 高管座谈会蓝主红辅配色
// =====================================================================

function create(pres) {
  const S = pres.shapes;

  // ======================== 主题配色 ========================
  const THEMES = {
    'telecom-red': {
      primary: 'C00000', primaryDark: 'A8001A', primaryLight: 'D6001F',
      accent: 'FFD700', accentLight: 'FFF0A0',
      iceLight: 'FFF0F0', iceMid: 'FFE4E4', border: 'E8B4B4',
      text: '000000', textLight: '333333', muted: '888888',
      highlight: 'FFFF00', white: 'FFFFFF',
      positive: '70B040', negative: 'C00000',
      fontFace: 'Microsoft YaHei',
    },
    'executive-blue': {
      primary: '0070C0', primaryDark: '0055B8', primaryLight: '5090D0',
      accent: 'C00000', accentLight: 'D6001F',
      iceLight: 'F5F9FC', iceMid: 'E8F0F8', border: 'D0D8E0',
      text: '000000', textLight: '333333', muted: '888888',
      highlight: 'FFFF00', white: 'FFFFFF',
      positive: '70B040', negative: 'C00000',
      fontFace: 'Microsoft YaHei',
    },
  };

  function getTheme(name) {
    return THEMES[name] || THEMES['telecom-red'];
  }

  function shadow() {
    return { type: 'outer', color: '000000', blur: 5, offset: 1.5, angle: 270, opacity: 0.08 };
  }

  // ======================== 1. 时间轴 ========================
  // milestones: [{ label, date, desc }]
  function drawTimeline(slide, x, y, w, h, milestones, opts) {
    opts = opts || {};
    const T = getTheme(opts.theme);
    const F = T.fontFace;
    const n = milestones.length;
    if (n < 2) return;

    const lineY = y + h * 0.45;
    const nodeR = 0.18; // 节点半径
    const step = (w - 0.8) / (n - 1);

    // 主轴线（渐变效果：用三段不同色矩形模拟）
    slide.addShape(S.RECTANGLE, {
      x: x + 0.4, y: lineY, w: w - 0.8, h: 0.05,
      fill: { color: T.primary }, line: { type: 'none' },
    });
    // 起点装饰
    slide.addShape(S.OVAL, {
      x: x + 0.4 - 0.08, y: lineY - 0.03, w: 0.12, h: 0.12,
      fill: { color: T.primaryDark }, line: { type: 'none' },
    });
    // 终点箭头
    slide.addShape(S.RIGHT_ARROW, {
      x: x + w - 0.4 - 0.15, y: lineY - 0.06, w: 0.3, h: 0.18,
      fill: { color: T.primary }, line: { type: 'none' },
    });

    milestones.forEach((m, i) => {
      const cx = x + 0.4 + step * i;
      const isAbove = i % 2 === 0; // 交替上下

      // 节点圆
      slide.addShape(S.OVAL, {
        x: cx - nodeR, y: lineY + 0.025 - nodeR, w: nodeR * 2, h: nodeR * 2,
        fill: { color: T.white }, line: { color: T.primary, width: 2.5 },
      });
      // 节点编号
      slide.addText(String(i + 1), {
        x: cx - nodeR, y: lineY + 0.025 - nodeR, w: nodeR * 2, h: nodeR * 2,
        fontFace: F, fontSize: 9, bold: true, color: T.primary,
        align: 'center', valign: 'middle', margin: 0,
      });

      // 连接线（节点到标签）
      const connH = 0.3;
      const labelY = isAbove ? lineY - connH - 0.7 : lineY + connH + 0.05;
      slide.addShape(S.RECTANGLE, {
        x: cx - 0.005, y: isAbove ? labelY + 0.65 : lineY + 0.2,
        w: 0.01, h: connH,
        fill: { color: T.border }, line: { type: 'none' },
      });

      // 日期标签
      if (m.date) {
        slide.addText(m.date, {
          x: cx - step * 0.4, y: isAbove ? labelY : labelY + 0.3,
          w: step * 0.8, h: 0.24,
          fontFace: F, fontSize: 10, bold: true, color: T.primary,
          align: 'center', valign: 'middle', margin: 0,
        });
      }
      // 标题
      slide.addText(m.label, {
        x: cx - step * 0.4, y: isAbove ? labelY + 0.22 : labelY,
        w: step * 0.8, h: 0.26,
        fontFace: F, fontSize: 11, bold: true, color: T.text,
        align: 'center', valign: 'middle', margin: 0,
      });
      // 描述
      if (m.desc) {
        slide.addText(m.desc, {
          x: cx - step * 0.42, y: isAbove ? labelY + 0.46 : labelY + 0.24,
          w: step * 0.84, h: 0.22,
          fontFace: F, fontSize: 9, color: T.muted,
          align: 'center', valign: 'middle', margin: 0,
        });
      }
    });
  }

  // ======================== 2. 流程箭头 ========================
  // steps: [{ label, desc }]
  function drawProcessFlow(slide, x, y, w, h, steps, opts) {
    opts = opts || {};
    const T = getTheme(opts.theme);
    const F = T.fontFace;
    const n = steps.length;
    if (n < 2) return;

    const arrowW = 0.35;
    const totalArrowW = arrowW * (n - 1);
    const boxW = (w - totalArrowW) / n;
    const boxH = h * 0.55;
    const boxY = y + (h - boxH) / 2;

    steps.forEach((st, i) => {
      const bx = x + i * (boxW + arrowW);
      const isLast = i === n - 1;
      const fillC = isLast ? T.primary : T.iceLight;
      const txtC = isLast ? T.white : T.primary;

      // 步骤盒子
      slide.addShape(S.RECTANGLE, {
        x: bx, y: boxY, w: boxW, h: boxH,
        fill: { color: fillC }, line: { color: T.primary, width: 1.2 },
        shadow: shadow(), rectRadius: 0.08,
      });
      // 编号圆
      slide.addShape(S.OVAL, {
        x: bx + boxW / 2 - 0.2, y: boxY - 0.15, w: 0.4, h: 0.4,
        fill: { color: T.primary }, line: { color: T.white, width: 2 },
      });
      slide.addText(String(i + 1), {
        x: bx + boxW / 2 - 0.2, y: boxY - 0.15, w: 0.4, h: 0.4,
        fontFace: F, fontSize: 14, bold: true, color: T.white,
        align: 'center', valign: 'middle', margin: 0,
      });
      // 标签
      slide.addText(st.label, {
        x: bx + 0.1, y: boxY + 0.18, w: boxW - 0.2, h: 0.3,
        fontFace: F, fontSize: 12, bold: true, color: txtC,
        align: 'center', valign: 'middle', margin: 0,
      });
      // 描述
      if (st.desc) {
        slide.addText(st.desc, {
          x: bx + 0.1, y: boxY + 0.48, w: boxW - 0.2, h: boxH - 0.55,
          fontFace: F, fontSize: 9, color: isLast ? T.white : T.muted,
          align: 'center', valign: 'top', margin: [2, 4, 2, 4],
        });
      }
      // 箭头
      if (!isLast) {
        slide.addShape(S.RIGHT_ARROW, {
          x: bx + boxW + 0.02, y: boxY + boxH / 2 - 0.15, w: arrowW - 0.04, h: 0.3,
          fill: { color: T.primary }, line: { type: 'none' },
        });
      }
    });
  }

  // ======================== 3. 金字塔 ========================
  // levels: [{ label, desc }] — 从顶层到底层
  function drawPyramid(slide, x, y, w, h, levels, opts) {
    opts = opts || {};
    const T = getTheme(opts.theme);
    const F = T.fontFace;
    const n = levels.length;
    if (n < 2) return;

    const maxW = w * 0.6;
    const minW = w * 0.15;
    const layerH = h / n;
    const cx = x + w / 2;

    // 颜色渐变：从深到浅（修正：确保第一层最深，逐层变浅）
    const colors = [
      T.primaryDark, T.primary, T.primaryLight, T.accent, T.iceMid, T.iceLight,
    ];

    levels.forEach((lv, i) => {
      const ratio = i / (n - 1);
      const layerW = minW + (maxW - minW) * ratio;
      const ly = y + i * layerH;
      const lx = cx - layerW / 2;
      const isTop = i === 0;
      const fillC = colors[i % colors.length];

      // 梯形层（用RECTANGLE + 透明三角模拟）
      slide.addShape(S.TRAPEZOID, {
        x: lx, y: ly, w: layerW, h: layerH - 0.04,
        fill: { color: fillC }, line: { color: T.white, width: 1.5 },
        shadow: i === 0 ? shadow() : undefined,
      });

      // 文字
      const txtC = isTop || i === 1 ? T.white : T.text;
      slide.addText([
        { text: lv.label, options: { bold: true, fontSize: 12, color: txtC } },
      ], {
        x: lx, y: ly + 0.05, w: layerW, h: layerH * 0.5,
        fontFace: F, align: 'center', valign: 'middle', margin: 0,
      });
      if (lv.desc) {
        slide.addText(lv.desc, {
          x: lx, y: ly + layerH * 0.5, w: layerW, h: layerH * 0.4,
          fontFace: F, fontSize: 9, color: isTop ? 'FFFFFF' : T.muted,
          align: 'center', valign: 'middle', margin: 0,
        });
      }
    });

    // 右侧标注（可选）
    if (opts.sideNote) {
      const sx = x + maxW + 0.45;
      slide.addShape(S.RECTANGLE, {
        x: sx, y: y, w: 0.06, h: h,
        fill: { color: T.primary }, line: { type: 'none' },
      });
      slide.addText(opts.sideNote, {
        x: sx + 0.25, y: y, w: w - maxW - 0.8, h: h,
        fontFace: F, fontSize: 11, color: T.text,
        align: 'left', valign: 'middle', margin: [4, 6, 4, 6],
      });
    }
  }

  // ======================== 4. 循环图 ========================
  // phases: [{ label, desc }] — 3~6个阶段
  function drawCycle(slide, x, y, w, h, phases, opts) {
    opts = opts || {};
    const T = getTheme(opts.theme);
    const F = T.fontFace;
    const n = phases.length;
    if (n < 3) return;

    const cx = x + w / 2;
    const cy = y + h / 2;
    const radius = Math.min(w, h) * 0.32;
    const nodeR = 0.55; // 节点半径

    // 中心圆
    slide.addShape(S.OVAL, {
      x: cx - 0.5, y: cy - 0.5, w: 1.0, h: 1.0,
      fill: { color: T.iceLight }, line: { color: T.primary, width: 1.5 },
    });
    if (opts.centerLabel) {
      slide.addText(opts.centerLabel, {
        x: cx - 0.5, y: cy - 0.5, w: 1.0, h: 1.0,
        fontFace: F, fontSize: 11, bold: true, color: T.primary,
        align: 'center', valign: 'middle', margin: 0,
      });
    }

    phases.forEach((ph, i) => {
      const angle = (i / n) * 2 * Math.PI - Math.PI / 2; // 从顶部开始
      const nx = cx + radius * Math.cos(angle);
      const ny = cy + radius * Math.sin(angle);
      const isOdd = i % 2 === 0;
      const fillC = isOdd ? T.primary : T.primaryLight;

      // 节点圆
      slide.addShape(S.OVAL, {
        x: nx - nodeR, y: ny - nodeR, w: nodeR * 2, h: nodeR * 2,
        fill: { color: fillC }, line: { color: T.white, width: 2 },
        shadow: shadow(),
      });
      // 编号
      slide.addText(String(i + 1), {
        x: nx - nodeR, y: ny - nodeR, w: nodeR * 2, h: nodeR * 2,
        fontFace: F, fontSize: 16, bold: true, color: T.white,
        align: 'center', valign: 'middle', margin: 0,
      });

      // 标签（放在节点外侧）
      const labelDist = nodeR + 0.35;
      const lx = cx + (radius + labelDist) * Math.cos(angle);
      const ly = cy + (radius + labelDist) * Math.sin(angle);
      slide.addText(ph.label, {
        x: lx - 0.8, y: ly - 0.15, w: 1.6, h: 0.3,
        fontFace: F, fontSize: 11, bold: true, color: T.text,
        align: 'center', valign: 'middle', margin: 0,
      });

      // 弧形箭头连接（用弯曲矩形模拟，简化版用短线段）
      if (i < n - 1) {
        const nextAngle = ((i + 1) / n) * 2 * Math.PI - Math.PI / 2;
        const midAngle = (angle + nextAngle) / 2;
        const arcR = radius + 0.1;
        const ax = cx + arcR * Math.cos(midAngle);
        const ay = cy + arcR * Math.sin(midAngle);
        slide.addText('\u21BB', {
          x: ax - 0.15, y: ay - 0.15, w: 0.3, h: 0.3,
          fontFace: F, fontSize: 18, bold: true, color: T.primary,
          align: 'center', valign: 'middle', margin: 0,
        });
      } else {
        // 回到起点的箭头
        const midAngle = (angle + (phases.length > 0 ? -Math.PI / 2 : angle)) / 2;
        const arcR = radius + 0.1;
        const ax = cx + arcR * Math.cos(midAngle);
        const ay = cy + arcR * Math.sin(midAngle);
        slide.addText('\u21BB', {
          x: ax - 0.15, y: ay - 0.15, w: 0.3, h: 0.3,
          fontFace: F, fontSize: 18, bold: true, color: T.primary,
          align: 'center', valign: 'middle', margin: 0,
        });
      }
    });
  }

  // ======================== 5. 总分结构 ========================
  // root: { label }
  // branches: [{ label, desc, items: [str] }]
  function drawTree(slide, x, y, w, h, root, branches, opts) {
    opts = opts || {};
    const T = getTheme(opts.theme);
    const F = T.fontFace;
    const n = branches.length;
    if (n < 2) return;

    const rootW = 2.2, rootH = 0.6;
    const rootX = x + w / 2 - rootW / 2;
    const rootY = y + 0.1;

    // 根节点
    slide.addShape(S.RECTANGLE, {
      x: rootX, y: rootY, w: rootW, h: rootH,
      fill: { color: T.primary }, line: { type: 'none' },
      shadow: shadow(), rectRadius: 0.06,
    });
    slide.addText(root.label, {
      x: rootX, y: rootY, w: rootW, h: rootH,
      fontFace: F, fontSize: 14, bold: true, color: T.white,
      align: 'center', valign: 'middle', margin: 0,
    });

    const branchY = rootY + rootH + 0.5;
    const branchH = h - (branchY - y) - 0.1;
    const gap = 0.25;
    const branchW = (w - gap * (n - 1)) / n;

    branches.forEach((br, i) => {
      const bx = x + i * (branchW + gap);

      // 连线（根→分支）
      slide.addShape(S.RECTANGLE, {
        x: x + w / 2 - 0.01, y: rootY + rootH, w: 0.02, h: 0.25,
        fill: { color: T.border }, line: { type: 'none' },
      });
      slide.addShape(S.RECTANGLE, {
        x: bx + branchW / 2, y: rootY + rootH + 0.25, w: 0.02, h: 0.25,
        fill: { color: T.border }, line: { type: 'none' },
      });

      // 分支卡片
      const fillC = i % 2 === 0 ? T.iceLight : T.white;
      slide.addShape(S.RECTANGLE, {
        x: bx, y: branchY, w: branchW, h: branchH,
        fill: { color: fillC }, line: { color: T.border, width: 1.2 },
        shadow: shadow(), rectRadius: 0.08,
      });
      // 标题栏
      slide.addShape(S.RECTANGLE, {
        x: bx, y: branchY, w: branchW, h: 0.4,
        fill: { color: T.iceMid }, line: { type: 'none' }, rectRadius: 0.08,
      });
      slide.addShape(S.RECTANGLE, {
        x: bx, y: branchY + 0.3, w: branchW, h: 0.1,
        fill: { color: T.iceMid }, line: { type: 'none' },
      });
      slide.addText(br.label, {
        x: bx + 0.1, y: branchY, w: branchW - 0.2, h: 0.4,
        fontFace: F, fontSize: 12, bold: true, color: T.primary,
        align: 'center', valign: 'middle', margin: 0,
      });

      // 子项
      if (br.items) {
        let iy = branchY + 0.5;
        br.items.forEach((item, j) => {
          slide.addShape(S.RECTANGLE, {
            x: bx + 0.15, y: iy + 0.04, w: 0.05, h: 0.05,
            fill: { color: T.primary }, line: { type: 'none' },
          });
          slide.addText(item, {
            x: bx + 0.28, y: iy, w: branchW - 0.4, h: 0.26,
            fontFace: F, fontSize: 10, color: T.text,
            align: 'left', valign: 'middle', margin: 0,
          });
          iy += 0.28;
        });
      }
      // 描述
      if (br.desc && !br.items) {
        slide.addText(br.desc, {
          x: bx + 0.12, y: branchY + 0.5, w: branchW - 0.24, h: branchH - 0.6,
          fontFace: F, fontSize: 10, color: T.muted,
          align: 'left', valign: 'top', margin: [2, 4, 2, 4],
        });
      }
    });
  }

  // ======================== 6. 漏斗图 ========================
  // stages: [{ label, value, pct }] — 从宽到窄
  function drawFunnel(slide, x, y, w, h, stages, opts) {
    opts = opts || {};
    const T = getTheme(opts.theme);
    const F = T.fontFace;
    const n = stages.length;
    if (n < 2) return;

    const maxW = w * 0.85;
    const stageH = h / n;
    const cx = x + w / 2;
    const colors = [T.primary, T.primaryDark, T.primaryLight, T.accent, T.iceMid];

    stages.forEach((st, i) => {
      const ratio = 1 - (i / n) * 0.7;
      const stageW = maxW * ratio;
      const sx = cx - stageW / 2;
      const sy = y + i * stageH;
      const fillC = colors[i % colors.length];

      slide.addShape(S.TRAPEZOID, {
        x: sx, y: sy, w: stageW, h: stageH - 0.06,
        fill: { color: fillC }, line: { color: T.white, width: 1.5 },
      });
      // 标签
      const txtC = i < 2 ? T.white : T.text;
      slide.addText([
        { text: st.label, options: { bold: true, fontSize: 12, color: txtC } },
      ], {
        x: sx, y: sy + 0.04, w: stageW, h: stageH * 0.5,
        fontFace: F, align: 'center', valign: 'middle', margin: 0,
      });
      // 数值
      if (st.value) {
        slide.addText(st.value, {
          x: sx, y: sy + stageH * 0.5, w: stageW, h: stageH * 0.35,
          fontFace: F, fontSize: 10, color: txtC,
          align: 'center', valign: 'middle', margin: 0,
        });
      }
      // 右侧百分比
      if (st.pct) {
        slide.addText(st.pct, {
          x: cx + maxW / 2 + 0.15, y: sy + 0.05, w: 1.2, h: stageH * 0.5,
          fontFace: F, fontSize: 12, bold: true, color: T.primary,
          align: 'left', valign: 'middle', margin: 0,
        });
      }
    });
  }

  // ======================== 7. 殿堂框架 ========================
  // roofText, pillarNames: [str], foundationText
  function drawTemple(slide, x, y, w, h, roofText, pillarNames, foundationText, opts) {
    opts = opts || {};
    const T = getTheme(opts.theme);
    const F = T.fontFace;
    const n = pillarNames.length;
    if (n < 2) return;

    const roofH = 0.65;
    const foundH = 0.6;
    const pillarAreaH = h - roofH - foundH - 0.2;
    const gap = 0.2;
    const pillarW = (w - gap * (n - 1)) / n;

    // 屋顶（梯形）
    slide.addShape(S.TRAPEZOID, {
      x: x + w * 0.05, y, w: w * 0.9, h: roofH,
      fill: { color: T.primary }, line: { type: 'none' },
      shadow: shadow(),
    });
    slide.addText(roofText, {
      x: x + w * 0.05, y, w: w * 0.9, h: roofH,
      fontFace: F, fontSize: 14, bold: true, color: T.white,
      align: 'center', valign: 'middle', margin: 0,
    });

    // 柱子
    pillarNames.forEach((pn, i) => {
      const px = x + i * (pillarW + gap);
      const py = y + roofH + 0.1;
      slide.addShape(S.RECTANGLE, {
        x: px, y: py, w: pillarW, h: pillarAreaH,
        fill: { color: T.white }, line: { color: T.border, width: 1.2 },
        shadow: shadow(), rectRadius: 0.04,
      });
      // 顶部彩色条
      const barColors = [T.primary, T.primaryLight, T.accent, T.primaryDark];
      slide.addShape(S.RECTANGLE, {
        x: px, y: py, w: pillarW, h: 0.08,
        fill: { color: barColors[i % barColors.length] }, line: { type: 'none' },
      });
      slide.addText(pn, {
        x: px + 0.08, y: py + 0.15, w: pillarW - 0.16, h: pillarAreaH - 0.3,
        fontFace: F, fontSize: 12, bold: true, color: T.primary,
        align: 'center', valign: 'middle', margin: [2, 4, 2, 4],
      });
    });

    // 基座
    slide.addShape(S.RECTANGLE, {
      x, y: y + h - foundH, w: w, h: foundH,
      fill: { color: T.primaryDark }, line: { type: 'none' },
      rectRadius: 0.04,
    });
    slide.addText(foundationText, {
      x: x + 0.2, y: y + h - foundH, w: w - 0.4, h: foundH,
      fontFace: F, fontSize: 12, bold: true, color: T.white,
      align: 'center', valign: 'middle', margin: [2, 8, 2, 8],
    });
  }

  // ======================== 8. 垂直步骤 ========================
  // steps: [{ label, desc }]
  function drawVerticalSteps(slide, x, y, w, h, steps, opts) {
    opts = opts || {};
    const T = getTheme(opts.theme);
    const F = T.fontFace;
    const n = steps.length;
    if (n < 2) return;

    const stepH = h / n;
    const nodeR = 0.22;
    const lineX = x + 0.5;

    // 主轴线
    slide.addShape(S.RECTANGLE, {
      x: lineX - 0.02, y: y + nodeR, w: 0.04, h: h - nodeR * 2,
      fill: { color: T.border }, line: { type: 'none' },
    });

    steps.forEach((st, i) => {
      const sy = y + i * stepH + stepH / 2;
      const isLast = i === n - 1;

      // 节点
      slide.addShape(S.OVAL, {
        x: lineX - nodeR, y: sy - nodeR, w: nodeR * 2, h: nodeR * 2,
        fill: { color: isLast ? T.primary : T.white }, line: { color: T.primary, width: 2.5 },
      });
      slide.addText(String(i + 1), {
        x: lineX - nodeR, y: sy - nodeR, w: nodeR * 2, h: nodeR * 2,
        fontFace: F, fontSize: 12, bold: true, color: isLast ? T.white : T.primary,
        align: 'center', valign: 'middle', margin: 0,
      });

      // 内容卡片
      const cardX = lineX + nodeR + 0.3;
      const cardW = x + w - cardX;
      const cardH = stepH * 0.8;
      const cardY = sy - cardH / 2;

      slide.addShape(S.RECTANGLE, {
        x: cardX, y: cardY, w: cardW, h: cardH,
        fill: { color: T.white }, line: { color: T.border, width: 1 },
        shadow: shadow(), rectRadius: 0.06,
      });
      // 左侧色条
      slide.addShape(S.RECTANGLE, {
        x: cardX, y: cardY, w: 0.06, h: cardH,
        fill: { color: T.primary }, line: { type: 'none' },
      });
      // 标签
      slide.addText(st.label, {
        x: cardX + 0.2, y: cardY + 0.06, w: cardW - 0.3, h: 0.3,
        fontFace: F, fontSize: 12, bold: true, color: T.primary,
        align: 'left', valign: 'middle', margin: 0,
      });
      // 描述
      if (st.desc) {
        slide.addText(st.desc, {
          x: cardX + 0.2, y: cardY + 0.36, w: cardW - 0.3, h: cardH - 0.42,
          fontFace: F, fontSize: 10, color: T.muted,
          align: 'left', valign: 'top', margin: [2, 4, 2, 4],
        });
      }
    });
  }

  // ======================== 9. 阶梯进化 ========================
  // steps: [{ label, desc }] — 从低到高
  function drawStaircase(slide, x, y, w, h, steps, opts) {
    opts = opts || {};
    const T = getTheme(opts.theme);
    const F = T.fontFace;
    const n = steps.length;
    if (n < 2) return;

    const maxStepH = h * 0.7;
    const minStepH = h * 0.15;
    const stepW = w / n;
    const baseY = y + h;

    steps.forEach((st, i) => {
      const ratio = i / (n - 1);
      const sH = minStepH + (maxStepH - minStepH) * ratio;
      const sx = x + i * stepW;
      const sy = baseY - sH;
      const isLast = i === n - 1;
      const fillC = isLast ? T.primary : T.iceLight;

      // 阶梯块
      slide.addShape(S.RECTANGLE, {
        x: sx + 0.02, y: sy, w: stepW - 0.08, h: sH,
        fill: { color: fillC }, line: { color: T.primary, width: 1.2 },
        shadow: shadow(), rectRadius: 0,
      });
      // 编号圆
      slide.addShape(S.OVAL, {
        x: sx + stepW / 2 - 0.18, y: sy - 0.18, w: 0.36, h: 0.36,
        fill: { color: T.primary }, line: { color: T.white, width: 2 },
      });
      slide.addText(String(i + 1), {
        x: sx + stepW / 2 - 0.18, y: sy - 0.18, w: 0.36, h: 0.36,
        fontFace: F, fontSize: 12, bold: true, color: T.white,
        align: 'center', valign: 'middle', margin: 0,
      });
      // 标签
      const txtC = isLast ? T.white : T.text;
      slide.addText(st.label, {
        x: sx + 0.05, y: sy + 0.15, w: stepW - 0.15, h: 0.25,
        fontFace: F, fontSize: 11, bold: true, color: txtC,
        align: 'center', valign: 'middle', margin: 0,
      });
      // 描述
      if (st.desc) {
        slide.addText(st.desc, {
          x: sx + 0.05, y: sy + 0.4, w: stepW - 0.15, h: sH - 0.45,
          fontFace: F, fontSize: 9, color: isLast ? T.white : T.muted,
          align: 'center', valign: 'top', margin: [2, 4, 2, 4],
        });
      }
    });

    // 上升箭头
    slide.addShape(S.RIGHT_ARROW, {
      x: x + 0.1, y: y, w: w * 0.3, h: 0.3,
      fill: { color: T.primary }, line: { type: 'none' },
      rotate: -25,
    });
    slide.addText(opts.arrowLabel || '持续进阶', {
      x: x + w * 0.32, y: y - 0.02, w: 2, h: 0.32,
      fontFace: F, fontSize: 11, bold: true, color: T.primary,
      align: 'left', valign: 'middle', margin: 0,
    });
  }

  // ======================== 10. 价值链 ========================
  // stages: [{ label, desc, color }] — 从左到右
  function drawValueChain(slide, x, y, w, h, stages, opts) {
    opts = opts || {};
    const T = getTheme(opts.theme);
    const F = T.fontFace;
    const n = stages.length;
    if (n < 2) return;

    const arrowW = 0.3;
    const totalArrowW = arrowW * (n - 1);
    const stageW = (w - totalArrowW) / n;
    const headerH = 0.4;

    stages.forEach((st, i) => {
      const sx = x + i * (stageW + arrowW);
      const isLast = i === n - 1;
      const accentC = st.color || (i % 2 === 0 ? T.primary : T.primaryLight);

      // 卡片
      slide.addShape(S.RECTANGLE, {
        x: sx, y, w: stageW, h: h,
        fill: { color: T.white }, line: { color: T.border, width: 1.2 },
        shadow: shadow(), rectRadius: 0.08,
      });
      // 顶部彩色条
      slide.addShape(S.RECTANGLE, {
        x: sx + 0.1, y: y + 0.1, w: stageW - 0.2, h: 0.45,
        fill: { color: accentC }, line: { type: 'none' }, rectRadius: 0.04,
      });
      // 阶段编号
      slide.addText(String(i + 1), {
        x: sx + 0.1, y: y + 0.1, w: 0.4, h: 0.45,
        fontFace: F, fontSize: 18, bold: true, color: T.white,
        align: 'center', valign: 'middle', margin: 0,
      });
      // 阶段名
      slide.addText(st.label, {
        x: sx + 0.5, y: y + 0.1, w: stageW - 0.65, h: 0.45,
        fontFace: F, fontSize: 12, bold: true, color: T.white,
        align: 'left', valign: 'middle', margin: 0,
      });
      // 描述
      if (st.desc) {
        slide.addText(st.desc, {
          x: sx + 0.12, y: y + 0.65, w: stageW - 0.24, h: h - 0.75,
          fontFace: F, fontSize: 10, color: T.text,
          align: 'left', valign: 'top', margin: [2, 4, 2, 4],
        });
      }
      // 连接箭头
      if (!isLast) {
        slide.addShape(S.RIGHT_ARROW, {
          x: sx + stageW + 0.02, y: y + h / 2 - 0.15, w: arrowW - 0.04, h: 0.3,
          fill: { color: T.primary }, line: { type: 'none' },
        });
      }
    });
  }

  // ======================== 智能匹配 ========================
  // 分析内容结构，推荐最合适的图形布局
  function recommendLayout(contentItems, context) {
    context = context || {};
    const text = (contentItems.map(function(i) { return i.label + ' ' + (i.desc || ''); }).join(' ')).toLowerCase();
    var scores = {};

    // 时间轴关键词
    if (/\d+月|\d+季度|\d+阶段|先.*再.*最后|时间|历程|里程碑|roadmap|timeline/.test(text)) {
      scores.timeline = 5;
    }
    // 流程关键词
    if (/\u6d41\u7a0b|\u6b65\u9aa4|\u8f93\u5165.*\u5904\u7406.*\u8f93\u51fa|pipeline|\u7ba1\u9053|process/.test(text)) {
      scores.processFlow = 5;
    }
    // 金字塔关键词
    if (/\u603b\u5206|\u5c42\u7ea7|\u5206\u5c42|\u9700\u6c42\u5c42\u6b21|\u9a6c\u65af\u6d1b|\u91d1\u5b57\u5854|hierarchy/.test(text)) {
      scores.pyramid = 5;
    }
    // 循环关键词
    if (/\u5faa\u73af|\u95ed\u73af|pdca|\u6301\u7eed\u4f18\u5316|\u56de\u73af|\u8f6e\u8f6c|\u6b63\u53cd\u9988/.test(text)) {
      scores.cycle = 5;
    }
    // 总分关键词
    if (/\u603b\u4f53|\u603b\u89c8|\u67b6\u6784|\u7ec4\u7ec7|\u5206\u89e3|\u7ed3\u6784\u56fe|\u6811\u5f62|\u603b\u89c8\u56fe/.test(text)) {
      scores.tree = 5;
    }
    // 漏斗关键词
    if (/\u6f0f\u6597|\u8f6c\u5316|\u7b5b\u9009|\u9010\u5c42\u9500\u51cf|\u6f0f\u6597\u5206\u6790|funnel/.test(text)) {
      scores.funnel = 5;
    }
    // 殿堂关键词
    if (/\u57fa\u7840.*\u652f\u67f1.*\u76ee\u6807|\u5e95\u5ea7|\u57fa\u7840\u4fdd\u969c|\u652f\u6491\u4f53\u7cfb|\u4fdd\u969c\u673a\u5236/.test(text)) {
      scores.temple = 5;
    }
    // 垂直步骤关键词
    if (/\u7b2c\u4e00\u6b65.*\u7b2c\u4e8c\u6b65|\u81ea\u4e0a\u800c\u4e0b|\u4e0b\u6c89|\u4e0b\u884c|\u63a8\u8fdb|vertical/.test(text)) {
      scores.verticalSteps = 4;
    }
    // 阶梯关键词
    if (/\u5347\u7ea7|\u8fdb\u9636|\u9010\u6b65\u63d0\u5347|\u8fdb\u5316|\u9636\u68af|staircase|evolution/.test(text)) {
      scores.staircase = 5;
    }
    // 价值链关键词
    if (/\u4ef7\u503c\u94fe|\u4e0a\u6e38.*\u4e0b\u6e38|\u4ea7\u4e1a\u94fe|\u4f9b\u5e94\u94fe|value chain/.test(text)) {
      scores.valueChain = 5;
    }

    // 结构特征加分
    var n = contentItems.length;
    if (n === 2) scores.processFlow = (scores.processFlow || 0) + 2;
    if (n === 3) { scores.cycle = (scores.cycle || 0) + 2; scores.pyramid = (scores.pyramid || 0) + 1; }
    if (n === 4) scores.cycle = (scores.cycle || 0) + 1;
    if (n >= 5) scores.timeline = (scores.timeline || 0) + 1;

    // 找最高分
    var best = null, bestScore = 0;
    for (var k in scores) {
      if (scores[k] > bestScore) { bestScore = scores[k]; best = k; }
    }

    // 默认回退
    if (!best) {
      if (n <= 4) best = 'tree';
      else best = 'timeline';
    }

    return {
      layout: best,
      score: bestScore,
      allScores: scores,
      reason: 'Content structure suggests ' + best + ' layout (score: ' + bestScore + ')',
    };
  }

  // ======================== 导出 ========================
  return {
    drawTimeline: drawTimeline,
    drawProcessFlow: drawProcessFlow,
    drawPyramid: drawPyramid,
    drawCycle: drawCycle,
    drawTree: drawTree,
    drawFunnel: drawFunnel,
    drawTemple: drawTemple,
    drawVerticalSteps: drawVerticalSteps,
    drawStaircase: drawStaircase,
    drawValueChain: drawValueChain,
    recommendLayout: recommendLayout,
    getTheme: getTheme,
    THEMES: THEMES,
  };
}

module.exports = { create: create };
