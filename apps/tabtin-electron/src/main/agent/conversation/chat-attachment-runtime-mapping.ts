import { runtimeTypeForChatVideoAttachment } from '@tabtin/media-capabilities/video'
import type { QueryStreamRuntimeAttachment } from '@tabtin/agent-host/conversation'

/**
 * 聊天附件 → runtime 附件映射（桌面端多图识别根因修复）。
 *
 * 背景：ElectronAgentHost 的 `prepareRuntimeAttachments` 端口此前是
 * `async () => []` 空桩——渲染层上传 OSS 后经 IPC 传来的附件在主进程被
 * 整批丢弃，`buildUserMessageWithAttachments(prompt, [])` 生成纯文本 user
 * 消息，模型从未见过图片本体；prompt 里只有 `<context type="attached">`
 * 的文件名元数据，多图识别只能按文件名编造（"胡乱回答"的根因）。
 *
 * 修复对齐 DaemonAgentHost（daemon-agent-host.ts `prepareRuntimeAttachments`）
 * 的既定语义：附件全量透传，供 runtime 装配
 * image→ImageBlock / video→VideoBlock / file→DocumentBlock；
 * `runtimeTypeForChatVideoAttachment` 负责无视频能力（或缺 URL）时把
 * type=video 降为 file，避免误装 VideoBlock。
 *
 * URL 直传不内联 base64：本机/公网 OSS URL 由 Django wire_adapter 的
 * `rewrite_local_oss_images`（受信本机 OSS 直读转 base64）或
 * `normalize_image_urls`（公网下载）在服务端收口——客户端内联会撑爆
 * 代理 1MB 进站闸门（proxy_api.py:476）。
 */

/** 与 `QueryRequest['attachments']`（electron-agent-types.ts）同构的入参形态。 */
export type ChatRequestAttachment = {
  type?: string
  file_id?: string
  filename?: string
  mime_type?: string
  size?: number
  url?: string
  preview_url?: string
}

/**
 * 全量透传聊天附件为 runtime 附件；空输入返回空数组（空桩兼容形态）。
 *
 * 不 mutate 输入；逐字段显式映射（file_id 供本机 transcript 落盘换链，
 * preview_url 供 UI 附件卡还原），缺省 type 兜底为 file。
 */
export function mapChatAttachmentsToRuntimeAttachments(
  attachments: readonly ChatRequestAttachment[] | undefined | null,
  options: { supportsVideoInput?: boolean } = {},
): QueryStreamRuntimeAttachment[] {
  const list = attachments ?? []
  return list.map((a) => ({
    type: runtimeTypeForChatVideoAttachment(
      options.supportsVideoInput,
      a.type ?? 'file',
      a.url,
    ) as QueryStreamRuntimeAttachment['type'],
    file_id: a.file_id,
    filename: a.filename,
    mime_type: a.mime_type,
    size: a.size,
    url: a.url,
    preview_url: a.preview_url,
  }))
}
