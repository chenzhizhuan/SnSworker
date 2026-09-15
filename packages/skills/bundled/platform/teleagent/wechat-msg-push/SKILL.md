---
name: wechat-msg-push
description: 'Connect to ClawBot to push text, image, and file messages to WeChat via TeleAgent local message delivery interface. Supports PDF/Word/Excel and other common file types. Writes a ''to_deliver'' record to the IM Service database; push-phone worker automatically picks it up and delivers to WeChat. Triggers: ''ClawBot推送'', ''推送到ClawBot'', ''ClawBot发消息'', ''ClawBot微信推送'', ''推送文本图片和文件到ClawBot'', ''微信消息对接发送''.'
name_cn: 微信消息对接推送
description_cn: |-
  连接ClawBot，可以推送文本、图片和文件到ClawBot里面，支持PDF/Word/Excel/ZIP等常见文件类型，手机上微信随时可见内容。使用方法（三步）
  1. 打开 TeleAgent 桌面端，在即时通讯模块设置中扫码绑定微信。
  2. 第一次使用：主动通过微信 ClawBot 发送一条消息，激活连接通道。
  3. 之后新建任务调用该技能，对话中直接说：“把 XX 文件发送给我”，消息即达。
AIGC:
  ContentProducer: 001191110102MAD55U9H0F10002
  ContentPropagator: 001191110102MAD55U9H0F10002
  Label: '1'
  ProduceID: c8fe8388-8efe-4591-83ee-8174b838c00b
  PropagateID: c8fe8388-8efe-4591-83ee-8174b838c00b
  ReservedCode1: a5575032-7439-4628-bee9-9bd9eb8febee
  ReservedCode2: a5575032-7439-4628-bee9-9bd9eb8febee
---
# 微信消息对接发送 (微信消息对接发送)

连接ClawBot，可以推送文本、图片和文件到ClawBot里面。通过 TeleAgent 桌面端的本地消息投递接口，向已绑定的微信发送消息。

## 快速使用

### 发送文本消息到微信

```bash
python scripts/push_wechat.py --text "这是一条测试消息"
```

### 发送图片消息到微信

```bash
python scripts/push_wechat.py --image "C:\path\to\image.jpg"
```

### 发送图片+文字消息到微信

```bash
python scripts/push_wechat.py --image "C:\path\to\image.jpg" --text "配图说明文字"
```

### 发送文件消息到微信

```bash
python scripts/push_wechat.py --file "C:\path\to\document.pdf"
```

### 发送文件+文字消息到微信

```bash
python scripts/push_wechat.py --file "C:\path\to\report.xlsx" --text "这是本周报告"
```

### 检查微信绑定状态

```bash
python scripts/push_wechat.py --check-status
```

## 工作原理

本技能利用 TeleAgent 桌面端 IM Service 的本地消息投递接口发送微信消息：

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

**关键技术点：**

- **不依赖 contextToken**：contextToken 在发送链路中是可选参数，真正必需的是 quill——channel profile 中的持久 bot 凭证，不会过期。
- **零网络请求**：所有操作在本机完成，只是读写本地 SQLite 数据库文件，不发起网络请求、不读取进程内存。
- **发送后轮询状态**：写入记录后轮询最多 8 秒，检查消息是否已送达。

## prepare failed 自动恢复机制

微信 ilink 通道在会话长时间不活跃（如隔夜无交互）时，`sendmessage` 接口会返回 `{"ret":-2,"errmsg":"prepare failed"}`，但 IM Service 仍将数据库状态标记为 `delivered`（HTTP 200 即视为成功），导致脚本误报成功而消息实际未送达。

改进后的脚本内置了**自动检测与恢复**机制：

```
发送消息 → 数据库标记 delivered
    ↓ 扫描 IM Service 日志验证微信服务器真实响应
    ↓ 检测到 prepare failed？
    ├─ 否 → 返回成功（正常流程）
    └─ 是 → 自动发送心跳激活消息（"."）唤醒会话
              ↓ 等待 3 秒
              ↓ 重新发送原始消息并再次验证
              ↓ 最多重试 2 次
              ├─ 成功 → 返回成功
              └─ 仍失败 → 返回 session_expired 错误
```

**关键参数**（可在脚本顶部调整）：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `MAX_RECOVER_ATTEMPTS` | 2 | 最多自动激活重试次数 |
| `ACTIVATION_WAIT` | 3.0 秒 | 发送激活消息后等待秒数 |
| `ACTIVATION_TEXT` | `.` | 心跳激活消息内容 |
| `LOG_SCAN_LINES` | 80 | 日志尾部扫描行数 |

**注意事项**：
- 自动恢复机制仅对命令行入口（`main()`）生效，Python API 直接调用 `send_message_via_db()` 等函数不经过此机制
- 如自动恢复仍失败（返回 `session_expired`），说明 bot 凭证已过期，需重新扫码绑定微信
- 心跳激活消息内容仅为 `.`，对用户干扰极小

## 图片推送说明

- 通过 `file_paths` 字段写入图片本地路径（JSON 数组格式），push-phone worker 会自动上传并发送
- `outbound_text` 字段可选填附言文字，也可留空仅发送图片
- 图片文件大小限制 20MB（微信限制）
- 支持常见图片格式（jpg、png、gif 等）

## 文件推送说明

- 通过 `file_paths` 字段写入文件本地路径（JSON 数组格式），push-phone worker 会自动上传到微信 CDN 并发送
- `outbound_text` 字段可选填附言文字，也可留空仅发送文件
- 文件大小限制 100MB
- 支持常见文件类型：PDF、Word（.doc/.docx）、Excel（.xls/.xlsx）、PPT（.ppt/.pptx）、TXT、CSV 等
- 文件以微信文件消息形式发送，接收方可直接下载查看

## 安全措施

### 1. 数据库并发安全

- **busy_timeout 设置**：连接时设置 `PRAGMA busy_timeout = 5000`，当 IM Service 的 push-phone worker 持有写锁时，脚本会等待最多 5 秒而非立即失败。
- **WAL 模式兼容**：数据库使用 WAL 模式，写入不会阻塞 IM Service 的读取。
- **指数退避轮询**：等待投递结果时逐步增加轮询间隔（0.3s → 2.0s），减少数据库读取压力。
- **锁竞争容错**：轮询中遇到 `OperationalError` 时自动短暂等待后重试。

### 2. 防止消息发送到非绑定用户

- **toUserId 强制绑定**：toUserId 从 `im_channel_profile` 表的绑定信息中读取，不接受外部参数传入，确保消息只能发送给已绑定的微信用户。

### 3. 敏感信息保护

- **不暴露 quill token**：状态检查接口不返回 quill token 和 ilink_user_id 等敏感字段。
- **read_weixin_profile 仅返回必要字段**：调用方无法获取完整 auth_payload。

### 4. 数据库膨胀防护

- **自动清理**：发送成功后自动清理 24 小时前的已投递/失败记录。
- **消息长度限制**：文本内容最长 4096 字符，防止异常大消息。

### 5. 超时安全

- **超时范围限制**：最小 5 秒，最大 120 秒，防止无限等待。

## Python 接口

```python
import sys
sys.path.insert(0, r'C:\Users\Administrator\.config\TeleAgent\skills\微信消息对接发送\scripts')
from push_wechat import send_message_via_db, send_image_via_db, send_file_via_db, check_weixin_status

# 发送文本消息（toUserId 自动使用绑定用户）
result = send_message_via_db("你好，这是提醒消息")

# 发送图片消息
result = send_image_via_db(r"C:\path\to\image.jpg")

# 发送图片+附言
result = send_image_via_db(r"C:\path\to\image.jpg", text="这是图片说明")

# 发送文件消息
result = send_file_via_db(r"C:\path\to\document.pdf")

# 发送文件+附言
result = send_file_via_db(r"C:\path\to\report.xlsx", text="这是本周报告")

# 检查微信绑定状态
status = check_weixin_status()
```

### 6. 图片安全

- **文件存在性校验**：发送前检查图片路径是否存在，不存在则直接返回错误
- **文件大小限制**：图片最大 20MB，超过则拒绝发送

### 7. 文件安全

- **文件存在性校验**：发送前检查文件路径是否存在，不存在则直接返回错误
- **文件大小限制**：文件最大 100MB，超过则拒绝发送

## 前置条件

1. TeleAgent 桌面应用已启动且 IM Service 运行中
2. 微信已在 TeleAgent 中完成扫码绑定（`auth_status = valid`）
3. push-phone worker 正常运行（随 IM Service 自动启动）

## 故障排除

| 问题 | 原因 | 解决 |
|------|------|------|
| `FileNotFoundError` | IM Service 数据库未找到 | 启动 TeleAgent 并绑定微信 |
| `微信渠道认证状态无效` | 未绑定微信或绑定过期 | 在 TeleAgent 设置中重新扫码绑定 |
| `db_write_error` | 数据库写入冲突 | IM Service 正忙，稍后重试 |
| `delivery_timeout` | push-phone worker 未处理 | 检查 IM Service 日志，重启 TeleAgent |
| `delivery_failed` | 发送失败 | 检查 IM Service 日志中的错误信息 |
| `text_too_long` | 消息超过 4096 字符 | 缩短消息内容 |
| `image_not_found` | 图片文件不存在 | 检查文件路径是否正确 |
| `image_too_large` | 图片超过 20MB | 压缩图片后重试 |
| `file_not_found` | 文件不存在 | 检查文件路径是否正确 |
| `file_too_large` | 文件超过 100MB | 压缩或拆分文件后重试 |
| `weixin cdn upload failed: HTTP 500` | 微信 CDN 临时故障 | 等待 3 秒后重试，通常第二次成功 |
| `session_expired: prepare failed` | 会话不活跃，自动激活后仍失败 | bot 凭证可能已过期，重新扫码绑定微信 |
| `prepare failed`（自动恢复已触发） | 会话长时间无交互 | 脚本会自动发送心跳激活消息并重试，通常无需干预 |
| `session timeout`（weixin-state.json） | 旧绑定会话过期 | 通过 im-service API 解绑并重新扫码（详见 references/im-service-api.md「微信通道重置流程」） |
| 消息显示 delivered 但用户收不到 | ilink bot 会话不在普通聊天列表 | 见下方「消息可见性与通道区分」章节 |

## 与定时任务联动

结合 `scheduler` 技能，可创建定时推送任务：

```
1. 创建定时任务，每天早上7点执行
2. 任务 prompt: "使用 微信消息对接发送 技能给微信发送提醒消息"
3. 定时触发后自动推送微信消息
```

## 注意事项

- 消息通过微信助手账号（ilink bot）代发
- 每条消息都有唯一的 msg_id，可用于追踪投递状态
- 本技能仅操作本地数据库，不涉及任何外部网络传输

## ⚠️ 重要：消息可见性与通道区分

### ilink bot 会话不可见问题

消息状态显示 `delivered`（已送达）且 IM Service 日志确认微信服务器返回 HTTP 200 + message_id，**但用户在微信普通聊天列表中看不到消息**。这是因为：

- 消息通过 **ilink 机器人账号**（如 `258364463e58@im.bot`）发送，不是普通微信好友
- 消息出现在微信中一个**独立的机器人会话**里，不在好友聊天列表中
- 用户需要在微信中搜索"ilink"、"超级智能体"或相关机器人名称才能找到

**排查步骤**（当用户反馈"没收到"时）：
1. 确认 `check_weixin_status()` 返回 `auth_status: valid`
2. 查看 IM Service 日志（`~/.local/share/TeleAgent/log/im-service-YYYY-MM-DD.log`）确认 HTTP 200
3. 指导用户在微信中搜索机器人会话（搜索"ilink"或"超级智能体"）
4. 若用户仍找不到，考虑改用 weclawbot-push 通道（消息在 ClawBot 会话中可见）

### 微信通道重置

当微信通道状态异常（session timeout、状态不一致、用户收不到消息）时，可通过 im-service HTTP API 完成完整重置（解绑 → 重新扫码）。详见 [references/im-service-api.md](references/im-service-api.md) 中的「微信通道重置流程」章节。