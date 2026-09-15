---
name: Windows电脑安全检查
description: "Windows 应急响应和安全基线排查专用工具，用户提供主机信息后，AI 自动引导进行全面的安全检查并分析结果。适用于安全基线检查、合规检查、终端安全检查、应急排查、可疑进程分析、配置审计等场景。"
metadata:
  name_cn: Windows 电脑终端安全检查
  description_cn: 对授权的 Windows 终端执行可复核的应急响应和安全排查，默认只读，分析专业
  version: 3.0
---

# Windows 电脑终端安全检查

Windows 应急响应和安全基线排查专用工具。在用户授权的 Windows 终端上执行分层安全检查，提供专业分析和可执行建议。

## 快速开始

当用户提供 Windows 主机信息时：

1. **验证环境**：确认主机名、当前用户、是否具备管理员权限
2. **询问排查模式**：快速全面排查 / 专项深度排查 / 应急响应模式
3. **执行检查命令**：使用 PowerShell 执行相应检查项
4. **⚠️ 立即分析输出**：每次执行命令后必须分析结果，给出专业结论
5. **生成报告**：汇总所有发现，提供风险评估和处置建议

---

## 输出分析要求（重要）

**每次执行命令后，必须对输出进行专业分析并给出结论**，格式如下：

### 标准分析报告格式

```
📋 检查项: [检查项名称]
🔧 命令: [执行的 PowerShell 命令]

📊 分析结果:
- [发现的关键信息点1]
- [发现的关键信息点2]
- [统计数据摘要]

⚠️ 可疑项:
- [可疑项1及原因]（🔴高危 / 🟡中危）
- [可疑项2及原因]

✅ 合规项:
- [符合基线的配置]

💡 建议:
- [下一步排查建议]
- [处置建议（如有必要）]
- [整改命令（需用户确认）]
```

### 威胁等级标注

| 等级 | 标识 | 定义 | 响应建议 |
|------|------|------|----------|
| **高危** | 🔴 | 确认存在入侵痕迹、后门或严重违规 | 立即隔离、深度排查、启动应急响应 |
| **中危** | 🟡 | 存在可疑项或违反基线需进一步确认 | 深入检查、查看日志、确认业务需要 |
| **低危/正常** | 🟢 | 未发现明显异常或符合预期 | 持续监控、纳入基线 |
| **未检查** | ⊘ | 权限不足或功能不可用导致无法检查 | 记录限制原因，不标记为合格 |

### 核心排查重点

根据输出内容重点关注以下 **8 大领域 + 18 个检查项**：

#### 1. **账号安全**
- UID=0 的非 Administrator 用户
- 新建账户、隐藏账户
- 密码策略、Guest 状态
- Administrators 组成员异常

#### 2. **进程与服务**
- 高 CPU/内存占用进程
- 异常进程路径、无签名进程
- 伪装系统进程、挖矿特征
- 危险服务状态（RemoteRegistry、Telnet）

#### 3. **网络与端口**
- 外连可疑 IP
- 高危端口监听（135/445/3389/4444 等）
- 0.0.0.0 监听且无防火墙保护
- 反弹 shell 特征

#### 4. **持久化机制**
- Run/RunOnce 注册表键
- 启动文件夹、计划任务
- 服务自启动、WMI 事件订阅
- 异常 DLL 劫持

#### 5. **文件与签名**
- Temp 目录可疑文件
- 用户可写路径的可执行文件
- 无签名或签名失效的二进制
- 近期修改的系统文件

#### 6. **日志与审计**
- 暴力破解痕迹（4625 事件）
- 异常登录 IP（4624 事件）
- 权限提升记录（4672 事件）
- 日志清除痕迹（1102 事件）

#### 7. **安全配置**
- UAC 禁用、防火墙关闭
- Defender 实时保护关闭
- 自动登录、空密码账户
- RDP/WinRM/SSH 未授权开放

#### 8. **后门与隐蔽通道**
- SSH 公钥后门
- WMI 持久化、DLL 劫持
- 注册表劫持（Image File Execution Options）
- PowerShell 下载执行痕迹

> 💡 详细解读要点见 `references/windows-analysis-guide.md`（需创建）

---

## 排查流程选择

连接成功后，询问用户选择使用哪个排查流程：

```
选择排查模式：

0. 🚀 快速全面排查（推荐，自动执行 18 项关键检查并汇总分析）

=== 专项深度排查 ===
1. 系统信息与账号安全
2. 进程与服务排查
3. 网络连接与端口
4. 文件与持久化机制
5. 日志与事件分析
6. 安全配置审计
7. 补丁与防护软件
8. 加密与启动安全
9. 远程访问配置
10. 浏览器与代理

=== 应急响应模式 ===
11. 🔥 应急响应（针对已知可疑行为的快速取证）
12. 🕵️ 深度后门检测（全面持久化机制排查）
13. 🌐 网络隐蔽通道检测（隧道、代理、C2）
14. 💾 内存与进程深度分析（需管理员权限）
15. 📊 性能异常分析（CPU/内存/磁盘）
```

> 📖 各流程详细检查项见 `references/windows-workflows.md`
> 🔧 具体命令和操作见 `references/windows-commands.md`

---

## 执行流程

### 选择 "0. 快速全面排查" 时

1. **预检**：记录主机信息、权限状态、PowerShell 版本
2. **自动执行 18 项关键检查**：
   - 账号安全
   - 进程检查
   - 网络端口
   - 异常文件
   - 登录日志
   - 历史命令
   - 定时任务
   - 自启动项
   - 系统服务
   - 防火墙配置
   - 共享文件夹
   - 注册表安全
   - 补丁与安全软件
   - 屏幕锁定策略
   - Defender/EDR 防护
   - 审计与日志保留
   - RDP/WinRM/SSH
   - 浏览器/Office/代理
3. **每项立即分析**：执行一项分析一项，标注风险等级
4. **生成综合报告**：
   - 执行摘要（风险等级统计）
   - 高危发现清单
   - 中危发现清单
   - 合规项汇总
   - 整改建议（优先级排序）
   - 验证方法

### 选择专项排查时

1. 执行该流程下的所有检查项命令
2. 分析每个命令的输出结果
3. 给出该领域的专业排查报告
4. 建议下一步排查方向或关联检查

### 应急响应模式（11-15）

当用户报告可疑行为时：

1. **现场固定**：
   - 记录当前时间、主机状态
   - 保存可疑对象信息（PID/路径/IP）
   - ⚠️ **不要结束进程或删除文件**

2. **关联分析**：
   - 围绕可疑对象展开：PID → 父进程 → 命令行 → 网络连接 → 文件 → 持久化
   - 构建时间线：登录时间 → 命令执行 → 文件修改 → 网络活动
   - 交叉验证：事件日志 ↔ 进程树 ↔ 网络连接 ↔ 文件落地

3. **证据分级**：
   - 🔴 **已确认恶意**：充分证据链（如反弹 shell + 外连 C2 + 持久化）
   - 🟡 **高度可疑**：多个可疑特征但缺少关键证据
   - 🟢 **待核实**：单一可疑特征，需业务确认
   - ✅ **正常/已授权**：经过验证的合法行为

4. **深度检测（需授权）**：
   - 内存扫描（Defender/EDR）
   - 外部 IOC 查询（VirusTotal）
   - 样本上传分析
   - 隔离/终止动作

> 详细采集命令与快速过滤示例见 `references/windows-incident-response.md`

---

## 预检命令

每次检查前必须执行，记录环境信息：

```powershell
# 预检脚本
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

[pscustomobject]@{
  ComputerName  = $env:COMPUTERNAME
  UserName      = [Security.Principal.WindowsIdentity]::GetCurrent().Name
  IsAdmin       = $isAdmin
  OS            = (Get-CimInstance Win32_OperatingSystem).Caption
  OSVersion     = [Environment]::OSVersion.Version.ToString()
  Architecture  = (Get-CimInstance Win32_OperatingSystem).OSArchitecture
  PowerShell    = $PSVersionTable.PSVersion.ToString()
  LocalTime     = Get-Date
  TimeZone      = (Get-TimeZone).DisplayName
  Uptime        = (Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime
}
```

**⚠️ 权限限制处理**：
- 若 `IsAdmin = False`，继续执行可用的只读检查
- 将受限项标为 **⊘ 未检查**，而不是 ✅ 合格
- 在报告中明确说明权限限制的影响范围

---

## 18 项核心检查清单

默认时间窗口：事件日志近 7 天；失败登录额外统计近 3 天。

| # | 检查项 | 风险关注点 | 典型威胁 |
|:---:|:---|:---|:---|
| 1 | **账号安全** | 隐藏管理员、Guest 启用、弱密码策略 | 持久化后门、权限维持 |
| 2 | **进程检查** | 无签名进程、异常路径、高资源占用 | 挖矿木马、RAT、勒索软件 |
| 3 | **网络端口** | 高危端口监听、0.0.0.0 暴露 | 反弹 shell、内网横向 |
| 4 | **异常文件** | Temp 目录可执行文件、无签名文件 | 落地载荷、持久化脚本 |
| 5 | **登录日志** | 暴力破解、异地登录、权限提升 | 初始访问、凭据窃取 |
| 6 | **历史命令** | 下载执行、账号操作、清痕命令 | 攻击者操作痕迹 |
| 7 | **定时任务** | 非 Microsoft 任务、可疑命令 | 持久化、定时回连 |
| 8 | **自启动项** | Run 键、启动文件夹异常 | 持久化 |
| 9 | **系统服务** | RemoteRegistry、异常服务路径 | 持久化、远程控制 |
| 10 | **防火墙配置** | 防火墙禁用、允许规则过宽 | 防御绕过 |
| 11 | **共享文件夹** | 未授权共享、Everyone 权限 | 横向移动、数据泄露 |
| 12 | **注册表安全** | UAC 禁用、自动登录 | 防御绕过、凭据泄露 |
| 13 | **补丁与安全软件** | 补丁滞后、Defender 禁用 | 漏洞利用 |
| 14 | **屏幕锁定策略** | 屏保未启用、超时过长 | 物理安全 |
| 15 | **Defender/EDR** | 实时保护禁用、排除项过宽 | 防御绕过 |
| 16 | **审计与日志** | 关键审计未启用、日志容量不足 | 取证盲区 |
| 17 | **RDP/WinRM/SSH** | 未授权开放、弱配置 | 初始访问、横向移动 |
| 18 | **浏览器/Office/代理** | 恶意扩展、宏策略宽松、代理劫持 | 钓鱼、C2 通信 |

---

## 参考文档结构

为保持轻量加载，采用按需读取的分层文档结构：

```
Windows-sec-doctor/
├── SKILL.md                           # 主 SKILL 文件（本文件）
├── references/
│   ├── windows-workflows.md              # 15 个排查流程的详细检查项清单
│   ├── windows-commands.md               # 检查项到具体命令的完整映射表
│   ├── windows-analysis-guide.md         # 详细解读要点和风险判断标准
│   ├── windows-security-baseline.md      # 安全基线参考标准（已存在）
│   └── windows-incident-response.md      # 应急响应参考（已存在）
└── templates/
    ├── report-template.docx              # 报告模板（可选）
    └── checklist.xlsx                    # 检查清单（可选）
```

**按需加载原则**：
- 用户选择 "快速全面排查"：只需本文件
- 用户选择专项排查（1-10）：读取 `windows-workflows.md` 对应章节
- 用户选择应急响应（11-15）：读取 `windows-incident-response.md`
- 需要详细判定标准时：读取 `windows-analysis-guide.md`
- 需要基线对比时：读取 `windows-security-baseline.md`

---

## 最佳实践

### 1. 按需加载 references 文件
只在用户选择特定排查流程时加载对应的检查项和命令，避免上下文过载。

### 2. 保持分析连贯性
**每次执行命令后立即分析**，不要等所有命令执行完再分析。用户需要实时了解检查进度和发现。

### 3. 明确风险等级
根据证据强度明确标注 🔴高危 / 🟡中危 / 🟢低危，不要模棱两可。

### 4. 提供可执行建议
不仅是发现问题，还要给出：
- 具体的整改命令（需用户确认）
- 回退方法
- 验证方式
- 业务影响说明

### 5. 构建时间线关联
对于应急响应模式，必须构建完整的时间线：
```
登录时间 → 命令执行 → 文件修改 → 进程启动 → 网络连接 → 持久化设置
```

### 6. 交叉验证证据
单一证据不足以定性，需要交叉验证：
- 进程 ↔ 网络连接 ↔ 文件路径
- 事件日志 ↔ 历史命令 ↔ 计划任务
- 签名状态 ↔ 文件哈希 ↔ 路径合法性

### 7. 区分"可疑"与"已确认"
- **可疑**：单一特征匹配，需进一步验证
- **已确认恶意**：多重证据链完整

### 8. 敏感操作必须获得明确授权
- 结束进程
- 删除文件
- 修改配置
- 禁用服务
- 更新补丁

### 9. 报告格式适应环境
- Windows 环境优先 `.docx`（确认工具可用）
- macOS/Linux 环境使用 Markdown
- 用户明确要求时使用指定格式

### 10. 记录检查盲区
必须明确说明：
- 权限不足导致的未检查项
- 功能不可用
- 被组策略/MDM 覆盖的设置
- 日志已被覆盖或清空的时间段

---

## 执行示例

### 示例 1：用户请求快速检查

**用户输入**：
```
请对这台 Windows 主机进行安全检查，主机名 WIN-SERVER-01
```

**AI 响应流程**：

1. **执行预检**
```powershell
# 执行预检命令
```

📋 **预检结果**:
```
主机名: WIN-SERVER-01
用户: DOMAIN\admin
管理员权限: True
操作系统: Microsoft Windows Server 2019 Datacenter
PowerShell 版本: 5.1.17763.5830
检查时间: 2026-07-27 14:30:15
```

2. **询问模式**
```
请选择排查模式：
0. 🚀 快速全面排查（推荐，18 项关键检查）
1-10. 专项深度排查
11-15. 应急响应模式

建议：首次检查选择 [0] 快速全面排查
```

3. **执行检查并逐项分析**

**[1/18] 账号安全检查**
```powershell
Get-LocalUser | Select-Object Name,Enabled,LastLogon,PasswordLastSet
```

📊 **分析结果**:
- 共 5 个本地用户
- Administrator: 已启用，最后登录 2026-07-26
- Guest: ⚠️ **已启用**（不符合基线）
- 发现 1 个新建用户 "backup_admin"（创建于 2026-07-25）

⚠️ **可疑项**:
- 🟡 Guest 账户已启用（基线要求禁用）
- 🟡 "backup_admin" 用户需确认是否为授权账号

💡 **建议**:
- 立即禁用 Guest 账户：`Disable-LocalUser -Name Guest`
- 确认 "backup_admin" 的创建者和用途
- 检查 "backup_admin" 的组成员资格

**[继续执行剩余 18 项...]**

4. **生成综合报告**

---

### 示例 2：用户报告可疑进程

**用户输入**：
```
发现一个可疑进程 PID 1234，占用大量 CPU，请帮忙分析
```

**AI 响应流程**：

1. **切换到应急响应模式**
```
检测到可疑行为报告，启动应急响应模式
```

2. **现场固定**
```powershell
# 记录时间和进程基本信息
Get-Process -Id 1234 | Select-Object *
Get-Date
```

📋 **固定信息**:
- 当前时间: 2026-07-27 14:35:00
- 进程名: svchost.exe
- PID: 1234
- 路径: C:\Windows\Temp\svchost.exe
- CPU: 95%
- 内存: 512 MB

⚠️ **初步判断**: 🔴 **高度可疑**
- svchost.exe 在 Temp 目录（正常应在 System32）
- 路径异常是典型的进程伪装手法

3. **关联排查**

**进程详情**:
```powershell
Get-CimInstance Win32_Process | Where-Object ProcessId -eq 1234 | Select-Object CommandLine,ParentProcessId,CreationDate
```

📊 **分析**:
- 命令行: `C:\Windows\Temp\svchost.exe -o pool.minexmr.com:4444`
- 父进程: PID 5678 (powershell.exe)
- 启动时间: 2026-07-27 10:15:30

🔴 **确认恶意**: 这是一个挖矿木马
- 连接到挖矿矿池 pool.minexmr.com
- 伪装成系统进程 svchost.exe
- 从 PowerShell 启动

**网络连接**:
```powershell
Get-NetTCPConnection | Where-Object OwningProcess -eq 1234
```

📊 **分析**:
- 外连 IP: 185.71.65.189:4444
- 状态: ESTABLISHED
- 持续时间: 4 小时

**父进程分析**:
```powershell
Get-Process -Id 5678
```

📊 **分析**:
- 父进程: powershell.exe
- 路径: C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe
- 命令行: （需进一步查看）

**持久化检查**:
```powershell
Get-ScheduledTask | Where-Object { $_.Actions.Execute -like '*svchost*' -and $_.TaskPath -notlike '\Microsoft\*' }
```

📊 **分析**:
- 发现定时任务 "SystemUpdate"
- 每 5 分钟执行: `C:\Windows\Temp\svchost.exe`
- 🔴 **确认持久化机制**

4. **生成证据报告和处置建议**

🔴 **威胁确认**: 挖矿木马感染

**证据链**:
1. 伪装进程: C:\Windows\Temp\svchost.exe
2. 挖矿行为: 连接矿池 pool.minexmr.com:4444
3. 持久化: 计划任务 "SystemUpdate" 每 5 分钟启动
4. 启动方式: 通过 PowerShell 下载执行（需查看历史命令）

**立即处置建议** (需用户确认):
```powershell
# 1. 终止进程
Stop-Process -Id 1234 -Force

# 2. 删除定时任务
Unregister-ScheduledTask -TaskName "SystemUpdate" -Confirm:$false

# 3. 删除恶意文件
Remove-Item "C:\Windows\Temp\svchost.exe" -Force

# 4. 防火墙封禁 C2 IP
New-NetFirewallRule -DisplayName "Block Mining Pool" -Direction Outbound -RemoteAddress 185.71.65.189 -Action Block
```

**下一步排查**:
- 检查 PowerShell 历史命令（查找下载来源）
- 检查事件日志（查找初始入侵时间）
- 检查其他持久化点（注册表 Run 键、服务）
- 全盘扫描其他恶意文件

---

## 注意事项

### ⚠️ 安全边界
- 仅检查用户明确授权的 Windows 主机
- 不尝试读取密码、导出凭据、绕过访问控制
- 不扫描未指定主机或进行横向移动

### ⚠️ 默认行为
- **默认只读**：不修改系统设置、不停止服务、不删除文件
- 整改操作必须获得用户对**具体对象和命令**的明确确认
- "做整改"不等于授权修改全部发现

### ⚠️ 证据判定
- 将"可疑"与"已确认违规"明确区分
- 进程名、端口号、路径只是线索，需结合多重证据
- 没有充分证据时不得标注为恶意

### ⚠️ 权限处理
- 缺少管理员权限时，将受限项标为 **⊘ 未检查**
- 不能把空结果直接视为无风险
- 在报告中明确说明检查盲区

### ⚠️ 环境兼容
- 检查 PowerShell 版本兼容性
- 不可用的 cmdlet 使用替代方案并记录原因
- 域环境下注意 GPO 策略覆盖

---

## 版本信息

- **版本**: 3.0
- **更新日期**: 2026-08-12
- **变更说明**:
  - 新增标准化分析报告格式
  - 新增 15 种排查模式（0-14）
  - 新增应急响应模式和深度检测
  - 优化文档结构，支持按需加载
  - 增强时间线构建和证据关联能力

**维护者**: 集团SOC