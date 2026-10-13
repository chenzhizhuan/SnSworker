import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  buildProjectTaskRunRequiredMessage,
  clearProjectTaskRunStatusCache,
  evaluateProjectTaskChatSendGate,
  isProjectTaskEditAndResendBlocked,
  PROJECT_TASK_NOT_CONFIGURED_MESSAGE,
  PROJECT_TASK_RUN_REQUIRED_MESSAGE,
  rememberProjectTaskRunStatus,
  resolveProjectTaskChatSendGate,
} from '../delivery/projectTaskSendGate'

const getLastAppContext = vi.fn()
const getSessionContext = vi.fn()
const getTask = vi.fn()

vi.mock('../../../session/slices/contextSyncSlice', () => ({
  getLastAppContext: (...args: unknown[]) => getLastAppContext(...args),
}))

vi.mock('@/services/chatExtraApi', () => ({
  getSessionContext: (...args: unknown[]) => getSessionContext(...args),
}))

vi.mock('@/services/projectApi', () => ({
  ProjectApiService: {
    getTask: (...args: unknown[]) => getTask(...args),
  },
}))

describe('evaluateProjectTaskChatSendGate', () => {
  it('普通聊天放行', () => {
    expect(evaluateProjectTaskChatSendGate({
      originSource: null,
      runStatus: 'failed',
    })).toBeNull()
  })

  it('project_task + running 放行', () => {
    expect(evaluateProjectTaskChatSendGate({
      originSource: 'project_task',
      runStatus: 'running',
    })).toBeNull()
  })

  it('project_task + completed 放行', () => {
    expect(evaluateProjectTaskChatSendGate({
      originSource: 'project_task',
      runStatus: 'completed',
    })).toBeNull()
  })

  it('project_task + failed 拒绝', () => {
    expect(evaluateProjectTaskChatSendGate({
      originSource: 'project_task',
      runStatus: 'failed',
    })).toEqual({
      errorCode: 'project_task_run_required',
      errorMessage: PROJECT_TASK_RUN_REQUIRED_MESSAGE,
      errorCategory: 'project_task_run_required',
      retryable: false,
    })
  })

  it('project_task + preparing 拒绝', () => {
    expect(evaluateProjectTaskChatSendGate({
      originSource: 'project_task',
      runStatus: 'preparing',
    })?.errorCode).toBe('project_task_run_required')
  })

  it('project_task 无 Run 拒绝', () => {
    expect(evaluateProjectTaskChatSendGate({
      originSource: 'project_task',
      runStatus: null,
    })?.errorCode).toBe('project_task_run_required')
  })

  it('project_task + failed 且未配置执行 → 引导先配置，而非找「重新运行」', () => {
    const block = evaluateProjectTaskChatSendGate({
      originSource: 'project_task',
      runStatus: 'failed',
      task: { execution_ready: false, work_status: 'todo' },
    })
    expect(block?.errorMessage).toBe(PROJECT_TASK_NOT_CONFIGURED_MESSAGE)
  })

  it('project_task + failed 且受阻 → 引导点击「重新运行」', () => {
    const block = evaluateProjectTaskChatSendGate({
      originSource: 'project_task',
      runStatus: 'failed',
      task: { execution_ready: true, work_status: 'blocked' },
    })
    expect(block?.errorMessage).toBe(
      '当前任务执行已结束，请回到任务详情点击「重新运行」创建新的执行。',
    )
  })

  it('project_task + failed 且任务已结束 → 明确不能继续发送', () => {
    const block = evaluateProjectTaskChatSendGate({
      originSource: 'project_task',
      runStatus: 'failed',
      task: { execution_ready: true, work_status: 'done' },
    })
    expect(block?.errorMessage).toBe(
      '当前任务已结束或已取消，不能在执行会话中继续发送。',
    )
  })
})

describe('buildProjectTaskRunRequiredMessage', () => {
  it('无任务投影时回退通用文案', () => {
    expect(buildProjectTaskRunRequiredMessage(null)).toBe(PROJECT_TASK_RUN_REQUIRED_MESSAGE)
    expect(buildProjectTaskRunRequiredMessage(undefined)).toBe(PROJECT_TASK_RUN_REQUIRED_MESSAGE)
  })

  it('未配置执行（接受指派后配置被重置）→ 配置引导', () => {
    expect(buildProjectTaskRunRequiredMessage({
      execution_ready: false,
      work_status: 'todo',
    })).toBe(PROJECT_TASK_NOT_CONFIGURED_MESSAGE)
  })

  it('受阻且有配置 → 「重新运行」引导', () => {
    expect(buildProjectTaskRunRequiredMessage({
      execution_ready: true,
      work_status: 'blocked',
    })).toContain('重新运行')
  })
})

describe('isProjectTaskEditAndResendBlocked', () => {
  beforeEach(() => {
    clearProjectTaskRunStatusCache()
    getLastAppContext.mockReset()
  })

  it('失败会话隐藏重新发送', () => {
    getLastAppContext.mockReturnValue({
      appType: 'project_task',
      appMeta: { project_id: 'p1', task_id: 't1', run_status: 'failed' },
    })
    expect(isProjectTaskEditAndResendBlocked('sess-failed')).toBe(true)
  })

  it('进行中会话不隐藏', () => {
    getLastAppContext.mockReturnValue({
      appType: 'project_task',
      appMeta: { project_id: 'p1', task_id: 't1', run_status: 'running' },
    })
    expect(isProjectTaskEditAndResendBlocked('sess-running')).toBe(false)
  })

  it('普通聊天不隐藏', () => {
    getLastAppContext.mockReturnValue({
      appType: 'tabdoc',
      appMeta: {},
    })
    expect(isProjectTaskEditAndResendBlocked('sess-normal')).toBe(false)
  })

  it('状态未知时不隐藏（交给送信门禁）', () => {
    getLastAppContext.mockReturnValue({
      appType: 'project_task',
      appMeta: { project_id: 'p1', task_id: 't1' },
    })
    expect(isProjectTaskEditAndResendBlocked('sess-unknown')).toBe(false)
  })

  it('缓存失败状态时隐藏', () => {
    getLastAppContext.mockReturnValue(null)
    rememberProjectTaskRunStatus('sess-cached', 'failed')
    expect(isProjectTaskEditAndResendBlocked('sess-cached')).toBe(true)
  })
})

describe('resolveProjectTaskChatSendGate', () => {
  beforeEach(() => {
    clearProjectTaskRunStatusCache()
    getLastAppContext.mockReset()
    getSessionContext.mockReset()
    getTask.mockReset()
  })

  it('本机 runtime 旁路：失败 Run 被拒', async () => {
    getLastAppContext.mockReturnValue({
      appType: 'project_task',
      appMeta: {
        project_id: 'project-1',
        task_id: 'task-1',
        task_run_id: 'run-1',
      },
    })
    getSessionContext.mockResolvedValue({
      context_data: {
        _origin_source: 'project_task',
        _project_task_id: 'task-1',
        _project_task_run_id: 'run-1',
      },
    })
    getTask.mockResolvedValue({
      id: 'task-1',
      execution_ready: false,
      work_status: 'todo',
      conversations: [{
        session_id: 'sess-1',
        run_id: 'run-1',
        run_status: 'failed',
      }],
      latest_run: { id: 'run-1', status: 'failed', chat_session_id: 'sess-1' },
    })

    const gate = await resolveProjectTaskChatSendGate('sess-1')
    expect(gate?.errorCode).toBe('project_task_run_required')
    expect(getTask).toHaveBeenCalledWith('project-1', 'task-1')
    // dogfood 修复：拦截反馈需要定位信息直达任务详情。
    expect(gate?.projectId).toBe('project-1')
    expect(gate?.taskId).toBe('task-1')
    // 未配置执行时不得再引导用户去找「重新运行」按钮。
    expect(gate?.errorMessage).toBe(PROJECT_TASK_NOT_CONFIGURED_MESSAGE)
  })

  it('普通聊天本机续聊不受影响，且不打 getSessionContext', async () => {
    getLastAppContext.mockReturnValue({
      appType: 'tabdoc',
      appMeta: {},
    })

    await expect(resolveProjectTaskChatSendGate('sess-normal')).resolves.toBeNull()
    expect(getSessionContext).not.toHaveBeenCalled()
    expect(getTask).not.toHaveBeenCalled()
  })

  it('pending Run 允许继续（仍会权威刷新，不信本地缓存短路）', async () => {
    getLastAppContext.mockReturnValue({
      appType: 'project_task',
      appMeta: {
        project_id: 'project-1',
        task_id: 'task-1',
        run_status: 'pending',
      },
    })
    getSessionContext.mockResolvedValue({
      context_data: { _origin_source: 'project_task' },
    })
    getTask.mockResolvedValue({
      id: 'task-1',
      conversations: [{
        session_id: 'sess-pending',
        run_id: 'run-pending',
        run_status: 'pending',
      }],
      latest_run: { id: 'run-pending', status: 'pending', chat_session_id: 'sess-pending' },
    })

    await expect(resolveProjectTaskChatSendGate('sess-pending')).resolves.toBeNull()
    expect(getTask).toHaveBeenCalledWith('project-1', 'task-1')
  })

  it('本地缓存仍为 running、服务端已 failed → 必须拒绝（dogfood 旁路）', async () => {
    getLastAppContext.mockReturnValue({
      appType: 'project_task',
      appMeta: {
        project_id: 'project-1',
        task_id: 'task-1',
        task_run_id: 'run-1',
        run_status: 'running',
      },
    })
    rememberProjectTaskRunStatus('sess-stale', 'running')
    getSessionContext.mockResolvedValue({
      context_data: {
        _origin_source: 'project_task',
        _project_task_id: 'task-1',
        _project_task_run_id: 'run-1',
        current_space_id: 'project-1',
      },
    })
    getTask.mockResolvedValue({
      id: 'task-1',
      conversations: [{
        session_id: 'sess-stale',
        run_id: 'run-1',
        run_status: 'failed',
      }],
      latest_run: { id: 'run-1', status: 'failed', chat_session_id: 'sess-stale' },
    })

    const gate = await resolveProjectTaskChatSendGate('sess-stale')
    expect(gate?.errorCode).toBe('project_task_run_required')
    expect(getTask).toHaveBeenCalledWith('project-1', 'task-1')
  })

  it('project_task 刷新失败时 fail-closed', async () => {
    getLastAppContext.mockReturnValue({
      appType: 'project_task',
      appMeta: {
        project_id: 'project-1',
        task_id: 'task-1',
        run_status: 'running',
      },
    })
    getSessionContext.mockResolvedValue({
      context_data: { _origin_source: 'project_task' },
    })
    getTask.mockRejectedValue(new Error('network'))

    const gate = await resolveProjectTaskChatSendGate('sess-refresh-fail')
    expect(gate?.errorCode).toBe('project_task_run_required')
  })

  it('仅有 current_space_id 时也能拼出 getTask', async () => {
    getLastAppContext.mockReturnValue({ appType: null, appMeta: null })
    getSessionContext.mockResolvedValue({
      context_data: {
        _origin_source: 'project_task',
        _project_task_id: 'task-1',
        current_space_id: 'project-1',
      },
    })
    getTask.mockResolvedValue({
      id: 'task-1',
      conversations: [{
        session_id: 'sess-space',
        run_id: 'run-1',
        run_status: 'running',
      }],
      latest_run: { id: 'run-1', status: 'running', chat_session_id: 'sess-space' },
    })

    await expect(resolveProjectTaskChatSendGate('sess-space')).resolves.toBeNull()
    expect(getTask).toHaveBeenCalledWith('project-1', 'task-1')
  })
})
