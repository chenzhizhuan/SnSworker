// =====================================================================
// PPT 生成进度预览 · 进度上报器
// 供生成脚本调用，通过 HTTP POST 把事件推到本地 Web 服务器
//
// 用法:
//   const { createReporter } = require("./reporter");
//   const r = createReporter({ serverUrl: "http://127.0.0.1:51720", deckTitle: "..." });
//   await r.start({ title, author, theme, totalPages, outputPath });
//   await r.slideBuildStart(0, { title, template });
//   ... 构建这页 ...
//   await r.slideBuilt(0, { title, template, buildMs });
//   await r.deckDone(outputPath);
// =====================================================================
"use strict";

const http = require("http");

function post(url, body) {
  return new Promise((resolve) => {
    const u = new URL(url);
    const payload = JSON.stringify(body || {});
    const req = http.request({
      hostname: u.hostname,
      port: u.port,
      path: u.pathname,
      method: "POST",
      headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(payload) },
      timeout: 4000,
    }, (res) => {
      res.on("data", () => {});
      res.on("end", () => resolve({ ok: res.statusCode < 500 }));
    });
    req.on("error", () => resolve({ ok: false }));
    req.on("timeout", () => { req.destroy(); resolve({ ok: false }); });
    req.write(payload);
    req.end();
  });
}

function createReporter(opts = {}) {
  const serverUrl = (opts.serverUrl || "http://127.0.0.1:51720").replace(/\/$/, "");
  const endpoint = serverUrl + "/api/progress";

  async function emit(type, data = {}) {
    await post(endpoint, { type, data });
  }

  return {
    serverUrl,
    async ping() {
      const r = await post(endpoint, { type: "ping", data: {} });
      return r.ok;
    },
    async log(msg, level = "info") { await emit("log", { msg, level }); },
    async start(meta) { await emit("start", { startedAt: new Date().toISOString(), ...meta }); },
    async slideBuildStart(idx, info) { await emit("slide_build_start", { idx, ...info }); },
    async slideBuilt(idx, info) { await emit("slide_built", { idx, ...info }); },
    async slideRenderStart(idx) { await emit("slide_render_start", { idx }); },
    async slideRendered(idx, thumbnail, renderMs) { await emit("slide_rendered", { idx, thumbnail, renderMs }); },
    async slideRenderFailed(idx, error) { await emit("slide_render_failed", { idx, error }); },
    async deckDone(outputPath) { await emit("deck_done", { outputPath }); },
    async deckError(error) { await emit("deck_error", { error }); },
  };
}

module.exports = { createReporter };
