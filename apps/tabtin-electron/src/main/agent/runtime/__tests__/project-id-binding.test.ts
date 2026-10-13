/**
 * projectId 会话级粘性契约测试（TODO #4：AI 编排确认方案后不写看板）。
 *
 * 回归背景：chat 视觉 Focus 同步会把 appContext.appMeta 置 null（P1-7），
 * 编排对话的下一条消息若以「无 project_id」重建 runtime，project_* 工具被
 * 静默摘除。wire 未显式提供时应沿用 HostState 已烘焙的 projectId。
 */
import { describe, expect, it } from 'vitest'
import { resolveRuntimeProjectId } from '../project-id-binding'

describe('resolveRuntimeProjectId — projectId 会话级粘性', () => {
  it('wire 显式提供 project_id：trim 后使用', () => {
    expect(resolveRuntimeProjectId({
      candidate: '  project-1  ',
      existingProjectId: 'project-old',
    })).toBe('project-1')
  })

  it('TODO#4 回归：appMeta 为 null（chat 视觉 Focus）时回退 HostState 烘焙值', () => {
    expect(resolveRuntimeProjectId({
      candidate: null,
      existingProjectId: 'project-1',
    })).toBe('project-1')
  })

  it('appMeta 存在但缺 project_id 键：回退烘焙值', () => {
    expect(resolveRuntimeProjectId({
      candidate: undefined,
      existingProjectId: 'project-1',
    })).toBe('project-1')
  })

  it('project_id 为空字符串视为显式清除（不回退烘焙值）', () => {
    expect(resolveRuntimeProjectId({
      candidate: '   ',
      existingProjectId: 'project-1',
    })).toBeUndefined()
  })

  it('wire 与烘焙值都缺失时为 undefined（非 Project 会话）', () => {
    expect(resolveRuntimeProjectId({
      candidate: undefined,
      existingProjectId: undefined,
    })).toBeUndefined()
  })

  it('非字符串类型（异常输入）回退烘焙值，不抛错', () => {
    expect(resolveRuntimeProjectId({
      candidate: 42,
      existingProjectId: 'project-1',
    })).toBe('project-1')
    expect(resolveRuntimeProjectId({
      candidate: { project_id: 'project-1' },
      existingProjectId: 'project-1',
    })).toBe('project-1')
  })
})
