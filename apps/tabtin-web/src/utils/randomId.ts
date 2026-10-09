/**
 * 非安全上下文（HTTP）安全的 UUID 生成。
 *
 * 背景：`crypto.randomUUID` 是 secure context only API。本平台 Web 形态
 * （compose.web.yaml）以 `http://<SERVER_IP>:13490` 直连公网 IP 部署，
 * 浏览器判定为非安全上下文，`crypto.randomUUID` 不存在，裸调用抛
 * `TypeError: crypto.randomUUID is not a function`。
 * 已知事故：登录后构造 ChatClient 时 getDeviceId() 崩溃，导致 WS 网关
 * （表格事件/通知/分享事件）整体挂载失败（WebNotificationWS attach failed）。
 *
 * 降级链：
 *   1. `crypto.randomUUID`（secure context / Electron file://，最优先）
 *   2. `crypto.getRandomValues` 手拼 RFC 4122 v4 —— 该 API 在非安全
 *      上下文依然可用，随机性质量等同原生 randomUUID
 *   3. `Date.now + Math.random` 兜底（极老环境，仅保证唯一性近似）
 */
export function randomUUID(): string {
  const c = globalThis.crypto
  if (c && typeof c.randomUUID === 'function') {
    return c.randomUUID()
  }
  if (c && typeof c.getRandomValues === 'function') {
    const bytes = new Uint8Array(16)
    c.getRandomValues(bytes)
    // RFC 4122 version 4 / variant 位
    bytes[6] = (bytes[6] & 0x0f) | 0x40
    bytes[8] = (bytes[8] & 0x3f) | 0x80
    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
    return (
      hex.slice(0, 8) +
      '-' +
      hex.slice(8, 12) +
      '-' +
      hex.slice(12, 16) +
      '-' +
      hex.slice(16, 20) +
      '-' +
      hex.slice(20)
    )
  }
  return `web-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}
