#!/usr/bin/env node
// 构建 ASCII 路径的 deploy 目录（C:\sns-deploy），绕过 pnpm deploy 的 EPERM 和中文路径编码问题。
// 1. 复制 app node_modules（解析 symlink 为真实文件）到 C:\sns-deploy\node_modules
// 2. 剪掉非 win32-x64 平台包（darwin/linux/android/freebsd）
// 3. 复制 out/static/build/package.json/scripts
// 然后从 C:\sns-deploy 跑 electron-builder（纯 ASCII 路径，无中文）
import fs from 'node:fs'
import path from 'node:path'

const REPO = 'D:\\20_工作\\00_项目\\天玑实验室\\智算方舟智能体\\SnSworker'
const APP_DIR = path.join(REPO, 'apps', 'tabtin-electron')
const NM_SRC = path.join(APP_DIR, 'node_modules')
const DEPLOY = 'C:\\sns-deploy'

const log = (m) => console.log(m)

// ---- 1. 解析 symlink 复制 node_modules ----
log('[1/3] 复制 node_modules（解析 symlink 为真实文件）...')
let copiedFiles = 0, copiedDirs = 0, skippedDangling = 0

function copyTreeResolved(src, dest) {
  let st
  try { st = fs.lstatSync(src) } catch { return }
  if (st.isSymbolicLink()) {
    let target
    try { target = fs.realpathSync(src) } catch { skippedDangling++; return }
    let tst
    try { tst = fs.lstatSync(target) } catch { skippedDangling++; return }
    copyTreeResolved(target, dest)
    return
  }
  if (st.isDirectory()) {
    fs.mkdirSync(dest, { recursive: true })
    copiedDirs++
    let entries
    try { entries = fs.readdirSync(src, { withFileTypes: true }) } catch { return }
    for (const ent of entries) {
      copyTreeResolved(path.join(src, ent.name), path.join(dest, ent.name))
    }
    return
  }
  try {
    fs.mkdirSync(path.dirname(dest), { recursive: true })
    fs.copyFileSync(src, dest)
    copiedFiles++
  } catch { /* ignore */ }
}

const nmDest = path.join(DEPLOY, 'node_modules')
if (fs.existsSync(nmDest)) fs.rmSync(nmDest, { recursive: true, force: true, maxRetries: 6, retryDelay: 1000 })
copyTreeResolved(NM_SRC, nmDest)
log(`  node_modules: ${copiedFiles} 文件, ${copiedDirs} 目录, ${skippedDangling} dangling 跳过`)

// ---- 2. 剪掉非 win32-x64 平台包 ----
log('[2/3] 剪掉非 win32-x64 平台包 ...')
const nm = path.join(DEPLOY, 'node_modules')
let removedPkgs = 0
const pnpmDir = path.join(nm, '.pnpm')
if (fs.existsSync(pnpmDir)) {
  for (const ent of fs.readdirSync(pnpmDir, { withFileTypes: true })) {
    if (!ent.isDirectory()) continue
    const name = ent.name
    // 匹配平台后缀：-darwin-, -linux-, -android-, -freebsd-, -win32-（保留 win32-x64）
    const isDarwin = /-darwin-|-darwin_/.test(name)
    const isLinux = /-linux-|-linux_/.test(name)
    const isAndroid = /-android-|-android_/.test(name)
    const isFreebsd = /-freebsd-|-freebsd_/.test(name)
    const isMusl = /-musl-|-musl_/.test(name)
    if (isDarwin || isLinux || isAndroid || isFreebsd || isMusl) {
      try {
        fs.rmSync(path.join(pnpmDir, name), { recursive: true, force: true })
        removedPkgs++
      } catch { /* ignore */ }
    }
  }
}
// 也剪掉顶层的跨平台可选包（如 @img/sharp-darwin-x64）
for (const ent of fs.readdirSync(nm, { withFileTypes: true })) {
  if (ent.isDirectory()) {
    const name = ent.name
    const isDarwin = /-darwin|darwin-/.test(name)
    const isLinux = /-linux|linux-/.test(name)
    const isAndroid = /-android|android-/.test(name)
    if (isDarwin || isLinux || isAndroid) {
      try {
        fs.rmSync(path.join(nm, name), { recursive: true, force: true })
        removedPkgs++
      } catch { /* ignore */ }
    }
  }
}
log(`  剪掉 ${removedPkgs} 个跨平台包`)

// ---- 3. 确保 out/static/build/package.json/scripts 已就位 ----
log('[3/3] 确认 out/static/build/package.json/scripts 就位 ...')
for (const d of ['out', 'static', 'build', 'scripts']) {
  if (fs.existsSync(path.join(DEPLOY, d))) {
    log(`  ${d}/ 已就位`)
  } else {
    log(`  ⚠ ${d}/ 缺失`)
  }
}

// 计算 node_modules 大小
let nmSize = 0, nmCount = 0
function sizeDir(dir) {
  let entries
  try { entries = fs.readdirSync(dir, { withFileTypes: true }) } catch { return }
  for (const ent of entries) {
    const p = path.join(dir, ent.name)
    if (ent.isDirectory()) sizeDir(p)
    else if (ent.isFile()) { try { nmSize += fs.statSync(p).size; nmCount++; } catch {} }
  }
}
sizeDir(nm)
log(`  node_modules: ${(nmSize/1024/1024).toFixed(1)} MB, ${nmCount} 文件`)
log('DEPLOY_ASCII_READY ' + DEPLOY)
