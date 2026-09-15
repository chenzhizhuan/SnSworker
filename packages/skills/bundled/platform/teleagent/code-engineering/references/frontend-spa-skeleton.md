
# Frontend SPA Skeleton Template

Standard single-page application skeleton for TeleAI projects. HTML + CSS + vanilla JS + ECharts.

## HTML Structure (`public/index.html`)

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Page Title</title>
  <!-- ECharts (CDN with local fallback) -->
  <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
  <style>
    /* === Reset & Base === */
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #1f2937; background: #f8fafc; }

    /* === Layout === */
    .container { max-width: 1400px; margin: 0 auto; padding: 16px; display: flex; gap: 16px; min-height: 100vh; }
    .sidebar { width: 280px; flex-shrink: 0; }
    .main { flex: 1; min-width: 0; }

    /* === Cards === */
    .card { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.08); padding: 16px; margin-bottom: 16px; }
    .card-title { font-size: 14px; font-weight: 600; color: #64748b; margin-bottom: 12px; text-transform: uppercase; letter-spacing: .5px; }

    /* === Stats Grid === */
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
    .stat-item { text-align: center; padding: 12px; }
    .stat-value { font-size: 24px; font-weight: 700; }
    .stat-label { font-size: 12px; color: #94a3b8; margin-top: 4px; }

    /* === Form Elements === */
    .input-group { margin-bottom: 12px; position: relative; }
    .input-group label { display: block; font-size: 13px; font-weight: 500; color: #475569; margin-bottom: 4px; }
    .input-group input, .input-group select {
      width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 14px; transition: border-color .2s;
    }
    .input-group input:focus, .input-group select:focus {
      outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,.1);
    }

    /* === Buttons === */
    .btn {
      padding: 8px 16px; border: none; border-radius: 6px; font-size: 14px; font-weight: 500;
      cursor: pointer; transition: all .2s; display: inline-flex; align-items: center; gap: 6px;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { background: #94a3b8; cursor: not-allowed; }
    .btn-danger { background: #ef4444; color: #fff; }
    .btn-danger:hover { background: #dc2626; }

    /* === Tables === */
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th { background: #f1f5f9; font-weight: 600; text-align: left; padding: 8px 12px; border-bottom: 2px solid #e2e8f0; }
    td { padding: 8px 12px; border-bottom: 1px solid #f1f5f9; }
    tr:hover td { background: #f8fafc; }

    /* === Dropdown (Search) === */
    .dropdown { position: absolute; top: 100%; left: 0; right: 0; z-index: 100; max-height: 200px; overflow-y: auto;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,.1); display: none; }
    .dropdown.show { display: block; }
    .dropdown-item { padding: 8px 12px; cursor: pointer; font-size: 14px; }
    .dropdown-item:hover, .dropdown-item.active { background: #eff6ff; color: #2563eb; }

    /* === Chart Container === */
    .chart-container { width: 100%; height: 400px; }

    /* === Loading & Toast === */
    .loading { display: inline-block; width: 16px; height: 16px; border: 2px solid #fff; border-top-color: transparent;
      border-radius: 50%; animation: spin .6s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .toast { position: fixed; top: 20px; right: 20px; padding: 12px 20px; border-radius: 8px; color: #fff;
      font-size: 14px; z-index: 9999; opacity: 0; transition: opacity .3s; }
    .toast.show { opacity: 1; }
    .toast-success { background: #22c55e; }
    .toast-error { background: #ef4444; }
    .toast-info { background: #3b82f6; }

    /* === Log Panel === */
    .log-panel { background: #0f172a; color: #e2e8f0; font-family: "Cascadia Code", Consolas, monospace;
      font-size: 12px; padding: 12px; border-radius: 6px; max-height: 200px; overflow-y: auto; line-height: 1.6; }
    .log-time { color: #64748b; }
    .log-info { color: #38bdf8; }
    .log-error { color: #f87171; }
    .log-success { color: #4ade80; }

    /* === Responsive === */
    @media (max-width: 768px) {
      .container { flex-direction: column; }
      .sidebar { width: 100%; }
      .chart-container { height: 300px; }
      .stats-grid { grid-template-columns: repeat(2, 1fr); }
    }
  </style>
</head>
<body>
  <div class="container">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="card">
        <div class="card-title">Control Panel</div>
        <div class="input-group">
          <label>Search</label>
          <input type="text" id="searchInput" placeholder="Input keyword..." autocomplete="off">
          <div class="dropdown" id="searchDropdown"></div>
        </div>
        <div class="input-group">
          <label>Options</label>
          <select id="optionSelect">
            <option value="">-- Select --</option>
          </select>
        </div>
        <button class="btn btn-primary" id="analyzeBtn" style="width:100%" onclick="doAnalyze()">
          Analyze
        </button>
      </div>
      <div class="card">
        <div class="card-title">Log</div>
        <div class="log-panel" id="logPanel"></div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main" id="mainContent">
      <div class="card">
        <div class="card-title">Statistics</div>
        <div class="stats-grid" id="statsGrid">
          <!-- Filled by JS -->
        </div>
      </div>
      <div class="card">
        <div class="card-title">Chart</div>
        <div class="chart-container" id="mainChart"></div>
      </div>
      <div class="card">
        <div class="card-title">Data Table</div>
        <div class="table-wrap" id="tableWrap">
          <!-- Filled by JS -->
        </div>
      </div>
    </main>
  </div>

  <!-- Toast -->
  <div class="toast" id="toast"></div>

  <script>
    const API_ORIGIN = location.origin;  // Dynamic, never hardcode localhost
    const API_BASE = API_ORIGIN + '/api';

    // === Logging ===
    function log(msg, level = 'info') {
      const panel = document.getElementById('logPanel');
      const ts = new Date().toLocaleTimeString();
      panel.innerHTML += `<div><span class="log-time">[${ts}]</span> <span class="log-${level}">${msg}</span></div>`;
      panel.scrollTop = panel.scrollHeight;
    }

    // === Toast ===
    function showToast(msg, type = 'info', duration = 3000) {
      const el = document.getElementById('toast');
      el.textContent = msg;
      el.className = `toast toast-${type} show`;
      setTimeout(() => el.classList.remove('show'), duration);
    }

    // === Fetch wrapper with timeout and error check ===
    async function apiFetch(path, options = {}, timeoutMs = 30000) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      try {
        const url = path.startsWith('http') ? path : (API_BASE + path);
        const resp = await fetch(url, { ...options, signal: controller.signal });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);
        return await resp.json();
      } finally {
        clearTimeout(timer);
      }
    }

    // === ECharts instance management (dispose before re-render) ===
    const chartInstances = {};
    function getOrCreateChart(domId) {
      if (chartInstances[domId]) {
        chartInstances[domId].dispose();
      }
      const dom = document.getElementById(domId);
      chartInstances[domId] = echarts.init(dom);
      return chartInstances[domId];
    }

    // === Search dropdown ===
    function showDropdown(items, containerId, onSelect) {
      const dd = document.getElementById(containerId);
      dd.innerHTML = items.map((item, i) =>
        `<div class="dropdown-item" data-index="${i}">${item.label}</div>`
      ).join('');
      dd.classList.add('show');
      dd.querySelectorAll('.dropdown-item').forEach(el => {
        el.addEventListener('click', () => {
          onSelect(items[parseInt(el.dataset.index)]);
          dd.classList.remove('show');
        });
      });
      // Close on outside click
      const close = (e) => { if (!dd.contains(e.target)) { dd.classList.remove('show'); document.removeEventListener('click', close); } };
      setTimeout(() => document.addEventListener('click', close), 0);
    }

    // === Extract clean symbol from input ===
    function extractValue(input) {
      return input.trim().split(/\s+/)[0];
    }

    // === Main analysis function ===
    async function doAnalyze() {
      const btn = document.getElementById('analyzeBtn');
      const value = extractValue(document.getElementById('searchInput').value);
      if (!value) { showToast('Please input a value', 'error'); return; }

      btn.disabled = true;
      btn.innerHTML = '<span class="loading"></span> Loading...';
      log(`Starting analysis: ${value}`);

      try {
        const data = await apiFetch(`/analyze?param=${encodeURIComponent(value)}`, {}, 120000);
        if (data.code !== 0) throw new Error(data.message);
        log('Analysis complete', 'success');
        showToast('Done', 'success');
        renderResults(data.data);
      } catch (err) {
        log(`Error: ${err.message}`, 'error');
        showToast(err.message, 'error');
      } finally {
        btn.disabled = false;
        btn.textContent = 'Analyze';
      }
    }

    // === Render results ===
    function renderResults(data) {
      // Stats
      const statsHtml = Object.entries(data.stats || {}).map(([label, val]) =>
        `<div class="stat-item"><div class="stat-value">${val}</div><div class="stat-label">${label}</div></div>`
      ).join('');
      document.getElementById('statsGrid').innerHTML = statsHtml;

      // Chart
      const chart = getOrCreateChart('mainChart');
      chart.setOption(data.chartOption || {});

      // Table
      const rows = (data.table || []).map(row =>
        `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`
      ).join('');
      const headers = (data.tableHeaders || []).map(h => `<th>${h}</th>`).join('');
      document.getElementById('tableWrap').innerHTML =
        `<table><thead><tr>${headers}</tr></thead><tbody>${rows}</tbody></table>`;
    }

    // === Init ===
    document.getElementById('searchInput').addEventListener('input', function() {
      const q = this.value.trim();
      if (q.length < 1) { document.getElementById('searchDropdown').classList.remove('show'); return; }
      // Debounced search
      clearTimeout(this._timer);
      this._timer = setTimeout(async () => {
        try {
          const data = await apiFetch(`/search?q=${encodeURIComponent(q)}`, {}, 10000);
          if (data.code === 0 && data.data.length > 0) {
            showDropdown(data.data, 'searchDropdown', (item) => {
              document.getElementById('searchInput').value = item.label;
            });
          }
        } catch {}
      }, 300);
    });
  </script>
</body>
</html>
```

## Key Points

| Concern | Solution |
|---------|----------|
| Dynamic API URL | `location.origin` instead of hardcoded localhost |
| Fetch safety | `apiFetch()` wrapper: HTTP check + AbortSignal timeout |
| ECharts lifecycle | `getOrCreateChart()` disposes old instance before re-rendering |
| Dropdown | Click-outside close, debounced search input |
| Value extraction | `extractValue()` trims and splits for clean input |
| Responsive | Flexbox column on mobile, reduced chart height, grid columns |
| Chinese color standard | Stock colors: up red `#cf222e`, down green `#1a7f37`, neutral `#0966da` |
| Loading state | Button disabled + spinner during async operations |
| Toast notifications | `showToast()` with auto-dismiss |

## Usage Checklist When Copying

- [ ] Update page title and card titles
- [ ] Customize stats grid fields for the domain
- [ ] Replace `doAnalyze()` with actual API calls and rendering logic
- [ ] Adjust chart option structure for the specific ECharts chart type
- [ ] Add domain-specific color scheme if not stock-related
- [ ] Customize sidebar controls for the actual input parameters
- [ ] Test on mobile viewport (< 768px)
<!-- Updated: 2026-04-26, initial creation -->