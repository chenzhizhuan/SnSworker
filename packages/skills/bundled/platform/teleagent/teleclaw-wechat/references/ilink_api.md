---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'd720c46f-f259-4313-a2af-f13ddf16024c'
  PropagateID: 'd720c46f-f259-4313-a2af-f13ddf16024c'
  ReservedCode1: 'c71b9504-5147-4e15-bb29-ae4f941ee142'
  ReservedCode2: 'c71b9504-5147-4e15-bb29-ae4f941ee142'
---

# 微信 iLink Bot API 协议参考

> 基于 `@tencent-weixin/openclaw-weixin@1.0.2` 源码逆向分析，截止 2026 年 3 月

## 目录

1. [协议概览](#1-协议概览)
2. [鉴权机制](#2-鉴权机制)
3. [API 端点](#3-api-端点)
4. [消息结构](#4-消息结构)
5. [媒体文件处理](#5-媒体文件处理)
6. [踩坑要点](#6-踩坑要点)
7. [合规与限制](#7-合规与限制)

## 1. 协议概览

iLink 是腾讯官方开放的微信个人号 Bot API 协议，纯 HTTP/JSON，接入域名 `ilinkai.weixin.qq.com`。

**整体流程**：

```
用户微信 <-> iLink 服务器 (ilinkai.weixin.qq.com) <-> 你的 Bot 程序 <-> AI 接口
```

**核心能力**：
- 扫码登录获取 bot_token
- 长轮询收消息（35s hold + 游标推进）
- 发送文本/图片/语音/文件/视频消息
- "正在输入" typing 状态
- CDN 媒体加解密（AES-128-ECB）

## 2. 鉴权机制

### 请求头

每次请求都必须携带以下 Header：

```json
{
  "Content-Type": "application/json",
  "AuthorizationType": "ilink_bot_token",
  "X-WECHAT-UIN": "<随机uint32转base64>",
  "Authorization": "Bearer <bot_token>"
}
```

**X-WECHAT-UIN 生成方式**：

```python
import base64, random
uin = str(random.randint(0, 0xFFFFFFFF))
encoded = base64.b64encode(uin.encode()).decode()
```

- 每次请求重新生成，起到防重放作用
- 登录前的请求不带 Authorization

### 登录流程

```
1. GET get_bot_qrcode?bot_type=3 → 获取 qrcode + qrcode_img_content
2. GET get_qrcode_status?qrcode=xxx（轮询）→ status="confirmed" 时得到 bot_token + baseurl
3. 持久化 bot_token，后续所有请求使用 Bearer 鉴权
```

## 3. API 端点

| 端点 | 方法 | 功能 | 超时 |
|------|------|------|------|
| `/ilink/bot/get_bot_qrcode` | GET | 获取登录二维码 | - |
| `/ilink/bot/get_qrcode_status` | GET | 轮询扫码状态 | 35s |
| `/ilink/bot/getupdates` | POST | 长轮询收消息（核心） | 35s |
| `/ilink/bot/sendmessage` | POST | 发送消息 | 15s |
| `/ilink/bot/getconfig` | POST | 获取 typing_ticket | 10s |
| `/ilink/bot/sendtyping` | POST | 发送 typing 状态 | 10s |
| `/ilink/bot/getuploadurl` | POST | 获取 CDN 预签名上传地址 | 15s |

每个请求的 body 中需要包含 `base_info: { channel_version: "1.0.2" }`。

### 3.1 get_bot_qrcode

```http
GET /ilink/bot/get_bot_qrcode?bot_type=3
```

响应：
```json
{
  "qrcode": "轮询用的key",
  "qrcode_img_content": "https://liteapp.weixin.qq.com/q/...（URL）或 base64 图片数据"
}
```

注意：`qrcode_img_content` 可以是 URL（以 http 开头）、SVG（以 `<svg` 开头）或 base64 数据。

### 3.2 get_qrcode_status

```http
GET /ilink/bot/get_qrcode_status?qrcode=<上一步的 qrcode key>
```

响应（轮询直到 status 为 confirmed）：
```json
{
  "status": "confirmed",
  "bot_token": "xxx",
  "baseurl": "https://ilinkai.weixin.qq.com",
  "account_id": "xxx"
}
```

其他 status 值：`waiting`（等待扫码）、`scaned`（已扫码待确认）、`scaned_but_redirect`（需切换域名）、`cancelled`、`expired`。

### 3.3 getupdates（核心）

```json
// 请求
POST /ilink/bot/getupdates
{
  "get_updates_buf": "<上次返回的游标，首次为空字符串>",
  "base_info": { "channel_version": "1.0.2" }
}

// 响应
{
  "ret": 0,
  "msgs": [ ...消息列表... ],
  "get_updates_buf": "<新游标，下次请求必须带上>",
  "longpolling_timeout_ms": 35000
}
```

**关键**：`get_updates_buf` 是游标，必须每次更新，否则会重复收到消息。

### 3.4 getconfig

```json
POST /ilink/bot/getconfig
{
  "ilink_user_id": "<用户ID>",
  "context_token": "<当前消息的 context_token>",
  "base_info": { "channel_version": "1.0.2" }
}

// 响应
{
  "typing_ticket": "xxx（缓存24h）"
}
```

### 3.5 sendtyping

```json
POST /ilink/bot/sendtyping
{
  "ilink_user_id": "<用户ID>",
  "typing_ticket": "<从 getconfig 获取>",
  "status": 1,  // 1=正在输入, 2=取消
  "base_info": { "channel_version": "1.0.2" }
}
```

### 3.6 sendmessage（核心）

**必须包含完整字段，缺少任意字段会导致消息静默丢失**：

```json
POST /ilink/bot/sendmessage
{
  "msg": {
    "from_user_id": "",
    "to_user_id": "<用户ID@im.wechat>",
    "client_id": "openclaw-weixin-<随机hex>",
    "message_type": 2,
    "message_state": 2,
    "context_token": "<从收到消息中取>",
    "item_list": [
      { "type": 1, "text_item": { "text": "回复内容" } }
    ]
  },
  "base_info": { "channel_version": "1.0.2" }
}
```

**字段说明**：
- `from_user_id`：必须为空字符串
- `client_id`：格式 `openclaw-weixin-<随机hex>`，每条消息新生成
- `message_type`：2 表示 Bot 发出
- `message_state`：2 表示 FINISH（完整消息）
- `context_token`：**必须从当前收到的消息中取，不可复用旧消息的 token**

### 3.7 getuploadurl（媒体上传）

```json
POST /ilink/bot/getuploadurl
{
  "file_type": 2,  // 2=图片, 3=语音, 4=文件, 5=视频
  "file_size": <字节数>,
  "file_name": "<文件名>",
  "aes_key": "<base64编码的AES-128密钥>",
  "base_info": { "channel_version": "1.0.2" }
}

// 响应
{
  "upload_full_url": "https://novac2c.cdn.weixin.qq.com/c2c/...",
  "upload_param": "旧版上传参数（如无 upload_full_url 则用此拼接）"
}
```

## 4. 消息结构

### 入站消息

```json
{
  "seq": 1,
  "message_id": 7441535359615655688,
  "from_user_id": "o9cq80xxx@im.wechat",
  "to_user_id": "2a4d413230a5@im.bot",
  "message_type": 1,
  "message_state": 2,
  "context_token": "AARzJWAF...",
  "item_list": [
    { "type": 1, "text_item": { "text": "你好" } }
  ]
}
```

### ID 格式规律

- 用户 ID：`xxx@im.wechat`
- Bot ID：`xxx@im.bot`

### 消息类型（item_list[].type）

| type | 含义 | 数据位置 |
|------|------|----------|
| 1 | 文本 | `text_item.text` |
| 2 | 图片 | `image_item` + CDN 加密存储 |
| 3 | 语音 | `voice_item`（silk 编码，附转文字） |
| 4 | 文件附件 | `file_item` |
| 5 | 视频 | `video_item` |

### 引用消息

入站消息可能包含 `ref_msg` 字段，为只读（发送不支持引用）：

```json
{
  "ref_msg": {
    "message_id": 123,
    "from_user_id": "xxx@im.wechat",
    "item_list": [...]
  }
}
```

## 5. 媒体文件处理

### 加密方式：AES-128-ECB

微信 CDN 上所有媒体文件都经过 AES-128-ECB 加密。

**上传流程**：
1. 生成随机 16 字节 AES key
2. 用 AES-128-ECB 加密文件
3. 调用 `getuploadurl` 获取预签名 URL
4. PUT 加密文件到 CDN
5. 在 `sendmessage` 中带上 `aes_key`（base64）和 CDN 引用参数

**下载流程**：
1. 从入站消息中获取 `media.full_url`（新版）或 `encrypt_query_param`（旧版）
2. 下载加密文件
3. 用消息中的 `aes_key` 解密

### 图片发送完整示例

```python
import os, base64, hashlib
from Crypto.Cipher import AES

# 1. 读取文件
with open("image.png", "rb") as f:
    file_data = f.read()

# 2. 生成 AES key
aes_key = os.urandom(16)

# 3. AES-128-ECB 加密（需补齐到16字节倍数）
def pkcs7_pad(data, block_size=16):
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len] * pad_len)

cipher = AES.new(aes_key, AES.MODE_ECB)
encrypted = cipher.encrypt(pkcs7_pad(file_data))

# 4. 获取上传地址
md5 = hashlib.md5(encrypted).hexdigest()
aes_key_b64 = base64.b64encode(aes_key).decode()

# 5. PUT 上传到 CDN
# 6. 在 sendmessage 的 item_list 中添加图片消息项
```

## 6. 踩坑要点

### 坑 1：qrcode_img_content 是 URL，必须编码为二维码图片（最关键）

`qrcode_img_content` 是一个以 `http` 开头的 URL（如 `https://liteapp.weixin.qq.com/q/...`），
**该 URL 无法在浏览器中直接访问成功**，也不能让用户复制链接后在微信中打开。

必须将此 URL 编码为二维码图片（PNG），然后由用户使用微信"扫一扫"功能扫描该图片完成绑定。

```python
import qrcode

# 正确做法：将 URL 编码为二维码图片
qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
qr.add_data(qrcode_img_content)  # 这是 URL
qr.make(fit=True)
img = qr.make_image(fill_color="black", back_color="white")
img.save("qrcode.png")
# 然后让用户用微信扫描 qrcode.png
```

错误做法（会失败）：
- 将 URL 发给用户让其点击访问
- 将 URL 复制到微信文件传输助手中打开
- 在浏览器中直接访问 URL

### 坑 2：aiohttp 拒绝解析 JSON

iLink 服务器可能返回 `Content-Type: application/octet-stream`，需要 `content_type=None`：

```python
data = await res.json(content_type=None)
```

### 坑 3：只有第一条消息能收到回复（最关键）

**原因**：`sendmessage` 缺少必要字段，或漏掉 `getconfig` + `sendtyping` 的前置调用。

**必须**：
- `from_user_id` = 空字符串
- `client_id` = `openclaw-weixin-<随机hex>`
- 包含 `base_info: { channel_version: "1.0.2" }`
- 发送前调用 `getconfig` 获取 typing_ticket
- 发送前调用 `sendtyping { status: 1 }`
- 发送后调用 `sendtyping { status: 2 }`

### 坑 4：context_token 不能复用

每条收到的消息都有独立的 `context_token`，回复时必须使用当前消息的 token。复用旧 token 会导致消息静默丢失（HTTP 200 但不投递）。

### 坑 5：24小时有效期

iLink 连接有效期为 24 小时，到期后必须重新扫码。需要实现自动重连机制。

### 坑 6：Bot ID 每次登录会变

每次扫码登录后 Bot 的 `@im.bot` 部分会变化，这是 iLink 的设计。

## 7. 合规与限制

### 腾讯条款要点

- 腾讯仅作"消息管道"，不存储用户内容，不提供 AI 服务
- 腾讯保留限速、内容过滤、随时终止服务的权利
- 禁止绕过技术保护措施、违法活动
- 腾讯收集 IP 地址和操作日志用于安全审计

### 当前能力边界

- **不能主动推送**：必须用户先发消息（context_token 机制限制）
- **不能发送引用消息**：ref_msg 是只读字段
- **媒体需自行加解密**：AES-128-ECB
- **消息历史不可拉取**：只有游标机制
- **速率限制未公开**：需要实测

### 参考开源项目

| 项目 | 语言 | 特点 |
|------|------|------|
| codeenxi/weixin-ClawBot-API | Python/Node.js | 免 OpenClaw 直接调用，含配置管理 |
| minibear2021/wechat_clawbot_sdk | Python | 全异步 SDK，会话复用，媒体支持 |
| ikrong/wx-clawbot | TypeScript | 事件驱动，简洁封装 |
| x1ah/wechat-ilink-demo | Node.js | 协议拆解，最简裸调 |
| lroolle/wxclawbot-cli | Node.js | 主动推送能力 |

> AI生成