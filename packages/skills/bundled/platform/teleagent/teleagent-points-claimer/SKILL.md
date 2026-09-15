---
name: teleagent-points-claimer
description: Automatically claim daily points in the TeleAgent desktop client (积分福利社 daily check-in). Use when the user wants to claim daily points, sign in for points, run a daily points task, or confirm points claim status.
name_cn: TeleAgent自动领取积分
description_cn: 自动打开TeleAgent客户端，在积分福利社完成每日签到领积分，并设置定时任务。
create_source: super-agent-skill-creator
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '4138c6fa-eb27-47a9-bd5a-cb4b6fa5fa05'
  PropagateID: '4138c6fa-eb27-47a9-bd5a-cb4b6fa5fa05'
  ReservedCode1: 'c42206a1-9118-4632-8cf5-d1e9d08f6514'
  ReservedCode2: 'c42206a1-9118-4632-8cf5-d1e9d08f6514'
---

# TeleAgent 自动领取积分

## 概览

自动完成 TeleAgent 客户端「积分福利社」的每日签到领积分（每日 100 积分），并确认领取结果。支持直接执行、定时任务触发，以及核对是否已领取。

## 关键经验（Electron 兼容性）

TeleAgent 桌面客户端基于 Electron（窗口类名 `Chrome_WidgetWin_1`），有以下注意事项：

1. **mouse_event 坐标点击不可靠**：低级鼠标事件（`win32api.mouse_event`）可能被 Electron 窗口拦截，点击不生效。**必须优先使用 uiautomation 的 `ctrl.Click()` 控件级点击**，坐标点击仅作为兜底。
2. **模糊匹配「领取」会误匹配侧边栏任务名**：侧边栏任务列表中常有「TeleAgent每日积分自动领取」等任务名，含「领取」二字。**必须用 `ButtonControl` + 精确名称匹配**（`立即领取` / `今日已领`），不可用模糊 `in` 匹配。
3. **点击后菜单会关闭**：点击「立即领取」后账户菜单通常关闭，需要重新打开菜单才能验证按钮是否变为「今日已领」。
4. **控制台中文编码**：Windows PowerShell 默认 GBK 编码，脚本输出中文按钮名会乱码。所有脚本必须用 `io.TextIOWrapper` 包装 stdout 为 UTF-8（`check_schedule.py` 曾遗漏此包装导致任务名乱码）。
5. **Electron 多进程窗口匹配**：TeleAgent 运行时有多个同名进程（主进程 + GPU + 渲染进程等），主窗口可能属于任一子进程而非最小 PID 进程。`shot_window.py` 的 `find_main_hwnd` 必须收集**所有**同名进程的窗口按面积选最大者，**不可**只取最小 PID 进程的窗口（曾因误取最小 PID 导致 `failed_no_window`）。
6. **`py_compile` 生成 `.pyc` 导致上架被拦截**：对技能脚本执行 `python -m py_compile` 语法检查会在 `scripts/__pycache__/` 下生成 `.pyc` 文件，技能上架时会被拒绝（「存在恶意扩展名文件」）。语法检查后必须删除 `__pycache__` 目录，或改用 `python -c "import ast; ast.parse(open('file.py').read())"` 等不生成缓存的方式检查语法。

## 入口路径

TeleAgent 客户端主界面**没有直接的签到/积分按钮**。正确入口为：

```
左下角账户入口（用户名「肖洋」，位于窗口左下角约 (0.043×宽, 0.94×高)）
  → 点击弹出账户菜单
    → 「积分福利社」模块（蓝绿渐变标题条）
      → 「立即领取」按钮（可点击，深蓝色）
      → 领取成功后变为「今日已领」按钮（浅蓝、禁用态）
```

## 执行流程

### 步骤 0：检查是否已设置定时任务（首次使用必查）

当用户首次使用本技能（或主动询问是否已有定时任务）时，**先检查是否已存在积分领取的定时任务**，确保不会遗漏自动化设置。

**运行检查脚本：**

```
python scripts/check_schedule.py
```

输出最后一行 `RESULT: {...}`，`has_schedule` 取值：

| has_schedule | 含义 |
|-------------|------|
| `true` | 已存在积分领取定时任务，列出详情（名称/时间/状态），跳过创建 |
| `false` | 未找到积分领取定时任务，进入「提供选项」流程 |

**已存在定时任务时：**

向用户展示已有任务信息，格式参考：

```
已检测到积分领取定时任务：
  - 名称「自动领取积分」| 每天 07:50 | ✅ 已启用 | prompt: 使用 @TeleAgent自动领取积分 技能
无需重复创建，继续执行领积分操作。
```

**未找到定时任务时，用 question 工具提供选项：**

使用 question 工具向用户提问，选项如下：

- 选项1（推荐）：「创建每天定时领取任务（默认 07:50）」— 创建 cron 类型定时任务，每天 07:50 自动执行本技能领取积分，prompt 为「使用 @TeleAgent自动领取积分 技能」，然后继续领积分
- 选项2：「自定义时间创建定时任务」— 让用户指定执行时间，再创建
- 选项3：「仅本次领取，不创建定时任务」— 跳过创建，直接执行领积分
- 选项4：「暂不领取」— 退出，不做任何操作

用户选择创建定时任务后，按照 scheduler 技能的 add-task 流程执行：
1. 展示任务卡片（任务名称、任务要求、执行频率、执行时间、工作空间、使用技能）
2. 用户确认后执行 `teleai-agent-schedule add` 命令
3. 报告创建成功及下次执行时间
4. 继续执行本次领积分操作（步骤 1 起）

用户选择不创建时，直接进入步骤 1 执行领积分。

> **注意**：此步骤仅在首次使用或用户主动询问时执行。如果本技能是由定时任务自动触发的，跳过此步骤直接执行领积分。

### 1. 确认窗口与菜单

- 检查 TeleAgent 进程与主窗口：`python scripts/shot_window.py --proc-name TeleAgent --out <截图路径>`，成功会输出 `saved ... size WxH`。
- 若需要确认菜单状态，先截图并用视觉工具查看左下角是否已弹出账户菜单。

### 2. 定位领取按钮

运行：

```
python scripts/find_claim_button.py
```

输出：
- `CLAIM_BTN_RECT=(left,top,right,bottom) CENTER=(cx,cy) NAME=立即领取` → 菜单已打开，按钮可点击
- `CLAIM_BTN_RECT=... NAME=今日已领` → 今日已领取，无需再点
- `CLAIM_BTN_NOT_FOUND` → 菜单未打开或未找到按钮，进入第 3 步
- `NO_WINDOW` → 客户端未启动

**重要**：该脚本只精确匹配「立即领取」/「今日已领」按钮名，避免误匹配侧边栏任务名（如「TeleAgent自动领取每日积分并记录结果」）。不要用模糊含「领取」的匹配。

### 3. 打开账户菜单（若按钮未找到）

- 点击左下角账户入口打开菜单。账户入口位置可先用 uiautomation 定位文本「肖洋」（账户用户名），拿到实时坐标再点击；兜底坐标为窗口底部约 (0.031×宽, 0.95×高)。
- 点击后等待 1~1.5 秒，再运行 `find_claim_button.py`。

### 4. 点击领取

- **优先控件级点击**：使用 uiautomation 控件 `Click()` 点击（`find_claim_button.py` 的 `find_claim_control()` 可返回控件对象），避免坐标点击被 Electron 窗口拦截失效。
- 控件点击失败时自动退回 `python scripts/click_xy.py --x <cx> --y <cy>` 坐标点击（仅作兜底）。
- 若按钮名为「今日已领」：今日已领取，直接确认状态，**不要点击**。

### 5. 确认结果（必须）

点击后等待 2 秒，**重新打开账户菜单**检查按钮状态：

- 成功标志：「立即领取」变为「今日已领」
- 菜单关闭后需重新打开才能看到按钮状态变化
- 截图（`shot_window.py`）并用视觉模型确认「已领 X 天 / 累计 Y 积分」天数+1
- `days`/`points` 可能为 `null`（UI 文字无法被 uiautomation 读取），此时必须通过截图视觉确认

### 6. 记录结果

将领取结果写入当日记忆日志（memory-manager 技能），格式参考：

```
- [时间戳] TeleAgent每日积分领取完成：已领天数 X→X+1，累计积分 Y→Y+100；按钮状态变为「今日已领」。
```

## 一键脚本（推荐用于定时任务）

```powershell
python scripts/claim_points.py --output-dir D:\TeleClaw的工作空间\.temp\teleagent-points
```

自动完成：置前窗口 →（必要时打开菜单）→ 精确定位按钮 → `ctrl.Click()` 点击 → 重新打开菜单验证 → 截图留档 → 输出结果 JSON。

输出最后一行 `RESULT: {...}`，`status` 取值：

| status | 含义 |
|--------|------|
| `claimed` | 已成功领取（且已验证按钮变为「今日已领」） |
| `already_claimed` | 今日已领取过 |
| `failed_missing_button` | 菜单打开后仍找不到按钮（可能界面改版） |
| `failed_verify` | 点击后未确认按钮变为「今日已领」（可能被拦截/界面卡顿，需人工查看截图） |
| `failed_no_window` | 客户端未运行 |

`verified` 字段表示是否成功验证按钮变为「今日已领」；状态为 `claimed` 时 `verified` 一定为 `true`（若未验证成功将返回 `failed_verify`）。`days` / `points` 可能为 `null`，此时必须通过截图视觉确认实际值。

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `claim_points.py` | 一键领取（推荐），自动完成全流程 |
| `check_schedule.py` | 检查是否已设置积分领取定时任务 |
| `find_claim_button.py` | 定位按钮坐标/控件，命令行输出 |
| `click_xy.py` | 坐标点击（兜底方案，Electron 下可能无效） |
| `shot_window.py` | 截取 TeleAgent 窗口画面 |

## 注意事项

- 依赖：`pip install uiautomation psutil pillow pywin32`（已安装于本机）
- 脚本路径基于本技能目录，引用时使用绝对路径
- 点击前自动将窗口置前（`SetForegroundWindow` + `SW_RESTORE`）
- **Electron 兼容**：优先 `ctrl.Click()` 控件级点击，不用 `mouse_event` 低级鼠标事件；`click_xy.py` 仅作兜底
- **精确匹配**：按钮定位始终用 `ButtonControl` 精确匹配 `立即领取`/`今日已领`，不用模糊 `in` 匹配
- 若「立即领取」按钮位置变化（客户端改版），用 `find_claim_button.py` 重新定位，勿硬编码坐标
- 本技能依赖 TeleAgent 桌面客户端已登录（用户名「肖洋」）
- **验证流程**：点击后菜单会关闭，需重新打开菜单才能确认按钮变为「今日已领」
- **语法检查注意**：对脚本做 `python -m py_compile` 后会生成 `__pycache__/*.pyc`，上架前必须删除；建议改用 `python -c "import ast; ast.parse(open('file.py',encoding='utf-8').read())"` 检查语法以避免生成缓存

## 故障排查

| 现象 | 原因与处理 |
|------|------|
| `NO_WINDOW` / `failed_no_window` | TeleAgent 未启动，需先启动客户端；若已启动仍报此错，检查 `shot_window.py` 的 `find_main_hwnd` 是否误取了无窗口的子进程（Electron 多进程，主窗口可能不属于最小 PID 进程） |
| `failed_missing_button` | 菜单打开后仍找不到按钮（可能界面改版，dump UI 树查找含「领取」「积分」「福利」的元素） |
| `failed_verify` | 点击后未验证成功（自动任务需人工看截图确认是否已领） |
| `click_xy` 点击无效果 | Electron 窗口拦截低级鼠标事件，改用 `ctrl.Click()` 控件级点击 |
| 脚本误点侧边栏任务名 | 按钮匹配用了模糊 `in`，需改为 `ButtonControl` 精确匹配 `立即领取`/`今日已领` |
| 截图确认天数未变化 | 点击后菜单关闭，需重新打开菜单才能看到更新后的按钮状态和天数 |
| 控制台中文乱码 | 脚本已用 `io.TextIOWrapper` 包装 stdout 为 UTF-8；若仍乱码，用视觉模型确认截图而非依赖文字输出 |
| 定时任务里执行失败 | 确保客户端保持运行且窗口未被最小化；执行前先 `SetForegroundWindow` |
| 上架报「存在恶意扩展名文件 .pyc」 | `python -m py_compile` 生成了 `scripts/__pycache__/*.pyc`，删除 `__pycache__` 目录后重新上架 |