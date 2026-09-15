# =====================================================================
# PPT 渲染 Worker · 把指定页的 PPTX 导出为 PNG
#
# 用法:
#   powershell -ExecutionPolicy RemoteSigned -File render-worker.ps1 `
#     -PptxPath "C:\path\to\preview.pptx" `
#     -OutPath  "C:\path\to\thumb-1.png" `
#     -PageIdx  1
# =====================================================================
param(
  [Parameter(Mandatory = $true)][string]$PptxPath,
  [Parameter(Mandatory = $true)][string]$OutPath,
  [int]$PageIdx = 1,
  [int]$Width = 1600,
  [int]$Height = 900
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 输出目录创建
$outDir = Split-Path -Parent $OutPath
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }

# 等待前序 PowerPoint 实例释放文件锁（COM Close/Quit 已在 finally 中处理）
Start-Sleep -Milliseconds 800

if (-not (Test-Path $PptxPath)) {
  Write-Error "RENDER_ERROR: 输入 PPTX 不存在: $PptxPath"
  exit 3
}

$ppt = $null
$pres = $null
try {
  $ppt = New-Object -ComObject PowerPoint.Application
  # Open(FileName, ReadOnly=$true, Untitled=$false, WithWindow=$false)
  $pres = $ppt.Presentations.Open($PptxPath, $true, $false, $false)
  $total = $pres.Slides.Count
  if ($PageIdx -lt 1 -or $PageIdx -gt $total) {
    throw "页码超出范围: $PageIdx (总页数 $total)"
  }
  $slide = $pres.Slides.Item($PageIdx)
  $slide.Export($OutPath, "PNG", $Width, $Height)
  $pres.Close(); $pres = $null
} catch {
  $msg = $_.Exception.Message
  Write-Error "RENDER_ERROR: $msg"
  exit 1
} finally {
  if ($pres) { try { $pres.Close() } catch {} }
  if ($ppt)  { try { $ppt.Quit() } catch {} }
  Start-Sleep -Milliseconds 150
  if ($ppt) { try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null } catch {} }
  [System.GC]::Collect()
  [System.GC]::WaitForPendingFinalizers()
}

if (Test-Path $OutPath) {
  Write-Output "OK $OutPath"
  exit 0
} else {
  Write-Error "RENDER_ERROR: 输出文件未生成 $OutPath"
  exit 2
}
