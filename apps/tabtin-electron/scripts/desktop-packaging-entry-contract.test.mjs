import assert from 'node:assert/strict'
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readlinkSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

const scriptDirectory = new URL('./', import.meta.url)
const fullBuild = readFileSync(new URL('build-packaged-app.sh', scriptDirectory), 'utf8')
const quickMacBuild = readFileSync(new URL('build-mac-dmg-quick.sh', scriptDirectory), 'utf8')
const frameworkLinkRepair = new URL('repair-macos-framework-links.sh', scriptDirectory)

/** Windows 上裸 bash 会命中 System32 的 WSL 启动器；项目主流程统一用 Git Bash。 */
function resolveBash() {
  if (process.platform !== 'win32') return 'bash'
  const candidates = [
    process.env.TABTIN_BASH,
    'C:\\Program Files\\Git\\bin\\bash.exe',
    'C:\\Program Files\\Git\\usr\\bin\\bash.exe',
  ].filter(Boolean)
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate
  }
  return 'bash'
}

/** Git Bash (MSYS) 只认 /c/... 风格路径。 */
function toMsysPath(url) {
  const p = fileURLToPath(url)
  if (process.platform !== 'win32') return p
  return p.replace(/^([A-Za-z]):/, (_, drive) => `/${drive.toLowerCase()}`).replaceAll('\\', '/')
}

test('packaged build runs typecheck without inheriting the repository i18n prebuild hook', () => {
  assert.match(fullBuild, /pnpm run typecheck\s+node "\$SCRIPT_DIR\/run-electron-vite\.mjs" build/)
  assert.doesNotMatch(fullBuild, /^\s*pnpm build\s*$/m)
})

test('full and quick builds invoke the pinned electron-builder installation', () => {
  for (const source of [fullBuild, quickMacBuild]) {
    assert.match(source, /EXPECTED_ELECTRON_BUILDER_VERSION="25\.1\.8"/)
    assert.match(source, /node "\$ELECTRON_BUILDER_CLI"/)
    assert.doesNotMatch(source, /\bnpx electron-builder\b/)
  }
})

test('local packaging has no private upload credential gate', () => {
  assert.doesNotMatch(fullBuild, /local profile 强制要求 sourcemap 上传/)
  assert.match(fullBuild, /Sourcemap upload failed \(non-fatal\)/)
})

test('packaging reuses the installed Electron runtime and guards optional helpers', () => {
  for (const source of [fullBuild, quickMacBuild]) {
    assert.match(source, /--config\.electronDist=\$INSTALLED_ELECTRON_DIST/)
  }
  assert.match(fullBuild, /if \[ ! -f "\$EMBEDDING_MODEL_FETCH_SCRIPT" \]/)
})

test('packaging uses moved runtime helpers and defers Office download to first preview', () => {
  assert.match(fullBuild, /scripts\/electron\/package\/prepare-python-runtime\.sh/)
  assert.match(fullBuild, /scripts\/electron\/runtime\/fetch-embedding-model\.mjs/)
  assert.doesNotMatch(fullBuild, /scripts\/prepare-python-runtime-for-electron-packaging\.sh/)
  assert.doesNotMatch(fullBuild, /\$REPO_ROOT\/scripts\/fetch-embedding-model\.mjs/)
  assert.match(fullBuild, /fetch-desktop-runtimes\.sh" --only python/)
  assert.match(fullBuild, /stage_office_preview_runtime_download_manifest/)
})

test('local macOS packages always use certificate-free ad-hoc signing', () => {
  for (const source of [fullBuild, quickMacBuild]) {
    assert.match(source, /export CSC_IDENTITY_AUTO_DISCOVERY=false/)
    assert.match(source, /repair-macos-framework-links\.sh" "\$app_bundle"\s+codesign/)
    assert.match(source, /codesign --force --deep --sign - "\$app_bundle"/)
  }
  // fullBuild：local 强制 ad-hoc；community 无 Developer ID 时也兑底 ad-hoc（unset 由 find_developer_id_identity 失败路径处理）。
  assert.match(
    fullBuild,
    /NEED_ADHOC_SIGN=0\s+if \[ "\$PROFILE" = "local" \] \|\| \[ "\$\{CSC_IDENTITY_AUTO_DISCOVERY:-\}" = "false" \]; then\s+NEED_ADHOC_SIGN=1/,
  )
  assert.doesNotMatch(quickMacBuild, /find_developer_id_identity/)
})

test('macOS signing discovers app bundles in the actual and legacy output layouts', () => {
  for (const source of [fullBuild, quickMacBuild]) {
    // 现行布局：根目录/*.app + mac/*.app + mac-ARCH/*.app（fullBuild 三路，quick 两路）。
    assert.match(source, /for app_bundle in "\$[^\"]+"\/\*\.app "\$[^\"]+"\/(mac|mac-\*)\/\*\.app/)
    assert.doesNotMatch(source, /mac-\$\{ARCH\}\/"\*\.app/)
  }
})

test('macOS packaging repairs flattened framework aliases before signing', (t) => {
  // repair-macos-framework-links.sh 只在 macOS 签名流程中运行，且验证目标依赖
  // macOS 的框架 symlink 语义（Versions/Current → A 等）。NTFS 无法创建/读取
  // 这类 symlink（readlink 报 EINVAL），该行为验证只能在 macOS 上执行；
  // 脚本本体仍由 mac 构建机上的完整构建负责覆盖。
  if (process.platform !== 'darwin') {
    t.skip('framework alias repair is macOS-only behavior; NTFS cannot represent these symlinks')
    return
  }
  const root = mkdtempSync(join(tmpdir(), 'tabtin-framework-links-'))
  t.after(() => rmSync(root, { recursive: true, force: true }))
  const appBundle = join(root, 'TabTin.app')
  const framework = join(appBundle, 'Contents', 'Frameworks', 'Example.framework')
  const version = join(framework, 'Versions', 'A')

  mkdirSync(join(version, 'Resources'), { recursive: true })
  writeFileSync(join(version, 'Example'), 'original binary')
  mkdirSync(join(framework, 'Versions', 'Current'), { recursive: true })
  writeFileSync(join(framework, 'Example'), 'binary with applied fuses')
  mkdirSync(join(framework, 'Resources'), { recursive: true })

  const result = spawnSync(resolveBash(), [toMsysPath(frameworkLinkRepair), appBundle], {
    encoding: 'utf8',
  })

  assert.equal(result.status, 0, result.stderr)
  assert.equal(readlinkSync(join(framework, 'Versions', 'Current')), 'A')
  assert.equal(readlinkSync(join(framework, 'Example')), 'Versions/Current/Example')
  assert.equal(readlinkSync(join(framework, 'Resources')), 'Versions/Current/Resources')
  assert.equal(readFileSync(join(framework, 'Example'), 'utf8'), 'binary with applied fuses')
  assert.equal(
    readFileSync(join(framework, 'Versions', 'Current', 'Example'), 'utf8'),
    'binary with applied fuses',
  )
})
