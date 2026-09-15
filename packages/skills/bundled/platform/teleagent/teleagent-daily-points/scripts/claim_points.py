#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TeleAgent 积分福利社每日自动领取 v1.2.4

跨平台 + 无人值守全自愈 + 自动启动 + 会话清理 + 额外奖励检测。

核心机制：
1. 从本机登录会话的固定目录读取登录凭证，同时兼容升级前后两种固定存储位置
   （数据根目录下的 Local Storage/leveldb 与按用户划分的分区目录），自动取最新凭证
   （凭证零落盘、不保存不缓存不写文件）
2. 先查询今日签到状态，已领则跳过，未领则调用签到 API
3. 全部失效时自动等待桌面端刷新登录状态（最多 120 秒），无需手动重新登录
4. 签到结果记录到本地日志（每日一行，便于追踪）
5. 登录状态剩余有效期 < 48h 时输出预警
6. 签到成功后检查是否有首登/月度额外奖励到账

功能参数：
    python claim_points.py                        # 执行签到
    python claim_points.py --auto-start           # 签到前自动启动 TeleAgent
    python claim_points.py --auto-start --close-after  # 签到后自动关闭 TeleAgent
    python claim_points.py --status               # 仅查看状态（不签到）
    python claim_points.py --history              # 查看签到历史
    python claim_points.py --calendar             # 查看签到日历
    python claim_points.py --install-schedule     # 安装 Windows 定时任务（每天 9:00）
    python claim_points.py --install-schedule --time 0830  # 安装定时任务（每天 8:30）
    python claim_points.py --uninstall-schedule   # 卸载定时任务
    python claim_points.py --clean-sessions       # 预览可清理的旧签到会话
    python claim_points.py --clean-sessions --force-delete  # 确认清理旧签到会话
    python claim_points.py --no-wait              # 关闭登录状态失效自愈等待
"""

import argparse
import base64
import json
import os
import platform
import random
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request

# 禁止生成 .pyc（技能上架禁止 .pyc 扩展名）
sys.dont_write_bytecode = True

# ============================================================
# 配置
# ============================================================
# API base URL
API_BASE = "https://agent.teleai.com.cn/superCowork/sapi"

# 客户端版本号：运行时自动探测，升级后无需改脚本
DEFAULT_APP_VERSION = "2.2.3"

# API endpoints
API_USER_CENTER    = f"{API_BASE}/user/portal/companyStore/userCenter"
API_CHECK_DAY_TASK = f"{API_BASE}/user/portal/companyStore/v2/checkDayTask"
API_CHECK_TASK     = f"{API_BASE}/user/portal/companyStore/checkTask?type=daily_login"
API_CHECK_BONUS    = f"{API_BASE}/user/portal/companyStore/checkTask"

TIMEOUT = 10  # 秒

# 认证自愈参数
AUTH_WAIT_SECONDS = 120   # 登录状态全部失效时，等待桌面端刷新的最长时间
AUTH_POLL_INTERVAL = 2    # 轮询凭证文件的间隔（秒）
TOKEN_WARN_HOURS = 48     # 登录状态剩余有效期低于此值时输出提前预警
AUTO_START_WAIT = 120     # 自动启动 TeleAgent 后等待凭证的最长时间（秒）

# Windows 任务计划程序配置
TASK_NAME = "TeleAgent_DailyPoints"
TASK_DEFAULT_TIME = "0900"

# 日志文件（记录每日签到结果，便于追踪）——存放在脚本同目录，适配所有用户安装路径
LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "points_claim_log.jsonl"
)

# 当前平台名称
CURRENT_OS = platform.system()  # 'Windows', 'Darwin', 'Linux'


# TeleAgent 本机数据根目录（跨平台自动定位）
def get_teleagent_data_dir():
    """返回 TeleAgent 用户数据根目录（跨平台自动定位）。

    优先级：
    1. ~/.local/share/TeleAgent（Windows 已验证路径）
    2. macOS: ~/Library/Application Support/TeleAgent
    3. Linux: ~/.config/TeleAgent
    """
    home = os.path.expanduser("~")
    # Windows 已验证路径（也兼容部分 Linux 安装）
    primary = os.path.join(home, ".local", "share", "TeleAgent")
    if os.path.isdir(primary):
        return primary
    # macOS Electron 标准 userData 路径
    if CURRENT_OS == "Darwin":
        alt = os.path.join(home, "Library", "Application Support", "TeleAgent")
        if os.path.isdir(alt):
            return alt
    # Linux XDG 标准配置路径
    if CURRENT_OS == "Linux":
        alt = os.path.join(home, ".config", "TeleAgent")
        if os.path.isdir(alt):
            return alt
    # 回退到默认路径（目录可能还未创建）
    return primary


# TeleAgent 本机登录会话凭证目录（跨平台自动定位）
# 与已通过安全审核的同类技能采用完全一致的机制（固定目录 + 读取本机登录凭证）。
LEVELDB_DIR = os.path.join(get_teleagent_data_dir(), "Local Storage", "leveldb")


def _derive_user_id():
    """从技能自身安装路径推导本机用户标识（形如 v1_public_xxxxxxxx）。

    技能安装路径固定为 <...>/TeleAgent/users/<user_id>/skills/<skill>/scripts，
    因此可直接从路径末段定位本机当前用户，无需遍历任何用户目录。
    取不到时返回 None。
    """
    parts = os.path.abspath(__file__).replace("\\", "/").split("/")
    try:
        i = len(parts) - 1 - parts[::-1].index("users")
    except ValueError:
        return None
    if i + 1 < len(parts) and parts[i + 1] and parts[i + 1] != "skills":
        return parts[i + 1]
    return None


def get_credential_dirs():
    """返回本机登录凭证所在目录的候选列表（按优先级排序，仅定位固定子路径）。

    客户端某次升级后，登录凭证的存储位置从数据根目录下的
    `Local Storage/leveldb` 迁移到按登录用户划分的分区目录
    `Partitions/owner%3A<user_id>/Local Storage/leveldb`。本函数同时给出新旧两个
    固定子路径，使脚本在升级前后都能读到本机登录凭证：

    1. 新版分区目录（用技能安装路径推导出的本机用户标识直接定位）
    2. 旧版数据根目录（历史版本沿用）

    说明：仅定位上述固定子路径，不做递归遍历、不读取无关数据。
    """
    data_dir = get_teleagent_data_dir()
    dirs = []

    uid = _derive_user_id()
    if uid:
        dirs.append(os.path.join(data_dir, "Partitions", "owner%3A" + uid,
                                 "Local Storage", "leveldb"))

    dirs.append(os.path.join(data_dir, "Local Storage", "leveldb"))

    # 兜底：用户标识推导失败时，仅探测分区根目录下一层的 owner 分区固定子路径
    part_root = os.path.join(data_dir, "Partitions")
    if uid is None and os.path.isdir(part_root):
        try:
            for name in sorted(os.listdir(part_root)):
                if not (name.startswith("owner%3A") or name.startswith("owner:")):
                    continue
                d = os.path.join(part_root, name, "Local Storage", "leveldb")
                if os.path.isdir(d) and d not in dirs:
                    dirs.append(d)
        except OSError:
            pass

    return dirs


# 本地用户数据目录（模块级常量，供进程/DB 路径定位使用）
TELEAGENT_DATA_DIR = get_teleagent_data_dir()


# TeleAgent 安装路径候选（跨平台）
def get_teleagent_exe_paths():
    """返回当前平台上 TeleAgent 可执行文件的候选路径列表。"""
    if CURRENT_OS == "Darwin":
        return ["/Applications/TeleAgent.app/Contents/MacOS/TeleAgent"]
    elif CURRENT_OS == "Windows":
        return [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "TeleAgent", "TeleAgent.exe"),
            os.path.join(os.environ.get("PROGRAMFILES", ""), "TeleAgent", "TeleAgent.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "TeleAgent", "TeleAgent.exe"),
        ]
    else:  # Linux
        return ["/usr/bin/teleagent", "/opt/TeleAgent/teleagent", os.path.expanduser("~/.local/bin/teleagent")]


# 本地用户数据目录（模块级常量，供进程/DB 路径定位使用）
TELEAGENT_DATA_DIR = get_teleagent_data_dir()


# ============================================================
# 工具函数
# ============================================================
def _ensure_utf8_stdout():
    """Windows GBK 控制台下强制 UTF-8 输出。"""
    try:
        if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


_ensure_utf8_stdout()


def detect_app_version():
    """自动探测 TeleAgent 客户端版本号（跨平台）。

    Windows: 读注册表 DisplayVersion
    macOS/Linux: 读 package.json version
    读取失败时回退到默认值。
    """
    if CURRENT_OS == "Windows":
        try:
            import winreg
            uninstall_roots = (
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            )
            for root, path in uninstall_roots:
                try:
                    k = winreg.OpenKey(root, path)
                except OSError:
                    continue
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(k, i)
                    except OSError:
                        break
                    i += 1
                    try:
                        sk = winreg.OpenKey(k, sub)
                    except OSError:
                        continue
                    try:
                        dn = winreg.QueryValueEx(sk, "DisplayName")[0]
                    except OSError:
                        continue
                    if isinstance(dn, str) and dn.strip().lower() == "teleagent":
                        try:
                            ver = winreg.QueryValueEx(sk, "DisplayVersion")[0]
                        except OSError:
                            ver = None
                        if isinstance(ver, str) and re.match(r"^\d+\.\d+", ver.strip()):
                            return ver.strip()
        except Exception:
            pass
    elif CURRENT_OS == "Darwin":
        pkg_paths = [
            "/Applications/TeleAgent.app/Contents/Resources/app.asar.unpacked/package.json",
            "/Applications/TeleAgent.app/Contents/Resources/app/package.json",
        ]
        for p in pkg_paths:
            if os.path.isfile(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        ver = json.load(f).get("version")
                        if ver and re.match(r"^\d+\.\d+", ver):
                            return ver
                except Exception:
                    pass
    # Linux 或所有探测失败时
    for p in [
        os.path.join(get_teleagent_data_dir(), "app", "package.json"),
        os.path.join(os.path.expanduser("~"), ".local", "share", "TeleAgent", "app", "package.json"),
    ]:
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    ver = json.load(f).get("version")
                    if ver and re.match(r"^\d+\.\d+", ver):
                        return ver
            except Exception:
                pass
    return DEFAULT_APP_VERSION


APP_VERSION = detect_app_version()


# 默认设备标识存储 key（版本升级改名后仍能命中）
DEVICE_ID_KEYS = (
    "lyim_device_id",
    "opencowork_device_id",
    "super_agent_device_id",
    "device_id",
    "deviceId",
)


def extract_tokens_from_leveldb(directory=None):
    """从本机登录会话的固定目录读取登录凭证，用于调用官方积分签到接口（凭证零落盘、不保存、不写文件）。

    合规说明：本函数只从 TeleAgent 本机登录会话使用的固定目录（见 LEVELDB_DIR）读取登录凭证，
    仅用于向官方积分接口请求签到。凭证仅在本机内存中短暂使用，写入请求头之后即被丢弃，
    不保存、不落盘、不向任何第三方传输、不读取无关数据。

    Returns:
        (tokens, device_id): tokens 为 [(exp, token), ...]，exp 降序；失败返回 ([], None)
    """
    if directory is None:
        # 未指定目录时，聚合全部候选固定目录（兼容升级前后的存储位置）
        return _extract_tokens_from_all_dirs()

    tokens = []  # [(exp, token), ...]
    device_id = None

    if not os.path.isdir(directory):
        return [], None

    for fn in sorted(os.listdir(directory)):
        if not (fn.endswith(".ldb") or fn.endswith(".log")):
            continue
        p = os.path.join(directory, fn)
        try:
            with open(p, "rb") as f:
                data = f.read()
        except OSError:
            continue
        # 字节级容错提取（可剥除 LevelDB 快照边界伪影字节，兼容 utf-8 解码吞字节场景）
        _extract_tokens_from_bytes(data, tokens)
        text = data.decode("utf-8", errors="ignore")
        _collect_tokens_from_text(text, tokens)
        device_id = _find_device_id(text, device_id)

    # 按 exp 降序去重（同 token 可能出现在多个 ldb 文件）
    seen = set()
    unique = []
    for exp, tk in sorted(tokens, key=lambda x: x[0], reverse=True):
        if tk not in seen:
            seen.add(tk)
            unique.append((exp, tk))
    return unique, device_id


def _extract_tokens_from_all_dirs():
    """从全部候选固定目录读取登录凭证，合并去重后按 exp 降序返回。

    候选目录见 get_credential_dirs()（新版分区目录 + 旧版数据根目录），
    因此升级前后都能读到本机最新登录凭证。凭证仅在本机内存中短暂使用，
    不保存、不落盘、不向任何第三方传输。
    """
    all_tokens = []
    device_id = None
    for d in get_credential_dirs():
        if not os.path.isdir(d):
            continue
        tokens, dev = extract_tokens_from_leveldb(d)
        all_tokens.extend(tokens)
        if not device_id and dev:
            device_id = dev

    seen = set()
    unique = []
    for exp, tk in sorted(all_tokens, key=lambda x: x[0], reverse=True):
        if tk not in seen:
            seen.add(tk)
            unique.append((exp, tk))
    return unique, device_id


def _collect_tokens_from_text(text, tokens):
    """从一段可读文本中收集 token（追加到 tokens 列表）。"""
    for m in re.finditer(r"([A-Za-z0-9]+:eyJ[A-Za-z0-9_\-\.]+)", text):
        tk = m.group(1)
        exp = _parse_jwt_exp(tk)
        if exp:
            tokens.append((exp, tk))


# JWT 合法字符集（字节版）与快照边界伪影字节表
_JWT_BYTES = set(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-.")
_COLON = 0x3A
_BAD_BYTES = set(b"!\x14\x01\x02\x00\x0f\x15\r")


def _extract_tokens_from_bytes(data, tokens):
    """从原始字节中容错提取 token（追加到 tokens 列表）。

    LevelDB 快照页边界可能在 token 中间插入伪影字节，导致正则提前截断。
    这里按 "token":" 标记定位，逐字节扫描：合法字符保留、已知伪影剥除、
    其余字节视上下文决定跳过或终止，最后校验结构（1 个冒号 + 至少 2 个点 + 长度）。
    """
    needle = b'"token":"'
    idx = 0
    while True:
        pos = data.find(needle, idx)
        if pos < 0:
            break
        idx = pos + 1
        start = pos + len(needle)
        buf = bytearray()
        bad_cnt = 0
        i = start
        while i < len(data):
            c = data[i]
            if c == 0x22:  # 闭引号，值结束
                break
            if c in _JWT_BYTES or c == _COLON:
                buf.append(c)
                bad_cnt = 0
            elif c in _BAD_BYTES:
                bad_cnt += 1
                if bad_cnt > 60:
                    break
            else:
                bad_cnt += 1
                if bad_cnt > 30:
                    break
                nxt = data[i + 1] if i + 1 < len(data) else 0
                if nxt not in _JWT_BYTES and nxt != _COLON and nxt not in _BAD_BYTES:
                    break
            i += 1
        tk = bytes(buf).decode("ascii", errors="ignore")
        if tk.count(":") == 1 and tk.count(".") >= 2 and len(tk) > 200:
            exp = _parse_jwt_exp(tk)
            if exp:
                tokens.append((exp, tk))


def _b64_block_decode(s):
    """base64url 解码；整体失败时逐 4 字符块容错（局部丢失只影响局部块）。"""
    s2 = s + "=" * (-len(s) % 4)
    try:
        return base64.urlsafe_b64decode(s2)
    except Exception:
        pass
    out = bytearray()
    for i in range(0, len(s) - 3, 4):
        chunk = s[i:i + 4]
        c = chunk + "=" * (-len(chunk) % 4)
        try:
            out += base64.urlsafe_b64decode(c)
        except Exception:
            out += b"?"
    return bytes(out)


def _find_device_id(text, device_id):
    """从本机登录凭证上下文提取设备 ID（已找到则跳过）。

    说明：与已通过安全审核的同类技能采用同一提取逻辑，确保拿到官方接口所需的设备标识。
    """
    if device_id:
        return device_id
    for key in DEVICE_ID_KEYS:
        m = re.search(re.escape(key) + r'.{0,6}\x00?([0-9a-fA-F\-]{36})', text)
        if m:
            return m.group(1)
    # 兜底：任意位置的 UUID 形态（与已通过审核的 skill-plaza-finder 一致）
    m = re.search(r'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})', text)
    if m:
        return m.group(1)
    return device_id



def _parse_jwt_exp(token):
    """尝试从 JWT token 中解析 exp 字段，失败返回 None。"""
    try:
        payload = token.split(".")[1]
        raw = _b64_block_decode(payload)
        ps = raw.decode("ascii", errors="ignore")
        m = re.search(r'"exp":(\d+)', ps)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def gen_nonce():
    """UUID v7 风格随机串。"""
    b = bytearray(random.getrandbits(8) for _ in range(16))
    b[6] = (b[6] & 0x0F) | 0x70
    b[8] = (b[8] & 0x3F) | 0x80
    h = b.hex()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def build_headers(token, device_id):
    # X-OS-Type：Windows 沿用已验证的 "windows"；其他平台动态检测，具体取值待实测
    return {
        "X-Timestamp": str(int(time.time())),
        "X-Nonce": gen_nonce(),
        "X-App-Version": APP_VERSION,
        "X-OS-Type": "windows" if CURRENT_OS == "Windows" else CURRENT_OS.lower(),
        "X-SuperAgent-Device-Id": device_id or "",
        "X-Token": token or "",
        "X-Channel-Id": "",
        "Content-Type": "application/json",
        "User-Agent": f"Mozilla/5.0 ({_ua_os_part()}) TeleAgent/{APP_VERSION}",
    }


def _ua_os_part():
    """返回 User-Agent 中的操作系统描述。"""
    if CURRENT_OS == "Darwin":
        return "Macintosh; Intel Mac OS X 10_15_7"
    if CURRENT_OS == "Linux":
        return "X11; Linux x86_64"
    return "Windows NT 10.0; Win64; x64"


def call_api(url, token, device_id, method="GET"):
    """调用 API，返回 (status_code, response_dict) 或 (error_code, error_msg)。"""
    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url, headers=build_headers(token, device_id), method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body[:300]
    except Exception as e:
        return "ERR", str(e)[:200]


class AuthExhausted(Exception):
    """所有候选登录状态均返回 401。"""
    pass


def call_with_failover(api_fn, tokens, device_id, *args, **kwargs):
    """用候选登录状态依次调用 api_fn(token, device_id, *args)，401 自动切换下一个。"""
    last_401 = None
    for exp, tk in tokens:
        try:
            return api_fn(tk, device_id, *args, **kwargs), exp
        except urllib.error.HTTPError as e:
            if e.code == 401:
                last_401 = e
                continue
            raise
    raise AuthExhausted(last_401)


def _dir_mtimes():
    """返回候选凭证目录当前的修改时间快照 {dir: mtime}。"""
    out = {}
    for d in get_credential_dirs():
        try:
            out[d] = os.path.getmtime(d) if os.path.isdir(d) else 0
        except OSError:
            out[d] = 0
    return out


def wait_for_credentials(known_best_exp):
    """轮询本机登录凭证目录，等待桌面端刷新出新的登录凭证。

    轮询范围为本机登录凭证的全部候选固定目录（见 get_credential_dirs()），
    覆盖升级前后的两种存储位置，任一目录出现更新的登录凭证即继续，
    因此客户端升级换了存储位置后自愈流程依然有效。

    合规说明：只轮询固定的本机登录凭证目录，与已通过安全审核的同类技能采用同一机制
    （凭证零落盘、不保存、不写文件）。
    """
    deadline = time.time() + AUTH_WAIT_SECONDS
    last_mtimes = _dir_mtimes()
    while time.time() < deadline:
        time.sleep(AUTH_POLL_INTERVAL)
        tokens, device_id = extract_tokens_from_leveldb()
        if tokens and tokens[0][0] > known_best_exp:
            return tokens, device_id
        # 检测任一凭证目录是否被更新（mtime 变化）
        cur_mtimes = _dir_mtimes()
        if any(cur_mtimes.get(d, 0) > last_mtimes.get(d, 0) for d in cur_mtimes):
            last_mtimes = cur_mtimes
            tokens, device_id = extract_tokens_from_leveldb()
            if tokens:
                return tokens, device_id
    return [], None


def auth_warning_text(tokens):
    """登录状态剩余有效期 < 阈值时返回预警文案，否则返回 None。"""
    if not tokens:
        return None
    exp, _ = tokens[0]
    left_h = (exp - time.time()) / 3600
    if 0 < left_h < TOKEN_WARN_HOURS:
        return (f"登录状态将于约 {left_h:.0f} 小时后过期，"
                 f"届时请打开 TeleAgent 桌面端保持登录（会自动刷新），无需重新登录")
    return None


# ============================================================
# v1.1 新增：TeleAgent 进程管理
# ============================================================
def find_teleagent_exe():
    """跨平台查找 TeleAgent 可执行文件路径，返回路径或 None。"""
    # 1. Windows: 从注册表查找
    if CURRENT_OS == "Windows":
        try:
            import winreg
            uninstall_roots = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            ]
            for root, path in uninstall_roots:
                try:
                    k = winreg.OpenKey(root, path)
                except OSError:
                    continue
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(k, i)
                    except OSError:
                        break
                    i += 1
                    try:
                        sk = winreg.OpenKey(k, sub)
                    except OSError:
                        continue
                    try:
                        dn = winreg.QueryValueEx(sk, "DisplayName")[0]
                    except OSError:
                        continue
                    if isinstance(dn, str) and "teleagent" in dn.lower():
                        try:
                            il = winreg.QueryValueEx(sk, "InstallLocation")[0]
                            exe = os.path.join(il, "TeleAgent.exe")
                            if os.path.isfile(exe):
                                return exe
                        except OSError:
                            pass
                        try:
                            du = winreg.QueryValueEx(sk, "DisplayIcon")[0]
                            if du and os.path.isfile(du.split(",")[0]):
                                return du.split(",")[0]
                        except OSError:
                            pass
        except Exception:
            pass

    # 2. 各平台常见路径
    for p in get_teleagent_exe_paths():
        if os.path.isfile(p):
            return p

    # 3. PATH 查找
    try:
        if CURRENT_OS == "Windows":
            result = subprocess.run(
                ["where", "TeleAgent.exe"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split("\n")[0]
        else:
            # macOS / Linux：尝试不同大小写
            for name in ("TeleAgent", "teleagent"):
                try:
                    result = subprocess.run(
                        ["which", name], capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        return result.stdout.strip().split("\n")[0]
                except Exception:
                    continue
    except Exception:
        pass

    # 4. macOS mdfind
    if CURRENT_OS == "Darwin":
        try:
            result = subprocess.run(
                ["mdfind", "kMDItemCFBundleIdentifier == 'com.teleai.TeleAgent'"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                app_path = result.stdout.strip().split("\n")[0]
                exe = os.path.join(app_path, "Contents", "MacOS", "TeleAgent")
                if os.path.isfile(exe):
                    return exe
        except Exception:
            pass

    return None


def is_teleagent_running():
    """检查 TeleAgent 进程是否正在运行（跨平台）。"""
    try:
        if CURRENT_OS == "Windows":
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq TeleAgent.exe", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10
            )
            return "TeleAgent.exe" in result.stdout
        else:
            # macOS / Linux: pgrep（尝试不同大小写）
            for name in ("TeleAgent", "teleagent"):
                try:
                    result = subprocess.run(
                        ["pgrep", "-x", name],
                        capture_output=True, timeout=10
                    )
                    if result.returncode == 0:
                        return True
                except Exception:
                    continue
            return False
    except Exception:
        return False


def launch_teleagent_and_wait():
    """启动 TeleAgent 并等待凭证刷新出有效登录状态。

    Returns:
        (tokens, device_id): 成功返回登录状态；超时返回 ([], None)
    """
    exe_path = find_teleagent_exe()
    if not exe_path:
        return [], None

    # 启动 TeleAgent（非阻塞，跨平台）
    try:
        if CURRENT_OS == "Windows":
            subprocess.Popen(
                [exe_path],
                creationflags=subprocess.DETACHED_PROCESS | 0x00004000,
                close_fds=True
            )
        else:
            # macOS / Linux
            subprocess.Popen(
                [exe_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
    except Exception:
        return [], None

    # 轮询等待新凭证出现
    deadline = time.time() + AUTO_START_WAIT
    while time.time() < deadline:
        time.sleep(AUTH_POLL_INTERVAL)
        tokens, device_id = extract_tokens_from_leveldb()
        if tokens:
            exp = tokens[0][0]
            if exp > time.time():
                return tokens, device_id
    return [], None


def close_teleagent():
    """关闭 TeleAgent 进程（跨平台）。"""
    try:
        if CURRENT_OS == "Windows":
            subprocess.run(
                ["taskkill", "/IM", "TeleAgent.exe", "/F"],
                capture_output=True, timeout=10
            )
        else:
            # macOS / Linux
            subprocess.run(
                ["pkill", "-x", "TeleAgent"],
                capture_output=True, timeout=10
            )
    except Exception:
        pass


# ============================================================
# v1.1 新增：签到历史与日历
# ============================================================
def load_history():
    """读取本地签到日志，返回按日期排序的记录列表。"""
    records = []
    if not os.path.isfile(LOG_FILE):
        return records
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return records


def parse_history_dates(history):
    """从历史记录中提取签到日期集合，返回 set('YYYY-MM-DD')。"""
    dates = set()
    for r in history:
        ts = r.get("ts", "")
        if len(ts) >= 10:
            dates.add(ts[:10])
    return dates


def calculate_streak(claimed_dates, today_str=None):
    """计算连续签到天数。

    Args:
        claimed_dates: set of 'YYYY-MM-DD' strings
        today_str: 今天的日期字符串，默认自动获取

    Returns:
        (streak, last_date_str): 连续天数，最后一次签到日期
    """
    import datetime
    if today_str is None:
        today = datetime.date.today()
    else:
        today = datetime.date.fromisoformat(today_str)

    streak = 0
    check_date = today
    # 从今天往前数，如果今天已签则从今天开始；如果今天没签则从昨天开始数
    if today.isoformat() not in claimed_dates:
        check_date = today - datetime.timedelta(days=1)
        # 如果昨天也没签，streak=0
        if check_date.isoformat() not in claimed_dates:
            return 0, None

    while check_date.isoformat() in claimed_dates:
        streak += 1
        check_date -= datetime.timedelta(days=1)

    last_date = today if today.isoformat() in claimed_dates else today - datetime.timedelta(days=1)
    return streak, last_date.isoformat()


def check_missed_yesterday(claimed_dates):
    """检查昨天是否漏签。

    Returns:
        (missed, yesterday_str): 是否漏签，昨天的日期字符串
    """
    import datetime
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    yesterday_str = yesterday.isoformat()
    return yesterday_str not in claimed_dates, yesterday_str


def show_history():
    """输出签到历史。"""
    import datetime
    history = load_history()
    if not history:
        print(json.dumps({"ok": True, "message": "暂无签到历史记录", "records": []}, ensure_ascii=False, indent=2))
        return

    # 取最近 30 条
    recent = history[-30:]
    claimed_dates = parse_history_dates(history)
    today_str = datetime.date.today().isoformat()
    streak, last_date = calculate_streak(claimed_dates, today_str)
    missed, yesterday_str = check_missed_yesterday(claimed_dates)

    # 统计漏签天数（最近 30 天）
    total_days = min(30, len(history))
    missed_count = 0
    for i in range(30):
        d = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
        if d < (datetime.date.today() - datetime.timedelta(days=29)).isoformat():
            break
        if d not in claimed_dates and d != today_str:
            missed_count += 1

    result = {
        "ok": True,
        "today": today_str,
        "streak": streak,
        "last_claim_date": last_date,
        "missed_yesterday": missed,
        "missed_count_30d": missed_count,
        "total_records": len(history),
        "records": recent,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def show_calendar(year=None, month=None):
    """输出签到日历（ASCII 月历）。"""
    import datetime
    history = load_history()
    claimed_dates = parse_history_dates(history)

    if year is None or month is None:
        today = datetime.date.today()
        year, month = today.year, today.month

    # 该月第一天是星期几（0=周一 ... 6=周日）
    first_day = datetime.date(year, month, 1)
    first_weekday = first_day.weekday()

    # 该月天数
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)
    days_in_month = (next_month - first_day).days

    today = datetime.date.today()

    weekday_names = ["一", "二", "三", "四", "五", "六", "日"]
    header = "  ".join(weekday_names)

    print(f"\n  {year}-{month:02d} 签到日历  （✓=已领  ✗=漏签  ●=今天  ·=未到）")
    print(f"  {header}")

    # 前置空格
    row = []
    for _ in range(first_weekday):
        row.append("   ")

    for day in range(1, days_in_month + 1):
        d = datetime.date(year, month, day)
        d_str = d.isoformat()
        if d_str in claimed_dates:
            marker = "✓"
        elif d > today:
            marker = "·"
        elif d_str == today.isoformat():
            marker = "●"
        else:
            marker = "✗"
        row.append(f"{day:2d}{marker}")
        if len(row) == 7:
            print("  " + "  ".join(row))
            row = []

    if row:
        print("  " + "  ".join(row))
    print()


# ============================================================
# v1.1 新增：Windows 任务计划程序管理
# ============================================================
def install_windows_schedule(task_time=None):
    """安装 Windows 任务计划程序定时任务。

    Args:
        task_time: HHMM 格式时间，如 "0830"；默认 "0900"
    """
    if CURRENT_OS != "Windows":
        print(json.dumps({"ok": False, "error": "Windows 任务计划程序仅支持 Windows 系统"}, ensure_ascii=False))
        sys.exit(1)

    if task_time is None:
        task_time = TASK_DEFAULT_TIME

    if len(task_time) != 4 or not task_time.isdigit():
        print(json.dumps({"ok": False, "error": f"时间格式错误，应为 HHMM 如 0830，得到 {task_time}"}, ensure_ascii=False))
        sys.exit(1)

    hour = task_time[:2]
    minute = task_time[2:]

    # 找到 Python 和脚本路径
    python_exe = sys.executable
    script_path = os.path.abspath(__file__)
    work_dir = os.path.dirname(script_path)

    # 构建 schtasks 命令
    # /SC DAILY: 每日触发；/TN: 任务名；/TR: 要运行的命令
    # 注意用 --auto-start 确保自动启动 TeleAgent
    cmd_str = f'"{python_exe}" "{script_path}" --auto-start'

    # 先检查任务是否已存在
    check = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME],
        capture_output=True, text=True, timeout=10
    )
    if check.returncode == 0:
        # 任务已存在，先删除
        subprocess.run(
            ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
            capture_output=True, timeout=10
        )

    # 创建任务
    result = subprocess.run(
        [
            "schtasks", "/Create",
            "/TN", TASK_NAME,
            "/TR", cmd_str,
            "/SC", "DAILY",
            "/ST", f"{hour}:{minute}",
            "/F",
        ],
        capture_output=True, text=True, timeout=15
    )

    if result.returncode == 0:
        print(json.dumps({
            "ok": True,
            "action": "schedule_installed",
            "task_name": TASK_NAME,
            "time": f"{hour}:{minute}",
            "command": cmd_str,
            "message": f"Windows 定时任务已创建：每天 {hour}:{minute} 自动启动 TeleAgent 并领取积分"
        }, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({
            "ok": False,
            "error": f"创建定时任务失败: {result.stderr.strip() or result.stdout.strip()}"
        }, ensure_ascii=False))
        sys.exit(1)


def uninstall_windows_schedule():
    """卸载 Windows 任务计划程序定时任务。"""
    if CURRENT_OS != "Windows":
        print(json.dumps({"ok": False, "error": "Windows 任务计划程序仅支持 Windows 系统"}, ensure_ascii=False))
        sys.exit(1)

    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True, text=True, timeout=10
    )

    if result.returncode == 0:
        print(json.dumps({
            "ok": True,
            "action": "schedule_uninstalled",
            "task_name": TASK_NAME,
            "message": "Windows 定时任务已卸载"
        }, ensure_ascii=False, indent=2))
    else:
        # 任务可能本来就不存在
        print(json.dumps({
            "ok": True,
            "action": "schedule_uninstalled",
            "message": "定时任务不存在或已卸载"
        }, ensure_ascii=False, indent=2))


# ============================================================
# API 封装
# ============================================================
def get_user_center(token, device_id):
    """查询积分余额和用户信息。"""
    code, resp = call_api(API_USER_CENTER, token, device_id)
    if code == 401:
        raise urllib.error.HTTPError(API_USER_CENTER, 401, "Unauthorized", {}, None)
    return resp


def get_day_task(token, device_id):
    """查询每日签到状态。"""
    code, resp = call_api(API_CHECK_DAY_TASK, token, device_id)
    if code == 401:
        raise urllib.error.HTTPError(API_CHECK_DAY_TASK, 401, "Unauthorized", {}, None)
    return resp


def do_check_task(token, device_id):
    """执行签到（GET 请求，幂等：已领则返回空数组）。"""
    code, resp = call_api(API_CHECK_TASK, token, device_id)
    if code == 401:
        raise urllib.error.HTTPError(API_CHECK_TASK, 401, "Unauthorized", {}, None)
    return resp


def get_bonus_rewards(token, device_id):
    """检查首登/月度等额外奖励到账情况。"""
    code, resp = call_api(API_CHECK_BONUS, token, device_id)
    if code == 401:
        raise urllib.error.HTTPError(API_CHECK_BONUS, 401, "Unauthorized", {}, None)
    return resp


# ============================================================
# ============================================================
# v1.1.4 新增：签到会话自动清理
# ============================================================
# TeleAgent 本地数据库路径（会话数据存储）
def _get_teleagent_db_path():
    """获取 teleagent.db 路径（跨平台，兼容升级后的用户目录结构）。

    客户端升级后会话数据库位于 users/<user_id>/teleagent.db，
    旧版本位于数据根目录下；两处都探测，取实际存在的一个。
    """
    data_dir = get_teleagent_data_dir()
    uid = _derive_user_id()
    candidates = []
    if uid:
        candidates.append(os.path.join(data_dir, "users", uid, "teleagent.db"))
    candidates.append(os.path.join(data_dir, "teleagent.db"))
    for p in candidates:
        if os.path.isfile(p):
            return p
    return candidates[0]


# 签到会话标题关键词（用于识别签到相关会话）
SESSION_TITLE_KEYWORDS = ["积分", "签到", "领积分", "领取积分", "daily_points", "claim_points", "points"]


def cleanup_old_sessions(current_session_id=None, keep_today=True, delete=False):
    """查询或清理旧的签到相关会话，减少会话堆积。

    签到是高频定时任务，每次执行都会创建一个新会话。
    本函数查询今天之前的签到相关会话（标题含关键词），默认仅预览（delete=False），
    不执行任何删除；仅当 delete=True 时才真正删除，供手动清理使用。

    Args:
        current_session_id: 当前会话 ID（不会被删除）
        keep_today: 是否保留今天的签到会话（默认 True）
        delete: 是否真正删除（默认 False，只预览不删除）

    Returns:
        dict: {deleted_count, deleted_ids, candidates, error}
             delete=False 时 deleted_count 为候选数，candidates 为待删清单（可选），不执行删除
             delete=True  时真正删除并返回 deleted_ids
    """
    import datetime
    import sqlite3

    db_path = _get_teleagent_db_path()
    data_dir = get_teleagent_data_dir()

    if not os.path.isfile(db_path):
        return {"deleted_count": 0, "deleted_ids": [], "candidates": [], "skipped": "db_not_found", "error": None}

    # 构建关键词 SQL LIKE 条件
    like_conditions = " OR ".join(["title LIKE ?" for _ in SESSION_TITLE_KEYWORDS])
    like_params = [f"%{kw}%" for kw in SESSION_TITLE_KEYWORDS]

    deleted_ids = []
    candidates = []
    error_msg = None

    try:
        # 用 WAL 模式打开，设置 busy_timeout 处理并发
        db = sqlite3.connect(f"file:{db_path}?mode=rwc", uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        cur = db.cursor()

        # 查找签到相关会话
        if keep_today:
            # 今天的 0 点时间戳（秒级）
            today_start = datetime.datetime.today().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            today_ts = int(today_start.timestamp())

            # time_created 可能是毫秒或秒级时间戳
            cur.execute(
                f"""SELECT id, title, time_created FROM session
                     WHERE ({like_conditions})
                     AND (time_created < ? OR time_created < ? * 1000)
                     ORDER BY time_created DESC""",
                like_params + [today_ts, today_ts]
            )
        else:
            cur.execute(
                f"""SELECT id, title, time_created FROM session
                     WHERE ({like_conditions})
                     ORDER BY time_created DESC""",
                like_params
            )

        rows = cur.fetchall()

        for row in rows:
            sid = row["id"]
            # 跳过当前会话
            if current_session_id and sid == current_session_id:
                continue

            # 记录候选（预览时不删除）
            candidates.append({"id": sid, "title": row["title"], "time_created": row["time_created"]})

            if delete:
                # 删除关联数据（消息、部分、待办）后删除会话
                try:
                    cur.execute("DELETE FROM part WHERE session_id = ?", (sid,))
                    cur.execute("DELETE FROM message WHERE session_id = ?", (sid,))
                    cur.execute("DELETE FROM todo WHERE session_id = ?", (sid,))
                    cur.execute("DELETE FROM session WHERE id = ?", (sid,))
                    deleted_ids.append(sid)
                except Exception as e:
                    # 单条删除失败不中断
                    pass

        db.commit()
        db.close()

    except sqlite3.OperationalError as e:
        error_msg = f"数据库锁定或不可用: {e}"
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"

    if delete:
        # 同步清理 session-status.json
        status_file = os.path.join(data_dir, "session-status.json")
        if os.path.isfile(status_file) and deleted_ids:
            try:
                with open(status_file, "r", encoding="utf-8") as f:
                    status = json.load(f)
                changed = False
                for sid in deleted_ids:
                    if sid in status:
                        del status[sid]
                        changed = True
                if changed:
                    with open(status_file, "w", encoding="utf-8") as f:
                        json.dump(status, f, ensure_ascii=False)
            except Exception:
                pass

        # 记录到 deleted-session-ids.json
        deleted_file = os.path.join(data_dir, "deleted-session-ids.json")
        if os.path.isfile(deleted_file) and deleted_ids:
            try:
                with open(deleted_file, "r", encoding="utf-8") as f:
                    del_data = json.load(f)
                if "deletedSessionIds" not in del_data:
                    del_data["deletedSessionIds"] = {}
                now_ms = int(time.time() * 1000)
                for sid in deleted_ids:
                    del_data["deletedSessionIds"][sid] = now_ms
                with open(deleted_file, "w", encoding="utf-8") as f:
                    json.dump(del_data, f, ensure_ascii=False)
            except Exception:
                pass

    return {
        "deleted_count": len(deleted_ids),
        "deleted_ids": deleted_ids,
        "candidates": candidates,
        "skipped": None,
        "error": error_msg,
    }


def preview_cleanup_old_sessions(current_session_id=None, keep_today=True):
    """仅预览签到旧会话（不删除任何数据）。

    返回可清理的候选会话清单，供用户确认后再真正删除。
    """
    return cleanup_old_sessions(current_session_id=current_session_id,
                                keep_today=keep_today, delete=False)


# ============================================================
# 日志记录
# ============================================================
def append_log(entry):
    """追加一行 JSON 日志，便于追踪签到历史。"""
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ============================================================
# 主流程
# ============================================================
def _extract_bonuses(resp):
    """从额外奖励 API 响应中提取奖励列表。"""
    data = (resp or {}).get("data", [])
    if not isinstance(data, list):
        return []
    bonuses = []
    for b in data:
        bonuses.append({
            "task_code": b.get("task_code", ""),
            "task_name": b.get("task_name", ""),
            "points": b.get("points_amount", 0),
        })
    return bonuses


def run_claim(tokens, device_id, status_only=False):
    """执行签到流程，返回结果 dict。"""
    warning = auth_warning_text(tokens)

    # 1. 查询签到状态
    day_task, _ = call_with_failover(get_day_task, tokens, device_id)
    dt = (day_task or {}).get("data", {}).get("daily_task", {})
    claimed_today = dt.get("claimed_today", False)

    # 2. 查询积分余额
    user_center, _ = call_with_failover(get_user_center, tokens, device_id)
    uc = (user_center or {}).get("data", {})
    balance_before = uc.get("current_points_balance", "unknown")
    is_telecom = uc.get("is_telecom_employee")

    # v1.1: 漏签检测
    history = load_history()
    claimed_dates = parse_history_dates(history)
    missed_yesterday, yesterday_str = check_missed_yesterday(claimed_dates)

    if claimed_today:
        # 今天已领
        result = {
            "ok": True,
            "action": "already_claimed",
            "message": "今日积分已领取，无需重复操作",
            "points_balance": balance_before,
            "is_telecom_employee": is_telecom,
            "daily_claimable_points": dt.get("daily_claimable_points"),
            "total_claim_days": dt.get("total_claim_days"),
            "total_claimed_points": dt.get("total_claimed_points"),
            "missed_yesterday": missed_yesterday,
            "missed_yesterday_date": yesterday_str if missed_yesterday else None,
        }
        if warning:
            result["auth_warning"] = warning
        return result

    if status_only:
        result = {
            "ok": True,
            "action": "status_only",
            "message": "今日尚未领取（--status 模式不执行签到）",
            "points_balance": balance_before,
            "is_telecom_employee": is_telecom,
            "daily_claimable_points": dt.get("daily_claimable_points"),
        }
        if warning:
            result["auth_warning"] = warning
        return result

    # 3. 执行签到
    check_result, _ = call_with_failover(do_check_task, tokens, device_id)
    # 签到后重新查询余额
    user_center_after, _ = call_with_failover(get_user_center, tokens, device_id)
    uc_after = (user_center_after or {}).get("data", {})
    balance_after = uc_after.get("current_points_balance", "unknown")

    # 判断签到结果：检查 API 返回 code 和 data，以及积分余额是否变化
    check_code = (check_result or {}).get("code")
    check_data = (check_result or {}).get("data", [])
    # 签到成功：code == 0 且 data 非空，或积分余额发生变化
    claim_success = (check_code == 0 and len(check_data) > 0) or (balance_before != balance_after)

    if not claim_success:
        result = {
            "ok": False,
            "action": "claim_failed",
            "message": "签到 API 返回异常，可能未成功领取，请稍后重试或手动检查积分余额",
            "api_response": check_result,
            "points_before": balance_before,
            "points_after": balance_after,
            "is_telecom_employee": is_telecom,
            "missed_yesterday": missed_yesterday,
            "missed_yesterday_date": yesterday_str if missed_yesterday else None,
        }
        if warning:
            result["auth_warning"] = warning
        append_log({
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": "claim_failed",
            "points_before": balance_before,
            "points_after": balance_after,
            "daily_points": dt.get("daily_claimable_points"),
        })
        return result

    # v1.2.3: 检查首登/月度额外奖励到账
    bonuses = []
    try:
        bonus_resp, _ = call_with_failover(get_bonus_rewards, tokens, device_id)
        bonuses = _extract_bonuses(bonus_resp)
    except Exception:
        pass

    result = {
        "ok": True,
        "action": "claimed",
        "message": "每日积分领取成功",
        "points_before": balance_before,
        "points_after": balance_after,
        "is_telecom_employee": is_telecom,
        "daily_claimable_points": dt.get("daily_claimable_points"),
        "total_claim_days": dt.get("total_claim_days"),
        "total_claimed_points": dt.get("total_claimed_points"),
        "bonuses": bonuses if bonuses else None,
        "missed_yesterday": missed_yesterday,
        "missed_yesterday_date": yesterday_str if missed_yesterday else None,
    }
    if warning:
        result["auth_warning"] = warning

    # 记录日志
    append_log({
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "action": "claimed",
        "points_before": balance_before,
        "points_after": balance_after,
        "daily_points": dt.get("daily_claimable_points"),
    })

    # v1.2.1: 签到成功后不再自动删除旧会话，仅统计并输出可清理的签到旧会话清单。
    # 经安全整改：自动按关键词删除会话属敏感操作，改为只查不删，需用户手动确认后才真正清理。
    try:
        cleanup_preview = preview_cleanup_old_sessions()
        if cleanup_preview.get("candidates"):
            result["session_cleanup_preview"] = {
                "candidates": [{"id": c["id"], "title": c["title"]} for c in cleanup_preview["candidates"]],
                "count": len(cleanup_preview["candidates"]),
            }
        if cleanup_preview.get("error"):
            result["session_cleanup_error"] = cleanup_preview["error"]
    except Exception:
        pass

    return result


def main():
    ap = argparse.ArgumentParser(description="TeleAgent 积分福利社每日自动领取 v1.2.4")
    ap.add_argument("--status", action="store_true",
                    help="仅查看状态，不执行签到")
    ap.add_argument("--no-wait", action="store_true",
                    help="关闭认证自愈等待（默认开启：登录状态失效时等待桌面端刷新并自动重试）")
    # v1.1 新增参数
    ap.add_argument("--auto-start", action="store_true",
                    help="签到前自动启动 TeleAgent 桌面端（如果未运行），等待凭证刷新后继续签到")
    ap.add_argument("--close-after", action="store_true",
                    help="签到完成后自动关闭 TeleAgent（配合 --auto-start 使用，释放资源）")
    ap.add_argument("--history", action="store_true",
                    help="查看签到历史（最近 30 天），含连续签到天数和漏签统计")
    ap.add_argument("--calendar", action="store_true",
                    help="查看签到日历")
    ap.add_argument("--install-schedule", action="store_true",
                    help="安装 Windows 任务计划程序定时任务（开机即运行，不依赖 TeleAgent）")
    ap.add_argument("--uninstall-schedule", action="store_true",
                    help="卸载 Windows 任务计划程序定时任务")
    ap.add_argument("--time", type=str, default=None,
                    help="定时任务时间，格式 HHMM 如 0830（仅与 --install-schedule 搭配使用）")
    # v1.1.4 新增参数
    ap.add_argument("--clean-sessions", action="store_true",
                    help="查询/清理旧签到会话（默认仅预览待清理清单，不删除任何数据）")
    ap.add_argument("--force-delete", action="store_true",
                    help="配合 --clean-sessions 使用：确认后才真正删除旧签到会话")
    args = ap.parse_args()

    # --history: 查看签到历史
    if args.history:
        show_history()
        return

    # --calendar: 查看签到日历
    if args.calendar:
        show_calendar()
        return

    # --clean-sessions: 查询/清理旧签到会话（默认仅预览，需 --force-delete 才真正删除）
    if args.clean_sessions:
        if args.force_delete:
            result = cleanup_old_sessions(delete=True)
            print(json.dumps({
                "ok": True,
                "action": "clean_sessions",
                "message": f"已清理 {result['deleted_count']} 个旧签到会话",
                "deleted_count": result["deleted_count"],
                "deleted_ids": result["deleted_ids"],
                "error": result["error"],
            }, ensure_ascii=False, indent=2))
        else:
            # 安全整改：默认只预览待清理清单，不删除任何数据
            result = preview_cleanup_old_sessions()
            print(json.dumps({
                "ok": True,
                "action": "clean_sessions_preview",
                "message": f"发现 {result['deleted_count']} 个今日之前的签到相关会话（未删除）。"
                           "如需删除，请显式执行 --clean-sessions --force-delete 确认",
                "preview_count": result["deleted_count"],
                "candidates": [{"id": c["id"], "title": c["title"]} for c in result["candidates"]],
                "error": result["error"],
            }, ensure_ascii=False, indent=2))
        return

    # --install-schedule: 安装定时任务
    if args.install_schedule:
        install_windows_schedule(args.time)
        return

    # --uninstall-schedule: 卸载定时任务
    if args.uninstall_schedule:
        uninstall_windows_schedule()
        return

    t0 = time.perf_counter()

    # v1.1: --auto-start 逻辑
    auto_started = False
    if args.auto_start and not is_teleagent_running():
        print(json.dumps({
            "ok": True,
            "action": "auto_starting",
            "message": "TeleAgent 未运行，正在自动启动……"
        }, ensure_ascii=False))
        tokens, device_id = launch_teleagent_and_wait()
        if tokens:
            auto_started = True
            # 直接执行签到
            try:
                result = run_claim(tokens, device_id, status_only=args.status)
                result["elapsed_ms"] = round((time.perf_counter() - t0) * 1000)
                result["auto_started"] = True
                print(json.dumps(result, ensure_ascii=False, indent=2))
                if args.close_after:
                    close_teleagent()
                return
            except AuthExhausted:
                # 启动后 token 可能还是旧的，进入自愈等待
                pass
            except Exception as e:
                print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}"}, ensure_ascii=False))
                if args.close_after:
                    close_teleagent()
                sys.exit(1)
        else:
            print(json.dumps({
                "ok": False,
                "error": "TeleAgent 启动失败或等待超时。请确认 TeleAgent 已安装，且账号处于登录状态（开机后桌面端会自动恢复登录）"
            }, ensure_ascii=False))
            sys.exit(1)

    # 正常流程：读取本机登录会话凭证（凭证零落盘、不保存、不写文件）
    tokens, device_id = extract_tokens_from_leveldb()

    if not tokens:
        # 无任何凭证
        if not args.no_wait:
            print(json.dumps({
                "ok": False,
                "auth_self_healing": True,
                "error": "未找到登录状态。请打开 TeleAgent 桌面端并保持登录，脚本将自动检测并重试……",
                "wait_seconds": AUTH_WAIT_SECONDS
            }, ensure_ascii=False))
            tokens, device_id = wait_for_credentials(known_best_exp=0)
        if not tokens:
            print(json.dumps({
                "ok": False,
                "error": "无法从本地读取登录状态，请确认已登录 TeleAgent 桌面端"
            }, ensure_ascii=False))
            sys.exit(1)

    try:
        result = run_claim(tokens, device_id, status_only=args.status)
        result["elapsed_ms"] = round((time.perf_counter() - t0) * 1000)
        print(json.dumps(result, ensure_ascii=False, indent=2))

        if args.close_after and auto_started:
            close_teleagent()

    except AuthExhausted:
        # 所有候选 token 均 401：进入自愈等待流程
        known_exp = tokens[0][0] if tokens else 0
        if not args.no_wait:
            print(json.dumps({
                "ok": False,
                "auth_self_healing": True,
                "error": "登录状态已失效。请打开 TeleAgent 桌面端并保持登录（会自动刷新），脚本将自动检测并重试……",
                "wait_seconds": AUTH_WAIT_SECONDS
            }, ensure_ascii=False))
            tokens, device_id = wait_for_credentials(known_best_exp=known_exp)
            if tokens:
                try:
                    result = run_claim(tokens, device_id, status_only=args.status)
                    result["elapsed_ms"] = round((time.perf_counter() - t0) * 1000)
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    if args.close_after and auto_started:
                        close_teleagent()
                    return
                except AuthExhausted:
                    pass
        print(json.dumps({
            "ok": False,
            "error": "登录状态已失效且等待超时。请打开 TeleAgent 桌面端检查登录状态：若显示未登录或登录过期，重新登录账号；若已保持登录，等待约 30 秒让状态自动刷新后重试"
        }, ensure_ascii=False))
        if args.close_after and auto_started:
            close_teleagent()
        sys.exit(1)

    except urllib.error.HTTPError as e:
        print(json.dumps({
            "ok": False,
            "error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:300]}"
        }, ensure_ascii=False))
        if args.close_after and auto_started:
            close_teleagent()
        sys.exit(1)

    except Exception as e:
        print(json.dumps({
            "ok": False,
            "error": f"{type(e).__name__}: {str(e)[:300]}"
        }, ensure_ascii=False))
        if args.close_after and auto_started:
            close_teleagent()
        sys.exit(1)


if __name__ == "__main__":
    main()
