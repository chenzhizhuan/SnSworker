# 保活程序代码模式参考

> 以下是构建保活程序所需的完整代码模板，按模块拆分。生成时根据用户系统配置定制 SITES 字典。

---

## 1. 完整 SITES 配置模板

```python
SITES = {
    "系统标识": {
        "name": "显示名称",                    # GUI 中显示的系统名称
        "keepalive_url": "http://系统首页URL",
        "cookie_domain": "系统域名或IP",       # Cookie 过滤用
        "cookie_json": os.path.join(SCRIPT_DIR, "xxx_cookies.json"),
        "cookie_txt": os.path.join(SCRIPT_DIR, "xxx_cookies.txt"),
        "login_page_keywords": ["关键词1", "关键词2"],  # 登录页 URL 中的关键词
        "logged_in_domain": "登录成功后的域名",   # 判断登录成功的域名
        "valid_cookie_names": ["关键Cookie名1", "Cookie名2"],  # 登录成功必须包含的 Cookie
        "color": "#0066cc",                    # GUI 中该系统的标识颜色
    },
}
```

> 多系统保活：在 SITES 字典中添加多个条目，程序自动为每个系统打开独立标签页，共用一个 Chrome 实例。

---

## 2. 通用配置常量

```python
import os
import sys
import json
import time
import threading
import subprocess
import queue
from datetime import datetime, timedelta

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_DIR = os.path.join(SCRIPT_DIR, ".chrome_profile")
REFRESH_INTERVAL = 120    # 页面刷新间隔（秒）
EXPORT_INTERVAL = 120     # Cookie 导出间隔（秒）
```

---

## 3. Chrome 启动参数（独立配置目录）

```python
from playwright.sync_api import sync_playwright

context = p.chromium.launch_persistent_context(
    user_data_dir=PROFILE_DIR,
    channel="chrome",
    headless=False,
    args=[
        "--disable-blink-features=AutomationControlled",  # 避免被检测为自动化
        "--no-first-run",
        "--disable-extensions",
        "--ignore-certificate-errors",                     # 内网 SSL 证书问题
        "--allow-running-insecure-content",
    ],
    ignore_default_args=["--enable-automation"],
    no_viewport=True,
)
```

> **关键**：`--ignore-certificate-errors` 解决内网 SSL 证书问题；`--disable-blink-features=AutomationControlled` 避免被网站检测为自动化浏览器。

---

## 4. 多系统保活：标签页管理

```python
# 为每个系统创建独立的 page
pages = {}
for idx, (site_key, site_cfg) in enumerate(SITES.items()):
    if idx == 0:
        # 第一个站点用 launch_persistent_context 自带的第一个页面
        pages[site_key] = context.pages[0] if context.pages else context.new_page()
    else:
        pages[site_key] = context.new_page()

    # 预加载 Cookie（重启优化）
    loaded = preload_cookies(context, site_cfg["cookie_json"])
    if loaded > 0:
        log(f"[{site_cfg['name']}] 预加载 Cookie: {loaded} 个")

    # 打开保活页面
    pages[site_key].goto(site_cfg["keepalive_url"],
                        wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)  # 等待页面稳定
```

---

## 5. Cookie 预加载（重启优化）

```python
def preload_cookies(context, cookie_file):
    """从 JSON 文件预加载 Cookie 到浏览器上下文"""
    if not os.path.exists(cookie_file):
        return 0
    try:
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
    except Exception:
        return 0
```

---

## 6. 登录检测逻辑（含二次确认）

```python
def is_login_page(page, config):
    """检测当前是否在登录页"""
    try:
        url = page.url or ""
        for keyword in config["login_page_keywords"]:
            if keyword in url:
                return True
        if "login" in url.lower() and config["logged_in_domain"] not in url:
            return True
        if "sso" in url.lower() and config["logged_in_domain"] not in url:
            return True
        if "auth" in url.lower() and config["logged_in_domain"] not in url:
            return True
        if "chrome-error" in url:  # SSL 证书错误页
            return True
        return False
    except Exception:
        return False


def is_logged_in(url, config):
    """检查 URL 是否表示已登录（URL 已回到目标域名且不在登录页）"""
    if not url:
        return False
    if config["logged_in_domain"] not in url:
        return False
    for keyword in config["login_page_keywords"]:
        if keyword in url:
            return False
    if "login" in url.lower():
        return False
    if "sso" in url.lower():
        return False
    return True


def has_valid_cookies(context, config):
    """检查浏览器中是否已有足够的登录 Cookie（二次确认）"""
    cookies = [c for c in context.cookies()
               if config["cookie_domain"] in c.get("domain", "")]
    if not cookies:
        return False
    if not config["valid_cookie_names"]:
        return len(cookies) > 0
    names = {c["name"] for c in cookies}
    return all(n in names for n in config["valid_cookie_names"])


def wait_for_login(page, context, config, is_running, timeout=120):
    """等待用户完成登录，含 Cookie 数量二次确认"""
    start = time.time()
    while time.time() - start < timeout and is_running:
        url = page.url
        if is_logged_in(url, config):
            time.sleep(2)  # 等待页面完全加载
            if has_valid_cookies(context, config):
                return True
        time.sleep(10)
    return False
```

> **关键**：`is_login_page` 排除 `chrome-error` 页面（SSL 证书问题导致的错误页不是登录页）；`has_valid_cookies` 做二次确认避免 URL 跳回但 Cookie 未写入的误判。

---

## 7. Cookie 导出格式

### JSON 格式（供 Python 数据脚本读取）

```python
def save_cookies(site_key, cookies):
    """保存 Cookie 到 JSON + TXT 文件"""
    simple = [{
        "name": c["name"],
        "value": c["value"],
        "domain": c["domain"],
        "path": c.get("path", "/"),
    } for c in cookies]

    with open(SITES[site_key]["cookie_json"], "w", encoding="utf-8") as f:
        json.dump(simple, f, ensure_ascii=False, indent=2)

    with open(SITES[site_key]["cookie_txt"], "w", encoding="utf-8") as f:
        for c in simple:
            f.write(f"{c['name']}={c['value']}\n")
```

### TXT 格式（供手动复制使用）

```
session=<会话令牌值>...
csrf_token=<CSRF令牌值>...
locale=zh-CN
```

---

## 8. 保活循环核心逻辑

```python
def keepalive_loop(context, pages, is_running_flag, log, refresh_count):
    """保活循环：定时刷新所有站点页面 + 导出 Cookie"""
    last_refresh = time.time()
    last_export = time.time()

    while is_running_flag():
        now = time.time()

        # 定时刷新所有站点
        if now - last_refresh >= REFRESH_INTERVAL:
            refresh_count[0] += 1
            for site_key, config in SITES.items():
                try:
                    page = pages[site_key]
                    if is_login_page(page, config):
                        log(f"[{config['name']}] Cookie 失效！需要重新登录...")
                        wait_for_login(page, context, config, is_running_flag)
                    else:
                        page.goto(config["keepalive_url"],
                                  wait_until="domcontentloaded", timeout=15000)
                        cookies = get_target_cookies(context, config)
                        save_cookies(site_key, cookies)
                        log(f"[{config['name']}] 刷新 #{refresh_count[0]} | Cookie: {len(cookies)} 个")
                except Exception as e:
                    log(f"[{config['name']}] 刷新异常: {e}")
            last_refresh = time.time()

        # 手动导出请求（由按钮触发，worker 线程执行）
        if export_cookie_requested():
            for site_key, config in SITES.items():
                cookies = get_target_cookies(context, config)
                save_cookies(site_key, cookies)
                log(f"[{config['name']}] 手动导出: {len(cookies)} 个")

        time.sleep(2)
```

---

## 9. 线程安全模式（标志位 + root.after）

```python
class CookieKeeperApp:
    def __init__(self, root):
        self.root = root
        self.is_running = False
        self._export_cookie_request = False  # 手动导出请求标志
        self.worker_thread = None
        self.log_queue = queue.Queue()
        self.pages = {}

    def start(self):
        """主线程：启动 worker 线程"""
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def stop(self):
        """主线程：只设标志位，不直接操作 Playwright"""
        self.is_running = False
        # worker 线程的 finally 块会自动清理

    def export_cookies_manual(self):
        """主线程：设置标志位，由 worker 线程执行"""
        self._export_cookie_request = True

    def _worker(self):
        """worker 线程：所有 Playwright 操作都在这里"""
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(...)
            # 创建标签页、登录、保活循环...

            while self.is_running:
                # 检查导出请求
                if self._export_cookie_request:
                    self._export_cookie_request = False
                    cookies = context.cookies()  # worker 线程中调用，安全
                    self._save_cookies(cookies)
                time.sleep(2)

            context.close()  # worker 线程自己负责清理

    # ========== 日志（线程安全） ==========
    def log(self, msg):
        """线程安全日志：通过 Queue 传递到主线程"""
        self.log_queue.put(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def _poll_log(self):
        """主线程：定期从 Queue 取日志并显示"""
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(200, self._poll_log)

    # ========== UI 更新（线程安全） ==========
    def _update_site_login_status(self, site_key, text, color="gray"):
        """线程安全 UI 更新"""
        var = self.site_status[site_key]["login_var"]
        label = self.site_status[site_key]["login_label"]
        var.set(f"● {text}")
        label.config(fg=color)

    def _auto_export_loop(self):
        """定时导出循环（在子线程中运行）"""
        while self.auto_export_enabled and self.is_running:
            time.sleep(self.auto_export_interval * 60)
            # 不能直接调用 self._do_export()，必须调度到主线程
            self.root.after(0, self._do_export)
```

---

## 10. subprocess 调用子进程（防乱码 + 防僵尸）

```python
def _make_subprocess_env(self):
    """创建子进程环境变量（防中文乱码）"""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return env

def _run_script(self, script_path, cmd_args, timeout=120):
    """调用外部 Python 脚本"""
    cmd = [sys.executable, "-u", script_path] + cmd_args
    env = self._make_subprocess_env()

    def _run():
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=os.path.dirname(script_path),
                encoding="utf-8",
                errors="replace",
                env=env,                          # 防子进程中文乱码
            )
            output = proc.communicate(timeout=timeout)[0]
            for line in output.strip().splitlines():
                self.log(f"  {line}")
        except subprocess.TimeoutExpired:
            self.log("执行超时!")
            try:
                proc.kill()
                proc.wait()                        # 防僵尸进程
            except Exception:
                pass
        except Exception as e:
            self.log(f"执行失败: {e}")
        finally:
            self.root.after(0, lambda: self.btn.config(state=tk.NORMAL))

    threading.Thread(target=_run, daemon=True).start()
```

---

## 11. 数据脚本读取 Cookie

```python
def load_cookies(cookie_file="system_cookies.json"):
    """从 JSON 文件加载 Cookie，返回 Cookie 字符串"""
    with open(cookie_file, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    parts = []
    for c in cookies:
        if "目标域名" in c.get("domain", ""):
            parts.append(f"{c['name']}={c['value']}")
    return "; ".join(parts)

# 在请求头中使用
cookie_str = load_cookies()
headers["Cookie"] = cookie_str
headers["x-csrf-token"] = extract_csrf_from_cookies(cookie_str)  # 如有
```

### csrf_token 提取

```python
def extract_csrf_from_cookies(cookie_str):
    """从 Cookie 字符串中提取 csrf_token 值"""
    for pair in cookie_str.split(";"):
        pair = pair.strip()
        if pair.startswith("csrf_token="):
            return pair.split("=", 1)[1]
    return None
```

---

## 12. GUI 框架骨架

```python
class CookieKeeperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cookie 保活程序（多系统）")
        self.root.geometry("860x760")
        self.root.minsize(720, 620)

        # 运行状态
        self.is_running = False
        self.playwright_ctx = None
        self.pages = {}
        self.worker_thread = None
        self.log_queue = queue.Queue()
        self.start_time = None
        self.refresh_count = 0
        self._export_cookie_request = False

        # 每个站点的状态
        self.site_status = {}
        for key in SITES:
            self.site_status[key] = {"cookie_count": 0, "logged_in": False}

        self._build_ui()
        self._poll_log()

    def _build_ui(self):
        # ---- 顶部控制栏 ----
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill=tk.X)

        ttk.Button(top, text="启动", command=self.start).pack(side=tk.LEFT, padx=(0, 4))
        self.btn_stop = ttk.Button(top, text="停止", command=self.stop, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=4)
        self.btn_export = ttk.Button(top, text="导出 Cookie",
                                      command=self.export_cookies_manual,
                                      state=tk.DISABLED)
        self.btn_export.pack(side=tk.LEFT, padx=4)

        # ---- 多系统状态面板 ----
        status_frame = ttk.LabelFrame(self.root, text="系统保活状态", padding=8)
        status_frame.pack(fill=tk.X, padx=8, pady=(8, 4))

        for site_key, site_cfg in SITES.items():
            f = ttk.Frame(status_frame)
            f.pack(fill=tk.X, pady=2)
            # 系统名称、Cookie 数量、登录状态指示灯、Cookie 文件路径

        # ---- 运行时长 + 刷新次数 ----
        info = ttk.Frame(self.root, padding=(8, 0))
        info.pack(fill=tk.X)
        # 运行时长标签、刷新次数标签

        # ---- 日志区 ----
        log_frame = ttk.LabelFrame(self.root, text="日志", padding=4)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.log_text = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, font=("Consolas", 9), state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # ---- 底部提示 ----
        bottom = ttk.Frame(self.root, padding=(8, 4))
        bottom.pack(fill=tk.X)
        ttk.Label(bottom, text=(
            "点击「启动」打开 Chrome → 在浏览器中登录各系统 SSO → 登录后自动保活\n"
            "Cookie 每次刷新自动保存到各自 JSON + TXT 文件"
        ), foreground="gray").pack(side=tk.LEFT)


def main():
    root = tk.Tk()
    app = CookieKeeperApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
```

> **启动 GUI 的推荐方式**：创建桌面快捷方式或 `.bat` 启动脚本，使用 `python.exe`（非 `pythonw.exe`）以便查看错误输出。路径中含中文时用 `%~dp0` 代替硬编码路径，规避 cmd 的 GBK 编码问题。

---

## 13. HTTP 请求安全模式（防连接泄漏）

> 长期运行的守护程序中，所有 `urlopen` 返回的响应对象必须显式关闭，否则 TCP 连接以 CLOSE_WAIT 状态堆积，最终耗尽系统套接字（陷阱 #12）。

```python
import ssl
import gzip
import json
from urllib import request, error

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

def api_request(url, method="GET", data=None, cookie_str=None, max_retries=3):
    """安全 HTTP 请求：响应对象总是被关闭，防止连接泄漏"""
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Encoding": "gzip, identity",
    }
    if method == "POST":
        headers["Content-Type"] = "application/json;charset=UTF-8"
    if cookie_str:
        headers["Cookie"] = cookie_str

    for attempt in range(max_retries):
        try:
            req_data = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None
            req = request.Request(url, data=req_data, headers=headers, method=method)
            resp = request.urlopen(req, context=SSL_CTX, timeout=30)
            try:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                body = raw.decode("utf-8")
                if body.lstrip().startswith(("<!DOCTYPE", "<html", "<HTML")):
                    raise Exception("登录已失效（API 返回 HTML 登录页）")
                return json.loads(body)
            finally:
                resp.close()  # 关键：无论成功或异常都关闭
        except error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                err_body = ""
            finally:
                try:
                    e.close()  # HTTPError 也持有连接
                except Exception:
                    pass
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise
```

---

## 14. Bark 手机推送集成

> 保活程序异常（Cookie 失效、Chrome 启动失败）时通过 Bark 推送到手机，无需安装额外 App。

```python
import urllib.request
import urllib.parse

class CookieKeeperApp:
    BARK_API_BASE = "https://api.day.app/你的BARK_KEY"
    BARK_PARAMS = "level=critical&volume=5"  # 紧急级别 + 最大音量
    BARK_QUIET_START = 0   # 静默开始时段
    BARK_QUIET_END = 8     # 静默结束时段
    BARK_DEDUP_SECONDS = 3600  # 去重间隔（秒）

    def _send_bark(self, title, body):
        """发送 Bark 推送（非阻塞，失败静默）"""
        resp = None
        try:
            url = (f"{self.BARK_API_BASE}/"
                   f"{urllib.parse.quote(title)}/{urllib.parse.quote(body)}"
                   f"?{self.BARK_PARAMS}")
            req = urllib.request.Request(url, method="GET")
            resp = urllib.request.urlopen(req, timeout=5)
            self.log(f"[Bark] 推送已发送: {title}")
            return True
        except Exception as e:
            self.log(f"[Bark] 推送失败: {e}")
            return False
        finally:
            if resp:
                try:
                    resp.close()  # 防连接泄漏
                except Exception:
                    pass

    def _notify_cookie_failed(self, site_key, site_name):
        """Cookie 失效推送（含防重复 + 静默时段）"""
        now = time.time()
        hour = datetime.now().hour
        # 静默时段不推送
        if self.BARK_QUIET_START <= hour < self.BARK_QUIET_END:
            return
        # 去重：1小时内不重复推送
        last = self._bark_last_notify.get(site_key, 0)
        if now - last < self.BARK_DEDUP_SECONDS:
            return
        success = self._send_bark(
            "Cookie 失效提醒",
            f"[{site_name}] Cookie 已失效，需要重新登录"
        )
        if success:
            self._bark_last_notify[site_key] = now
```

> **注意**：Chrome 启动失败属于程序级故障，任何时段都应推送（不走静默逻辑）。在 Chrome 启动异常处理中直接调用 `_send_bark`，不经过 `_notify_cookie_failed` 的静默判断。
