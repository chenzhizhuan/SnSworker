import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'
import { pathToFileURL } from 'node:url'
import { createRequire } from 'node:module'
import test from 'node:test'
import path from 'node:path'

const requireFromTabslide = createRequire(
  new URL('../../packages/tabslide/package.json', import.meta.url),
)
const { chromium } = requireFromTabslide('playwright')

const chromiumExecutable = [
  process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,
  chromium.executablePath(),
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
].find((candidate) => candidate && existsSync(candidate))

const repoRoot = path.resolve(import.meta.dirname, '../..')
const pages = [
  path.join(
    repoRoot,
    'apps/tabtin-android/app/src/main/assets/login_motion/login-motion.html',
  ),
  path.join(
    repoRoot,
    'apps/tabtin-ios/Tabtin/Resources/LoginMotion/login-motion.html',
  ),
]

test('Android and iOS render the same inline SnSworker ark logo', async () => {
  const browser = await chromium.launch({
    executablePath: chromiumExecutable,
    headless: true,
  })

  try {
    const rendered = []

    for (const file of pages) {
      const page = await browser.newPage()
      await page.goto(`${pathToFileURL(file).href}?lang=zh`)

      const brandName = await page.locator('.brand-word').textContent()
      const logos = page.locator('svg[data-brand-logo="snsworker-ark"]')

      assert.equal(brandName, '智算方舟')
      assert.equal(await logos.count(), 2)
      assert.equal(await logos.first().locator('[data-logo-part="sail"]').count(), 1)
      assert.equal(await logos.first().locator('[data-logo-part="wave"]').count(), 2)
      assert.equal(await logos.first().locator('[data-logo-part="pixel"]').count(), 4)

      rendered.push(await logos.first().evaluate((logo) => logo.outerHTML))
      await page.close()
    }

    assert.equal(rendered[0], rendered[1])
  } finally {
    await browser.close()
  }
})
