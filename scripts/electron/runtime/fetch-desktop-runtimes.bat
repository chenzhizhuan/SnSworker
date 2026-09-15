@echo off
setlocal EnableExtensions
rem 输出统一用 UTF-8 代码页，避免中文在 GBK 终端下显示为乱码。
chcp 65001 >nul
rem Windows 入口：只调用 fetch-desktop-runtimes.ps1，不调用 .sh。
set "FETCH_PS1=%~dp0fetch-desktop-runtimes.ps1"
where powershell.exe >nul 2>&1
if errorlevel 1 (
  echo [ERROR] 未找到 powershell.exe，无法拉取桌面运行时。
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%FETCH_PS1%" %*
exit /b %ERRORLEVEL%
