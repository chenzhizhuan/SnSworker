---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '6e8654e1-3d68-4a89-a224-1bb94b76238b'
  PropagateID: '6e8654e1-3d68-4a89-a224-1bb94b76238b'
  ReservedCode1: '9b8e1b53-c562-4d0e-aaef-010a34e97f96'
  ReservedCode2: '9b8e1b53-c562-4d0e-aaef-010a34e97f96'
---

# 保活程序验证清单

> 生成保活程序后，按以下检查项逐项验证。
> **内网版**：完成第一至八部分（21 项）。
> **公网版**：完成第十部分（公网版保活验证 6 项）+ 第十一部分（扩展操作验证 5 项），跳过第一至八部分。

---

## 一、Cookie 与认证（5 项）

- [ ] **1. Cookie 通过 `context.cookies()` 提取**：未使用 `document.cookie`（HttpOnly Cookie 不可获取，陷阱 #1）
- [ ] **2. API 请求同时携带 Cookie**：纯 API Key 不足以通过 SSO 认证，必须注入会话 Cookie（陷阱 #2）
- [ ] **3. Cookie 保存为 JSON + TXT 双格式**：JSON 供 Python 脚本读取，TXT 供手动复制
- [ ] **4. Cookie 预加载已实现**：守护进程重启时注入上次保存的 Cookie，未过期可跳过登录（陷阱 #7）
- [ ] **5. 登录检测含 Cookie 数量二次确认**：URL 回到目标域名后检查 Cookie 是否达标，避免误判（陷阱 #6）

## 二、Chrome 配置与多系统（3 项）

- [ ] **6. 使用独立 `.chrome_profile` 目录**：未复用系统 Chrome 用户数据目录（陷阱 #4）
- [ ] **7. 多系统保活使用单 Chrome 多标签页方案**：`SITES` 字典 + `self.pages` 多页面，非多 Chrome 进程
- [ ] **8. Chrome 启动参数完整**：含 `--disable-blink-features=AutomationControlled`、`--no-first-run`、`--ignore-certificate-errors`、`--allow-running-insecure-content`；`ignore_default_args=["--enable-automation"]`

## 三、线程安全（4 项）

- [ ] **9. 所有 Playwright API 在 worker 线程中调用**：跨线程仅用标志位通信（陷阱 #8）
- [ ] **10. 所有 UI 更新通过 `root.after(0, callback)` 调度**：未直接跨线程操作 Tkinter（陷阱 #9）
- [ ] **11. 日志通过 `queue.Queue` 传递**：worker 线程不直接写 UI 组件，主线程 `_poll_log` 轮询
- [ ] **12. `stop()` 只设标志位不操作 Playwright**：worker 线程 `finally` 块自行清理

## 四、子进程与编码（2 项）

- [ ] **13. subprocess 调用时设置 `env["PYTHONIOENCODING"] = "utf-8"`**：防子进程中文乱码（陷阱 #3）
- [ ] **14. 所有 `proc.kill()` 后都跟了 `proc.wait()`**：防僵尸进程（陷阱 #10）

## 五、HTTP 连接安全（3 项）

- [ ] **15. 所有 `urlopen` 返回的响应对象在 `finally` 中 `close()`**：防 CLOSE_WAIT 连接泄漏（陷阱 #12）
- [ ] **16. `HTTPError` 异常对象也调用了 `e.close()`**：HTTPError 同样持有 TCP 连接
- [ ] **17. 导出脚本包含 `WinError 10055` 识别逻辑**：套接字耗尽时给出排查提示（陷阱 #13）

## 六、登录检测（2 项）

- [ ] **18. 等待登录循环中优先检查 Cookie 有效性**：Cookie 有效即判定登录成功，不依赖 URL 关键词（陷阱 #14）
- [ ] **19. URL 中残留 SSO 参数不阻止进入保活循环**：`_is_logged_in` 的 URL 判断为辅助，Cookie 判断为主

## 七、推送（1 项）

- [ ] **20. Bark 推送已集成**：Cookie 失效、Chrome 启动失败时推送到手机；含防重复和静默时段逻辑

## 八、GUI 与交付（1 项）

- [ ] **21. GUI 启动后 Chrome 自动打开**：点击「启动」后 Chrome 窗口出现，各系统标签页正确加载

---

## 验证流程

### 首次启动验证

1. 运行 `python cookie_keeper_gui.py`，确认 GUI 窗口正常显示
2. 点击「启动」，确认 Chrome 窗口打开，各系统标签页正确加载
3. 在 Chrome 中手动完成各系统 SSO 登录
4. 确认各系统状态指示灯变为绿色（已登录）
5. 确认 Cookie 自动导出到 JSON + TXT 文件
6. 等待 2 分钟，确认刷新次数递增、Cookie 数量稳定
7. 点击「导出 Cookie」，确认手动导出功能正常

### 重启验证

8. 点击「停止」，确认 Chrome 窗口关闭，按钮状态重置
9. 再次点击「启动」，确认 Cookie 预加载生效（无需重新登录）
10. 确认保活循环恢复正常运行

### Cookie 失效验证（可选）

11. 等待 Cookie 过期（或手动清除 `.chrome_profile` 中的 Cookie）
12. 确认状态指示灯变红，日志提示"需要重新登录"
13. 确认 Bark 推送已发送到手机（工作时段）
14. 在 Chrome 中重新登录，确认状态恢复绿色

### 连接泄漏验证（长时间运行）

15. 程序运行 2 小时后，运行 `netstat -an | findstr CLOSE_WAIT` 检查连接数
16. CLOSE_WAIT 数量应保持在合理范围（< 100），不应持续增长

---

## 九、公网版扩展操作验证（5 项）

> 仅公网版需要验证。内网版跳过本部分。

- [ ] **22. 定时任务脚本可读取 Cookie 文件**：脚本运行时 Cookie 文件存在且可读取，Cookie 字符串非空
- [ ] **23. API 请求携带 Cookie 成功**：首次运行返回 JSON 数据，未返回 HTML 登录页（陷阱 #2）
- [ ] **24. 定时任务按配置频率执行**：通过 `scheduler` 技能确认 cron 表达式正确，任务按时触发
- [ ] **25. 通知推送可达**：涉及的 Bark / 邮件等推送渠道能收到通知
- [ ] **26. Cookie 失效时脚本正确处理**：Cookie 过期时脚本不崩溃，返回明确错误信息并推送告警

---

## 十、公网版保活验证（6 项）

> 仅公网版需要验证。内网版跳过本部分。

- [ ] **27. Agent 提取 Cookie 成功**：Agent 用 Playwright 打开目标系统，用户登录后 Cookie 提取到完整 Cookie 列表
- [ ] **28. Cookie 文件保存到用户指定目录**：用户指定目录下生成 `{系统名}_cookies.json` 和 `{系统名}_cookies.txt` 两个文件
- [ ] **29. Cookie 刷新定时任务已创建**：通过 `scheduler` 技能确认 `Cookie刷新_{系统名}` 定时任务存在，cron 表达式正确
- [ ] **30. Cookie 刷新脚本首次运行成功**：手动运行一次刷新脚本，输出 `[OK] Cookie 刷新成功: N 个`，Cookie 文件更新时间已变更
- [ ] **31. Cookie 刷新脚本检测失效**：当 Cookie 过期时，刷新脚本输出 `[WARN] Cookie 已失效`，不崩溃
- [ ] **32. .chrome_profile 目录在用户指定目录下**：独立 Chrome 配置目录存在，未复用系统 Chrome 用户数据目录（陷阱 #4）

---

## 十一、公网版扩展操作验证（5 项）

> 仅公网版需要验证。内网版跳过本部分。

- [ ] **33. 扩展操作脚本 Cookie 路径正确**：脚本中 `COOKIE_DIR` 指向用户第一步指定的目录，`COOKIE_FILE` 文件名与保活生成的 Cookie 文件一致
- [ ] **34. 扩展操作脚本首次运行成功**：手动运行一次，能读取 Cookie 并成功调用 API，未返回 HTML 登录页
- [ ] **35. 扩展操作定时任务已创建**：通过 `scheduler` 技能确认定时任务存在，执行频率与用户配置一致
- [ ] **36. 通知推送可达**：涉及的 Bark / 邮件等推送渠道能收到通知
- [ ] **37. Cookie 失效时脚本正确处理**：Cookie 过期时脚本不崩溃，返回明确错误信息