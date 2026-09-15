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

# 系统运维操作指南（补充2）

> 从 security-ops-guide.md 拆分。

## 电脑优化维护命令库

[Agent-运维型]执行6类电脑优化维护时使用的完整PowerShell命令库。分析/诊断为只读操作免确认；清理/修改/重置类操作须逐项确认后执行。

### 优化等级标注规范

优化建议须标注优化等级（与诊断健康等级、安全检查威胁等级三者独立判定）：

| 等级 | 标记 | 判定条件 | 处置要求 |
|------|------|---------|---------|
| 已优化 | 🟢 | 当前配置已最优或指标在正常范围 | 维持现状，纳入基线跟踪 |
| 建议优化 | 🟡 | 指标偏离最优范围但未达危险阈值 | 给出优化建议，询问是否执行优化 |
| 需要优化 | 🔴 | 指标达到危险阈值或配置严重不合理 | 给出优化方案，⛔须用户确认后执行 |

---

### 优化1：磁盘空间深度清理（⛔清理操作须逐项确认）

#### 磁盘空间总览

```powershell
# 各分区空间使用情况
Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | ForEach-Object {
  $totalGB = [math]::Round($_.Size/1GB,1)
  $freeGB = [math]::Round($_.FreeSpace/1GB,1)
  $usedPct = if ($_.Size -gt 0) { [math]::Round(($_.Size - $_.FreeSpace) / $_.Size * 100,1) } else { 0 }
  $level = if ($freeGB -lt 5) { '🔴需要清理' } elseif ($freeGB -lt 20 -or $usedPct -gt 85) { '🟡建议清理' } else { '🟢空间充足' }
  [pscustomobject]@{Drive=$_.DeviceID;Total_GB=$totalGB;Free_GB=$freeGB;Used_percent=$usedPct;OptLevel=$level}
}
```

#### WinSxS组件存储分析

```powershell
# WinSxS组件存储大小分析（只读）
DISM /Online /Get-Packages /Format:Table | Out-Null
$winsxs = Get-ChildItem "$env:WINDIR\WinSxS" -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum
$winsxsGB = [math]::Round($winsxs.Sum/1GB,2)
$level = if ($winsxsGB -gt 10) { '🔴需要清理' } elseif ($winsxsGB -gt 5) { '🟡建议清理' } else { '🟢正常' }
"WinSxS组件存储: $winsxsGB GB - $level"

# 分析组件存储（推荐使用DISM内置命令，更准确）
# DISM /Online /AnalyzeComponentStore
# 该命令会输出：组件存储的实际大小、是否需要清理、推荐的清理操作
```

#### Windows Update缓存清理（须确认）

```powershell
# 扫描Windows Update缓存大小（只读）
$updateCache = "$env:WINDIR\SoftwareDistribution\Download"
if (Test-Path $updateCache) {
  $size = (Get-ChildItem $updateCache -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
  $sizeGB = [math]::Round($size/1GB,2)
  $level = if ($sizeGB -gt 3) { '🟡建议清理' } else { '🟢正常' }
  "Windows Update缓存: $sizeGB GB - $level"
}

# 清理Windows Update缓存（⛔须确认后执行）
# Stop-Service -Name wuauserv -Force -ErrorAction SilentlyContinue
# Stop-Service -Name bits -Force -ErrorAction SilentlyContinue
# Remove-Item "$env:WINDIR\SoftwareDistribution\Download\*" -Recurse -Force -ErrorAction SilentlyContinue
# Start-Service -Name wuauserv
# Start-Service -Name bits
```

#### 休眠文件管理（须确认）

```powershell
# 检查休眠文件状态（只读）
$hiberFile = "$env:SystemDrive\hiberfil.sys"
if (Test-Path $hiberFile) {
  $size = (Get-Item $hiberFile -Force).Length
  $sizeGB = [math]::Round($size/1GB,2)
  $level = if ($sizeGB -gt 4) { '🟡建议关闭休眠释放空间' } else { '🟢正常' }
  "休眠文件: $sizeGB GB - $level"
} else {
  "休眠文件不存在（已关闭休眠）- 🟢已优化"
}

# 关闭休眠释放空间（⛔须确认，执行后无法使用快速启动）
# powercfg /hibernate off
# 重新启用：
# powercfg /hibernate on
```

#### Windows.old清理（须确认）

```powershell
# 检查Windows.old是否存在（只读）
$oldDir = "$env:SystemDrive\Windows.old"
if (Test-Path $oldDir) {
  $size = (Get-ChildItem $oldDir -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
  $sizeGB = [math]::Round($size/1GB,2)
  $level = if ($sizeGB -gt 5) { '🟡建议清理' } else { '🟢正常' }
  "Windows.old: $sizeGB GB - $level"
} else {
  "Windows.old不存在 - 🟢已优化"
}

# 清理Windows.old（⛔须确认，清理后无法回退到旧系统版本）
# Take ownership + Remove-Item (管理员权限)
```

#### 系统还原点清理（须确认）

```powershell
# 查看还原点占用空间（只读）
vssadmin list shadowstorage 2>$null

# 清理旧还原点（⛔须确认，清理后无法恢复到该时间点）
# vssadmin delete shadows /for=$env:SystemDrive /oldest
# 或通过磁盘清理工具：
# cleanmgr /sageset:1 （设置选项后）
# cleanmgr /sagerun:1 （执行清理）
```

#### 交付优化缓存清理（须确认）

```powershell
# 交付优化缓存大小（只读，用于P2P更新分发）
$doCache = "$env:WINDIR\ServiceProfiles\NetworkService\AppData\Local\Microsoft\Windows\DeliveryOptimization\Cache"
if (Test-Path $doCache) {
  $size = (Get-ChildItem $doCache -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
  $sizeGB = [math]::Round($size/1GB,2)
  $level = if ($sizeGB -gt 2) { '🟡建议清理' } else { '🟢正常' }
  "交付优化缓存: $sizeGB GB - $level"
}
```

---

### 优化2：内存深度优化

#### 内存总览与泄漏检测

```powershell
# 内存总览
$os = Get-CimInstance Win32_OperatingSystem
$totalGB = [math]::Round($os.TotalVisibleMemorySize/1MB,1)
$freeGB = [math]::Round($os.FreePhysicalMemory/1MB,1)
$usedPct = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize * 100,1)
$level = if ($usedPct -gt 95) { '🔴需要优化' } elseif ($usedPct -gt 85) { '🟡建议优化' } else { '🟢已优化' }
[pscustomobject]@{Total_GB=$totalGB;Available_GB=$freeGB;Used_percent=$usedPct;OptLevel=$level}

# 检测疑似内存泄漏进程（工作集持续增长且不释放）
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 15 Name,Id,
  @{N='WorkingSet_MB';E={[math]::Round($_.WorkingSet64/1MB,1)}},
  @{N='PrivateMemory_MB';E={[math]::Round($_.PrivateMemorySize/1MB,1)}},
  @{N='VirtualMem_MB';E={[math]::Round($_.VirtualMemorySize64/1MB,1)}} |
  ForEach-Object {
    $leak = if ($_.WorkingSet_MB -gt 500 -and $_.PrivateMemory_MB -gt 500) { '🟡疑似泄漏' } else { '🟢正常' }
    [pscustomobject]@{Name=$_.Name;PID=$_.Id;WorkingSet_MB=$_.WorkingSet_MB;PrivateMem_MB=$_.PrivateMemory_MB;VirtualMem_MB=$_.VirtualMem_MB;LeakSuspect=$leak}
  }
```

#### 工作集分析

```powershell
# 进程工作集详情（物理内存实际占用）
Get-Process | Select-Object Name,Id,
  @{N='WorkingSet_MB';E={[math]::Round($_.WorkingSet64/1MB,1)}},
  @{N='PeakWorkingSet_MB';E={[math]::Round($_.PeakWorkingSet64/1MB,1)}},
  @{N='PagedMem_MB';E={[math]::Round($_.PagedMemorySize64/1MB,1)}},
  @{N='NonPagedMem_MB';E={[math]::Round($_.NonpagedSystemMemorySize64/1MB,1)}} |
  Sort-Object WorkingSet_MB -Descending | Select-Object -First 20

# 系统缓存与Standby内存
$memInfo = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
[pscustomobject]@{
  TotalPhysical_GB=[math]::Round($cs.TotalPhysicalMemory/1GB,1)
  FreePhysical_MB=[math]::Round($memInfo.FreePhysicalMemory/1KB,1)
  TotalVirtual_MB=[math]::Round($memInfo.TotalVirtualMemorySize/1KB,1)
  FreeVirtual_MB=[math]::Round($memInfo.FreeVirtualMemory/1KB,1)
}
```

#### 页面文件优化

```powershell
# 当前页面文件配置
Get-CimInstance Win32_PageFileSetting | Select-Object Name,InitialSize,MaximumSize
Get-CimInstance Win32_PageFileUsage | Select-Object Name,AllocatedBaseSize,CurrentUsage,PeakUsage

# 页面文件优化建议（自动管理模式检测）
$cs = Get-CimInstance Win32_ComputerSystem
$pf = Get-CimInstance Win32_PageFileUsage
if ($pf) {
  $ramGB = [math]::Round($cs.TotalPhysicalMemory/1GB,1)
  $pfAllocated = $pf.AllocatedBaseSize
  $ratio = [math]::Round($pfAllocated / $ramGB,2)
  $level = if ($ratio -gt 1.5) { '🟡页面文件过大，建议缩小' } elseif ($ratio -lt 0.5 -and $ramGB -lt 16) { '🟡页面文件偏小' } else { '🟢配置合理' }
  "物理内存: ${ramGB}GB | 页面文件: ${pfAllocated}MB | 比率: $ratio - $level"
} else {
  "页面文件可能被禁用或由系统自动管理"
}

# 自动管理检测
$auto = Get-CimInstance Win32_ComputerSystem -Property AutomaticManagedPagefile
if ($auto.AutomaticManagedPagefile) { "页面文件: 系统自动管理 - 🟢已优化" } else { "页面文件: 手动管理 - 检查配置是否合理" }
```

#### 内存释放操作（须确认）

```powershell
# 释放指定进程的工作集（⛔须确认，仅对非关键进程执行）
# Get-Process -Name "target_process" | ForEach-Object { $_.MinimizeWorkingSet() }
# 或者通过重启服务释放内存（须确认）

# 查看可释放内存的候选进程（只读分析）
Get-Process | Where-Object { $_.WorkingSet64 -gt 200MB -and $_.Name -notin @('System','Idle','smss','csrss','wininit','services','lsass','svchost') } |
  Select-Object Name,Id,@{N='WorkingSet_MB';E={[math]::Round($_.WorkingSet64/1MB,1)}} |
  Sort-Object WorkingSet_MB -Descending
```

---

### 优化3：启动优化

#### 开机时间测量

```powershell
# 上次启动时间
$os = Get-CimInstance Win32_OperatingSystem
$bootTime = $os.LastBootUpTime
$uptime = (Get-Date) - $bootTime
$uptimeHours = [math]::Round($uptime.TotalHours,1)
"上次开机时间: $($bootTime.ToString('yyyy-MM-dd HH:mm:ss')) | 已运行: ${uptimeHours}小时"

# 从事件日志获取开机速度（6005=开机启动，6006=关机，6009=系统启动信息）
$bootEvents = Get-WinEvent -FilterHashtable @{LogName='System';Id=6005;StartTime=(Get-Date).AddDays(-30)} -ErrorAction SilentlyContinue
if ($bootEvents) { "近30天开机次数: $($bootEvents.Count)" }

# 通过LastBootUpTime计算平均开机间隔
$boot6001 = Get-WinEvent -FilterHashtable @{LogName='System';Id=6013;StartTime=(Get-Date).AddDays(-7)} -ErrorAction SilentlyContinue
# Event 6013记录系统运行时间
```

#### 启动影响评级

```powershell
# 启动项详情+影响评级
$startupItems = Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location,User
$startupItems | ForEach-Object {
  $impact = if ($_.Command -match 'update|sync|cloud|oneDrive|dropbox') { '🟡中影响（同步类）' }
            elseif ($_.Command -match 'helper|tray|shortcut|launcher') { '🟢低影响（辅助类）' }
            else { '🟡需评估' }
  [pscustomobject]@{Name=$_.Name;Location=$_.Location;User=$_.User;Impact=$impact}
}

# 计数
$itemCount = ($startupItems | Measure-Object).Count
$level = if ($itemCount -gt 20) { '🔴启动项过多' } elseif ($itemCount -gt 15) { '🟡启动项偏多' } else { '🟢启动项正常' }
"启动项总数: $itemCount - $level"
```

#### 服务启动类型分析

```powershell
# 服务启动类型分布
Get-CimInstance Win32_Service | Group-Object StartMode | Select-Object Name,Count | Sort-Object Count -Descending

# 自动启动服务数量（开机即加载）
$autoServices = Get-CimInstance Win32_Service -Filter "StartMode='Auto'"
$autoCount = ($autoServices | Measure-Object).Count
$level = if ($autoCount -gt 60) { '🔴自动启动服务过多' } elseif ($autoCount -gt 40) { '🟡自动启动服务偏多' } else { '🟢正常' }
"自动启动服务: $autoCount 个 - $level"

# 延迟启动服务
$delayedAuto = Get-CimInstance Win32_Service -Filter "StartMode='Auto'" | Where-Object { $_.DelayedAutoStart -eq $true }
"延迟启动服务: $(($delayedAuto | Measure-Object).Count) 个"
```

#### 启动优化建议

```powershell
# 识别可延迟启动的自动服务（非关键服务建议改为延迟启动或手动）
$nonCriticalAuto = Get-CimInstance Win32_Service -Filter "StartMode='Auto' AND State='Running'" |
  Where-Object { $_.Name -match 'update|telemetry|diagnostic|cache|report|edge|chrome|adobe' } |
  Select-Object Name,DisplayName,State,StartMode
$nonCriticalAuto | ForEach-Object {
  [pscustomobject]@{Service=$_.Name;Display=$_.DisplayName;CurrentMode='Auto';SuggestedMode='Manual/Delayed';Reason='非关键服务，可延迟启动'}
}

# UEFI引导时间（仅适用于UEFI系统）
$bootMgr = bcdedit /enum '{bootmgr}' 2>$null
if ($bootMgr) {
  $timeout = ($bootMgr | Select-String 'timeout').ToString() -replace '.*timeout\s+',''
  $level = if ([int]$timeout -gt 10) { '🟡引导等待时间过长' } else { '🟢正常' }
  "引导管理器超时: ${timeout}秒 - $level"
}
```

---

### 优化4：系统服务优化

#### 非必要服务识别

```powershell
# 运行中的服务清单+安全等级评定
Get-CimInstance Win32_Service -Filter "State='Running'" | ForEach-Object {
  $safety = '需评估'
  $knownSafe = @('BITS','CoreMessagingRegistrar','CryptSvc','DcomLaunch','Dhcp','Dnscache','EventLog','EventSystem',
    'FontCache','LSM','MpsSvc','nsi','PlugPlay','Power','ProfSvc','RpcEptMapper','RpcSs','Schedule','SENS',
    'SystemEventsBroker','UserManager','Winmgmt','WinHttpAutoProxySvc','wuauserv','Audiosrv','BFE','WinDefend')
  $knownUnnecessary = @('WSearch','SysMain','DiagTrack','dmwappushservice','MapsBroker','RetailDemo','wisvc',
    'lfsvc','PhoneSvc','TabletInputService','WbioSrvc','XblAuthManager','XblGameSave','XboxNetApiSvc',
    'XboxGipSvc','WMPNetworkSvc','TrkWks','WbioSrvc','SCardSvr','ScDeviceEnum','SCPolicySvc')
  if ($knownSafe -contains $_.Name) { $safety = '🟢关键服务-保留' }
  elseif ($knownUnnecessary -contains $_.Name) { $safety = '🟡非必要-可禁用' }
  [pscustomobject]@{Name=$_.Name;Display=$_.DisplayName;StartMode=$_.StartMode;State=$_.State;Safety=$safety}
} | Sort-Object Safety | Format-Table -AutoSize
```

#### 服务依赖链分析

```powershell
# 服务依赖关系（查看哪些服务依赖某服务，禁用前必须检查）
function Get-ServiceDependents {
  param([string]$ServiceName)
  $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
  if ($svc) {
    $deps = $svc.DependentServices | Where-Object { $_.Status -eq 'Running' }
    if ($deps) {
      $deps | Select-Object Name,DisplayName,Status
    } else {
      "无运行中的依赖服务 - 可安全禁用"
    }
  }
}

# 示例：检查WSearch(Windows Search)的依赖
# Get-ServiceDependents -ServiceName "WSearch"
```

#### 服务启动模式批量优化建议

```powershell
# 生成优化建议清单（只读，不执行修改）
$optimizeList = Get-CimInstance Win32_Service -Filter "State='Running'" |
  Where-Object { $_.StartMode -eq 'Auto' -and $_.Name -in @('WSearch','SysMain','DiagTrack','dmwappushservice','MapsBroker','wisvc','lfsvc','PhoneSvc','XblAuthManager','XblGameSave','TrkWks') } |
  ForEach-Object {
    [pscustomobject]@{
      Service=$_.Name
      Display=$_.DisplayName
      CurrentMode='Auto(自动)'
      SuggestedMode='Manual(手动)或Disabled(禁用)'
      Reason='非关键服务，禁用可释放CPU/内存/IO资源'
      Risk='低风险（禁用后相关功能不可用，但可随时恢复）'
    }
  }
$optimizeList | Format-Table -AutoSize
"共 $($optimizeList.Count) 个服务建议优化"
```

---

### 优化5：临时文件全盘清理（⛔清理操作须逐项确认）

#### 全路径临时文件扫描（只读）

```powershell
# 全路径临时文件扫描（12类缓存/临时文件）
$tempPaths = @(
  @{Name='系统临时';Path="$env:WINDIR\Temp";Ext='*'},
  @{Name='用户临时';Path="$env:TEMP";Ext='*'},
  @{Name='浏览器缓存';Path="$env:LOCALAPPDATA\Microsoft\Windows\INetCache";Ext='*'},
  @{Name='Windows Update临时';Path="$env:WINDIR\SoftwareDistribution\Download";Ext='*'},
  @{Name='Prefetch预读';Path="$env:WINDIR\Prefetch";Ext='*.pf'},
  @{Name='崩溃转储';Path="$env:WINDIR\Minidump";Ext='*.dmp'},
  @{Name='内存转储';Path="$env:WINDIR";Ext='MEMORY.DMP'},
  @{Name='缩略图缓存';Path="$env:LOCALAPPDATA\Microsoft\Windows\Explorer";Ext='thumbcache_*.db'},
  @{Name='字体缓存';Path="$env:WINDIR\ServiceProfiles\LocalService\AppData\Local\FontCache";Ext='*'},
  @{Name='错误报告';Path="$env:LOCALAPPDATA\Microsoft\Windows\WER";Ext='*'},
  @{Name='传递优化';Path="$env:WINDIR\SoftwareDistribution\DeliveryOptimization";Ext='*'},
  @{Name='旧日志文件';Path="$env:WINDIR\Logs";Ext='*.log'}
)

$results = $tempPaths | ForEach-Object {
  $p = $_.Path; $e = $_.Ext; $n = $_.Name
  if (Test-Path $p) {
    $files = Get-ChildItem $p -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { -not $_.PSIsContainer }
    $sizeMB = [math]::Round(($files | Measure-Object -Property Length -Sum).Sum / 1MB,1)
    $count = ($files | Measure-Object).Count
    $level = if ($sizeMB -gt 2000) { '🔴需要清理' } elseif ($sizeMB -gt 500) { '🟡建议清理' } else { '🟢正常' }
    [pscustomobject]@{Category=$n;Path=$p;Size_MB=$sizeMB;FileCount=$count;OptLevel=$level}
  } else {
    [pscustomobject]@{Category=$n;Path=$p;Size_MB=0;FileCount=0;OptLevel='⊘路径不存在'}
  }
}
$results | Sort-Object Size_MB -Descending | Format-Table -AutoSize

$totalMB = ($results | Where-Object { $_.Size_MB -is [double] } | Measure-Object -Property Size_MB -Sum).Sum
$totalGB = [math]::Round($totalMB/1024,2)
"临时文件总量: ${totalGB} GB"
```

#### 各类别清理命令（⛔每类独立确认后执行）

```powershell
# === 以下清理命令均为示例，⛔须逐项确认后执行 ===

# 1. 系统临时文件
# Remove-Item "$env:WINDIR\Temp\*" -Recurse -Force -ErrorAction SilentlyContinue

# 2. 用户临时文件
# Remove-Item "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue

# 3. 缩略图缓存（清理后系统会重建）
# Remove-Item "$env:LOCALAPPDATA\Microsoft\Windows\Explorer\thumbcache_*.db" -Force -ErrorAction SilentlyContinue

# 4. 崩溃转储文件
# Remove-Item "$env:WINDIR\Minidump\*.dmp" -Force -ErrorAction SilentlyContinue
# Remove-Item "$env:WINDIR\MEMORY.DMP" -Force -ErrorAction SilentlyContinue

# 5. 错误报告
# Remove-Item "$env:LOCALAPPDATA\Microsoft\Windows\WER\*" -Recurse -Force -ErrorAction SilentlyContinue

# 6. Prefetch（清理后首次启动应用会稍慢，系统会重建）
# Remove-Item "$env:WINDIR\Prefetch\*.pf" -Force -ErrorAction SilentlyContinue
```

---

### 优化6：网络栈优化（⛔重置操作须逐项确认）

#### 网络栈状态诊断（只读）

```powershell
# DNS缓存状态
$dnsCache = Get-DnsClientCache -ErrorAction SilentlyContinue
$dnsEntryCount = if ($dnsCache) { ($dnsCache | Measure-Object).Count } else { 0 }
$level = if ($dnsEntryCount -gt 500) { '🟡DNS缓存过大' } else { '🟢正常' }
"DNS缓存条目: $dnsEntryCount - $level"

# Winsock目录状态
$winsock = netsh winsock show catalog 2>$null
$winsockEntries = ($winsock | Measure-Object -Line).Lines
"Winsock目录条目: $winsockEntries 行"

# 网络适配器列表
Get-NetAdapter | Select-Object Name,InterfaceDescription,Status,LinkSpeed,MacAddress |
  Sort-Object Status -Descending

# TCP全局参数
Get-NetTCPSetting -ErrorAction SilentlyContinue | Select-Object SettingName,AutoTuningLevelLocal,CongestionProvider,EcnCapability,InitialRtoMs,MinRtoMs
```

#### MTU最优值检测

```powershell
# 检测各网络适配器MTU
Get-NetIPInterface -ErrorAction SilentlyContinue | Where-Object { $_.ConnectionState -eq 'Connected' } |
  Select-Object InterfaceAlias,AddressFamily,NlMtu,Dhcp,ConnectionState |
  Sort-Object InterfaceAlias

# MTU探测（ping分片测试）
# ping -f -l 1472 8.8.8.8  # 如果需要分片则MTU需要调整
# 最优MTU = 不分片的最大payload + 28（IP头20 + ICMP头8）
# 常见MTU值：以太网=1500, PPPoE=1492, VPN=1400
```

#### 网络栈重置命令（⛔须逐项确认后执行）

```powershell
# === 以下重置命令⛔须逐项确认后执行 ===

# 1. 刷新DNS缓存
# Clear-DnsClientCache
# 或 ipconfig /flushdns

# 2. 重置Winsock目录（解决网络连接问题，须确认）
# netsh winsock reset
# 执行后需要重启电脑

# 3. 重置TCP/IP栈（须确认，执行后需要重启）
# netsh int ip reset
# netsh int ipv4 reset
# netsh int ipv6 reset

# 4. 释放并重新获取IP
# ipconfig /release
# ipconfig /renew

# 5. 刷新ARP缓存
# arp -d *

# 6. 重置防火墙规则到默认（须确认，会清除自定义规则）
# netsh advfirewall reset
```

#### TCP自动调优检测

```powershell
# TCP接收窗口自动调优级别
$tcpSetting = Get-NetTCPSetting -ErrorAction SilentlyContinue
if ($tcpSetting) {
  $tuning = $tcpSetting.AutoTuningLevelLocal
  $level = switch ($tuning) {
    'Normal' { '🟢已优化（推荐）' }
    'Disabled' { '🔴已禁用（影响吞吐量）' }
    'HighlyRestricted' { '🟡受限模式' }
    'Restricted' { '🟡受限模式' }
    'Experimental' { '🟡实验模式（可能不稳定）' }
    default { '需评估' }
  }
  "TCP自动调优: $tuning - $level"
}

# 建议优化命令（须确认）
# Set-NetTCPSetting -AutoTuningLevelLocal Normal
```

---

### 优化维护决策树

发现优化机会后的推荐操作路径：

| 优化发现 | 优化等级 | 推荐操作路径 |
|---------|---------|------------|
| C盘空间不足 | 🔴 | 磁盘空间深度清理→临时文件全盘清理→Windows Update缓存清理→休眠文件管理→WinSxS分析 |
| 内存持续高占用 | 🟡 | 内存泄漏检测→Top进程工作集分析→页面文件优化→非必要进程内存释放→服务优化 |
| 开机速度慢 | 🟡 | 启动项影响评级→非必要启动项禁用→服务启动类型优化→延迟启动配置→UEFI引导优化 |
| 服务过多占用资源 | 🟡 | 非必要服务识别→依赖链分析→安全禁用建议→启动模式批量优化→延迟启动配置 |
| 临时文件堆积 | 🟡 | 全路径扫描→按类别逐项确认→系统/用户临时文件→浏览器缓存→崩溃转储→Prefetch清理 |
| 网络连接异常 | 🟡 | DNS缓存刷新→Winsock检查→TCP自动调优检测→MTU检测→网络栈重置（须确认） |
| WinSxS过大 | 🟡 | DISM组件分析→组件存储清理→旧版本组件移除→磁盘空间释放评估 |

---