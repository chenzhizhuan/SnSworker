/**
 * useWebviewDisplay — flag=webview 时的显示驱动 hook
 *
 * 与 useViewDisplay 的关系：**顶部分流、结构对齐**。EmbeddedCrawlView 在
 * flag=webview 时把 useViewDisplay 置于 managedExternally（不发
 * crawl-view:show / setViewBounds IPC），由本 hook 驱动 WebviewManager：
 *
 *   - 主 effect：仅 isActive 决定 show / hide（throttle）。webview 已在 DOM
 *     合成层（稳定层 z=10），App 弹窗在 z-modal=50，**不再**因 overlayCount
 *     把页面藏掉——那是 WCV 原生层盖不住 DOM 时的绕行，搬过来等于根治失效。
 *   - overlayCount > 0 时只开鼠标穿透：Electron <webview> guest 偶发仍会吞
 *     被遮罩盖住区域的点击，穿透让事件落回宿主弹窗/backdrop。
 *   - bounds 只作"容器已有有效尺寸"的门槛信号，实际几何由 WebviewManager
 *     测量 slot rect（CSS px）
 *   - 几何跟随：WebviewManager.syncTo + 与 useViewDisplay 相同的布局事件
 *   - 卸载：hide（与 useViewDisplay 的 isClosing 检查同口径）
 *
 * flag=wcv 时本 hook 完全惰性（enabled=false，所有 effect 空跑），
 * 对现状路径零影响。
 */

import { useCallback, useEffect, useLayoutEffect, useRef } from 'react'
import { useCrawlTabStore } from '@stores/useCrawlTabStore'
import {
  beginCrawlViewMousePassthrough,
  endCrawlViewMousePassthrough,
} from '@/crawlspace/crawl-view-mouse-passthrough-depth'
import { CRAWL_VIEW_LAYOUT_CHANGE_EVENT, getElementViewBounds } from '@/utils/crawl-view-bounds'
import { createIPCErrorHandler } from '../utils/ipc-error-handler'
import { getWebviewManager } from '../../../crawlspace/webview-manager/WebviewManager'

const handleError = createIPCErrorHandler('WebviewDisplay')

type Bounds = { x: number; y: number; width: number; height: number }

export type WebviewDisplayOptions = {
  /** flag=webview 且非 managedExternally 时为 true；false 时全部 effect 空跑 */
  enabled: boolean
  tabId: string
  containerRef: React.RefObject<HTMLDivElement | null>
  showViewRef: React.MutableRefObject<((targetUrl?: string, boundsOverride?: Bounds) => void) | null>
  hostView: { hide?: (viewId: string) => Promise<unknown> } | undefined
  isActive: boolean
  overlayCount: number
  crawlspaceId?: string
}

export function useWebviewDisplay({
  enabled,
  tabId,
  containerRef,
  showViewRef,
  hostView,
  isActive,
  overlayCount,
  crawlspaceId,
}: WebviewDisplayOptions): void {
  const pendingShowRef = useRef(false)
  /** overlayCount 跨 0 边界时持有/释放穿透引用计数，避免与拖拽穿透互相提前关闭 */
  const overlayPassthroughHeldRef = useRef(false)

  const releaseOverlayPassthrough = useCallback(() => {
    if (!overlayPassthroughHeldRef.current) return
    endCrawlViewMousePassthrough()
    overlayPassthroughHeldRef.current = false
  }, [])

  const syncOverlayPassthrough = useCallback((shouldHold: boolean) => {
    if (shouldHold === overlayPassthroughHeldRef.current) return
    if (shouldHold) {
      beginCrawlViewMousePassthrough()
      overlayPassthroughHeldRef.current = true
    } else {
      endCrawlViewMousePassthrough()
      overlayPassthroughHeldRef.current = false
    }
  }, [])

  const tryShowWithFreshBounds = useCallback((): boolean => {
    const bounds = getElementViewBounds(containerRef.current)
    if (!bounds) {
      pendingShowRef.current = true
      return false
    }
    pendingShowRef.current = false
    // 先 syncTo 再 show：manager.show 内部依赖 slotEl 同步测量最新几何
    // （measureAndApply）后才 reveal——若先 show，slotEl 还是上一会话的旧 slot
    // （已断开），会走 fallback 用陈旧 lastRect reveal，导致切回时在旧位置
    // 闪现一帧（左上角残留的根因）。
    if (containerRef.current) {
      getWebviewManager().syncTo(tabId, containerRef.current)
    }
    showViewRef.current?.(undefined, bounds)
    return true
  }, [containerRef, showViewRef, tabId])

  // ── 主 effect：仅 isActive 决定 show/hide；overlay 只穿透、不藏页 ──
  // 用 useLayoutEffect（pre-paint）而不是 useEffect：webview 挂在 body 直属
  // 稳定层（#tabtin-webview-layer, z=10），React 层的 DOM 隐藏覆盖不到它；
  // isActive 变 false 时如果 hide 在 post-paint 才执行，切走标签/一级菜单的
  // 那一帧里 webview 仍 visible 停在旧 rect 上，会"闪现"在界面上（2026-09-15
  // live：协作沟通 → 切一级菜单闪现）。useLayoutEffect 让 hide 在浏览器绘制
  // 前同步生效，彻底消除这一帧窗口。show 分支内部仍走 tryShowWithFreshBounds
  // （含 manager.show + syncTo，同步路径），语义不变。
  useLayoutEffect(() => {
    if (!enabled) {
      releaseOverlayPassthrough()
      return
    }

    if (!isActive) {
      pendingShowRef.current = false
      releaseOverlayPassthrough()
      hostView?.hide?.(tabId).catch(handleError('hide'))
      return
    }

    // 页面保持可见；浮层打开时只穿透鼠标，让弹窗/backdrop 收到点击
    syncOverlayPassthrough(overlayCount > 0)

    if (!containerRef.current) return

    tryShowWithFreshBounds()

    // 容器尺寸变化：show 仍 pending 时重试；否则交给 manager 重新测量
    const resizeObserver = typeof ResizeObserver !== 'undefined'
      ? new ResizeObserver(() => {
          if (pendingShowRef.current) {
            tryShowWithFreshBounds()
            return
          }
          getWebviewManager().requestSync(tabId)
        })
      : null
    if (resizeObserver && containerRef.current) {
      resizeObserver.observe(containerRef.current)
    }

    return () => {
      resizeObserver?.disconnect()
    }
  }, [
    enabled,
    isActive,
    overlayCount,
    tabId,
    containerRef,
    hostView,
    tryShowWithFreshBounds,
    releaseOverlayPassthrough,
    syncOverlayPassthrough,
  ])

  // ── 布局事件触发点：对齐 useViewDisplay（浮层打开时仍跟几何，不因 overlay 停） ──
  useEffect(() => {
    if (!enabled || typeof window === 'undefined') return
    const handleLayoutChange = (event: Event): void => {
      const detail = (event as CustomEvent).detail as { viewId?: string } | undefined
      if (detail?.viewId && detail.viewId !== tabId) return
      if (!isActive) return
      window.requestAnimationFrame(() => {
        if (pendingShowRef.current) {
          tryShowWithFreshBounds()
          return
        }
        getWebviewManager().requestSync(tabId)
      })
    }
    window.addEventListener(CRAWL_VIEW_LAYOUT_CHANGE_EVENT, handleLayoutChange)
    window.addEventListener('crawl-view-slot-change', handleLayoutChange)
    return () => {
      window.removeEventListener(CRAWL_VIEW_LAYOUT_CHANGE_EVENT, handleLayoutChange)
      window.removeEventListener('crawl-view-slot-change', handleLayoutChange)
    }
  }, [enabled, isActive, tabId, tryShowWithFreshBounds])

  // ── 卸载：hide + 释放 overlay 穿透（与 useViewDisplay 的 isClosing 检查同口径） ──
  // 同样用 useLayoutEffect：卸载发生在切走/销毁路径，hide 必须在 paint 前生效，
  // 否则卸载帧会闪现 webview 页面。
  // hide 同步执行（不走 Promise.resolve().then 微任务延迟）：useLayoutEffect 的
  // cleanup 已在 pre-paint 同步阶段，微任务延迟会让浏览器先绘制卸载帧再 hide，
  // 仍有一帧闪现窗口。
  useLayoutEffect(() => {
    if (!enabled) return
    const currentTabId = tabId
    return () => {
      releaseOverlayPassthrough()
      const store = useCrawlTabStore.getState()
      const cache = crawlspaceId ? store.crawlspaceContextCache[crawlspaceId] : null
      const isClosing = cache?.viewList?.some(view => view.viewId === currentTabId && view.isClosing)
      if (!isClosing) {
        hostView?.hide?.(currentTabId).catch(handleError('hide'))
      }
    }
  }, [enabled, crawlspaceId, tabId, hostView, releaseOverlayPassthrough])
}
