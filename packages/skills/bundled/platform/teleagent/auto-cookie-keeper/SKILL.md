---
name: auto-cookie-keeper
name_cn: 全天候OA综调等系统保持登录神器
description_cn: >
  7×24小时网页登录态保活 + 20项企业办公自动化，一次配置终身免登录。
  保活：自动采集、自动续期、自动保存Cookie，综调系统、OA门户、BI报表、工单平台等任何Web系统永不掉线。
  扩展：资料下载、数据库更新、变动提醒、增量资料、网络故障巡查、自动接单等20项操作，
  Agent引导式配置定时任务，全程只需回答几个问题。
  双模式：内网版（本地守护，纯保活） / 公网版（Agent在线，保活+20项扩展全自动化）。
  沉淀14个实战踩坑点，覆盖SSL证书、HttpOnly Cookie、跨线程崩溃、僵尸进程、HTTP连接泄漏等所有暗坑。
description: >
  7×24小时Cookie保活 + 20项企业办公自动化，一次配置终身免登录。
  保活：自动采集、自动续期、自动保存Cookie，综调系统、OA门户、BI报表、工单平台等任何Web系统永不掉线。
  扩展：资料下载、数据库更新、变动提醒、增量资料、网络故障巡查、自动接单等20项操作，
  Agent引导式配置定时任务，全程只需回答几个问题。
  双模式：内网版（本地守护，纯保活） / 公网版（Agent在线，保活+20项扩展全自动化）。
  沉淀14个实战踩坑点，覆盖SSL证书、HttpOnly Cookie、跨线程崩溃、僵尸进程、HTTP连接泄漏等所有暗坑。
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '51307272-4118-4d84-b397-9f81f91caca7'
  PropagateID: '51307272-4118-4d84-b397-9f81f91caca7'
  ReservedCode1: '077024e6-db7f-4f34-a921-f362065b178b'
  ReservedCode2: '077024e6-db7f-4f34-a921-f362065b178b'
---

## 这能帮你干什么

**一句话：你登录一次，剩下的一切交给它。**

你有没有遇到过这些场景——

- 每天早上打开 OA 门户看公文，Cookie 过期了，得重新登录
- 写了个定时脚本拉报表，跑了两天全挂，一查又是会话失效
- 想让 Agent 定时去系统抓数据，但它压根没法保持登录态
- 手动登录浏览器复制粘贴 Cookie，一天搞好几回，烦不烦

**这个技能就是来终结这一切的。**

### 两种模式，按需选择

| | 内网版（本地守护） | 公网版（智能托管） |
|---|---|---|
| 核心能力 | Cookie 保活 + 自动导出 | Cookie 保活 + 20 项扩展操作 |
| 保活方式 | 本地桌面小程序，自动刷新页面 | Agent 定时打开浏览器提取最新 Cookie |
| 是否需要 Agent 在线 | 不需要 | 需要 |
| 智能程度 | 纯自动化守护，无智能引导 | Agent 引导式配置，逐步生成定时任务 |
| 适用场景 | 内网环境、Agent 无法常驻 | 公网可达、Agent 可保持在线 |
| 扩展操作 | 无 | 资料下载、变动提醒、自动接单等 20 项 |
| 复杂度 | 低（一键启动） | 中（需配置定时任务，但全程引导） |

**不知道选哪个？简单记：你的电脑能被 Agent 远程操作就选公网版，不能就选内网版。两个都能保活，公网版多了脑子。**

### 适用系统

任何需要登录的 Web 系统都能用——

- 各省市**综调系统**（综合调度平台）
- 各级**OA 办公门户**（公文流转、审批系统）
- **BI 报表平台**（Redash、自研报表系统）
- **监控告警平台**（AIOps、运维管理平台）
- **工单管理系统**（故障工单、服务请求）
- **考勤 / 资产 / 合同管理系统**
- 任何使用 SSO 单点登录或账号密码认证的 **Web 系统**

## 前置条件

- Python 3.10+ 已安装
- Playwright 已安装（`pip install playwright` + `playwright install chromium`）
- 目标系统可通过 Chrome 浏览器访问
- 用户知道目标系统的 URL 和登录方式
- **公网版额外要求**：Agent 可保持在线，用户已安装 TeleAgent Desktop

> 用户可能不具备电脑基础，在开始前需提醒安装难度，如果用户执意要用，需要更详细的逐步引导。

---

## 内网版流程（本地守护程序）

> 内网版生成一个本地桌面小程序，启动后自动保活。不需要 Agent 在线。

### 第一步：信息收集

向用户收集以下信息：

| 信息项 | 说明 | 示例 |
|--------|------|------|
| 系统名称 | 用于 GUI 显示和日志标识 | "综调系统"、"OA 门户" |
| 保活 URL | 系统首页 URL（非数据嵌入页，越轻量越好） | `http://内网地址/系统首页` |
| Cookie 域名 | Cookie 所属域名（用于过滤） | `系统域名或IP` |
| 登录方式 | SSO 单点登录 / 账号密码 / 其他 | "SSO，跳转到统一身份认证平台" |
| 预期 Cookie 名称 | 登录成功后应包含的关键 Cookie（可选） | 不确定可留空，第三步实测提取 |

> 多系统保活：用户有多个系统需要保活时，收集每个系统的信息，在 SITES 字典中添加多个条目。

### 第二步：实测提取 Cookie 信息

使用 Playwright 浏览器工具完成以下操作：

1. **导航到目标 URL**，处理 SSL 证书问题（见陷阱 #4）
2. **用户手动完成 SSO 登录**（可能有图形验证码，Agent 无法代劳）
3. **登录成功后，提取完整 Cookie 列表**：

```javascript
async (page) => {
    const context = page.context();
    const cookies = await context.cookies();
    return JSON.stringify(cookies.map(c => ({
        name: c.name,
        value: c.value.substring(0, 20) + "...",
        domain: c.domain,
        path: c.path,
        httpOnly: c.httpOnly
    })), null, 2);
}
```

4. **记录登录页关键词**：登录跳转时 URL 中出现的关键词（如 `login`、`sso`、`cas` 等）
5. **记录有效 Cookie 名称**：登录成功后目标域名下的 Cookie 名称列表

> 将提取到的信息填入第一步的信息表格，作为 SITES 配置的依据。

### 第三步：生成保活程序

根据收集到的信息，生成以下文件（全部放在用户指定目录）：

```
目标目录/
├── cookie_keeper_gui.py     ← GUI 守护进程（保活 + 自动导出 Cookie）
├── {系统名}_cookies.json     ← Cookie JSON（守护进程自动更新）
├── {系统名}_cookies.txt      ← Cookie TXT（守护进程自动更新）
└── .chrome_profile/          ← Playwright 独立 Chrome 配置目录
```

> 代码模板见 `references/code-patterns.md`，生成时需根据用户系统配置定制 SITES 字典。

### 第四步：验证与交付

生成代码后，引导用户按 `references/verification.md` 中的验证清单逐项检查：

1. 启动程序，Chrome 打开目标页面
2. 手动完成 SSO 登录
3. 确认登录状态正确检测（绿灯）
4. 确认 Cookie 自动导出到 JSON + TXT 文件
5. 确认保活循环正常运行（刷新次数递增）
6. 确认 Cookie 失效后能检测并提示重新登录

---

## 公网版流程（Agent 智能托管）

> 公网版不创建本地小程序。Agent 直接用浏览器提取 Cookie，然后创建定时任务定期刷新 Cookie，再引导配置 20 项扩展操作。

### 第一步：信息收集

向用户收集以下信息：

| 信息项 | 说明 | 示例 |
|--------|------|------|
| 系统名称 | 用于 Cookie 文件命名和日志标识 | "综调系统"、"OA 门户" |
| 系统首页 URL | 系统登录页或首页地址 | `http://系统地址/首页` |
| Cookie 域名 | Cookie 所属域名（用于过滤提取） | `系统域名或IP` |
| Cookie 保存目录 | 用户指定的本地文件夹，Cookie 文件存在这里 | `D:\cookies` |
| 登录方式 | SSO / 账号密码 / 其他 | "SSO 跳转到统一认证" |
| 预期 Cookie 名称 | 登录成功后应包含的关键 Cookie（可选） | 不确定可留空，第二步实测提取 |

**向用户解释每个参数的含义，用大白话，不要假设用户懂技术术语。**

示例话术：
> - 系统名称：就是你想保活的那个系统叫什么，比如「综调系统」「OA门户」，随便起个名字，方便后面区分。
> - 系统首页 URL：就是你平时打开这个系统时在浏览器地址栏输入的那个网址。
> - Cookie 域名：就是你那个系统网址里的域名部分，比如 `http://10.20.30.40/portal` 里的 `10.20.30.40` 就是域名。
> - Cookie 保存目录：你想让 Cookie 文件存在你电脑的哪个文件夹里。比如你可以在 D 盘建个文件夹叫 `cookies`，路径就是 `D:\cookies`。**这个目录要记住，后面定时任务和扩展操作都要用到。**

### 第二步：Agent 提取 Cookie

这一步 Agent 用浏览器打开目标系统，用户手动登录一次，Agent 提取登录后的 Cookie 并保存到用户指定目录。

**详细步骤（面向 0 基础用户）：**

1. **告诉用户即将打开浏览器**：
   > 我现在会用 Chrome 浏览器打开你刚才说的系统地址。你的屏幕上会弹出一个浏览器窗口，你需要在里面完成一次登录操作。登录成功后我会自动提取 Cookie，你什么都不用管。

2. **Agent 用 Playwright 打开目标 URL**：
   - 使用 `playwright_browser_navigate` 导航到系统首页
   - 如果出现 SSL 证书警告页面，Agent 用 `playwright_browser_navigate` 重新导航（Playwright 默认忽略证书错误）

3. **引导用户完成登录**：
   > 浏览器已经打开了。现在请在弹出的浏览器窗口里完成登录：
   > - 如果是 SSO 登录：点击登录按钮，跳到统一认证平台，输入账号密码
   > - 如果有图形验证码：需要你手动输入验证码（Agent 没法帮你认验证码）
   > - 登录成功后，页面会跳回系统首页，你告诉我一声「登录好了」就行

4. **用户确认登录后，Agent 提取完整 Cookie**：

```javascript
async (page) => {
    const context = page.context();
    const cookies = await context.cookies();
    // 只保留目标域名的 Cookie
    const target = cookies.filter(c => c.domain.includes('目标域名'));
    return JSON.stringify(cookies.map(c => ({
        name: c.name,
        value: c.value,
        domain: c.domain,
        path: c.path,
        httpOnly: c.httpOnly
    })), null, 2);
}
```

5. **记录登录页关键词和有效 Cookie 名称**：
   - 登录跳转时 URL 中出现的关键词（如 `login`、`sso`、`cas`）
   - 登录成功后目标域名下的 Cookie 名称列表
   - 这些信息用于后续定时任务判断 Cookie 是否有效

6. **Agent 将 Cookie 保存到用户指定目录**：
   - JSON 格式：`{用户指定目录}/{系统名}_cookies.json`
   - TXT 格式：`{用户指定目录}/{系统名}_cookies.txt`
   - 告诉用户：Cookie 已经保存好了，在 `D:\cookies` 文件夹里你会看到两个文件。

### 第三步：创建 Cookie 刷新定时任务

这一步 Agent 创建一个定时任务，每隔一段时间自动打开浏览器、访问目标系统页面刷新 Cookie、重新保存到文件。

**向用户解释**：
> Cookie 就像一张通行证，有过期时间。如果长时间不刷新，它就失效了，你的系统又会要求重新登录。
> 我现在帮你创建一个定时任务，每隔 2 小时自动用浏览器访问一次你的系统页面，刷新 Cookie，然后更新保存到你的文件夹里。
> 这样你的 Cookie 就一直是有效的，永远不会掉线。
> **这个定时任务需要 Agent 保持在线才能运行。如果你关掉 Agent，定时任务会暂停，重新打开 Agent 后自动恢复。**

**Agent 操作**：

1. **生成 Cookie 刷新脚本**，保存到 `.temp/` 目录：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Cookie 刷新定时任务脚本 — 自动打开浏览器访问目标系统，刷新并保存 Cookie"""

import json, os, sys, time
from datetime import datetime

# ========== 配置区（Agent 根据用户信息填充）==========
SYSTEM_NAME = "系统名称"
KEEPALIVE_URL = "http://系统首页URL"
COOKIE_DOMAIN = "系统域名或IP"
COOKIE_DIR = r"用户指定目录"
COOKIE_JSON = os.path.join(COOKIE_DIR, f"{SYSTEM_NAME}_cookies.json")
COOKIE_TXT = os.path.join(COOKIE_DIR, f"{SYSTEM_NAME}_cookies.txt")
LOGIN_PAGE_KEYWORDS = ["login", "sso", "cas"]  # Agent 实测提取
VALID_COOKIE_NAMES = []  # Agent 实测提取，如不确定则留空
# ===================================================

def refresh_cookies():
    """用 Playwright 打开页面刷新 Cookie 并保存"""
    from playwright.sync_api import sync_playwright

    profile_dir = os.path.join(COOKIE_DIR, ".chrome_profile")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--disable-extensions",
                "--ignore-certificate-errors",
                "--allow-running-insecure-content",
            ],
            ignore_default_args=["--enable-automation"],
            no_viewport=True,
        )

        page = context.pages[0] if context.pages else context.new_page()

        # 预加载上次 Cookie
        if os.path.exists(COOKIE_JSON):
            with open(COOKIE_JSON, "r", encoding="utf-8") as f:
                old_cookies = json.load(f)
            pw_cookies = [{
                "name": c["name"],
                "value": c["value"],
                "domain": c["domain"],
                "path": c.get("path", "/"),
            } for c in old_cookies]
            context.add_cookies(pw_cookies)

        # 访问保活页面
        page.goto(KEEPALIVE_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        # 检查是否在登录页
        url = page.url or ""
        is_login = any(kw in url for kw in LOGIN_PAGE_KEYWORDS)
        if is_login or "login" in url.lower():
            print(f"[WARN] Cookie 已失效，需要重新登录")
            # 保存当前状态
            context.close()
            return False

        # 提取并保存 Cookie
        all_cookies = context.cookies()
        target_cookies = [c for c in all_cookies if COOKIE_DOMAIN in c.get("domain", "")]

        simple = [{
            "name": c["name"],
            "value": c["value"],
            "domain": c["domain"],
            "path": c.get("path", "/"),
        } for c in target_cookies]

        with open(COOKIE_JSON, "w", encoding="utf-8") as f:
            json.dump(simple, f, ensure_ascii=False, indent=2)

        with open(COOKIE_TXT, "w", encoding="utf-8") as f:
            for c in simple:
                f.write(f"{c['name']}={c['value']}\n")

        print(f"[OK] {datetime.now()} Cookie 刷新成功: {len(simple)} 个")
        context.close()
        return True

if __name__ == "__main__":
    if not os.path.exists(COOKIE_DIR):
        os.makedirs(COOKIE_DIR)
    try:
        success = refresh_cookies()
        if not success:
            print("[ERROR] Cookie 已失效，请重新运行技能提取 Cookie")
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
```

2. **通过 `scheduler` 技能创建定时任务**：
   - 任务名称：`Cookie刷新_{系统名称}`
   - 执行频率：每 2 小时（或用户指定）
   - 执行内容：运行上面的刷新脚本
   - 告诉用户：定时任务已创建，每 2 小时自动刷新一次 Cookie

3. **首次验证**：
   - 手动运行一次刷新脚本，确认输出 `[OK] Cookie 刷新成功`
   - 确认 Cookie 文件更新时间已变更为当前时间
   - 告诉用户：验证通过，Cookie 刷新任务已就绪

### 第四步：配置扩展操作（20 项可选）

> 到这一步，保活已经就绪。接下来是公网版的核心价值——20 项扩展操作。

1. 向用户展示 20 项扩展操作清单（见下文）
2. 用户选择需要的一项或多项
3. 针对每项操作，收集必要的配置参数（API 地址、数据格式、推送方式等）
4. 生成对应的定时任务脚本
5. 通过 `scheduler` 技能创建定时任务
6. 验证定时任务正常运行

**一次配置，终身运行。你只需要做一件事：首次让 Agent 提取一次 Cookie。**

---

## 20 项扩展操作框架

> 以下 20 项操作均为框架模板，每项仅提供简短提示词和配置要点。实际实现需根据用户的具体系统 API 和业务需求定制。适用于公网版模式。

---

### 1. 资料下载

**提示词**：定时从目标系统批量下载报表文件、附件、文档，保存到本地指定目录。

**配置要点**：下载 API 地址、文件存储路径、文件命名规则、下载频率、增量/全量。

---

### 2. 数据库更新

**提示词**：定时拉取系统数据，写入本地数据库（MySQL/SQLite/Excel），保持数据同步。

**配置要点**：数据源 API、目标数据库连接串、字段映射、写入模式（覆盖/追加/更新）、同步频率。

---

### 3. 变动提醒

**提示词**：监控系统关键数据变化（状态变更、数值波动、新增记录），检测到变动时推送通知。

**配置要点**：监控 API、变动判断逻辑（阈值/差值/新增）、推送渠道（Bark/邮件/IM）、检查频率、防重复。

---

### 4. 增量资料

**提示词**：只抓取上次同步以来的新增或变更数据，避免全量拉取，提高效率。

**配置要点**：增量标识字段（时间戳/版本号/状态标记）、上次同步水位线存储、增量查询参数构造、异常回退全量。

---

### 5. 网络故障巡查

**提示词**：定时巡检告警平台 / 监控系统，发现未处理故障时自动通知责任人。

**配置要点**：告警 API、故障筛选条件（级别/状态/时间窗）、通知模板、责任人映射、巡查频率、静默时段。

---

### 6. 自动接单

**提示词**：监控工单池，新工单符合条件时自动接单 / 分派 / 回复，减少人工干预。

**配置要点**：工单池 API、接单条件（类型/区域/优先级）、自动回复模板、接单操作 API、冲突处理（多人抢单）、频率。

---

### 7. 公文流转监控

**提示词**：定时检查 OA 门户是否有新公文下发，发现新公文时推送通知并提取关键信息。

**配置要点**：公文列表 API、已读标记存储、公文摘要提取规则、推送渠道、检查频率。

---

### 8. 审批流程催办

**提示词**：定时检查待审批事项，超时未处理时自动催办相关审批人。

**配置要点**：待审批列表 API、超时阈值、催办消息模板、催办渠道（IM/邮件/Bark）、催办频率限制、升级机制。

---

### 9. 报表自动生成

**提示词**：定时从多个数据源拉取数据，汇总处理后生成报表文件（Excel/PDF），推送给相关人员。

**配置要点**：数据源 API 列表、数据汇总逻辑、报表模板、输出格式、推送对象、生成频率。

---

### 10. 工单状态跟踪

**提示词**：跟踪工单处理进度，检测超时 / 停滞 / 异常状态，自动告警。

**配置要点**：工单查询 API、跟踪条件、超时阈值、异常判断逻辑、告警渠道、跟踪频率。

---

### 11. 值班排班提醒

**提示词**：定时读取排班表，在值班前推送提醒（提前 N 小时），包含值班信息。

**配置要点**：排班表 API / 文件、提醒提前量、提醒内容模板、推送渠道、节假日处理。

---

### 12. 资源利用率监控

**提示词**：定时抓取资源监控平台数据（CPU/内存/磁盘/带宽），超过阈值时告警。

**配置要点**：监控 API、监控指标列表、阈值配置、告警级别、告警渠道、检查频率、连续超次确认。

---

### 13. 会议纪要归档

**提示词**：定时从 OA 系统提取会议纪要，按规范格式归档保存，并推送给参会人员。

**配置要点**：会议列表 API、纪要提取规则、归档目录结构、参会人提取、推送渠道、检查频率。

---

### 14. 考勤数据同步

**提示词**：定时拉取考勤系统数据，同步到本地数据库或 Excel，生成考勤统计报表。

**配置要点**：考勤 API、同步范围（部门/人员/时间）、数据映射、统计规则、输出格式、同步频率。

---

### 15. 资产台账核对

**提示词**：定时核对资产管理系统台账，检测资产变更（新增/调拨/报废），变更时通知资产管理员。

**配置要点**：资产 API、核对维度、变更判断逻辑、通知模板、核对频率、差异报告格式。

---

### 16. 合同到期提醒

**提示词**：监控合同管理系统，合同到期前 N 天开始提醒，多级递进提醒。

**配置要点**：合同列表 API、到期计算规则、提醒梯度（30/15/7/3/1天）、提醒对象、推送渠道。

---

### 17. 流程节点监控

**提示词**：监控业务流程关键节点，检测卡住的流程实例，自动通知处理人或上级。

**配置要点**：流程实例 API、关键节点定义、停滞判断逻辑、通知升级机制、检查频率。

---

### 18. 知识库更新检测

**提示词**：监控知识库系统内容变更，检测到更新时增量同步到本地，并推送更新摘要。

**配置要点**：知识库 API、变更检测方式、增量同步逻辑、摘要生成规则、推送渠道、检查频率。

---

### 19. 运维日志收集

**提示词**：定时收集各系统运维日志（操作日志 / 告警日志 / 系统日志），统一归档并生成日志摘要。

**配置要点**：日志 API 列表、日志过滤规则、归档目录结构、摘要生成逻辑、收集频率、保留期限。

---

### 20. 跨系统数据比对

**提示词**：从多个系统拉取同类数据，交叉比对差异，生成差异报告并告警。

**配置要点**：多系统 API、数据对齐键、比对字段列表、差异容忍度、差异报告格式、告警渠道、比对频率。

---

> 以上 20 项均为框架模板。实际部署时，Agent 会根据用户选择的具体项目，收集详细参数后生成完整的定时任务脚本。框架的存在是为了让用户在配置时有清晰的选择，而不是从零开始想"我到底需要什么"。

## SITES 配置模板

每个需要保活的系统对应一个 SITES 条目（内网版 GUI 程序用）：

```python
SITES = {
    "系统标识": {
        "name": "显示名称",                    # GUI 中显示的系统名称
        "keepalive_url": "http://系统首页URL",
        "cookie_domain": "系统域名或IP",       # Cookie 过滤用
        "cookie_json": os.path.join(SCRIPT_DIR, "xxx_cookies.json"),
        "cookie_txt": os.path.join(SCRIPT_DIR, "xxx_cookies.txt"),
        "login_page_keywords": ["关键词1", "关键词2"],  # 登录页 URL 中的关键词
        "logged_in_domain": "登录成功后的域名",
        "valid_cookie_names": ["关键Cookie名1", "Cookie名2"],  # 登录成功必须包含的 Cookie
        "color": "#0066cc",                   # GUI 中该系统的标识颜色
    },
}
```

> 多系统保活：在 SITES 字典中添加多个条目，程序自动为每个系统打开独立标签页，共用一个 Chrome 实例。

## 关键设计决策

### 为什么用独立 Chrome 配置目录（`.chrome_profile`）而非复用系统 Chrome？

- 系统 Chrome 的用户数据目录被运行中的 Chrome 锁定，必须先关闭 Chrome 才能复用
- 大型 Chrome 用户数据目录导致 `launch_persistent_context` 启动缓慢甚至无限超时（实测 60 秒+ 无响应）
- 独立目录首次需手动登录 SSO，后续自动保留登录态，不影响用户日常使用 Chrome
- 多系统保活共用一个 `.chrome_profile`，资源占用低

### 为什么用单 Chrome 多标签页而非多 Chrome 进程？

- 单进程管理简单，资源占用低
- 用户只需看到一个 Chrome 窗口
- 各系统 Cookie 文件独立，Agent 各取所需
- 共用 `.chrome_profile`，登录态统一管理

### 为什么守护进程和数据脚本要解耦？

- 守护进程（keeper）：只负责保持登录态和更新 Cookie 文件
- 数据脚本（fetcher）：从 Cookie 文件读取凭据，调用 API 获取数据
- 两者通过 Cookie 文件解耦，互不依赖
- 数据脚本崩溃不影响保活，保活重启不影响数据脚本

### 为什么公网版需要 Agent 保持在线？

- 公网版的 Cookie 刷新和扩展操作（20 项）都依赖 Agent 在线执行定时任务
- Cookie 刷新：Agent 定时打开浏览器访问系统页面，提取最新 Cookie 保存到文件
- 扩展操作：Agent 从 Cookie 文件读取凭据，调用 API 处理数据，推送通知
- Agent 离线时定时任务暂停，Agent 恢复在线后自动继续执行

### 为什么公网版不需要本地小程序？

- 内网版生成 GUI 程序是因为 Agent 无法常驻内网，需要一个本地守护进程独立运行
- 公网版 Agent 可保持在线，直接用 Playwright 定时刷新 Cookie 即可，无需额外程序
- 减少了用户的操作步骤：不用学怎么启动 GUI、怎么看状态灯，Agent 全自动处理
- Cookie 文件存储在用户指定目录，Agent 和用户都能直接使用

## 可选增强功能

以下功能已在实战中验证，按需集成：

### Bark 手机推送

Cookie 失效、Chrome 启动失败时自动推送到手机，包含防重复和静默时段逻辑。代码模式见 `references/code-patterns.md` 第 14 节。

## 参考文件

- `references/pitfalls.md` — 14 个实战踩坑点详解
- `references/code-patterns.md` — 完整代码模板（SITES 配置、守护进程核心、线程安全、Cookie 管理、登录检测、GUI 框架、HTTP 连接安全、Bark 推送）
- `references/verification.md` — 验证清单（内网版 21 项 + 公网版扩展 5 项）
- `references/extensions.md` — 20 项扩展操作详细框架与配置引导

用户可能不具备电脑基础，在开始前警告，如果用户执意要用，需要更详细的引导。