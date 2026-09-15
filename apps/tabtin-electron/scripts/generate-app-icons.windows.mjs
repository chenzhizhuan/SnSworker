#!/usr/bin/env node
/**
 * Windows 版全平台 app 图标生成脚本（新 logo 交付用，一次性）。
 *
 * 与 scripts/generate-app-icons.mjs 的逻辑完全一致，唯一差异：
 *   - 不依赖 macOS 的 iconutil，因此跳过 .icns 打包；
 *   - 改为在 build/icons/macos-iconset/ 输出 .icns 所需的全套 iconset PNG，
 *     在 Mac 上执行 `iconutil -c icns -o icon.icns macos-iconset` 即可补齐
 *     build/icons/icon.icns 与 icon-preprod.icns（见文末说明）。
 *
 * 输出（与仓库内 SSoT 脚本一致）：
 *   build/icon-source/icon-master.png   完整 1024 PNG（规范化源图，回退用）
 *   build/icons/icon-{16..1024}.png     多尺寸 PNG（套 82% 安全区）
 *   build/icons/icon.png                1024 PNG（linux + win，builder 自动转 ico）
 *   build/icons/macos-iconset/          10 张 iconset PNG（Mac 端打包 .icns 用）
 *   build/icons/icon-preprod.png        预发粉色 1024
 *   static/icon.png                     打包用 1024（main-app import.meta.url）
 *   static/icon-preprod.png             预发打包用 1024
 *   ../tabtin-web/public/favicon.png    Web favicon（64）
 *   ../tabtin-ios/.../AppIcon-1024.png  iOS AppIcon（白底满幅）
 *   ../tabtin-android/.../ic_launcher_foreground.png  Android 前景（432）
 *
 * 用法（在 apps/tabtin-electron 下）：
 *   node scripts/generate-app-icons.windows.mjs
 */

import sharp from 'sharp';
import {
  writeFileSync,
  mkdirSync,
  existsSync,
} from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');
const REPO_ROOT = resolve(ROOT, '../..');

// ---------- 配置（与 generate-app-icons.mjs 保持同步） ----------
const CONFIG = {
  localSourcePng: resolve(REPO_ROOT, 'SnSworker-icon.png'),
  trackedSourcePng: resolve(ROOT, 'build/icon-source/icon-master.png'),

  iconSourceDir: resolve(ROOT, 'build/icon-source'),
  iconsDir: resolve(ROOT, 'build/icons'),
  preprodIconPng: resolve(ROOT, 'build/icons/icon-preprod.png'),
  preprodStaticIcon: resolve(ROOT, 'static/icon-preprod.png'),
  staticIcon: resolve(ROOT, 'static/icon.png'),
  webFavicon: resolve(REPO_ROOT, 'apps/tabtin-web/public/favicon.png'),
  // 官网 tabtin-www 目录当前不存在，跳过（SSoT 脚本会写它；目录恢复后补跑即可）
  wwwFavicon: resolve(REPO_ROOT, 'apps/tabtin-www/favicon.png'),
  wwwFaviconIco: resolve(REPO_ROOT, 'apps/tabtin-www/favicon.ico'),
  iosAppIcon: resolve(REPO_ROOT, 'apps/tabtin-ios/Tabtin/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png'),
  iosOddAppIcon: resolve(REPO_ROOT, 'apps/tabtin-ios/tabtin-ios-odd/SnSworker/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png'),
  androidForeground: resolve(REPO_ROOT, 'apps/tabtin-android/app/src/main/res/drawable/ic_launcher_foreground.png'),

  size: 1024,
  safeAreaScale: 0.82,
  sizes: [16, 32, 64, 128, 256, 512, 1024],

  // Mac 端 .icns 打包交接：输出 iconset 文件夹 + 收尾说明
  macosIconsetDir: resolve(ROOT, 'build/icons/macOS-iconset'),
  macosIconsetPreprodDir: resolve(ROOT, 'build/icons/macOS-iconset-preprod'),
};

function resolveSourcePng() {
  if (existsSync(CONFIG.localSourcePng)) {
    return CONFIG.localSourcePng;
  }
  return CONFIG.trackedSourcePng;
}

/** 目标文件所在目录不存在时跳过（不建新目录），返回 true 表示可写。 */
function ensureTargetDir(filePath) {
  const dir = resolve(filePath, '..');
  if (!existsSync(dir)) {
    console.log(`  - 跳过（目录不存在）: ${filePath}`);
    return false;
  }
  return true;
}

async function sourceToPng(size, options = {}) {
  const { flattenBackground, contentScale = 1 } = options;

  const inner = Math.max(1, Math.round(size * contentScale));
  const innerBuffer = await sharp(resolveSourcePng())
    .resize(inner, inner, {
      fit: 'contain',
      background: { r: 0, g: 0, b: 0, alpha: 0 },
      withoutEnlargement: false,
    })
    .png()
    .toBuffer();

  const pad = Math.round((size - inner) / 2);
  let pipeline = sharp({
    create: {
      width: size,
      height: size,
      channels: 4,
      background: { r: 0, g: 0, b: 0, alpha: 0 },
    },
  }).composite([{ input: innerBuffer, top: pad, left: pad }]);

  if (flattenBackground) {
    pipeline = pipeline.flatten({ background: flattenBackground });
  }

  return pipeline.png({ compressionLevel: 9 }).toBuffer();
}

async function tintPreprodPink(pngBuffer) {
  const { data, info } = await sharp(pngBuffer)
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });
  const dark = [157, 23, 77]; // #9D174D，深莓色线稿
  const light = [252, 231, 243]; // #FCE7F3，浅樱粉面板

  for (let index = 0; index < data.length; index += 4) {
    const luminance = (
      data[index] * 0.2126
      + data[index + 1] * 0.7152
      + data[index + 2] * 0.0722
    ) / 255;
    data[index] = Math.round(dark[0] + (light[0] - dark[0]) * luminance);
    data[index + 1] = Math.round(dark[1] + (light[1] - dark[1]) * luminance);
    data[index + 2] = Math.round(dark[2] + (light[2] - dark[2]) * luminance);
  }

  return sharp(data, { raw: info }).png({ compressionLevel: 9 }).toBuffer();
}

function buildIco(entries) {
  const headerSize = 6;
  const entrySize = 16;
  const directorySize = headerSize + entries.length * entrySize;
  const header = Buffer.alloc(directorySize);
  header.writeUInt16LE(0, 0);
  header.writeUInt16LE(1, 2);
  header.writeUInt16LE(entries.length, 4);

  let imageOffset = directorySize;
  entries.forEach(({ size, buffer }, index) => {
    const offset = headerSize + index * entrySize;
    header.writeUInt8(size >= 256 ? 0 : size, offset);
    header.writeUInt8(size >= 256 ? 0 : size, offset + 1);
    header.writeUInt8(0, offset + 2);
    header.writeUInt8(0, offset + 3);
    header.writeUInt16LE(1, offset + 4);
    header.writeUInt16LE(32, offset + 6);
    header.writeUInt32LE(buffer.length, offset + 8);
    header.writeUInt32LE(imageOffset, offset + 12);
    imageOffset += buffer.length;
  });

  return Buffer.concat([header, ...entries.map((entry) => entry.buffer)]);
}

/** 写 .icns 所需 iconset 文件夹（PNG 命名遵循 Apple 规范；打包留给 Mac 的 iconutil）。 */
function writeIconset(pngBuffers, iconsetDir) {
  mkdirSync(iconsetDir, { recursive: true });
  const iconsetMap = [
    [16, 'icon_16x16.png'],
    [32, 'icon_16x16@2x.png'],
    [32, 'icon_32x32.png'],
    [64, 'icon_32x32@2x.png'],
    [128, 'icon_128x128.png'],
    [256, 'icon_128x128@2x.png'],
    [256, 'icon_256x256.png'],
    [512, 'icon_256x256@2x.png'],
    [512, 'icon_512x512.png'],
    [1024, 'icon_512x512@2x.png'],
  ];
  for (const [size, fname] of iconsetMap) {
    writeFileSync(resolve(iconsetDir, fname), pngBuffers[size]);
  }
}

async function main() {
  console.log('→ 检查依赖');
  const sourcePng = resolveSourcePng();
  if (!existsSync(sourcePng)) {
    throw new Error(`找不到源 PNG: ${CONFIG.localSourcePng} 或 ${CONFIG.trackedSourcePng}`);
  }
  console.log(`  ✓ 源图: ${sourcePng}`);

  mkdirSync(CONFIG.iconSourceDir, { recursive: true });
  mkdirSync(CONFIG.iconsDir, { recursive: true });

  console.log('→ 生成 master PNG (1024)');
  const masterPng = await sourceToPng(CONFIG.size);
  const masterPngPath = resolve(CONFIG.iconSourceDir, 'icon-master.png');
  writeFileSync(masterPngPath, masterPng);
  console.log(`  ✓ ${masterPngPath}`);

  console.log('→ 生成多尺寸 PNG（桌面/Web 套安全区外缘）');
  const pngBuffers = {};
  for (const s of CONFIG.sizes) {
    const buf = await sourceToPng(s, { contentScale: CONFIG.safeAreaScale });
    pngBuffers[s] = buf;
    const file = resolve(CONFIG.iconsDir, `icon-${s}.png`);
    writeFileSync(file, buf);
    console.log(`  ✓ ${file}`);
  }

  console.log('→ 写入主图标 PNG');
  const iconPng = resolve(CONFIG.iconsDir, 'icon.png');
  writeFileSync(iconPng, pngBuffers[1024]);
  console.log(`  ✓ ${iconPng}`);
  writeFileSync(CONFIG.staticIcon, pngBuffers[1024]);
  console.log(`  ✓ ${CONFIG.staticIcon}`);

  console.log('→ 同步 Web / 移动端图标');
  writeFileSync(CONFIG.webFavicon, pngBuffers[64]);
  console.log(`  ✓ ${CONFIG.webFavicon}`);
  if (ensureTargetDir(CONFIG.wwwFavicon)) {
    writeFileSync(CONFIG.wwwFavicon, pngBuffers[64]);
    console.log(`  ✓ ${CONFIG.wwwFavicon}`);
  }
  if (ensureTargetDir(CONFIG.wwwFaviconIco)) {
    writeFileSync(CONFIG.wwwFaviconIco, buildIco([
      { size: 16, buffer: pngBuffers[16] },
      { size: 32, buffer: pngBuffers[32] },
      { size: 64, buffer: pngBuffers[64] },
    ]));
    console.log(`  ✓ ${CONFIG.wwwFaviconIco}`);
  }
  const iosAppIcon = await sourceToPng(1024, { flattenBackground: '#FFFFFF' });
  if (ensureTargetDir(CONFIG.iosAppIcon)) {
    writeFileSync(CONFIG.iosAppIcon, iosAppIcon);
    console.log(`  ✓ ${CONFIG.iosAppIcon}`);
  }
  if (ensureTargetDir(CONFIG.iosOddAppIcon)) {
    writeFileSync(CONFIG.iosOddAppIcon, iosAppIcon);
    console.log(`  ✓ ${CONFIG.iosOddAppIcon}`);
  }
  writeFileSync(CONFIG.androidForeground, await sourceToPng(432));
  console.log(`  ✓ ${CONFIG.androidForeground}`);

  console.log('→ 准备 macOS .icns 交接（iconset 文件夹，Mac 端打包）');
  writeIconset(pngBuffers, CONFIG.macosIconsetDir);
  console.log(`  ✓ ${CONFIG.macosIconsetDir}`);

  console.log('→ 生成预发专属粉色图标');
  const preprodPngBuffers = {};
  for (const size of CONFIG.sizes) {
    preprodPngBuffers[size] = await tintPreprodPink(pngBuffers[size]);
  }
  writeFileSync(CONFIG.preprodIconPng, preprodPngBuffers[1024]);
  writeFileSync(CONFIG.preprodStaticIcon, preprodPngBuffers[1024]);
  console.log(`  ✓ ${CONFIG.preprodIconPng}`);
  console.log(`  ✓ ${CONFIG.preprodStaticIcon}`);
  writeIconset(preprodPngBuffers, CONFIG.macosIconsetPreprodDir);
  console.log(`  ✓ ${CONFIG.macosIconsetPreprodDir}`);

  console.log('\n✅ Windows 端全部完成。');
  console.log('   - win:   build/icons/icon.png  (electron-builder 自动转 .ico)');
  console.log('   - linux: build/icons/icon.png');
  console.log('   - pack:  static/icon.png + static/icon-preprod.png');
  console.log('   - web:   apps/tabtin-web/public/favicon.png');
  console.log('   - ios:   apps/tabtin-ios/**/AppIcon-1024.png');
  console.log('   - android: apps/tabtin-android/**/ic_launcher_foreground.png');
  console.log('');
  console.log('   ⚠️  .icns 需要 macOS iconutil，在 Mac 上执行：');
  console.log('       cd apps/tabtin-electron/build/icons');
  console.log('       iconutil -c icns -o icon.icns macOS-iconset');
  console.log('       iconutil -c icns -o icon-preprod.icns macOS-iconset-preprod');
}

main().catch((e) => {
  console.error('❌', e.message);
  process.exit(1);
});
