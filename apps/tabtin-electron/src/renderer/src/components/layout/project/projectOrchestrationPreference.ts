const PROJECT_ORCHESTRATION_COLLAPSED_KEY = 'tabtin.project-orchestration-collapsed'

function preferenceKey(userId: string): string {
  return `${PROJECT_ORCHESTRATION_COLLAPSED_KEY}:${userId || 'anonymous'}`
}

/**
 * Project 的 AI 编排入口默认展开；偏好只在当前用户的本地客户端保存。
 *
 * 存储语义：`'true'` = 用户显式折叠过；`'false'` = 用户显式展开过；
 * 无存储值（新用户 / 清缓存）→ 默认展开。
 */
export function readProjectOrchestrationCollapsed(userId: string): boolean {
  try {
    return localStorage.getItem(preferenceKey(userId)) === 'true'
  } catch {
    return false
  }
}

export function writeProjectOrchestrationCollapsed(userId: string, collapsed: boolean): void {
  try {
    localStorage.setItem(preferenceKey(userId), String(collapsed))
  } catch {
    // 本地存储不可用时保留本次会话状态，下一次仍回到默认展开态。
  }
}
