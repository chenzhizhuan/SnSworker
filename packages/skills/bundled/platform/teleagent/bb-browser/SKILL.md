---
name: bb-browser
description: 电信员工每天登录多个内外网系统查数据，但这些系统基本没有API，AI想帮忙却进不去。本技能直接把已登录的浏览器接力给AI用，通过Cookie调取数据，网站看到的就是合法用户在查。预置36个平台命令，内网系统10分钟可CLI化。
name_cn: 个人浏览器操作助手
description_cn: 直接把已登录的浏览器接力给AI用，通过Cookie调取数据，网站看到的就是合法用户在查。预置36个平台一键调用，内网系统10分钟可CLI化。适合运维、客服、报表岗跨系统查数。
allowed-tools: Bash(bb-browser:*)
---

# 个人浏览器操作助手 (bb-browser)

## 解决什么痛点

电信员工每天要登录一堆系统——CRM、计费、网管、工单、报表平台。这些系统大多没有 API，AI 想帮你查个用户账单、拉张报表、看条告警，它进不去——要么你手动截图发它，要么它去写爬虫还被反爬挡住。AI 明明就坐在你旁边，却够不着你已经打开的窗口。

## 怎么解决

不重新登录、不写爬虫、不模拟身份——直接把"你已经登录好的浏览器"接力给 AI 用。AI 通过浏览器里的 Cookie 和页面模块调取数据，网站看到的就是你这个合法用户在查。预置 36 个常用平台命令（搜索/社交媒体/财经/招聘/视频等），也支持内网任意网站 10 分钟内 CLI 化。

一句话：**让 AI 借你的眼睛和工牌去拿数据**。

## 适用人群

- 运维岗、客服岗、数据报表岗：每天要在多个内部/外部系统间反复查询取数
- 市场/规划岗：需要跨多个平台调研行业舆情、技术方案

## 与"网页测试自动化"的区别

| 维度 | 个人浏览器操作助手 (bb-browser) | 网页测试自动化 (Playwright MCP) |
|------|---------------------------|---------------------------|
| 登录态 | 直接用你已登录的浏览器 | 默认开干净浏览器，无登录态 |
| 数据范围 | 能拿私域数据（你的工单、账单） | 默认只能拿公开页面 |
| 反爬风控 | 网站看到的是你本人，不会被拦 | 自动化特征明显，易被识别 |
| 适用 | 查数据（需要你身份） | 做操作（无人值守流程） |

**判断公式**：任务需要"你这个人"的身份 → 用本技能；任务不需要身份、只是无人值守网页流程 → 用网页测试自动化。

## 快速开始

```bash
bb-browser open <url>        # 打开页面（新 tab）
bb-browser snapshot -i       # 获取可交互元素
bb-browser click @5          # 点击元素
bb-browser fill @3 "text"    # 填写输入框
bb-browser close             # 完成后关闭 tab
```

## Site 系统 — 把任何网站变成命令行 API

预置 36+ 平台，103 命令：

```bash
bb-browser site zhihu/hot                     # 知乎热榜
bb-browser site twitter/search "AI agent"     # 搜索推文
bb-browser site eastmoney/stock "茅台"         # 股票查询
bb-browser site weibo/hot                     # 微博热搜
bb-browser site arxiv/search "transformer"    # 论文搜索
```

adapter 自动处理 tab 管理和登录检测。详见 [references/site-system.md](references/site-system.md)。

## 核心工作流

1. `open` 打开页面
2. `snapshot -i` 查看可操作元素（返回 @ref）
3. 用 `@ref` 执行操作（click, fill, etc.）
4. 页面变化后重新 `snapshot -i`
5. 任务完成后 `close` 关闭 tab

## 典型电信场景

### 跨系统查政企客户信息

已登录 CRM → AI 直接借会话查客户实时账单、工单历史，1 秒拿到结果，网站以为是你点的。

### 把内网报表系统 CLI 化

跟 AI 说"帮我把 XX 系统 CLI 化"，它读 guide、逆向 API、写 adapter、测试，10 分钟出可用命令。此后一条命令取数。

## 命令速查

### 导航
```bash
bb-browser open <url>                # 打开 URL（新 tab）
bb-browser open <url> --tab current  # 在当前 tab 打开
bb-browser back / forward / refresh / close
```

### 快照
```bash
bb-browser snapshot -i          # 只显示可交互元素（推荐）
bb-browser snapshot -c -d 5     # 压缩空节点 + 限制深度
```

### 元素交互
```bash
bb-browser click @5 / hover @5 / fill @3 "text" / type @3 "text"
bb-browser check @7 / uncheck @7 / select @4 "option"
bb-browser press Enter / scroll down 500
```

### 获取信息
```bash
bb-browser get text @5 / get url / get title
bb-browser eval "document.body.innerText.substring(0, 5000)"
```

### Tab 管理
```bash
bb-browser tab                  # 列出所有 tab
bb-browser tab new [url]        # 新建 tab
bb-browser tab 2                # 切换到第 2 个 tab
bb-browser tab close            # 关闭当前 tab
```

### 网络与调试
```bash
bb-browser network requests "api" --with-body   # 过滤 + 完整请求/响应体
bb-browser network route "*analytics*" --abort   # 拦截并阻止请求
bb-browser console / errors                       # 查看 console/JS 错误
bb-browser trace start / stop                    # 录制用户操作
```

## fetch — 带登录态的 curl

```bash
bb-browser fetch <url>                                    # GET，自动带 Cookie
bb-browser fetch <url> --method POST --body '{"k":"v"}'   # POST
bb-browser fetch /api/me.json                             # 相对路径（用当前 tab origin）
```

## MCP 集成

```json
{
  "mcpServers": {
    "bb-browser": {
      "command": "npx",
      "args": ["-y", "bb-browser", "--mcp"]
    }
  }
}
```

## 全局选项

```bash
--json               # JSON 格式输出
--tab <tabId>        # 指定标签页 ID
--mcp                # 启动 MCP server
```

## 深入文档

| 文档 | 说明 |
|------|------|
| [references/site-system.md](references/site-system.md) | Site 系统完整指南：35 平台列表、命令用法 |
| [references/adapter-development.md](references/adapter-development.md) | Adapter 开发：API 逆向、三层复杂度 |
| [references/fetch-and-network.md](references/fetch-and-network.md) | Fetch 与 Network 高级功能 |
| [references/snapshot-refs.md](references/snapshot-refs.md) | Ref 生命周期、最佳实践 |
