import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DEVICE_LOCAL_KEYS } from '@/stores/persist-key-registry'

// 注册入口开关在模块顶层求值，切换环境后需 resetModules 重新加载模块。
const loadAuthEntryMode = async () => {
  vi.resetModules()
  const mod = await import('../authEntryMode')
  return mod.resolveInitialAuthEntryMode
}

describe('认证入口初始页面', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('注册关停（未设置，默认关）时新装首启展示登录页且不写入口记忆', async () => {
    const resolveInitialAuthEntryMode = await loadAuthEntryMode()
    expect(resolveInitialAuthEntryMode(localStorage)).toBe('login')
    expect(localStorage.getItem(DEVICE_LOCAL_KEYS.authEntrySeen)).toBeNull()
  })

  it('显式开启注册（VITE_REGISTRATION_ENABLED=true）时新装首启展示注册页并记录设备已见', async () => {
    vi.stubEnv('VITE_REGISTRATION_ENABLED', 'true')
    const resolveInitialAuthEntryMode = await loadAuthEntryMode()
    expect(resolveInitialAuthEntryMode(localStorage)).toBe('register')
    expect(localStorage.getItem(DEVICE_LOCAL_KEYS.authEntrySeen)).toBe('1')
  })

  it('设备已经见过认证入口时展示登录页', async () => {
    vi.stubEnv('VITE_REGISTRATION_ENABLED', 'true')
    localStorage.setItem(DEVICE_LOCAL_KEYS.authEntrySeen, '1')
    const resolveInitialAuthEntryMode = await loadAuthEntryMode()
    expect(resolveInitialAuthEntryMode(localStorage)).toBe('login')
  })

  it('服务端渲染等无 localStorage 环境安全回退到登录页', async () => {
    const resolveInitialAuthEntryMode = await loadAuthEntryMode()
    expect(resolveInitialAuthEntryMode(undefined)).toBe('login')
  })
})
