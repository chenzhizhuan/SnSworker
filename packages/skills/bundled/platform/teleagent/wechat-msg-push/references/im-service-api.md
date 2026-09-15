---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '2449049d-f9ae-484f-96df-3a70bd53ec16'
  PropagateID: '2449049d-f9ae-484f-96df-3a70bd53ec16'
  ReservedCode1: 'd5f82d1c-5a7e-4574-982b-cc622b77167e'
  ReservedCode2: 'd5f82d1c-5a7e-4574-982b-cc622b77167e'
---

# IM Service API 参考

TeleAgent 内置 IM Service，支持微信、企业微信、飞书三种即时通讯渠道。

## 服务地址

- IM Service: `http://127.0.0.1:17802`（HTTP API，需认证）
- WebSocket: `ws://127.0.0.1:17802/im/ws`（需认证）
- 认证方式: Header `X-IM-Service-Auth` = 环境变量 `SUPER_AGENT_LOCAL_SESSION_KEY` 的值，或 URL 参数 `?sessionKey=xxx`

### 认证密钥获取方法

`SUPER_AGENT_LOCAL_SESSION_KEY` 的值可从以下途径获取：

1. **IM Service 日志**：查看 `~/.local/share/TeleAgent/log/im-service-YYYY-MM-DD.log`，搜索 `x-im-service-auth` 请求头，其值即为认证密钥。
2. **local-secret.json**：文件路径 `~/.local/share/TeleAgent/im-service/local-secret.json`，其中 `localSecret` 字段可能为认证密钥（需验证）。

> **注意**：`/health` 是唯一无需认证的路径。其他所有接口（包括 `/im/weixin/state`、`/im/weixin/login-status` 等）均需要 `X-IM-Service-Auth` 认证头。

## HTTP API 端点

### 微信渠道管理接口

所有接口前缀 `/im/weixin`，需 `X-IM-Service-Auth` 认证头。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/im/weixin/state` | 微信连接状态（connected/bindingStatus/authStatus） |
| POST | `/im/weixin/login-qrcode` | 获取登录二维码，body: `{"force": true}` 强制重新生成 |
| GET | `/im/weixin/login-status` | 登录状态（含 qrcodeStatus: wait/confirmed/idle） |
| POST | `/im/weixin/disconnect` | 解绑微信通道，清空绑定凭证 |
| GET | `/im/weixin/session` | 当前会话信息（sessionId, title, directory） |

### state 接口返回字段

```json
{
  "success": true,
  "data": {
    "channel": "weixin",
    "status": "connected",          // connected / disconnected / error
    "connected": true,
    "bindingStatus": "bound",       // bound / unbound / binding
    "authStatus": "valid",          // valid / unconfigured / unknown
    "showSessionEntry": false,
    "sessionId": "ses_xxx",
    "qrcodeStatus": "idle",         // idle / wait / confirmed
    "qrcodeUrl": "",
    "qrcodeExpiresAt": 0
  }
}
```

### login-qrcode 接口返回字段

```json
{
  "success": true,
  "data": {
    "channel": "weixin",
    "status": "connecting",
    "bindingStatus": "binding",
    "qrcodeStatus": "wait",
    "qrCodeUrl": "https://liteapp.weixin.qq.com/q/xxx?qrcode=xxx&bot_type=3",
    "expiresAt": 1787904532000,
    "pendingLogin": {
      "qrCodeUrl": "...",
      "expiresAt": ...,
      "startedAt": "2026-08-28T08:03:52.000Z"
    },
    "sessionKey": "uuid"
  }
}
```

> **提示**：`qrCodeUrl` 是微信登录链接，需用 `qrcode` 库生成二维码图片供用户扫码。

### disconnect 接口返回字段

```json
{
  "success": true,
  "data": {
    "channel": "weixin",
    "status": "disconnected",
    "bindingStatus": "unbound",
    "authStatus": "unconfigured"
  }
}
```

## 本地消息投递接口（推荐）

通过 TeleAgent 桌面端的本地数据库，写入待投递消息记录，由 push-phone worker 自动拾取并发送。

### 消息发送链路

```
push_wechat.py
    ↓ 向 im_message 表写入 status='to_deliver' 记录
    ↓ route_target 只含 {toUserId}
TeleAgent 桌面端 (im-service)
    ↓ push-phone worker 轮询拾取 to_deliver 记录
    ↓ 从 channel_profile 的 auth_payload 提取 quill（持久 bot 凭证）
    ↓ 用 quill 调用微信 ilink API
用户微信
```

### 关键技术点

- **不依赖 contextToken**：contextToken 在发送链路中是可选参数，真正必需的是 quill——channel profile 中的持久 bot 凭证，不会过期。
- **零网络请求**：所有操作在本机完成，只是读写本地 SQLite 数据库文件，不发起网络请求、不读取进程内存。
- **发送后轮询状态**：写入记录后轮询最多 8 秒，检查消息是否已送达。

### 数据库路径

```
%USERPROFILE%\.local\share\TeleAgent\im-service\im-service.db
```

### 消息记录字段

| 字段 | 值 | 说明 |
|------|------|------|
| `id` | UUID hex | 消息唯一ID |
| `channel` | `weixin` | 渠道名称 |
| `status` | `to_deliver` | 触发 push-phone worker 投递 |
| `outbound_text` | 消息文本 | 要发送的内容 |
| `route_target` | `{"toUserId":"..."}` | 投递目标（JSON） |
| `inbound_source` | `push` | 标识主动推送 |
| `submitted_at` | ISO 时间戳 | 提交时间 |

### 消息状态流转

```
to_deliver → delivered  （成功投递）
           → failed     （投递失败）
           → skipped    （跳过，如渠道不支持）
```

### 微信渠道配置

```
数据库表: im_channel_profile
关键字段:
  - channel = 'weixin'
  - auth_status = 'valid'（已绑定）
  - third_party_user_id = ilink 用户 ID
  - third_party_account_id = ilink bot ID（每次重新绑定会变）
  - auth_payload.quill = quill token（持久 bot 凭证，不过期）
```

## 微信 ilink 协议

微信渠道使用 ilink 协议通信：

- 认证 token: `quill`（存储在 `im_channel_profile` 表的 `auth_payload` 中，为持久 bot 凭证，不会过期）
- API Base URL: `https://ilinkai.weixin.qq.com`
- 消息发送端点: `ilink/bot/sendmessage`（POST）
- 轮询端点: `ilink/bot/getupdates`（POST，长轮询）
- 配置查询: `ilink/bot/getconfig`（POST）

### ilink 请求头

```
Content-Type: application/json
AuthorizationType: ilink_bot_token
X-WECHAT-UIN: <4字节随机数的base64编码>
Authorization: Bearer <quill_token>
Content-Length: <body长度>
```

### ilink 消息体格式

```json
{
  "from_user_id": "",
  "to_user_id": "<ilink_user_id>",
  "client_id": "im-service-weixin-<uuid>",
  "message_type": "bot",
  "message_state": "finish",
  "context_token": null,
  "item_list": [{"type": 1, "text_item": {"text": "消息内容"}}],
  "base_info": {"channel_version": "1"}
}
```

> **注意**: context_token 字段在主动推送场景中可选（为 null 即可），
> 真正必需的认证凭据是 quill token。

## WebSocket 协议（参考）

### 连接

连接到 `ws://127.0.0.1:17802/im/ws`（需 `SUPER_AGENT_LOCAL_SESSION_KEY` 认证）

### 心跳

- 服务端发送: `{"kind": "ping"}`
- 客户端回复: `{"kind": "pong"}`

### 请求/响应

**请求格式:**
```json
{
  "kind": "req",
  "id": "唯一ID（UUID）",
  "method": "方法名",
  "params": { ... }
}
```

**成功响应:**
```json
{
  "kind": "res",
  "id": "对应的请求ID",
  "ok": true,
  "result": { ... }
}
```

**失败响应:**
```json
{
  "kind": "res",
  "id": "对应的请求ID",
  "ok": false,
  "error": "错误信息"
}
```

### 可用方法

| 方法 | 参数 | 说明 |
|------|------|------|
| `msg.send_phone` | `{channel, text, files}` | 主动推送消息 |
| `result.submit` | `{channel, status, text, files}` | 提交任务结果 |
| `intervention.notify` | `{channel, promptText}` | 干预通知 |
| `session.register` | `{channel, sessionId}` | 注册会话 |
| `session.clear` | `{channel}` | 清除会话 |
| `inbound.ack` | - | 确认入站消息 |
| `renderer.ready` | `{}` | 标记就绪 |

## 微信通道重置流程（解绑 + 重新扫码）

当微信通道状态异常（如 `session timeout`、状态不一致、用户收不到消息）时，可通过 HTTP API 完成完整重置：

### 步骤

```python
import urllib.request, json, qrcode
from PIL import Image

base = 'http://127.0.0.1:17802'
auth = '<X-IM-Service-Auth 值>'  # 从日志或 local-secret.json 获取

# 1. 解绑当前通道
req = urllib.request.Request(base + '/im/weixin/disconnect', data=b'{}', method='POST')
req.add_header('X-IM-Service-Auth', auth)
req.add_header('Content-Type', 'application/json')
resp = urllib.request.urlopen(req, timeout=10)
# 返回: bindingStatus=unbound, authStatus=unconfigured

# 2. 获取新登录二维码
req = urllib.request.Request(base + '/im/weixin/login-qrcode',
    data=json.dumps({'force': True}).encode(), method='POST')
req.add_header('X-IM-Service-Auth', auth)
req.add_header('Content-Type', 'application/json')
resp = urllib.request.urlopen(req, timeout=15)
data = json.loads(resp.read())['data']
qr_url = data['qrCodeUrl']

# 3. 生成二维码图片供用户扫码
qr = qrcode.QRCode(version=1, box_size=12, border=4)
qr.add_data(qr_url)
qr.make(fit=True)
img = qr.make_image(fill_color='black', back_color='white')
img.save('weixin_login_qr.png')

# 4. 轮询 login-status 确认扫码完成
import time
for _ in range(60):
    req = urllib.request.Request(base + '/im/weixin/login-status')
    req.add_header('X-IM-Service-Auth', auth)
    resp = urllib.request.urlopen(req, timeout=8)
    data = json.loads(resp.read())['data']
    if data.get('qrcodeStatus') == 'confirmed':
        print('绑定成功!', data)
        break
    time.sleep(2)
```

### 注意事项

- **解绑会清空 quill 凭证**：解绑后到重新扫码完成期间，推送功能不可用。
- **每次绑定生成新 bot**：`third_party_account_id`（bot ID）每次重新绑定都会变化（如 `258364463e58@im.bot` → `310b318ac3ca@im.bot`）。
- **扫码后需验证**：用 `push_wechat.py --check-status` 确认 `auth_status: valid` 后再推送。

## 故障排除

### 状态不一致问题

`weixin-state.json`（路径：`~/.local/share/TeleAgent/im-service/weixin-state.json`）可能显示旧的错误状态（如 `lastError: session timeout`、`consecutiveFailures: 3`），即使数据库中 `auth_status = valid`。

**排查方法**：
1. 以 HTTP API `/im/weixin/state` 返回的 `status` 和 `authStatus` 为准。
2. `/im/weixin/login-status` 的 `qrcodeStatus` 可确认扫码是否完成。
3. `weixin-state.json` 中的 `accountId` 可能是旧 bot ID，与数据库中的 `third_party_account_id` 不一致——这是正常的，以数据库为准。

### 图片推送 CDN 失败

首次图片推送可能返回 `weixin cdn upload failed: HTTP 500`，这是微信 CDN 的临时问题。

**解决方法**：等待 3 秒后重试，通常第二次即可成功。

### 消息显示 delivered 但用户收不到

参见 SKILL.md 中的"⚠️ 重要：消息可见性与通道区分"章节。核心原因：消息通过 ilink 机器人账号发送，出现在独立的机器人会话中，不在普通好友聊天列表里。

> AI生成