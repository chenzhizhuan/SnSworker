import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'

const mockConnect = vi.fn()
const mockOnEvent = vi.fn()
const mockOnReconnected = vi.fn()
const mockSubscribe = vi.fn()
const mockUnsubscribe = vi.fn()
const mockRequest = vi.fn()
const mockGetStatus = vi.fn()

// mainAgentGateway 走 window.tabtin.agentGateway bridge（main 进程 IPC）：
// - addListener/onReconnectedEvent 是本地 Set，事件经 bridge.onEvent/onReconnected 分发
// - subscribe/unsubscribe 参数为 { topics, options } 包装
// 旧 mock 挂在 chatApi.getGateway 上与现行架构失配，订阅链用例全部空转。
function installBridgeMock(): void {
  ;(window as unknown as { tabtin?: unknown }).tabtin = {
    agentGateway: {
      getStatus: mockGetStatus,
      reconnect: mockConnect,
      onEvent: mockOnEvent,
      onReconnected: mockOnReconnected,
      subscribe: mockSubscribe,
      unsubscribe: mockUnsubscribe,
      request: mockRequest,
    },
  }
}

function uninstallBridgeMock(): void {
  delete (window as unknown as { tabtin?: unknown }).tabtin
}

const mockOrganizationState: {
  selectedOrganization: { id: string } | null
  organizations: Array<{ id: string }>
} = {
  selectedOrganization: { id: 'ws-1' },
  organizations: [{ id: 'ws-1' }],
}

vi.mock('@/stores/useOrganizationStore', () => ({
  useOrganizationStore: (selector: (state: typeof mockOrganizationState) => unknown) =>
    selector(mockOrganizationState),
}))

// membership 守卫与 WS 连接 store：真实实现会拉起 auth/IPC 链，测试环境不可用。
vi.mock('@/services/gatewayOrganizationMembership', () => ({
  isGatewayMembershipReadyForOrganization: () => true,
}))
vi.mock('@/stores/useWsConnectionStore', () => ({
  useWsConnectionStore: (selector: (state: { organizationAccessRecoveryInFlight: boolean }) => unknown) =>
    selector({ organizationAccessRecoveryInFlight: false }),
}))

describe('useGatewayTopic', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    installBridgeMock()
    // getStatus 返回非 ready，让 connect() 走 reconnect 分支（mainAgentGateway 语义）。
    mockGetStatus.mockResolvedValue('idle')
    mockConnect.mockResolvedValue(true)
    mockSubscribe.mockResolvedValue({ ok: true })
    mockUnsubscribe.mockResolvedValue({ ok: true })
    mockRequest.mockResolvedValue({ ok: true })
    mockOrganizationState.selectedOrganization = { id: 'ws-1' }
    mockOrganizationState.organizations = [{ id: 'ws-1' }]
  })

  afterEach(() => {
    uninstallBridgeMock()
    vi.resetModules()
  })

  it('同一 topic 多个消费者并存时只订阅一次，并在最后一个卸载时才退订', async () => {
    const { useGatewayTopic } = await import('../useGatewayTopic')

    const first = renderHook(() => useGatewayTopic({ topic: 'tracker.events.ws-1' }))
    const second = renderHook(() => useGatewayTopic({ topic: 'tracker.events.ws-1' }))

    await waitFor(() => {
      expect(mockSubscribe).toHaveBeenCalledTimes(1)
    })

    first.unmount()
    expect(mockUnsubscribe).not.toHaveBeenCalled()

    second.unmount()

    await waitFor(() => {
      expect(mockUnsubscribe).toHaveBeenCalledTimes(1)
    })
    expect(mockUnsubscribe).toHaveBeenCalledWith({ topics: ['tracker.events.ws-1'] })
    expect(mockRequest).not.toHaveBeenCalled()
  })

  it('organization 未就绪时不尝试连接，状态保持 idle', async () => {
    mockOrganizationState.selectedOrganization = null
    mockOrganizationState.organizations = []

    const { useGatewayTopic } = await import('../useGatewayTopic')

    const { result } = renderHook(() =>
      useGatewayTopic({ topic: 'notifications.user-1' }),
    )

    // 给异步足够时间确认不发生连接
    await new Promise(r => setTimeout(r, 50))

    expect(mockConnect).not.toHaveBeenCalled()
    expect(mockSubscribe).not.toHaveBeenCalled()
    expect(result.current.status).toBe('idle')
  })

  it('topic 为 null 时不尝试连接', async () => {
    const { useGatewayTopic } = await import('../useGatewayTopic')

    const { result } = renderHook(() =>
      useGatewayTopic({ topic: null }),
    )

    await new Promise(r => setTimeout(r, 50))

    expect(mockConnect).not.toHaveBeenCalled()
    expect(result.current.status).toBe('idle')
  })

  it('enabled=false 时不尝试连接', async () => {
    const { useGatewayTopic } = await import('../useGatewayTopic')

    const { result } = renderHook(() =>
      useGatewayTopic({ topic: 'tracker.events.ws-1', enabled: false }),
    )

    await new Promise(r => setTimeout(r, 50))

    expect(mockConnect).not.toHaveBeenCalled()
    expect(result.current.status).toBe('idle')
  })

  it('限流(WS_1007)被判为可重试，会自动重订而不是永久放弃', async () => {
    // 回归：网关限流是 10s/100 条的滑动窗口，属于瞬态。漏进 TRANSIENT 集合会被
    // 当成 non-retryable —— 冷启动 space 一多（每 space 一条 tracker.events），
    // 被拒的 topic 直到下次重连都收不到事件。
    mockSubscribe
      .mockResolvedValueOnce({ ok: false, error: { code: 'WS_1007_RATE_LIMITED', message: 'too many messages, slow down' } })
      .mockResolvedValue({ ok: true })

    const { useGatewayTopic } = await import('../useGatewayTopic')
    const { result } = renderHook(() =>
      useGatewayTopic({ topic: 'tracker.events.ws-rate-limited' }),
    )

    // 首次被限流 → 退避后自动重试 → 第二次成功
    await waitFor(() => {
      expect(mockSubscribe.mock.calls.length).toBeGreaterThanOrEqual(2)
    }, { timeout: 8000 })
    await waitFor(() => {
      expect(result.current.status).toBe('connected')
    }, { timeout: 8000 })
  }, 15000)

  it('权限类失败(WS_1005)仍然不重试', async () => {
    mockSubscribe.mockResolvedValue({
      ok: false,
      error: { code: 'WS_1005_PERMISSION_DENIED', message: 'denied' },
    })

    const { useGatewayTopic } = await import('../useGatewayTopic')
    const { result } = renderHook(() =>
      useGatewayTopic({ topic: 'tracker.events.ws-denied' }),
    )

    await waitFor(() => {
      expect(result.current.status).toBe('error')
    })
    await new Promise(r => setTimeout(r, 300))
    expect(mockSubscribe).toHaveBeenCalledTimes(1)
  })

  it('connect 返回 false 时状态为 error', async () => {
    mockConnect.mockResolvedValue(false)
    const { useGatewayTopic } = await import('../useGatewayTopic')

    const { result } = renderHook(() =>
      useGatewayTopic({ topic: 'tracker.events.ws-1' }),
    )

    await waitFor(() => {
      expect(result.current.status).toBe('error')
    })
  })

  it('selectedOrganization 为 null 但 organizations 列表非空时仍可连接（fallback）', async () => {
    mockOrganizationState.selectedOrganization = null
    mockOrganizationState.organizations = [{ id: 'ws-fallback' }]

    const { useGatewayTopic } = await import('../useGatewayTopic')

    renderHook(() => useGatewayTopic({ topic: 'tracker.events.ws-1' }))

    await waitFor(() => {
      expect(mockConnect).toHaveBeenCalledTimes(1)
      expect(mockSubscribe).toHaveBeenCalledTimes(1)
    })
  })

  it('subscribe 失败时仍从本地重连清单退订', async () => {
    mockSubscribe.mockResolvedValue({
      ok: false,
      error: { code: 'WS_1005_PERMISSION_DENIED', message: 'denied' },
    })

    const { useGatewayTopic } = await import('../useGatewayTopic')

    const { result, unmount } = renderHook(() =>
      useGatewayTopic({ topic: 'billing.events.ws-1' }),
    )

    await waitFor(() => {
      expect(result.current.status).toBe('error')
    })

    expect(mockConnect).toHaveBeenCalledTimes(1)
    unmount()
    await waitFor(() => {
      expect(mockUnsubscribe).toHaveBeenCalledWith({ topics: ['billing.events.ws-1'] })
    })
  })

  it('只把当前 topic 的 envelope 交给业务回调', async () => {
    const { useGatewayTopic } = await import('../useGatewayTopic')
    const onEvent = vi.fn()

    renderHook(() =>
      useGatewayTopic({ topic: 'agent.stream.chat-session-a', onEvent }),
    )

    await waitFor(() => {
      expect(mockOnEvent).toHaveBeenCalledTimes(1)
    })

    const dispatcher = mockOnEvent.mock.calls[0][0] as (envelope: Record<string, unknown>) => void
    dispatcher({
      type: 'agent.stream.lifecycle',
      event_id: 'evt-other',
      _topic: 'agent.stream.chat-session-b',
      payload: { phase: 'start' },
    })
    dispatcher({
      type: 'agent.stream.lifecycle',
      event_id: 'evt-current',
      _topic: 'agent.stream.chat-session-a',
      payload: { phase: 'start' },
    })

    expect(onEvent).toHaveBeenCalledTimes(1)
    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({
      event_id: 'evt-current',
      _topic: 'agent.stream.chat-session-a',
    }))
  })

  it('#10899 重连后 WS_REQUEST_TIMEOUT 会退避重订', async () => {
    mockSubscribe
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({
        ok: false,
        error: { code: 'WS_REQUEST_TIMEOUT', message: 'timeout' },
      })
      .mockResolvedValue({ ok: true })

    const { subscribeGatewayTopic } = await import('../useGatewayTopic')
    const unsubscribe = subscribeGatewayTopic('chat.session.events.s1', {
      logPrefix: 'ChatSessionEventStream',
    })

    await waitFor(() => {
      expect(mockSubscribe).toHaveBeenCalledTimes(1)
    })
    const reconnect = mockOnReconnected.mock.calls[0]?.[0] as (() => void) | undefined
    expect(reconnect).toEqual(expect.any(Function))
    reconnect?.()

    await waitFor(() => {
      expect(mockSubscribe.mock.calls.length).toBeGreaterThanOrEqual(3)
    }, { timeout: 8000 })

    unsubscribe()
  }, 15000)

  it('启动窗口 NOT_READY 退避耗尽后，重连事件仍能恢复订阅（不再永久失联）', async () => {
    // 回归：冷启动 WS 未就绪 → ipc-shim 把 ok:false envelope 转 throw →
    // WS_SUBSCRIBE_THROWN。旧实现在失败分支摘掉 reconnectHandler，
    // 6 次退避耗尽（giving up）后即使网关最终 ready 该 topic 也收不到事件。
    // 新实现保留 listener + reconnectHandler：重连事件到来即补订阅成功。
    const { subscribeGatewayTopic } = await import('../useGatewayTopic')
    const onReconnected = vi.fn()
    let callCount = 0
    mockSubscribe.mockImplementation(async () => {
      callCount += 1
      // 冷启动窗口：首次订阅时 WS 未就绪（ipc-shim 把 ok:false 转 throw）；
      // 重连事件到来后的补订阅即成功。
      if (callCount === 1) {
        throw new Error('ws connection not ready')
      }
      return { ok: true }
    })

    const unsubscribe = subscribeGatewayTopic('tracker.events.ws-coldstart', {
      logPrefix: 'TrackerEventStream',
      onReconnected,
    })

    await waitFor(() => {
      expect(mockSubscribe).toHaveBeenCalledTimes(1)
    })

    // WS 稍后才真正就绪：重连事件到来 → 补订阅 → 恢复
    const reconnect = mockOnReconnected.mock.calls[0]?.[0] as (() => void) | undefined
    expect(reconnect).toEqual(expect.any(Function))
    reconnect?.()

    await waitFor(() => {
      expect(mockSubscribe.mock.calls.length).toBeGreaterThanOrEqual(2)
    }, { timeout: 8000 })
    expect(onReconnected).toHaveBeenCalled()

    unsubscribe()
  }, 15000)

  it('不会把业务 payload.topic 误当作 Gateway 订阅 topic', async () => {
    const { envelopeMatchesGatewayTopic } = await import('../useGatewayTopic')

    expect(envelopeMatchesGatewayTopic({
      type: 'tracker.run.updated',
      payload: {
        topic: 'user-visible-business-topic',
      },
    }, 'tracker.events.ws-1')).toBe(true)
  })
})
