// =====================================================================
// 前端 · SSE 客户端 + DOM 更新
// =====================================================================
"use strict";

const $ = (id) => document.getElementById(id);
const STATUS_LABEL = {
  pending: "待生成", building: "构建中", built: "已构建",
  rendering: "渲染中", rendered: "已渲染", failed: "渲染失败",
};
const STATUS_BADGE = {
  pending: "badge-pending", building: "badge-building", built: "badge-built",
  rendering: "badge-rendering", rendered: "badge-rendered", failed: "badge-failed",
};

const state = {
  deck: { title: "", author: "", theme: "telecom-red", totalPages: 0, outputPath: "", startedAt: null, finishedAt: null },
  status: "idle",
  slides: [],
  stats: { built: 0, rendered: 0, failed: 0 },
};

// ============== DOM helpers ==============
function fmtTime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("zh-CN", { hour12: false });
  } catch { return "—"; }
}
function fmtDuration(ms) {
  if (!ms || ms < 0) return "00:00";
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return String(m).padStart(2, "0") + ":" + String(sec).padStart(2, "0");
}
function statusBadge(status) {
  return `<span class="badge ${STATUS_BADGE[status] || "badge-pending"}">${STATUS_LABEL[status] || status}</span>`;
}

// ============== Render ==============
function renderDeck() {
  $("deck-title").textContent = state.deck.title || "等待生成脚本接入…";
  $("deck-title").title = state.deck.title || "";
  $("deck-theme").textContent = state.deck.theme === "telecom-red" ? "电信红" : (state.deck.theme || "—");
  $("deck-total").textContent = state.deck.totalPages || 0;
  $("stat-total").textContent = state.deck.totalPages || 0;
  const statusMap = { idle: "待机", running: "生成中", done: "已完成", error: "出错" };
  $("deck-status").textContent = statusMap[state.status] || state.status;
  const elapsedMs = state.deck.startedAt
    ? ((state.deck.finishedAt ? new Date(state.deck.finishedAt) : new Date()) - new Date(state.deck.startedAt))
    : 0;
  $("deck-elapsed").textContent = fmtDuration(elapsedMs);

  // 总进度：渲染完成数 / 总页数
  const total = state.deck.totalPages || 0;
  const rendered = state.stats.rendered || 0;
  const built = state.stats.built || 0;
  // 综合：构建占50%，渲染占50%
  const pct = total > 0 ? Math.round((built * 0.5 + rendered * 0.5) / total * 100) : 0;
  $("progress-fill").style.width = pct + "%";
  $("progress-text").textContent = pct + "%";
  $("stat-built").textContent = built;
  $("stat-rendered").textContent = rendered;
  $("stat-failed").textContent = state.stats.failed || 0;

  // 当前动作
  const action = currentActionText();
  $("current-action").textContent = action;
  $("current-action").style.color = state.status === "error" ? "var(--status-failed)" : "var(--primary)";
}

function currentActionText() {
  if (state.status === "idle") return "等待开始…";
  if (state.status === "done") return `✓ 全部完成 · ${fmtDuration(((state.deck.finishedAt ? new Date(state.deck.finishedAt) : new Date()) - new Date(state.deck.startedAt)))}`;
  if (state.status === "error") return "✗ 生成出错，查看日志";
  // running
  const rendering = state.slides.find(s => s && s.status === "rendering");
  if (rendering) return `正在渲染第 ${rendering.idx + 1} 页…`;
  const building = state.slides.find(s => s && s.status === "building");
  if (building) return `正在构建第 ${building.idx + 1} 页…`;
  const pending = state.slides.find(s => s && s.status === "pending");
  if (pending) return `等待构建第 ${pending.idx + 1} 页…`;
  return "等待中…";
}

function renderGrid() {
  const grid = $("grid");
  if (!state.slides.length) {
    if (!$("placeholder")) {
      grid.innerHTML = `<div class="placeholder" id="placeholder">尚无页面信息。启动生成脚本后这里会逐页显示进度和缩略图。</div>`;
    }
    return;
  }
  // 重绘
  let html = "";
  state.slides.forEach((s) => { html += slideCardHTML(s); });
  grid.innerHTML = html;
  // 触发缩略图加载
  state.slides.forEach((s) => { tryLoadThumb(s); });
}

function slideCardHTML(s) {
  if (!s) return "";
  const cls = ["slide-card"];
  if (s.status === "building" || s.status === "rendering") cls.push("is-active");
  if (s.status === "failed") cls.push("is-failed");

  let thumb = "";
  if (s.thumbnail && s.status === "rendered") {
    thumb = `<img data-src="${s.thumbnail}" alt="slide-${s.idx + 1}" onload="this.classList.add('loaded')">`;
  } else if (s.status === "rendering") {
    thumb = `<div class="thumb-placeholder"><div class="thumb-spinner"></div><div>渲染中…</div></div>`;
  } else if (s.status === "building") {
    thumb = `<div class="thumb-placeholder"><div class="thumb-spinner"></div><div>构建中…</div></div>`;
  } else if (s.status === "failed") {
    thumb = `<div class="thumb-placeholder"><div class="icon">!</div><div>渲染失败</div></div>`;
  } else {
    thumb = `<div class="thumb-placeholder"><div class="icon">${s.idx + 1}</div><div>等待生成</div></div>`;
  }

  const titleText = s.title || `第 ${s.idx + 1} 页`;
  const tplText = s.template || "";
  const foot = s.status === "failed"
    ? `<span class="err">${escapeHTML(s.error || "渲染失败")}</span><span></span>`
    : `<span>构建 ${s.buildMs || 0}ms</span><span>${s.renderMs ? "渲染 " + s.renderMs + "ms" : ""}</span>`;

  return `
    <div class="${cls.join(" ")}" id="card-${s.idx}">
      <div class="card-head">
        <div class="card-head-left">
          <span class="page-no">${s.idx + 1}</span>
          <span class="card-title" title="${escapeHTML(titleText)}">${escapeHTML(titleText)}</span>
        </div>
        ${statusBadge(s.status)}
      </div>
      <div class="thumb-wrap">${thumb}</div>
      <div class="card-foot">
        <span class="template-tag" title="${escapeHTML(tplText)}">${escapeHTML(tplText || "—")}</span>
        ${foot}
      </div>
    </div>`;
}

function tryLoadThumb(s) {
  if (!s || !s.thumbnail || s.status !== "rendered") return;
  const card = $("card-" + s.idx);
  if (!card) return;
  const img = card.querySelector("img");
  if (!img) return;
  if (img.src) return; // 已加载
  // 加时间戳防缓存（rendered 后立即刷新）
  img.src = s.thumbnail + "?t=" + Date.now();
}

function updateSlideCard(s) {
  if (!s) return;
  const cardOld = $("card-" + s.idx);
  if (!cardOld) {
    // 重新构建整个 grid
    renderGrid();
    return;
  }
  // 用 outerHTML 替换
  const wrap = document.createElement("div");
  wrap.innerHTML = slideCardHTML(s);
  const newCard = wrap.firstElementChild;
  cardOld.replaceWith(newCard);
  tryLoadThumb(s);
}

function escapeHTML(str) {
  return String(str || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ============== Log ==============
function appendLog(entry) {
  state._logs = state._logs || [];
  state._logs.push(entry);
  if (state._logs.length > 300) state._logs.shift();
  const body = $("log-body");
  const line = document.createElement("div");
  line.className = "log-line level-" + (entry.level || "info");
  line.innerHTML = `<span class="log-time">${escapeHTML(fmtTime(entry.t))}</span><span class="log-msg">${escapeHTML(entry.msg)}</span>`;
  body.appendChild(line);
  $("log-count").textContent = state._logs.length;
  // 自动滚到底（如果用户没在上拉）
  if (body.scrollHeight - body.scrollTop - body.clientHeight < 60) {
    body.scrollTop = body.scrollHeight;
  }
}

function rebuildLog() {
  const body = $("log-body");
  body.innerHTML = "";
  (state._logs || []).forEach((e) => {
    const line = document.createElement("div");
    line.className = "log-line level-" + (e.level || "info");
    line.innerHTML = `<span class="log-time">${escapeHTML(fmtTime(e.t))}</span><span class="log-msg">${escapeHTML(e.msg)}</span>`;
    body.appendChild(line);
  });
  $("log-count").textContent = (state._logs || []).length;
  body.scrollTop = body.scrollHeight;
}

// ============== SSE ==============
function connectSSE() {
  const es = new EventSource("/api/events");
  es.onmessage = (e) => {
    let ev;
    try { ev = JSON.parse(e.data); } catch { return; }
    dispatchEvent(ev);
  };
  es.onerror = () => {
    // 浏览器自动重连，这里仅同步状态
    $("current-action").textContent = "连接断开，重连中…";
  };
}

function dispatchEvent(ev) {
  const { type, data } = ev;
  switch (type) {
    case "snapshot":
      // 全量状态恢复
      Object.assign(state.deck, data.deck || {});
      state.status = data.status || "idle";
      state.slides = (data.slides || []).map(s => s ? { ...s } : null);
      state.stats = data.stats || { built: 0, rendered: 0, failed: 0 };
      state._logs = data.logs || [];
      renderDeck();
      renderGrid();
      rebuildLog();
      break;
    case "reset":
      state.slides = new Array(data.totalPages || 0).fill(null).map((_, i) => ({
        idx: i, title: "", template: "", status: "pending", thumbnail: "", error: "", buildMs: 0, renderMs: 0,
      }));
      state._logs = [];
      renderDeck();
      renderGrid();
      rebuildLog();
      break;
    case "deck_update":
      Object.assign(state.deck, data);
      renderDeck();
      break;
    case "status_update":
      state.status = data.status || state.status;
      renderDeck();
      break;
    case "slide_update":
      state.slides[data.idx] = { ...state.slides[data.idx], ...data };
      updateSlideCard(state.slides[data.idx]);
      renderDeck();
      break;
    case "stats":
      state.stats = data;
      renderDeck();
      break;
    case "log":
      appendLog(data);
      break;
  }
}

// ============== Init ==============
document.addEventListener("DOMContentLoaded", () => {
  // 折叠日志面板
  $("log-toggle").addEventListener("click", () => {
    $("log-panel").classList.toggle("collapsed");
  });
  // 默认折叠
  // $("log-panel").classList.add("collapsed");

  // 每秒刷新用时
  setInterval(() => {
    if (state.status === "running") renderDeck();
  }, 1000);

  connectSSE();
});
