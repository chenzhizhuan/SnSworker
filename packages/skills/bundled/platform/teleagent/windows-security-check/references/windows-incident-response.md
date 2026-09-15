# Windows 应急排查参考

本参考用于授权 Windows 主机的证据采集。默认只读。将每次命令的执行时间、主机名和原始输出保存到独立证据目录；不要把工具输出或进程名直接当作恶意结论。

## 1. 用户账户与组

```powershell
Get-LocalUser | Select-Object Name,SID,Enabled,LastLogon,PasswordLastSet,Description
Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction SilentlyContinue | Select-Object Name,SID,ObjectClass,PrincipalSource
Get-CimInstance Win32_UserAccount -Filter 'LocalAccount=True' | Select-Object Name,SID,Disabled,Lockout,PasswordRequired,Status
```

- “隐藏用户”应以 SID、账户类型、`ProfileList`、本地组成员和登录事件交叉验证；UI 中未展示不代表恶意。
- “克隆账户”应检查相近名称、异常 SID/描述、创建或首次登录时间、管理员组成员资格和业务授权。不要仅因名称相似判定违规。

## 2. 进程树、DLL、签名与哈希

```powershell
# 进程树基础数据
Get-CimInstance Win32_Process | Select-Object Name,ProcessId,ParentProcessId,ExecutablePath,CommandLine,CreationDate

# 可执行文件签名与 SHA-256；路径为空或拒绝访问需记录为受限
Get-CimInstance Win32_Process | Where-Object ExecutablePath | ForEach-Object {
  $sig = Get-AuthenticodeSignature -FilePath $_.ExecutablePath -ErrorAction SilentlyContinue
  $owner = Invoke-CimMethod -InputObject $_ -MethodName GetOwner -ErrorAction SilentlyContinue
  [pscustomobject]@{Name=$_.Name;PID=$_.ProcessId;PPID=$_.ParentProcessId;Owner=("$($owner.Domain)\\$($owner.User)");Path=$_.ExecutablePath;CommandLine=$_.CommandLine;Signature=$sig.Status;Signer=$sig.SignerCertificate.Subject;SHA256=(Get-FileHash $_.ExecutablePath -Algorithm SHA256 -ErrorAction SilentlyContinue).Hash}
}

# 指定 PID 的已加载模块；保护进程或跨位数查询可能受限
Get-Process -Id <PID> -Module -ErrorAction SilentlyContinue | Select-Object ModuleName,FileName,FileVersionInfo
```

- 重点关注用户可写目录启动的进程、异常父子关系、无签名/签名失效二进制、伪装系统名称和可疑命令行；任一单独信号通常不足以确认恶意。
- 在线信誉查询默认仅查询 SHA-256，且必须先获得用户确认并说明所用服务。绝不默认上传文件、命令行、内存或内部路径。

## 3. TCP/UDP 网络连接

```powershell
# 已建立 TCP 连接与进程映射
Get-NetTCPConnection -State Established | ForEach-Object {
  $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
  [pscustomobject]@{Local="$($_.LocalAddress):$($_.LocalPort)";Remote="$($_.RemoteAddress):$($_.RemotePort)";State=$_.State;PID=$_.OwningProcess;Process=$p.ProcessName;Path=$p.Path}
}

# TCP 监听与 UDP 端点
Get-NetTCPConnection -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess
Get-NetUDPEndpoint | Select-Object LocalAddress,LocalPort,OwningProcess

# 快速过滤：指定 PID、远端 IP 或非本地地址
Get-NetTCPConnection | Where-Object { $_.OwningProcess -eq <PID> }
Get-NetTCPConnection | Where-Object { $_.RemoteAddress -eq '<IP>' }
Get-NetTCPConnection -State Established | Where-Object { $_.RemoteAddress -notmatch '^(127\\.|::1$|0\.0\.0\.0$)' }
```

- 记录五元组、PID、映像路径、账户与连接时间。公网 IP、CDN、代理和企业 VPN 需结合资产/代理日志确认；不要仅凭地理位置判恶意。

## 4. 持久化：启动项、IFEO、服务和计划任务

```powershell
# Run/RunOnce 与启动文件夹
$runKeys = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run','HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce'
$runKeys | ForEach-Object { Get-ItemProperty -Path $_ -ErrorAction SilentlyContinue }
Get-ChildItem 'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp',"$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup" -Force -ErrorAction SilentlyContinue

# IFEO 调试器与 SilentProcessExit；存在值不一定恶意，需核对调试/运维用途
Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options' -ErrorAction SilentlyContinue | ForEach-Object { Get-ItemProperty $_.PSPath | Where-Object { $_.Debugger -or $_.GlobalFlag } }
Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SilentProcessExit' -ErrorAction SilentlyContinue | ForEach-Object { Get-ItemProperty $_.PSPath }

# 服务与计划任务
Get-CimInstance Win32_Service | Select-Object Name,DisplayName,State,StartMode,StartName,PathName,ProcessId
Get-ScheduledTask | Where-Object State -ne 'Disabled' | ForEach-Object { [pscustomobject]@{TaskName=$_.TaskName;TaskPath=$_.TaskPath;State=$_.State;Actions=(($_.Actions | ForEach-Object { "$($_.Execute) $($_.Arguments)" }) -join '; ');Triggers=($_.Triggers | ForEach-Object { $_.CimClass.CimClassName }) -join '; '} }
```

- 对服务检查二进制路径是否无引号、位于用户可写路径、签名异常或由异常账户运行。
- 对任务同时记录任务 XML、触发器、执行命令、作者、最近运行信息；Microsoft 任务不能因路径属于 Microsoft 就直接排除。

### 扩展持久化与远程访问

```powershell
# 32 位 Run 键、策略 Run 键、Winlogon 和登录脚本
$keys = 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\RunOnce','HKCU:\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run','HKLM:\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run','HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon','HKCU:\Environment'
$keys | ForEach-Object { Get-ItemProperty -Path $_ -ErrorAction SilentlyContinue }

# DLL/执行链劫持及应用兼容性持久化
reg query 'HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Windows' /v AppInit_DLLs
reg query 'HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\AppCertDlls'
reg query 'HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Custom' /s
reg query 'HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\InstalledSDB' /s
reg query 'HKLM\Software\Classes\exefile\shell\open\command'

# RDP、LSA 包、WDigest 与受限管理员模式
reg query 'HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server' /v fDenyTSConnections
reg query 'HKLM\SYSTEM\CurrentControlSet\Control\Lsa' /v 'Security Packages'
reg query 'HKLM\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest' /v UseLogonCredential
reg query 'HKLM\SYSTEM\CurrentControlSet\Control\Lsa' /v DisableRestrictedAdmin
```

- `Winlogon` 仅重点检查 `Userinit`、`Shell` 和 `AutoAdminLogon`，`HKCU:\Environment` 重点检查 `UserInitMprLogonScript`。
- COM 劫持（`HKCU\Software\Classes\CLSID`）、AppInit DLL、AppCert DLL、Shim 数据库和文件关联劫持信噪比较高。仅在发现可疑 CLSID/路径时，记录其完整键、DLL 路径、签名、哈希和关联进程，避免导出整个用户注册表。
- `UseLogonCredential=1`、异常 SSP/LSA 包或未授权 RDP 配置属于高优先级核实项；读取 RDP 客户端历史会暴露用户使用痕迹，需按用户指定范围执行。

## 5. 文件落地排查

```powershell
$paths = 'C:\Windows\Temp','C:\temp','C:\Users\Public',"$env:APPDATA","$env:LOCALAPPDATA",'C:\ProgramData'
$extensions = '*.exe','*.dll','*.sys','*.ps1','*.psm1','*.bat','*.cmd','*.vbs','*.js','*.jse','*.hta','*.lnk','*.zip','*.7z'
$paths | Where-Object { Test-Path $_ } | ForEach-Object {
  Get-ChildItem -Path $_ -Recurse -Force -File -Include $extensions -ErrorAction SilentlyContinue |
    Select-Object FullName,Length,CreationTime,LastWriteTime,@{N='SHA256';E={(Get-FileHash $_.FullName -Algorithm SHA256 -ErrorAction SilentlyContinue).Hash}}
}
```

- 支持用户提供的额外路径；大目录或网络盘先限定深度、时间范围或扩展名，避免影响终端性能。
- 对可疑文件先取哈希、签名、关联进程/持久化和时间线；隔离或删除必须单独授权。

## 6. 防护、软件与网络使用痕迹

```powershell
# Defender 近期检测和防火墙日志（存在时仅读取）
Get-MpThreatDetection -ErrorAction SilentlyContinue | Select-Object InitialDetectionTime,ThreatName,Resources,ActionSuccess,DomainUser
Get-Content "$env:windir\System32\LogFiles\Firewall\pfirewall.log" -Tail 500 -ErrorAction SilentlyContinue

# 已安装软件：仅读取卸载注册表，避免 Win32_Product 的 MSI 自修复副作用
$uninstall = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
Get-ItemProperty $uninstall -ErrorAction SilentlyContinue | Where-Object DisplayName | Select-Object DisplayName,DisplayVersion,Publisher,InstallDate,InstallLocation

# 当前 DNS 缓存、活动网络映射和当前用户近期使用痕迹
Get-DnsClientCache -ErrorAction SilentlyContinue | Select-Object Entry,RecordName,RecordType,Data,TimeToLive
Get-SmbMapping -ErrorAction SilentlyContinue | Select-Object LocalPath,RemotePath,UserName,Status
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Recent" -Force -ErrorAction SilentlyContinue | Select-Object Name,LastWriteTime,Length
```

- Defender 检测、DNS 缓存、网络映射、Recent、浏览器/CertUtil URL 缓存均属时间敏感或隐私相关证据。先记录采集范围和时间，必要时只导出元数据；不要默认上传或共享原始内容。
- 进一步查看 SMB 审计、RDP 连接、Task Scheduler、Defender 和 Sysmon 原始事件时，优先导出原始 `.evtx`，保留哈希和采集时间，避免只保留格式化文本。

## 7. 安全事件与时间线

```powershell
$start = (Get-Date).AddDays(-7)
Get-WinEvent -FilterHashtable @{LogName='Security';Id=4624,4625,4648,4672,4688,4697,4720,4728,4732;StartTime=$start} -ErrorAction SilentlyContinue |
  Select-Object TimeCreated,Id,ProviderName,MachineName,Message
Get-WinEvent -FilterHashtable @{LogName='System';Id=7045;StartTime=$start} -ErrorAction SilentlyContinue |
  Select-Object TimeCreated,Id,ProviderName,MachineName,Message
Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-PowerShell/Operational';Id=4104;StartTime=$start} -ErrorAction SilentlyContinue |
  Select-Object TimeCreated,Id,Message
```

- 4624/4625 为登录成功/失败，4672 为特殊权限登录，4688 为进程创建（需先启用审计），4697/7045 与服务安装相关，4720/4728/4732 与账户和组成员变更相关。
- 事件字段应从 XML 提取并按系统版本验证，避免依赖中文/英文消息位置。日志缺失、被覆盖或未启用应标为取证盲区。

## 8. 原始证据保全（深度动作）

经用户确认后，将原始日志和执行痕迹复制到用户指定的证据目录，并计算 SHA-256。优先收集与事件相关的最小集合：`Security`、`System`、`Application`、PowerShell Operational、TaskScheduler Operational、Defender Operational、TerminalServices Operational 和 Sysmon Operational（若存在）。按需补充 Prefetch、SRUM、BAM、ShimCache、MUICache 等执行痕迹。

- 导出前确认可用磁盘空间、目标目录访问控制和保留期限；不要覆盖已有证据文件。
- `SAM` 与 `SECURITY` hive 可能含有凭据衍生材料，默认不导出、不解析；只有用户明确授权的专项取证流程才可处理，并须采取加密存储与链路记录。
- 原始工件需要与时区、系统启动时间、事件日志保留策略和采集工具版本一并记录，否则不能单独作为时间线结论。

## 9. 内存特征威胁检索（深度动作）

仅在用户明确授权、具备管理员权限且说明性能/稳定性影响后执行。优先使用经批准的 EDR 或取证工具，对进程内存执行 YARA/IOC 规则匹配；不要自行注入 DLL、修改内存、转储或上传内存。记录工具版本、规则哈希、目标 PID、匹配偏移和采集时间。规则命中是进一步取证线索，需结合模块、网络、文件和行为证据确认。
