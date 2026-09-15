---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '24a094d5-14a9-4ca3-bcf9-b53f0759194d'
  PropagateID: '24a094d5-14a9-4ca3-bcf9-b53f0759194d'
  ReservedCode1: '3ff47aba-1434-44c0-b40a-ec457eedcc3e'
  ReservedCode2: '3ff47aba-1434-44c0-b40a-ec457eedcc3e'
---

# 联网搜索增强指南（Web Search Enhancement）

> 移植自 agent-reach（互联网能力路由器）与 last30days（近30天社区研究）的可执行规则。
> 本文件解决 SuperAgent 的三个空白：**平台级路由缺失、工具链命令缺失、社区真实声音采集缺失**。
> 与 [execution-guide.md §Scatter-Gather搜索模式](execution-guide.md) 正交——本文件管"去哪搜/用什么工具搜"，该文件管"怎么组织搜索流程"。两者100%并行强制执行。

## 零、内置搜索工具（⛔首选，零配置开箱即用）

**SuperAgent 自带 `scripts/search_tools.py`，仅依赖 Python 标准库（urllib+json），无需安装任何第三方工具即可使用。** 这是所有搜索型 Agent 的**首选通道**；外部 CLI 工具（gh/bili/opencli 等）为**可选增强**，装了更好、没装用内置脚本。

### 0.1 内置通道一览

| 命令 | 平台 | 零配置 | 说明 |
|------|------|--------|------|
| `python scripts/search_tools.py github "<query>" -n 10` | GitHub 仓库搜索 | ✅ 是 | 按 stars 排序，免认证（限 10 次/分钟） |
| `python scripts/search_tools.py bilibili "<query>" -n 10` | B站视频搜索 | ✅ 是 | 返回标题/播放量/UP主 |
| `python scripts/search_tools.py reddit "<query>" -n 10` | Reddit 帖子搜索 | ✅ 是 | 返回标题/分数/评论数/子版 |
| `python scripts/search_tools.py hackernews "<query>" -n 10` | Hacker News 搜索 | ✅ 是 | 通过 Algolia API |
| `python scripts/search_tools.py hackernews-trending -n 10` | HN 热门帖子 | ✅ 是 | Front Page 热门 |
| `python scripts/search_tools.py v2ex -n 20` | V2EX 热门帖子 | ✅ 是 | 实时热门话题 |
| `python scripts/search_tools.py read "<url>"` | 网页阅读（Jina Reader） | ✅ 是 | 将任意网页转为可读文本 |
| `python scripts/search_tools.py doctor` | 全通道体检 | ✅ 是 | 检测所有通道连通性 |

### 0.2 通道优先级规则

1. **内置脚本优先**：搜索型 Agent 必须先尝试内置脚本通道
2. **外部 CLI 增强**：若本机已装 gh/opencli/bili 等工具，可作为补充使用（例如 gh 支持更细粒度搜索）
3. **降级链**：内置脚本返回 `unreachable` → 换通用搜索（online_search）→ 标注状态，禁止伪装成功
4. **体检前置**：搜索前可运行 `python scripts/search_tools.py doctor` 快速确认哪些通道当前可用

### 0.3 输出格式

所有搜索结果输出为 JSON 数组，每条结果包含：
- `platform`：平台名
- `title`：标题
- `url`：链接
- `desc`：描述（截断 200 字符）
- `status`：搜索状态（ok/no-results/rate-limited/unreachable）
- 平台特有字段（stars/play/score/points 等）

搜索失败时输出 `{"platform": "...", "status": "unreachable", "items": [], "message": "..."}`，**禁止将 unreachable 当作 no-results**。

## 一、多平台路由表（P1，源自 agent-reach）

[Agent-搜索型] 在执行搜索前，必须先按任务意图选择平台通道，禁止无差别"泛搜索"。平台选择后按对应命令组执行（见下方工具链手册）。**首选内置脚本（§零），外部 CLI 为可选增强（§二）。**

| 用户意图 | 首选平台 | 补充平台 | 说明 |
|---------|---------|---------|------|
| 网页/通用搜索 | 通用搜索（online_search / Exa） | Jina Reader | 时效性任务必须含当前年份关键词 |
| 中文社交讨论（口碑/种草/测评） | 小红书、B站 | 微博 | 需登录态时按doctor确认后端 |
| 英文技术讨论/开发者社区 | Reddit、V2EX、Hacker News | GitHub | 社区声音专项 |
| 代码/仓库/开源项目 | GitHub | 通用搜索 | gh CLI 优先 |
| 视频内容/播客 | YouTube、B站、小宇宙 | - | yt-dlp 拉字幕 |
| 招聘/职位/LinkedIn | LinkedIn | 招聘聚合 | 需登录态 |
| 股票/行情/财经 | 雪球 | 财经媒体 | 雪球API |
| 实时热点 | V2EX热门、微博、B站热门 | 全网热点 | 零配置 |
| 全网调研 | Exa搜索 + 中英社媒并行 | 多平台组合 | 见下方组合模式 |

**组合模式（全网调研类任务强制）**：Exa/通用搜索（事实底座）+ Twitter/Reddit（英文社区讨论）+ 小红书/B站（中文社区讨论）三线并行，再进 Verify 交叉验证。禁止单平台得出结论。

## 二、外部 CLI 工具链命令（P2，源自 agent-reach，可选增强）

> ⛔ **以下命令为可选增强通道**。新用户无需安装任何工具，内置脚本（§零）已覆盖 GitHub/B站/Reddit/HN/V2EX/Jina 等平台。仅当需要更细粒度搜索或内置脚本降级时，才使用以下外部 CLI。

以下命令为搜索型 Agent 的标准动作库。按平台路由选择，优先使用本机已配置的后端；命令不可用时按 `agent-reach doctor` 确认，禁止猜测替代命令。

### 2.1 通用网页搜索

```bash
# Exa AI 搜索（英文/技术/代码资料）
mcporter call exa.web_search_exa query="<query>" numResults=5

# 通用网页阅读（Jina Reader，将网页转为可读Markdown）
curl -s "https://r.jina.ai/<URL>"
```

### 2.2 GitHub 搜索

```bash
gh search repos "<query>" --sort stars --limit 10
```

### 2.3 V2EX 热门（零配置）

```bash
curl -s "https://www.v2ex.com/api/topics/hot.json" -H "User-Agent: agent-reach/1.0"
```

### 2.4 B站搜索（零配置）

```bash
bili search "<query>" --type video -n 5
```

### 2.5 YouTube 字幕提取

```bash
yt-dlp --write-sub --write-auto-sub --skip-download -o "%(id)s" "<URL>"
```

### 2.6 Twitter / Reddit / 小红书（需登录态，先 doctor）

```bash
# 先确认后端可用（agent-reach）
agent-reach doctor --json

# Twitter 搜索（twitter-cli 首选）
twitter search "<query>" -n 10

# Reddit（OpenCLI 桌面 / rdt 存量服务器）
opencli reddit search "<query>" -f yaml

# 小红书（桌面首选 OpenCLI，复用浏览器登录态）
opencli xiaohongshu search "<query>" -f yaml
```

### 2.7 雪球股票行情

```bash
# 雪球搜索/热门内容（agent-reach finance 通道）
opencli xueqiu search "<query>" -f yaml
```

### 2.8 通用网页/文章/RSS

```bash
# Jina Reader 阅读指定文章
curl -s "https://r.jina.ai/<article-url>"
```

## 三、搜索状态显式化（P4，源自 last30days source_status）

搜索结果必须显式标注状态，禁止把"未搜到"等同于"不存在"。**每个搜索 Agent 返回时，状态字段为必填**：

| 状态 | 含义 | 处理方式 |
|------|------|---------|
| `no-results` | 该源正常返回但零匹配 | 可下结论"该源无相关讨论" |
| `partial` | 部分覆盖（命中少/不完整） | 标注"部分覆盖"，补搜其他平台 |
| `rate-limited` | 被限流 | 降级换平台或重试 |
| `auth-failed` | 登录态失效 | 提示配置/换后端，禁止硬跑 |
| `unreachable` | 平台不可达 | 换通道，禁止当作"无内容" |
| `timeout` | 超时未返回 | 标"超时跳过"，其余路继续汇聚 |
| `skipped-unconfigured` | 未配置未运行 | 标注未配置原因，换可用平台 |

**规则**：只有 `no-results` 状态可以支撑"该平台无相关内容"的结论；其余状态一律标注为"部分覆盖"并补搜其他平台。禁止在未确认来源可用性的情况下断言"全网没有相关内容"。

## 四、doctor 体检前置 + 登录态规则（P5，源自 agent-reach）

### 4.1 多后端体检

搜索涉及多后端/登录态平台（小红书/Reddit/B站/Twitter/Facebook/Instagram）时，**先体检确认可用后端**。体检分两层：

1. **内置脚本体检（零配置）**：`python scripts/search_tools.py doctor` —— 检测 GitHub/B站/Reddit/HN/V2EX/Jina 六个内置通道的连通性
2. **外部 CLI 体检（需安装 agent-reach）**：`agent-reach doctor --json` —— 确认 opencli/gh/bili 等外部后端可用性

### 4.2 登录态边界规则

- 小红书：不替用户登录、不读浏览器 Cookie。用用户已有且明确的 Chrome 会话（OpenCLI）；无会话时不自动登录
- Twitter：Cookie 仅供 doctor 检查配置，直接调用前必须显式提供 TWITTER_AUTH_TOKEN/TWITTER_CT0（子进程环境变量，禁止在日志或回显暴露值）
- 所有登录态平台：无登录态即标注 `auth-failed`，换后端或换平台，禁止假装已登录执行

### 4.3 平台失败重试链

平台命令失败 → 按以下顺序重试（不可跳过）：
1. 换后端（同平台多后端切换，如 OpenCLI→rdt-cli）
2. 换平台（同意图其他平台，如小红书→微博）
3. 换通道（网页搜索 → API → 平台官方接口）
4. 全部失败 → 标注"平台不可用"并保留残差链路，禁止伪装成功

## 五、社区真实声音专项模式（P3，源自 last30days）

当任务需要了解"大家最近怎么讨论 X"、"用户口碑/评价"、"社区热议"时，启动社区声音专项，与常规搜索并列强制。

### 5.1 触发条件（任一命中即启动）

- 任务目标含"讨论/口碑/评价/热议/吐槽/种草/避雷/推荐"
- 任务涉及消费决策（选型/购车/买房/软件选型）
- 任务目标是人物/产品/项目/事件的社会反响
- 用户明确要求"看看大家怎么说/社区怎么评价"

### 5.2 采集规则

1. **真实评论优先**：社区评论（含点赞/投票数）是一手信号，权重 ≥ 权威新闻稿。引用评论必须标注：`{作者, 平台, 投票数, 原句}`
2. **近30天窗口**：默认只采近30天内发布的讨论；任务另有时效要求时按任务口径，但必须显式标注时间窗口
3. **覆盖至少2个平台**：社区声音结论必须有≥2个独立平台来源（不可全部来自同一平台/同一作者）
4. **高赞优先**：优先引用高赞/高参与度评论（≥100赞或≥10条回复的评论为强信号），低参与度评论仅作辅助
5. **禁止编造评论**：禁止根据标题推测评论内容；无评论数据时标注"该平台无评论返回"并补搜其他平台

### 5.3 输出格式

社区声音采集结果必须在 Swarm 汇聚时以独立区块输出：

```text
【社区声音】
平台：Reddit r/Nvidia | 时间窗：近30天
- 高赞评论1："{原句}" | 作者 | 投票数 | 来源
- 高赞评论2："{原句}" | 作者 | 投票数 | 来源
共识信号：{社区共识/分歧}
置信度：{基于投票数与平台数}
```

### 5.4 来源分级适配

社区评论默认归入 T3/T4（自媒体/论坛），但**高赞一手评论**（≥1000赞且多平台可复现）可升级为 T2 辅助证据。核心结论仍须 T1/T2 支撑，社区声音用于"发现信号、验证分歧、补充口碑维度"，不单独构成核心结论。

## 六、平台路由与现有搜索框架的衔接

| 现有框架 | 增强后行为 |
|---------|-----------|
| Scatter 首轮并行 | 按平台路由表分发：A1=通用搜索、A2=社区平台、A3=财经/技术平台 |
| Gather 定向补搜 | 命中搜索状态"partial"的维度优先补搜其他平台 |
| 深度溯源 | 引文链追溯时可用 Jina Reader 读取原文 URL |
| 时效性强制 | 通用搜索关键词强制含当前年份，社区搜索强制近30天窗口 |
| 搜索验证门禁 | 新增"平台多样性"门禁：核心结论须≥2 平台类型（见上方规则） |

## 七、适用范围与边界

- 本指南仅约束[Agent-搜索型]的搜索动作，不改变 Swarm 阶段的 Agent 生成/交叉验证/共振收敛判定
- 所有命令必须使用本机可用后端，命令缺失时按"doctor 体检"处理，禁止编造命令
- 敏感平台（Twitter/小红书）登录态遵循 §4.2 边界（doctor 体检前置的登录态边界规则），不越权访问用户未授权的会话