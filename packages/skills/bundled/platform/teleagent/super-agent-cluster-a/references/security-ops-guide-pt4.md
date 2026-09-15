---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '595f547b-dee4-4a61-b89e-68affd8c6684'
  PropagateID: '595f547b-dee4-4a61-b89e-68affd8c6684'
  ReservedCode1: '29e4f948-2ced-4f02-8c6d-6c32b3986505'
  ReservedCode2: '29e4f948-2ced-4f02-8c6d-6c32b3986505'
---

# 系统运维操作指南（补充3）

> 从 security-ops-guide.md 拆分。

## 操作能力清单

| 操作类别 | 具体操作 | 执行方式 |
|---------|---------|----------|
| 软件管理 | 软件安装与卸载、依赖检查、版本管理 | PowerShell命令执行 |
| 系统体检 | 磁盘空间/内存/CPU/服务状态/启动项全面检测 | PowerShell只读查询 |
| 磁盘维护 | 磁盘清理/碎片整理/大文件筛查 | cleanmgr/defrag/PowerShell |
| 服务管理 | 查看/启动/停止/禁用Windows服务 | PowerShell Service cmdlets |
| 启动项管理 | 查看开机启动项/禁用无用启动项 | PowerShell/注册表查询 |
| 系统优化 | 性能调优/内存释放/临时文件清理/电源计划调整 | PowerShell命令 |
| 网络诊断 | 连通性/DNS解析/端口检测/路由追踪 | ping/nslookup/Test-NetConnection |
| 安全检查 | 防火墙状态/Windows更新状态/已安装程序审查/18项安全基线排查/应急响应取证 | PowerShell只读查询 |
| 环境配置 | 环境变量管理/路径配置/开发环境搭建 | PowerShell/系统属性 |
| 故障排查 | 错误日志分析/崩溃诊断/蓝屏排查/应用兼容性修复 | PowerShell Get-WinEvent/事件查看器 |
| 深度系统诊断 | 蓝屏dump分析/系统可靠性指数/SMART磁盘健康/驱动签名排查/温度监控 | PowerShell+WMI只读查询 |
| 性能根因分析 | CPU/IO/内存/网络瓶颈定位/性能计数器阈值判定/Top进程资源消耗排行/资源阻塞链分析 | PowerShell+性能计数器只读查询 |
| 系统修复与恢复 | SFC系统文件检查/DISM组件修复/系统还原点管理/Windows更新重置/引导配置修复 | PowerShell（须逐项确认） |
| 注册表深度审计 | LSA保护状态/SMB签名配置/Credential Guard/WDigest凭据缓存/LSA脚本鉴权 | PowerShell+reg查询只读审计 |
| 事件日志全面分析 | System/Application日志/Error+Warning级别聚类/故障事件速查/服务崩溃历史/应用程序挂起记录 | PowerShell Get-WinEvent只读查询 |
| 电源管理诊断 | 电源计划分析/睡眠唤醒失败诊断/能效报告生成/电池健康(笔记本)/虚拟化电源策略 | PowerShell powercfg只读查询 |
| 磁盘空间深度清理 | WinSxS组件存储分析/Windows Update缓存清理/休眠文件管理/Windows.old清理/系统还原点清理/交付优化缓存清理 | PowerShell+DISM（须逐项确认） |
| 内存深度优化 | 内存泄漏检测/工作集分析/页面文件优化配置/Standby内存释放/物理内存vs虚拟内存占比分析 | PowerShell+WMI只读查询+优化操作 |
| 启动优化 | 开机时间测量/启动影响评级/启动项延迟加载分析/服务启动类型优化/UEFI引导优化 | PowerShell Get-CimInstance只读分析+优化操作 |
| 系统服务优化 | 非必要服务识别/服务依赖链分析/安全禁用建议/服务启动模式批量优化/延迟启动配置 | PowerShell Service cmdlets只读分析+优化操作（须逐项确认） |
| 临时文件全盘清理 | System/User/Browser/Update/Prefetch/Crash Dump/缩略图/字体缓存全路径扫描与清理 | PowerShell扫描只读+清理须确认 |
| 网络栈优化 | TCP/IP重置/DNS缓存刷新/Winsock目录重置/MTU最优值检测/网络适配器高级配置 | PowerShell netsh/Reset-IP（须逐项确认） |

---

## 高级系统诊断能力清单

| 诊断类别 | 诊断内容 | 关键指标与阈值 | 健康等级判定 |
|---------|---------|--------------|------------|
| 深度系统诊断 | 蓝屏dump分析/系统可靠性指数/SMART磁盘健康/驱动签名排查 | 可靠性指数1-10（<6=🔴）、SMART ReallocatedSectorCount>0=🔴、未签名驱动=🟡 | 🟢全部正常/🟡有警告项/🔴有异常项 |
| 性能根因分析 | CPU/IO/内存/网络瓶颈/Top进程资源消耗/资源阻塞链 | CPU持续>80%=🟡/>95%=🔴、磁盘队列长度>2=🟡/>4=🔴、可用内存<10%=🟡/<5%=🔴 | 🟢无瓶颈/🟡有预警/🔴有严重瓶颈 |
| 系统修复与恢复 | SFC/DISM/还原点/更新重置/引导修复 | SFC找到损坏=🟡、DISM修复失败=🔴、无还原点=🟡 | 🟢无需修复/🟡建议修复/🔴必须修复 |
| 注册表深度审计 | LSA/SMB签名/Credential Guard/WDigest/LSA脚本鉴权 | WDigest UseLogonCredential=1=🔴、SMB签名未启用=🟡、Credential Guard未启用=🟡 | 🟢全部合规/🟡有配置建议/🔴有安全风险 |
| 事件日志全面分析 | System/Application/Error+Warning聚类/服务崩溃/应用挂起 | 近7天Error>50=🟡/>200=🔴、关键服务崩溃=🔴 | 🟢日志正常/🟡有警告事件/🔴有严重故障 |
| 电源管理诊断 | 电源计划/睡眠唤醒失败/能效报告/电池健康 | 唤醒失败率>10%=🟡/>30%=🔴、无电源计划=🟡 | 🟢配置合理/🟡建议优化/🔴存在异常 |

---

## 电脑优化维护能力清单

| 优化类别 | 优化内容 | 关键指标与阈值 | 优化等级判定 |
|---------|---------|--------------|------------|
| 磁盘空间深度清理 | WinSxS/Windows Update缓存/休眠文件/Windows.old/还原点/交付优化缓存 | C盘剩余<10%=🔴/<20%=🟡/≥20%=🟢、WinSxS>5GB=🟡 | 🟢空间充足/🟡建议清理/🔴需要清理 |
| 内存深度优化 | 内存泄漏检测/工作集分析/页面文件优化/Standby内存 | 工作集持续增长=🟡、页面文件>物理内存1.5倍=🟡、Standby>物理内存50%=🟡 | 🟢配置合理/🟡建议优化/🔴存在泄漏 |
| 启动优化 | 开机时间/启动影响评级/延迟加载/服务启动类型 | 开机>60秒=🟡/>120秒=🔴、启动项>15个=🟡 | 🟢启动正常/🟡建议优化/🔴启动过慢 |
| 系统服务优化 | 非必要服务识别/依赖链/安全禁用/启动模式 | 非必要服务运行>10个=🟡、依赖冲突=🔴 | 🟢服务精简/🟡建议优化/🔴存在冲突 |
| 临时文件全盘清理 | System/User/Browser/Update/Prefetch/Crash Dump/缩略图/字体缓存 | 临时文件总量>5GB=🟡/>10GB=🔴、Crash Dump>1GB=🟡 | 🟢临时文件少/🟡建议清理/🔴需要清理 |
| 网络栈优化 | TCP/IP重置/DNS刷新/Winsock重置/MTU检测/适配器配置 | DNS解析失败率>5%=🟡、MTU非最优=🟡、Winsock损坏=🔴 | 🟢网络正常/🟡建议优化/🔴需要重置 |

---

## 脚本文件编码规范（⛔生成.bat/.cmd脚本时100%强制执行）

[Agent-运维型]在为用户生成需要管理员权限运行的 .bat/.cmd 批处理脚本时，必须遵守以下编码规则，否则脚本将无法运行。

### 问题根因

PowerShell 5.1 的 `Set-Content -Encoding UTF8` 会写入 UTF-8 BOM 头（3字节 `EF BB BF`）。Windows CMD 解释器遇到 BOM 字节会将其当作 `@echo off` 前面的非法字符，导致脚本执行失败（闪退或报错）。

### 强制规则

| 文件类型 | 禁止编码 | 正确做法 | 验证方法 |
|---------|---------|---------|---------|
| .bat / .cmd | `Set-Content -Encoding UTF8`（带BOM） | `[System.IO.File]::WriteAllText($path, $content, (New-Object System.Text.UTF8Encoding($false)))` | 读取前3字节，不能是 `EF BB BF` |
| .bat / .cmd | `Out-File -Encoding UTF8`（带BOM） | 同上，或 PowerShell 7+ 用 `Set-Content -Encoding utf8NoBOM` | 同上 |
| .ps1 | 无限制 | 任意编码均可（PowerShell兼容BOM） | 无需验证 |

### 正确代码模板

```powershell
# ✅ 正确：无BOM写入bat文件
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($scriptPath, $batContent, $utf8NoBom)

# ❌ 错误：Set-Content -Encoding UTF8 会带BOM
# Set-Content -Path $scriptPath -Value $batContent -Encoding UTF8  # 禁止！

# ❌ 错误：Out-File -Encoding UTF8 也会带BOM
# $batContent | Out-File -FilePath $scriptPath -Encoding UTF8      # 禁止！

# ✅ 验证：检查前3字节
$bytes = [System.IO.File]::ReadAllBytes($scriptPath)
if ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    Write-Host "BOM检测失败！bat文件无法运行" -ForegroundColor Red
} else {
    Write-Host "编码正确，无BOM" -ForegroundColor Green
}
```

### 生成bat脚本后的强制验证步骤

1. 写入文件后，立即读取前3字节验证
2. 若检测到 BOM（`EF BB BF`），必须重新用无 BOM 编码写入
3. 验证通过后方可执行（禁止让用户手动运行）

---

## 管理员权限提权执行与内容披露（⛔需要管理员权限时100%强制执行）

[Agent-运维型] 在用户逐项确认操作后，需要管理员权限的操作可提权执行，禁止生成最终交付脚本让用户手动右键管理员运行。⛔**核心安全约束：提权前必须强制披露执行内容**——Agent必须在用户确认前完整展示将执行的确切命令/脚本内容（禁止仅展示说人话摘要而不展示实际命令），让用户对提权执行的具体内容有充分审查机会。用户逐项审查确认后，Agent生成临时脚本写入 `.temp/` 目录，通过 `Start-Process -Verb RunAs` 触发 UAC 弹窗（用户点“是”即授权执行已审查的命令）。

### ⛔提权安全红线（不可违反）

1. **提权前强制披露执行内容**：对每项需提权的操作，Agent必须在用户确认前完整展示将执行的确切命令/脚本内容。禁止仅展示说人话摘要而不展示实际命令——说人话摘要与实际命令必须同时呈现
2. **每项破坏性操作独立提权**：禁止将多项破坏性操作合并为单个脚本一次 UAC 授权。每项破坏性操作独立生成临时脚本、独立触发 UAC、独立授权。只读诊断类操作可合并（无破坏性）
3. **Sentinel安全审查前置**：所有提权脚本须经[Sentinel]安全审查，检查命令内容是否含外传敏感数据/系统级破坏/越权操作模式，审查通过后方可提权执行
4. **禁止生成最终交付脚本**：临时脚本写入 `.temp/`，执行后自动清理，禁止生成最终交付的 bat 文件让用户手动运行
5. **临时脚本编码无BOM**：bat脚本必须用无BOM UTF-8写入，执行前验证前3字节不为 `EF BB BF`

### 提权执行流程

```text
用户确认操作（已审查完整命令内容）
  → [Sentinel] 对将执行的命令内容进行安全审查（检查外传/破坏/越权模式）
  → 审查通过 → [Agent-运维型] 生成临时脚本写入 .temp/ 目录
  → 通过 Start-Process -Verb RunAs 触发 UAC 弹窗
  → 用户在 UAC 弹窗点“是”授权（授权的是已审查的命令）
  → 脚本以管理员权限自动执行
  → 捕获执行输出结果
  → 自动清理临时脚本
  → 用说人话汇报执行结果
```

### 单项操作提权执行代码模板

```powershell
# ✅ 单项操作提权执行（用户已审查完整命令内容，只需在UAC弹窗点“是”）
# 提权前向用户完整展示将执行的命令内容（⛔强制，不可跳过）
# Agent已向用户展示以下命令的确切内容并获得逐项确认

# 生成临时脚本（无BOM编码写入.temp/）
$tempDir = ".temp"
if (-not (Test-Path $tempDir)) { New-Item -ItemType Directory -Path $tempDir -Force | Out-Null }
$tempScript = Join-Path $tempDir "admin_task_$(Get-Date -Format 'yyyyMMddHHmmss').bat"

$batContent = @"
@echo off
chcp 65001 >nul
echo ============================================
echo   正在执行管理员操作...
echo ============================================
echo.
$AdminCommands
echo.
echo ============================================
echo   执行完成
echo ============================================
echo 执行结果已保存
"@

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($tempScript, $batContent, $utf8NoBom)

# 验证无BOM
$bytes = [System.IO.File]::ReadAllBytes($tempScript)
if ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    Write-Host "BOM检测失败，重新生成" -ForegroundColor Red
    [System.IO.File]::WriteAllText($tempScript, $batContent, $utf8NoBom)
}

# 自动提权执行（弹出UAC，用户点“是”即可）
$process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $tempScript -Verb RunAs -Wait -PassThru -WindowStyle Normal

# 检查执行结果
if ($process.ExitCode -eq 0) {
    Write-Host "管理员操作执行成功" -ForegroundColor Green
} else {
    Write-Host "管理员操作执行失败（退出码: $($process.ExitCode)）" -ForegroundColor Red
}

# 清理临时脚本
Remove-Item $tempScript -Force -ErrorAction SilentlyContinue
```

### 需要管理员权限的常见操作与对应命令

| 操作类型 | 需管理员 | 提权执行的命令 |
|---------|---------|-----------------|
| 禁用计划任务 | 是 | `schtasks /Change /TN "任务名" /Disable` |
| SFC系统文件检查 | 是 | `sfc /scannow` |
| DISM组件修复 | 是 | `dism /online /cleanup-image /restorehealth` |
| 磁盘清理(cleanmgr) | 是 | `cleanmgr /sagerun:1` |
| 修改服务启动类型 | 是 | `Set-Service -Name "服务名" -StartupType Disabled` |
| 系统还原点创建 | 是 | `Checkpoint-Computer -Description "优化前还原点"` |
| 网络栈重置 | 是 | `netsh winsock reset` / `netsh int ip reset` |
| 安装/卸载软件 | 是 | `msiexec /i / /x` 或 `winget install/uninstall` |

⛔**每项破坏性操作独立提权**——上述命令均为单项操作模板，禁止将多项破坏性操作合并为单个脚本一次 UAC 授权。只读诊断类操作可合并为一个脚本（无破坏性风险）。

### ⛔废弃模板——禁止使用：多项破坏性操作合并一次提权

以下模板已废弃，禁止用于破坏性操作。仅当所有操作均为只读诊断类（无破坏性风险）时，可参考此模式合并执行。破坏性操作必须使用上方单项提权模板逐项独立提权。

```powershell
# ⛔废弃模板：多项管理员操作合并到一个脚本中，只需UAC授权一次
# 此模板仅适用于只读诊断类操作合并，禁止用于破坏性操作
$batContent = @"
@echo off
chcp 65001 >nul
echo 正在执行系统优化操作...
echo.

echo [1/3] 禁用计划任务...
schtasks /Change /TN "Task1" /Disable
echo.

echo [2/3] 运行SFC修复...
sfc /scannow
echo.

echo [3/3] DISM修复...
dism /online /cleanup-image /restorehealth
echo.

echo 全部操作完成
"@

$tempScript = ".temp\admin_batch_$(Get-Date -Format 'yyyyMMddHHmmss').bat"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($tempScript, $batContent, $utf8NoBom)

# 一次UAC授权执行所有操作（输出重定向到日志，便于捕获回传）
$logFile = ".temp\admin_batch_$(Get-Date -Format 'yyyyMMddHHmmss').log"
$args = "/c `"`$tempScript`" > `"`$logFile`" 2>&1`""
$process = Start-Process -FilePath "cmd.exe" -ArgumentList $args -Verb RunAs -Wait -PassThru

# 校验执行结果
if ($process.ExitCode -eq 0) {
    Write-Host "✅ 批量管理员操作执行成功" -ForegroundColor Green
} else {
    Write-Host "⚠️ 执行失败（退出码: $($process.ExitCode)），检查日志后重试" -ForegroundColor Yellow
}
# 读取输出用于说人话汇报
if (Test-Path $logFile) { Get-Content $logFile -Tail 20 }

# 清理临时脚本与日志
Remove-Item $tempScript -Force -ErrorAction SilentlyContinue
Remove-Item $logFile -Force -ErrorAction SilentlyContinue
```

### 强制规则

- **⛔提权前强制披露执行内容**——对每项需提权的操作，Agent必须在用户确认前完整展示将执行的确切命令/脚本内容（禁止仅展示说人话摘要而不展示实际命令），让用户对提权执行的具体内容有充分审查机会
- **⛔每项破坏性操作独立提权**——禁止将多项破坏性操作合并为单个脚本一次 UAC 授权。每项破坏性操作独立生成临时脚本、独立触发 UAC、独立授权。只读诊断类操作可合并
- **⛔Sentinel安全审查前置**——所有提权脚本须经[Sentinel]安全审查（检查命令内容是否含外传敏感数据/系统级破坏/越权操作模式），审查通过后方可提权执行
- **禁止生成最终交付的 bat 文件让用户手动运行**——临时脚本写入 `.temp/`，执行后自动清理
- **必须通过 `Start-Process -Verb RunAs` 自动触发 UAC**——用户只需在弹窗点"是"授权已审查的命令
- **执行后自动清理临时脚本**——`.temp/` 中的临时文件执行完毕即删除
- **仍需逐项确认操作内容**——提权不跳过逐项确认流程，只是执行方式从"用户手动运行"改为"技能提权执行"
- **⛔执行结果必须回传主会话**——`Start-Process -Wait -PassThru` 后读取 `$process.ExitCode`，并将输出重定向到 `.temp/` 日志文件；执行结束后读取日志内容用于说人话汇报（做了什么/结果如何/前后对比），禁止"执行完就完事"不汇报结果
- **⛔失败自动重试一次**——退出码非 0 时，[Agent-运维型] 先排查失败原因（命令语法/权限/依赖），修正后自动重试 1 次；仍失败则向用户报告具体失败点并请求协助，禁止静默吞掉失败结果
- **⛔超时保护**——提权脚本设总超时（默认 15 分钟，可因命令类型调整）；超时未完成 → 标记"超时"并检查进度日志，向用户报告已完成/未完成部分，不得伪造完成状态