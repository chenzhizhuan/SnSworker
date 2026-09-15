---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '3e273490-4572-4df9-b336-40e6ddf9fbf9'
  PropagateID: '3e273490-4572-4df9-b336-40e6ddf9fbf9'
  ReservedCode1: 'dac89317-59fc-4afc-9a92-f5a89128a783'
  ReservedCode2: 'dac89317-59fc-4afc-9a92-f5a89128a783'
---

# Windows电脑安全基线检查参考标准

## Windows安全基线评估标准

### 合格判定条件

| 检查项 | 合格标准 |
|--------|----------|
| 账号安全 | 无弱口令、Guest已禁用、无多余管理员账号 |
| 进程检查 | 无可疑进程运行（mimikatz、ncat、psexec等） |
| 网络端口 | 高危端口(135/445/3389)未绑定公网IP，无异常监听 |
| 异常文件 | 系统目录无可疑可执行文件 |
| 登录日志 | 近7天无异常登录IP，无暴力破解痕迹 |
| 历史命令 | 无可疑PowerShell编码命令或恶意脚本执行记录 |
| 定时任务 | 无可疑定时任务，非Microsoft任务均经授权 |
| 自启动项 | 无可疑自启动项，启动路径注册表无异常 |
| 系统服务 | 危险服务(TermService/RemoteRegistry/TLNTSVR)已禁用或合理管控 |
| 防火墙配置 | 防火墙已启用，默认入站策略为阻止 |
| 共享文件夹 | 默认共享(C$/D$/Admin$)已关闭或受控 |
| 注册表安全 | UAC已启用(EnableLUA=1)，DisableCAD=0 |
| 补丁与安全软件 | 补丁滞后不超过30天，安全软件正常运行 |
| 屏幕锁定策略 | 超时<=5分钟，恢复需密码认证 |
| Defender/EDR 防护配置 | Defender 或经批准的企业 EDR 处于正常受管控状态；实时保护、防篡改和云保护未被非授权关闭，排除项与 ASR/受控文件夹访问策略经业务确认。 |
| 审计与日志保留 | 安全、系统、应用及已部署的 PowerShell/Defender/Sysmon 日志已启用并具备满足本地制度的容量和保留策略；关键审核子类别按组织策略开启。 |
| RDP/WinRM/SSH 远程访问 | 未经授权的远程访问服务已禁用；获准服务只对受信网络开放，RDP 启用 NLA 与适当 TLS，WinRM/SSH 认证和授权配置符合本地制度。 |
| 浏览器/Office 宏与代理 | 代理/PAC、hosts、浏览器策略和扩展均经授权；Office 宏策略阻止来自 Internet 的不受信任宏，受信任位置受控。 |

### 风险等级划分

- **高风险**：可能导致系统被直接入侵（如RDP暴露公网、弱口令）
- **中风险**：可能增加安全风险但需要特定条件（如补丁滞后、非必要服务）
- **低风险**：合规建议项（如日志策略优化、默认共享管控）

## 高危端口参考表

| 端口 | 服务 | 风险说明 |
|------|------|----------|
| 21 | FTP | 明文传输，易被暴力破解 |
| 22 | SSH | 密钥管理不当风险 |
| 23 | Telnet | 明文传输，建议禁用 |
| 25 | SMTP | 开放中继风险 |
| 135 | RPC | 常见攻击入口 |
| 139 | NetBIOS | 信息泄露 |
| 445 | SMB | 勒索病毒利用 |
| 1433 | MSSQL | 数据库暴露 |
| 3306 | MySQL | 数据库暴露 |
| 3389 | RDP | 远程桌面暴露 |
| 5900 | VNC | 远程控制暴露 |
| 6379 | Redis | 未授权访问 |
| 8080/8443 | Web代理 | 服务暴露 |

## 常见整改命令速查

### 禁用Guest账号
```powershell
Disable-LocalUser -Name "Guest"
```

### 关闭默认共享
```powershell
# 临时关闭
Get-SmbShare | Where-Object { $_.Name -match '\$$' } | ForEach-Object { Remove-SmbShare -Name $_.Name -Force }

# 永久关闭（注册表）
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters" -Name "AutoShareServer" -Value 0
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters" -Name "AutoShareWks" -Value 0
```

### 禁用危险服务
```powershell
Set-Service -Name "RemoteRegistry" -StartupType Disabled -Status Stopped
Set-Service -Name "TLNTSVR" -StartupType Disabled
```

### 启用UAC
```powershell
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableLUA" -Value 1
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "ConsentPromptBehaviorAdmin" -Value 2
```

> AI生成
