# 保活程序 14 个踩坑点详解

> 以下踩坑点均来自实际项目验证，每条包含：问题描述、根因分析、修复方法、代码示例。

---

## 1. HttpOnly Cookie 不可通过 document.cookie 获取

**问题**：SSO 系统的会话 Cookie 通常设置为 HttpOnly，`document.cookie` 只返回非 HttpOnly 的 Cookie。如果用 `document.cookie` 提取 Cookie，会发现关键会话 Cookie 全部缺失。

**根因**：HttpOnly 是浏览器安全机制，禁止 JavaScript 访问该 Cookie，防止 XSS 攻击窃取会话信息。

**修复**：必须通过 Playwright 的 `context.cookies()` 获取完整 Cookie 列表：

```javascript
async (page) => {
    const context = page.context();
    const cookies = await context.cookies();
    const target = cookies.filter(c => c.domain.includes('目标域名'));
    return JSON.stringify(target, null, 2);
}
```

---

## 2. API Key 不足以通过认证

**问题**：即使系统页面 URL 中包含 API Key 参数，API 仍可能需要 SSO 会话 Cookie。纯 `urllib` 不带 Cookie 请求会被重定向到登录页，返回 HTML 而非 JSON。

**根因**：SSO 系统的 API 认证依赖会话 Cookie，API Key 只是应用层面的鉴权，不替代 SSO 认证。

**修复**：从 Cookie 文件注入 Cookie 到请求头，同时设置 csrf_token（如有）：

```python
headers["Cookie"] = cookie_str
headers["x-csrf-token"] = extract_csrf_from_cookies(cookie_str)  # 如有
headers["Authorization"] = f"Key {api_key}"  # 如有
```

> 响应头中的 `Vary: Cookie` 是重要信号，表明请求结果依赖 Cookie。

---

## 3. Windows PowerShell / subprocess 中文乱码

**问题**：Python 脚本在 Windows PowerShell 中输出中文会乱码；GUI 程序通过 `subprocess.Popen` 调用子进程时，子进程输出中文也会乱码。

**根因**：
- PowerShell 5.1 默认使用 GBK 编码，Python 输出 UTF-8 时编码不匹配
- subprocess 子进程的 stdout 编码由环境变量 `PYTHONIOENCODING` 决定，Popen 的 `encoding` 参数只影响父进程读取管道的解码方式

**修复**：
- 控制台临时方案：`$env:PYTHONIOENCODING="utf-8"`
- subprocess 必须在 Popen 调用时显式设置子进程环境变量：

```python
env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"
subprocess.Popen([sys.executable, script, ...], env=env, encoding="utf-8", errors="replace")
```

---

## 4. Chrome 用户数据目录锁定与启动超时

**问题**：Playwright 的 `launch_persistent_context` 无法在 Chrome 运行时复用其用户数据目录。即使关闭 Chrome 并删除锁文件（`SingletonLock` 等），复用系统 Chrome 的大型用户数据目录仍会导致启动缓慢甚至无限超时（60 秒+ 无响应）。

**根因**：
- Chrome 运行时会锁定用户数据目录（通过 `SingletonLock` 文件）
- 系统 Chrome 用户数据目录可能包含大量缓存、扩展、历史记录，导致 Playwright 初始化缓慢

**修复**：使用独立的 Playwright 配置目录：

```python
PROFILE_DIR = os.path.join(SCRIPT_DIR, ".chrome_profile")
context = p.chromium.launch_persistent_context(
    user_data_dir=PROFILE_DIR,
    channel="chrome",
    ...
)
```

> 首次运行需手动登录 SSO，登录态保存在 `.chrome_profile` 中，后续运行自动保留。

---

## 5. SSO 登录页 SSL 证书问题

**问题**：内网 SSO 系统可能使用不匹配的 SSL 证书或自签名证书。Playwright 导航时会遇到"您的连接不是私密连接"页面，导致登录流程中断。

**根因**：内网系统常使用自签名证书或域名不匹配的证书。

**修复**：
- Playwright 启动参数加 `--ignore-certificate-errors` 和 `--allow-running-insecure-content`
- Python urllib 请求需创建忽略证书的 SSL 上下文：

```python
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE
```

---

## 6. 登录检测误判：URL 已跳回但 Cookie 未写入

**问题**：SSO 登录跳转过程中，URL 可能短暂回到目标域名，但浏览器尚未写入会话 Cookie。此时仅检查 URL 会导致误判"已登录"，但实际 Cookie 不可用。

**根因**：SSO 跳转链路复杂（认证中心 → 目标系统 → 写 Cookie），URL 回到目标域名是中间状态，Cookie 写入有延迟。

**修复**：URL 回到目标域名后，增加二次确认——检查浏览器中目标域名的 Cookie 是否达标：

```python
def has_valid_cookies(context, config):
    cookies = [c for c in context.cookies() if config["cookie_domain"] in c.get("domain", "")]
    names = {c["name"] for c in cookies}
    required = set(config["valid_cookie_names"])
    return all(n in names for n in required)  # 所有关键 Cookie 都在才算登录成功
```

---

## 7. 守护进程重启时应预加载已有 Cookie

**问题**：守护进程重启时如果不预加载 Cookie，每次都要等用户手动登录，用户体验差。

**根因**：`.chrome_profile` 虽然保存了登录态，但 Playwright 启动新 context 时可能不自动加载所有 Cookie（尤其是不同域名的 Cookie）。

**修复**：启动时先注入上次保存的 Cookie 文件：

```python
def preload_cookies(context, cookie_file):
    if not os.path.exists(cookie_file):
        return 0
    with open(cookie_file, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    pw_cookies = [{
        "name": c["name"],
        "value": c["value"],
        "domain": c["domain"],
        "path": c.get("path", "/"),
    } for c in cookies]
    context.add_cookies(pw_cookies)
    return len(pw_cookies)
```

---

## 8. Playwright 同步 API 跨线程调用崩溃

**问题**：Playwright 同步 API（`sync_playwright`）的 `Page`、`BrowserContext` 等对象绑定创建它们的线程。在 GUI 守护进程中，如果 Playwright 在 worker 线程中创建，但 `stop()` 操作从主线程调用 `context.cookies()` 等 API，会触发 `greenlet.error: Cannot switch to a different thread` 崩溃。

**根因**：Playwright 同步 API 底层使用 greenlet，greenlet 绑定创建线程，跨线程调用会崩溃。

**修复**：使用标志位机制，让 worker 线程自己检测并执行所有 Playwright 操作：

```python
class CookieKeeper:
    def __init__(self):
        self._stop_requested = False
        self._export_cookie_request = False

    def worker_loop(self):
        # worker 线程中创建和操作所有 Playwright 对象
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(...)
            page = context.pages[0] if context.pages else context.new_page()

            while not self._stop_requested:
                page.reload(...)
                cookies = context.cookies()  # 在 worker 线程中调用，安全
                self._save_cookies(cookies)
                time.sleep(REFRESH_INTERVAL)

                if self._export_cookie_request:
                    cookies = context.cookies()
                    self._save_cookies(cookies)
                    self._export_cookie_request = False

            context.close()  # worker 线程自己负责清理

    def stop(self):
        self._stop_requested = True  # 只设标志位，不直接操作 Playwright

    def request_export(self):
        self._export_cookie_request = True
```

**核心原则**：所有 Playwright API 调用必须在创建 Playwright 对象的同一个线程中执行。跨线程通信只通过标志位/队列传递信号。

---

## 9. Tkinter 跨线程操作 UI 必须用 `root.after`

**问题**：Tkinter 不是线程安全的，从非主线程直接操作 UI 组件（如 `label.config()`、`text.insert()`）会导致随机崩溃或界面冻结。

**根因**：Tkinter 的事件循环运行在主线程中，非主线程操作 UI 组件会破坏事件循环的内部状态。

**修复**：所有 UI 更新必须通过 `self.root.after(0, callback)` 调度到主线程执行：

```python
def _update_status(self, site, text):
    """线程安全的 UI 更新"""
    self.root.after(0, lambda: self.status_labels[site].config(text=text))

def _auto_export_loop(self):
    """定时任务循环（在子线程中运行）"""
    while not self._stop_requested:
        time.sleep(self.export_interval)
        # 不能直接调用 self._do_export()，必须调度到主线程
        self.root.after(0, self._do_export)
```

**常见错误模式**：定时任务在子线程中直接调用需要操作 UI 的方法，导致跨线程 UI 操作崩溃。正确做法是用 `self.root.after(0, callback)` 将执行调度到主线程。

---

## 10. subprocess `kill()` 后必须 `wait()` 防僵尸进程

**问题**：通过 `subprocess.Popen` 启动的子进程，调用 `proc.kill()` 后如果不跟 `proc.wait()`，子进程会变成僵尸进程（zombie），长期运行会累积大量僵尸进程导致系统资源耗尽。

**根因**：`kill()` 发送终止信号，但父进程必须通过 `wait()` 回收子进程的退出状态和资源。不调用 `wait()` 则子进程成为僵尸进程。

**修复**：所有 `proc.kill()` 调用后必须紧跟 `proc.wait()`：

```python
try:
    stdout, stderr = proc.communicate(timeout=30)
except subprocess.TimeoutExpired:
    proc.kill()
    proc.wait()  # 必须！回收子进程资源
    stdout, stderr = proc.communicate()
```

> 检查代码中所有 `proc.kill()` 调用点，确保每一处都跟了 `proc.wait()`。一个文件内可能有 3 处以上需要修复。

---

## 11. gzip 压缩响应处理

**问题**：部分系统的 API 响应使用 gzip 压缩，如果请求头中设置了 `Accept-Encoding: gzip` 但代码中没有解压，会收到乱码数据。

**根因**：服务端根据 `Accept-Encoding` 头决定是否压缩响应，客户端必须自行解压。

**修复**：检查 `Content-Encoding` 响应头，必要时解压：

```python
import gzip

raw = resp.read()
if resp.headers.get("Content-Encoding") == "gzip":
    raw = gzip.decompress(raw)
body = raw.decode("utf-8")
```

---

## 12. HTTP 响应未关闭导致连接泄漏（CLOSE_WAIT 累积）

**问题**：长期运行的守护程序中，每次 `urlopen` 返回的 HTTP 响应对象如果未显式 `close()`，底层 TCP 连接不会及时释放，逐渐积累大量 CLOSE_WAIT 状态连接。最终系统套接字耗尽，新请求报 `WinError 10055: 由于系统缓冲区空间不足或队列已满`，数据脚本等子进程全部无法联网。

**根因**：Python `urllib.request.urlopen` 返回的响应对象持有底层 TCP 连接引用。虽然 Python 有 GC，但在长时间运行的进程中，GC 时机不确定，连接堆积到系统上限后才触发问题。这在短脚本中看不出，但守护程序运行数小时后必然爆发。

**修复**：所有 `urlopen` 调用必须在 `try/finally` 中关闭响应：

```python
resp = request.urlopen(req, context=SSL_CTX, timeout=30)
try:
    raw = resp.read()
    if resp.headers.get("Content-Encoding") == "gzip":
        raw = gzip.decompress(raw)
    body = raw.decode("utf-8")
    return json.loads(body)
finally:
    resp.close()  # 必须！释放底层 TCP 连接
```

HTTPError 同样需要关闭：

```python
except error.HTTPError as e:
    try:
        err_body = e.read().decode("utf-8", errors="replace")[:500]
    finally:
        try:
            e.close()  # HTTPError 也是响应对象，同样持有连接
        except Exception:
            pass
```

**排查方法**：

```powershell
# 查看 CLOSE_WAIT 连接数量及对应进程
$raw = netstat -ano
$pidGroups = @{}
foreach ($line in $raw) {
    if ($line -match "CLOSE_WAIT\s+(\d+)\s*$") {
        $procId = $matches[1]
        $pidGroups[$procId] = ($pidGroups[$procId] + 1)
    }
}
$pidGroups.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 5
```

**检查清单**：搜索代码中所有 `urlopen` 调用点，确保每一处都有 `resp.close()` 或 `with` 语句包裹。

---

## 13. 系统套接字被其他程序耗尽导致网络瘫痪

**问题**：保活程序和数据脚本自身代码没问题，但系统中其他程序（如 Foxmail）累积了上万条 CLOSE_WAIT 连接，耗尽系统套接字缓冲区。数据脚本 `urlopen` 时报 `WinError 10055`，但保活程序的 Cookie 刷新（走 Playwright 浏览器）不受影响——因为 Playwright 用的是 Chrome 的网络栈，不依赖 Python urllib。

**根因**：Windows 系统套接字是全局资源。任何程序泄漏连接都会影响所有网络程序。`WinError 10055` 不是你的代码问题，但需要能识别和应对。

**修复**：

1. **识别**：数据脚本失败报 `WinError 10055` 时，先查 `netstat -an | findstr CLOSE_WAIT` 数量
2. **定位**：用 `netstat -ano` 找出 CLOSE_WAIT 最多的 PID，定位到具体程序
3. **处理**：关闭泄漏连接最多的程序（如 Foxmail），系统套接字立即释放
4. **预防**：在数据脚本的异常处理中增加套接字错误识别：

```python
except OSError as e:
    if e.winerror == 10055:
        print("[!] 系统套接字耗尽，可能其他程序泄漏连接")
        print("[!] 运行 netstat -an | findstr CLOSE_WAIT 检查")
    raise
```

> 实测案例：Foxmail 累积 13,852 条 CLOSE_WAIT，关闭 Foxmail 后立即降至 56 条，系统网络恢复正常。

---

## 14. SSO 登录后 URL 残留参数导致登录状态误判

**问题**：某些 SSO 系统（如 TJOA 门户）登录成功后 URL 中仍残留 `sso`、`cas` 等关键词参数。保活程序的 `_is_logged_in` 方法通过 URL 关键词判断登录状态时，会因残留的 `sso` 关键词永远返回 False，导致程序一直等待登录、无法进入保活循环。

**根因**：SSO 跳转链路中，认证中心完成认证后可能以 302 跳回目标系统，但 URL 中携带 `ticket`、`sso` 等参数不立即清除。纯 URL 关键词判断无法区分「正在跳转」和「已完成跳转」。

**修复**：等待登录循环中优先检查 Cookie 有效性，Cookie 有效即判定登录成功，URL 关键词判断降为辅助：

```python
# 等待登录循环中，优先检查 Cookie
while self.is_running:
    for site_key in site_keys:
        if self.site_status[site_key]["logged_in"]:
            continue
        # 优先检查 Cookie：已有有效 Cookie 就算登录成功
        if self._has_valid_cookies(site_key):
            self.site_status[site_key]["logged_in"] = True
            self._update_site_login_status(site_key, "已登录", "green")
            continue

        # URL 判断为辅助
        cur = self.pages[site_key].url
        if self._is_logged_in(site_key, cur):
            time.sleep(2)
            if self._has_valid_cookies(site_key):
                self.site_status[site_key]["logged_in"] = True
            else:
                all_logged_in = False  # URL 对了但 Cookie 没跟上
        else:
            all_logged_in = False
    time.sleep(2)
```

**核心原则**：登录状态判断应以 Cookie 有效性为主、URL 为辅。URL 中残留 SSO 参数不应阻止进入保活循环。