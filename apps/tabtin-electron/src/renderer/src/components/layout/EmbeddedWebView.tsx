/**
 * EmbeddedWebView — 内置浏览器组件。
 *
 * 用于在主画布中嵌入外部网页（场景市场 / 经营看板）。
 * 使用 iframe 实现，填充父容器全部空间。
 */

import React from 'react'

interface EmbeddedWebViewProps {
  url: string
}

export const EmbeddedWebView: React.FC<EmbeddedWebViewProps> = ({ url }) => {
  return (
    <div className="h-full w-full overflow-hidden">
      <iframe
        src={url}
        className="h-full w-full border-0"
        title="embedded-web-view"
        sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-downloads"
      />
    </div>
  )
}

EmbeddedWebView.displayName = 'EmbeddedWebView'
