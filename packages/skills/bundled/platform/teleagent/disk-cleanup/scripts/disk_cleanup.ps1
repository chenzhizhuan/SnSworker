<#
.SYNOPSIS
    C盘深度清理脚本 - 扫描并清理Windows系统磁盘空间
.DESCRIPTION
    分三个阶段执行：
    1. 扫描：检查磁盘空间和各目录占用
    2. 标准清理：自动清理缓存、临时文件、日志等安全项
    3. 深度清理：清理聊天软件缓存、浏览器缓存、开发工具缓存等（需确认）
.PARAMETER Mode
    scan    - 仅扫描，不清理
    standard - 标准清理（安全项，无需确认）
    deep    - 深度清理（包含聊天媒体缓存，需确认）
    all     - 标准清理 + 深度清理
.EXAMPLE
    .\disk_cleanup.ps1 -Mode scan
    .\disk_cleanup.ps1 -Mode standard
    .\disk_cleanup.ps1 -Mode deep
    .\disk_cleanup.ps1 -Mode all
#>

param(
    [ValidateSet("scan","standard","deep","all")]
    [string]$Mode = "scan"
)

$ErrorActionPreference = "SilentlyContinue"

# ===== 全局状态 =====
$script:TotalFreedBytes = 0
$script:CleanLog = @()

function Get-DirSize {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return 0 }
    $size = (Get-ChildItem -Path $Path -Recurse -Force -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
    if (-not $size) { return 0 }
    return $size
}

function Format-Size {
    param([long]$Bytes)
    if ($Bytes -ge 1GB) { return ("{0:F2} GB" -f ($Bytes/1GB)) }
    elseif ($Bytes -ge 1MB) { return ("{0:F0} MB" -f ($Bytes/1MB)) }
    elseif ($Bytes -ge 1KB) { return ("{0:F0} KB" -f ($Bytes/1KB)) }
    else { return "$Bytes B" }
}

function Clean-Path {
    param([string]$Name, [string]$Path, [switch]$Recurse)
    if (-not (Test-Path $Path)) {
        Write-Output ("  [跳过] {0}: 目录不存在" -f $Name)
        return 0
    }
    $size = Get-DirSize -Path $Path
    if ($size -eq 0) {
        Write-Output ("  [跳过] {0}: 已为空" -f $Name)
        return 0
    }
    if ($Recurse) {
        Remove-Item -Path $Path -Recurse -Force -ErrorAction SilentlyContinue
        New-Item -ItemType Directory -Path $Path -Force -ErrorAction SilentlyContinue | Out-Null
    } else {
        Remove-Item -Path "$Path\*" -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Output ("  [清理] {0}: {1}" -f $Name, (Format-Size $size))
    return $size
}

function Clean-CacheSubdirs {
    param([string]$RootPath, [string[]]$Patterns = @("cache","log","tmp","crash","dump","backup"))
    if (-not (Test-Path $RootPath)) { return 0 }
    $total = 0
    $cacheDirs = Get-ChildItem -Path $RootPath -Directory -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object { $matched = $false; foreach ($p in $Patterns) { if ($_.Name -match $p) { $matched = $true; break } }; $matched }
    foreach ($cd in $cacheDirs) {
        $sz = Get-DirSize -Path $cd.FullName
        if ($sz -gt 5MB) {
            Remove-Item -Path "$($cd.FullName)\*" -Recurse -Force -ErrorAction SilentlyContinue
            $total += $sz
        }
    }
    return $total
}

# ===== 阶段1: 扫描 =====
function Show-DiskStatus {
    $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
    $totalGB = [math]::Round($disk.Size/1GB, 2)
    $freeGB = [math]::Round($disk.FreeSpace/1GB, 2)
    $usedGB = [math]::Round(($disk.Size - $disk.FreeSpace)/1GB, 2)
    $usedPct = [math]::Round(($disk.Size - $disk.FreeSpace)/$disk.Size*100, 1)
    Write-Output ""
    Write-Output "===== C盘磁盘状态 ====="
    Write-Output ("总空间: {0} GB" -f $totalGB)
    Write-Output ("已用: {0} GB ({1}%)" -f $usedGB, $usedPct)
    Write-Output ("可用: {0} GB" -f $freeGB)
    Write-Output ""
    return $freeGB
}

function Scan-Disk {
    Write-Output "===== 阶段1: 扫描磁盘空间 ====="

    # 系统级可清理项
    $systemPaths = @(
        @{Name="回收站"; Path="C:\`$Recycle.Bin"},
        @{Name="Windows临时文件"; Path="C:\Windows\Temp"},
        @{Name="用户临时文件"; Path="$env:TEMP"},
        @{Name="Windows更新缓存"; Path="C:\Windows\SoftwareDistribution\Download"},
        @{Name="缩略图缓存"; Path="$env:LOCALAPPDATA\Microsoft\Windows\Explorer"},
        @{Name="Windows日志"; Path="C:\Windows\Logs"},
        @{Name="崩溃转储"; Path="$env:LOCALAPPDATA\CrashDumps"}
    )
    Write-Output "`n--- 系统级 ---"
    foreach ($item in $systemPaths) {
        $sz = Get-DirSize -Path $item.Path
        if ($sz -gt 1MB) { Write-Output ("  {0}: {1}" -f $item.Name, (Format-Size $sz)) }
    }

    # 浏览器缓存
    Write-Output "`n--- 浏览器 ---"
    $browserPaths = @(
        @{Name="Edge"; Path="$env:LOCALAPPDATA\Microsoft\Edge\User Data"},
        @{Name="Chrome"; Path="$env:LOCALAPPDATA\Google\Chrome\User Data"}
    )
    foreach ($item in $browserPaths) {
        $sz = Get-DirSize -Path $item.Path
        if ($sz -gt 1MB) { Write-Output ("  {0}: {1}" -f $item.Name, (Format-Size $sz)) }
    }

    # 开发工具缓存
    Write-Output "`n--- 开发工具 ---"
    $devPaths = @(
        @{Name="npm缓存(Roaming)"; Path="$env:APPDATA\npm-cache"},
        @{Name="npm缓存(Local)"; Path="$env:LOCALAPPDATA\npm-cache"},
        @{Name="pip缓存"; Path="$env:LOCALAPPDATA\pip\cache"},
        @{Name="Yarn缓存"; Path="$env:LOCALAPPDATA\Yarn"},
        @{Name="JetBrains"; Path="$env:LOCALAPPDATA\JetBrains"},
        @{Name="VS Code"; Path="$env:APPDATA\Code"},
        @{Name="ms-playwright"; Path="$env:LOCALAPPDATA\ms-playwright"},
        @{Name="Postman"; Path="$env:LOCALAPPDATA\Postman"}
    )
    foreach ($item in $devPaths) {
        $sz = Get-DirSize -Path $item.Path
        if ($sz -gt 1MB) { Write-Output ("  {0}: {1}" -f $item.Name, (Format-Size $sz)) }
    }

    # 聊天/办公软件
    Write-Output "`n--- 聊天/办公软件 ---"
    $appPaths = @(
        @{Name="微信4.0(xwechat)"; Path="$env:APPDATA\Tencent\xwechat"},
        @{Name="微信(旧版)"; Path="$env:APPDATA\Tencent\WeChat"},
        @{Name="企业微信"; Path="$env:APPDATA\Tencent\WXWork"},
        @{Name="腾讯会议"; Path="$env:APPDATA\Tencent\WeMeet"},
        @{Name="QQ"; Path="$env:APPDATA\Tencent\QQ"},
        @{Name="钉钉Ykz"; Path="$env:APPDATA\DingTalkYkz"},
        @{Name="钉钉"; Path="$env:APPDATA\DingTalk"},
        @{Name="IM聊天媒体"; Path="$env:APPDATA\im"},
        @{Name="WPS(kingsoft)"; Path="$env:APPDATA\kingsoft"},
        @{Name="iSlide"; Path="$env:APPDATA\iSlide"},
        @{Name="HBuilder X"; Path="$env:APPDATA\HBuilder X"},
        @{Name="utForpc"; Path="$env:APPDATA\utForpc"},
        @{Name="百度网盘"; Path="$env:APPDATA\baidunetdisk"},
        @{Name="深信服VPN"; Path="$env:APPDATA\Sangfor"}
    )
    foreach ($item in $appPaths) {
        $sz = Get-DirSize -Path $item.Path
        if ($sz -gt 1MB) { Write-Output ("  {0}: {1}" -f $item.Name, (Format-Size $sz)) }
    }

    # 多版本残留
    Write-Output "`n--- 多版本/Updater ---"
    $versionPaths = @(
        @{Name="DingTalkGov_91(旧版)"; Path="$env:LOCALAPPDATA\DingTalkGov_91"},
        @{Name="DingTalkGov_108"; Path="$env:LOCALAPPDATA\DingTalkGov_108"},
        @{Name="DingTalk_108"; Path="$env:LOCALAPPDATA\DingTalk_108"},
        @{Name="super-agent-updater"; Path="$env:LOCALAPPDATA\super-agent-updater"},
        @{Name="teleagent-updater"; Path="$env:LOCALAPPDATA\teleagent-updater"},
        @{Name="jinwu-updater"; Path="$env:LOCALAPPDATA\jinwu-updater"},
        @{Name="VMware"; Path="$env:LOCALAPPDATA\VMware"},
        @{Name="Netease(网易云)"; Path="$env:LOCALAPPDATA\Netease"}
    )
    foreach ($item in $versionPaths) {
        $sz = Get-DirSize -Path $item.Path
        if ($sz -gt 1MB) { Write-Output ("  {0}: {1}" -f $item.Name, (Format-Size $sz)) }
    }

    $freeGB = Show-DiskStatus
    Write-Output "扫描完成。使用 -Mode standard 进行标准清理，-Mode deep 进行深度清理。"
}

# ===== 阶段2: 标准清理 =====
function Run-StandardClean {
    Write-Output "===== 阶段2: 标准清理（安全项） ====="
    $total = 0

    Write-Output "`n[1/7] 清空回收站..."
    try {
        Clear-RecycleBin -Force -ErrorAction Stop
        Write-Output "  [清理] 回收站: 已清空"
    } catch {
        Get-ChildItem 'C:\$Recycle.Bin' -Recurse -Force -ErrorAction SilentlyContinue |
            Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
        Write-Output "  [清理] 回收站: 已清空(直接删除)"
    }

    Write-Output "`n[2/7] 清理系统临时文件..."
    $total += Clean-Path "用户临时文件" $env:TEMP
    $total += Clean-Path "Windows临时文件" "C:\Windows\Temp"
    $total += Clean-Path "崩溃转储" "$env:LOCALAPPDATA\CrashDumps"
    $total += Clean-Path "Windows更新缓存" "C:\Windows\SoftwareDistribution\Download"

    # 缩略图缓存
    $thumbPath = "$env:LOCALAPPDATA\Microsoft\Windows\Explorer"
    if (Test-Path $thumbPath) {
        $thumbSize = (Get-ChildItem -Path $thumbPath -Filter "thumbcache_*" -Force -ErrorAction SilentlyContinue |
            Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
        if ($thumbSize) {
            Remove-Item -Path "$thumbPath\thumbcache_*" -Force -ErrorAction SilentlyContinue
            Write-Output ("  [清理] 缩略图缓存: {0}" -f (Format-Size $thumbSize))
            $total += $thumbSize
        }
    }

    # Windows旧日志（>3天）
    $cutoff = (Get-Date).AddDays(-3)
    $logFiles = Get-ChildItem -Path "C:\Windows\Logs" -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $cutoff -and $_.Length -gt 1MB }
    $logSize = ($logFiles | Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
    if ($logSize) {
        $logFiles | ForEach-Object { Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue }
        Write-Output ("  [清理] Windows旧日志: {0}" -f (Format-Size $logSize))
        $total += $logSize
    }

    Write-Output "`n[3/7] 清理浏览器缓存..."
    foreach ($browser in @("Edge","Chrome")) {
        $dataPath = if ($browser -eq "Edge") {
            "$env:LOCALAPPDATA\Microsoft\Edge\User Data"
        } else {
            "$env:LOCALAPPDATA\Google\Chrome\User Data"
        }
        $cacheDirs = @("Cache","Code Cache","GPUCache","Service Worker\CacheStorage","Default\Cache","Default\Code Cache","Default\GPUCache")
        $browserTotal = 0
        foreach ($dir in $cacheDirs) {
            $fullPath = Join-Path $dataPath $dir
            if (Test-Path $fullPath) {
                $sz = Get-DirSize -Path $fullPath
                Remove-Item -Path $fullPath -Recurse -Force -ErrorAction SilentlyContinue
                New-Item -ItemType Directory -Path $fullPath -Force -ErrorAction SilentlyContinue | Out-Null
                $browserTotal += $sz
            }
        }
        if ($browserTotal -gt 0) {
            Write-Output ("  [清理] {0}缓存: {1}" -f $browser, (Format-Size $browserTotal))
            $total += $browserTotal
        }
    }

    Write-Output "`n[4/7] 清理开发工具缓存..."
    $total += Clean-Path "npm缓存(Roaming)" "$env:APPDATA\npm-cache"
    $total += Clean-Path "npm缓存(Local)" "$env:LOCALAPPDATA\npm-cache"
    $total += Clean-Path "pip缓存" "$env:LOCALAPPDATA\pip\cache"
    $total += Clean-Path "Yarn缓存" "$env:LOCALAPPDATA\Yarn\Cache"

    # JetBrains缓存（保留配置）
    $jbPath = "$env:LOCALAPPDATA\JetBrains"
    if (Test-Path $jbPath) {
        $jbTotal = 0
        foreach ($sub in @("caches","log","index")) {
            $dirs = Get-ChildItem -Path $jbPath -Directory -Force -ErrorAction SilentlyContinue
            foreach ($d in $dirs) {
                $targetPath = Join-Path $d.FullName $sub
                if (Test-Path $targetPath) {
                    $sz = Get-DirSize -Path $targetPath
                    if ($sz -gt 5MB) {
                        Remove-Item -Path "$targetPath\*" -Recurse -Force -ErrorAction SilentlyContinue
                        $jbTotal += $sz
                    }
                }
            }
        }
        if ($jbTotal -gt 0) {
            Write-Output ("  [清理] JetBrains缓存/日志/索引: {0}" -f (Format-Size $jbTotal))
            $total += $jbTotal
        }
    }

    # VS Code缓存
    $vscodePaths = @("Cache","CachedData","Code Cache","GPUCache","logs")
    $vsTotal = 0
    foreach ($sub in $vscodePaths) {
        $p = "$env:APPDATA\Code\$sub"
        if (Test-Path $p) {
            $sz = Get-DirSize -Path $p
            if ($sz -gt 1MB) {
                Remove-Item -Path "$p\*" -Recurse -Force -ErrorAction SilentlyContinue
                $vsTotal += $sz
            }
        }
    }
    if ($vsTotal -gt 0) {
        Write-Output ("  [清理] VS Code缓存: {0}" -f (Format-Size $vsTotal))
        $total += $vsTotal
    }

    Write-Output "`n[5/7] 清理WPS缓存..."
    $wpsTotal = Clean-CacheSubdirs -RootPath "$env:APPDATA\kingsoft" -Patterns @("cache","backup","log","temp","crash")
    # WPS backup单独处理
    $wpsBackup = "$env:APPDATA\kingsoft\office6\backup"
    if (Test-Path $wpsBackup) {
        $bsz = Get-DirSize -Path $wpsBackup
        if ($bsz -gt 5MB) {
            Remove-Item -Path "$wpsBackup\*" -Recurse -Force -ErrorAction SilentlyContinue
            $wpsTotal += $bsz
        }
    }
    if ($wpsTotal -gt 0) {
        Write-Output ("  [清理] WPS缓存/备份/日志: {0}" -f (Format-Size $wpsTotal))
        $total += $wpsTotal
    }

    Write-Output "`n[6/7] 清理多版本残留和Updater..."
    # DingTalkGov_91旧版
    $total += Clean-Path "DingTalkGov_91(旧版)" "$env:LOCALAPPDATA\DingTalkGov_91" -Recurse

    # Updater pending
    foreach ($u in @("super-agent-updater","jinwu-updater")) {
        $p = "$env:LOCALAPPDATA\$u\pending"
        if (Test-Path $p) {
            $sz = Get-DirSize -Path $p
            if ($sz -gt 1MB) {
                Remove-Item -Path "$p\*" -Recurse -Force -ErrorAction SilentlyContinue
                Write-Output ("  [清理] {0}/pending: {1}" -f $u, (Format-Size $sz))
                $total += $sz
            }
        }
    }

    # VMware下载缓存
    $vmDirs = Get-ChildItem -Path "$env:LOCALAPPDATA\VMware" -Directory -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match "download" }
    foreach ($vd in $vmDirs) {
        $sz = Get-DirSize -Path $vd.FullName
        if ($sz -gt 1MB) {
            Remove-Item -Path $vd.FullName -Recurse -Force -ErrorAction SilentlyContinue
            Write-Output ("  [清理] VMware/{0}: {1}" -f $vd.Name, (Format-Size $sz))
            $total += $sz
        }
    }

    # Playwright旧版浏览器
    $pwPath = "$env:LOCALAPPDATA\ms-playwright"
    if (Test-Path $pwPath) {
        $pwVersions = Get-ChildItem -Path $pwPath -Directory -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match "chromium" } | Sort-Object Name
        if ($pwVersions.Count -gt 2) {
            $toRemove = $pwVersions | Select-Object -First ($pwVersions.Count - 2)
            foreach ($v in $toRemove) {
                $sz = Get-DirSize -Path $v.FullName
                Remove-Item -Path $v.FullName -Recurse -Force -ErrorAction SilentlyContinue
                Write-Output ("  [清理] Playwright旧版 {0}: {1}" -f $v.Name, (Format-Size $sz))
                $total += $sz
            }
        }
    }

    # Postman旧版本
    $pmPath = "$env:LOCALAPPDATA\Postman"
    if (Test-Path $pmPath) {
        $pmVersions = Get-ChildItem -Path $pmPath -Directory -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match "^app-" } | Sort-Object Name
        if ($pmVersions.Count -gt 1) {
            $toRemove = $pmVersions | Select-Object -First ($pmVersions.Count - 1)
            foreach ($v in $toRemove) {
                $sz = Get-DirSize -Path $v.FullName
                Remove-Item -Path $v.FullName -Recurse -Force -ErrorAction SilentlyContinue
                Write-Output ("  [清理] Postman旧版 {0}: {1}" -f $v.Name, (Format-Size $sz))
                $total += $sz
            }
        }
    }

    Write-Output "`n[7/7] 清理其他软件缓存..."
    # 网易云音乐缓存
    $nmPath = "$env:LOCALAPPDATA\Netease\CloudMusic"
    if (Test-Path $nmPath) {
        $nmTotal = Clean-CacheSubdirs -RootPath $nmPath -Patterns @("cache","Cache")
        $wsPath = "$nmPath\WebStorage"
        if (Test-Path $wsPath) {
            $wsz = Get-DirSize -Path $wsPath
            if ($wsz -gt 1MB) { Remove-Item -Path "$wsPath\*" -Recurse -Force -ErrorAction SilentlyContinue; $nmTotal += $wsz }
        }
        if ($nmTotal -gt 0) {
            Write-Output ("  [清理] 网易云音乐缓存: {0}" -f (Format-Size $nmTotal))
            $total += $nmTotal
        }
    }

    # 深信服VPN日志
    $sfTotal = Clean-CacheSubdirs -RootPath "$env:APPDATA\Sangfor" -Patterns @("log","cache","tmp","crash")
    $sfTotal += Clean-CacheSubdirs -RootPath "$env:LOCALAPPDATA\Sangfor" -Patterns @("log","cache","tmp","crash")
    if ($sfTotal -gt 0) {
        Write-Output ("  [清理] 深信服VPN缓存/日志: {0}" -f (Format-Size $sfTotal))
        $total += $sfTotal
    }

    # 百度网盘缓存
    $bdTotal = Clean-CacheSubdirs -RootPath "$env:APPDATA\baidunetdisk" -Patterns @("cache","log","tmp")
    if ($bdTotal -gt 0) {
        Write-Output ("  [清理] 百度网盘缓存: {0}" -f (Format-Size $bdTotal))
        $total += $bdTotal
    }

    # iSlide缓存
    $isTotal = Clean-CacheSubdirs -RootPath "$env:APPDATA\iSlide" -Patterns @("cache","log","tmp")
    if ($isTotal -gt 0) {
        Write-Output ("  [清理] iSlide缓存: {0}" -f (Format-Size $isTotal))
        $total += $isTotal
    }

    # HBuilder X缓存
    $hbTotal = Clean-CacheSubdirs -RootPath "$env:APPDATA\HBuilder X" -Patterns @("cache","log","tmp")
    if ($hbTotal -gt 0) {
        Write-Output ("  [清理] HBuilder X缓存: {0}" -f (Format-Size $hbTotal))
        $total += $hbTotal
    }

    # 语雀桌面缓存
    $yqTotal = Clean-CacheSubdirs -RootPath "$env:APPDATA\yuque-desktop" -Patterns @("cache","log")
    if ($yqTotal -gt 0) {
        Write-Output ("  [清理] 语雀桌面缓存: {0}" -f (Format-Size $yqTotal))
        $total += $yqTotal
    }

    Write-Output ("`n标准清理完成，共释放: {0}" -f (Format-Size $total))
    $script:TotalFreedBytes += $total
    return $total
}

# ===== 阶段3: 深度清理 =====
function Run-DeepClean {
    Write-Output "===== 阶段3: 深度清理（聊天软件缓存/媒体） ====="
    $total = 0

    Write-Output "`n[1/6] 清理微信4.0 (xwechat) 缓存..."
    $total += Clean-Path "xwechat log" "$env:APPDATA\Tencent\xwechat\log"
    $total += Clean-Path "xwechat update" "$env:APPDATA\Tencent\xwechat\update"
    $total += Clean-Path "xwechat xplugin" "$env:APPDATA\Tencent\xwechat\xplugin"

    Write-Output "`n[2/6] 清理旧版微信缓存..."
    foreach ($sub in @("log","XPlugin","xweb","radium")) {
        $total += Clean-Path "WeChat $sub" "$env:APPDATA\Tencent\WeChat\$sub"
    }

    Write-Output "`n[3/6] 清理企业微信/腾讯会议/QQ缓存..."
    $total += Clean-Path "WXWork upgrade" "$env:APPDATA\Tencent\WXWork\upgrade"
    $total += Clean-Path "WXWork wmpf_Applet" "$env:APPDATA\Tencent\WXWork\wmpf_Applet"
    $wmTotal = Clean-CacheSubdirs -RootPath "$env:APPDATA\Tencent\WeMeet\Global" -Patterns @("cache","log","tmp","crash","dump")
    if ($wmTotal -gt 0) { Write-Output ("  [清理] 腾讯会议缓存: {0}" -f (Format-Size $wmTotal)); $total += $wmTotal }
    $total += Clean-Path "QQ" "$env:APPDATA\Tencent\QQ"

    Write-Output "`n[4/6] 清理钉钉缓存..."
    foreach ($sub in @("Cache","Code Cache")) {
        $total += Clean-Path "DingTalk cef/$sub" "$env:APPDATA\DingTalkYkz\cef\$sub"
    }
    $total += Clean-Path "DingTalk log" "$env:APPDATA\DingTalkYkz\log"
    $total += Clean-Path "DingTalk 旧环境(chongqing-prod)" "$env:APPDATA\DingTalkYkz\699305@chongqing-prod.zwdingding"

    # DingTalk_108/DingTalkGov_108 缓存
    foreach ($dt in @("$env:LOCALAPPDATA\DingTalk_108","$env:LOCALAPPDATA\DingTalkGov_108")) {
        $dtTotal = Clean-CacheSubdirs -RootPath $dt -Patterns @("cache","log","tmp","crash")
        if ($dtTotal -gt 0) {
            Write-Output ("  [清理] {0} 缓存: {1}" -f (Split-Path $dt -Leaf), (Format-Size $dtTotal))
            $total += $dtTotal
        }
    }
    # DingTalk Roaming缓存
    $dtRoamingTotal = Clean-CacheSubdirs -RootPath "$env:APPDATA\DingTalk" -Patterns @("cache","log","tmp")
    if ($dtRoamingTotal -gt 0) {
        Write-Output ("  [清理] DingTalk(Roaming)缓存: {0}" -f (Format-Size $dtRoamingTotal))
        $total += $dtRoamingTotal
    }

    Write-Output "`n[5/6] 清理聊天媒体缓存（图片/视频/文件）..."
    # 钉钉图片缓存
    $total += Clean-Path "DingTalk ImageFiles" "$env:APPDATA\DingTalkYkz\699305@zwdingding\ImageFiles"

    # IM聊天媒体
    $imPath = "$env:APPDATA\im"
    if (Test-Path $imPath) {
        $imTotal = 0
        $mediaDirs = Get-ChildItem -Path $imPath -Directory -Force -ErrorAction SilentlyContinue
        foreach ($md in $mediaDirs) {
            $mediaSubDirs = Get-ChildItem -Path $md.FullName -Directory -Force -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match "Image|Video|File|Thumb" }
            foreach ($msd in $mediaSubDirs) {
                $ssz = Get-DirSize -Path $msd.FullName
                Remove-Item -Path "$($msd.FullName)\*" -Recurse -Force -ErrorAction SilentlyContinue
                $imTotal += $ssz
            }
        }
        # userPhoto
        $photoPath = "$imPath\userPhoto"
        if (Test-Path $photoPath) {
            $psz = Get-DirSize -Path $photoPath
            Remove-Item -Path "$photoPath\*" -Recurse -Force -ErrorAction SilentlyContinue
            $imTotal += $psz
        }
        if ($imTotal -gt 0) {
            Write-Output ("  [清理] IM聊天媒体缓存: {0}" -f (Format-Size $imTotal))
            $total += $imTotal
        }
    }

    Write-Output "`n[6/6] 清理下载缓存..."
    $total += Clean-Path "utForpc" "$env:APPDATA\utForpc" -Recurse

    Write-Output ("`n深度清理完成，共释放: {0}" -f (Format-Size $total))
    $script:TotalFreedBytes += $total
    return $total
}

# ===== 主入口 =====
$beforeFree = Show-DiskStatus

switch ($Mode) {
    "scan" {
        Scan-Disk
    }
    "standard" {
        Run-StandardClean | Out-Null
    }
    "deep" {
        Run-DeepClean | Out-Null
    }
    "all" {
        Run-StandardClean | Out-Null
        Write-Output ""
        Run-DeepClean | Out-Null
    }
}

$afterFree = Show-DiskStatus
$freed = [math]::Round($afterFree - $beforeFree, 2)
if ($Mode -ne "scan") {
    Write-Output ("`n===== 清理总结 =====")
    Write-Output ("清理前可用: {0} GB" -f $beforeFree)
    Write-Output ("清理后可用: {0} GB" -f $afterFree)
    Write-Output ("释放空间: ~{0} GB" -f $freed)
}
