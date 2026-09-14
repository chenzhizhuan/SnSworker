/**
 * EmbeddedWebView — 内置浏览器组件。
 *
 * 用于在主画布中嵌入外部网页（场景市场 / 经营看板）。
 * 使用 Electron <webview> 标签实现（webviewTag: true 已启用），
 * 绕过 iframe 的 X-Frame-Options 限制。
 *
 * 安全策略由主进程 will-attach-webview 白名单统一裁决（attach-policy.ts）：
 *   - browser guest，空 partition（共享默认 session）
 *   - src 仅 http(s)（13481 / 13491 均符合）
 *   - 无 preload / nodeIntegration（sandbox + contextIsolation 强制开启）
 *
 * 事件绑定：Electron <webview> 的 DOM 事件方法（addEventListener）在元素
 * 进入 DOM 之前不可用（"The webview must be attached to the DOM"），
 * 因此 ref callback 需兼容「未就绪 → 就绪」两种时序：
 *   1. node 存在但方法不可用 → 挂 dom-ready 兜底后再绑事件
 *   2. node 就绪且方法可用 → 立即绑定
 * 并叠加 12s 加载超时兜底，避免服务端正常但 overlay 永不消失。
 */

import React, { useRef, useEffect, useState } from 'react'

interface EmbeddedWebViewProps {
  url: string
}

/** 服务端正常但事件链异常时的兜底超时（ms） */
const LOAD_TIMEOUT_MS = 12_000

export const EmbeddedWebView: React.FC<EmbeddedWebViewProps> = ({ url }) => {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const webviewRef = useRef<HTMLElement | null>(null)
  const cleanupRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    // key={url} 保证 url 变更时 remount，此 effect 对应新元素
    const node = webviewRef.current
    if (!node) return
    const wv = node as any

    let bound = false
    // setInterval 与 setTimeout 句柄统一收口为 number，
    // cleanup 时 window.clearTimeout / clearInterval 双清（DOM lib 下两者互兼容）
    const pendingTimers: Array<number> = []

    const handleDidStartLoad = () => {
      setLoading(true)
      setError(null)
    }
    const handleDidFinishLoad = () => {
      setLoading(false)
    }
    const handleDidFailLoad = (e: any) => {
      // isMainFrame=false 的子资源失败不影响页面展示，不打成整页错误
      if (e?.isMainFrame === false) return
      setLoading(false)
      const desc = e?.errorDescription || '页面加载失败'
      setError(desc)
    }

    const bindEvents = () => {
      if (bound || typeof wv.addEventListener !== 'function') return
      bound = true
      wv.addEventListener('did-start-loading', handleDidStartLoad)
      wv.addEventListener('did-finish-load', handleDidFinishLoad)
      wv.addEventListener('did-fail-load', handleDidFailLoad)
    }

    if (typeof wv.addEventListener === 'function') {
      // 元素已 attach，直接绑定
      bindEvents()
    } else {
      // attach 前访问内部方法会抛 "The webview must be attached to the DOM"
      // —— 用 DOM 事件轮询到可绑定为止（TinSandboxView 同款防御思路）
      try {
        wv.addEventListener('dom-ready', () => bindEvents())
      } catch {
        /* 极端时序：留给超时兜底 */
      }
      const poll = window.setInterval(() => {
        try {
          if (typeof wv.addEventListener === 'function') {
            window.clearInterval(poll)
            bindEvents()
          }
        } catch {
          /* still not attached */
        }
      }, 200)
      pendingTimers.push(poll)
    }

    // 兜底：12s 内无论事件链如何，都撤掉 loading（页面可能已可见）
    const timeout = window.setTimeout(() => {
      setLoading(false)
    }, LOAD_TIMEOUT_MS)
    pendingTimers.push(timeout)

    return () => {
      for (const t of pendingTimers) {
        window.clearTimeout(t)
        window.clearInterval(t)
      }
      try {
        if (bound) {
          wv.removeEventListener('did-start-loading', handleDidStartLoad)
          wv.removeEventListener('did-finish-load', handleDidFinishLoad)
          wv.removeEventListener('did-fail-load', handleDidFailLoad)
        }
      } catch {
        /* element may be detached */
      }
    }
  }, [url])

  return (
    <div className="relative h-full w-full overflow-hidden">
      <webview
        key={url}
        ref={webviewRef as any}
        src={url}
        style={{ width: '100%', height: '100%', border: 'none' }}
        // 空 partition = 共享默认 session（attach-policy 允许）
        // 不设 preload / nodeintegration（will-attach 强制 sandbox + contextIsolation）
      />
      {/* 局部加载指示：顶部细进度条 + 右上角小提示，不遮挡主界面 */}
      {loading && (
        <>
          <div className="pointer-events-none absolute inset-x-0 top-0 z-10 h-0.5 overflow-hidden bg-border/40">
            <div className="h-full w-full origin-left bg-brand-500 animate-progress-indeterminate" />
          </div>
          <div className="pointer-events-none absolute right-3 top-2.5 z-10 rounded-full border border-border/60 bg-background/70 px-2.5 py-0.5 text-xs text-muted-foreground backdrop-blur-sm">
            正在加载页面…
          </div>
        </>
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
