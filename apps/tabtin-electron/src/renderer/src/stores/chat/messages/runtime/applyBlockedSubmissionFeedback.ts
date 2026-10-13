import i18n from '@/i18n'
import { createElement } from 'react'
import { toast, ToastAction } from '@tabtin/smartsheet-ui/toast'
import { trackSendTimingTelemetry } from '../../execution/sendTimingTrace'
import type { BlockedSubmission } from '../product/types'
import type { SendTimingTrace } from '../../execution/sendTimingTrace'
import { isCommunityDistribution } from '@/config/distribution'
import { PROJECT_TASK_RUN_REQUIRED_MESSAGE } from '../product/delivery/projectTaskSendGate'

/**
 * 技术域：根据产品域阻断结果执行 UI / telemetry 副作用。
 * 产品规则在 product/delivery；此处只做呈现与埋点。
 */
export function applyBlockedSubmissionFeedback(
  blocked: BlockedSubmission,
  ctx: {
    sessionId: string | null
    sendTimingTrace?: SendTimingTrace
    log: { warn: (...args: unknown[]) => void; error: (...args: unknown[]) => void }
  },
): void {
  switch (blocked.reason) {
    case 'no_session':
      ctx.log.error('没有选中的会话')
      return
    case 'restoring':
      ctx.log.warn('sendMessage blocked: session %s is restoring', ctx.sessionId)
      toast({
        title: i18n.t('chat:checkpoint.sendBlockedRestoring', {
          defaultValue: '正在恢复中，请稍后再发送',
        }),
      })
      return
    case 'awaiting_approval':
      ctx.log.warn('当前有待审批操作，请先审批或拒绝')
      return
    case 'awaiting_ask_user':
      ctx.log.warn('当前有待回答问题，请先回答或跳过')
      return
    case 'no_runtime':
      ctx.log.warn('sendMessage aborted: local runtime unavailable', { sessionId: ctx.sessionId })
      toast({
        title: i18n.t('chat:messages.deviceRequiredTitle', {
          defaultValue: '请先为该 Agent 绑定一台设备',
        }),
        description: i18n.t('chat:messages.deviceRequiredHint', {
          defaultValue:
            '该 Agent 目前没有可用的本地 Runtime。请在 Agent 设置中绑定一台已启动的 Electron 或 Daemon 设备后再发起对话。',
        }),
      })
      if (ctx.sessionId) {
        trackSendTimingTelemetry(
          'message.send.blocked_no_device',
          { sessionId: ctx.sessionId },
          ctx.sendTimingTrace,
          { counterKey: 'message.send.blocked_no_device', sessionId: ctx.sessionId },
        )
      }
      return
    case 'no_model':
      toast({
        title: i18n.t(isCommunityDistribution
          ? 'chat:errors.communityModelNotConfigured'
          : 'chat:errors.modelNotConfigured', {
          defaultValue: isCommunityDistribution
            ? 'AI NOT CONFIGURED · 请前往「设置 → 模型配置 → BYOK」'
            : '请先在管理后台配置模型 API Key 并开启路由',
        }),
        variant: 'destructive',
      })
      return
    case 'project_task_run_required': {
      ctx.log.warn('sendMessage blocked: project task run required', {
        sessionId: ctx.sessionId,
      })
      // 文案按任务状态生成：接受指派后未配置时任务详情并没有「重新运行」按钮。
      const target = blocked.projectTask
      toast({
        title: i18n.t('chat:projectTask.runRequiredTitle', {
          defaultValue: '请回到任务详情继续任务',
        }),
        description: target?.message
          ?? i18n.t('chat:projectTask.runRequiredHint', {
            defaultValue: PROJECT_TASK_RUN_REQUIRED_MESSAGE,
          }),
        variant: 'destructive',
        // 直达任务详情，避免用户被历史会话卡在死胡同里（dogfood）。
        ...(target ? {
          action: createElement(
            ToastAction,
            {
              altText: '去任务详情',
              onClick: () => {
                void import('@/services/focusProjectTask').then((mod) => {
                  mod.focusProjectTask({
                    projectId: target.projectId,
                    taskId: target.taskId,
                  })
                })
              },
            },
            '去任务详情',
          ),
        } : {}),
      })
      return
    }
    default: {
      const _exhaustive: never = blocked.reason
      void _exhaustive
    }
  }
}
