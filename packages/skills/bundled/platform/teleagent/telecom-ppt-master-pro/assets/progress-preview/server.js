// =====================================================================
// PPT 生成进度预览 · Web 服务器
// 提供静态资源服务 + SSE 实时推送 + 状态快照
//
// 启动:
//   node server.js                // 默认端口 51720，自动开浏览器
//   node server.js --no-browser   // 不自动开浏览器
//   node server.js --port 51800
// =====================================================================
"use strict";

const http = require("http");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const ROOT = __dirname;
const PUBLIC_DIR = path.join(ROOT, "public");

// =====================================================================
// 缩略图缓存目录（安全约束）
//   - 启动时一次性解析确定，后续不可被客户端改写（修复越权目录穿越）
//   - 默认固定在本技能目录的 .ppt-preview-cache 下，归属权清晰
//   - 仅当传入的 --cache-dir 明确落在本技能目录内时才采纳，否则回退默认，
//     防止把服务指向任意系统目录
// =====================================================================
const SKILL_ROOT = path.resolve(path.join(__dirname, "..", ".."));
function resolveCacheDir() {
  const i = process.argv.indexOf("--cache-dir");
  if (i >= 0 && process.argv[i + 1]) {
    const candidate = path.resolve(process.argv[i + 1]);
    const rel = path.relative(SKILL_ROOT, candidate);
    const inside = rel && !rel.startsWith("..") && !path.isAbsolute(rel);
    if (inside) return candidate;
  }
  return path.join(SKILL_ROOT, ".ppt-preview-cache");
}
const CACHE_DIR = process.env.PPT_PREVIEW_CACHE_DIR
  ? path.join(SKILL_ROOT, ".ppt-preview-cache")
  : resolveCacheDir();
function ensureCacheDir() {
  if (!fs.existsSync(CACHE_DIR)) fs.mkdirSync(CACHE_DIR, { recursive: true });
}
ensureCacheDir();

// =====================================================================
// 安全辅助：判断某个绝对路径是否位于允许的根目录之内
//   拒绝：等于根目录本身（防把整个 C:\ 暴露）、位于根目录之外、以及
//   ..\  盘符穿越等任何逃逸情况。此校验对 Windows 反斜杠同样生效。
// =====================================================================
function isWithin(root, target) {
  const rel = path.relative(root, target);
  if (rel === "" || rel === ".") return false;      // target 就是 root 本身，拒绝
  if (rel.startsWith("..") || path.isAbsolute(rel)) return false; // 逃逸到 root 之外
  return true;
}

// 将 URL 中的相对路径安全地映射到 base 目录，防目录穿越
// 返回合法绝对路径；不合法返回 null
function safeJoin(base, rel) {
  if (typeof rel !== "string" || !rel) return null;
  const p = path.normalize(rel).replace(/^[/\\]+/, ""); // 去掉开头的 / 或 \，避免绝对路径逃逸
  const abs = path.resolve(base, p);
  return isWithin(base, abs) ? abs : null;
}

// 从命令行读取参数
const argv = process.argv.slice(2);
const PORT = (() => {
  const i = argv.indexOf("--port");
  return i >= 0 && argv[i + 1] ? parseInt(argv[i + 1], 10) : 51720;
})();
const OPEN_BROWSER = !argv.includes("--no-browser");

// =====================================================================
// 全局状态（单 deck 会话）
// =====================================================================
const state = {
  deck: {
    title: "等待生成脚本接入…",
    author: "",
    theme: "telecom-red",
    totalPages: 0,
    outputPath: "",
    startedAt: null,
    finishedAt: null,
  },
  status: "idle", // idle | running | done | error
  slides: [], // [{ idx, title, template, status, thumbnail, error, buildMs, renderMs }]
  logs: [], // [{ t, msg, level }]
  stats: { built: 0, rendered: 0, failed: 0 },
};

const SSE_CLIENTS = new Set(); // 响应对象集合

function nowMs() { return Date.now(); }
function ts() { return new Date().toISOString(); }

function pushLog(msg, level = "info") {
  const entry = { t: ts(), msg: String(msg), level };
  state.logs.push(entry);
  if (state.logs.length > 500) state.logs.shift();
  broadcast({ type: "log", data: entry });
}

function updateSlide(idx, patch) {
  if (!state.slides[idx]) {
    state.slides[idx] = { idx, title: "", template: "", status: "pending", thumbnail: "", error: "", buildMs: 0, renderMs: 0 };
  }
  Object.assign(state.slides[idx], patch);
  broadcast({ type: "slide_update", data: state.slides[idx] });
}

function updateDeck(patch) {
  Object.assign(state.deck, patch);
  broadcast({ type: "deck_update", data: state.deck });
}

function setStats() {
  state.stats.built = state.slides.filter(s => s && ["built", "rendering", "rendered", "failed"].includes(s.status)).length;
  state.stats.rendered = state.slides.filter(s => s && s.status === "rendered").length;
  state.stats.failed = state.slides.filter(s => s && s.status === "failed").length;
  broadcast({ type: "stats", data: state.stats });
}

// =====================================================================
// SSE 广播
// =====================================================================
function broadcast(event) {
  const payload = `data: ${JSON.stringify(event)}\n\n`;
  for (const res of SSE_CLIENTS) {
    try { res.write(payload); } catch (_) { SSE_CLIENTS.delete(res); }
  }
}

// =====================================================================
// HTTP 路由
// =====================================================================
const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
};

function serveStatic(req, res, filePath) {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Not Found: " + path.basename(filePath));
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream", "Cache-Control": "no-cache" });
    res.end(data);
  });
}

function readBody(req) {
  return new Promise((resolve) => {
    let buf = "";
    req.on("data", c => { buf += c; if (buf.length > 5e6) req.destroy(); });
    req.on("end", () => {
      try { resolve(JSON.parse(buf || "{}")); }
      catch (_) { resolve({}); }
    });
    req.on("error", () => resolve({}));
  });
}

async function handleApi(req, res, url) {
  // 接收生成脚本推送的事件
  if (url.pathname === "/api/progress" && req.method === "POST") {
    const body = await readBody(req);
    handleProgressEvent(body);
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  // 状态快照（SSE 重连后恢复用）
  if (url.pathname === "/api/state" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-cache" });
    res.end(JSON.stringify(state));
    return;
  }

  // 查询当前 cacheDir（只读）。不再允许客户端改写缓存目录——
  // 旧版允许通过 body.cacheDir 把 CACHE_DIR 指向任意系统目录，属越权目录穿越漏洞。
  // 缓存目录现由启动参数/环境变量一次性确定，并强制限定在本技能目录内。
  if (url.pathname === "/api/config" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-cache" });
    res.end(JSON.stringify({ ok: true, cacheDir: CACHE_DIR, skillRoot: SKILL_ROOT }));
    return;
  }

  // SSE 长连接
  if (url.pathname === "/api/events" && req.method === "GET") {
    res.writeHead(200, {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
    });
    res.write(": connected\n\n");
    SSE_CLIENTS.add(res);
    // 立即推送当前状态快照
    res.write(`data: ${JSON.stringify({ type: "snapshot", data: state })}\n\n`);
    req.on("close", () => SSE_CLIENTS.delete(res));
    return;
  }

  res.writeHead(404, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ error: "not found" }));
}

function handleProgressEvent(body) {
  const { type, data } = body;
  switch (type) {
    case "start":
      state.status = "running";
      state.deck.startedAt = data.startedAt || ts();
      updateDeck({
        title: data.title || state.deck.title,
        author: data.author || "",
        theme: data.theme || "telecom-red",
        totalPages: data.totalPages || 0,
        outputPath: data.outputPath || "",
        startedAt: state.deck.startedAt,
        finishedAt: null,
      });
      state.slides = new Array(data.totalPages || 0).fill(null).map((_, i) => ({
        idx: i, title: "", template: "", status: "pending",
        thumbnail: "", error: "", buildMs: 0, renderMs: 0,
      }));
      broadcast({ type: "reset", data: { totalPages: data.totalPages || 0 } });
      broadcast({ type: "status_update", data: { status: state.status } });
      pushLog(`开始生成: ${data.title || ""} · 共 ${data.totalPages || 0} 页`, "info");
      break;
    case "slide_build_start":
      updateSlide(data.idx, { status: "building", title: data.title || "", template: data.template || "" });
      break;
    case "slide_built":
      updateSlide(data.idx, {
        status: "built",
        title: data.title || "",
        template: data.template || "",
        buildMs: data.buildMs || 0,
      });
      setStats();
      pushLog(`第 ${data.idx + 1} 页构建完成 · ${data.title || ""} (${data.template || ""})`, "info");
      break;
    case "slide_render_start":
      updateSlide(data.idx, { status: "rendering" });
      break;
    case "slide_rendered":
      updateSlide(data.idx, {
        status: "rendered",
        thumbnail: data.thumbnail || "",
        renderMs: data.renderMs || 0,
      });
      setStats();
      break;
    case "slide_render_failed":
      updateSlide(data.idx, { status: "failed", error: data.error || "渲染失败" });
      setStats();
      pushLog(`第 ${data.idx + 1} 页渲染失败: ${data.error || ""}`, "error");
      break;
    case "deck_done":
      state.status = "done";
      state.deck.finishedAt = ts();
      updateDeck({ finishedAt: state.deck.finishedAt, outputPath: data.outputPath || "" });
      broadcast({ type: "status_update", data: { status: state.status } });
      pushLog(`PPT 生成完成: ${data.outputPath || ""}`, "success");
      break;
    case "deck_error":
      state.status = "error";
      broadcast({ type: "status_update", data: { status: state.status } });
      pushLog(`生成失败: ${data.error || ""}`, "error");
      break;
    case "log":
      pushLog(data.msg || "", data.level || "info");
      break;
    default:
      pushLog(`[未知事件 ${type}] ${JSON.stringify(data).slice(0, 120)}`, "warn");
  }
}

// =====================================================================
// 启动服务器
// =====================================================================
const server = http.createServer(async (req, res) => {
  // 本服务仅面向本机浏览器，不应对任意来源放开跨域读写（修复越权目录穿越）
  res.setHeader("Access-Control-Allow-Origin", "null"); // 仅允许本地文件/null 源
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("X-Content-Type-Options", "nosniff");
  if (req.method === "OPTIONS") { res.writeHead(204); res.end(); return; }

  const url = new URL(req.url, `http://${req.headers.host}`);

  // 仅放行 GET 与 POST（POST 仅用于本机脚本上报进度）；其余方法一律拒绝
  if (req.method !== "GET" && req.method !== "POST") {
    res.writeHead(405, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "method not allowed" }));
    return;
  }

  if (url.pathname.startsWith("/api/")) {
    await handleApi(req, res, url);
    return;
  }
  if (url.pathname === "/" || url.pathname === "/index.html") {
    serveStatic(req, res, path.join(PUBLIC_DIR, "index.html"));
    return;
  }
  // /cache/* → 缩略图目录（用安全校验映射，杜绝目录穿越到缓存目录之外）
  if (url.pathname.startsWith("/cache/")) {
    const rel = url.pathname.slice("/cache/".length);
    const filePath = safeJoin(CACHE_DIR, decodeURIComponent(rel));
    if (!filePath) {
      res.writeHead(403, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Forbidden");
      return;
    }
    serveStatic(req, res, filePath);
    return;
  }
  // 其他静态文件（同样防穿越到 public 之外）
  const pubPath = safeJoin(PUBLIC_DIR, decodeURIComponent(url.pathname));
  if (!pubPath) {
    res.writeHead(403, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("Forbidden");
    return;
  }
  serveStatic(req, res, pubPath);
});

// SSE 心跳
setInterval(() => {
  if (SSE_CLIENTS.size === 0) return;
  for (const res of SSE_CLIENTS) {
    try { res.write(": heartbeat\n\n"); } catch (_) { SSE_CLIENTS.delete(res); }
  }
}, 25000);

server.listen(PORT, "127.0.0.1", () => {
  const url = `http://127.0.0.1:${PORT}/`;
  pushLog(`预览服务器已启动 @ ${url}`, "info");
  console.log(`[ppt-preview] server listening on ${url}`);
  if (OPEN_BROWSER) {
    try {
      spawn("cmd", ["/c", "start", "", url], { detached: false, stdio: "ignore" });
      console.log(`[ppt-preview] opening browser: ${url}`);
    } catch (_) {}
  }
});

server.on("error", (e) => {
  console.error("[ppt-preview] server error:", e.message);
  if (e.code === "EADDRINUSE") {
    console.error(`端口 ${PORT} 被占用，请用 --port 指定其他端口`);
  }
  process.exit(1);
});
