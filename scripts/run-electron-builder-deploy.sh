#!/bin/bash
# 从手动构建的 deploy 目录跑 electron-builder（community win x64）。
# 重写 extraResources 的 from 为绝对路径（指向 REPO_ROOT），因为 deploy 目录不在 app 目录下。
set -euo pipefail

DEPLOY_DIR="$(cd "$1" && pwd)"
REPO_ROOT="$(cd "$DEPLOY_DIR/../../.." && pwd)"   # deploy 在 SnSworker/.deploy-runs/<run>/ → 上 3 级是 智算方舟智能体，上 4 级... 重新算
# deploy 目录 = REPO_ROOT/.deploy-runs/<run>。REPO_ROOT = SnSworker。
# 从 deploy 目录: .. = .deploy-runs, ../.. = SnSworker (REPO_ROOT), 所以 REPO_ROOT = ../../
REPO_ROOT="$(cd "$DEPLOY_DIR/../.." && pwd)"

APP_DIR="$REPO_ROOT/apps/tabtin-electron"
ELECTRON_BUILDER_CLI="$APP_DIR/node_modules/electron-builder/cli.js"
ELECTRON_DIST="$APP_DIR/node_modules/electron/dist"
ELECTRON_VERSION="$(node -p "require('$APP_DIR/node_modules/electron/package.json').version")"

# 从 deploy-manifest.json 读取 staged 目录
STAGED="$(node -e 'const m=require(process.argv[1]); process.stdout.write(JSON.stringify(m.staged))' "$DEPLOY_DIR/deploy-manifest.json")"

# 生成 extraResources 重写：把每个 from 的绝对路径替换
# 原 package.json 的 extraResources 结构（from/to/filter）。这里用 --config 覆盖整个 extraResources 数组。
EXTRA_RESOURCES_JSON="$(node - "$DEPLOY_DIR/deploy-manifest.json" "$REPO_ROOT" <<'NODE'
const fs = require('node:fs')
const path = require('node:path')
const manifest = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'))
const repoRoot = process.argv[2]
const staged = manifest.staged || {}
const abs = (rel) => path.join(repoRoot, rel)
const has = (key) => !!staged[key]
const entries = []
// 与 package.json 原 extraResources 对齐，但 from 全部改为绝对路径
if (has('tabsite-templates')) entries.push({ from: staged['tabsite-templates'], to: 'tabsite-templates', filter: ['**/*','!**/src/**','!**/*.ts','!**/*.tsx','!**/*.map','!**/*.tsbuildinfo','!**/*.test.*','!**/*.spec.*','!**/__tests__/**','!**/example/**','!**/examples/**','!**/benchmark/**','!**/benchmarks/**','!**/browser-test/**','!**/system-test/**','!**/test/**','!**/tests/**','!**/fixtures/**','!**/fixture/**','!**/docs/**','!**/vite.config.*','!**/tsconfig*.json','!**/node_modules/**','!**/dist/**','!**/.git/**','!**/.env','!**/.env.*'] })
if (has('personal-plugins')) entries.push({ from: staged['personal-plugins'], to: 'personal-plugins', filter: ['**/*','!**/__tests__/**','!**/test/**','!**/tests/**','!**/*.ts','!**/*.tsx','!**/.env','!**/.env.*','!**/.DS_Store'] })
if (has('bundled-skills-src')) entries.push({ from: staged['bundled-skills-src'], to: 'app.asar.unpacked/bundled-skills', filter: ['**/*','!**/__pycache__/**','!**/__tests__/**','!**/example/**','!**/examples/**','**/examples/**','!**/benchmark/**','!**/benchmarks/**','!**/browser-test/**','!**/system-test/**','!**/test/**','!**/tests/**','!**/fixtures/**','!**/fixture/**','!**/*.pyc','!**/*.pyo','!**/*.map','!**/*.tsbuildinfo','!**/.pytest_cache/**','!**/.DS_Store'] })
if (has('tabtracker-src')) entries.push({ from: staged['tabtracker-src'], to: 'app.asar.unpacked/package-skills/tabtracker', filter: ['**/*','!**/__pycache__/**','!**/__tests__/**','!**/example/**','!**/examples/**','**/examples/**','!**/benchmark/**','!**/benchmarks/**','!**/browser-test/**','!**/system-test/**','!**/test/**','!**/tests/**','!**/fixtures/**','!**/fixture/**','!**/*.pyc','!**/*.pyo','!**/*.map','!**/*.tsbuildinfo','!**/.pytest_cache/**','!**/.DS_Store'] })
if (has('packages-apps-src')) entries.push({ from: staged['packages-apps-src'], to: 'app.asar.unpacked/packages/apps', filter: ['**/*','!**/node_modules/**','!**/dist/**','!**/.git/**','!**/__pycache__/**','!**/__tests__/**','!**/example/**','!**/examples/**','**/skills/**/examples/**','!**/benchmark/**','!**/benchmarks/**','!**/browser-test/**','!**/system-test/**','!**/test/**','!**/tests/**','!**/fixtures/**','!**/fixture/**','!**/*.ts','!**/*.tsx','!**/*.map','!**/*.tsbuildinfo','!**/*.test.*','!**/*.spec.*','!**/*.pyc','!**/.env','!**/.env.*','!**/.DS_Store'] })
if (has('official-plugins')) entries.push({ from: staged['official-plugins'], to: 'official-plugins', filter: ['**/*','!**/.DS_Store'] })
if (has('scrcpy-server.jar')) entries.push({ from: staged['scrcpy-server.jar'], to: 'scrcpy-server.jar' })
if (has('models')) entries.push({ from: staged['models'], to: 'models', filter: ['**/*','!**/.DS_Store','!**/*.download'] })
process.stdout.write(JSON.stringify(entries))
NODE
)"

echo "=== 从 deploy 目录跑 electron-builder (community win x64) ==="
echo "deploy: $DEPLOY_DIR"
echo "repo: $REPO_ROOT"
echo "electron: $ELECTRON_VERSION"

cd "$DEPLOY_DIR"

# 准备输出目录（每次独立 run）
ARTIFACT_DIR_REL="dist-app-runs/manual-run"
if [ -e "$DEPLOY_DIR/$ARTIFACT_DIR_REL" ]; then rm -rf "$DEPLOY_DIR/$ARTIFACT_DIR_REL"; fi
mkdir -p "$DEPLOY_DIR/$ARTIFACT_DIR_REL"

# 去掉 package.json 的 devDependencies（electron-builder 默认只打包 prod，但保险起见）
node -e '
const fs = require("node:fs")
const p = process.argv[1]
const pkg = JSON.parse(fs.readFileSync(p, "utf8"))
const ev = process.argv[2]
pkg.build = pkg.build || {}
if (ev) pkg.build.electronVersion = ev
delete pkg.devDependencies
delete pkg.optionalDevDependencies
// patch version
pkg.version = "1.0.0"
pkg.build.productName = "SnSworker"
pkg.build.appId = "com.snsworker.community"
pkg.build.extraMetadata = {
  ...(pkg.build.extraMetadata || {}),
  version: "1.0.0",
  tabtinDesktop: { buildProfile: "community" }
}
// 锁定 win target
pkg.build.win = {
  ...(pkg.build.win || {}),
  target: [{ target: "nsis", arch: ["x64"] }]
}
fs.writeFileSync(p, JSON.stringify(pkg, null, 2) + "\n")
' "$DEPLOY_DIR/package.json" "$ELECTRON_VERSION"

echo "extraResources: $EXTRA_RESOURCES_JSON"

set +e
node "$ELECTRON_BUILDER_CLI" \
  --win --x64 \
  --config.productName="SnSworker" \
  --config.appId="com.snsworker.community" \
  --config.extraMetadata.version="1.0.0" \
  --config.win.executableName="snsworker" \
  --publish=never \
  --config.nsis.shortcutName="SnSworker" \
  --config.nsis.differentialPackage=false \
  --config.electronVersion="$ELECTRON_VERSION" \
  --config.electronDist="$ELECTRON_DIST" \
  --config.directories.output="$ARTIFACT_DIR_REL" \
  --config.extraResources="$EXTRA_RESOURCES_JSON" \
  2>&1 | tee "$DEPLOY_DIR/electron-builder-community-win-x64.log"
CODE=${PIPESTATUS[0]}
set -e
echo "electron-builder exit code: $CODE"
exit $CODE
