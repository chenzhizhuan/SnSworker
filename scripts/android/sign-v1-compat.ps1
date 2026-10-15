#Requires -Version 5.1
<#
.SYNOPSIS
    AGP 9 构建产物的 v1 (JAR) 签名补齐脚本。

.DESCRIPTION
    AGP 9.2 在 minSdk >= 24 时无条件跳过 v1 (JAR) 签名（signingConfigs DSL 与
    Variant API 的 enableV1Signing 开关均不生效），产物只有 v2/v3 签名。
    部分国产厂商安装器（华为/荣耀等）强制要求 v1 证书，缺 v1 会报
    「该安装包未包含任何证书 / 请使用官方版本进行安装」。

    本脚本对 assembleRelease 产物用 apksigner 重签，显式开启 v1+v2，
    keystore 与构建时一致（证书不变，已装设备可直接覆盖升级）。

    注意 apksigner verify 的语义：APK minSdk>=24 时 verify 默认报
    "v1: false"（表示该 SDK 范围不使用 v1），并不代表 APK 缺 v1 签名；
    需加 --min-sdk-version 23 验证，或直接检查 META-INF/*.SF/*.RSA。

.PARAMETER Apk
    assembleRelease 产出的 APK 路径（默认 build/outputs/apk/release/app-release.apk）。

.PARAMETER Keystore
    签名 keystore。默认探测顺序：
      1. $env:ANDROID_USER_HOME\.android\debug.keystore
      2. $env:USERPROFILE\.android\debug.keystore
    Gradle daemon 环境可能通过 XDG 路径定位 keystore（例如 TeleAgent 环境的
    .config\TeleAgent\users\<id>\.android\debug.keystore），与 shell 环境不同；
    跨环境构建时请显式传 -Keystore 保证与构建用证书一致。

.PARAMETER Alias / StorePass / KeyPass
    默认 androiddebugkey / android / android（标准 debug keystore 口径）。

.EXAMPLE
    .\sign-v1-compat.ps1 -Apk app\build\outputs\apk\release\app-release.apk `
        -Keystore C:\Users\Administrator\.config\TeleAgent\users\v1_public_xxx\.android\debug.keystore
#>
param(
    [string]$Apk = (Join-Path $PSScriptRoot "..\..\apps\tabtin-android\app\build\outputs\apk\release\app-release.apk"),
    [string]$Keystore,
    [string]$Alias = "androiddebugkey",
    [string]$StorePass = "android",
    [string]$KeyPass = "android"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Apk)) { throw "APK 不存在: $Apk" }

if (-not $Keystore) {
    $candidates = @()
    if ($env:ANDROID_USER_HOME) { $candidates += Join-Path $env:ANDROID_USER_HOME ".android\debug.keystore" }
    if ($env:USERPROFILE) { $candidates += Join-Path $env:USERPROFILE ".android\debug.keystore" }
    $Keystore = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $Keystore) { throw "未找到 debug.keystore，请显式传 -Keystore" }
}
if (-not (Test-Path $Keystore)) { throw "Keystore 不存在: $Keystore" }

# 自动发现 apksigner（优先 34/35/36；34+ 均支持 --v1-signing-enabled）
$sdkRoot = if ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { "$env:LOCALAPPDATA\Android\Sdk" }
$apksigner = Get-ChildItem "$sdkRoot\build-tools" -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending |
    ForEach-Object { Join-Path $_.FullName "apksigner.bat" } |
    Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $apksigner) { throw "未找到 apksigner（build-tools），请安装 Android SDK Build-Tools" }

Write-Host "[1/3] 重签（v1+v2）：$Apk"
$tmp = [System.IO.Path]::ChangeExtension($Apk, ".v1signed.tmp.apk")
& $apksigner sign `
    --ks $Keystore --ks-key-alias $Alias `
    --ks-pass "pass:$StorePass" --key-pass "pass:$KeyPass" `
    --v1-signing-enabled true --v2-signing-enabled true `
    --out $tmp $Apk
if ($LASTEXITCODE -ne 0) { throw "apksigner sign 失败" }

Write-Host "[2/3] 验证（--min-sdk-version 23 视角，v1 应为 true）"
$verify = & $apksigner verify -v --min-sdk-version 23 $tmp 2>&1 | Out-String
Write-Host $verify
if ($verify -notmatch 'Verified using v1 scheme \(JAR signing\): true') {
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    throw "v1 签名验证失败（期望 true）"
}

Write-Host "[3/3] 覆盖原文件"
Move-Item $tmp $Apk -Force
Write-Host "完成：$Apk（v1+v2 签名，keystore=$Keystore）"
