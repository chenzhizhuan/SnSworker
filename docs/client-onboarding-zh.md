# SnSworker（SnSworker）客户端 上手手册

> 面向从零开始的使用者：本地首次编译打包 Windows 客户端 → 连接已部署的服务端 → 客户端操作指引。
> 你的服务端已部署在 `221.237.179.2`（公网），端口：主站 `13490`、管理后台 `13491`、API `13492`、协作 `13493`、实时 `13494`。
> 账号：`285625881@qq.com`（已超管），登录用**邮箱 + 收到的 6 位验证码**（邮件已配好，走 QQ）。

---

## 模块一：本地首次编译 & 打包 Windows 客户端（.exe）

### 0. 先明确两个关键事实（避免走弯路）

1. **架构是 x64，不是 x86。** 本项目 Electron 打包的 Windows 目标固定为 `nsis` + `x64`（见 `apps/tabtin-electron/package.json` 的 `build.win`）。"Windows x86" 在这里就是指 **64 位 Windows**，产物是 `x64` 安装程序，可直接在 64 位 Windows 上安装。没有 32 位（x86）选项，也不需要。
2. **必须在 Windows 机器上打包。** NSIS 安装包只能在 Windows 上生成（`build-win-nsis-quick.sh` 会检测 `uname`，非 Windows 直接退出）。你在 Windows 上，正好符合。

### 1. 环境准备（一次性）

**Node.js / pnpm**
```powershell
# 项目要求 node >= 18（.tool-versions 写的是 23.11.0，18+ 即可，建议用 20/22）
node --version
corepack enable
corepack prepare pnpm@9.15.0 --activate
pnpm --version
```

**Visual Studio Build Tools（必需，用于 node-pty 等原生模块）**
- 用 `winget` 装：`winget install Microsoft.VisualStudio.2022.BuildTools`
- 安装时**勾选「使用 C++ 的桌面开发」(Desktop development with C++)**，并确认装了 MSVC 编译器 + Windows 10/11 SDK。
- 这一步是 Windows 打包最常见的坑：缺 C++ 工作负载 → `node-pty` 编译失败。

**Python（必需，node-gyp 依赖）**
```powershell
winget install Python.Python.3.11
python --version
```

**Go（可选，仅当要内置 CLI 二进制 `tabtin-cli-go`）**
- 若 `packages/tabtin-cli-go/dist/tabtin.exe` 已存在则不用装 Go。
- 需要时：`go.mod` 要求 `go 1.26.1`，装 Go 后在 `packages/tabtin-cli-go` 里 `go build` 出 `dist/tabtin.exe`。没有它客户端大部分功能仍可用（CLI 是增强项）。

**Git Bash**：构建脚本是 bash，请在 **Git Bash**（随 Git for Windows 自带）里执行打包命令，不要用纯 PowerShell 跑 `.sh`。

**中国大陆网络加速（强烈建议）**：拉 electron / 依赖二进制走国内镜像，避免卡住。
```bash
export ELECTRON_MIRROR=https://cdn.npmmirror.com/binaries/electron/
export ELECTRON_BUILDER_BINARIES_MIRROR=https://cdn.npmmirror.com/binaries/electron-builder-binaries/
```

### 2. 拉代码 & 装依赖
```bash
cd <你的仓库目录>/SnSworker
git pull            # 确保是最新（origin/main_sns_v1）
pnpm install --frozen-lockfile
```
`postinstall` 会执行 `electron-rebuild -f --only node-pty`（需要上面的 VS C++ 工具链）。
装完体检：
```bash
node scripts/electron/install-dependencies.mjs --doctor
# 国内可加 --region cn
```

### 3. 指定服务端地址（关键）

Community 版客户端的**服务端地址是在打包时"烧"进安装包的**（不是安装后随便改）。四个变量都用你的服务器公网 IP：

```bash
# 在 Git Bash 里 export（或用 PowerShell 的 $env:）
export TABTIN_COMMUNITY_API_BASE_URL="http://221.237.179.2:13492/api"
export TABTIN_COMMUNITY_COLLAB_WS_BASE="ws://221.237.179.2:13493"
export TABTIN_COMMUNITY_CENTRIFUGO_WS_URL="ws://221.237.179.2:13494/connection/websocket"
export TABTIN_COMMUNITY_PUBLIC_WEB_BASE_URL="http://221.237.179.2:13490"
```

> 说明：API 走 `13492`（Django 直连），实时协作走 `13493`（collab-live），IM 推送走 `13494`（centrifugo），公开分享页走 `13490`（tabtin-web）。这些都是 UFW 放通的公网端口。

### 4. 打包

**方式 A：Community 完整包（推荐，最贴近你部署的服务端）**
```bash
bash apps/tabtin-electron/scripts/build-packaged-app.sh win community x64
```

**方式 B：Windows NSIS 快路径（local profile，适合高频调试，跳过 sourcemap）**
```bash
bash apps/tabtin-electron/scripts/build-win-nsis-quick.sh local x64
```

**首次构建很慢**（要下载 Chromium/Electron 二进制 + 编译原生模块 + 打包运行时），预计 10–40 分钟，取决于网络。

### 5. 产物位置

```
apps/tabtin-electron/dist-app/
  ├─ SnSworker Local Setup x.y.z.exe   ← 这就是你要的 .exe 安装程序（NSIS）
  └─ win-unpacked/snsworker-local.exe  ← 绿色版单文件（免安装，可直接双击）
```
把 `SnSworker Local Setup … .exe` 拷给别人即可安装。

### 6. 常见报错 & 解决

| 报错 | 原因 | 解决 |
| --- | --- | --- |
| `gyp ERR!` / `node-pty` 编译失败 | 缺 VS C++ 工具链或 Python | 装 VS Build Tools 并勾选「使用 C++ 的桌面开发」；`python --version` 确认可用；重开 Git Bash 再试 |
| 卡在 `downloading electron` | 国外 CDN 慢 | 设 `ELECTRON_MIRROR`（国内镜像），见上 |
| `prebuild-install` / 原生模块找不到 | electron-rebuild 没跑 | 手动 `pnpm --dir apps/tabtin-electron exec electron-rebuild -f --only node-pty` |
| 提示 `Unsupported arch` | 传了 x86/32 | 只能用 `x64`（本项目不支持 32 位） |
| `onnxruntime` / embedding 相关警告 | 本地小模型二进制没下载 | 可选：`pnpm --dir apps/tabtin-electron run runtimes:fetch`；不影响联网 AI（你走的是远端 vLLM） |
| 打包成功但打开报错 `MODULE_NOT_FOUND` | 运行时资源没 staging | 用**方式 A** 的 community 完整包；确认没手动改动 `dist-app` |
| 首次 `pnpm install` 很慢/失败 | 网络 | `pnpm install --frozen-lockfile --registry=https://registry.npmmirror.com` |

> 提示：你已经在用远端 vLLM（`172.16.15.134:13480`）做 AI，所以客户端**不需要**在本地跑任何模型，本地 embedding/onnx 都可以不装，能显著减小打包时间和体积。

---

## 模块二：客户端 ↔ 服务端 连通 & 登录

### 1. 网络连通性验证（打包前/后各查一次）

在你的 Windows 机器上（PowerShell 或浏览器）：
```powershell
# 浏览器直接开：
#   http://221.237.179.2:13490   → 主站应能打开
#   http://221.237.179.2:13492/health/ready → 返回 ok
```
```powershell
# 命令行测端口
Test-NetConnection 221.237.179.2 -Port 13492   # TcpTestSucceeded: True
Test-NetConnection 221.237.179.2 -Port 13490
Test-NetConnection 221.237.179.2 -Port 13493
Test-NetConnection 221.237.179.2 -Port 13494
```
若某端口不通：检查 (a) 你所在网络能否访问公网该端口；(b) 服务端 UFW 已放通 `13490:13494`（已确认），(c) 云安全组是否放通。

> 注意：vLLM 的 `172.16.15.134:13480` 是**内网地址**，只有服务器能访问，**你的客户端连不到它也不需要连**——客户端只连 `221.237.179.2` 的 4 个端口，AI 由服务端转发到 vLLM。

### 2. 登录态 & 鉴权注意事项

- **登录方式**：邮箱 `285625881@qq.com` + 验证码。**邮箱登录必须用 QQ 收到的真实 6 位码**（`888888` 固定码只对手机号有效，你走邮箱所以要收邮件）。
- **登录态保持**：客户端用 JWT（`access_token`）。勾选「记住我」可把有效期延长到 7 天。token 过期后客户端会自动 refresh；refresh 失败才会要求重新登录。
- **首次交互**：登录后进入主界面 → 新建一个对话/任务，发一句话（如"你好，用一句话介绍你自己"）→ 应能看到 Qwen3.8 的回复。这就是"首次业务交互"成功的标志。
- **权限**：你是超管（`permissions: ["*"]`），所有功能模块都可进。

### 3. 验证两者通信正常的清单

| 验证点 | 怎么做 | 期望 |
| --- | --- | --- |
| 主站可达 | 浏览器开 `:13490` | 页面加载 |
| 健康检查 | `:13492/health/ready` | `ok` / 200 |
| 登录 | 客户端输邮箱→收码→填码 | 进入主界面 |
| AI 对话 | 新建对话发消息 | 收到 Qwen 回复 |
| 实时协作 | 打开一个文档/表格，另开一个窗口 | 光标/编辑同步 |
| 文件上传 | 给 Agent 传一个本地文件 | 上传成功、可被读取 |

---

## 模块三：客户端操作手册（新手引导）

> 客户端是"人 + Agent 协作工作台"。核心心智：**你下达任务 → Agent（用 Qwen 等大模型）执行 → 产出物（文档/表格/演示文稿/文件）你和 Agent 都能读写**。下面按模块讲。

### A. 界面布局

- **左侧导航**：会话/任务列表、工作空间（Space）、文档、表格、演示文稿等入口。
- **中间主区**：当前对话或正在编辑的协作对象（文档/表格）。
- **右侧/底部**：Agent 执行状态、工具调用日志、产出物面板。
- **顶部**：当前工作空间、搜索、模型选择器（这里能看到 `Qwen3.8-27B-AWQ-INT4`）。
- **设置（Settings）**：账号、语言、模型偏好、Agent 规则、执行环境。

### B. 核心功能操作流程

**1. 发起一次 Agent 任务**
1. 新建对话 → 用自然语言描述任务（例："帮我调研 X 并整理成一页文档"）。
2. Agent 开始执行，右侧实时显示步骤/工具调用。
3. 执行完得到产出物（文档/文件），可直接查看、编辑、导出。
4. 不满意可追问（"改成表格""再补充数据来源"），上下文会延续。

**2. 文档协作（Doc）**
- 新建文档 → Agent 或你都能编辑（实时协同，Y.js）。
- 支持 Markdown / 富文本、表格、代码块、Mermaid、公式。
- 导出：HTML / PDF / Markdown（文档菜单里）。

**3. 多维表格（Table / Smartsheet）**
- 新建表格 → 定义列（文本/数字/日期/链接/附件等）→ 加记录。
- Agent 可以帮你**采集数据填入表格**（浏览器采集）、做转换、生成图表。
- 视图：表格 / 看板 / 甘特等切换。

**4. 演示文稿（Slide）**
- 新建项目 → 逐页编辑或让 Agent 生成 → 元素可拖拽 → 导出 PPT。

**5. 文件与本地能力**
- 把本地文件拖进对话 → Agent 可读（PDF/Office/代码等）。
- 终端能力（node-pty）：Agent 可在授权下执行命令。
- 浏览器采集：Agent 打开网页抓数据进表格/文档。

**6. 交接任务**
- 把已完成任务"交接"给下一位成员/Agent：会带上对话上下文 + 引用且有权共享的文档/文件。接手人在自己的工作空间继续。

### C. 参数配置指引

| 配置项 | 在哪 | 说明 |
| --- | --- | --- |
| 默认模型 | 顶部模型选择器 / 设置 | 已默认 `Qwen3.8-27B-AWQ-INT4`（服务端已配好，无需填 key） |
| 语言 | 设置 → 语言 | 中/英 |
| Agent 规则/Prompt | 设置 → Agent | 可给不同 Agent 角色设固定规则、技能（Skill）、记忆 |
| 记住我 | 登录页 | 延长登录有效期到 7 天 |
| 执行环境 | 设置 → 执行环境 | 授权 Agent 用本地终端/文件 |

> AI 能力说明：服务端已接入 vLLM（Qwen3.8-27B），**客户端不用自己配模型 key**。若以后要加别的模型，在 AdminDash（`:13491` → AI 管理）里加 Provider/Model 即可。

### D. 典型场景示例

- **场景 1：快速调研** — "调研 2026 年 XX 行业主要玩家并输出一页对比文档" → Agent 用搜索+浏览器采集 → 产出文档。
- **场景 2：数据处理** — 拖入一个 Excel → "清洗数据、去掉空行、按地区分组汇总，生成表格" → Agent 处理 → 表格 + 图表。
- **场景 3：写报告** — 给几份资料 → "汇总成一份 3 页的演示文稿" → Slide。
- **场景 4：团队协作** — 你做完一部分，"交接给张三，带上这份文档" → 张三继续。

### E. 常见问题排查

| 现象 | 排查 |
| --- | --- |
| 客户端打不开/闪退 | 先装对版本（x64）；确认 Windows 是 64 位；看 `win-unpacked` 里的启动日志；检查是否被杀软拦截（首装加信任） |
| 连不上服务器 | `Test-NetConnection 221.237.179.2 -Port 13492`；确认打包时 4 个地址填的是 `221.237.179.2` 对应端口 |
| 登录收不到验证码 | 邮箱登录走 QQ 真实码：检查 QQ 收件箱/垃圾邮件；确认服务器邮件配置正常（已配好） |
| AI 无回复/很慢 | 首次调用 vLLM 冷启动可能 ~1 分钟，之后快；持续无响应到 AdminDash「AI 管理」看 Provider 健康/探测 |
| 实时协作不同步 | 检查 `13493`(collab) 和 `13494`(centrifugo) 端口连通；确认服务端这些容器 healthy |
| 打包失败 | 回到模块一的"常见报错"表；多数是 VS C++ 工具链 / 网络镜像 |
| 忘记服务端地址 | 重新打包并 `export` 4 个地址变量（地址是编译期固定的） |

---

## 附：一页速查

```
# 打包（Windows / Git Bash）
export ELECTRON_MIRROR=https://cdn.npmmirror.com/binaries/electron/
export TABTIN_COMMUNITY_API_BASE_URL="http://221.237.179.2:13492/api"
export TABTIN_COMMUNITY_COLLAB_WS_BASE="ws://221.237.179.2:13493"
export TABTIN_COMMUNITY_CENTRIFUGO_WS_URL="ws://221.237.179.2:13494/connection/websocket"
export TABTIN_COMMUNITY_PUBLIC_WEB_BASE_URL="http://221.237.179.2:13490"
bash apps/tabtin-electron/scripts/build-packaged-app.sh win community x64
# 产物：apps/tabtin-electron/dist-app/SnSworker Local Setup x.y.z.exe

# 登录：285625881@qq.com + QQ 收到的 6 位验证码
```
