---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '50aa5e82-08da-44cd-b935-ec6cc56e3d10'
  PropagateID: '50aa5e82-08da-44cd-b935-ec6cc56e3d10'
  ReservedCode1: '196630fe-b826-4fc5-a77e-0cc7d9828b91'
  ReservedCode2: '196630fe-b826-4fc5-a77e-0cc7d9828b91'
---

# lark-shared

> **Version**: `1.0.0`
本技能指导你如何通过lark-cli操作飞书资源, 以及有哪些注意事项。

## 配置初始化

首次使用需运行 `lark-cli config init --new` 完成应用配置。该命令默认会阻塞等待用户在浏览器完成操作，在 Agent 场景中必须使用非阻塞方案。

### 非阻塞方案（Agent 必须）

**第一步：后台运行，提取配置链接**

```bash
lark-cli config init --new > .temp/lark-config.log 2>&1 &
```

等待 2-3 秒后读取日志，提取链接：

```bash
sleep 3 && grep "https://open.feishu.cn" .temp/lark-config.log
```

将提取到的链接（格式如 `https://open.feishu.cn/page/cli?user_code=XXXX-XXXX&...`）原样发送给用户，由用户在浏览器中打开并完成应用配置。**不要修改链接**（包括 URL 编码/解码、添加空格或标点、重新拼接 query）。

同时生成二维码并展示给用户：`lark-cli auth qrcode <URL> --output .temp/lark-config-qrcode.png`。**链接和二维码必须同时提供**，二维码生成的 PNG 文件必须作为附件发给用户，方便手机扫码。

**第二步：等待用户确认，读取结果**

用户确认配置完成后，读取日志确认：

```bash
cat .temp/lark-config.log
```

看到 `OK: 应用配置成功! App ID: cli_xxxx` 即为成功。

> `config init` 没有原生的 `--no-wait` 参数，因此采用后台运行 + 日志轮询。官方帮助文档也确认了这一做法：Run it in the background and retrieve the verification URL from its output.

## 认证

### 身份类型

两种身份类型，通过 `--as` 切换：

| 身份 | 标识 | 获取方式 | 适用场景 |
|------|------|---------|---------|
| user 用户身份 | `--as user` | `lark-cli auth login` 等 | 访问用户自己的资源（日历、云空间/云盘/云存储等） |
| bot 应用身份 | `--as bot` | 自动，只需 appId + appSecret | 应用级操作,访问bot自己的资源 |

### 切换登录账户

用户要求切换到另一个飞书账号时，**必须**询问用户：

> "目标账户与当前账户是否属于同一个飞书组织（租户）？同一公司的同事通常属于同一组织。"

- **同一组织**：直接执行 `lark-cli auth login --domain all`，生成二维码并用 `report_final_files` 将 PNG 文件作为附件返回给用户，等待用户扫码授权
- **不同组织**：先执行 `lark-cli config init --new` 创建新组织的应用，再执行 `lark-cli auth login --domain all`，生成二维码并用 `report_final_files` 将 PNG 文件作为附件返回给用户，等待用户扫码授权

### 身份选择原则

输出的 `[identity: bot/user]` 代表当前身份。bot 与 user 表现差异很大，需确认身份符合目标需求：

- **Bot 看不到用户资源**：无法访问用户的日历、云空间（云盘/云存储）文档、邮箱等个人资源。例如 `--as bot` 查日程返回 bot 自己的（空）日历
- **Bot 无法代表用户操作**：发消息以应用名义发送，创建文档归属 bot
- **Bot 权限**：只需在飞书开发者后台开通 scope，无需 `auth login`
- **User 权限**：后台开通 scope + 用户通过 `auth login` 授权，两层都要满足

### 权限不足处理

遇到权限相关错误时，**根据当前身份类型采取不同解决方案**。

错误响应中包含关键信息：
- `permission_violations`：列出缺失的 scope (N选1)
- `console_url`：飞书开发者后台的权限配置链接
- `hint`：建议的修复命令

#### Bot 身份（`--as bot`）

将错误中的 `console_url` 原样提供给用户，引导去后台开通 scope。**禁止**对 bot 执行 `auth login`。

#### User 身份（`--as user`）

```bash
lark-cli auth login --domain <domain>           # 按业务域授权
lark-cli auth login --scope "<missing_scope>"   # 按具体 scope 授权（推荐,符合最小权限原则）
```

**规则**：auth login 必须指定范围（`--domain` 或 `--scope`）。多次 login 的 scope 会累积（增量授权）。

#### Agent 代理发起认证（推荐）

当你作为 AI agent 需要帮用户完成认证时，优先使用 split-flow，避免在同一轮对话中阻塞等待用户授权：

```bash
# 发起授权（立即返回 device_code 和 verification_url）
lark-cli auth login --scope "calendar:calendar:readonly" --no-wait --json
```

拿到 `verification_url` 后，将它原样作为本轮最终消息发给用户，并结束本轮/交还控制权。不要在同一轮中展示 URL 后立刻执行 `--device-code` 阻塞轮询；在不透传中间输出的 agent harness 里，这会导致用户永远看不到 URL。

用户回复已完成授权后，再在后续步骤执行：

```bash
lark-cli auth login --device-code <device_code>
```

**Split-Flow 完整步骤**：

**第一步：发起授权（当前轮）**

1. 执行 `lark-cli auth login --scope "xxx" --no-wait --json`（必须加 `--no-wait --json`）
2. 从 JSON 输出中提取 `verification_url` 和 `device_code`
3. 生成二维码：`lark-cli auth qrcode <verification_url> --output .temp/lark-auth-qrcode.png`
4. 将 URL 和二维码**同时**展示给用户，二维码生成的 PNG 文件必须作为附件发给用户，方便手机扫码
5. **结束本轮对话前，必须明确告知用户**："请完成授权后，回来告诉我已授权完成，我会帮你完成后续步骤"

**第二步：完成授权（后续轮）**

1. 等待用户回复"已完成授权"
2. **由你（AI agent）亲自执行**：`lark-cli auth login --device-code <device_code>`
3. 此命令会轮询授权状态并完成登录
4. 如果返回授权成功，流程结束

**关键规则**：

- **你必须亲自执行 `--device-code` 命令**，不要指示用户自行执行
- **不要在同一轮中展示 URL 后立刻执行 `--device-code`**，这会导致用户看不到 URL
- **禁止缓存 `verification_url` 或 `device_code`**：每次需要授权时，必须重新执行 `lark-cli auth login --no-wait --json` 生成新的链接。不要将授权链接和 device code 存入上下文供后续复用
- **二维码必须作为附件返回**：生成二维码 PNG 后，必须调用 `report_final_files` 将文件返回给用户，仅生成文件不够，用户看不到就无法扫码

## 更新检查

lark-cli 命令执行后，如果检测到新版本，JSON 输出中会包含 `_notice.update` 字段（含 `message`、`command` 等）。

**当你在输出中看到 `_notice.update` 时，完成用户当前请求后，主动提议帮用户更新**：

1. 告知用户当前版本和最新版本号
2. 提议执行更新（同时更新 CLI 和 Skills）：
   ```bash
   lark-cli update
   ```
3. 更新完成后提醒用户：**退出并重新打开 AI Agent** 以加载最新 Skills

**重要**：始终使用 `lark-cli update` 更新，它会同时更新 CLI 和 AI Skills。

**规则**：不要静默忽略更新提示。即使当前任务与更新无关，也应在完成用户请求后补充告知。

## 安全规则

- **禁止输出密钥**（appSecret、accessToken）到终端明文。
- **写入/删除操作前必须确认用户意图**。
- 用 `--dry-run` 预览危险请求。
- **文件路径只接受相对路径**：`--file`、`--output`、`--output-dir`、`@file` 等路径参数只接受 cwd 下的相对路径，传绝对路径会报 `unsafe file path`。数据输入（`@file`、大 JSON）优先用 stdin 传入，避免路径和转义问题。

## 高风险操作的审批协议（exit 10）

lark-cli 对高风险写操作（`risk: "high-risk-write"`）有强制确认门禁。当你不带 `--yes` 调用这类命令时，CLI 会退出码 `10`、并在 stderr 返回如下结构化 envelope：

```json
{
  "ok": false,
  "error": {
    "type": "confirmation_required",
    "message": "drive +delete requires confirmation",
    "hint": "add --yes to confirm",
    "risk": {
      "level": "high-risk-write",
      "action": "drive +delete"
    }
  }
}
```

**遇到这种情况，不要当普通错误放弃。** 按以下流程处理：

1. **识别**：看到子进程 exit code = `10` 且 stderr JSON 里 `error.type == "confirmation_required"`
2. **向用户确认**：把 `error.risk.action` 和关键参数展示给用户，明确告知"这是高风险操作"，等待用户显式同意
3. **用户同意** → 在你**原始 argv 的末尾追加 `--yes`** 后重试
4. **用户拒绝** → 终止流程，不要擅自改写参数或跳过门禁

**绝对不允许**：
- 看到 exit 10 就默认加 `--yes` 静默重试（这等于禁用门禁）
- 把 `confirmation_required` 当网络错误/权限错误处理
- 在用户没明确同意的前提下追加 `--yes` 重试
- 用 `sh -c` 等 shell 方式拼接命令重试——用 `exec.Command(argv...)` 参数数组形式，避免 shell 解析把用户参数当作语法

提前预判：想先让用户 review 危险操作的具体请求，调用时加 `--dry-run`——它不触发门禁，会打印完整请求详情（URL / body / params），你可以把这个预览给用户看过再去真正执行。

### 如何识别一条命令是高风险

- shortcut：`lark-cli <service> +<cmd> --help` 顶部会显示 `Risk: high-risk-write`
- service 命令：`lark-cli schema <service>.<resource>.<method> --format json` 的返回值里 `"risk": "high-risk-write"`

> AI生成