---
name: wechat-messenger
description: "Send text, image, or combined messages to the user's bound WeChat account via TeleAgent local IM delivery interface. Auto-resolves bound user; supports message status polling and delivery confirmation. Triggers: '发微信消息', '微信推送', '微信通知', '推微信', '发微信', '通知微信', 'send to WeChat', 'push to WeChat', 'notify WeChat', '微信发消息', 'WeChat message'."
name_cn: 微信消息助手
description_cn: 向已绑定的微信账号发送文字、图片或图文消息
create_source: super-agent-skill-creator
---

# 微信消息助手 (wechat-messenger)

通过 TeleAgent 桌面端的本地消息投递接口，向已绑定的微信发送消息。

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

## 图片推送说明

- 通过 `file_paths` 字段写入图片本地路径（JSON 数组格式），push-phone worker 会自动上传并发送
- `outbound_text` 字段可选填附言文字，也可留空仅发送图片
- 图片文件大小限制 20MB（微信限制）
- 支持常见图片格式（jpg、png、gif 等）

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
sys.path.insert(0, r'C:\Users\Administrator\.config\TeleAgent\skills\wechat-connection-universal\scripts')
from push_wechat import send_message_via_db, send_image_via_db, check_weixin_status

# 发送文本消息（toUserId 自动使用绑定用户）
result = send_message_via_db("你好，这是提醒消息")

# 发送图片消息
result = send_image_via_db(r"C:\path\to\image.jpg")

# 发送图片+附言
result = send_image_via_db(r"C:\path\to\image.jpg", text="这是图片说明")

# 检查微信绑定状态
status = check_weixin_status()
```

### 6. 图片安全

- **文件存在性校验**：发送前检查图片路径是否存在，不存在则直接返回错误
- **文件大小限制**：图片最大 20MB，超过则拒绝发送

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

## 与定时任务联动

结合 `scheduler` 技能，可创建定时推送任务：

```
1. 创建定时任务，每天早上7点执行
2. 任务 prompt: "使用 wechat-messenger 技能给微信发送提醒消息"
3. 定时触发后自动推送微信消息
```

## 注意事项

- 消息通过微信助手账号（ilink bot）代发
- 每条消息都有唯一的 msg_id，可用于追踪投递状态
- 本技能仅操作本地数据库，不涉及任何外部网络传输
