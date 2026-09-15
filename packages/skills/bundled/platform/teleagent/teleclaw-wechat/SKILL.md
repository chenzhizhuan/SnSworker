---
name: teleclaw-wechat
description: "WeChat iLink Bot dialogue skill for TeleClaw. Connect WeChat personal account via official iLink Bot API (ClawBot) to enable AI-powered conversations. Supports QR code login, long-polling message receiving, text/media sending, typing status, 24h auto-reconnect, and bot commands. Use when user wants to: (1) Connect their WeChat to AI for auto-reply, (2) Build a WeChat chatbot, (3) Send messages via WeChat iLink API, (4) Monitor and reply to WeChat messages automatically, or mentions '微信机器人', '微信Bot', 'ClawBot', 'iLink', 'wechat bot', '微信对话', '微信自动回复'."
name_cn: 微信对话
description_cn: 通过微信官方 iLink Bot API 连接微信个人账号，实现 AI 自动对话收发，支持扫码登录、消息收发、typing 状态和 24 小时自动重连
create_source: super-agent-skill-creator
---

# TeleClaw 微信对话技能

通过腾讯官方 iLink Bot API（微信 ClawBot 插件）连接微信个人账号，让本地 TeleClaw super-agent 成为微信 AI 助手。

## 架构

```
微信用户 → iLink API → ILinkBot → SuperAgentClient → 本地 super-agent (4397/4398) → AI 回复 → iLink API → 微信用户
```

AI 回复由本地运行的 TeleClaw super-agent 提供，无需外部 AI API。凭证从 im-service 进程自动发现，支持 HMAC 签名认证。

## 快速开始

### 前置条件

1. Python >= 3.11
2. 安装依赖：`pip install aiohttp qrcode pillow psutil`
3. 微信客户端（iOS 8.0.70+ / Android 8.0.68+）
4. 已在微信中启用 ClawBot 插件（我 -> 设置 -> 插件）
5. TeleClaw 正在运行（super-agent 服务可用）

### 一键启动

```bash
# 交互模式（首次配置系统提示词）
python scripts/wechat_bot.py

# 非交互模式（使用默认或已有配置，适合后台运行）
python scripts/wechat_bot.py --no-input

# 调试模式
python scripts/wechat_bot.py --no-input --debug
```

脚本自动生成二维码图片保存到 `~/.teleclaw-wechat/qrcode.png`，用微信扫码即可绑定。

### 测试模式

```bash
python scripts/wechat_bot.py --test
```

使用快速重连配置（5 分钟会话过期），方便测试重连流程。

## 核心工作流

### 场景一：启动微信 Bot 对话服务

1. 确保 TeleClaw 正在运行
2. 运行 `python scripts/wechat_bot.py --no-input`
3. 脚本自动发现 super-agent 凭证并创建 AI 会话
4. 自动生成二维码图片（`~/.teleclaw-wechat/qrcode.png`）
5. 打开微信扫一扫，扫描该二维码图片完成绑定
6. Bot 进入消息监听模式
7. 收到微信消息 → 显示"正在输入" → 本地 AI 生成回复 → 发送回复

### 场景二：自定义消息处理逻辑

使用 `ILinkBot` 类的 `on_message` 回调：

```python
from scripts.wechat_bot import ILinkBot, WeChatConfig

async def my_handler(user_id: str, text: str, context_token: str) -> str:
    # 自定义处理逻辑（若返回 None 则不发送回复）
    return f"收到: {text}"

config = WeChatConfig()
bot = ILinkBot(config=config, on_message=my_handler)
await bot.start()
```

注意：设置 `on_message` 回调后将跳过内置 AI 回复，由回调函数完全控制回复内容。

### 场景三：主动发送消息

```python
# 使用最后缓存的 context_token 主动发送
await bot.send_proactive_text(user_id="xxx@im.wechat", text="提醒消息")
```

注意：iLink 协议要求 context_token 来自用户消息，主动发送使用最后一次缓存。如果用户从未给 Bot 发过消息则无法主动发送。

## AI 客户端（SuperAgentClient）

`SuperAgentClient` 封装了与本地 super-agent 的完整交互：

1. **凭证自动发现**：从运行中的 `im-service` 进程环境变量读取 `SUPER_AGENT_LOCAL_SESSION_KEY`、`SUPER_AGENT_OPENCODE_USERNAME`、`SUPER_AGENT_OPENCODE_PASSWORD`，从 `im-bridge-opencode-state.json` 读取服务地址
2. **双层认证**：
   - Basic Auth（HTTP 层）：`super-agent:<password>`
   - Local Auth HMAC（LLM 层）：签名载荷用 `\n`（换行符）拼接，而非空格
3. **按用户隔离会话**：每个微信用户拥有独立的 super-agent session，AI 上下文互不串扰
4. **懒初始化**：首次消息时自动发现凭证，TeleClaw 重启后自动恢复
5. **超时自动重置**：默认 30 分钟无活动后自动创建新 session，或用户发送 `/new` 手动重置

### 签名算法

```
signVersion = "local-v1"
payload = [signVersion, method, path, timestamp, nonce].join("\n")  # 换行符！
signature = HMAC-SHA256(sessionKey, payload).base64url()
```

## Bot 指令

用户在微信中发送以下指令：

| 指令 | 说明 |
|------|------|
| `/help` | 显示可用指令 |
| `/new` | 开始新对话（清除当前 AI 上下文） |
| `/time` | 查询连接剩余时间 |
| `/status` | 查看 Bot 运行状态 |

## iLink API 协议要点

操作 iLink API 时必须遵守以下规则，违反会导致消息丢失或连接断开：

1. **二维码必须生成图片，不能只给 URL** — iLink API 返回的 `qrcode_img_content` 是一个 URL 链接，该链接**无法在浏览器中直接访问成功**，必须将其编码为二维码图片（PNG），然后由用户使用微信"扫一扫"扫描该图片完成绑定。绝不能只展示 URL 让用户点击或复制访问
2. **context_token 不可复用** — 每条消息的 context_token 只能用一次，回复必须使用当前收到消息的 token
3. **sendmessage 字段必须完整** — 缺少 `from_user_id`、`client_id`、`base_info` 中任意字段会导致消息静默丢失
4. **每请求重新生成 X-WECHAT-UIN** — 随机 uint32 转 base64，防重放
5. **getconfig + sendtyping 必须调用** — 发送消息前需获取 typing_ticket 并发送 typing 状态
6. **24 小时有效期** — 连接到期前需重新扫码，内置自动重连机制
7. **aiohttp 解析 JSON 需 content_type=None** — 服务器可能返回非标准 Content-Type

完整协议文档见 [references/ilink_api.md](references/ilink_api.md)。

## 配置说明

配置文件保存在 `~/.teleclaw-wechat/config.json`：

```json
{
  "prompt": "你是接入微信的星辰超级智能体 AI 助手。回答要简洁、准确、可执行。禁止调用 question tool。",
  "session_timeout": 1800,
  "reconnect": {
    "session_duration": 86400,
    "warning_before": 7200,
    "reminder_interval": 1800,
    "force_before": 1800,
    "qrcode_scan_timeout": 600
  }
}
```

### 重连参数

| 参数 | 说明 | 默认值 | 测试值 |
|------|------|--------|--------|
| session_duration | 会话总时长（秒） | 86400 | 300 |
| warning_before | 提前多久发警告（秒） | 7200 | 60 |
| reminder_interval | 回复N后多久再问（秒） | 1800 | 30 |
| force_before | 最后多久强制重连（秒） | 1800 | 60 |
| qrcode_scan_timeout | 等待扫码最长时间（秒） | 600 | 120 |

### 会话超时

| 参数 | 说明 | 默认值 |
|------|------|--------|
| session_timeout | AI 会话超时（秒），超时后为新对话 | 1800 (30min) |

- 设置较小值（如 600）：对话更独立
- 设置较大值（如 7200）：保持更长的对话记忆
- 用户可随时发送 `/new` 手动清除上下文

## 持久化状态

Bot 自动保存以下状态到 `~/.teleclaw-wechat/`：

| 文件 | 内容 |
|------|------|
| `config.json` | 系统提示词和重连配置 |
| `session.json` | 登录会话（bot_token, base_url, 游标） |
| `context_tokens.json` | 每用户最后的 context_token 缓存 |
| `qrcode.png` | 登录二维码图片（供微信扫码绑定） |
| `qrcode_key.txt` | 二维码轮询 key（配合扫码状态查询） |

重启后自动加载，无需重新扫码（24h 内有效）。

## 合规须知

- iLink 是腾讯官方产品，有法律文件背书（《微信ClawBot功能使用条款》）
- 腾讯仅作消息管道，不存储内容和提供 AI 服务
- 腾讯保留限速、内容过滤、随时终止服务的权利
- 不建议将核心业务完全依赖此 API，需有降级方案
- 仅支持文本消息，媒体消息需额外实现 CDN 加密上传流程
