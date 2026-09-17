import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import test from 'node:test'

const repoRoot = path.resolve(import.meta.dirname, '../..')
const source = async (relativePath) =>
  readFile(path.join(repoRoot, relativePath), 'utf8')

test('mobile launchers display the 智算方舟 product name in every locale', async () => {
  const [androidZh, androidEn, iosInfo] = await Promise.all([
    source('apps/tabtin-android/app/src/main/res/values/strings.xml'),
    source('apps/tabtin-android/app/src/main/res/values-en/strings.xml'),
    source('apps/tabtin-ios/Tabtin/Resources/Info.plist'),
  ])

  assert.match(androidZh, /<string name="app_name">智算方舟<\/string>/)
  assert.match(androidEn, /<string name="app_name">智算方舟<\/string>/)
  assert.match(
    iosInfo,
    /<key>CFBundleDisplayName<\/key>\s*<string>智算方舟<\/string>/,
  )
})

test('Android cold start and launch overlay use the ark mark and brand name', async () => {
  const [theme, overlay, artwork] = await Promise.all([
    source('apps/tabtin-android/app/src/main/res/values/themes.xml'),
    source(
      'apps/tabtin-android/app/src/main/java/com/tabtin/mobile/ui/splash/LaunchSplashOverlay.kt',
    ),
    source('apps/tabtin-android/app/src/main/res/drawable/splash_ark_art.xml'),
  ])

  assert.match(theme, /windowSplashScreenAnimatedIcon">@drawable\/splash_ark</)
  assert.match(overlay, /R\.drawable\.splash_ark_art/)
  assert.match(overlay, /stringResource\(R\.string\.app_name\)/)
  assert.match(artwork, /android:pathData="M48,68C57,42 76,21 104,8V59C82,59 64,63 48,68Z"/)
})

test('iOS launch overlay draws the ark mark and presents the 智算方舟 brand name', async () => {
  const launchView = await source(
    'apps/tabtin-ios/Tabtin/App/LaunchSplashView.swift',
  )

  assert.match(launchView, /Text\("智算方舟"\)/)
  assert.match(launchView, /drawArk\(context:/)
  assert.doesNotMatch(launchView, /drawTin\(context:/)
})
