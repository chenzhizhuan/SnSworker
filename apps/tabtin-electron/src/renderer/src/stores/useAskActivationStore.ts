/**
 * askActivationStore —— 「外部导航到问一句会话」的激活意图。
 *
 * AskPage 的 activeSessionId 是组件内部 useState，通知中心 / deep link /
 * 其它外部入口无法直接写入。本 store 记录「外部请求激活的 ask 会话 id」，
 * AskPage 挂载（或 space 就绪）后消费并切换到对应会话。
 *
 * 背景（bug 修复）：点击任务完成通知跳转 ask 会话时，通用跳转链路
 * enterChatSession 会硬编码 setCurrentTab('agent')，把用户从「问一句」
 * 流放到「办件事」工作台。修复后该链路改为：setCurrentTab('ask')
 * + requestActivate(sessionId)，由 AskPage 自身完成会话激活。
 */

import { create } from 'zustand'

interface AskActivationState {
  /** 待激活的 ask 会话 id；null 表示无待办意图。 */
  requestedSessionId: string | null
  /** 外部请求激活指定 ask 会话（幂等，重复请求覆盖）。 */
  requestActivate: (sessionId: string) => void
  /** AskPage 消费意图后清空。 */
  consumeRequest: () => void
}

export const useAskActivationStore = create<AskActivationState>((set) => ({
  requestedSessionId: null,
  requestActivate: (sessionId) => set({ requestedSessionId: sessionId }),
  consumeRequest: () => set({ requestedSessionId: null }),
}))