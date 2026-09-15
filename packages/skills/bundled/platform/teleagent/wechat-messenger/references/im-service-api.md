---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '6cddbba1-66b7-4141-9187-5dac51002c64'
  PropagateID: '6cddbba1-66b7-4141-9187-5dac51002c64'
  ReservedCode1: '10bdde75-74b2-44be-bed3-c153f0093741'
  ReservedCode2: '10bdde75-74b2-44be-bed3-c153f0093741'
---

# IM Service API 参考

TeleAgent 内置 IM Service，支持微信、企业微信、飞书三种即时通讯渠道。

## 服务地址

- IM Service: `http://127.0.0.1:17802`（HTTP API，需认证）
- WebSocket: `ws://127.0.0.1:17802/im/ws`（需认证）
- 认证方式: Header `X-IM-Service-Auth` = 环境变量 `SUPER_AGENT_LOCAL_SESSION_KEY` 的值，或 URL 参数 `?sessionKey=xxx`

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

## 无需认证的路径

| 路径 | 说明 |
|------|------|
| `/health` | 健康检查 |
| `/im/weixin/state` | 微信连接状态 |
| `/im/wecom/state` | 企业微信状态 |
| `/im/feishu/state` | 飞书状态 |
| `/im/weixin/login-status` | 微信登录状态 |
| `/im/wecom/login-status` | 企业微信登录状态 |
| `/im/feishu/login-status` | 飞书登录状态 |
| `/im/ws` | WebSocket 端点 |

> AI生成