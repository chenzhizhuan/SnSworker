# Windows 应急响应排查流程 - 检查项清单

本文档列出了 15 个排查流程的详细检查项目录。具体命令请参见 `windows-commands.md`，详细的解读要点请参见 `windows-analysis-guide.md`。

---

## 0. 快速全面排查

自动执行所有流程中的 18 项关键检查，并汇总分析结果。适合首次排查或需要快速评估系统状态的场景。

**执行顺序**：
1. 预检（环境信息）
2. 账号安全 → 进程检查 → 网络端口 → 异常文件
3. 登录日志 → 历史命令 → 定时任务 → 自启动项
4. 系统服务 → 防火墙 → 共享 → 注册表安全
5. 补丁安全软件 → 屏幕锁定 → Defender/EDR
6. 审计日志 → 远程访问 → 浏览器代理
7. 生成综合报告

---

## 1. 系统信息与账号安全

### 系统基础信息
- 主机名与域成员资格
- 操作系统版本与架构
- 系统启动时间与运行时长
- 时区与本地时间
- PowerShell 版本与执行策略
- .NET Framework 版本

### 账号安全分析
- 本地用户列表与状态
  - 检查可登录用户（Enabled=True）
  - 检查 Administrator 组成员
  - 检查 Guest 账户状态
  - 检查密码过期策略
  - 检查空密码账户
  - 检查最近创建的用户（近 30 天）
- 用户组信息
  - Administrators 组成员
  - Remote Desktop Users 组
  - Power Users 组
  - Backup Operators 组
- 密码策略
  - 密码最小长度
  - 密码复杂度要求
  - 密码历史记录
  - 账户锁定策略
- 特权分配
  - SeDebugPrivilege（调试权限）
  - SeTakeOwnershipPrivilege（取得所有权）
  - SeBackupPrivilege（备份权限）

### 域环境检查（如适用）
- 域成员资格
- 域控制器信息
- 组策略应用状态
- 域信任关系

---

## 2. 进程与服务排查

### 基础进程分析
- 运行中进程列表
- 进程资源占用排序（CPU TOP 20 / 内存 TOP 20）
- 进程路径与签名状态
- 进程命令行参数
- 进程启动时间
- 进程所有者（用户）

### 异常进程检测
- 用户可写路径进程（Temp/AppData/Public）
- 无签名进程
- 签名失效进程
- 伪装系统进程（路径异常的系统进程名）
- 隐藏进程（进程名包含特殊字符）
- 孤儿进程检测（父进程已退出）
- 高 CPU/内存持续占用进程（>80% 超过 1 小时）

### 进程-网络映射
- 进程对应的网络连接
- 外连进程及目标 IP
- 监听进程及端口

### 系统服务分析
- 所有服务列表与状态
- 自动启动服务（Automatic）
- 正在运行的服务（Running）
- 非系统路径服务（非 Windows 目录）
- 服务二进制路径与签名
- 服务启动账户（LocalSystem/NetworkService/特定用户）
- 高危服务状态检查
  - RemoteRegistry（远程注册表）
  - TermService（RDP）
  - TlntSvr（Telnet）
  - SNMP（简单网络管理协议）
  - FTP 服务

### DLL 劫持检测
- 加载的异常 DLL（非系统路径）
- 未签名 DLL
- 系统进程加载的非系统 DLL

---

## 3. 网络连接与端口

### 网络基础信息
- 网络适配器列表
- IP 地址与网关配置
- DNS 服务器配置
- 路由表信息
- ARP 缓存
- 网络配置文件（活动/域/公用）

### TCP 连接分析
- 所有 TCP 连接（ESTABLISHED）
- 监听端口列表（LISTEN）
- 外连 IP 地址列表
- 按进程分组的连接
- 高危端口监听检测
  - 21 (FTP)
  - 23 (Telnet)
  - 135 (RPC)
  - 139/445 (SMB)
  - 1433 (MSSQL)
  - 3306 (MySQL)
  - 3389 (RDP)
  - 5900 (VNC)
  - 4444/5555/6666 (常见木马端口)
  - 8080/8443 (Web 代理)

### UDP 端点分析
- 监听 UDP 端口
- 高危 UDP 端口
  - 53 (DNS)
  - 69 (TFTP)
  - 161/162 (SNMP)
  - 137/138 (NetBIOS)

### 防火墙策略排查
- 三个配置文件状态（域/专用/公用）
- 默认入站/出站策略
- 允许入站规则列表
- 禁用的防火墙规则
- 高危端口允许规则

### hosts 文件排查
- hosts 文件内容
- 异常静态解析（劫持常见域名）

---

## 4. 文件与持久化机制

### 敏感目录文件排查
- C:\Windows\Temp 目录
  - 可执行文件（.exe/.dll/.bat/.ps1/.vbs）
  - 近期修改文件（7 天内）
  - 隐藏文件
- C:\Temp 目录
- C:\Users\Public 目录
- 用户临时目录（%TEMP%）
- 用户 AppData 目录
  - AppData\Roaming
  - AppData\Local
  - AppData\LocalLow

### 启动项排查
- 注册表 Run 键
  - HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
  - HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce
  - HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
  - HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce
  - WOW6432Node 变体（32 位）
- 启动文件夹
  - C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp
  - %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
- 策略 Run 键
  - HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run
  - HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run

### 计划任务分析
- 所有计划任务列表
- 非 Microsoft 任务
- 已启用任务
- 任务操作命令
- 任务触发器
- 任务作者
- 最近运行时间与结果
- 可疑任务特征
  - 执行路径在 Temp 目录
  - base64 编码命令
  - PowerShell 下载执行
  - 高频率触发（每分钟/每 5 分钟）

### WMI 事件订阅排查
- WMI 事件过滤器
- WMI 事件消费者
- WMI 过滤器-消费者绑定
- ActiveScriptEventConsumer（脚本执行）
- CommandLineEventConsumer（命令执行）

### 文件时间戳分析
- 24 小时内修改的系统文件
- 近 7 天创建的可执行文件
- 文件签名状态
- 文件哈希（SHA256）

---

## 5. 日志与事件分析

### Security 日志分析
- 登录成功事件（4624）
  - 登录类型分析（2=交互/3=网络/10=RDP）
  - 登录来源 IP
  - 登录账户
  - 登录时间分布
- 登录失败事件（4625）
  - 失败原因
  - 爆破特征检测（同一 IP 大量失败）
  - 失败后成功的账户
- 特殊权限分配（4672）
  - 管理员登录记录
  - 特权提升
- 账户管理事件
  - 用户创建（4720）
  - 用户启用（4722）
  - 用户密码重置（4724）
  - 组成员添加（4728/4732/4756）
- 进程创建事件（4688）
  - 需启用进程审计
  - 可疑进程启动
- 服务安装事件（4697）
- 审计日志清除（1102）

### System 日志分析
- 服务启动/停止事件（7035/7036）
- 服务安装事件（7045）
- 系统启动/关闭时间
- 异常重启记录
- 驱动加载事件（6）
- 时间更改事件（1）

### Application 日志分析
- 应用程序错误
- 应用程序崩溃（1000/1001）
- Windows Error Reporting

### PowerShell 日志分析
- PowerShell 模块日志（4103）
- PowerShell 脚本块日志（4104）
  - base64 编码命令
  - 下载执行（IEX/Invoke-WebRequest）
  - 混淆脚本
  - 敏感命令（Get-Credential/Invoke-Mimikatz）
- PowerShell 启动/停止（4105/4106）

### Defender 日志分析
- 威胁检测记录
- 隔离文件
- 实时保护禁用事件
- 定义更新记录

### Sysmon 日志分析（如已部署）
- 进程创建（Event ID 1）
- 文件创建时间修改（Event ID 2）
- 网络连接（Event ID 3）
- 进程终止（Event ID 5）
- 驱动加载（Event ID 6）
- 镜像加载（Event ID 7）
- 注册表操作（Event ID 12/13/14）
- 文件流创建（Event ID 15）
- DNS 查询（Event ID 22）

---

## 6. 安全配置审计

### UAC 配置
- UAC 启用状态（EnableLUA）
- 管理员批准模式（ConsentPromptBehaviorAdmin）
- 提示在安全桌面（PromptOnSecureDesktop）
- UAC 虚拟化（EnableVirtualization）

### 远程桌面配置
- RDP 服务状态
- RDP 端口配置
- 网络级别身份验证（NLA）
- 加密级别
- 防火墙规则

### 自动登录检查
- AutoAdminLogon 状态
- DefaultUserName
- DefaultPassword（检查是否存在，不读取值）

### 凭据保护
- Credential Guard 状态
- LSA Protection
- WDigest 凭据缓存（UseLogonCredential）
- NTLM 配置

### 安全选项
- LAN Manager 身份验证级别
- 匿名 SID/名称转换
- 匿名枚举 SAM 账户
- 限制匿名访问
- 安全通道数据签名

---

## 7. 补丁与防护软件

### Windows Update
- Windows Update 服务状态
- 最后检查更新时间
- 待安装更新列表
- 更新历史（最近 10 个）

### 热修复补丁
- 已安装补丁列表
- 最新补丁安装日期
- 关键补丁缺失检测
- 补丁滞后天数

### Windows Defender
- 服务状态（WinDefend）
- 实时保护状态
- 云保护状态
- 行为监控状态
- IOAV 保护状态
- 防篡改保护状态
- 签名版本与更新时间
- 快速/完整扫描时间
- 排除项配置
  - 排除路径
  - 排除进程
  - 排除扩展名
- ASR 规则配置
- 受控文件夹访问

### 企业 EDR 检测
- CrowdStrike Falcon
- Microsoft Defender for Endpoint（Sense）
- Carbon Black
- SentinelOne
- Cylance
- Trend Micro
- Symantec Endpoint Protection
- McAfee Endpoint Security
- Kaspersky Endpoint Security

---

## 8. 远程访问配置

### RDP（远程桌面）
- TermService 服务状态
- RDP 端口配置（默认 3389）
- fDenyTSConnections（RDP 禁用状态）
- 网络级别身份验证（NLA）
- 安全层（TLS 版本）
- 最小加密级别
- 防火墙规则
- RDP 会话配置
- 空闲超时设置

### WinRM（Windows 远程管理）
- WinRM 服务状态
- WinRM 监听器配置
- 认证方式
  - Kerberos
  - Negotiate
  - Certificate
  - Basic（不安全）
- TrustedHosts 配置
- 防火墙规则
- AllowUnencrypted 设置

### OpenSSH
- sshd 服务状态
- SSH 端口配置
- sshd_config 配置
  - PasswordAuthentication
  - PubkeyAuthentication
  - PermitRootLogin（Administrator）
  - AllowUsers/DenyUsers
  - AllowGroups/DenyGroups
  - PermitEmptyPasswords
- authorized_keys 文件
- known_hosts 文件

### PowerShell Remoting
- PSRemoting 启用状态
- Session 配置
- JEA（Just Enough Administration）配置

---

## 9. 浏览器与代理

### 系统代理配置
- 用户代理设置（Internet Settings）
  - ProxyEnable
  - ProxyServer
  - AutoConfigURL（PAC）
  - AutoDetect（WPAD）
- WinHTTP 代理配置
- 代理绕过列表

### hosts 文件
- 静态解析条目
- 恶意域名劫持检测

### Edge 浏览器
- 浏览器策略（组策略/MDM）
- 扩展元数据（不读取内容）
- 主页/搜索引擎设置
- 代理设置

### Chrome 浏览器
- 浏览器策略
- 扩展元数据
- 企业策略配置

### Office 宏策略
- VBA 宏警告级别
- 来自 Internet 的内容执行阻止
- 受保护视图设置
- 受信任位置
- 允许网络位置

---

## 10. 🔥 应急响应模式

针对已知可疑行为的快速取证，重点关注：

### 快速固定现场
- 当前时间与系统状态
- 可疑对象信息（PID/路径/IP/文件）
- 当前网络连接快照
- 当前进程树快照
- 当前登录用户

### 围绕可疑对象的关联分析
- **进程分析**：
  - 进程详细信息
  - 父进程与子进程
  - 进程命令行
  - 进程模块（DLL）
  - 进程网络连接
  - 进程文件路径与签名
  - 进程启动时间
- **文件分析**：
  - 文件哈希（MD5/SHA256）
  - 文件签名状态
  - 文件时间戳（创建/修改/访问）
  - 文件关联进程
  - 文件 PE 头信息
- **网络分析**：
  - 连接的五元组信息
  - 对端 IP 归属查询
  - 历史 DNS 查询
  - 防火墙日志
- **持久化分析**：
  - 相关计划任务
  - 相关注册表键
  - 相关服务
  - 相关启动项
  - WMI 事件订阅

### 时间线构建
- 初始访问时间（登录日志）
- 命令执行时间（PowerShell 日志/历史命令）
- 文件落地时间（文件时间戳）
- 进程启动时间（进程创建时间）
- 网络活动时间（连接建立时间）
- 持久化设置时间（任务创建时间）

### 证据采集
- 可疑文件采集（计算哈希）
- 内存镜像（需专业工具）
- 事件日志导出（.evtx）
- 注册表导出
- 网络连接快照
- 进程列表快照

---

## 11. 🕵️ 深度后门检测

全面持久化机制排查，覆盖所有已知后门技术：

### 注册表持久化
- Run/RunOnce 键（含 WOW6432Node）
- 策略 Run 键
- Winlogon 键
  - Userinit
  - Shell
  - AppSetup
- Image File Execution Options（IFEO）
  - Debugger 劫持
  - GlobalFlag + SilentProcessExit
- AppInit_DLLs
- AppCertDlls
- 文件关联劫持（exefile/batfile/cmdfile）
- COM 劫持（CLSID）
- Shell 扩展
- 打印机驱动劫持
- 屏幕保护程序劫持

### 计划任务持久化
- 所有非 Microsoft 任务
- 隐藏任务（XML 中 Hidden=true）
- 高频率任务（每分钟/5 分钟）
- 可疑触发器（系统启动/用户登录/空闲）

### 服务持久化
- 非系统路径服务
- 自启动服务
- 服务 DLL（svchost 托管）
- 驱动服务（内核级）

### WMI 持久化
- __EventFilter
- __EventConsumer
- __FilterToConsumerBinding
- ActiveScriptEventConsumer
- CommandLineEventConsumer

### DLL 劫持
- DLL 搜索顺序劫持
- KnownDLLs 检测
- 系统进程加载的非系统 DLL
- DLL 侧加载（SideLolading）

### 文件系统持久化
- NTFS 交替数据流（ADS）
- 隐藏文件与文件夹
- 系统文件替换
- 白名单程序替换

### 组件劫持
- WinSxS 劫持
- Application Shims
- .NET 程序劫持

---

## 12. 🌐 网络隐蔽通道检测

检测隧道、代理、C2 通信：

### 隧道检测
- SSH 隧道特征
  - 本地转发（-L）
  - 远程转发（-R）
  - 动态 SOCKS（-D）
- HTTP/HTTPS 隧道
- DNS 隧道
- ICMP 隧道
- 常见隧道工具
  - ngrok
  - frp/frpc
  - chisel
  - Cloudflared

### 代理检测
- SOCKS 代理
- HTTP 代理
- 正向代理
- 反向代理
- 透明代理

### C2 通信特征
- 心跳包特征（固定间隔连接）
- 长连接特征
- 加密流量特征
- 域前置（Domain Fronting）
- DNS Beaconing
- 流量混淆

### 异常 DNS 行为
- 高频 DNS 查询
- 异常长度域名
- 随机子域名
- TXT 记录查询
- DNS 隧道特征

---

## 13. 💾 内存与进程深度分析

需要管理员权限和专业工具：

### 进程内存分析
- 内存映射异常
- 注入 DLL 检测
- Hollowing 检测（进程镂空）
- 反射 DLL 注入
- 内存段权限异常（RWX）

### 句柄分析
- 进程句柄列表
- 跨进程句柄
- 敏感对象句柄（LSASS）

### 线程分析
- 远程线程注入
- APC 注入
- 线程上下文劫持

### Hook 检测
- Inline Hook
- IAT Hook
- SSDT Hook（内核）
- 系统调用 Hook

### Rootkit 检测
- 内核模块异常
- 系统调用表篡改
- SSDT 挂钩
- IRP Hook
- Direct Kernel Object Manipulation（DKOM）

---

## 14. 📊 性能异常分析

排查性能问题和资源滥用：

### CPU 分析
- CPU 使用率历史
- TOP 进程（CPU）
- 持续高 CPU 进程（>80% 超过 1 小时）
- CPU 中断与 DPC 时间

### 内存分析
- 内存使用率
- 可用内存
- TOP 进程（内存）
- 内存泄漏检测
- 页面文件使用

### 磁盘分析
- 磁盘空间使用
- 磁盘 I/O 性能
- TOP 进程（磁盘 I/O）
- 磁盘队列长度
- 大文件排查（>1GB）

### 网络分析
- 网络带宽使用
- TOP 进程（网络）
- 连接数统计
- DNS 解析延迟
- 网络错误与丢包

### 系统负载
- 系统队列长度
- 线程数统计
- 句柄数统计
- 进程数统计

---

## 使用说明

1. 根据用户选择的流程，查看对应的检查项列表
2. 在 `windows-commands.md` 中查找每个检查项对应的具体命令
3. 执行命令并立即分析输出
4. 参考 `windows-analysis-guide.md` 获取详细的解读要点和风险判断标准
5. 根据发现的可疑项，建议下一步排查方向或深度检查

---

## 流程关联建议

### 发现可疑进程 → 推荐流程
1. 进程与服务排查（#2）
2. 网络连接与端口（#3）
3. 文件与持久化机制（#4）
4. 深度后门检测（#12）
5. 内存与进程深度分析（#14）

### 发现可疑网络连接 → 推荐流程
1. 网络连接与端口（#3）
2. 进程与服务排查（#2）
3. 网络隐蔽通道检测（#13）
4. 日志与事件分析（#5）

### 发现可疑账号 → 推荐流程
1. 系统信息与账号安全（#1）
2. 日志与事件分析（#5）
3. 安全配置审计（#6）
4. 远程访问配置（#9）

### 怀疑持久化后门 → 推荐流程
1. 文件与持久化机制（#4）
2. 深度后门检测（#12）
3. 日志与事件分析（#5）
4. 进程与服务排查（#2）

### 性能异常或挖矿 → 推荐流程
1. 性能异常分析（#15）
2. 进程与服务排查（#2）
3. 网络连接与端口（#3）
4. 文件与持久化机制（#4）

---

**文档版本**: 3.0  
**最后更新**: 2026-08-12
