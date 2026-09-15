#!/usr/bin/env powershell
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    TeleAgent 每日积分自动领取脚本 v3.9
.DESCRIPTION
    自动启动 TeleAgent 桌面客户端，定位窗口，打开个人菜单，通过像素扫描定位
    「立即领取」按钮并点击，完成每日积分领取。
    支持静默执行（无人值守），适合定时任务调用。
    
    v3.0 优化：
    - 第一步始终启动 TeleAgent 进程，确保客户端已运行且窗口就绪
    v3.1 优化：
    - 第一步改为先结束所有 TeleAgent 进程再重新启动，确保客户端处于干净状态
    v3.2 优化：
    - 第一步改回检测到进程就跳过，未检测到才启动，避免中断对话
    - 新增 BitBlt 屏幕截图方案，解决 PrintWindow 对 Electron 窗口黑屏问题
    - 修正头像点击坐标（6.6%宽 96%高），匹配实际 UI 布局
    - 截图采用 BitBlt 优先、PrintWindow 备选的双方案策略
    v3.3 优化：
    - Step 7 验证逻辑升级：新增累计积分区域像素对比作为主要验证手段
    - 点击「立即领取」前先截图记录累计积分区域像素，点击后重新截图对比
    - 累计积分区域像素有变化 = 领取成功（积分增加导致数字渲染变化）
    - 兼容原有的蓝色按钮消失/紫色按钮出现双重验证
    v3.4 优化：
    - Step 8 改为重启客户端后以新进程重新执行整个领取流程，不再仅重试点击
    - 新增 -RetryCount 参数控制重启重试次数（默认最多 1 次）
    v3.5 优化：
    - Step 1 进程检测升级：区分主进程与子进程，避免子进程误判
      * 主进程判定：有 MainWindowHandle 的进程，或命令行无 --type= 参数（Electron 主进程）
      * 仅有子进程无主进程时，判定为客户端未正常运行，清理残留后重新启动
    - 窗口就绪后增加可见性检查：窗口最小化时自动恢复（SW_RESTORE）
    - 日志输出增强：进程总数、主进程 PID、窗口句柄、可见性/最小化状态
    v3.6 优化：
    - 新增白屏检测（IsWhiteScreen）：截图白色像素占比>=90%判定为白屏，UI未渲染完成
    - 窗口不可见（IsWindowVisible=False）时不再继续执行，直接重启客户端并重试
    - 初始截图白屏时自动重启客户端并重试，不再兜底推断"今日已领"
    - Step 5 未找到按钮时先检测白屏，白屏则重启重试而非推断"已领"
    - 提取 Restart-AndRetry 函数，统一管理重启+重试逻辑
    - 重启后等待时间从5秒增至15秒，确保UI完全加载
    v3.7 优化：
    - 将 Restart-AndRetry 改为 Retry-InPlace：不再杀进程、不再重启客户端
    - 客户端运行中时杀进程会中断当前对话会话，改为仅重新聚焦窗口+等待UI渲染后重试
    - 重试等待时间保持10秒（原重启需15秒，原地重试无需等待启动）
    - Step 3 新增白屏重试循环（最多3次截图，每次间隔5秒）
    - IsWhiteScreen 改为深色像素检测法（20x20网格采样，深色像素<3判白屏）
    v3.8 优化：
    - 冷启动场景修复：客户端刚启动时窗口为加载界面（436x438），非主界面
    - 窗口就绪判定从 >100x100 改为 >800x600，排除加载/登录小窗口
    - 冷启动后额外等待10秒确保主界面完全加载
    v3.9 优化：
    - 新增自动恢复机制：检测到渲染进程崩溃/白屏等故障时，自动杀掉所有 TeleAgent 进程并重启客户端
    - Retry-InPlace 分两级重试：第1级原地重试（不杀进程），第1级失败后第2级自动重启客户端再重试
    - 新增 Restart-Client 函数：杀所有进程→等3秒→重启客户端→等窗口就绪
    - 重启后冷启动等待10秒确保UI完全加载后再执行领取流程
    #>

param(
    [string]$LogDir = "",
    [int]$RetryCount = 0
)

$ErrorActionPreference = "Stop"

# ==================== 日志函数 ====================

function Write-Log {
    param([string]$Msg)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Output "[$ts] $Msg"
}

function Write-Result {
    param(
        [int]$Code,
        [string]$Status,
        [string]$Detail = ""
    )
    $result = @{
        code      = $Code
        status    = $Status
        detail    = $Detail
        timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
    }
    Write-Output ("RESULT:" + ($result | ConvertTo-Json -Compress))
}

# ==================== Win32 API 定义 ====================

Add-Type -AssemblyName System.Drawing

$win32 = @"
using System;
using System.Runtime.InteropServices;
using System.Threading;
using System.Drawing;
using System.Drawing.Imaging;
using System.Collections.Generic;

public class Win32Helper {
    [StructLayout(LayoutKind.Sequential)]
    public struct MOUSEINPUT {
        public int dx; public int dy; public uint mouseData;
        public uint dwFlags; public uint time; public IntPtr dwExtraInfo;
    }
    [StructLayout(LayoutKind.Sequential)]
    public struct INPUT {
        public uint type; public MOUSEINPUT mi;
    }
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")]
    public static extern bool IsIconic(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")]
    public static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    [DllImport("user32.dll")]
    public static extern IntPtr GetDC(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern int ReleaseDC(IntPtr hWnd, IntPtr hDC);
    [DllImport("gdi32.dll")]
    public static extern bool BitBlt(IntPtr hdcDest, int xDest, int yDest, int w, int h, IntPtr hdcSrc, int xSrc, int ySrc, int rop);
    [DllImport("user32.dll")]
    public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, int nFlags);

    public static IntPtr FindTeleAgent() {
        IntPtr h = FindWindow(null, "TeleAgent");
        return h;
    }
    public static RECT GetWinRect(IntPtr hWnd) {
        RECT r;
        GetWindowRect(hWnd, out r);
        return r;
    }
    public static bool FocusWin(IntPtr hWnd) {
        if (IsIconic(hWnd)) ShowWindow(hWnd, 9);
        Thread.Sleep(300);
        return SetForegroundWindow(hWnd);
    }
    public static void DoClick(int x, int y) {
        SetCursorPos(x, y);
        Thread.Sleep(200);
        INPUT[] ins = new INPUT[2];
        ins[0].type = 0;
        ins[0].mi.mouseData = 0;
        ins[0].mi.dwFlags = 0x0002;
        ins[0].mi.time = 0;
        ins[0].mi.dwExtraInfo = IntPtr.Zero;
        ins[1] = ins[0];
        ins[1].mi.dwFlags = 0x0004;
        SendInput(2, ins, Marshal.SizeOf(typeof(INPUT)));
    }

    // BitBlt 截图：从屏幕 DC 复制窗口区域，不依赖窗口自身 DC 权限
    public static string CaptureScreenBitBlt(IntPtr hWnd, string path) {
        RECT r = GetWinRect(hWnd);
        int w = r.Right - r.Left;
        int h = r.Bottom - r.Top;
        if (w <= 0 || h <= 0) return null;
        try {
            Bitmap bmp = new Bitmap(w, h);
            Graphics g = Graphics.FromImage(bmp);
            IntPtr hdcDest = g.GetHdc();
            IntPtr hdcSrc = GetDC(IntPtr.Zero); // screen DC
            BitBlt(hdcDest, 0, 0, w, h, hdcSrc, r.Left, r.Top, 0x00CC0020); // SRCCOPY
            g.ReleaseHdc(hdcDest);
            ReleaseDC(IntPtr.Zero, hdcSrc);
            bmp.Save(path, ImageFormat.Png);
            int blackCount = 0;
            for (int i = 0; i < 100 && i < w * h; i++) {
                int px = (i * 37) % w;
                int py = (i * 53) % h;
                if (bmp.GetPixel(px, py).R == 0 && bmp.GetPixel(px, py).G == 0 && bmp.GetPixel(px, py).B == 0) {
                    blackCount++;
                }
            }
            g.Dispose();
            bmp.Dispose();
            if (blackCount >= 95) return null;
            return path;
        } catch (Exception) {
            return null;
        }
    }

    // PrintWindow 截图（备选方案）
    public static string CaptureScreenPW(IntPtr hWnd, string path) {
        RECT r = GetWinRect(hWnd);
        int w = r.Right - r.Left;
        int h = r.Bottom - r.Top;
        if (w <= 0 || h <= 0) return null;
        try {
            Bitmap bmp = new Bitmap(w, h);
            Graphics g = Graphics.FromImage(bmp);
            IntPtr hdc = g.GetHdc();
            PrintWindow(hWnd, hdc, 2); // PW_RENDERFULLCONTENT
            g.ReleaseHdc(hdc);
            bmp.Save(path, ImageFormat.Png);
            int blackCount = 0;
            for (int i = 0; i < 100 && i < w * h; i++) {
                int px = (i * 37) % w;
                int py = (i * 53) % h;
                if (bmp.GetPixel(px, py).R == 0 && bmp.GetPixel(px, py).G == 0 && bmp.GetPixel(px, py).B == 0) {
                    blackCount++;
                }
            }
            g.Dispose();
            bmp.Dispose();
            if (blackCount >= 95) return null;
            return path;
        } catch (Exception) {
            return null;
        }
    }

    // 定位蓝色按钮
    public static int[] FindBlueBtn(string imgPath, int yStart, int yEnd, int xMax) {
        Bitmap img = (Bitmap)Image.FromFile(imgPath);
        var rows = new List<int>();
        for (int y = yStart; y < yEnd && y < img.Height; y++) {
            int cnt = 0, rxMin = int.MaxValue, rxMax = 0;
            for (int x = 0; x < xMax && x < img.Width; x++) {
                Color c = img.GetPixel(x, y);
                if (c.B > 140 && c.B > c.R + 50 && c.B > c.G + 30 && c.R < 120 && c.G < 160) {
                    cnt++;
                    if (x < rxMin) rxMin = x;
                    if (x > rxMax) rxMax = x;
                }
            }
            int width = rxMax - rxMin + 1;
            if (cnt >= 150 && width >= 180) { rows.Add(y); }
        }
        img.Dispose();
        if (rows.Count < 5) return null;
        int bestIdx = 0, bestLen = 1, curIdx = 0, curLen = 1;
        for (int i = 1; i < rows.Count; i++) {
            if (rows[i] - rows[i - 1] <= 3) { curLen++; if (curLen > bestLen) { bestLen = curLen; bestIdx = curIdx; } }
            else { curIdx = i; curLen = 1; }
        }
        int btnYMin = rows[bestIdx], btnYMax = rows[bestIdx + bestLen - 1];
        img = (Bitmap)Image.FromFile(imgPath);
        int fxMin = int.MaxValue, fxMax = 0;
        for (int y = btnYMin; y <= btnYMax && y < img.Height; y++) {
            for (int x = 0; x < xMax && x < img.Width; x++) {
                Color c = img.GetPixel(x, y);
                if (c.B > 140 && c.B > c.R + 50 && c.B > c.G + 30 && c.R < 120 && c.G < 160) {
                    if (x < fxMin) fxMin = x; if (x > fxMax) fxMax = x;
                }
            }
        }
        img.Dispose();
        if (fxMin == int.MaxValue) return null;
        return new int[] { (fxMin + fxMax) / 2, (btnYMin + btnYMax) / 2, btnYMin, btnYMax };
    }

    // 定位紫色按钮
    public static int[] FindPurpleBtn(string imgPath, int yStart, int yEnd, int xMax) {
        Bitmap img = (Bitmap)Image.FromFile(imgPath);
        var rows = new List<int>();
        for (int y = yStart; y < yEnd && y < img.Height; y++) {
            int cnt = 0, rxMin = int.MaxValue, rxMax = 0;
            for (int x = 0; x < xMax && x < img.Width; x++) {
                Color c = img.GetPixel(x, y);
                bool isBlue = (c.B > 140 && c.B > c.R + 50 && c.R < 120);
                if (c.B > 110 && c.B > c.G + 10 && c.B > c.R && c.R > 60 && !isBlue) {
                    cnt++; if (x < rxMin) rxMin = x; if (x > rxMax) rxMax = x;
                }
            }
            int width = rxMax - rxMin + 1;
            if (cnt >= 80 && width >= 140) { rows.Add(y); }
        }
        img.Dispose();
        if (rows.Count < 5) return null;
        int bestIdx = 0, bestLen = 1, curIdx = 0, curLen = 1;
        for (int i = 1; i < rows.Count; i++) {
            if (rows[i] - rows[i - 1] <= 3) { curLen++; if (curLen > bestLen) { bestLen = curLen; bestIdx = curIdx; } }
            else { curIdx = i; curLen = 1; }
        }
        int btnYMin = rows[bestIdx], btnYMax = rows[bestIdx + bestLen - 1];
        img = (Bitmap)Image.FromFile(imgPath);
        int fxMin = int.MaxValue, fxMax = 0;
        for (int y = btnYMin; y <= btnYMax && y < img.Height; y++) {
            for (int x = 0; x < xMax && x < img.Width; x++) {
                Color c = img.GetPixel(x, y);
                bool isBlue = (c.B > 140 && c.B > c.R + 50 && c.R < 120);
                if (c.B > 110 && c.B > c.G + 10 && c.B > c.R && c.R > 60 && !isBlue) {
                    if (x < fxMin) fxMin = x; if (x > fxMax) fxMax = x;
                }
            }
        }
        img.Dispose();
        if (fxMin == int.MaxValue) return null;
        return new int[] { (fxMin + fxMax) / 2, (btnYMin + btnYMax) / 2, btnYMin, btnYMax };
    }

    // 对比两个截图指定区域的像素差异（返回差异像素数）
    public static int CountPixelDiff(string img1Path, string img2Path, int xStart, int xEnd, int yStart, int yEnd) {
        Bitmap img1 = (Bitmap)Image.FromFile(img1Path);
        Bitmap img2 = (Bitmap)Image.FromFile(img2Path);
        int diff = 0;
        int xEndClamped = Math.Min(Math.Min(img1.Width, img2.Width), xEnd);
        int yEndClamped = Math.Min(Math.Min(img1.Height, img2.Height), yEnd);
        for (int y = yStart; y < yEndClamped; y += 4) {
            for (int x = xStart; x < xEndClamped; x += 4) {
                Color c1 = img1.GetPixel(x, y); Color c2 = img2.GetPixel(x, y);
                if (Math.Abs(c1.R - c2.R) > 30 || Math.Abs(c1.G - c2.G) > 30 || Math.Abs(c1.B - c2.B) > 30) diff++;
            }
        }
        img1.Dispose(); img2.Dispose();
        return diff;
    }

    // 像素差异比较（精确区域，逐像素比较）
    public static int CountPixelDiffExact(string img1Path, string img2Path, int xStart, int xEnd, int yStart, int yEnd) {
        Bitmap img1 = (Bitmap)Image.FromFile(img1Path);
        Bitmap img2 = (Bitmap)Image.FromFile(img2Path);
        int diff = 0;
        int xEndClamped = Math.Min(Math.Min(img1.Width, img2.Width), xEnd);
        int yEndClamped = Math.Min(Math.Min(img1.Height, img2.Height), yEnd);
        for (int y = yStart; y < yEndClamped; y++) {
            for (int x = xStart; x < xEndClamped; x++) {
                Color c1 = img1.GetPixel(x, y); Color c2 = img2.GetPixel(x, y);
                if (Math.Abs(c1.R - c2.R) > 20 || Math.Abs(c1.G - c2.G) > 20 || Math.Abs(c1.B - c2.B) > 20) diff++;
            }
        }
        img1.Dispose(); img2.Dispose();
        return diff;
    }

    // 白屏检测：UI未渲染完成时界面为纯白，无任何深色像素（文字/图标/边框）
    // v3.7: 改为深色像素检测法——TeleAgent UI 使用浅色主题（背景 R248 G249 B250），
    //        白色像素占比高达92%，用白色占比检测会误判。
    //        但正常 UI 必然包含深色像素（文字、图标、按钮等），
    //        纯白屏则完全没有深色像素。
    //        20x20网格采样400点，检测是否存在深色像素，无深色像素 = 白屏
    public static bool IsWhiteScreen(string imgPath) {
        try {
            Bitmap img = (Bitmap)Image.FromFile(imgPath);
            int darkCount = 0;
            int gridCols = 20, gridRows = 20;
            for (int row = 0; row < gridRows; row++) {
                for (int col = 0; col < gridCols; col++) {
                    int px = (int)((col + 0.5) / gridCols * img.Width);
                    int py = (int)((row + 0.5) / gridRows * img.Height);
                    Color c = img.GetPixel(px, py);
                    if (c.R < 200 || c.G < 200 || c.B < 200) darkCount++;
                }
            }
            img.Dispose();
            // 正常 UI 有 10+ 深色像素，纯白屏为 0；阈值为 3 给余量
            return darkCount < 3;
        } catch (Exception) {
            return false;
        }
    }
}
"@

try {
    Add-Type -TypeDefinition $win32 -Language CSharp -ReferencedAssemblies @("System.Drawing") -ErrorAction Stop
    Write-Log "Win32 类型加载成功"
} catch {
    Write-Log "Win32 类型加载失败: $($_.Exception.Message)"
    Write-Result -Code 3 -Status "type_load_error" -Detail "C# type compile failed: $($_.Exception.Message)"
    exit 3
}

# ==================== 脚本路径（供函数使用）====================
$script:ScriptPath = $MyInvocation.MyCommand.Path

# ==================== 自动重启客户端函数（v3.9 新增）====================

function Restart-Client {
    Write-Log "Restart-Client: killing all TeleAgent processes and restarting..."
    
    # 杀掉所有 TeleAgent 进程（主进程 + GPU + 渲染 + 网络 + 守护等所有子进程）
    $allProcs = @(Get-Process -Name "TeleAgent" -ErrorAction SilentlyContinue)
    if ($allProcs.Count -gt 0) {
        Write-Log "  killing $($allProcs.Count) TeleAgent process(es)..."
        $allProcs | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
    }
    
    # 确认进程已全部退出
    $remaining = @(Get-Process -Name "TeleAgent" -ErrorAction SilentlyContinue)
    if ($remaining.Count -gt 0) {
        Write-Log "  WARNING: $($remaining.Count) process(es) still alive, force killing again..."
        $remaining | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    
    # 重新启动客户端
    $teleAgentExe = "D:\Program Files\TeleAgent\TeleAgent.exe"
    if (-not (Test-Path $teleAgentExe)) {
        Write-Log "  ERROR: TeleAgent.exe not found at $teleAgentExe"
        return $false
    }
    
    Write-Log "  starting TeleAgent.exe..."
    Start-Process -FilePath $teleAgentExe
    Start-Sleep -Seconds 5
    
    # 等待窗口就绪（与主流程 Step 1 相同的逻辑：>800x600）
    $restartHwnd = [IntPtr]::Zero
    $waitMax = 30
    for ($i = 0; $i -lt $waitMax; $i++) {
        $restartHwnd = [Win32Helper]::FindTeleAgent()
        if ($restartHwnd -eq [IntPtr]::Zero) {
            $proc = Get-Process -Name "TeleAgent" -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
            if ($proc) { $restartHwnd = [IntPtr]$proc.MainWindowHandle }
        }
        if ($restartHwnd -ne [IntPtr]::Zero) {
            $winRect = [Win32Helper]::GetWinRect($restartHwnd)
            $w = $winRect.Right - $winRect.Left
            $h = $winRect.Bottom - $winRect.Top
            if ($w -gt 800 -and $h -gt 600) {
                Write-Log "  window ready after restart: hwnd=$restartHwnd, size=${w}x${h} (waited $($i*2)s)"
                break
            }
        }
        Start-Sleep -Seconds 2
    }
    
    if ($restartHwnd -eq [IntPtr]::Zero) {
        Write-Log "  ERROR: window not found after restart"
        return $false
    }
    
    # 冷启动后等待 UI 完全加载
    Write-Log "  cold start after restart, waiting 10s for UI to fully load..."
    Start-Sleep -Seconds 10
    
    return $true
}

# ==================== 重试函数（v3.9 两级重试）====================

function Retry-InPlace {
    param([string]$Reason)
    Write-Log "Retry-InPlace: $Reason"

    $maxRetry = 1
    if ($RetryCount -ge $maxRetry) {
        Write-Log "max in-place retry reached ($maxRetry), trying client restart..."
        
        # v3.9: 原地重试用完后，自动重启客户端再试一次
        $restartOk = Restart-Client
        if (-not $restartOk) {
            Write-Log "client restart failed, giving up"
            Write-Result -Code 5 -Status "claim_unverified" -Detail "$Reason - client restart failed, please check manually"
            exit 5
        }
        
        # 重启成功后以新进程重新执行脚本（RetryCount 跳过原地重试，直接走正常流程）
        Write-Log "  client restarted, relaunching script (post-restart)..."
        $retryOutput = & powershell -ExecutionPolicy Bypass -File $script:ScriptPath -RetryCount 0 2>&1
        Write-Output $retryOutput
        
        $resultLine = $retryOutput | Where-Object { $_ -match '^RESULT:' } | Select-Object -Last 1
        if ($resultLine) {
            exit 0
        }
        
        Write-Log "post-restart script completed without RESULT"
        Write-Result -Code 5 -Status "claim_unverified" -Detail "post-restart script completed without confirmation, please check manually"
        exit 5
    }

    # --- 第1级：原地重试（不杀进程、不重启客户端）---
    # Close menu if hwnd is valid (click blank area)
    if ($hwnd -ne $null -and $hwnd -ne [IntPtr]::Zero) {
        try {
            $rect = [Win32Helper]::GetWinRect($hwnd)
            [Win32Helper]::DoClick($rect.Left + [int](($rect.Right - $rect.Left) * 0.5), $rect.Top + [int](($rect.Bottom - $rect.Top) * 0.3))
            Start-Sleep -Milliseconds 500
        } catch { }
    }

    Write-Log "  [level 1] re-focusing window and waiting for UI to settle..."
    if ($hwnd -ne $null -and $hwnd -ne [IntPtr]::Zero) {
        try {
            [Win32Helper]::FocusWin($hwnd) | Out-Null
        } catch { }
    }
    Start-Sleep -Seconds 10

    # Relaunch script with incremented retry count
    Write-Log "  [level 1] relaunching script (retry $($RetryCount + 1))..."
    $retryOutput = & powershell -ExecutionPolicy Bypass -File $script:ScriptPath -RetryCount ($RetryCount + 1) 2>&1
    Write-Output $retryOutput

    # Extract RESULT from child process
    $resultLine = $retryOutput | Where-Object { $_ -match '^RESULT:' } | Select-Object -Last 1
    if ($resultLine) {
        exit 0
    }

    # --- 第1级原地重试失败，进入第2级：自动重启客户端 ---
    Write-Log "  [level 1] in-place retry failed, proceeding to [level 2] client restart..."
    $restartOk = Restart-Client
    if (-not $restartOk) {
        Write-Log "client restart failed, giving up"
        Write-Result -Code 5 -Status "claim_unverified" -Detail "$Reason - client restart failed after in-place retry, please check manually"
        exit 5
    }

    Write-Log "  [level 2] client restarted, relaunching script (post-restart)..."
    $retryOutput = & powershell -ExecutionPolicy Bypass -File $script:ScriptPath -RetryCount 0 2>&1
    Write-Output $retryOutput

    $resultLine = $retryOutput | Where-Object { $_ -match '^RESULT:' } | Select-Object -Last 1
    if ($resultLine) {
        exit 0
    }

    Write-Log "post-restart script completed without RESULT"
    Write-Result -Code 5 -Status "claim_unverified" -Detail "retry exhausted (in-place + client restart), please check manually"
    exit 5
}

# ==================== 主流程 ====================

Write-Log "=== TeleAgent daily points claim v3.9 ==="
if ($RetryCount -gt 0) {
    Write-Log "  (retry attempt $RetryCount)"
}

$workDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$tempDir = Join-Path $workDir ".temp"
if (-not (Test-Path $tempDir)) {
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
}
$ts = Get-Date -Format "yyyyMMdd_HHmmss"

# TeleAgent.exe path
$teleAgentExe = "D:\Program Files\TeleAgent\TeleAgent.exe"

# Step 0: clean old temp files
Write-Log "Step 0: clean old temp files..."
$cutoff = (Get-Date).AddDays(-1)
$oldFiles = Get-ChildItem -Path $tempDir -Filter "*.png" -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt $cutoff }
if ($oldFiles) {
    $oldFiles | Remove-Item -Force
    Write-Log "cleaned $(@($oldFiles).Count) old files"
} else {
    Write-Log "no old files"
}

# Step 1: start TeleAgent if not running, skip if already running
Write-Log "Step 1: start TeleAgent and find window..."

# --- v3.5 改进：区分主进程与子进程 ---
# Electron 应用会生成多个同名进程：主进程（Main）、GPU、渲染、网络服务等
# Get-Process -Name "TeleAgent" 会匹配所有同名进程，Select-Object -First 1 可能取到子进程
# 主进程判定标准：
#   1. 有 MainWindowHandle 的进程（持有窗口）
#   2. 命令行不含 --type= 参数（Electron 子进程命令行都带 --type=gpu-process/renderer/utility 等）
$allProcs = @(Get-Process -Name "TeleAgent" -ErrorAction SilentlyContinue)
$mainProc = $null

if ($allProcs.Count -gt 0) {
    # 优先：有窗口句柄的进程（主进程持有主窗口）
    $mainProc = $allProcs | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
    if (-not $mainProc) {
        # 备选：命令行不含 --type= 的进程（Electron 主进程特征）
        foreach ($p in $allProcs) {
            try {
                $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)" -ErrorAction SilentlyContinue).CommandLine
                if ($cmd -and $cmd -notmatch '--type=') {
                    $mainProc = $p
                    break
                }
            } catch { }
        }
    }

    if ($mainProc) {
        Write-Log "TeleAgent main process running (PID=$($mainProc.Id), total $($allProcs.Count) processes)"
    } else {
        Write-Log "WARNING: $($allProcs.Count) TeleAgent process(es) found but NO main process (only sub-processes)"
        Write-Log "  -> client not in normal state, cleaning up leftover processes and restarting..."
        $allProcs | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        $mainProc = $null
    }
}

if (-not $mainProc) {
    Write-Log "TeleAgent not running, starting..."
    if (Test-Path $teleAgentExe) {
        Start-Process -FilePath $teleAgentExe
        Write-Log "TeleAgent.exe started, waiting for process..."
        Start-Sleep -Seconds 5
    } else {
        Write-Log "ERROR: TeleAgent.exe not found at $teleAgentExe"
        Write-Result -Code 2 -Status "client_not_running" -Detail "TeleAgent.exe not found: $teleAgentExe"
        exit 2
    }
}

# Track if this is a cold start (client was not running before)
$coldStart = -not $mainProc

# Now find the window (poll up to 60 seconds)
# v3.8: 窗口就绪判定从 >100x100 改为 >800x600
# TeleAgent 冷启动时先出现加载/登录小窗口（436x438），需等待主界面窗口出现
$hwnd = [IntPtr]::Zero
$waitMax = 30
$minReadyW = 800
$minReadyH = 600
for ($i = 0; $i -lt $waitMax; $i++) {
    # Try FindWindow
    $hwnd = [Win32Helper]::FindTeleAgent()
    if ($hwnd -eq [IntPtr]::Zero) {
        # Fallback: process lookup (main process with window)
        $proc = Get-Process -Name "TeleAgent" -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
        if ($proc) { $hwnd = [IntPtr]$proc.MainWindowHandle }
    }
    if ($hwnd -ne [IntPtr]::Zero) {
        $winRect = [Win32Helper]::GetWinRect($hwnd)
        $w = $winRect.Right - $winRect.Left
        $h = $winRect.Bottom - $winRect.Top
        if ($w -gt $minReadyW -and $h -gt $minReadyH) {
            Write-Log "window ready: hwnd=$hwnd, size=${w}x${h} (waited $($i*2)s)"
            break
        }
        # Log small window for debugging
        if ($i -eq 0 -and $w -gt 0 -and $h -gt 0) {
            Write-Log "  found small window ${w}x${h}, waiting for main UI (>${minReadyW}x${minReadyH})..."
        }
    } elseif ($i -eq 0) {
        Write-Log "  waiting for window..."
    }
    Start-Sleep -Seconds 2
}

if ($hwnd -eq [IntPtr]::Zero) {
    Write-Log "ERROR: window not found after 60s"
    Write-Result -Code 2 -Status "client_not_running" -Detail "TeleAgent window not ready after 60s"
    exit 2
}

# v3.8: 冷启动后额外等待确保主界面完全加载
if ($coldStart) {
    Write-Log "cold start detected, waiting 10s for main UI to fully load..."
    Start-Sleep -Seconds 10
} else {
    Start-Sleep -Seconds 3
}
Write-Log "window hwnd: $hwnd"

# --- v3.5 改进：窗口可见性检查 ---
# 窗口可能存在但不可见（最小化/隐藏），导致截图截到桌面，误判"今日已领"
# 最小化时自动恢复（SW_RESTORE=9），并记录状态日志
$isIconic = [Win32Helper]::IsIconic($hwnd)
if ($isIconic) {
    Write-Log "  WARNING: window is minimized, restoring..."
    [Win32Helper]::ShowWindow($hwnd, 9) | Out-Null
    Start-Sleep -Seconds 1
    Write-Log "  window restored"
}

# 获取窗口可见性状态（IsWindowVisible）
Add-Type -MemberDefinition '
[DllImport("user32.dll")]
public static extern bool IsWindowVisible(IntPtr hWnd);
' -Namespace Win32 -Name Visibility -ErrorAction SilentlyContinue
$isVisible = [Win32.Visibility]::IsWindowVisible($hwnd)
Write-Log "  window visible: $isVisible, minimized: $isIconic"

# v3.6: 窗口不可见时不应继续执行（截图会截到桌面，导致误判）
if (-not $isVisible) {
    Write-Log "  WARNING: window not visible after restore, UI may not be loaded"
    Retry-InPlace "window not visible (IsWindowVisible=False), UI may not be rendered"
}

# Step 2: focus window
Write-Log "Step 2: focus window..."
[Win32Helper]::FocusWin($hwnd) | Out-Null
Start-Sleep -Milliseconds 800
$fg = [Win32Helper]::GetForegroundWindow()
Write-Log "foreground window: $fg"

$rect = [Win32Helper]::GetWinRect($hwnd)
$winX = $rect.Left
$winY = $rect.Top
$winW = $rect.Right - $rect.Left
$winH = $rect.Bottom - $rect.Top
Write-Log "window: ($winX, $winY) ${winW}x${winH}"

if ($winW -le 0 -or $winH -le 0) {
    Write-Result -Code 3 -Status "window_error" -Detail "window size invalid"
    exit 3
}

# Screenshot function: BitBlt first, PrintWindow fallback
function Capture-Window {
    param([string]$Path)
    $captureOk = $false
    for ($retry = 1; $retry -le 3; $retry++) {
        # Try BitBlt from screen DC first
        $result = [Win32Helper]::CaptureScreenBitBlt($hwnd, $Path)
        if ($result -and (Test-Path $Path) -and (Get-Item $Path).Length -gt 10000) {
            $captureOk = $true
            break
        }
        Write-Log "  BitBlt failed/black(retry $retry/3), try PrintWindow..."
        # Fallback: PrintWindow
        $result2 = [Win32Helper]::CaptureScreenPW($hwnd, $Path)
        if ($result2 -and (Test-Path $Path) -and (Get-Item $Path).Length -gt 10000) {
            $captureOk = $true
            Write-Log "  PrintWindow ok"
            break
        }
        Write-Log "  both failed, refocus..."
        [Win32Helper]::FocusWin($hwnd) | Out-Null
        Start-Sleep -Milliseconds 1000
    }
    if (-not $captureOk) {
        Write-Log "ERROR: 3 captures all failed"
        Write-Result -Code 3 -Status "capture_error" -Detail "screenshot failed (BitBlt+PrintWindow both black)"
        exit 3
    }
}

# Step 3: initial screenshot (with white screen retry)
$cap1 = Join-Path $tempDir "cap_${ts}_1.png"
$whiteMaxRetry = 3
for ($whiteAttempt = 1; $whiteAttempt -le $whiteMaxRetry; $whiteAttempt++) {
    Capture-Window -Path $cap1
    $isWhite = [Win32Helper]::IsWhiteScreen($cap1)
    if (-not $isWhite) {
        Write-Log "Step 3: initial screenshot done (attempt $whiteAttempt)"
        break
    }
    Write-Log "  white screen detected (attempt $whiteAttempt/$whiteMaxRetry), waiting 5s..."
    if ($whiteAttempt -lt $whiteMaxRetry) {
        # Re-focus and wait for UI rendering
        [Win32Helper]::FocusWin($hwnd) | Out-Null
        Start-Sleep -Seconds 5
    }
}
if ($isWhite) {
    Write-Log "  WARNING: white screen after $whiteMaxRetry attempts, UI not rendered"
    Retry-InPlace "white screen detected after $whiteMaxRetry screenshot attempts, UI not loaded"
}

# Step 4: click avatar to open menu (with verification and retry)
$cap2 = Join-Path $tempDir "cap_${ts}_2.png"
$menuOpened = $false

for ($attempt = 1; $attempt -le 3; $attempt++) {
    $rect = [Win32Helper]::GetWinRect($hwnd)
    $winX = $rect.Left
    $winY = $rect.Top
    $winW = $rect.Right - $rect.Left
    $winH = $rect.Bottom - $rect.Top

    # Avatar coordinates: 6.6% width, 96% height (measured from actual UI)
    # Attempt 2: 7.5% width, 94% height
    # Attempt 3: 5.8% width, 97% height
    $ax = $winX + [int]($winW * 0.066)
    $ay = $winY + [int]($winH * 0.96)
    if ($attempt -eq 2) {
        $ax = $winX + [int]($winW * 0.075)
        $ay = $winY + [int]($winH * 0.94)
    } elseif ($attempt -eq 3) {
        $ax = $winX + [int]($winW * 0.058)
        $ay = $winY + [int]($winH * 0.97)
    }

    Write-Log "Step 4: click avatar (attempt ${attempt}) ($ax, $ay)..."
    [Win32Helper]::DoClick($ax, $ay)
    Start-Sleep -Milliseconds 1200

    Capture-Window -Path $cap2

    # Verify menu opened: compare pixel diff in left area
    $diffXEnd = [int]($winW * 0.30)
    $diffYStart = [int]($winH * 0.50)
    $pixelDiff = [Win32Helper]::CountPixelDiff($cap1, $cap2, 0, $diffXEnd, $diffYStart, $winH)
    Write-Log "  pixel diff: $pixelDiff (threshold: 100)"

    if ($pixelDiff -gt 100) {
        Write-Log "  menu opened"
        $menuOpened = $true
        break
    } else {
        Write-Log "  menu not detected, retry..."
        if ($attempt -lt 3) {
            [Win32Helper]::DoClick($winX + [int]($winW * 0.5), $winY + [int]($winH * 0.3))
            Start-Sleep -Milliseconds 500
        }
    }
}

if (-not $menuOpened) {
    Write-Log "menu open verification failed (3 retries), continue scanning..."
}

# Step 5: scan for blue button
$scanYStart = [int]($winH * 0.63)
$scanYEnd = $winH
$scanXMax = [int]($winW * 0.22)

Write-Log "Step 5: scan blue button (y=$scanYStart-$scanYEnd, xMax=$scanXMax)..."
$btn = [Win32Helper]::FindBlueBtn($cap2, $scanYStart, $scanYEnd, $scanXMax)

if ($btn -eq $null) {
    Write-Log "  not found in main range, expand (y from 40%)..."
    $btnCheck = [Win32Helper]::FindBlueBtn($cap2, [int]($winH * 0.40), $scanYEnd, $scanXMax)
    if ($btnCheck -ne $null) {
        $btn = $btnCheck
        Write-Log "  found in expanded range"
    }
}

if ($btn -eq $null) {
    Write-Log "blue button not found"

    # Check for purple "already claimed" button
    $purpleBtn = [Win32Helper]::FindPurpleBtn($cap2, [int]($winH * 0.50), $scanYEnd, $scanXMax)
    if ($purpleBtn -ne $null) {
        Write-Log "purple button detected, already claimed"
        [Win32Helper]::DoClick($winX + [int]($winW * 0.5), $winY + [int]($winH * 0.3))
        Start-Sleep -Milliseconds 500
        Write-Result -Code 1 -Status "already_claimed" -Detail "already claimed today (purple button detected)"
        exit 1
    }

    # v3.6: 未找到按钮时先检测白屏，白屏则重启重试而非推断"已领"
    $isWhiteScreen = [Win32Helper]::IsWhiteScreen($cap2)
    if ($isWhiteScreen) {
        Write-Log "  white screen detected, UI not rendered, retrying in-place..."
        Retry-InPlace "white screen detected during button scan, UI not loaded"
    }

    Write-Log "no blue or purple button, infer already claimed"
    [Win32Helper]::DoClick($winX + [int]($winW * 0.5), $winY + [int]($winH * 0.3))
    Start-Sleep -Milliseconds 500
    Write-Result -Code 1 -Status "already_claimed" -Detail "already claimed today"
    exit 1
}

$btnCx = $btn[0]
$btnCy = $btn[1]
$screenX = $winX + $btnCx
$screenY = $winY + $btnCy
Write-Log "blue button center: ($btnCx, $btnCy) screen: ($screenX, $screenY)"

# 累计积分区域定义（基于实际 UI 测量）
# 累计积分数字位于个人菜单中，比例约 x:10.8%-13.7%, y:75.4%-78.1%
$cumXStart = [int]($winW * 0.09)
$cumXEnd = [int]($winW * 0.16)
$cumYStart = [int]($winH * 0.73)
$cumYEnd = [int]($winH * 0.80)

# Step 6: 点击前先截图记录累计积分区域
Write-Log "Step 6: record cumulative points area before click..."
$capBeforeClick = Join-Path $tempDir "cap_${ts}_before.png"
Capture-Window -Path $capBeforeClick

# Step 6b: click claim button
Write-Log "Step 6b: click claim ($screenX, $screenY)..."
[Win32Helper]::DoClick($screenX, $screenY)
Start-Sleep -Milliseconds 1800

# Step 7: verify - 三重验证：累计积分区域像素变化 + 蓝色按钮消失 + 紫色按钮出现
# 首次点击后按钮状态刷新可能有延迟（实测需2-3秒），先等待再截图验证
Start-Sleep -Milliseconds 1500
$cap3 = Join-Path $tempDir "cap_${ts}_3.png"
Capture-Window -Path $cap3

# 验证1：累计积分区域像素是否变化（主要验证手段）
# 累计积分数字变化（如 2200 -> 2300）必然导致该区域像素变化
$pointsChanged = $false
$pixelDiffPoints = [Win32Helper]::CountPixelDiffExact($capBeforeClick, $cap3, $cumXStart, $cumXEnd, $cumYStart, $cumYEnd)
Write-Log "Step 7: cumulative points area pixel diff: $pixelDiffPoints (threshold: 5)"
if ($pixelDiffPoints -gt 5) {
    $pointsChanged = $true
    Write-Log "Step 7: cumulative points area changed, claim confirmed"
}

# 验证2：蓝色按钮是否消失
$btnAfter = [Win32Helper]::FindBlueBtn($cap3, [int]($winH * 0.40), $scanYEnd, $scanXMax)
Write-Log "Step 7: blue button after click: $(if ($btnAfter -eq $null) {'gone'} else {'still there'})"

# 若蓝色按钮仍在，额外等待2秒并重新截图复查（避免状态刷新延迟导致的误判）
if ($btnAfter -ne $null) {
    Start-Sleep -Milliseconds 2000
    $cap3b = Join-Path $tempDir "cap_${ts}_3b.png"
    Capture-Window -Path $cap3b
    $btnAfter = [Win32Helper]::FindBlueBtn($cap3b, [int]($winH * 0.40), $scanYEnd, $scanXMax)
    Write-Log "Step 7b: blue button after extra wait: $(if ($btnAfter -eq $null) {'gone'} else {'still there'})"
}

# 验证3：紫色按钮是否出现
$purpleAfter = [Win32Helper]::FindPurpleBtn($cap3, [int]($winH * 0.50), $scanYEnd, $scanXMax)
Write-Log "  purple button: $(if ($purpleAfter -ne $null) {'appeared'} else {'not found'})"

# 综合判断：累计积分增加 或 (蓝色按钮消失) 均算成功
if ($pointsChanged) {
    [Win32Helper]::DoClick($winX + [int]($winW * 0.5), $winY + [int]($winH * 0.3))
    Start-Sleep -Milliseconds 500
    Write-Log "claim success (cumulative points area changed)"
    Write-Result -Code 0 -Status "success" -Detail "daily points claimed successfully (cumulative points area pixel diff: $pixelDiffPoints)"
    exit 0
}

if ($btnAfter -eq $null) {
    if ($purpleAfter -ne $null) {
        Write-Log "claim success (blue -> purple)"
    } else {
        Write-Log "claim success (blue gone)"
    }
    [Win32Helper]::DoClick($winX + [int]($winW * 0.5), $winY + [int]($winH * 0.3))
    Start-Sleep -Milliseconds 500
    Write-Result -Code 0 -Status "success" -Detail "daily points claimed successfully (button changed)"
    exit 0
}

# Step 8: 验证未通过，调用 Retry-InPlace 原地重试（不重启客户端）
Write-Log "Step 8: first click unverified, calling Retry-InPlace..."
Retry-InPlace "click verification failed (Step 7), retrying in-place"
