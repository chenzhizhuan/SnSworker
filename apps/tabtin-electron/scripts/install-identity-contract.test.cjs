const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')

const scriptPath = path.join(__dirname, 'build-packaged-app.sh')
const installerPath = path.join(__dirname, '..', 'build', 'installer.nsh')
const buildScript = fs.readFileSync(scriptPath, 'utf8')
const quickMacBuildScript = fs.readFileSync(
  path.join(__dirname, 'build-mac-dmg-quick.sh'),
  'utf8',
)
const installer = fs.readFileSync(installerPath, 'utf8')
const packageJson = JSON.parse(
  fs.readFileSync(path.join(__dirname, '..', 'package.json'), 'utf8'),
)
const pnpmStore = path.join(__dirname, '..', '..', '..', 'node_modules', '.pnpm')
const appBuilderLibPackage = fs.readdirSync(pnpmStore).find((entry) =>
  entry.startsWith('app-builder-lib@'),
)
assert.ok(appBuilderLibPackage, 'app-builder-lib must be installed for packaging contract tests')
const { AppInfo } = require(path.join(
  pnpmStore,
  appBuilderLibPackage,
  'node_modules',
  'app-builder-lib',
  'out',
  'appInfo.js',
))

// macOS 的系统可见品牌必须来自最终 builder 配置，而不是运行时 app.setName()。
// 这样 Finder、Dock、DMG 与权限弹窗在应用启动前就能显示一致的名称和图标。
assert.equal(packageJson.build.productName, '智算方舟')
assert.equal(packageJson.build.mac.icon, 'build/icons/icon.icns')
assert.equal(packageJson.build.dmg.icon, 'build/icons/icon.icns')
assert.equal(packageJson.build.mac.extendInfo.CFBundleDisplayName, '智算方舟')
assert.equal(packageJson.build.mac.extendInfo.CFBundleName, '智算方舟')
assert.doesNotMatch(JSON.stringify(packageJson.build.mac.extendInfo), /SnSworker/)
const macAppInfo = new AppInfo(
  { metadata: packageJson, config: packageJson.build },
  null,
  packageJson.build.mac,
  true,
)
assert.equal(macAppInfo.productFilename, '智算方舟')

// 开源版发行身份：Local（本地自测）+ Community（社区发行）。
// 内部版 Preprod profile 已在开源化时移除（installer.nsh 仍保留 Preprod 残留清理）。
assert.ok(buildScript.includes('PROFILE_PRODUCT_NAME="智算方舟 Local"'))
assert.ok(buildScript.includes('PROFILE_APP_ID="com.zhifangfang.app.local"'))
assert.ok(buildScript.includes('PROFILE_EXECUTABLE_NAME="snsworker-local"'))
assert.ok(buildScript.includes('PROFILE_SHORTCUT_NAME="智算方舟 Local"'))
assert.ok(buildScript.includes('PROFILE_PRODUCT_NAME="智算方舟"'))
assert.ok(buildScript.includes('PROFILE_APP_ID="com.zhifangfang.community"'))
assert.ok(buildScript.includes('PROFILE_EXECUTABLE_NAME="snsworker"'))
assert.ok(buildScript.includes('PROFILE_SHORTCUT_NAME="智算方舟"'))
assert.match(
  buildScript,
  /if \[ "\$TARGET_RUNTIME" = "darwin" \]; then\s+PROFILE_PRODUCT_NAME="智算方舟"\s+PROFILE_EXECUTABLE_NAME=""\s+fi/,
)
// executableName 的目标平台已参数化（win/dmg 共用同一段）。
assert.ok(buildScript.includes('"--config.${TARGET_NAME}.executableName=$PROFILE_EXECUTABLE_NAME"'))
assert.ok(buildScript.includes('if [ -n "$PROFILE_EXECUTABLE_NAME" ]; then'))
assert.ok(buildScript.includes('"--config.nsis.shortcutName=$PROFILE_SHORTCUT_NAME"'))
assert.ok(quickMacBuildScript.includes('PROFILE_PRODUCT_NAME="智算方舟"'))
assert.ok(quickMacBuildScript.includes('PROFILE_APP_ID="com.zhifangfang.app.local"'))
assert.ok(!quickMacBuildScript.includes('executableName: "snsworker"'))

const appIdentity = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'main', 'app-identity.ts'),
  'utf8',
)
assert.ok(appIdentity.includes('process.env.TABTIN_DATA_ROOT = profileRoot'))
assert.ok(appIdentity.includes("process.env.TABTIN_RUNTIME_ROOT = join(profileRoot, 'runtime')"))

const deepLink = fs.readFileSync(path.join(__dirname, '..', 'src', 'main', 'deep-link.ts'), 'utf8')
assert.ok(deepLink.includes('resolveTabTinProtocolScheme'))
assert.ok(deepLink.includes('app.setAsDefaultProtocolClient(deepLinkScheme)'))

const notifyLaunch = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'main', 'services', 'notification', 'notify-launch.ts'),
  'utf8',
)
assert.ok(notifyLaunch.includes('resolveTabTinProtocolScheme'))
assert.ok(notifyLaunch.includes('${scheme}://${TOAST_NOTIFY_HOST}'))
// Keep the newer release cleanup contract: uninstall removes credentials and
// optional config/cache for every known profile, while preserving workspaces.
for (const profile of ['SnSworker', 'SnSworker Dev', 'SnSworker Local', 'SnSworker Preprod', 'tabtin-electron']) {
  assert.ok(installer.includes(`Delete "$APPDATA\\${profile}\\credentials.json"`))
  assert.ok(installer.includes(`!insertmacro wipeTabTinProfileConfig "$APPDATA\\${profile}"`))
}
assert.ok(installer.includes('$PROFILE\\.tabtin\\server.json'))
assert.ok(installer.includes('$PROFILE\\.tabtin-daemon'))
assert.ok(installer.includes('$LOCALAPPDATA\\com.snsworker.app.preprod-updater'))
assert.ok(!installer.includes('RMDir /r "$APPDATA\\SnSworker"'))

console.log('install identity contract: ok')
