import { parseOptionalFeatureFlag } from '@tabtin/shared/auth-forms'
import { DEVICE_LOCAL_KEYS } from '@/stores/persist-key-registry'

export type InitialAuthEntryMode = 'login' | 'register'

/**
 * 注册入口总开关（与后端 TABTIN_REGISTRATION_ENABLED 对应）：未设置视为开启，
 * 显式 `false` 才关闭。公网部署形态由 `.env.community` 注入 false。
 */
const REGISTRATION_ENTRY_ENABLED = parseOptionalFeatureFlag(
  import.meta.env.VITE_REGISTRATION_ENABLED,
)

/**
 * 新安装首次进入认证页时优先展示注册；此后（包括退出登录、修改/重置密码后）
 * 都回到登录页。入口记忆是设备级状态，不包含账号身份或凭证。
 *
 * 注册入口整体关停（VITE_REGISTRATION_ENABLED=false）时不再默认展示注册页，
 * 也不写入入口记忆——将来重新放开注册后，老设备仍能按"新安装"逻辑看到注册引导。
 */
export function resolveInitialAuthEntryMode(
  storage: Pick<Storage, 'getItem' | 'setItem'> | undefined,
): InitialAuthEntryMode {
  if (!storage) return 'login'
  if (!REGISTRATION_ENTRY_ENABLED) return 'login'

  const hasSeenAuthEntry = storage.getItem(DEVICE_LOCAL_KEYS.authEntrySeen) === '1'
  if (hasSeenAuthEntry) return 'login'

  storage.setItem(DEVICE_LOCAL_KEYS.authEntrySeen, '1')
  return 'register'
}
