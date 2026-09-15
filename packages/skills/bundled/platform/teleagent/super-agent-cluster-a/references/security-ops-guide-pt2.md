---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '0b453ec5-ee1a-49ec-8817-a574d4ce67dd'
  PropagateID: '0b453ec5-ee1a-49ec-8817-a574d4ce67dd'
  ReservedCode1: '8e6c6052-4974-48c9-ac1f-0bd3e65647ba'
  ReservedCode2: '8e6c6052-4974-48c9-ac1f-0bd3e65647ba'
---

# 系统运维操作指南（补充）

> 从 security-ops-guide.md 拆分。

## 高级系统诊断命令库

[Agent-运维型]执行6类高级系统诊断时使用的完整PowerShell命令库。所有命令均为只读查询（除系统修复类须确认后执行），免确认直接执行。

### 健康等级标注规范

系统诊断结果必须标注健康等级（与安全检查威胁等级独立判定，不混淆）：

| 等级 | 标记 | 判定条件 | 处置要求 |
|------|------|---------|---------|
| 健康 | 🟢 | 所有指标在正常范围内 | 维持现状，纳入基线跟踪 |
| 警告 | 🟡 | 指标偏离正常范围但未达危险阈值 | 给出优化建议，询问是否执行修复 |
| 异常 | 🔴 | 指标达到危险阈值或发现严重故障 | 立即给出修复方案，⛔须用户确认后执行修复 |

---

### 诊断1：深度系统诊断

#### 蓝屏Dump分析

```powershell
# 检查是否有内存转储文件
$dumpPaths = "$env:WINDIR\Minidump","$env:WINDIR\MEMORY.DMP"
$dumpPaths | Where-Object { Test-Path $_ } | ForEach-Object {
  Get-ChildItem $_ -File -ErrorAction SilentlyContinue | Select-Object Name,Length,LastWriteTime
}

# 从系统事件日志读取BugCheck（蓝屏）记录
Get-WinEvent -FilterHashtable @{LogName='System';Id=1001;ProviderName='Microsoft-Windows-WER-SystemErrorReporting'} -MaxEvents 20 -ErrorAction SilentlyContinue |
  Select-Object TimeCreated,@{N='BugCheckCode';E={$_.Properties[0].Value}},@{N='Parameters';E={($_.Properties[1..5] | ForEach-Object {$_.Value}) -join ', '}}
```

#### 系统可靠性指数

```powershell
# 获取系统稳定性指数（1-10分，越低越不稳定）
Get-CimInstance Win32_ReliabilityStabilityMetrics -ErrorAction SilentlyContinue |
  Sort-Object TimeGenerated -Descending |
  Select-Object -First 7 TimeGenerated,SystemStabilityIndex |
  ForEach-Object {
    $level = if ($_.SystemStabilityIndex -ge 8) { '🟢健康' } elseif ($_.SystemStabilityIndex -ge 6) { '🟡警告' } else { '🔴异常' }
    [pscustomobject]@{Date=$_.TimeGenerated.ToString('yyyy-MM-dd');StabilityIndex=$_.SystemStabilityIndex;HealthLevel=$level}
  }
```

#### SMART磁盘健康

```powershell
# 磁盘SMART健康状态
Get-PhysicalDisk | ForEach-Object {
  $health = $_.HealthStatus
  $level = if ($health -eq 'Healthy') { '🟢健康' } elseif ($health -eq 'Warning') { '🟡警告' } else { '🔴异常' }
  [pscustomobject]@{Device=$_.DeviceId;FriendlyName=$_.FriendlyName;MediaType=$_.MediaType;HealthStatus=$health;OperationalStatus=$_.OperationalStatus;Size_GB=[math]::Round($_.Size/1GB,1);HealthLevel=$level}
}

# 磁盘可靠性计数器
Get-CimInstance Win32_DiskDrive | Select-Object Model,Status,InterfaceType,Size,Partitions,SerialNumber

# 存储可靠性历史（Reallocated Sector Count等关键指标）
Get-StorageReliabilityCounter -ErrorAction SilentlyContinue | Select-Object DeviceId,Temperature,ReadErrorsTotal,WriteErrorsTotal,SpinRetryCount,PowerCycleCount
```

#### 驱动签名排查

```powershell
# 列出所有未签名或签名无效的驱动
Get-CimInstance Win32_PnPSignedDriver -ErrorAction SilentlyContinue |
  Where-Object { $_.DriverClass -ne $null } |
  ForEach-Object {
    $sig = Get-AuthenticodeSignature -FilePath $_.DriverClass -ErrorAction SilentlyContinue
    if ($sig -and $sig.Status -ne 'Valid') {
      [pscustomobject]@{DeviceName=$_.DeviceName;DriverVersion=$_.DriverVersion;DriverProvider=$_.DriverProviderName;SignatureStatus=$sig.Status;InfName=$_.InfName}
    }
  }
```

---

### 诊断2：性能根因分析

#### CPU瓶颈分析

```powershell
# CPU总体使用率+逻辑核心数
$cpu = Get-CimInstance Win32_Processor
$load = $cpu.LoadPercentage
$level = if ($load -lt 80) { '🟢健康' } elseif ($load -lt 95) { '🟡警告' } else { '🔴异常' }
[pscustomobject]@{CPUName=$cpu.Name;Cores=$cpu.NumberOfCores;LogicalCores=$cpu.NumberOfLogicalProcessors;CurrentLoadPercent=$load;HealthLevel=$level}

# Top 10 CPU消耗进程
Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 Name,Id,CPU,@{N='Memory_MB';E={[math]::Round($_.WorkingSet64/1MB,1)}},Path
```

#### 磁盘IO瓶颈分析

```powershell
# 磁盘队列长度（>2=警告，>4=异常）
Get-CimInstance Win32_PerfFormattedData_PerfDisk_PhysicalDisk -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -ne '_Total' } |
  ForEach-Object {
    $ql = $_.CurrentDiskQueueLength
    $level = if ($ql -le 2) { '🟢健康' } elseif ($ql -le 4) { '🟡警告' } else { '🔴异常' }
    [pscustomobject]@{Disk=$_.Name;QueueLength=$ql;PctDiskTime=$_.PercentDiskTime;AvgReadBytes=$_.AvgDiskBytesPerRead;AvgWriteBytes=$_.AvgDiskBytesPerWrite;HealthLevel=$level}
  }

# 磁盘响应时间（>25ms=警告，>50ms=异常）
Get-CimInstance Win32_PerfFormattedData_PerfDisk_PhysicalDisk -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -ne '_Total' } |
  Select-Object Name,@{N='AvgDiskSecPerRead_ms';E={[math]::Round($_.AvgDisksecPerRead*1000,2)}},@{N='AvgDiskSecPerWrite_ms';E={[math]::Round($_.AvgDisksecPerWrite*1000,2)}}
```

#### 内存使用分析

```powershell
# 内存总览+可用率
$os = Get-CimInstance Win32_OperatingSystem
$totalGB = [math]::Round($os.TotalVisibleMemorySize/1MB,1)
$freeGB = [math]::Round($os.FreePhysicalMemory/1MB,1)
$usedPct = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize * 100,1)
$level = if ($usedPct -lt 90) { '🟢健康' } elseif ($usedPct -lt 95) { '🟡警告' } else { '🔴异常' }
[pscustomobject]@{Total_GB=$totalGB;Available_GB=$freeGB;Used_percent=$usedPct;HealthLevel=$level}

# Top 10内存消耗进程
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 Name,Id,@{N='Memory_MB';E={[math]::Round($_.WorkingSet64/1MB,1)}}

# 页面文件使用情况
Get-CimInstance Win32_PageFileUsage | Select-Object Name,AllocatedBaseSize,CurrentUsage,PeakUsage
```

#### 网络性能分析

```powershell
# 网络接口流量与错误
Get-CimInstance Win32_PerfFormattedData_Tcpip_NetworkInterface -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -notmatch 'Loopback|isatap' } |
  Select-Object Name,BytesReceivedPersec,BytesSentPersec,PacketsReceivedErrors,PacketsOutboundErrors,OutputQueueLength

# TCP连接状态分布
Get-NetTCPConnection | Group-Object State | Select-Object Name,Count | Sort-Object Count -Descending
```

#### 综合性能计数器快照

```powershell
# 一键采集关键性能计数器（60秒采样）
$counters = '\Processor(_Total)\% Processor Time','\Memory\Available MBytes','\PhysicalDisk(_Total)\Avg. Disk Queue Length','\PhysicalDisk(_Total)\Avg. Disk sec/Transfer','\Network Interface(*)\Bytes Total/sec'
Get-Counter -Counter $counters -SampleInterval 2 -MaxSamples 3 -ErrorAction SilentlyContinue |
  ForEach-Object { $_.CounterSamples } |
  Select-Object Path,CookedValue
```

---

### 诊断3：系统修复与恢复（⛔须逐项确认后执行）

#### SFC系统文件检查

```powershell
# 扫描并修复系统文件完整性（须确认，执行时间约15-30分钟）
sfc /scannow

# 仅扫描不修复
sfc /verifyonly
```

#### DISM组件修复

```powershell
# 修复Windows组件存储（须确认）
DISM /Online /Cleanup-Image /CheckHealth
DISM /Online /Cleanup-Image /ScanHealth
DISM /Online /Cleanup-Image /RestoreHealth

# 内网环境（WSUS源不可达时可能失败，须说明）
# DISM /Online /Cleanup-Image /RestoreHealth /Source:WIM:X:\sources\install.wim:1 /LimitAccess
```

#### 系统还原点管理

```powershell
# 查看现有还原点（只读）
Get-ComputerRestorePoint -ErrorAction SilentlyContinue | Select-Object SequenceNumber,Description,CreationTime,EventType

# 检查系统还原是否启用
$sr = Get-CimInstance Win32_SystemRestore -ErrorAction SilentlyContinue
if ($sr) { "系统还原已启用，还原点数：$($sr.Count)" } else { "系统还原可能未启用" }
```

#### Windows更新重置

```powershell
# 重置Windows更新组件（须确认，会停止更新服务）
# Stop-Service -Name wuauserv -Force
# Stop-Service -Name cryptSvc -Force
# Stop-Service -Name bits -Force
# Stop-Service -Name msiserver -Force
# Remove-Item "$env:windir\SoftwareDistribution\Download\*" -Recurse -Force -ErrorAction SilentlyContinue
# Start-Service -Name wuauserv
# Start-Service -Name cryptSvc
# Start-Service -Name bits
# Start-Service -Name msiserver
# 上述命令须用户明确确认后执行
```

#### 引导配置检查（只读）

```powershell
# 查看引导配置
bcdedit /enum

# 检查引导管理器超时
bcdedit /enum '{bootmgr}' | Select-String 'timeout'
```

---

### 诊断4：注册表深度审计

#### LSA保护状态

```powershell
# LSA RunAsPPL（受保护进程轻量级）
$lsa = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' -Name 'RunAsPPL' -ErrorAction SilentlyContinue
if ($lsa.RunAsPPL -eq 1) { '🟢LSA保护已启用' } else { '🟡LSA保护未启用，建议开启' }

# LSA脚本鉴权
$lsaCfg = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' -ErrorAction SilentlyContinue
[pscustomobject]@{RunAsPPL=$lsaCfg.RunAsPPL;SCENoApplyLegacyAuditPolicy=$lsaCfg.SCENoApplyLegacyAuditPolicy;AuditBaseObjects=$lsaCfg.AuditBaseObjects;RestrictAnonymous=$lsaCfg.RestrictAnonymous;EveryoneIncludesAnonymous=$lsaCfg.EveryoneIncludesAnonymous}
```

#### WDigest凭据缓存（明文密码风险）

```powershell
# UseLogonCredential=1表示明文密码存储在内存中（高风险）
$wdigest = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest' -Name 'UseLogonCredential' -ErrorAction SilentlyContinue
if ($wdigest.UseLogonCredential -eq 1) { '🔴WDigest明文凭据缓存已启用，高危！建议设为0' } else { '🟢WDigest明文凭据缓存已禁用' }
```

#### Credential Guard状态

```powershell
# 查看Credential Guard配置
$cg = Get-CimInstance Win32_DeviceGuard -Namespace 'root\Microsoft\Windows\DeviceGuard' -ErrorAction SilentlyContinue
if ($cg) {
  $running = $cg.SecurityServicesRunning
  $level = if ($running -contains 1 -or $running -contains 2) { '🟢Credential Guard运行中' } else { '🟡Credential Guard未运行，建议启用' }
  [pscustomobject]@{VirtualizationBasedSecurity=$cg.VirtualizationBasedSecurityStatus;SecurityServicesConfigured=$cg.SecurityServicesConfigured;SecurityServicesRunning=$cg.SecurityServicesRunning;HealthLevel=$level}
}
```

#### SMB签名配置

```powershell
# 检查SMB签名是否启用
$smbClient = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters' -Name 'RequireSecuritySignature' -ErrorAction SilentlyContinue
$smbServer = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters' -Name 'RequireSecuritySignature' -ErrorAction SilentlyContinue
$clientSig = if ($smbClient.RequireSecuritySignature -eq 1) { '已启用' } else { '未启用' }
$serverSig = if ($smbServer.RequireSecuritySignature -eq 1) { '已启用' } else { '未启用' }
$level = if ($smbClient.RequireSecuritySignature -eq 1 -and $smbServer.RequireSecuritySignature -eq 1) { '🟢' } else { '🟡' }
"$level SMB签名 - 客户端: $clientSig | 服务端: $serverSig"
```

#### 综合注册表安全审计

```powershell
# 一次性检查所有关键注册表安全项
$audit = @{}

# UAC
$uac = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' -ErrorAction SilentlyContinue
$audit['UAC_EnableLUA'] = if ($uac.EnableLUA -eq 1) { '🟢已启用' } else { '🔴未启用' }

# WDigest
$wdf = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest' -ErrorAction SilentlyContinue
$audit['WDigest_UseLogonCredential'] = if ($wdf.UseLogonCredential -eq 1) { '🔴已启用(高危)' } else { '🟢已禁用' }

# LSA RunAsPPL
$lsa = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' -ErrorAction SilentlyContinue
$audit['LSA_RunAsPPL'] = if ($lsa.RunAsPPL -eq 1) { '🟢已启用' } else { '🟡未启用' }

# Anonymous Access
$audit['LSA_RestrictAnonymous'] = if ($lsa.RestrictAnonymous -eq 1) { '🟢已限制' } else { '🟡未限制' }

# SMB签名
$smbS = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters' -ErrorAction SilentlyContinue
$audit['SMB_RequireSignature_Server'] = if ($smbS.RequireSecuritySignature -eq 1) { '🟢已启用' } else { '🟡未启用' }

# AppInit_DLLs
$appinit = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Windows' -Name 'AppInit_DLLs' -ErrorAction SilentlyContinue
$audit['AppInit_DLLs'] = if ($appinit.AppInit_DLLs) { '🟡存在AppInit_DLLs注入' } else { '🟢无注入' }

# 输出审计结果表
$audit.GetEnumerator() | ForEach-Object { [pscustomobject]@{CheckItem=$_.Key;Result=$_.Value} } | Format-Table -AutoSize
```

---

### 诊断5：事件日志全面分析

#### System日志故障事件

```powershell
# 近7天System日志Error+Critical事件统计
$start = (Get-Date).AddDays(-7)
Get-WinEvent -FilterHashtable @{LogName='System';Level=1,2;StartTime=$start} -ErrorAction SilentlyContinue |
  Group-Object Id,ProviderName |
  Sort-Object Count -Descending |
  Select-Object -First 15 @{N='EventId';E={($_.Name -split ',')[0]}},@{N='Provider';E={($_.Name -split ',')[1]}},Count |
  ForEach-Object {
    $level = if ($_.Count -gt 200) { '🔴异常' } elseif ($_.Count -gt 50) { '🟡警告' } else { '🟢正常' }
    [pscustomobject]@{EventId=$_.EventId;Provider=$_.Provider;Count=$_.Count;HealthLevel=$level}
  }
```

#### Application日志故障事件

```powershell
# 近7天Application日志Error+Critical事件统计
Get-WinEvent -FilterHashtable @{LogName='Application';Level=1,2;StartTime=$start} -ErrorAction SilentlyContinue |
  Group-Object Id,ProviderName |
  Sort-Object Count -Descending |
  Select-Object -First 15 @{N='EventId';E={($_.Name -split ',')[0]}},@{N='Provider';E={($_.Name -split ',')[1]}},Count |
  ForEach-Object {
    $level = if ($_.Count -gt 200) { '🔴异常' } elseif ($_.Count -gt 50) { '🟡警告' } else { '🟢正常' }
    [pscustomobject]@{EventId=$_.EventId;Provider=$_.Provider;Count=$_.Count;HealthLevel=$level}
  }
```

#### 服务崩溃历史

```powershell
# 近7天服务崩溃记录（Event ID 7031/7034）
Get-WinEvent -FilterHashtable @{LogName='System';Id=7031,7034;StartTime=$start} -ErrorAction SilentlyContinue |
  Select-Object TimeCreated,Id,@{N='ServiceName';E={($_.Message -split "'")[1]}},Message -First 30
```

#### 应用程序挂起/崩溃

```powershell
# 近7天Application Hang和Crash记录（Event ID 1000/1002）
Get-WinEvent -FilterHashtable @{LogName='Application';Id=1000,1002;StartTime=$start} -ErrorAction SilentlyContinue |
  Select-Object TimeCreated,Id,@{N='AppName';E={($_.Message -split ',')[0]}},Message -First 30
```

#### 关键事件ID速查表

| 事件ID | 日志 | 含义 | 健康影响 |
|--------|------|------|---------|
| 7031 | System | 服务意外终止 | 🔴关键服务崩溃 |
| 7034 | System | 服务意外终止（无操作） | 🟡服务不稳定 |
| 7045 | System | 新服务安装 | 需确认是否授权 |
| 1001 | System | BugCheck（蓝屏） | 🔴系统蓝屏 |
| 1000 | Application | 应用程序崩溃 | 🟡应用不稳定 |
| 1002 | Application | 应用程序挂起 | 🟡应用卡死 |
| 41 | System | 内核电源事件（异常关机） | 🟡非正常关机 |
| 6008 | System | 意外关机记录 | 🟡非正常关机 |
| 51 | System | 磁盘错误 | 🔴磁盘可能故障 |

---

### 诊断6：电源管理诊断

#### 电源计划分析

```powershell
# 当前电源计划
powercfg /getactivescheme

# 所有电源计划列表
powercfg /list

# 当前电源计划详细设置（超时/亮度/睡眠等）
powercfg /query
```

#### 睡眠唤醒失败诊断

```powershell
# 最近唤醒源
powercfg /lastwake

# 唤醒历史（近7天）
powercfg /waketimers

# 睡眠失败原因分析
powercfg /energy /duration 60 /output "$env:TEMP\power_energy_report.html"
# 生成能效报告，60秒采样，输出HTML文件路径

# 查看设备唤醒权限（哪些设备可以唤醒系统）
powercfg /devicequery wake_armed
```

#### 电池健康（笔记本适用）

```powershell
# 电池信息
Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue | Select-Object Name,EstimatedChargeRemaining,BatteryStatus,DesignVoltage

# 电池详细报告
powercfg /batteryreport /output "$env:TEMP\battery_report.html"
# 生成电池健康报告HTML

# 生成电池报告后检查路径
if (Test-Path "$env:TEMP\battery_report.html") { "电池报告已生成" }
```

#### 能效问题排查

```powershell
# 能效报告中的常见问题分类
$report = "$env:TEMP\power_energy_report.html"
if (Test-Path $report) {
  $content = Get-Content $report -Raw -ErrorAction SilentlyContinue
  $errors = ([regex]::Matches($content, 'Error:.+')).Count
  $warnings = ([regex]::Matches($content, 'Warning:.+')).Count
  $level = if ($errors -gt 5) { '🔴异常' } elseif ($errors -gt 0 -or $warnings -gt 3) { '🟡警告' } else { '🟢健康' }
  [pscustomobject]@{ReportPath=$report;Errors=$errors;Warnings=$warnings;HealthLevel=$level}
}
```

---

### 高级诊断决策树

发现诊断异常后的推荐排查路径：

| 诊断发现 | 健康等级 | 推荐排查路径 |
|---------|---------|------------|
| 蓝屏频繁 | 🔴 | 蓝屏dump分析→驱动签名排查→系统修复(SFC/DISM)→内存检查→硬件排查 |
| 可靠性指数低 | 🔴 | 事件日志分析→服务崩溃历史→系统修复→更新修复 |
| SMART磁盘警告 | 🔴 | 磁盘健康确认→数据备份建议→磁盘更换评估 |
| CPU持续高负载 | 🟡 | Top进程分析→进程树溯源→安全检查(排除挖矿)→性能优化 |
| 磁盘IO瓶颈 | 🟡 | 磁盘队列分析→Top IO进程→碎片整理评估→SSD升级建议 |
| 内存不足 | 🟡 | Top内存进程→页面文件检查→内存释放→内存升级建议 |
| WDigest凭据缓存 | 🔴 | 立即建议设置UseLogonCredential=0→检查是否有凭据窃取工具→安全检查 |
| 服务频繁崩溃 | 🔴 | 服务崩溃历史→事件日志分析→服务依赖检查→重装服务 |
| 唤醒失败率高 | 🟡 | 能效报告→唤醒源排查→设备驱动更新→电源计划优化 |
| 未签名驱动 | 🟡 | 驱动签名确认→驱动更新→WHQL签名验证 |

---