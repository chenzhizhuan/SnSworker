import { describe, expect, it } from 'vitest'
import { buildUserMessageWithAttachments } from '@tabtin/agent-runtime'
import {
  mapChatAttachmentsToRuntimeAttachments,
  type ChatRequestAttachment,
} from '../chat-attachment-runtime-mapping'

/**
 * 桌面端多图识别根因修复的契约测试。
 *
 * 背景：ElectronAgentHost 的 `prepareRuntimeAttachments` 此前是
 * `async () => []` 空桩——附件进不了 runtime 的 user 消息，模型从未
 * 看到图片本体，多图识别只能按文件名编造。修复对齐 DaemonAgentHost：
 * 附件全量透传（image→ImageBlock / video→VideoBlock / file→DocumentBlock）。
 */
describe('mapChatAttachmentsToRuntimeAttachments', () => {
  it('多张图片全量按序透传，ImageBlock 装配所需字段一个不丢', () => {
    const attachments: ChatRequestAttachment[] = [
      {
        type: 'image',
        file_id: 'file-a',
        filename: 'shot-a.png',
        mime_type: 'image/png',
        size: 1024,
        url: 'http://221.237.179.2:13492/api/services/oss/local-object?object_key=chat%2Fa.png',
        preview_url: 'preview://a',
      },
      {
        type: 'image',
        file_id: 'file-b',
        filename: 'shot-b.jpg',
        mime_type: 'image/jpeg',
        size: 2048,
        url: 'http://221.237.179.2:13492/api/services/oss/local-object?object_key=chat%2Fb.jpg',
      },
      {
        type: 'image',
        file_id: 'file-c',
        filename: 'shot-c.webp',
        mime_type: 'image/webp',
        size: 4096,
        url: 'http://221.237.179.2:13492/api/services/oss/local-object?object_key=chat%2Fc.webp',
      },
    ]

    const out = mapChatAttachmentsToRuntimeAttachments(attachments)

    expect(out).toHaveLength(3)
    expect(out.map((a) => a.type)).toEqual(['image', 'image', 'image'])
    expect(out.map((a) => a.file_id)).toEqual(['file-a', 'file-b', 'file-c'])
    expect(out.map((a) => a.filename)).toEqual(['shot-a.png', 'shot-b.jpg', 'shot-c.webp'])
    expect(out.map((a) => a.mime_type)).toEqual(['image/png', 'image/jpeg', 'image/webp'])
    expect(out.map((a) => a.size)).toEqual([1024, 2048, 4096])
    expect(out[0].url).toContain('object_key=chat%2Fa.png')
    expect(out[0].preview_url).toBe('preview://a')
    expect(out[1].preview_url).toBeUndefined()
  })

  it('file 附件透传为 DocumentBlock 原料', () => {
    const out = mapChatAttachmentsToRuntimeAttachments([
      { type: 'file', file_id: 'doc-1', filename: 'brief.pdf', mime_type: 'application/pdf', size: 999, url: 'https://oss/doc.pdf' },
    ])
    expect(out).toEqual([
      { type: 'file', file_id: 'doc-1', filename: 'brief.pdf', mime_type: 'application/pdf', size: 999, url: 'https://oss/doc.pdf' },
    ])
  })

  it('视频：模型支持原生输入且带 URL 时保留 video', () => {
    const out = mapChatAttachmentsToRuntimeAttachments(
      [{ type: 'video', file_id: 'v-1', url: 'https://cdn/x.mp4' }],
      { supportsVideoInput: true },
    )
    expect(out[0].type).toBe('video')
  })

  it('视频：模型不支持或缺少 URL 时降级为 file（对齐 Daemon 语义）', () => {
    expect(
      mapChatAttachmentsToRuntimeAttachments([{ type: 'video', file_id: 'v-1', url: 'https://cdn/x.mp4' }], { supportsVideoInput: false })[0].type,
    ).toBe('file')
    expect(
      mapChatAttachmentsToRuntimeAttachments([{ type: 'video', file_id: 'v-2' }], { supportsVideoInput: true })[0].type,
    ).toBe('file')
  })

  it('undefined / null / 空数组返回空数组（空桩兼容形态）', () => {
    expect(mapChatAttachmentsToRuntimeAttachments(undefined)).toEqual([])
    expect(mapChatAttachmentsToRuntimeAttachments(null)).toEqual([])
    expect(mapChatAttachmentsToRuntimeAttachments([])).toEqual([])
  })

  it('缺 type 的附件兜底为 file，不抛错', () => {
    const out = mapChatAttachmentsToRuntimeAttachments([{ file_id: 'x', filename: 'blob.bin' }])
    expect(out).toEqual([{ type: 'file', file_id: 'x', filename: 'blob.bin' }])
  })

  it('不 mutate 输入附件数组', () => {
    const attachments: ChatRequestAttachment[] = [{ type: 'image', file_id: 'f', url: 'https://x/a.png' }]
    const snapshot = JSON.stringify(attachments)
    mapChatAttachmentsToRuntimeAttachments(attachments, { supportsVideoInput: false })
    expect(JSON.stringify(attachments)).toBe(snapshot)
  })

  it('与 buildUserMessageWithAttachments 联动：映射结果可装配出等量 ImageBlock', () => {
    const attachments: ChatRequestAttachment[] = [
      { type: 'image', file_id: 'a', url: 'https://cdn/a.png' },
      { type: 'image', file_id: 'b', url: 'https://cdn/b.png' },
    ]
    const runtimeAttachments = mapChatAttachmentsToRuntimeAttachments(attachments)
    const message = buildUserMessageWithAttachments('看看这两张图', runtimeAttachments)
    const blocks = message.content as Array<{ type: string }>
    expect(blocks.filter((b) => b.type === 'image')).toHaveLength(2)
    expect(blocks[0].type).toBe('text')
  })
})
