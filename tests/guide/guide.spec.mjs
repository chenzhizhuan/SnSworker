#!/usr/bin/env node
/**
 * 智算方舟桌面端使用指南 · 全功能单元测试
 * ------------------------------------------------------------------
 * 目标：user-guide.html（静态单页指南）
 * 运行：node tests/guide/guide.spec.mjs
 *   可用环境变量：
 *     GUIDE_URL  被测页面地址（默认 http://127.0.0.1:18925/user-guide.html）
 *     CHROME_EXE 浏览器路径（默认系统 Chrome，找不到时回退 playwright 内置）
 *
 * 覆盖组：
 *   T1  结构完整性（章节/FIG 序/内容口径）
 *   T2  导航结构（左栏 + 顶栏锚点）
 *   T3  滚动高亮（JS 导航联动）
 *   T4  锚点跳转（桌面无遮挡 / 手机不被吸顶导航遮住）
 *   T5  FAQ 折叠面板交互
 *   T6  资源加载（图片 + 控制台零错误）
 *   T7  响应式断点（375 手机 / 800 平板 / 1280 桌面）
 *   T8  键盘可达性
 *   T9  打印样式
 *   T10 页面元信息（lang / viewport / favicon）
 *   T13 一键复制（clipboard + execCommand 双兜底）
 *   T14 应用导航（找到这次工作需要的应用 · 分类筛选）
 *   T15 内容补缺（v2.7 · 培训 PPT 查漏补全）
 *   T16 配色对齐桌面端（v2.7 · blue 方案 token）
 */

import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';

const require = createRequire(import.meta.url);

// ── 解析 playwright（pnpm 虚拟库，不新增任何安装）──────────────────
function resolvePlaywright() {
  const candidates = [
    path.resolve(import.meta.dirname, '../../node_modules/playwright'),
    ...(() => {
      const pnpmDir = path.resolve(import.meta.dirname, '../../node_modules/.pnpm');
      try {
        return fs.readdirSync(pnpmDir)
          .filter(d => d.startsWith('playwright@'))
          .sort()
          .map(d => path.join(pnpmDir, d, 'node_modules', 'playwright'));
      } catch { return []; }
    })(),
    'playwright',
  ];
  for (const c of candidates) {
    try { return require(c); } catch { /* try next */ }
  }
  throw new Error('playwright 不可用：请在仓库内安装或确认 pnpm 虚拟库存在');
}
const { chromium } = resolvePlaywright();

const GUIDE_URL = process.env.GUIDE_URL || 'http://127.0.0.1:18925/user-guide.html';
const CHROME_EXE = process.env.CHROME_EXE || 'C:/Program Files/Google/Chrome/Application/chrome.exe';

// ── 断言框架 ──────────────────────────────────────────────────────
const results = [];
let currentGroup = '';
function group(name) { currentGroup = name; }
function check(name, cond, detail = '') {
  results.push({ group: currentGroup, name, ok: !!cond, detail: detail === '' ? '' : String(detail) });
  return !!cond;
}
function eq(name, actual, expected) {
  return check(name, actual === expected, `actual=${JSON.stringify(actual)} expected=${JSON.stringify(expected)}`);
}

// ── 工具 ──────────────────────────────────────────────────────────
async function waitScrollSettle(page, timeoutMs = 3000) {
  await page.waitForFunction(timeout => new Promise(resolve => {
    let last = window.scrollY, stable = 0;
    const timer = setInterval(() => {
      if (Math.abs(window.scrollY - last) < 1) {
        stable += 60;
        if (stable >= 240) { clearInterval(timer); resolve(true); }
      } else { stable = 0; }
      last = window.scrollY;
    }, 60);
    setTimeout(() => { clearInterval(timer); resolve(true); }, timeout || 3000);
  }), timeoutMs).catch(() => {});
}
function collectConsoleErrors(page, bucket) {
  page.on('console', m => { if (m.type() === 'error') bucket.push(m.text()); });
  page.on('pageerror', e => bucket.push(String(e && e.message || e)));
}

async function launch() {
  const opts = { headless: true };
  if (fs.existsSync(CHROME_EXE)) opts.executablePath = CHROME_EXE;
  return chromium.launch(opts);
}

// ── 主流程 ────────────────────────────────────────────────────────
(async () => {
  const browser = await launch();
  const consoleErrors = [];
  let failed = 0;

  try {
    // ============ 桌面视口（1280）：T1-T6, T8-T10 ============
    {
      const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
      const page = await ctx.newPage();
      collectConsoleErrors(page, consoleErrors);
      await page.goto(GUIDE_URL, { waitUntil: 'networkidle' });
      await waitScrollSettle(page);

      // ── T1 结构完整性 ──
      group('T1 结构完整性');
      eq('页面标题含「智算方舟」', await page.title(), '智算方舟桌面端使用指南 · 内部版');
      const secs = await page.evaluate(() => [...document.querySelectorAll('section[id]')].map(s => s.id));
      eq('六大章节存在且顺序正确', secs.join(','), 'start,ui,daily,bid,faq,appendix');
      const footText = await page.evaluate(() => document.querySelector('.foot').innerText);
      check('页脚含版本号 v2.10', footText.includes('v2.10'));
      check('页脚含服务器地址 13495', footText.includes('13495'));
      const figs = await page.evaluate(() => [...document.querySelectorAll('.fig-no')].map(e => e.textContent));
      eq('FIG 编号 01-07 严格按序', figs.join(','), 'FIG.01,FIG.02,FIG.03,FIG.04,FIG.05,FIG.06,FIG.07');
      const bodyText = await page.evaluate(() => document.body.innerText);
      check('登录口径含工号 SJ0851', bodyText.includes('SJ0851'));
      check('登录口径含「预设」密码', bodyText.includes('预设'));
      eq('FAQ 折叠项数量 = 11', await page.evaluate(() => document.querySelectorAll('details.faq').length), 11);
      check('示例指令框数量 = 30（18 场景 + 11 应用卡 + 1 终端指令）', (await page.evaluate(() => document.querySelectorAll('.prompt-box').length)) === 30);
      check('应用内快捷 chips = 15', (await page.evaluate(() => document.querySelectorAll('.chip').length)) === 15);
      eq('进阶场景卡 = 6', await page.evaluate(() => document.querySelectorAll('.adv').length), 6);
      const scenarios = await page.evaluate(() => (document.body.innerText.match(/场景 [A-N]/g) || []));
      check('场景编号覆盖 A-N（14 个场景）', scenarios.length >= 14, `count=${scenarios.length}`);
      const scenarioOrder = await page.evaluate(() => [...document.querySelectorAll('#daily h3')].map(h => h.textContent.trim()).filter(t => t.startsWith('场景')));
      eq('高频场景按一级菜单顺序：问一句→文档→表格→浏览器→资料空间', scenarioOrder.slice(0, 5).join(','), ['场景 A · 问一句：最快的提问入口', '场景 B · 在线文档：把想法和资料写成文档', '场景 C · 多维表格：把记录整理成表格', '场景 D · 浏览器：查资料、比信息', '场景 E · 资料空间与本地文件'].join(','));
      const figCaps = await page.evaluate(() => [...document.querySelectorAll('.fig-cap')].every(c => c.querySelector('.fig-no') && c.querySelector('.fig-title') && c.querySelector('.fig-tag')));
      check('每张图注含编号+标题+标签三要素', figCaps);

      // ── T15 内容补缺（v2.7 · 培训 PPT 查漏补全） ──
      group('T15 内容补缺（PPT 精华）');
      check('「任务续接」小节存在（界面导览）', await page.evaluate(() => [...document.querySelectorAll('#ui h3')].some(h => h.textContent.includes('任务续接'))));
      check('任务续接含「冻结上下文快照」口径', bodyText.includes('冻结当时的对话上下文快照'));
      check('语音输入快捷键 Ctrl+Shift+M', bodyText.includes('Ctrl+Shift+M'));
      check('记忆可导出 Markdown / JSON', bodyText.includes('Markdown / JSON'));
      check('三步上手（说清目标/选对入口/审核沉淀）', await page.evaluate(() => {
        const t = document.body.innerText;
        return t.includes('说清目标') && t.includes('选对入口') && t.includes('审核沉淀');
      }));
      eq('四个好习惯标签 = 4', await page.evaluate(() => document.querySelectorAll('.hchip').length), 4);
      check('协作全景流程条存在（①-⑤ 共 5 节点）', await page.evaluate(() => {
        const p = document.querySelector('.panorama');
        return !!p && p.querySelectorAll('.pl-node').length === 5;
      }));
      check('投标「三步走」小节存在（发起/推进/收尾）', await page.evaluate(() => [...document.querySelectorAll('#bid h3')].some(h => h.textContent.includes('三步走'))));
      check('「待补充素材」铁律存在', bodyText.includes('待补充素材'));
      check('评分点覆盖率自查口径', bodyText.includes('评分点覆盖率'));
      check('人工角色三件事（确认、补料、把关）', bodyText.includes('确认、补料、把关'));
      check('macOS 安装指令（sudo xattr 去隔离）', await page.evaluate(() => {
        const t = document.body.innerText;
        return t.includes('sudo xattr -rd com.apple.quarantine') && t.includes('arm64') && t.includes('拖进右侧');
      }));

      // ── T16 配色对齐桌面端（v2.8 · teal 青瓷绿方案） ──
      group('T16 配色对齐桌面端（teal）');
      eq('--accent = #008878（桌面端 teal primary）', (await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--accent'))).trim(), '#008878');
      eq('--accent-ink = #006E61（teal hover 档）', (await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--accent-ink'))).trim(), '#006E61');
      eq('--accent-soft = #E8F6F2（teal 浅底）', (await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--accent-soft'))).trim(), '#E8F6F2');
      eq('--bg = #F7F9F8（teal 页面底）', (await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--bg'))).trim(), '#F7F9F8');
      eq('--ok = #2D7654（success 同色相文字档）', (await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--ok'))).trim(), '#2D7654');
      eq('--warn = #93471A（warning 同色相文字档）', (await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--warn'))).trim(), '#93471A');
      check('favicon 图标色已换青瓷绿', await page.evaluate(() => {
        const href = document.querySelector('link[rel="icon"]').getAttribute('href');
        return href.includes('%23008878') && !href.includes('%233577D4') && !href.includes('%232E6BE6');
      }));
      check('页面无历史蓝强调残留', await page.evaluate(() => {
        const html = document.documentElement.outerHTML;
        return !/#2E6BE6|#1D4FB8|#EAF0FC|#3577D4|#245BA8|#E8EEF7|#F6F8FB/i.test(html);
      }));

      // ── T2 导航结构 ──
      group('T2 导航结构');
      const railHrefs = await page.evaluate(() => [...document.querySelectorAll('#railnav a')].map(a => a.getAttribute('href')));
      eq('左栏 6 个导航链接', railHrefs.length, 6);
      eq('左栏链接与章节一一对应', railHrefs.join(','), ['#start', '#ui', '#daily', '#bid', '#faq', '#appendix'].join(','));
      const topHrefs = await page.evaluate(() => [...document.querySelectorAll('#topnav a')].map(a => a.getAttribute('href')));
      eq('顶栏 6 个导航链接', topHrefs.length, 6);
      eq('顶栏链接与章节一一对应', topHrefs.join(','), ['#start', '#ui', '#daily', '#bid', '#faq', '#appendix'].join(','));
      const anchorsValid = await page.evaluate(() => [...document.querySelectorAll('a[href^="#"]')].every(a => document.getElementById(a.getAttribute('href').slice(1))));
      check('全部页内锚点目标存在', anchorsValid);

      // ── T3 滚动高亮 ──
      group('T3 滚动高亮（JS 导航联动）');
      const activeRail = () => page.evaluate(() => { const a = document.querySelector('#railnav a.active'); return a ? a.getAttribute('href') : null; });
      const activeTop = () => page.evaluate(() => { const a = document.querySelector('#topnav a.active'); return a ? a.getAttribute('href') : null; });
      eq('初始状态高亮「快速上手」', await activeRail(), '#start');
      for (const id of ['ui', 'daily', 'bid', 'faq', 'appendix']) {
        await page.evaluate(id => window.scrollTo(0, document.getElementById(id).offsetTop + 50), id);
        await waitScrollSettle(page, 2000);
        const want = '#' + id;
        eq(`滚动至 ${id} 后左栏高亮正确`, await activeRail(), want);
        eq(`滚动至 ${id} 后顶栏高亮同步`, await activeTop(), want);
      }
      await page.evaluate(() => window.scrollTo(0, 0));
      await waitScrollSettle(page, 2000);
      eq('回到顶部后高亮复位 #start', await activeRail(), '#start');

      // ── T4 锚点跳转（桌面）──
      group('T4 锚点跳转 · 桌面（无遮挡）');
      for (const id of ['start', 'ui', 'daily', 'bid', 'faq', 'appendix']) {
        await page.evaluate(id => { document.querySelector(`#railnav a[href="#${id}"]`).click(); }, id);
        await waitScrollSettle(page, 2500);
        const top = await page.evaluate(id => Math.round(document.getElementById(id).getBoundingClientRect().top), id);
        check(`点击「${id}」后章节可见（top=${top}）`, top >= 0, `top=${top}`);
      }

      // ── T5 FAQ 折叠面板 ──
      group('T5 FAQ 折叠面板交互');
      const faqCount = await page.evaluate(() => document.querySelectorAll('details.faq').length);
      const allClosed = await page.evaluate(() => [...document.querySelectorAll('details.faq')].every(d => !d.open));
      check('初始全部折叠', allClosed);
      let openOk = 0;
      for (let i = 0; i < faqCount; i++) {
        openOk += await page.evaluate(i => {
          const d = document.querySelectorAll('details.faq')[i];
          d.open = true;
          return d.open && d.querySelector('.faq-body').offsetHeight > 40 && d.querySelector('ol, .esc') ? 1 : 0;
        }, i);
      }
      eq('逐个展开：内容渲染且高度 > 40px', openOk, faqCount);
      const reClosed = await page.evaluate(() => { document.querySelectorAll('details.faq').forEach(d => d.open = false); return [...document.querySelectorAll('details.faq')].every(d => !d.open); });
      check('可全部重新折叠', reClosed);

      // ── T6 资源加载 ──
      group('T6 资源加载');
      const imgStat = await page.evaluate(() => {
        const imgs = [...document.querySelectorAll('img')];
        return { total: imgs.length, loaded: imgs.filter(i => i.complete && i.naturalWidth > 0).length, broken: imgs.filter(i => i.complete && i.naturalWidth === 0).map(i => i.getAttribute('src')) };
      });
      eq('实机截图共 7 张', imgStat.total, 7);
      eq('7 张图片全部加载成功', imgStat.loaded, 7);
      check('无损坏图片', imgStat.broken.length === 0, imgStat.broken.join(','));

      // ── T13 一键复制交互 ──
      group('T13 一键复制（clipboard + execCommand 双兜底）');
      const pbCount = await page.evaluate(() => document.querySelectorAll('.prompt-box').length);
      const btnCount = await page.evaluate(() => document.querySelectorAll('.pb-copy').length);
      eq('复制按钮已注入全部 30 个指令框', btnCount, pbCount);
      eq('指令框总数 = 30', pbCount, 30);
      const textsOk = await page.evaluate(() => [...document.querySelectorAll('.prompt-box')].every(b => {
        const clone = b.cloneNode(true);
        clone.querySelectorAll('.pb-label').forEach(n => n.remove());
        return clone.textContent.trim().length > 5;
      }));
      check('每个指令框都有可复制的非空指令文本', textsOk);
      const feedback = await page.evaluate(async () => {
        const btn = document.querySelector('.pb-copy');
        btn.click();
        await new Promise(r => setTimeout(r, 250));
        const during = btn.textContent;
        const copiedCls = btn.classList.contains('copied');
        await new Promise(r => setTimeout(r, 1650));
        return { during, copiedCls, after: btn.textContent.trim() };
      });
      check('点击后显示「已复制 ✓」反馈态', feedback.during.includes('已复制'), JSON.stringify(feedback));
      check('反馈态伴随高亮样式（.copied）', feedback.copiedCls);
      check('1.6 秒后按钮复原「复制」', feedback.after === '复制', JSON.stringify(feedback));
      const fallbackOk = await page.evaluate(async () => {
        try { Object.defineProperty(navigator, 'clipboard', { value: undefined, configurable: true }); } catch (e) {}
        const btn = document.querySelectorAll('.pb-copy')[3];
        btn.click();
        await new Promise(r => setTimeout(r, 250));
        return btn.textContent.includes('已复制');
      });
      check('剪贴板 API 不可用时走 execCommand 兜底仍成功（HTTP 环境）', fallbackOk);

      // ── T14 应用导航 ──
      group('T14 应用导航（找到这次工作需要的应用）');
      eq('应用卡 = 11', await page.evaluate(() => document.querySelectorAll('.af-card').length), 11);
      eq('分类页签 = 6', await page.evaluate(() => document.querySelectorAll('#afTabs button').length), 6);
      const catMap = { all: 11, creative: 3, data: 3, research: 1, collab: 2, dev: 2 };
      for (const [cat, want] of Object.entries(catMap)) {
        const n = await page.evaluate(cat => {
          document.querySelector('#afTabs button[data-cat="' + cat + '"]').click();
          return [...document.querySelectorAll('.af-card')].filter(c => c.style.display !== 'none').length;
        }, cat);
        eq(`分类「${cat}」筛出 ${want} 张卡`, n, want);
      }
      const tabActive = await page.evaluate(() => document.querySelector('#afTabs button[data-cat="dev"]').classList.contains('active'));
      check('当前分类页签呈选中态', tabActive);
      const allBack = await page.evaluate(() => {
        document.querySelector('#afTabs button[data-cat="all"]').click();
        return [...document.querySelectorAll('.af-card')].filter(c => c.style.display !== 'none').length;
      });
      eq('切回「全部」恢复 11 张卡', allBack, 11);
      const cardsComplete = await page.evaluate(() => [...document.querySelectorAll('.af-card')].every(c =>
        c.querySelector('.prompt-box') && c.querySelector('.pb-copy') && c.querySelector('.af-open') && c.querySelector('.af-cat')));
      check('每张应用卡含指令 + 复制按钮 + 打开方式 + 应用标识', cardsComplete);

      // ── T8 键盘可达性（桌面测可见的左栏链接）──
      group('T8 键盘可达性');
      const focusOk = await page.evaluate(() => {
        const a = document.querySelector('#railnav a[href="#faq"]');
        a.focus();
        return document.activeElement === a;
      });
      check('导航链接可键盘聚焦（Tab 路径）', focusOk);
      const summaryFocusOk = await page.evaluate(() => {
        const s = document.querySelector('details.faq summary');
        s.focus();
        return document.activeElement === s;
      });
      check('FAQ 标题可键盘聚焦（Enter 展开）', summaryFocusOk);
      const cursorPointer = await page.evaluate(() => getComputedStyle(document.querySelector('details.faq summary')).cursor === 'pointer');
      check('FAQ 标题呈现可点击指针样式', cursorPointer);

      // ── T9 打印样式 ──
      group('T9 打印样式');
      const printRules = await page.evaluate(() => {
        let found = 0;
        for (const sheet of document.styleSheets) {
          try {
            for (const rule of sheet.cssRules) {
              if (rule.media && rule.media.mediaText.includes('print')) {
                const text = rule.cssText;
                if (/\.leftrail[^{]*\{[^}]*display:\s*none/.test(text) && /\.topbar[^{]*\{[^}]*display:\s*none/.test(text)) found++;
              }
            }
          } catch { /* ignore */ }
        }
        return found;
      });
      check('打印时隐藏左栏与顶栏（@media print）', printRules >= 1);

      // ── T10 页面元信息 ──
      group('T10 页面元信息');
      eq('语言标记 zh-CN', await page.evaluate(() => document.documentElement.lang), 'zh-CN');
      check('含 viewport meta（移动适配前提）', await page.evaluate(() => !!document.querySelector('meta[name="viewport"]')));
      check('含内联 favicon（无外链请求）', await page.evaluate(() => !!document.querySelector('link[rel="icon"]')));
      check('平滑滚动已启用', await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior === 'smooth'));

      await ctx.close();
    }

    // ============ 手机视口（375）：T7a + 锚点不遮挡 ============
    {
      const ctx = await browser.newContext({ viewport: { width: 375, height: 812 } });
      const page = await ctx.newPage();
      collectConsoleErrors(page, consoleErrors);
      await page.goto(GUIDE_URL, { waitUntil: 'networkidle' });
      await waitScrollSettle(page);

      group('T7a 响应式 · 手机（375px）');
      eq('手机端左栏隐藏', await page.evaluate(() => getComputedStyle(document.querySelector('.leftrail')).display), 'none');
      check('手机端顶栏显示', await page.evaluate(() => getComputedStyle(document.querySelector('.topbar')).display !== 'none'));
      const noOverflow = await page.evaluate(() => document.documentElement.scrollWidth === document.documentElement.clientWidth);
      check('无横向溢出（scrollW=clientW）', noOverflow, await page.evaluate(() => `scrollW=${document.documentElement.scrollWidth} clientW=${document.documentElement.clientWidth}`));
      eq('登录示意图上下堆叠', await page.evaluate(() => getComputedStyle(document.querySelector('.login-mock')).flexDirection), 'column');
      eq('进阶场景卡单列', (await page.evaluate(() => getComputedStyle(document.querySelector('.adv-grid')).gridTemplateColumns.split(' ').length)), 1);
      eq('应用导航卡单列', (await page.evaluate(() => getComputedStyle(document.querySelector('.af-grid')).gridTemplateColumns.split(' ').length)), 1);
      const flowStacked = await page.evaluate(() => {
        const nodes = [...document.querySelectorAll('.flow-node')];
        const flow = document.querySelector('.flow').getBoundingClientRect();
        return nodes.every(n => n.getBoundingClientRect().width > flow.width * 0.9);
      });
      check('投标三环流程图纵向堆叠', flowStacked);
      const tblScroll = await page.evaluate(() => {
        const t = document.querySelector('#appendix table.tbl'); // 附录服务器表：宽表
        const narrow = document.querySelector('#start table.tbl'); // 准备工作表：窄表
        return {
          wideScrollable: getComputedStyle(t).overflowX.includes('auto') && getComputedStyle(t).display === 'block',
          narrowContained: narrow.scrollWidth <= document.documentElement.clientWidth
        };
      });
      check('宽表格具备横滚能力（overflow-x: auto）', tblScroll.wideScrollable);
      check('窄表格不溢出视口', tblScroll.narrowContained);
      eq('大标题字号收紧为 24px', await page.evaluate(() => getComputedStyle(document.querySelector('.hero h1')).fontSize), '24px');

      group('T4b 锚点跳转 · 手机（不被吸顶导航遮挡）');
      const topbarH = await page.evaluate(() => Math.round(document.querySelector('.topbar').getBoundingClientRect().height));
      for (const id of ['start', 'ui', 'daily', 'bid', 'faq', 'appendix']) {
        await page.evaluate(id => { document.querySelector(`#topnav a[href="#${id}"]`).click(); }, id);
        await waitScrollSettle(page, 2500);
        const top = await page.evaluate(id => Math.round(document.getElementById(id).getBoundingClientRect().top), id);
        check(`「${id}」跳转后标题未被吸顶导航遮挡`, top >= topbarH - 2, `top=${top} topbarH=${topbarH}`);
      }

      group('T7b 吸顶行为 · 手机');
      await page.evaluate(() => window.scrollTo(0, 3000));
      await waitScrollSettle(page, 1500);
      const stickyTop = await page.evaluate(() => Math.round(document.querySelector('.topbar').getBoundingClientRect().top));
      eq('滚动后顶栏保持吸顶（top=0）', stickyTop, 0);

      await ctx.close();
    }

    // ============ 平板（800）与桌面（1280）断点 ============
    {
      const ctx = await browser.newContext({ viewport: { width: 800, height: 900 } });
      const page = await ctx.newPage();
      await page.goto(GUIDE_URL, { waitUntil: 'networkidle' });
      group('T7c 响应式 · 平板（800px）');
      check('平板：左栏隐藏', await page.evaluate(() => getComputedStyle(document.querySelector('.leftrail')).display === 'none'));
      check('平板：顶栏显示', await page.evaluate(() => getComputedStyle(document.querySelector('.topbar')).display !== 'none'));
      eq('平板：登录示意图左右分栏', await page.evaluate(() => getComputedStyle(document.querySelector('.login-mock')).flexDirection), 'row');
      check('平板：无横向溢出', await page.evaluate(() => document.documentElement.scrollWidth === document.documentElement.clientWidth));
      await ctx.close();
    }
    {
      const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
      const page = await ctx.newPage();
      await page.goto(GUIDE_URL, { waitUntil: 'networkidle' });
      group('T7d 响应式 · 桌面（1280px）');
      check('桌面：左栏显示', await page.evaluate(() => getComputedStyle(document.querySelector('.leftrail')).display !== 'none'));
      check('桌面：顶栏隐藏', await page.evaluate(() => getComputedStyle(document.querySelector('.topbar')).display === 'none'));
      eq('桌面：登录示意图左右分栏', await page.evaluate(() => getComputedStyle(document.querySelector('.login-mock')).flexDirection), 'row');
      check('桌面：无横向溢出', await page.evaluate(() => document.documentElement.scrollWidth === document.documentElement.clientWidth));
      await ctx.close();
    }

    // ============ 小屏（320px）：宽表必然需要横滚 ============
    {
      const ctx = await browser.newContext({ viewport: { width: 320, height: 700 } });
      const page = await ctx.newPage();
      await page.goto(GUIDE_URL, { waitUntil: 'networkidle' });
      group('T7e 响应式 · 小屏（320px）');
      check('小屏：无页面级横向溢出', await page.evaluate(() => document.documentElement.scrollWidth === document.documentElement.clientWidth));
      check('附录宽表确实需要横向滚动（scrollW>clientW）', await page.evaluate(() => {
        const t = document.querySelector('#appendix table.tbl');
        return t.scrollWidth > t.clientWidth;
      }));
      await ctx.close();
    }

    // ============ 控制台零错误 ============
    group('T6b 控制台');
    check('全视口控制台零错误', consoleErrors.length === 0, consoleErrors.slice(0, 3).join(' | '));

  } finally {
    await browser.close();
  }

  // ── 报告输出 ──────────────────────────────────────────────────────
  const passed = results.filter(r => r.ok).length;
  failed = results.length - passed;
  let lastGroup = '';
  for (const r of results) {
    if (r.group !== lastGroup) { console.log(`\n■ ${r.group}`); lastGroup = r.group; }
    const mark = r.ok ? '  ✓' : '  ✗';
    console.log(`${mark} ${r.name}${r.ok ? '' : `  → ${r.detail}`}`);
  }
  console.log('\n────────────────────────────────────────');
  console.log(`RESULT: ${passed} passed, ${failed} failed, ${results.length} total`);
  console.log('TARGET:', GUIDE_URL);
  process.exit(failed === 0 ? 0 : 1);
})().catch(e => { console.error('SUITE ERROR:', e); process.exit(2); });
