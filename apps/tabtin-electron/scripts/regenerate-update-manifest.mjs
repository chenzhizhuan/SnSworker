#!/usr/bin/env node
/**
 * regenerate-update-manifest.mjs — 重签重建产物后同步 electron-updater 清单校验值
 *
 * 背景（2026-10-12 v1.0.6 Mac 发布事故）：
 *   mac ad-hoc 发布流在 flip fuses 后重签 .app，并用 create-styled-dmg.sh / ditto
 *   重建 DMG 与 ZIP。electron-builder 早先写出的 latest-mac.yml 仍保留重建前旧包的
 *   sha512/size → 客户端升级时报 "sha512 checksum mismatch"。
 *
 * 行为：
 *   按清单 files[] 逐条定位 artifact 目录中的实际文件，重算 sha512(base64) 与
 *   size 并回写；顶层 path 对应条目的 sha512 同步到顶层兼容字段。
 *   - 清单缺失：仅告警退出（不阻塞打包）。
 *   - files[] 引用的文件缺失：保留原值并告警（不阻塞打包）。
 *   - 计算失败（文件读错等）：非零退出，构建脚本 fail closed。
 *
 * 幂等：校验值已一致时直接跳过，不重写文件。
 *
 * 用法：
 *   node regenerate-update-manifest.mjs --artifact-dir <dir> [--manifest latest-mac.yml]
 */
import { createHash } from 'node:crypto'
import { createReadStream, existsSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'

const ROOT_KEYS = ['version', 'files', 'path', 'sha512', 'releaseDate']

function parseArgs(argv) {
  const args = {}
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index]
    if (!token.startsWith('--')) continue
    const key = token.slice(2)
    const next = argv[index + 1]
    if (!next || next.startsWith('--')) {
      args[key] = true
      continue
    }
    args[key] = next
    index += 1
  }
  return args
}

function stripQuotes(value) {
  const trimmed = String(value ?? '').trim()
  if (
    trimmed.length >= 2 &&
    ((trimmed.startsWith("'") && trimmed.endsWith("'")) ||
      (trimmed.startsWith('"') && trimmed.endsWith('"')))
  ) {
    return trimmed.slice(1, -1)
  }
  return trimmed
}

/**
 * 极简解析 electron-builder generic latest*.yml：
 * 顶层标量键 + files[] 列表（`  - url: X` 起条目，`    key: value` 续字段）。
 * 只覆盖这种稳定格式，不做通用 YAML。
 */
function parseManifest(text) {
  const root = {}
  const files = []
  const extraRootKeys = []
  let inFiles = false
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.replace(/\s+$/, '')
    if (!line || /^\s*#/.test(line)) continue
    if (/^files:\s*$/.test(line)) {
      inFiles = true
      continue
    }
    if (inFiles) {
      const item = line.match(/^  - (\w+): ?(.*)$/)
      if (item) {
        files.push({ [item[1]]: stripQuotes(item[2]) })
        continue
      }
      const field = line.match(/^    (\w+): ?(.*)$/)
      if (field && files.length > 0) {
        files[files.length - 1][field[1]] = stripQuotes(field[2])
        continue
      }
      inFiles = false // 列表结束，回落到顶层键
    }
    const kv = line.match(/^(\w+): ?(.*)$/)
    if (kv) {
      const key = kv[1]
      const value = stripQuotes(kv[2])
      if (ROOT_KEYS.includes(key)) {
        root[key] = value
      } else if (!(key in root)) {
        root[key] = value
        extraRootKeys.push(key)
      }
    }
  }
  return { root, files, extraRootKeys }
}

function renderManifest({ root, files, extraRootKeys }) {
  const lines = []
  lines.push(`version: ${root.version ?? ''}`)
  lines.push('files:')
  for (const entry of files) {
    lines.push(`  - url: ${entry.url ?? ''}`)
    for (const key of Object.keys(entry)) {
      if (key === 'url') continue
      lines.push(`    ${key}: ${entry[key] ?? ''}`)
    }
  }
  if (root.path !== undefined) lines.push(`path: ${root.path}`)
  if (root.sha512 !== undefined) lines.push(`sha512: ${root.sha512}`)
  if (root.releaseDate !== undefined) lines.push(`releaseDate: '${root.releaseDate}'`)
  for (const key of extraRootKeys) lines.push(`${key}: ${root[key]}`)
  return `${lines.join('\n')}\n`
}

function sha512Base64(filePath) {
  return new Promise((resolvePromise, reject) => {
    const hash = createHash('sha512')
    const stream = createReadStream(filePath)
    stream.on('data', (chunk) => hash.update(chunk))
    stream.on('error', reject)
    stream.on('end', () => resolvePromise(hash.digest('base64')))
  })
}

async function main() {
  const args = parseArgs(process.argv)
  const artifactDir = resolve(String(args['artifact-dir'] || '.'))
  const manifestName = String(args.manifest || 'latest-mac.yml')
  const manifestPath = join(artifactDir, manifestName)

  if (!existsSync(manifestPath)) {
    console.warn(`[manifest] 未找到 ${manifestPath}，跳过校验值同步`)
    return
  }

  const parsed = parseManifest(readFileSync(manifestPath, 'utf8'))
  if (parsed.files.length === 0) {
    console.warn(`[manifest] ${manifestName} 没有 files[] 条目，跳过`)
    return
  }

  let changed = 0
  for (const entry of parsed.files) {
    if (!entry.url) continue
    const filePath = join(artifactDir, entry.url)
    if (!existsSync(filePath)) {
      console.warn(`[manifest] ⚠ files[] 引用的文件不存在，保留原值: ${entry.url}`)
      continue
    }
    const size = statSync(filePath).size
    const sha512 = await sha512Base64(filePath)
    if (entry.sha512 !== sha512 || String(entry.size) !== String(size)) {
      console.log(`[manifest] · ${entry.url}`)
      console.log(`    sha512: ${entry.sha512 ?? '(空)'} → ${sha512}`)
      console.log(`    size:   ${entry.size ?? '(空)'} → ${size}`)
      entry.sha512 = sha512
      entry.size = size
      changed += 1
    }
  }

  // 顶层兼容字段：path 指向的条目即 electron-updater 实际下载对象（mac 为 zip）。
  if (parsed.root.path) {
    const pathEntry = parsed.files.find((entry) => entry.url === parsed.root.path)
    if (pathEntry && parsed.root.sha512 !== pathEntry.sha512) {
      parsed.root.sha512 = pathEntry.sha512
      changed += 1
    }
  }

  if (changed === 0) {
    console.log(`[manifest] ✓ ${manifestName} 校验值与实际产物一致，无需更新`)
    return
  }

  writeFileSync(manifestPath, renderManifest(parsed), 'utf8')
  console.log(`[manifest] ✓ 已重写 ${manifestPath}（同步 ${changed} 处校验值）`)
}

main().catch((error) => {
  console.error(`[manifest] ✗ ${error instanceof Error ? error.message : String(error)}`)
  process.exitCode = 1
})
