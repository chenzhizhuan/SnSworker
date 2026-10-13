/**
 * projectId 会话级粘性契约（TODO #4：AI 编排确认方案后不写看板）。
 *
 * 背景：chat 视觉 Focus 的 syncContext（chatPanelController.requestContextSync，
 * P1-7）会把 appContext.appMeta 置 null，覆盖编排打开时写入的 { project_id }。
 * 若 runtime 装配仅依赖 wire 快照，用户在编排对话里的下一条消息就会以
 * 「无 Project 上下文」重建 runtime，project_members_list / project_tasks_create
 * 等工具被静默摘除。
 *
 * 语义：会话归属的 Project 是创建期绑定（chat_session.project_id），视觉
 * Focus 不改变它 —— wire 未显式提供（appMeta 缺 project_id 或为 null）时，
 * 沿用当前 HostState 已烘焙的 projectId；显式提供时（含空串）以 wire 为准
 * （空串语义 = 显式清除）。
 */

export interface ResolveRuntimeProjectIdParams {
  /** request.appContext?.appMeta?.project_id 的原始值（未知类型，需防御）。 */
  candidate: unknown
  /** 当前 HostState 已烘焙的 projectId（可能为 undefined）。 */
  existingProjectId?: string | undefined
}

/**
 * 解析本轮 runtime 装配使用的 projectId。
 * - candidate 为非空字符串 → trim 后使用；
 * - candidate 为空字符串 → undefined（显式清除，不回退）；
 * - candidate 缺失 / null / 非字符串 → 回退 existingProjectId。
 */
export function resolveRuntimeProjectId(
  params: ResolveRuntimeProjectIdParams,
): string | undefined {
  const { candidate, existingProjectId } = params
  if (typeof candidate === 'string') {
    return candidate.trim() || undefined
  }
  return existingProjectId
}
