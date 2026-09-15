// =====================================================================
// Runner · 生成脚本的"一站式"主入口辅助
//
// 职责:
//   1. 确保 Web server 在运行（没有就后台拉起一个）
//   2. 串行构建主 deck（pages.buildSlides）
//   3. 每页构建完成 → 上报进度 + 入队异步渲染（串行，PowerPoint COM 不并发）
//   4. 全部构建完成 → 保存主 .pptx
//   5. 等待所有渲染完成 → 上报 deck_done
//
// 用户最小用法（gen_main.js）:
//   const { run } = require("./runner");
//   module.exports = {
//     deckMeta: { title, author, theme, totalPages },
//     setup(pres) { return require("./lib/themes").setup(pres, "telecom-red"); },
//     buildSlides: [ (pres, ctx) => {...}, ... ],
//   };
//   if (require.main === module) run({ pages: module.exports, outputPath: "demo.pptx" });
// =====================================================================
"use strict";

const fs = require("fs");
const path = require("path");
const http = require("http");
const { spawn, fork } = require("child_process");
const pptxgen = require("pptxgenjs");
const { createReporter } = require("./reporter");

// ---- 串行任务队列（保证 PowerPoint COM 不并发） ----
class SerialQueue {
  constructor() { this._chain = Promise.resolve(); this._size = 0; }
  get size() { return this._size; }
  push(task) {
    this._size += 1;
    const r = this._chain.then(() => task()).finally(() => { this._size -= 1; });
    this._chain = r.then(() => {}, () => {});
    return r;
  }
  idle() { return this._size === 0; }
  waitAll() {
    return new Promise((resolve) => {
      const tick = () => this.idle() ? resolve() : setTimeout(tick, 100);
      tick();
    });
  }
}

// ---- ping server 是否存活 ----
function pingServer(serverUrl) {
  return new Promise((resolve) => {
    const u = new URL(serverUrl);
    const req = http.request({ hostname: u.hostname, port: u.port, path: "/api/state", method: "GET", timeout: 1500 }, (res) => {
      res.on("data", () => {});
      res.on("end", () => resolve(res.statusCode === 200));
    });
    req.on("error", () => resolve(false));
    req.on("timeout", () => { req.destroy(); resolve(false); });
    req.end();
  });
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ---- 后台拉起 server ----
async function ensureServer(serverUrl, serverJsPath) {
  if (await pingServer(serverUrl)) return true;
  const child = spawn("node", [serverJsPath, "--no-browser"], {
    cwd: path.dirname(serverJsPath),
    detached: true,
    windowsHide: true,
    stdio: "ignore",
  });
  try { child.unref(); } catch (_) {}
  // 等待 server 就绪
  for (let i = 0; i < 30; i++) {
    await sleep(300);
    if (await pingServer(serverUrl)) return true;
  }
  return false;
}

// =====================================================================
// 主入口
// =====================================================================
async function run(opts) {
  const { pages, outputPath } = opts;
  const serverUrl = (opts.serverUrl || "http://127.0.0.1:51720").replace(/\/$/, "");
  const themeName = pages.deckMeta?.theme || "telecom-red";
  const totalPages = (pages.buildSlides || []).length;
  const deckMeta = {
    title: pages.deckMeta?.title || "PPT Preview",
    author: pages.deckMeta?.author || "",
    theme: themeName,
    totalPages,
    outputPath: path.resolve(outputPath || "preview.pptx"),
  };

  // 0. 确保目录存在
  const outAbs = deckMeta.outputPath;
  const outDir = path.dirname(outAbs);
  if (outDir && !fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  // 缩略图 cache 目录：与 server 锁定的目录保持一致（skill 根目录下 .ppt-preview-cache），
  // 这样 /cache/thumbs/* 才能被 server 静态服务读到。
  // 修复前曾把 cacheDir 通过 /api/config 传给 server 去改写，存在越权目录穿越风险，现已移除。
  const skillRoot = path.resolve(path.join(__dirname, "..", ".."));
  const cacheDir = path.resolve(opts.cacheDir || path.join(skillRoot, ".ppt-preview-cache"));
  if (!fs.existsSync(cacheDir)) fs.mkdirSync(cacheDir, { recursive: true });

  // 1. 启动 server
  const serverJs = path.join(__dirname, "server.js");
  const ok = await ensureServer(serverUrl, serverJs);
  if (!ok) {
    console.error("[runner] server 启动失败，将以无预览模式继续");
  }

  const reporter = createReporter({ serverUrl });
  await reporter.log("[runner] 开始生成流程", "info");

  // 2. 构造主 deck
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.title = deckMeta.title;
  pres.author = deckMeta.author;

  let ctx;
  try {
    ctx = pages.setup ? pages.setup(pres) : require("./lib/themes").setup(pres, themeName);
  } catch (e) {
    await reporter.deckError("setup 失败: " + e.message);
    throw e;
  }

  // 3. 上报 start
  await reporter.start(deckMeta);

  // 4. 串行构建 + 异步渲染
  const renderQueue = new SerialQueue();
  const slideMetas = pages.deckMeta?.slideMetas || []; // [{title, template}]

  for (let i = 0; i < totalPages; i++) {
    const meta = slideMetas[i] || {};
    await reporter.slideBuildStart(i, { title: meta.title || "", template: meta.template || "" });
    const t0 = Date.now();
    try {
      pages.buildSlides[i](pres, ctx);
    } catch (e) {
      await reporter.deckError(`第 ${i + 1} 页构建失败: ${e.message}`);
      throw e;
    }
    const buildMs = Date.now() - t0;
    await reporter.slideBuilt(i, { title: meta.title || "", template: meta.template || "", buildMs });

    // 入队渲染：把 thumbnail 输出到 cacheDir/thumbs/slide-{i+1}.png
    const thumbPath = path.join(cacheDir, "thumbs", `slide-${String(i + 1).padStart(3, "0")}.png`);
    if (!fs.existsSync(path.dirname(thumbPath))) fs.mkdirSync(path.dirname(thumbPath), { recursive: true });

    // 用闭包捕获 i；push 必须传入"返回 Promise 的函数"，让队列串行触发执行
    const renderTask = () => (async () => {
      await reporter.slideRenderStart(i);
      const r = await renderOne(i, thumbPath);
      if (r.ok) {
        await reporter.slideRendered(i, `/cache/thumbs/slide-${String(i + 1).padStart(3, "0")}.png`, r.renderMs);
      } else {
        await reporter.slideRenderFailed(i, r.error || "未知错误");
      }
    })().catch(async (e) => {
      try { await reporter.slideRenderFailed(i, "渲染异常: " + (e?.message || e)); } catch (_) {}
    });
    renderQueue.push(renderTask);
  }

  // 5. 全部构建完成 → 保存主 .pptx
  try {
    await pres.writeFile({ fileName: outAbs });
  } catch (e) {
    await reporter.deckError("writeFile 失败: " + e.message);
    throw e;
  }

  // 6. 等待所有渲染完成
  await renderQueue.waitAll();
  await reporter.log("[runner] 所有页渲染完成", "success");

  // 7. 上报 deck_done
  await reporter.deckDone(outAbs);
  console.log("[runner] DONE:", outAbs);
  return { outputPath: outAbs, totalPages, rendered: renderQueue.idle() };
}

// 渲染单页（fork 子进程 + IPC 通道接收 process.send 消息）
function renderOne(pageIdx, outPngPath) {
  return new Promise((resolve) => {
    // pages 模块路径 = 主生成脚本路径（用户脚本应使用 require.main===module 守卫 run 调用，避免递归）
    const mainModule = require.main ? require.main.filename : process.argv[1];
    const child = fork(path.join(__dirname, "render-single.js"), [mainModule, String(pageIdx), outPngPath], {
      cwd: __dirname,
      silent: true,
    });
    let stderr = "";
    let resolved = false;
    if (child.stderr) child.stderr.on("data", (d) => { stderr += d.toString(); });
    child.on("message", (msg) => {
      if (resolved) return;
      resolved = true;
      if (msg && typeof msg === "object") resolve(msg);
      else resolve({ ok: false, error: "未知消息格式" });
    });
    child.on("error", (e) => {
      if (resolved) return;
      resolved = true;
      resolve({ ok: false, error: "fork 失败: " + e.message });
    });
    child.on("close", (code) => {
      if (resolved) return;
      resolved = true;
      // 若没收到 message 但输出文件存在，认为成功
      if (fs.existsSync(outPngPath)) resolve({ ok: true, renderMs: 0 });
      else resolve({ ok: false, error: `子进程退出 code=${code}, stderr=${stderr.slice(0, 200)}` });
    });
  });
}

module.exports = { run, SerialQueue };
