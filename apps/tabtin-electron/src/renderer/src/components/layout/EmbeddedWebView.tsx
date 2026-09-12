/**
 * EmbeddedWebView — 内置浏览器组件。
 *
 * 用于在主画布中嵌入外部网页（场景市场 / 经营看板）。
 * 使用 Electron <webview> 标签实现（webviewTag: true 已启用），
 * 绕过 iframe 的 X-Frame-Options 限制。
 *
 * 安全策略由主进程 will-attach-webview 白名单统一裁决（attach-policy.ts）：
 *   - browser guest，空 partition（共享默认 session）
 *   - src 仅 http(s)（13490 / 13491 均符合）
 *   - 无 preload / nodeIntegration（sandbox + contextIsolation 强制开启）
 */

import React, { useRef, useCallback, useState } from 'react'

interface EmbeddedWebViewProps {
  url: string
}

export const EmbeddedWebView: React.FC<EmbeddedWebViewProps> = ({ url }) => {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const webviewRef = useRef<HTMLElement | null>(null)

  const handleRef = useCallback((node: HTMLElement | null) => {
    webviewRef.current = node
    if (!node) return

    const wv = node as any

    const handleDidStartLoad = () => {
      setLoading(true)
      setError(null)
    }
    const handleDidFinishLoad = () => {
      setLoading(false)
    }
    const handleDidFailLoad = (e: any) => {
      setLoading(false)
      const desc = e?.errorDescription || '页面加载失败'
      setError(desc)
    }

    wv.addEventListener('did-start-loading', handleDidStartLoad)
    wv.addEventListener('did-finish-load', handleDidFinishLoad)
    wv.addEventListener('did-fail-load', handleDidFailLoad)
  }, [])

  return (
    <div className="relative h-full w-full overflow-hidden">
      <webview
        key={url}
        ref={handleRef as any}
        src={url}
        style={{ width: '100%', height: '100%', border: 'none' }}
        // 空 partition = 共享默认 session（attach-policy 允许）
        // 不设 preload / nodeintegration（will-attach 强制 sandbox + contextIsolation）
      />
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-3">
            <span className="block h-8 w-8 rounded-full border-2 border-border border-t-accent animate-spin" />
            <span className="text-sm text-muted-foreground">正在加载页面…</span>
          </div>
        </div>
      )}
      {error && !loading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex flex-col items-center gap-2 text-center px-8">
            <span className="text-title text-muted-foreground/40">⚠</span>
            <p className="text-sm text-muted-foreground">页面加载失败</p>
            <p className="text-xs text-muted-foreground/60 max-w-md">{error}</p>
          </div>
        </div>
      )}
    </div>
  )
}

EmbeddedWebView.displayName = 'EmbeddedWebView'
