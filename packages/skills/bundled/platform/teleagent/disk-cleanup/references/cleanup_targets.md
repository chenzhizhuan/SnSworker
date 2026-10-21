---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '0e0b5ead-6781-42de-ab89-7983b3b6e0fe'
  PropagateID: '0e0b5ead-6781-42de-ab89-7983b3b6e0fe'
  ReservedCode1: '67538c88-0fd1-441e-9f87-1a30e2a009eb'
  ReservedCode2: '67538c88-0fd1-441e-9f87-1a30e2a009eb'
---

# 磁盘清理目标参考

## 清理类别与路径

### 1. 临时文件 (temp)

| 路径 | 说明 | 安全等级 |
|------|------|----------|
| `%TEMP%` | 用户临时目录 | 安全 |
| `C:\Windows\Temp` | Windows 临时目录 | 安全 |

### 2. 缓存文件 (cache)

| 路径 | 说明 | 安全等级 |
|------|------|----------|
| `%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*` | 缩略图缓存 | 安全 |
| `%LOCALAPPDATA%\pip\Cache` | pip 缓存 | 安全 |
| `%APPDATA%\npm-cache` | npm 缓存 | 安全 |
| `%USERPROFILE%\.nuget\packages` | NuGet 包缓存 | 安全 |
| `%LOCALAPPDATA%\Microsoft\Windows\FontCache` | 字体缓存 | 安全 |

### 3. 日志文件 (log)

| 路径 | 说明 | 安全等级 |
|------|------|----------|
| `C:\Windows\Logs` | Windows 系统日志 | 安全 |
| `C:\Windows\System32\winevt\Logs` | Windows 事件日志 | 不建议删除 |
| `%LOCALAPPDATA%\Logs` | 应用日志 | 安全 |
| `%USERPROFILE%\*.log` | 用户目录下的日志文件 | 安全 |

### 4. 回收站 (recycle)

| 路径 | 说明 | 安全等级 |
|------|------|----------|
| `C:\$Recycle.Bin` | 回收站 | 安全 |

### 5. 更新缓存 (update)

| 路径 | 说明 | 安全等级 |
|------|------|----------|
| `C:\Windows\SoftwareDistribution\Download` | Windows 更新下载缓存 | 安全 |
| `C:\Windows.old` | 旧系统文件 | 需确认 |

### 6. 错误报告 (error_report)

| 路径 | 说明 | 安全等级 |
|------|------|----------|
| `%LOCALAPPDATA%\Microsoft\Windows\WER` | Windows 错误报告 | 安全 |
| `C:\Windows\PCHealth` | Windows 健康报告 | 安全 |

### 7. 预读取文件 (prefetch)

| 路径 | 说明 | 安全等级 |
|------|------|----------|
| `C:\Windows\Prefetch` | Windows 预读取文件 | 安全 |

### 8. 崩溃转储 (crash_dump)

| 路径 | 说明 | 安全等级 |
|------|------|----------|
| `C:\Windows\Minidump` | 系统崩溃转储 | 安全 |
| `%LOCALAPPDATA%\CrashDumps` | 用户模式崩溃转储 | 安全 |

### 9. 浏览器缓存 (browser_cache)

| 路径 | 说明 | 安全等级 |
|------|------|----------|
| Chrome 缓存目录 | Google Chrome 浏览器缓存 | 安全 |
| Edge 缓存目录 | Microsoft Edge 浏览器缓存 | 安全 |
| Firefox Profiles 缓存 | Firefox 浏览器缓存 | 安全 |

## 安全等级说明

- **安全**: 删除后不影响系统和应用正常运行，仅会自动重建
- **不建议删除**: 包含重要系统信息，删除可能影响系统功能
- **需确认**: 删除后不可恢复，需用户明确同意

> AI生成