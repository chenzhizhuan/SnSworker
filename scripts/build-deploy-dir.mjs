#!/usr/bin/env node
// 手动构建 deploy 目录（绕过 pnpm deploy 的 Windows EPERM rename 问题）。
// 从 app 的 node_modules（pnpm symlink 树）解析出真实文件，复制到 deploy 目录。
// dangling symlink（目标不存在）跳过。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..');
const APP_DIR = path.join(REPO_ROOT, 'apps', 'tabtin-electron');
const NM_SRC = path.join(APP_DIR, 'node_modules');

const profile = process.argv[2] || 'community';
const arch = process.argv[3] || 'x64';
const runId = process.argv[4] || new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
const DEPLOY_DIR = path.join(REPO_ROOT, '.deploy-runs', `${profile}-win-${arch}-manual-${runId}`);

const log = (m) => console.log(m);

if (fs.existsSync(DEPLOY_DIR)) {
  log(`清理旧 deploy 目录: ${DEPLOY_DIR}`);
  fs.rmSync(DEPLOY_DIR, { recursive: true, force: true, maxRetries: 6, retryDelay: 1500 });
}
fs.mkdirSync(DEPLOY_DIR, { recursive: true });

log('[1/3] 复制 node_modules（解析 symlink，跳过 dangling）...');
let copiedFiles = 0, copiedDirs = 0, skippedDangling = 0;

function copyTreeResolved(src, dest) {
  let st;
  try { st = fs.lstatSync(src); } catch { return; }
  if (st.isSymbolicLink()) {
    let target;
    try { target = fs.realpathSync(src); } catch { skippedDangling++; return; }
    let tst;
    try { tst = fs.lstatSync(target); } catch { skippedDangling++; return; }
    copyTreeResolved(target, dest);
    return;
  }
  if (st.isDirectory()) {
    fs.mkdirSync(dest, { recursive: true });
    copiedDirs++;
    let entries;
    try { entries = fs.readdirSync(src, { withFileTypes: true }); } catch { return; }
    for (const ent of entries) {
      copyTreeResolved(path.join(src, ent.name), path.join(dest, ent.name));
    }
    return;
  }
  try {
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(src, dest);
    copiedFiles++;
  } catch { /* ignore */ }
}

copyTreeResolved(NM_SRC, path.join(DEPLOY_DIR, 'node_modules'));
log(`  node_modules: ${copiedFiles} 文件, ${copiedDirs} 目录, ${skippedDangling} dangling 跳过`);

function cpDirReal(src, dest) {
  if (!fs.existsSync(src)) return;
  if (fs.existsSync(dest)) fs.rmSync(dest, { recursive: true, force: true });
  fs.mkdirSync(dest, { recursive: true });
  for (const ent of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, ent.name);
    const d = path.join(dest, ent.name);
    if (ent.isDirectory()) cpDirReal(s, d);
    else if (ent.isFile()) fs.copyFileSync(s, d);
    else if (ent.isSymbolicLink()) {
      try {
        const t = fs.realpathSync(s);
        const tst = fs.lstatSync(t);
        if (tst.isDirectory()) cpDirReal(t, d);
        else fs.copyFileSync(t, d);
      } catch { /* skip */ }
    }
  }
}

log('[2/3] 复制 out / static / build / package.json / scripts ...');
cpDirReal(path.join(APP_DIR, 'out'), path.join(DEPLOY_DIR, 'out'));
cpDirReal(path.join(APP_DIR, 'static'), path.join(DEPLOY_DIR, 'static'));
cpDirReal(path.join(APP_DIR, 'build'), path.join(DEPLOY_DIR, 'build'));
if (fs.existsSync(path.join(APP_DIR, 'package.json'))) {
  fs.copyFileSync(path.join(APP_DIR, 'package.json'), path.join(DEPLOY_DIR, 'package.json'));
}
for (const f of ['flip-electron-fuses.cjs', 'audit-packaged-artifact.mjs', 'after-sign-notarize.cjs', 'win-wosign-sign.cjs']) {
  const s = path.join(APP_DIR, 'scripts', f);
  if (fs.existsSync(s)) {
    fs.mkdirSync(path.join(DEPLOY_DIR, 'scripts'), { recursive: true });
    fs.copyFileSync(s, path.join(DEPLOY_DIR, 'scripts', f));
  }
}

log('[3/3] 复制 extraResources 源目录（绝对路径存于 manifest 供 electron-builder 重写）...');
const extraResourcesFrom = {
  'tabsite-templates': 'packages/tabsite-templates',
  'personal-plugins': 'packages/agent-runtime/fixtures/personal-plugins',
  'bundled-skills-src': 'packages/skills/bundled',
  'tabtracker-src': 'packages/skills/tabtracker',
  'packages-apps-src': 'packages/apps',
  'official-plugins': 'packages/agent-runtime/src/official-plugins/fixtures',
  'scrcpy-server.jar': 'apps/tabtin-electron/resources/scrcpy-server.jar',
  'models': 'apps/tabtin-electron/resources/models',
};
const staged = {};
for (const [key, rel] of Object.entries(extraResourcesFrom)) {
  const abs = path.join(REPO_ROOT, rel);
  if (fs.existsSync(abs)) {
    const d = path.join(DEPLOY_DIR, key);
    cpDirReal(abs, d);
    staged[key] = d;
  } else {
    staged[key] = null;
  }
}
log('  staged: ' + Object.entries(staged).filter(([, v]) => v).map(([k]) => k).join(', '));

// 写 manifest，记录 deploy 目录与 REPO_ROOT（electron-builder 重写 extraResources 用）
fs.writeFileSync(
  path.join(DEPLOY_DIR, 'deploy-manifest.json'),
  JSON.stringify({ deployDir: DEPLOY_DIR, repoRoot: REPO_ROOT, staged }, null, 2),
);

log('DEPLOY_OK ' + DEPLOY_DIR);
