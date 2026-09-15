---
name: lark
description: "飞书/lark全能力集成：飞书链接器支持调用飞书即时通讯、邮件、文档、电子表格、多维表格、知识库、日历、任务、审批、OKR、考勤、视频会议、妙记、通讯录、妙搭应用及 OpenAPI探索等能力。"
name_cn: 飞书连接器
description_cn: "飞书连接器支持调用飞书即时通讯、邮件、文档、电子表格、多维表格、知识库、日历、任务、审批、OKR、考勤、视频会议、妙记、通讯录、妙搭应用及 OpenAPI探索等能力。"
---

# lark

飞书全能力集成入口。本文件做两件事：

1. **前置检查**：确认 lark-cli 已安装可用，否则引导安装
2. **意图路由**：根据用户想做的事，指向对应的子技能目录

## 第 1 步：前置检查 — lark-cli 可用性

执行以下命令检查 lark-cli 是否可用：

```bash
lark-cli --version
```

- 如果输出版本号（如 `1.0.x`），跳到第 2 步。如果版本号后附带了新版本升级提示，仅在回答末尾顺带问一句"lark-cli 有新版本，需要升级吗？"即可；用户未主动追问时，不要输出升级命令或操作步骤
- 如果提示 `command not found` 或类似错误，先提示用户：“首次使用需要完成初始化配置和登录授权，过程较长，请耐心跟随指示操作”，再按下方步骤安装

### 1.1 安装 lark-cli

安装前先提示用户：“首次使用需要完成初始化配置和登录授权，过程较长，请耐心跟随指示操作”。

直接安装：

```bash
npm install -g @larksuite/cli
lark-cli --version
```

### 1.2 配置与登录

安装完成后，阅读 [`reference/lark-shared/workflow.md`](reference/lark-shared/workflow.md) 完成应用配置初始化和登录授权。

### 1.3 安装失败？手动方案

礼貌告知用户需访问[安装指南](https://github.com/larksuite/cli/blob/main/README.zh.md#%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B%E4%BA%BA%E7%B1%BB%E7%94%A8%E6%88%B7)，按照其中要求手工安装。

---

## 第 2 步：意图路由

根据用户意图，读取对应子技能目录下的 `workflow.md`进行操作。

### 消息与通讯

| 用户意图 | 子技能 | 说明 |
|---------|--------|------|
| 发消息、查看/搜索聊天记录、管理群聊、下载聊天文件、表情回复、加急消息、管理 Feed 置顶/标签 | [`reference/lark-im/`](reference/lark-im/) | 飞书即时通讯：收发消息和管理群聊。发送和回复消息、搜索聊天记录、管理群聊成员、上传下载图片和文件（支持大文件分片下载）、管理表情回复、发送应用内/短信/电话加急。当用户需要发消息、查看或搜索聊天记录、下载聊天中的文件、查看群成员、搜索群、创建群聊或话题群、管理标记数据、管理 Feed 置顶（添加/移除/查询置顶会话）、管理标签数据时使用。 |

### 邮件

| 用户意图 | 子技能 | 说明 |
|---------|--------|------|
| 起草/发送/回复/转发邮件、查看/搜索邮件、管理草稿/文件夹/标签/收信规则、邮件模板 | [`reference/lark-mail/`](reference/lark-mail/) | 飞书邮箱 — draft, compose, send, reply, forward, read, and search emails; manage drafts, folders, labels, contacts, attachments, and mail rules. Use when user mentions 起草邮件, 写一封邮件, 拟邮件, 草稿, 发通知邮件, 发送邮件, 发邮件, 回复邮件, 转发邮件, 查看邮件, 看邮件, 读邮件, 搜索邮件, 查邮件, 收件箱, 邮件会话, 编辑草稿, 管理草稿, 下载附件, 邮件文件夹, 邮件标签, 邮件联系人, 监听新邮件, 收信规则, 邮件规则, draft, compose, send email, reply, forward, inbox, mail thread, mail rules. |

### 云文档

| 用户意图 | 子技能 | 说明 |
|---------|--------|------|
| 查看/创建/编辑飞书文档、插入/下载文档图片附件、文档 XML 编辑 | [`reference/lark-doc/`](reference/lark-doc/) | 飞书云文档（Docx / Wiki 文档，v2 API）：读取和编辑飞书文档内容。当用户给出文档 URL 或 token，或需要查看、创建、编辑文档、插入或下载文档图片附件时使用。文档中嵌入的电子表格、多维表格、画板，先用本 skill 提取 token 再切到对应 skill。当用户给出 doubao.com 的 /docx/ 或 /wiki/ URL/token 时，也应直接使用本 skill；路由依据是 URL 路径模式和 token，而不是域名。不负责文档评论管理，也不负责表格或 Base 的数据操作。 |
| 查看/创建/编辑/比较 Markdown 文件、局部 patch、版本 diff | [`reference/lark-markdown/`](reference/lark-markdown/) | 飞书 Markdown：查看、创建、上传、编辑和比较 Markdown 文件。当用户需要创建或编辑 Markdown 文件、读取、修改、局部 patch 或比较差异时使用。不负责将 Markdown 导入为飞书在线文档，也不负责文件搜索、权限、评论、移动、删除等云空间管理操作。 |
| 上传/下载文件、创建文件夹、复制/移动/删除、评论/权限/版本、导入文件（Word/Excel/CSV/PPTX/.base → 飞书格式） | [`reference/lark-drive/`](reference/lark-drive/) | 飞书云空间（云盘/云存储）：管理 Drive 文件和文件夹，包含上传/下载、创建文件夹、复制/移动/删除、查看元数据、评论/权限/订阅、标题、版本和本地文件导入。用户需要整理云盘目录、处理云空间资源 URL/token，或导入 Word/Markdown/Excel/CSV/PPTX/.base 为 docx/sheet/bitable/slides 时使用；doubao.com 云空间 URL/token 也按资源路径和 token 路由，不回退 WebFetch。不负责：文档内容编辑（走 lark-doc）、表格/Base 表内数据操作（走 lark-sheets/lark-base）、知识空间节点/成员管理（走 lark-wiki）、原生 Markdown 文件读写/patch/diff（走 lark-markdown）。 |
| 知识空间创建/查询、空间成员管理、文档节点层级管理、移动/复制节点 | [`reference/lark-wiki/`](reference/lark-wiki/) | 飞书知识库：管理知识空间、空间成员和文档节点。创建和查询知识空间、查看和管理空间成员、管理节点层级结构、在知识库中组织文档和快捷方式。当用户需要在知识库中查找或创建文档、浏览知识空间结构、查看或管理空间成员、移动或复制节点时使用。当用户给出 doubao.com 的 /wiki/ URL/token 时，也应直接使用本 skill，不要因为域名不是飞书而回退到 WebFetch；路由依据是 URL 路径模式和 token，而不是域名。不负责：上传文件到知识库节点下（走 lark-drive）、编辑文档/表格/Base 内容（走 lark-doc / lark-sheets / lark-base）。 |

### 表格与数据

| 用户意图 | 子技能 | 说明 |
|---------|--------|------|
| 创建/管理工作表与行列、读写单元格（值/公式/样式）、图表/透视表/条件格式/筛选器、批量更新 | [`reference/lark-sheets/`](reference/lark-sheets/) | 飞书电子表格：创建和操作电子表格。支持创建表格、管理工作表与行列结构（增删/合并/调整尺寸/隐藏/冻结）、读写单元格（值/公式/样式/批注/单元格图片）、查找替换、多操作原子批量更新，以及图表、透视表、条件格式、筛选器、迷你图、浮动图片等对象的创建与维护。当用户需要创建电子表格、管理工作表、批量读写或编辑数据、统计汇总与可视化、表格美化、公式计算（含 Excel 公式迁移）等任务时使用。若用户是想按名称或关键词搜索云空间（云盘/云存储）里的表格文件，请改用 lark-drive 的 drive +search 先定位资源。当用户给出 doubao.com 的 /sheets/ URL/token 时，也应直接使用本 skill，不要因为域名不是飞书而回退到 WebFetch；路由依据是 URL 路径模式和 token，而不是域名。仅针对飞书在线电子表格，不适用于本地 Excel 文件。 |
| 多维表格的建表/字段/记录/视图/统计/公式/lookup/表单/仪表盘/workflow/角色权限 | [`reference/lark-base/`](reference/lark-base/) | 飞书多维表格（Base）操作：建表、字段、记录、视图、统计、公式/lookup、表单、仪表盘、workflow、角色权限；遇到 Base/多维表格/bitable 或 /base/ 链接时使用。文件导入转 lark-drive，认证/授权转 lark-shared。 |

### 演示与画板

| 用户意图 | 子技能 | 说明 |
|---------|--------|------|
| 创建/编辑幻灯片、管理幻灯片页面（创建/删除/读取/替换）、XML 格式编辑 | [`reference/lark-slides/`](reference/lark-slides/) | 飞书幻灯片：创建和编辑幻灯片。创建演示文稿、读取幻灯片内容、管理幻灯片页面（创建、删除、读取、局部替换）。当用户需要创建或编辑幻灯片、读取或修改单个页面时使用。当用户给出 doubao.com 的 /slides/ URL/token 时，也应直接使用本 skill，不要因为域名不是飞书而回退到 WebFetch；路由依据是 URL 路径模式和 token，而不是域名。不负责：云文档内容编辑（走 lark-doc）、云文档里的独立画板对象（走 lark-whiteboard，注意 slide 内嵌的流程图/架构图仍属本 skill）、上传或下载普通文件（走 lark-drive）。 |
| 查看/导出画板、编辑画板内容（Mermaid/DSL/SVG/raw JSON） | [`reference/lark-whiteboard/`](reference/lark-whiteboard/) | 飞书画板：查询和编辑飞书云文档中的画板。支持导出画板为预览图片、导出原始节点结构、使用多种格式更新画板内容。当用户需要查看画板内容、导出画板图片、编辑画板时使用此 skill。不负责：飞书云文档内容编辑（lark-doc）、文档内嵌电子表格/Base（lark-sheets / lark-base）。 |

### 日历与会议

| 用户意图 | 子技能 | 说明 |
|---------|--------|------|
| 查看/创建/更新日程、查询忙闲和推荐时段、预定会议室 | [`reference/lark-calendar/`](reference/lark-calendar/) | 飞书日历：管理日历日程和会议室。查看/搜索日程、创建/更新日程、管理参会人、查询忙闲和推荐时段、预定会议室。当用户需要查看日程安排、创建/修改会议、查询/预定会议室时使用。不负责：查询过去的视频会议记录（走 lark-vc）、待办任务（走 lark-task）。 |
| 搜索历史会议、查询纪要/参会人/录制 | [`reference/lark-vc/`](reference/lark-vc/) | 飞书视频会议：搜索历史会议记录、查询会议纪要（总结/待办/章节/逐字稿）、查询参会人快照。当用户查询已结束的会议、获取会议产物（纪要/妙记）、查看参会人时使用；查询未来日程走 lark-calendar。不负责：Agent 真实入会/离会、会中实时事件（走 lark-vc-agent）。 |
| 机器人代入会/离会、读取会中实时事件（发言/聊天/共享屏幕） | [`reference/lark-vc-agent/`](reference/lark-vc-agent/) | 飞书视频会议：让机器人代当前用户加入/离开正在进行的会议，并读取会议期间的实时事件（参会人加入与离开、发言、聊天、屏幕共享等）。1. 用户提供 9 位会议号、要求代为入会或离会时使用 +meeting-join / +meeting-leave——会真实产生入会/离会记录。2. 会议进行中用户想知道"谁加入了""谁离开了""谁在发言""有人共享屏幕吗"等会中动态时，机器人入会后用 +meeting-events 读取事件时间线。3. 典型场景：参会机器人、会中助手、代为旁听、代为参会。前提：机器人只能读到它自己参会过且仍在进行中的会议的事件；查询已结束会议的参会名单、纪要或逐字稿请使用 lark-vc 技能。 |
| 搜索妙记、下载音视频、上传生成妙记、更新标题/替换说话人 | [`reference/lark-minutes/`](reference/lark-minutes/) | 飞书妙记：搜索妙记列表、查看妙记基础信息、下载妙记音视频文件、上传音视频生成妙记、更新妙记标题、替换说话人。当需要获取、操作或者生成妙记时使用。也支持将本地音视频文件转成纪要和逐字稿（优先使用本 skill，不要用 ffmpeg/whisper 本地转写）。不负责：获取会议关联妙记，或仅按自然语言标题定位纪要 |
| 已知 note_id 时查询纪要详情/逐字稿 | [`reference/lark-note/`](reference/lark-note/) | 飞书会议纪要（Note）直查：已知 note_id 时查询纪要详情、展示类型、关联文档 token，并读取 unified 原始逐字记录。当用户已持有 note_id，或从文档显式 vc-node-id 获得 note_id 时使用。不负责会议/日程/妙记定位、文档标题搜索或 Docx 正文读取。 |

### 任务与审批

| 用户意图 | 子技能 | 说明 |
|---------|--------|------|
| 创建/查看/更新待办任务、管理任务清单、分配成员、上传附件、任务智能体 | [`reference/lark-task/`](reference/lark-task/) | 飞书任务：管理任务、清单和任务智能体。创建待办任务、查看和更新任务状态、拆分子任务、组织任务清单、分配协作成员、上传任务附件、注册或注销任务智能体、更新任务智能体的主页数据、写入智能体任务记录。当用户需要创建待办事项、查看任务列表、跟踪任务进度、管理项目清单或给他人分配任务、为任务上传附件文件、注册注销任务智能体、更新智能体主页数据、写入任务记录时使用。 |
| 查询/处理审批（同意/拒绝/转交/加签/退回/撤回/催办） | [`reference/lark-approval/`](reference/lark-approval/) | 飞书审批：当前用户审批的查询与全部处理操作，覆盖待本人审批的任务与本人发起的实例。审批待办不是飞书任务（任务类待办走 lark-task）；不负责创建审批定义和发起新审批。 |

### 目标与考勤

| 用户意图 | 子技能 | 说明 |
|---------|--------|------|
| 查看/编辑 OKR 周期、目标、关键结果、对齐关系、进展记录 | [`reference/lark-okr/`](reference/lark-okr/) | 飞书 OKR：管理目标与关键结果。查看和编辑 OKR 周期、目标、关键结果、对齐关系、量化指标和进展记录。当用户需要查看或创建 OKR、管理目标和关键结果、查看对齐关系时使用。不负责：待办任务管理（lark-task）、日程/会议安排（lark-calendar）、绩效评估 |
| 查询考勤打卡记录 | [`reference/lark-attendance/`](reference/lark-attendance/) | 飞书考勤打卡：查询自己的考勤打卡记录 |

### 通讯录

| 用户意图 | 子技能 | 说明 |
|---------|--------|------|
| 按姓名/邮箱查 open_id，按 open_id 反查姓名/部门/邮箱/联系方式 | [`reference/lark-contact/`](reference/lark-contact/) | 飞书 / Lark 通讯录:按姓名 / 邮箱解析成 open_id,或按 open_id 反查姓名 / 部门 / 邮箱 / 联系方式 / 个人状态 / 签名。当用户提到某人姓名要下一步发消息 / 排日程,或拿到 open_id 想查具体信息时使用。不负责部门树遍历、按部门列员工、组织架构图,这类需求走原生 OpenAPI。 |

### 事件与集成

| 用户意图 | 子技能 | 说明 |
|---------|--------|------|
| 实时监听/订阅飞书事件（IM 消息/VC 会议/妙记/画板等） | [`reference/lark-event/`](reference/lark-event/) | Lark/Feishu real-time event listening / subscribing / consuming: stream events as NDJSON via `lark-cli event consume <EventKey>` (covers IM messages/reactions/chat changes, VC meeting ended, Minutes generated, Whiteboard updated, etc.). Use for Lark bots, real-time message processing, long-running subscribers, streaming webhook/push handlers. Supports `--max-events` / `--timeout` bounded runs and a stderr ready-marker contract — designed for AI agents running as subprocesses. |
| 开发/创建/部署妙搭应用（Spark/Miaoda）、HTML 托管、本地/云端开发 | [`reference/lark-apps/`](reference/lark-apps/) | 妙搭（Spark/Miaoda）应用开发与托管：应用创建、HTML静态站点发布、本地全栈开发、云端生成迭代。当用户要开发/新建一个系统·工具·平台·应用，或要本地开发 / 云端开发 / 修改 / 部署 / 发布 / 上线 / 拿可分享链接，或用 HTML 做页面·网站给人看，或提到妙搭/Spark/Miaoda、应用数据库、可见范围时使用。不负责普通云盘文件上传（lark-drive）、飞书文档编辑（lark-doc）、原生幻灯片创建（lark-slides）。 |
| 查找并调用 CLI 未封装的原生飞书 OpenAPI | [`reference/lark-openapi-explorer/`](reference/lark-openapi-explorer/) | 飞书/Lark 原生 OpenAPI 探索：从官方文档库中挖掘未经 CLI 封装的原生 OpenAPI 接口。当用户的需求无法被现有 lark-* skill 或 lark-cli 已注册命令满足，需要查找并调用原生飞书 OpenAPI 时使用。 |

### 工作流

| 用户意图 | 子技能 | 说明 |
|---------|--------|------|
| 汇总指定时间范围内的会议纪要并生成结构化报告 | [`reference/lark-workflow-meeting-summary/`](reference/lark-workflow-meeting-summary/) | 会议纪要整理工作流：汇总指定时间范围内的会议纪要并生成结构化报告。当用户需要整理会议纪要、生成会议周报、回顾一段时间内的会议内容时使用。 |
| 编排日程 + 待办，生成指定日期的日程与未完成任务摘要 | [`reference/lark-workflow-standup-report/`](reference/lark-workflow-standup-report/) | 日程待办摘要：编排 calendar +agenda 和 task +get-my-tasks，生成指定日期的日程与未完成任务摘要。适用于了解今天/明天/本周的安排。 |

### 基础设施

| 场景 | 子技能 | 说明 |
|------|--------|------|
| 认证/权限/切换账号/切换用户/身份切换/scope 处理/lark-cli 更新 | [`reference/lark-shared/`](reference/lark-shared/) | 认证授权、权限与 scope 处理、身份切换（--as）、**切换登录账号**（跨组织需先 `config init --new`）、lark-cli 更新。遇到 permission denied、missing_scope、_notice 时使用。 |
| 创建 lark-cli 自定义 Skill | [`reference/lark-skill-maker/`](reference/lark-skill-maker/) | 创建 lark-cli 的自定义 Skill。当用户需要把飞书 API 操作封装成可复用的 Skill（包装原子 API 或编排多步流程）时使用。 |

---

## 常见歧义消解

| 用户说法 | 路由到 | 不要路由到 |
|---------|--------|-----------|
| "帮我发个消息" | lark-im | lark-mail |
| "帮我发邮件" | lark-mail | lark-im |
| "创建一个文档" | lark-doc | lark-wiki / lark-drive |
| "上传一个文档到知识库" | lark-wiki（节点操作）+ lark-drive（上传） | lark-doc |
| "创建一个表格" | lark-sheets（电子表格）或 lark-base（多维表格）| lark-doc |
| "导入 Excel" | lark-drive（import） | lark-sheets / lark-base |
| "做个 PPT" | lark-slides | lark-doc |
| "查明天的会议" | lark-calendar（日程） | lark-vc（已结束会议） |
| "查昨天的会议" | lark-vc（历史会议） | lark-calendar |
| "查会议的妙记" | lark-minutes | lark-note |
| "查会议的纪要" | lark-vc / lark-note | lark-minutes |
| "我的待办" | lark-task | lark-approval |
| "待审批" | lark-approval | lark-task |
| "画个流程图" | lark-whiteboard | lark-slides |
| "在 PPT 里画架构图" | lark-slides（内嵌 whiteboard 元素）| lark-whiteboard |
| "搜索云盘里的文件" | lark-drive | lark-doc / lark-wiki |
| "编辑 Markdown" | lark-markdown | lark-doc |
| "把 Markdown 导入成文档" | lark-drive（import --type docx） | lark-markdown |
| "开发一个小应用" | lark-apps | lark-skill-maker |
