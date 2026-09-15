@echo off
setlocal
rem 输出统一用 UTF-8 代码页，避免中文在 GBK 终端下显示为乱码。
chcp 65001 >nul
rem 启动默认只准备 Python runtime，避免可选 Office runtime 阻塞冷启动。
if "%TABTIN_FETCH_OFFICE_RUNTIME_ON_START%"=="1" (
  call "%~dp0fetch-desktop-runtimes.bat" %*
) else (
  call "%~dp0fetch-desktop-runtimes.bat" --only python %*
)
exit /b 0
