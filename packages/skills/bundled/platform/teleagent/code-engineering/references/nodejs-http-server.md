
# Node.js HTTP Server Template

Standard Node.js HTTP server skeleton for TeleAI projects. Zero-dependency, Windows-compatible.

## Core Server (`server.js`)

```javascript
const http = require('http');
const { execFileSync, spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const readline = require('readline');

const PORT = process.env.PORT || 19998;
const HOST = '127.0.0.1';

// --- Python path bridge ---
let pythonPath = null;
function getPythonPath() {
  if (pythonPath) return pythonPath;
  try {
    pythonPath = fs.readFileSync(path.join(__dirname, '.python_path'), 'utf8').trim();
  } catch {
    pythonPath = 'python';
  }
  return pythonPath;
}

// --- Utility: call Python script synchronously ---
function runPython(scriptPath, args = [], timeoutMs = 120000) {
  const py = getPythonPath();
  const result = execFileSync(py, [scriptPath, ...args], {
    encoding: 'utf8',
    timeout: timeoutMs,
    cwd: path.dirname(scriptPath),
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
  });
  return JSON.parse(result);
}

// --- Utility: call Python script asynchronously ---
function spawnPython(scriptPath, args = [], options = {}) {
  const py = getPythonPath();
  const proc = spawn(py, [scriptPath, ...args], {
    cwd: path.dirname(scriptPath),
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    stdio: ['ignore', 'pipe', 'pipe'],
    ...options
  });
  return proc;
}

// --- Request helpers ---
function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', c => chunks.push(c));
    req.on('end', () => resolve(Buffer.concat(chunks).toString()));
    req.on('error', reject);
  });
}

function sendJSON(res, data, status = 200) {
  const body = JSON.stringify(data);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
  });
  res.end(body);
}

function sendError(res, message, status = 500) {
  sendJSON(res, { error: message }, status);
}

function sendFile(res, filePath, contentType) {
  try {
    const content = fs.readFileSync(filePath);
    res.writeHead(200, {
      'Content-Type': contentType,
      'Cache-Control': 'no-cache, no-store, must-revalidate'
    });
    res.end(content);
  } catch (err) {
    sendError(res, 'File not found', 404);
  }
}

// --- URL routing ---
function parseUrl(req) {
  return new URL(req.url, `http://${req.headers.host}`);
}

// --- Server ---
const server = http.createServer(async (req, res) => {
  // CORS preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    });
    res.end();
    return;
  }

  const url = parseUrl(req);

  try {
    // Health check
    if (url.pathname === '/api/health') {
      sendJSON(res, { status: 'ok', uptime: process.uptime() });
      return;
    }

    // --- Route: API endpoint example ---
    if (url.pathname === '/api/example' && req.method === 'GET') {
      const param = url.searchParams.get('param');
      if (!param) {
        sendError(res, 'Missing param', 400);
        return;
      }
      // Call Python backend
      const result = runPython(path.join(__dirname, 'scripts', 'main.py'), [param]);
      sendJSON(res, result);
      return;
    }

    // --- Route: POST with JSON body ---
    if (url.pathname === '/api/data' && req.method === 'POST') {
      const body = await readBody(req);
      const data = JSON.parse(body);
      // Process data...
      sendJSON(res, { received: true });
      return;
    }

    // --- Route: SPA fallback (serve index.html for all non-API routes) ---
    if (!url.pathname.startsWith('/api/')) {
      sendFile(res, path.join(__dirname, 'public', 'index.html'), 'text/html; charset=utf-8');
      return;
    }

    sendError(res, 'Not found', 404);
  } catch (err) {
    console.error(`[ERROR] ${req.method} ${url.pathname}:`, err.message);
    sendError(res, err.message, 500);
  }
});

server.listen(PORT, HOST, () => {
  console.log(`Server running at http://${HOST}:${PORT}`);
});
```

## Key Points

| Concern | Solution |
|---------|----------|
| Chinese path in exec | `execFileSync` with arg array, never command string |
| Python path discovery | `.python_path` bridge file |
| CORS | `OPTIONS` preflight handler + per-response headers |
| No-cache | Every response includes no-cache headers |
| Error handling | try/catch per route, never crash the process |
| URL parsing | `new URL()` (WHATWG), not `url.parse()` |
| JSON output | `Content-Type: application/json; charset=utf-8` |
| Process management | Save spawn process reference for lifecycle control |
| Health check | `/api/health` always available |

## Usage Checklist When Copying

- [ ] Change PORT to the correct port for the project
- [ ] Update route paths to match the actual API design
- [ ] Adjust Python script paths in `runPython` calls
- [ ] Add project-specific middleware (auth, rate limiting, etc.)
- [ ] Verify `.python_path` file exists or Python discovery works
<!-- Updated: 2026-04-26, initial creation -->