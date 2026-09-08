import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

const appRoot = new URL('../', import.meta.url)
const buildScript = new URL('build-packaged-app.sh', import.meta.url)

/**
 * Windows 上裸 `bash` 会被解析到 System32 的 WSL 启动器（未装发行版时立即失败），
 * 项目主流程统一使用 Git Bash，这里按同样优先级解析。
 */
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

/** Git Bash (MSYS) 只认 /c/... 风格路径；URL.pathname 的 /C:/... 会 ENOENT。 */
function toMsysPath(url) {
  const p = fileURLToPath(url)
  if (process.platform !== 'win32') return p
  const msys = p.replace(/^([A-Za-z]):/, (_, drive) => `/${drive.toLowerCase()}`)
  return msys.replaceAll('\\', '/')
}

function validateProfile(extraEnv = {}) {
  return spawnSync(resolveBash(), [toMsysPath(buildScript), 'mac', 'community'], {
    cwd: appRoot,
    encoding: 'utf8',
    env: {
      PATH: process.env.PATH,
      HOME: process.env.HOME,
      TABTIN_COMMUNITY_PROFILE_VALIDATE_ONLY: '1',
      ...extraEnv,
    },
  })
}

test('Community profile defaults every connection endpoint to localhost', () => {
  const result = validateProfile()
  assert.equal(result.status, 0, result.stderr)
  assert.match(result.stdout, /API=http:\/\/127\.0\.0\.1:6060\/api/)
  assert.match(result.stdout, /WS=ws:\/\/127\.0\.0\.1:6060/)
  assert.match(result.stdout, /IM=http:\/\/127\.0\.0\.1:6060\/api/)
  assert.match(result.stdout, /Centrifugo=ws:\/\/127\.0\.0\.1:8100\/connection\/websocket/)

  const envFile = readFileSync(new URL('../.env.community', import.meta.url), 'utf8')
  for (const endpoint of ['api.example.com', 'ws.example.com', 'xmov.ai', 'example.com']) {
    assert.doesNotMatch(envFile, new RegExp(endpoint.replaceAll('.', '\\.')))
  }
})

test('Community profile rejects company endpoints but accepts explicit third-party hosts', () => {
  for (const url of [
    'https://api.example.com/api',
    'https://ws.example.com/api',
    'https://gptapi.xmov.ai/v1',
    'https://api.example.com/api',
  ]) {
    const result = validateProfile({ TABTIN_COMMUNITY_API_BASE_URL: url })
    assert.notEqual(result.status, 0, `${url} must be rejected`)
  }

  const thirdParty = validateProfile({
    TABTIN_COMMUNITY_API_BASE_URL: 'https://selfhost.example.org/api',
    TABTIN_COMMUNITY_CENTRIFUGO_WS_URL: 'wss://events.example.org/connection/websocket',
  })
  assert.equal(thirdParty.status, 0, thirdParty.stderr)

  const companyFeed = validateProfile({
    TABTIN_COMMUNITY_UPDATE_FEED_URL: 'https://downloads.example.com/community',
  })
  assert.notEqual(companyFeed.status, 0, 'company update feeds must not be inherited')
})
