---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '55fa781e-a644-4f84-b50f-0768a5a49226'
  PropagateID: '55fa781e-a644-4f84-b50f-0768a5a49226'
  ReservedCode1: '26bb916e-77ca-43c3-a6e9-c57b75627a51'
  ReservedCode2: '26bb916e-77ca-43c3-a6e9-c57b75627a51'
---

# 安全运维参考指南

[Agent-运维型]执行安全检查与应急响应时的专用参考文档。覆盖18项安全基线检查、三模式排查体系、应急响应流程、威胁等级标注规范和高危端口参考表。

<!-- INDEX: Table of Contents,20 | 安全检查三模式,36 | 18项安全基线检查标准,46 | 高危端口参考表,71 | 威胁等级标注规范,91 | 说人话表达规范（⛔面向用户汇报时强制执行）,109 | 应急响应流程,124 | 应急响应PowerShell命令库,175 | 常见整改命令速查,287 | 预检命令,321 | 流程关联建议,340 | 拆分文件说明,354 -->

---

## Table of Contents

- 安全检查三模式
- 18项安全基线检查标准
- 高危端口参考表
- 威胁等级标注规范
- 说人话表达规范
- 应急响应流程
- 应急响应PowerShell命令库
- 常见整改命令速查
- 预检命令
- 流程关联建议
- 拆分文件说明

---

## 安全检查三模式

| 模式 | 名称 | 触发场景 | 执行内容 | 确认要求 |
|------|------|---------|---------|---------|
| 模式0 | 快速全面排查 | 首次排查、定期体检、系统状态评估 | 自动执行全部18项安全基线检查，汇总分析结果 | 只读操作，免确认 |
| 模式1-10 | 专项深度排查 | 针对特定怀疑方向深入检查 | 账号安全/进程服务/网络端口/文件持久化/日志事件/安全配置/补丁防护/远程访问/浏览器代理/性能异常，按专项展开 | 只读操作，免确认；深度检测（内存检索、在线信誉查询）须授权 |
| 模式11-15 | 应急响应模式 | 确认或高度怀疑入侵 | 快速取证/深度后门检测/网络隐蔽通道检测/内存进程深度分析/性能异常分析 | ⛔仅只读取证，禁止结束进程/删除文件/清除日志；深度动作须明确授权 |

---

## 18项安全基线检查标准

| 序号 | 检查项 | 合格标准 | 风险等级 |
|------|--------|----------|---------|
| 1 | 账号安全 | 无弱口令、Guest已禁用、无多余管理员账号 | 高 |
| 2 | 进程检查 | 无可疑进程运行（mimikatz、ncat、psexec等） | 高 |
| 3 | 网络端口 | 高危端口(135/445/3389)未绑定公网IP，无异常监听 | 高 |
| 4 | 异常文件 | 系统目录无可疑可执行文件 | 中 |
| 5 | 登录日志 | 近7天无异常登录IP，无暴力破解痕迹 | 高 |
| 6 | 历史命令 | 无可疑PowerShell编码命令或恶意脚本执行记录 | 中 |
| 7 | 定时任务 | 无可疑定时任务，非Microsoft任务均经授权 | 中 |
| 8 | 自启动项 | 无可疑自启动项，启动路径注册表无异常 | 中 |
| 9 | 系统服务 | 危险服务(TermService/RemoteRegistry/TLNTSVR)已禁用或合理管控 | 中 |
| 10 | 防火墙配置 | 防火墙已启用，默认入站策略为阻止 | 高 |
| 11 | 共享文件夹 | 默认共享(C$/D$/Admin$)已关闭或受控 | 中 |
| 12 | 注册表安全 | UAC已启用(EnableLUA=1)，DisableCAD=0 | 中 |
| 13 | 补丁与安全软件 | 补丁滞后不超过30天，安全软件正常运行 | 中 |
| 14 | 屏幕锁定策略 | 超时<=5分钟，恢复需密码认证 | 低 |
| 15 | Defender/EDR防护 | Defender或企业EDR正常受管控，实时保护/防篡改/云保护未被非授权关闭，排除项与ASR策略经业务确认 | 高 |
| 16 | 审计与日志 | 安全/系统/应用/PowerShell/Defender/Sysmon日志已启用并满足保留策略，关键审核子类别按策略开启 | 中 |
| 17 | RDP/WinRM/SSH | 未经授权的远程访问服务已禁用，获准服务只对受信网络开放，RDP启用NLA与TLS | 高 |
| 18 | 浏览器/Office/代理 | 代理/PAC/hosts/浏览器策略和扩展均经授权，Office宏策略阻止Internet不受信任宏 | 中 |

---

## 高危端口参考表

| 端口 | 服务 | 风险说明 |
|------|------|----------|
| 21 | FTP | 明文传输，易被暴力破解 |
| 22 | SSH | 密钥管理不当风险 |
| 23 | Telnet | 明文传输，建议禁用 |
| 25 | SMTP | 开放中继风险 |
| 135 | RPC | 常见攻击入口 |
| 139 | NetBIOS | 信息泄露 |
| 445 | SMB | 勒索病毒利用 |
| 1433 | MSSQL | 数据库暴露 |
| 3306 | MySQL | 数据库暴露 |
| 3389 | RDP | 远程桌面暴露 |
| 5900 | VNC | 远程控制暴露 |
| 6379 | Redis | 未授权访问 |
| 8080/8443 | Web代理 | 服务暴露 |

---

## 威胁等级标注规范

安全检查结果必须标注威胁等级，禁止省略：

| 等级 | 标记 | 判定条件 | 处置要求 |
|------|------|---------|---------|
| 高危 | 🔴 | 确认入侵痕迹（如发现恶意进程、后门、异常外连、暴力破解成功） | 立即建议隔离主机+启动应急响应模式+深度排查；不可标记为合格 |
| 中危 | 🟡 | 可疑项需确认（如补丁滞后、非必要服务运行、异常但未确认恶意的进程） | 建议深入检查+查看相关日志+确认业务需要后再定级 |
| 低危 | 🟢 | 合规建议项（如日志保留策略优化、默认共享管控建议） | 持续监控+纳入基线跟踪 |
| 未检查 | ⊘ | 权限不足或工具不可用导致该项无法检查 | 记录限制原因，不可标记为合格，须标注"须补充检查" |

**强制规则**：
- 每项检查结果必须标注上述四种等级之一，禁止留空
- 🔴高危项须在报告最前部突出标注，不可埋没在正常项中
- ⊘未检查项不可与其他等级混合标注，须独立列出并说明原因

---

## 说人话表达规范（⛔面向用户汇报时强制执行）

向用户汇报安全检查/系统操作结果时，一律用通俗语言+量化结论，禁止把命令、注册表路径、服务名等术语作为说明主体：

| 场景 | 禁止说法 | 说人话说法 |
|------|---------|-----------|
| 磁盘检查 | "C盘使用率78%，执行cleanmgr清理临时文件" | "C盘快满了（用了78%，还剩12G），我建议清理临时文件腾出空间" |
| 服务状态 | "TermService服务运行中，建议Set-Service禁用" | "远程桌面服务还开着，外人有机会远程连你这台电脑，建议关掉" |
| 安全检查 | "445端口监听于0.0.0.0，存在SMB暴露风险" | "有个共享端口对外开放，黑客常用的攻击入口，建议封锁" |
| 启动项 | "发现Run键下可疑启动项unknown.exe" | "开机时有个可疑程序会自动启动，可能是广告或木马" |

**量化要求**：涉及数量/比例/前后对比时给出具体数字，拒绝"挺多/有点卡/占用较高"等模糊表述。例："已清理3.2GB临时文件，C盘占用78%→71%"。

---

## 应急响应流程

当发现🔴高危项或用户报告可疑入侵时，启动应急响应流程：

### 快速固定现场（⛔仅只读取证）

- 记录当前时间与系统状态
- 记录可疑对象信息（PID/路径/IP/文件）
- 采集当前网络连接快照
- 采集当前进程树快照
- 记录当前登录用户

**⛔强制规则**：禁止结束可疑进程、禁止删除可疑文件、禁止清除日志，确保证据链完整性。

### 围绕可疑对象的关联分析

| 分析维度 | 检查内容 |
|---------|---------|
| 进程分析 | 进程详情→父进程与子进程→命令行→模块(DLL)→网络连接→文件路径与签名→启动时间 |
| 文件分析 | 文件哈希(MD5/SHA256)→签名状态→时间戳(创建/修改/访问)→关联进程→PE头信息 |
| 网络分析 | 五元组信息→对端IP归属→历史DNS查询→防火墙日志 |
| 持久化分析 | 相关计划任务→相关注册表键→相关服务→相关启动项→WMI事件订阅 |

### 时间线构建

- 初始访问时间（登录日志4624/4625）
- 命令执行时间（PowerShell日志4104/历史命令）
- 文件落地时间（文件时间戳）
- 进程启动时间（进程创建时间）
- 网络活动时间（连接建立时间）
- 持久化设置时间（任务创建时间）

### 证据分级

| 证据等级 | 定义 | 处置 |
|---------|------|------|
| 已确认恶意 | 哈希匹配已知恶意软件/签名验证失败且行为异常 | 标注🔴高危，建议隔离 |
| 高度可疑 | 异常行为模式但未完全确认 | 标注🟡中危，建议深度检测 |
| 须核实 | 存在异常指标但可能有合理原因 | 标注🟡中危，需业务确认 |
| 正常已授权 | 经业务确认为合法操作 | 标注🟢低危，纳入基线 |

### 深度检测（须用户明确授权）

| 深度动作 | 授权要求 | 说明 |
|---------|---------|------|
| 内存特征检索 | 须明确授权+说明性能影响 | YARA/IOC规则匹配，禁止注入DLL/修改内存/转储上传 |
| 原始证据导出 | 须明确授权+确认磁盘空间 | 导出.evtx日志+计算SHA256，优先最小集合 |
| 在线信誉查询 | 须明确授权+说明所用服务 | 仅查询SHA-256，禁止上传文件/命令行/内存/内部路径 |

---

## 应急响应PowerShell命令库

### 用户账户与组

```powershell
Get-LocalUser | Select-Object Name,SID,Enabled,LastLogon,PasswordLastSet,Description
Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction SilentlyContinue | Select-Object Name,SID,ObjectClass,PrincipalSource
Get-CimInstance Win32_UserAccount -Filter 'LocalAccount=True' | Select-Object Name,SID,Disabled,Lockout,PasswordRequired,Status
```

### 进程树、签名与哈希

```powershell
# 进程树基础数据
Get-CimInstance Win32_Process | Select-Object Name,ProcessId,ParentProcessId,ExecutablePath,CommandLine,CreationDate

# 可执行文件签名与SHA-256
Get-CimInstance Win32_Process | Where-Object ExecutablePath | ForEach-Object {
  $sig = Get-AuthenticodeSignature -FilePath $_.ExecutablePath -ErrorAction SilentlyContinue
  $owner = Invoke-CimMethod -InputObject $_ -MethodName GetOwner -ErrorAction SilentlyContinue
  [pscustomobject]@{Name=$_.Name;PID=$_.ProcessId;PPID=$_.ParentProcessId;Owner=("$($owner.Domain)\\$($owner.User)");Path=$_.ExecutablePath;CommandLine=$_.CommandLine;Signature=$sig.Status;Signer=$sig.SignerCertificate.Subject;SHA256=(Get-FileHash $_.ExecutablePath -Algorithm SHA256 -ErrorAction SilentlyContinue).Hash}
}
```

### TCP/UDP网络连接

```powershell
# 已建立TCP连接与进程映射
Get-NetTCPConnection -State Established | ForEach-Object {
  $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
  [pscustomobject]@{Local="$($_.LocalAddress):$($_.LocalPort)";Remote="$($_.RemoteAddress):$($_.RemotePort)";State=$_.State;PID=$_.OwningProcess;Process=$p.ProcessName;Path=$p.Path}
}

# TCP监听与UDP端点
Get-NetTCPConnection -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess
Get-NetUDPEndpoint | Select-Object LocalAddress,LocalPort,OwningProcess
```

### 持久化：启动项、IFEO、服务和计划任务

```powershell
# Run/RunOnce与启动文件夹
$runKeys = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run','HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce'
$runKeys | ForEach-Object { Get-ItemProperty -Path $_ -ErrorAction SilentlyContinue }
Get-ChildItem 'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp',"$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup" -Force -ErrorAction SilentlyContinue

# IFEO调试器与SilentProcessExit
Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options' -ErrorAction SilentlyContinue | ForEach-Object { Get-ItemProperty $_.PSPath | Where-Object { $_.Debugger -or $_.GlobalFlag } }

# 服务与计划任务
Get-CimInstance Win32_Service | Select-Object Name,DisplayName,State,StartMode,StartName,PathName,ProcessId
Get-ScheduledTask | Where-Object State -ne 'Disabled' | ForEach-Object { [pscustomobject]@{TaskName=$_.TaskName;TaskPath=$_.TaskPath;State=$_.State;Actions=(($_.Actions | ForEach-Object { "$($_.Execute) $($_.Arguments)" }) -join '; ');Triggers=($_.Triggers | ForEach-Object { $_.CimClass.CimClassName }) -join '; '} }
```

### 扩展持久化与远程访问

```powershell
# 32位Run键、策略Run键、Winlogon
$keys = 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\RunOnce','HKCU:\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run','HKLM:\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run','HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon','HKCU:\Environment'
$keys | ForEach-Object { Get-ItemProperty -Path $_ -ErrorAction SilentlyContinue }

# AppInit_DLLs、RDP、LSA包、WDigest
reg query 'HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Windows' /v AppInit_DLLs
reg query 'HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server' /v fDenyTSConnections
reg query 'HKLM\SYSTEM\CurrentControlSet\Control\Lsa' /v 'Security Packages'
reg query 'HKLM\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest' /v UseLogonCredential
```

### 文件落地排查

```powershell
$paths = 'C:\Windows\Temp','C:\temp','C:\Users\Public',"$env:APPDATA","$env:LOCALAPPDATA",'C:\ProgramData'
$extensions = '*.exe','*.dll','*.sys','*.ps1','*.psm1','*.bat','*.cmd','*.vbs','*.js','*.jse','*.hta','*.lnk','*.zip','*.7z'
$paths | Where-Object { Test-Path $_ } | ForEach-Object {
  Get-ChildItem -Path $_ -Recurse -Force -File -Include $extensions -ErrorAction SilentlyContinue |
    Select-Object FullName,Length,CreationTime,LastWriteTime,@{N='SHA256';E={(Get-FileHash $_.FullName -Algorithm SHA256 -ErrorAction SilentlyContinue).Hash}}
}
```

### 防护、软件与网络痕迹

```powershell
# Defender检测和防火墙日志
Get-MpThreatDetection -ErrorAction SilentlyContinue | Select-Object InitialDetectionTime,ThreatName,Resources,ActionSuccess,DomainUser
Get-Content "$env:windir\System32\LogFiles\Firewall\pfirewall.log" -Tail 500 -ErrorAction SilentlyContinue

# 已安装软件
$uninstall = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
Get-ItemProperty $uninstall -ErrorAction SilentlyContinue | Where-Object DisplayName | Select-Object DisplayName,DisplayVersion,Publisher,InstallDate,InstallLocation

# DNS缓存、SMB映射、Recent
Get-DnsClientCache -ErrorAction SilentlyContinue | Select-Object Entry,RecordName,RecordType,Data,TimeToLive
Get-SmbMapping -ErrorAction SilentlyContinue | Select-Object LocalPath,RemotePath,UserName,Status
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Recent" -Force -ErrorAction SilentlyContinue | Select-Object Name,LastWriteTime,Length
```

### 安全事件与时间线

```powershell
$start = (Get-Date).AddDays(-7)
Get-WinEvent -FilterHashtable @{LogName='Security';Id=4624,4625,4648,4672,4688,4697,4720,4728,4732;StartTime=$start} -ErrorAction SilentlyContinue |
  Select-Object TimeCreated,Id,ProviderName,MachineName,Message
Get-WinEvent -FilterHashtable @{LogName='System';Id=7045;StartTime=$start} -ErrorAction SilentlyContinue |
  Select-Object TimeCreated,Id,ProviderName,MachineName,Message
Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-PowerShell/Operational';Id=4104;StartTime=$start} -ErrorAction SilentlyContinue |
  Select-Object TimeCreated,Id,Message
```

事件ID速查：4624=登录成功 | 4625=登录失败 | 4672=特殊权限登录 | 4688=进程创建(需启用审计) | 4697/7045=服务安装 | 4720=用户创建 | 4728/4732=组成员变更 | 1102=审计日志清除

---

## 常见整改命令速查

### 禁用Guest账号

```powershell
Disable-LocalUser -Name "Guest"
```

### 关闭默认共享

```powershell
# 临时关闭
Get-SmbShare | Where-Object { $_.Name -match '\$$' } | ForEach-Object { Remove-SmbShare -Name $_.Name -Force }
# 永久关闭（注册表）
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters" -Name "AutoShareServer" -Value 0
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters" -Name "AutoShareWks" -Value 0
```

### 禁用危险服务

```powershell
Set-Service -Name "RemoteRegistry" -StartupType Disabled -Status Stopped
Set-Service -Name "TLNTSVR" -StartupType Disabled
```

### 启用UAC

```powershell
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableLUA" -Value 1
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "ConsentPromptBehaviorAdmin" -Value 2
```

---

## 预检命令

应急响应或安全检查开始前，先执行预检采集环境信息：

```powershell
# 系统基础信息
$os = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
[pscustomobject]@{
  HostName=$cs.Name;Domain=$cs.Domain;OSVersion=$os.Caption;
  Architecture=$os.OSArchitecture;BootTime=$os.LastBootUpTime;
  TimeZone=(Get-TimeZone).Id;LocalTime=(Get-Date);
  PSVersion=$PSVersionTable.PSVersion.ToString();
  ExecutionPolicy=(Get-ExecutionPolicy)
}
```

---

## 流程关联建议

发现可疑项后推荐排查方向：

| 发现项 | 推荐排查流程 |
|--------|------------|
| 可疑进程 | 进程服务排查→网络端口→文件持久化→深度后门检测→内存进程深度分析 |
| 可疑网络连接 | 网络端口→进程服务排查→网络隐蔽通道检测→日志事件分析 |
| 可疑账号 | 账号安全→日志事件分析→安全配置审计→远程访问配置 |
| 持久化后门 | 文件持久化→深度后门检测→日志事件分析→进程服务排查 |
| 性能异常/挖矿 | 性能异常分析→进程服务排查→网络端口→文件持久化 |

---

## 拆分文件说明

> 以下章节已拆分至独立文件，原文件与拆分文件内容完整保留（未删除任何内容）：

| 章节 | 拆分文件 |
|------|----------|
| 高级系统诊断命令库 | security-ops-guide-pt2.md |
| 电脑优化维护命令库 | security-ops-guide-pt3.md |
| 操作能力清单 | security-ops-guide-pt4.md |
| 高级系统诊断能力清单 | security-ops-guide-pt4.md |
| 电脑优化维护能力清单 | security-ops-guide-pt4.md |
| 脚本文件编码规范 | security-ops-guide-pt4.md |
| 管理员权限提权执行与内容披露 | security-ops-guide-pt4.md |