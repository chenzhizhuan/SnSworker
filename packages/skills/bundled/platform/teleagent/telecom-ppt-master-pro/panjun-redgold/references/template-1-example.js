const PptxGenJS = require('pptxgenjs');
const path = require('path');

const pres = new PptxGenJS();

// Theme - 党课红金风格 C2
const theme = {
  primary: 'C00000',
  primaryDark: '8B0000',
  gold: 'D4AF37',
  goldLight: 'F5DC8A',
  white: 'FFFFFF',
  warmWhite: 'FFF8F0',
  lightGray: 'F5F5F5',
  darkGray: '2C2C2C',
  mediumGray: '666666',
  borderGray: 'E0E0E0',
};

pres.defineLayout({ name: 'LAYOUT_16x9', width: 10, height: 7.5 });
pres.layout = 'LAYOUT_16x9';

const FONT = 'Microsoft YaHei';
const imgDir = path.join(__dirname, '..', 'images');

// ===== Helper Functions =====

function addHeaderBar(slide) {
  slide.addShape('rect', { x: 0, y: 0, w: 10, h: 0.08, fill: { color: theme.primary } });
}

function addFooterBar(slide) {
  slide.addShape('rect', { x: 0, y: 7.2, w: 10, h: 0.04, fill: { color: theme.gold } });
}

function addPageNumber(slide, num) {
  slide.addText(String(num), {
    x: 9.3, y: 6.95, w: 0.5, h: 0.25,
    fontSize: 10, color: theme.mediumGray, align: 'right', fontFace: FONT
  });
}

function addSectionTitle(slide, num, title) {
  slide.addShape('roundRect', {
    x: 0.6, y: 0.4, w: 0.55, h: 0.55,
    fill: { color: theme.gold }, rectRadius: 0.08, line: { color: theme.gold, width: 1 }
  });
  slide.addText(String(num), {
    x: 0.6, y: 0.4, w: 0.55, h: 0.55,
    fontSize: 28, color: theme.white, bold: true, align: 'center', valign: 'middle', fontFace: FONT
  });
  slide.addText(title, {
    x: 1.3, y: 0.4, w: 7, h: 0.55,
    fontSize: 28, color: theme.primary, bold: true, align: 'left', valign: 'middle', fontFace: FONT
  });
  slide.addShape('rect', { x: 1.3, y: 1.0, w: 7, h: 0.03, fill: { color: theme.gold } });
}

// ===== Slide 1: 封面页 =====
function slide1() {
  const slide = pres.addSlide();
  slide.background = { color: theme.primaryDark };
  slide.addImage({ path: path.join(imgDir, 'cover-bg.jpg'), x: 0, y: 0, w: 10, h: 7.5 });
  slide.addShape('rect', { x: 0, y: 0, w: 10, h: 7.5, fill: { color: theme.primaryDark, transparency: 30 } });
  slide.addText('深学笃行习近平党建思想', {
    x: 0.8, y: 2.0, w: 8.4, h: 1.2,
    fontSize: 44, color: theme.white, bold: true, align: 'center', fontFace: FONT
  });
  slide.addText('学习贯彻2026年全国党建工作座谈会精神', {
    x: 0.8, y: 3.3, w: 8.4, h: 0.8,
    fontSize: 24, color: theme.goldLight, bold: true, align: 'center', fontFace: FONT
  });
  slide.addShape('rect', { x: 3.5, y: 4.3, w: 3, h: 0.04, fill: { color: theme.gold } });
  slide.addText('2026年8月', {
    x: 0.8, y: 5.0, w: 8.4, h: 0.5,
    fontSize: 18, color: theme.goldLight, align: 'center', fontFace: FONT
  });
  slide.addShape('rect', { x: 0, y: 7.2, w: 10, h: 0.06, fill: { color: theme.gold } });
}

// ===== Slide 2: 目录页 =====
function slide2() {
  const slide = pres.addSlide();
  slide.background = { color: theme.white };
  addHeaderBar(slide); addFooterBar(slide); addPageNumber(slide, 2);
  slide.addText('目  录', {
    x: 0.6, y: 0.3, w: 8.8, h: 0.7,
    fontSize: 32, color: theme.primary, bold: true, align: 'center', fontFace: FONT
  });
  slide.addShape('rect', { x: 4.2, y: 1.05, w: 1.6, h: 0.03, fill: { color: theme.gold } });
  const items = [
    { num: '01', title: '习近平党建思想的重大意义', desc: '马克思主义建党学说的最新成果' },
    { num: '02', title: '"十四个坚持"的科学内涵', desc: '习近平党建思想的核心要义' },
    { num: '03', title: '贯彻落实的思路与举措', desc: '推动党建思想入耳入脑入心' },
    { num: '04', title: '当前学习要点与行动倡议', desc: '结合时事 践行使命' },
  ];
  items.forEach((item, i) => {
    const y = 1.5 + i * 1.35;
    slide.addShape('roundRect', {
      x: 1.2, y: y, w: 0.7, h: 0.7,
      fill: { color: theme.gold }, rectRadius: 0.06, line: { color: theme.goldLight, width: 1 }
    });
    slide.addText(item.num, {
      x: 1.2, y: y, w: 0.7, h: 0.7,
      fontSize: 22, color: theme.white, bold: true, align: 'center', valign: 'middle', fontFace: FONT
    });
    slide.addText(item.title, {
      x: 2.1, y: y, w: 6.5, h: 0.4,
      fontSize: 20, color: theme.primary, bold: true, valign: 'middle', fontFace: FONT
    });
    slide.addText(item.desc, {
      x: 2.1, y: y + 0.4, w: 6.5, h: 0.3,
      fontSize: 14, color: theme.mediumGray, valign: 'middle', fontFace: FONT
    });
  });
}

// ===== Slide 3: 第一章节过渡 =====
function slide3() {
  const slide = pres.addSlide();
  slide.background = { color: theme.primaryDark };
  slide.addImage({ path: path.join(imgDir, 'theory-scroll.jpg'), x: 5.5, y: 1.0, w: 4, h: 3.5 });
  slide.addText('01', { x: 0.6, y: 1.8, w: 1.5, h: 1.0, fontSize: 72, color: theme.gold, bold: true, fontFace: FONT });
  slide.addShape('rect', { x: 0.6, y: 3.0, w: 2, h: 0.04, fill: { color: theme.gold } });
  slide.addText('习近平党建思想的\n重大意义', {
    x: 0.6, y: 3.3, w: 5, h: 1.5,
    fontSize: 36, color: theme.white, bold: true, fontFace: FONT, lineSpacing: 48
  });
  slide.addShape('rect', { x: 0, y: 7.2, w: 10, h: 0.06, fill: { color: theme.gold } });
}

// ===== Slide 4: 第一章节内容1 =====
function slide4() {
  const slide = pres.addSlide();
  slide.background = { color: theme.white };
  addHeaderBar(slide); addFooterBar(slide); addPageNumber(slide, 4);
  addSectionTitle(slide, 1, '习近平党建思想的重大意义');
  const items = [
    { title: '坚持发展马克思主义建党学说', desc: '结合长期执政大国政党实际，丰富发展马克思主义建党学说' },
    { title: '继承发展毛泽东建党思想', desc: '在改革开放和市场经济条件下丰富发展毛泽东建党思想' },
    { title: '丰富发展习近平新时代中国特色社会主义思想', desc: '作为重要组成部分，完善新时代党的指导思想体系' },
    { title: '百年大党管党治党的根本遵循', desc: '为中华民族伟大复兴提供坚强领导力量' },
  ];
  items.forEach((item, i) => {
    const y = 1.3 + i * 1.35;
    slide.addShape('ellipse', { x: 0.6, y: y, w: 0.35, h: 0.35, fill: { color: theme.gold }, line: { color: theme.gold, width: 1 } });
    slide.addText(String(i + 1), { x: 0.6, y: y, w: 0.35, h: 0.35, fontSize: 14, color: theme.white, bold: true, align: 'center', valign: 'middle', fontFace: FONT });
    slide.addText(item.title, { x: 1.1, y: y - 0.05, w: 5, h: 0.4, fontSize: 18, color: theme.primary, bold: true, valign: 'middle', fontFace: FONT });
    slide.addText(item.desc, { x: 1.1, y: y + 0.35, w: 5, h: 0.4, fontSize: 14, color: theme.darkGray, valign: 'middle', fontFace: FONT });
  });
  slide.addImage({ path: path.join(imgDir, 'theory-scroll.jpg'), x: 6.5, y: 1.5, w: 3, h: 2.5 });
  slide.addShape('roundRect', { x: 6.5, y: 4.2, w: 3, h: 2.2, fill: { color: theme.warmWhite }, rectRadius: 0.05, line: { color: theme.borderGray, width: 1 } });
  slide.addText('时间脉络', { x: 6.7, y: 4.3, w: 2.6, h: 0.35, fontSize: 14, color: theme.gold, bold: true, fontFace: FONT });
  slide.addText([
    { text: '2023.06 ', options: { bold: true, color: theme.primary } },
    { text: '全国组织工作会议\n首次系统阐述', options: { color: theme.darkGray } },
    { text: '\n2025.01 ', options: { bold: true, color: theme.primary } },
    { text: '《概论》出版', options: { color: theme.darkGray } },
    { text: '\n2026.06 ', options: { bold: true, color: theme.primary } },
    { text: '全国党建工作座谈会\n提出"十四个坚持"', options: { color: theme.darkGray } },
  ], { x: 6.7, y: 4.7, w: 2.6, h: 1.5, fontSize: 13, fontFace: FONT, lineSpacing: 20 });
}

// ===== Slide 5: 第一章节内容2 =====
function slide5() {
  const slide = pres.addSlide();
  slide.background = { color: theme.white };
  addHeaderBar(slide); addFooterBar(slide); addPageNumber(slide, 5);
  addSectionTitle(slide, 1, '理论定位与里程碑意义');
  const cards = [
    { title: '马克思主义建党学说\n新发展', desc: '坚持意识形态领域斗争\n坚持党的全面领导\n推进全面从严治党' },
    { title: '毛泽东建党思想\n新继承', desc: '坚持党的全面领导\n加强纪律建设\n加强作风建设\n加强理论武装' },
    { title: '习近平新时代中国特色社会主义思想\n新贡献', desc: '完善新时代党的指导思想\n为民族复兴提供根本遵循\n强大政党领导保证' },
  ];
  cards.forEach((card, i) => {
    const x = 0.6 + i * 3.1;
    slide.addShape('roundRect', { x: x, y: 1.3, w: 2.9, h: 5.0, fill: { color: theme.warmWhite }, rectRadius: 0.05, line: { color: theme.borderGray, width: 1 } });
    slide.addShape('roundRect', { x: x, y: 1.3, w: 2.9, h: 0.7, fill: { color: theme.primary }, rectRadius: 0.05, line: { color: theme.primary, width: 1 } });
    slide.addText(card.title, { x: x + 0.15, y: 1.3, w: 2.6, h: 0.7, fontSize: 15, color: theme.white, bold: true, align: 'center', valign: 'middle', fontFace: FONT, lineSpacing: 18 });
    slide.addText(card.desc, { x: x + 0.2, y: 2.2, w: 2.5, h: 3.0, fontSize: 14, color: theme.darkGray, fontFace: FONT, lineSpacing: 24, valign: 'top' });
    slide.addShape('rect', { x: x + 0.5, y: 5.8, w: 1.9, h: 0.03, fill: { color: theme.gold } });
  });
}

// ===== Slide 6: 第二章节过渡 =====
function slide6() {
  const slide = pres.addSlide();
  slide.background = { color: theme.primaryDark };
  slide.addImage({ path: path.join(imgDir, '初心-heart.jpg'), x: 5.5, y: 1.0, w: 4, h: 3.5 });
  slide.addText('02', { x: 0.6, y: 1.8, w: 1.5, h: 1.0, fontSize: 72, color: theme.gold, bold: true, fontFace: FONT });
  slide.addShape('rect', { x: 0.6, y: 3.0, w: 2, h: 0.04, fill: { color: theme.gold } });
  slide.addText('"十四个坚持"\n的科学内涵', { x: 0.6, y: 3.3, w: 5, h: 1.5, fontSize: 36, color: theme.white, bold: true, fontFace: FONT, lineSpacing: 48 });
  slide.addShape('rect', { x: 0, y: 7.2, w: 10, h: 0.06, fill: { color: theme.gold } });
}

// ===== Slide 7: 第二章节内容1 - 十四个坚持(1-7) =====
function slide7() {
  const slide = pres.addSlide();
  slide.background = { color: theme.white };
  addHeaderBar(slide); addFooterBar(slide); addPageNumber(slide, 7);
  addSectionTitle(slide, 2, '"十四个坚持"（上）');
  const items = [
    '坚持党的领导是中国特色社会主义最本质特征',
    '坚持党中央集中统一领导',
    '坚持全面从严治党',
    '坚持不忘初心、牢记使命',
    '坚持以党的政治建设为统领',
    '坚持用党的创新理论凝心铸魂',
    '坚持锤炼坚强党性',
  ];
  items.forEach((item, i) => {
    const col = i < 4 ? 0 : 1;
    const row = i < 4 ? i : i - 4;
    const x = 0.6 + col * 4.7;
    const y = 1.3 + row * 1.35;
    slide.addShape('roundRect', { x: x, y: y, w: 0.5, h: 0.5, fill: { color: theme.primary }, rectRadius: 0.04 });
    slide.addText(String(i + 1), { x: x, y: y, w: 0.5, h: 0.5, fontSize: 18, color: theme.white, bold: true, align: 'center', valign: 'middle', fontFace: FONT });
    slide.addText(item, { x: x + 0.65, y: y, w: 3.8, h: 0.5, fontSize: 15, color: theme.darkGray, valign: 'middle', fontFace: FONT });
    if (row < 3) { slide.addShape('rect', { x: x + 0.65, y: y + 0.6, w: 3.8, h: 0.02, fill: { color: theme.borderGray } }); }
  });
}

// ===== Slide 8: 第二章节内容2 - 十四个坚持(8-14) =====
function slide8() {
  const slide = pres.addSlide();
  slide.background = { color: theme.white };
  addHeaderBar(slide); addFooterBar(slide); addPageNumber(slide, 8);
  addSectionTitle(slide, 2, '"十四个坚持"（下）');
  const items = [
    '坚持健全上下贯通、执行有力的组织体系',
    '坚持建设堪当民族复兴重任的高素质干部队伍',
    '坚持推进作风建设常态化长效化',
    '坚持用严明的纪律管全党治全党',
    '坚持一体推进不敢腐不能腐不想腐',
    '坚持制度治党、依规治党',
    '坚持落实管党治党政治责任',
  ];
  items.forEach((item, i) => {
    const col = i < 4 ? 0 : 1;
    const row = i < 4 ? i : i - 4;
    const x = 0.6 + col * 4.7;
    const y = 1.3 + row * 1.35;
    slide.addShape('roundRect', { x: x, y: y, w: 0.5, h: 0.5, fill: { color: theme.gold }, rectRadius: 0.04 });
    slide.addText(String(i + 8), { x: x, y: y, w: 0.5, h: 0.5, fontSize: 16, color: theme.white, bold: true, align: 'center', valign: 'middle', fontFace: FONT });
    slide.addText(item, { x: x + 0.65, y: y, w: 3.8, h: 0.5, fontSize: 15, color: theme.darkGray, valign: 'middle', fontFace: FONT });
    if (row < 3) { slide.addShape('rect', { x: x + 0.65, y: y + 0.6, w: 3.8, h: 0.02, fill: { color: theme.borderGray } }); }
  });
}

// ===== Slide 9: 第三章节过渡 =====
function slide9() {
  const slide = pres.addSlide();
  slide.background = { color: theme.primaryDark };
  slide.addImage({ path: path.join(imgDir, '治党-shield.jpg'), x: 5.5, y: 1.0, w: 4, h: 3.5 });
  slide.addText('03', { x: 0.6, y: 1.8, w: 1.5, h: 1.0, fontSize: 72, color: theme.gold, bold: true, fontFace: FONT });
  slide.addShape('rect', { x: 0.6, y: 3.0, w: 2, h: 0.04, fill: { color: theme.gold } });
  slide.addText('贯彻落实的\n思路与举措', { x: 0.6, y: 3.3, w: 5, h: 1.5, fontSize: 36, color: theme.white, bold: true, fontFace: FONT, lineSpacing: 48 });
  slide.addShape('rect', { x: 0, y: 7.2, w: 10, h: 0.06, fill: { color: theme.gold } });
}

// ===== Slide 10: 第三章节内容1 - 贯彻落实四条思路 =====
function slide10() {
  const slide = pres.addSlide();
  slide.background = { color: theme.white };
  addHeaderBar(slide); addFooterBar(slide); addPageNumber(slide, 10);
  addSectionTitle(slide, 3, '贯彻落实的四条思路');
  const items = [
    { num: '一', title: '学深悟透，加强党性修养', desc: '坚定"四个自信"，用党的创新理论武装头脑\n指导改革发展实践，发挥制度优势' },
    { num: '二', title: '推动理论入耳入脑入心', desc: '转化为故事、数据、案例\n运用互联网、新媒体、AR体验等创新手段\n加强"五史"基础教育' },
    { num: '三', title: '加强党风廉政建设和反腐败斗争', desc: '健全制度建设，明确纪律"红线"\n强化监督执纪问责\n树立正面典型，激励廉洁干部' },
    { num: '四', title: '推进党建工作创新', desc: '打造党建品牌，以高质量党建引领\n企业高质量发展\n发挥优秀创新案例示范带动作用' },
  ];
  items.forEach((item, i) => {
    const y = 1.3 + i * 1.35;
    slide.addShape('ellipse', { x: 0.6, y: y + 0.1, w: 0.5, h: 0.5, fill: { color: theme.gold }, line: { color: theme.gold, width: 1 } });
    slide.addText(item.num, { x: 0.6, y: y + 0.1, w: 0.5, h: 0.5, fontSize: 18, color: theme.white, bold: true, align: 'center', valign: 'middle', fontFace: FONT });
    slide.addText(item.title, { x: 1.3, y: y, w: 3.5, h: 0.4, fontSize: 18, color: theme.primary, bold: true, valign: 'middle', fontFace: FONT });
    slide.addText(item.desc, { x: 1.3, y: y + 0.4, w: 3.5, h: 0.8, fontSize: 13, color: theme.darkGray, valign: 'top', fontFace: FONT, lineSpacing: 18 });
    if (i < 3) { slide.addShape('rect', { x: 0.6, y: y + 1.2, w: 8.8, h: 0.02, fill: { color: theme.borderGray } }); }
  });
}

// ===== Slide 11: 第三章节内容2 - 全面从严治党五大体系表格 =====
function slide11() {
  const slide = pres.addSlide();
  slide.background = { color: theme.white };
  addHeaderBar(slide); addFooterBar(slide); addPageNumber(slide, 11);
  addSectionTitle(slide, 3, '全面从严治党五大体系');
  const rows = [
    ['体系名称', '核心要求', '建设重点'],
    ['组织体系', '上下贯通、执行有力', '建立横向到边、纵向到底的组织体系\n大抓基层党建，加强带头人队伍建设'],
    ['教育体系', '固本培元、凝心铸魂', '加强党性教育，坚定理想信念\n用党的创新理论武装头脑'],
    ['监管体系', '精准发力、标本兼治', '整合监督资源，形成监督合力\n强化日常监督和专项监督'],
    ['制度体系', '科学完备、有效管用', '完善党内法规，增强权威性\n严格落实各项制度规定'],
    ['责任体系', '主体明确、要求清晰', '落实"一岗双责"，明确各级责任\n以严肃问责推动责任落实落地'],
  ];
  const colW = [2.0, 2.8, 4.0];
  const startX = 0.6, startY = 1.3, rowH = 0.95;
  rows.forEach((row, ri) => {
    const isHeader = ri === 0;
    row.forEach((cell, ci) => {
      const x = startX + colW.slice(0, ci).reduce((a, b) => a + b, 0);
      slide.addShape('rect', {
        x: x, y: startY + ri * rowH, w: colW[ci], h: rowH,
        fill: { color: isHeader ? theme.primary : (ri % 2 === 0 ? theme.warmWhite : theme.white) },
        line: { color: theme.borderGray, width: 1 }
      });
      slide.addText(cell, {
        x: x + 0.1, y: startY + ri * rowH, w: colW[ci] - 0.2, h: rowH,
        fontSize: isHeader ? 14 : 13,
        color: isHeader ? theme.white : theme.darkGray,
        bold: isHeader,
        align: 'center', valign: 'middle', fontFace: FONT, lineSpacing: 18
      });
    });
  });
}

// ===== Slide 12: 第四章节过渡 =====
function slide12() {
  const slide = pres.addSlide();
  slide.background = { color: theme.primaryDark };
  slide.addImage({ path: path.join(imgDir, '担当-sunrise.jpg'), x: 5.5, y: 1.0, w: 4, h: 3.5 });
  slide.addText('04', { x: 0.6, y: 1.8, w: 1.5, h: 1.0, fontSize: 72, color: theme.gold, bold: true, fontFace: FONT });
  slide.addShape('rect', { x: 0.6, y: 3.0, w: 2, h: 0.04, fill: { color: theme.gold } });
  slide.addText('当前学习要点\n与行动倡议', { x: 0.6, y: 3.3, w: 5, h: 1.5, fontSize: 36, color: theme.white, bold: true, fontFace: FONT, lineSpacing: 48 });
  slide.addShape('rect', { x: 0, y: 7.2, w: 10, h: 0.06, fill: { color: theme.gold } });
}

// ===== Slide 13: 第四章节内容1 - 2026年8月学习要点 =====
function slide13() {
  const slide = pres.addSlide();
  slide.background = { color: theme.white };
  addHeaderBar(slide); addFooterBar(slide); addPageNumber(slide, 13);
  addSectionTitle(slide, 4, '2026年8月学习要点');
  const items = [
    { title: '习近平总书记最新重要讲话', desc: '《求是》文章《加快建设健康中国》\n党外人士座谈会关于下半年经济工作讲话\n《习近平关于基层工作方法论述摘编》' },
    { title: '学习贯彻习近平党建思想', desc: '全国党建工作座谈会精神\n深刻领会"十四个坚持"\n将学习成果转化为自觉行动' },
    { title: '党纪学习教育持续深化', desc: '学纪、知纪、明纪、守纪\n推动教育、监督、执纪、问责一体化\n坚持正风肃纪反腐相贯通' },
  ];
  items.forEach((item, i) => {
    const x = 0.6 + i * 3.1;
    slide.addShape('roundRect', { x: x, y: 1.3, w: 2.9, h: 5.0, fill: { color: theme.warmWhite }, rectRadius: 0.05, line: { color: theme.borderGray, width: 1 } });
    slide.addShape('roundRect', { x: x, y: 1.3, w: 2.9, h: 0.7, fill: { color: theme.gold }, rectRadius: 0.05 });
    slide.addText(item.title, { x: x + 0.15, y: 1.3, w: 2.6, h: 0.7, fontSize: 15, color: theme.white, bold: true, align: 'center', valign: 'middle', fontFace: FONT });
    slide.addText(item.desc, { x: x + 0.2, y: 2.2, w: 2.5, h: 3.5, fontSize: 14, color: theme.darkGray, fontFace: FONT, lineSpacing: 22, valign: 'top' });
  });
}

// ===== Slide 14: 第四章节内容2 - 党员行动倡议 =====
function slide14() {
  const slide = pres.addSlide();
  slide.background = { color: theme.white };
  addHeaderBar(slide); addFooterBar(slide); addPageNumber(slide, 14);
  addSectionTitle(slide, 4, '党员行动倡议');
  const items = [
    { num: '1', title: '带头学习领学促学', desc: '党员领导干部带头参加所在党支部学习交流\n发挥领学带学促学作用' },
    { num: '2', title: '结合实际践行使命', desc: '结合防汛救灾、乡村振兴等重点任务\n发挥先锋模范作用，冲锋在前' },
    { num: '3', title: '深入基层服务群众', desc: '深入农村、社区、企业\n聚焦党建引领基层治理\n开展志愿服务，为民办实事' },
    { num: '4', title: '赓续红色血脉', desc: '结合建军99周年\n学习习近平强军思想\n充分利用红色资源优势' },
    { num: '5', title: '按时足额交纳党费', desc: '自觉足额交纳8月份党费\n党组织及时提醒未交纳党员' },
    { num: '6', title: '推进党建品牌建设', desc: '将党建品牌与企业品牌结合\n以高质量党建引领高质量发展' },
  ];
  items.forEach((item, i) => {
    const col = i < 3 ? 0 : 1;
    const row = i < 3 ? i : i - 3;
    const x = 0.6 + col * 4.7;
    const y = 1.3 + row * 1.85;
    slide.addShape('roundRect', { x: x, y: y, w: 0.55, h: 0.55, fill: { color: theme.primary }, rectRadius: 0.04 });
    slide.addText(item.num, { x: x, y: y, w: 0.55, h: 0.55, fontSize: 20, color: theme.white, bold: true, align: 'center', valign: 'middle', fontFace: FONT });
    slide.addText(item.title, { x: x + 0.7, y: y, w: 3.8, h: 0.4, fontSize: 16, color: theme.primary, bold: true, valign: 'middle', fontFace: FONT });
    slide.addText(item.desc, { x: x + 0.7, y: y + 0.4, w: 3.8, h: 0.8, fontSize: 12, color: theme.darkGray, valign: 'top', fontFace: FONT, lineSpacing: 18 });
  });
}

// ===== Slide 15: 总结页 =====
function slide15() {
  const slide = pres.addSlide();
  slide.background = { color: theme.primary };
  addPageNumber(slide, 15);
  slide.addText('总  结', { x: 0.6, y: 0.5, w: 8.8, h: 0.8, fontSize: 36, color: theme.white, bold: true, align: 'center', fontFace: FONT });
  slide.addShape('rect', { x: 4.2, y: 1.4, w: 1.6, h: 0.04, fill: { color: theme.gold } });
  const items = [
    '习近平党建思想是马克思主义建党学说的最新成果，是新时代党的建设的根本遵循',
    '"十四个坚持"构建完整的科学体系，涵盖党的领导、政治建设、思想建设、组织建设、作风建设、纪律建设、反腐败斗争、制度建设等各方面',
    '学习贯彻习近平党建思想是当前和今后一个时期的重要政治任务，要做到学深悟透、入耳入脑入心',
    '结合2026年8月最新学习要点，将学习成果转化为推动工作的强大力量',
  ];
  items.forEach((item, i) => {
    const y = 1.8 + i * 1.25;
    slide.addShape('ellipse', { x: 0.8, y: y + 0.1, w: 0.3, h: 0.3, fill: { color: theme.gold }, line: { color: theme.gold, width: 1 } });
    slide.addText(String(i + 1), { x: 0.8, y: y + 0.1, w: 0.3, h: 0.3, fontSize: 12, color: theme.primaryDark, bold: true, align: 'center', valign: 'middle', fontFace: FONT });
    slide.addText(item, { x: 1.3, y: y, w: 7.8, h: 1.0, fontSize: 16, color: theme.white, valign: 'top', fontFace: FONT, lineSpacing: 24 });
  });
  slide.addShape('rect', { x: 0, y: 7.2, w: 10, h: 0.06, fill: { color: theme.gold } });
}

// ===== Slide 16: 行动倡议页 =====
function slide16() {
  const slide = pres.addSlide();
  slide.background = { color: theme.warmWhite };
  addPageNumber(slide, 16);
  slide.addShape('rect', { x: 0.3, y: 0.3, w: 9.4, h: 0.04, fill: { color: theme.gold } });
  slide.addShape('rect', { x: 0.3, y: 0.3, w: 0.04, h: 6.6, fill: { color: theme.gold } });
  slide.addShape('rect', { x: 9.66, y: 0.3, w: 0.04, h: 6.6, fill: { color: theme.gold } });
  slide.addShape('rect', { x: 0.3, y: 6.86, w: 9.4, h: 0.04, fill: { color: theme.gold } });
  slide.addText('行动倡议', { x: 1, y: 1.0, w: 8, h: 0.8, fontSize: 32, color: theme.primary, bold: true, align: 'center', fontFace: FONT });
  slide.addShape('rect', { x: 4.2, y: 1.9, w: 1.6, h: 0.03, fill: { color: theme.gold } });
  slide.addText('让我们以习近平党建思想为指引\n坚持党要管党、全面从严治党\n将学习成果转化为坚定信仰、锤炼党性\n转化为指导实践、推动工作的强大力量\n\n以高质量党建引领高质量发展\n为实现中华民族伟大复兴贡献力量', {
    x: 1.5, y: 2.5, w: 7, h: 3.5,
    fontSize: 20, color: theme.darkGray, align: 'center', valign: 'middle', fontFace: FONT, lineSpacing: 36
  });
}

// ===== Slide 17: 金句引用页 =====
function slide17() {
  const slide = pres.addSlide();
  slide.background = { color: theme.primaryDark };
  addPageNumber(slide, 17);
  slide.addText('"', { x: 0.8, y: 0.8, w: 1.5, h: 1.5, fontSize: 120, color: theme.gold, bold: true, fontFace: 'Georgia' });
  slide.addText('江山就是人民，人民就是江山\n打江山、守江山\n守的是人民的心', {
    x: 2.0, y: 2.0, w: 7.0, h: 2.5,
    fontSize: 28, color: theme.white, bold: true, align: 'center', valign: 'middle', fontFace: FONT, lineSpacing: 44
  });
  slide.addShape('rect', { x: 3.5, y: 4.8, w: 3, h: 0.03, fill: { color: theme.gold } });
  slide.addText('—— 习近平', { x: 2.0, y: 5.0, w: 7.0, h: 0.6, fontSize: 18, color: theme.goldLight, align: 'center', fontFace: FONT });
  slide.addShape('rect', { x: 0, y: 7.2, w: 10, h: 0.06, fill: { color: theme.gold } });
}

// ===== Slide 18: 数据成果页 =====
function slide18() {
  const slide = pres.addSlide();
  slide.background = { color: theme.white };
  addHeaderBar(slide); addFooterBar(slide); addPageNumber(slide, 18);
  addSectionTitle(slide, 4, '学习成果与展望');
  const cards = [
    { num: '14', unit: '个坚持', label: '习近平党建思想\n科学体系' },
    { num: '5', unit: '大体系', label: '全面从严治党\n制度保障' },
    { num: '33', unit: '个', label: '党建工作座谈会\n里程碑意义' },
  ];
  cards.forEach((card, i) => {
    const x = 0.8 + i * 3.1;
    slide.addShape('roundRect', { x: x, y: 1.5, w: 2.7, h: 4.5, fill: { color: theme.warmWhite }, rectRadius: 0.05, line: { color: theme.borderGray, width: 1 } });
    slide.addText(card.num, { x: x, y: 1.8, w: 2.7, h: 1.8, fontSize: 80, color: theme.gold, bold: true, align: 'center', valign: 'middle', fontFace: FONT });
    slide.addText(card.unit, { x: x, y: 3.6, w: 2.7, h: 0.5, fontSize: 20, color: theme.primary, bold: true, align: 'center', fontFace: FONT });
    slide.addShape('rect', { x: x + 0.8, y: 4.2, w: 1.1, h: 0.03, fill: { color: theme.gold } });
    slide.addText(card.label, { x: x + 0.2, y: 4.5, w: 2.3, h: 1.2, fontSize: 15, color: theme.darkGray, align: 'center', valign: 'top', fontFace: FONT, lineSpacing: 22 });
  });
}

// ===== Slide 19: 结尾页 =====
function slide19() {
  const slide = pres.addSlide();
  slide.background = { color: theme.primaryDark };
  slide.addText('感 谢 聆 听', { x: 0.5, y: 2.5, w: 9, h: 1.5, fontSize: 52, color: theme.white, bold: true, align: 'center', valign: 'middle', fontFace: FONT });
  slide.addShape('rect', { x: 3.5, y: 4.2, w: 3, h: 0.04, fill: { color: theme.gold } });
  slide.addText('深学笃行 久久为功', { x: 0.5, y: 4.5, w: 9, h: 0.8, fontSize: 24, color: theme.goldLight, align: 'center', fontFace: FONT });
  slide.addShape('rect', { x: 0, y: 7.2, w: 10, h: 0.06, fill: { color: theme.gold } });
}

// ===== Slide 20: 封底页 =====
function slide20() {
  const slide = pres.addSlide();
  slide.background = { color: theme.primaryDark };
  slide.addShape('rect', { x: 0, y: 7.2, w: 10, h: 0.06, fill: { color: theme.gold } });
  slide.addText('2026年8月', { x: 1, y: 2.5, w: 8, h: 0.8, fontSize: 24, color: theme.goldLight, align: 'center', fontFace: FONT });
  slide.addText('学习贯彻习近平党建思想', { x: 1, y: 3.5, w: 8, h: 0.8, fontSize: 20, color: theme.white, align: 'center', fontFace: FONT });
  slide.addShape('rect', { x: 4, y: 4.5, w: 2, h: 0.03, fill: { color: theme.gold } });
  slide.addText('党 课  PPT', { x: 1, y: 4.8, w: 8, h: 0.6, fontSize: 16, color: theme.mediumGray, align: 'center', fontFace: FONT });
}

// ===== Build All Slides =====
slide1(); slide2(); slide3(); slide4(); slide5();
slide6(); slide7(); slide8(); slide9(); slide10();
slide11(); slide12(); slide13(); slide14(); slide15();
slide16(); slide17(); slide18(); slide19(); slide20();

const outputPath = path.join(__dirname, '..', '..', '深学笃行习近平党建思想-党课PPT.pptx');
pres.writeFile({ fileName: outputPath }).then(() => {
  console.log('PPT generated: ' + outputPath);
}).catch(err => {
  console.error('Error:', err);
});
