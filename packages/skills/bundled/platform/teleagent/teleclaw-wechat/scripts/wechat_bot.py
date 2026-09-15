#!/usr/bin/env python3
"""
微信 iLink Bot 客户端 — teleclaw-wechat 技能核心脚本

基于腾讯官方 iLink Bot API 协议实现，参考开源项目：
  - codeenxi/weixin-ClawBot-API（Python/Node.js 实现）
  - minibear2021/wechat_clawbot_sdk（Python SDK）
  - ikrong/wx-clawbot（TypeScript 封装）
  - x1ah/wechat-ilink-demo（iLink 协议拆解）

用法：
  python wechat_bot.py [--config CONFIG_PATH] [--test]

功能：
  - 扫码登录微信（生成二维码图片，由微信扫码绑定）
  - 长轮询实时接收消息
  - 主动发送文本消息给指定用户
  - 发送 typing 状态（"正在输入"）
  - 24 小时自动重连
  - Bot 指令系统（/time /help /status）
  - 配置文件管理（首次运行自动引导创建）
  - 会话状态持久化（重启后可复用）

重要：iLink API 返回的 qrcode_img_content 是 URL 链接，
该 URL 无法在浏览器直接访问，必须编码为二维码图片后
由微信"扫一扫"扫描完成绑定。
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import random
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

try:
    import aiohttp
except ImportError:
    print("缺少依赖 aiohttp，请运行: pip install aiohttp")
    sys.exit(1)

try:
    import qrcode as qrcode_lib
except ImportError:
    qrcode_lib = None

try:
    import psutil
except ImportError:
    psutil = None

# ==================== 常量 ====================

ILINK_BASE_URL = "https://ilinkai.weixin.qq.com"
CDN_BASE_URL = "https://novac2c.cdn.weixin.qq.com/c2c"
CHANNEL_VERSION = "1.0.2"
POLL_TIMEOUT_MS = 35000
RECONNECT_DEFAULTS = {
    "session_duration": 24 * 3600,
    "warning_before": 2 * 3600,
    "reminder_interval": 30 * 60,
    "force_before": 30 * 60,
    "qrcode_scan_timeout": 600,
}
RECONNECT_TEST = {
    "session_duration": 300,
    "warning_before": 60,
    "reminder_interval": 30,
    "force_before": 60,
    "qrcode_scan_timeout": 120,
}

# 消息类型
MSG_TYPE_TEXT = 1
MSG_TYPE_IMAGE = 2
MSG_TYPE_VOICE = 3
MSG_TYPE_FILE = 4
MSG_TYPE_VIDEO = 5

# Bot 发送消息时的 message_type
BOT_MSG_TYPE = 2
BOT_MSG_STATE_FINISH = 2

# ==================== 数据类 ====================


@dataclass
class WeChatConfig:
    """Bot 运行配置"""

    system_prompt: str = "你是接入微信的星辰超级智能体 AI 助手。回答要简洁、准确、可执行。禁止调用 question tool。"
    session_timeout: int = 1800  # AI 会话超时（秒），超时后为新对话
    reconnect: dict[str, int] = field(default_factory=lambda: dict(RECONNECT_DEFAULTS))

    @classmethod
    def load(cls, path: str) -> "WeChatConfig":
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            reconnect_raw = data.get("reconnect", {})
            reconnect = dict(RECONNECT_DEFAULTS)
            reconnect.update({k: v for k, v in reconnect_raw.items() if k in reconnect})
            return cls(
                system_prompt=data.get("prompt", data.get("system_prompt", "你是接入微信的星辰超级智能体 AI 助手。回答要简洁、准确、可执行。禁止调用 question tool。")),
                session_timeout=data.get("session_timeout", 1800),
                reconnect=reconnect,
            )
        return cls()

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "prompt": self.system_prompt,
                    "session_timeout": self.session_timeout,
                    "reconnect": self.reconnect,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )


@dataclass
class SessionState:
    """登录会话持久化状态"""

    bot_token: str = ""
    base_url: str = ""
    account_id: str = ""
    login_time: float = 0.0
    get_updates_buf: str = ""

    @classmethod
    def load(cls, path: str) -> Optional["SessionState"]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(
                bot_token=data.get("bot_token", ""),
                base_url=data.get("base_url", ""),
                account_id=data.get("account_id", ""),
                login_time=data.get("login_time", 0.0),
                get_updates_buf=data.get("get_updates_buf", ""),
            )
        return None

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "bot_token": self.bot_token,
                    "base_url": self.base_url,
                    "account_id": self.account_id,
                    "login_time": self.login_time,
                    "get_updates_buf": self.get_updates_buf,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )


# ==================== Super-Agent AI 客户端 ====================


class SuperAgentClient:
    """本地 super-agent AI 客户端（按用户隔离会话）

    每个微信用户拥有独立的 super-agent session，
    AI 上下文按用户隔离，互不串扰。

    会话管理策略（参考 OpenClaw per-channel-peer 模式）：
    - 首次消息：为该用户创建新 session
    - 超时（默认 30 分钟）：自动创建新 session，丢弃旧上下文
    - 用户发送 /new 或 /reset：强制创建新 session
    - 服务端错误（session not found）：自动重建

    关键：
    - 凭证从 im-service 进程环境变量中读取（psutil）
    - Local Auth 签名使用换行符 \\n 拼接（非空格）
    - 签名格式：HMAC-SHA256(sessionKey, "local-v1\\nMETHOD\\npath\\ntimestamp\\nnonce")
    - 每次获取的凭证在 TeleClaw 重启后失效
    """

    SIGN_VERSION = "local-v1"
    DEFAULT_SESSION_TIMEOUT = 1800  # 30 分钟

    def __init__(self, logger: Optional[logging.Logger] = None, session_timeout: int = 0):
        # 凭证
        self._base_url: str = ""
        self._username: str = ""
        self._password: str = ""
        self._session_key: str = ""
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._credentials_ok = False

        # 按用户隔离的会话管理
        self._user_sessions: dict[str, str] = {}       # user_id → session_id
        self._user_last_active: dict[str, float] = {}   # user_id → timestamp
        self._session_timeout = session_timeout or self.DEFAULT_SESSION_TIMEOUT

        self._logger = logger or logging.getLogger("teleclaw-wechat")

    # ---------- 凭证发现 ----------

    @staticmethod
    def discover_credentials() -> dict[str, str]:
        """从运行中的进程自动发现 super-agent 凭证

        返回 dict，包含：
        - session_key: HMAC 签名密钥
        - username: Basic Auth 用户名
        - password: Basic Auth 密码
        - base_url: super-agent 服务地址
        """
        if psutil is None:
            raise RuntimeError("缺少 psutil 库，请运行: pip install psutil")

        data: dict[str, str] = {}

        # 1. 从 im-service 进程获取凭证
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline", []) or []
                if any("im-service" in str(c) for c in cmdline):
                    env = proc.environ()
                    data["session_key"] = env.get("SUPER_AGENT_LOCAL_SESSION_KEY", "")
                    data["username"] = env.get("SUPER_AGENT_OPENCODE_USERNAME", "")
                    data["password"] = env.get("SUPER_AGENT_OPENCODE_PASSWORD", "")
                    break
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue

        # 2. 从状态文件获取服务地址
        state_file = os.path.join(
            os.path.expanduser("~"),
            ".local", "share", "teleai-super-agent",
            "im-bridge-opencode-state.json",
        )
        if os.path.exists(state_file):
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            data["base_url"] = state.get("url", "")

        # 3. 如果状态文件无地址，从进程参数查找端口
        if not data.get("base_url"):
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    name = proc.info.get("name", "") or ""
                    if "super-agent" in name.lower():
                        for arg in proc.info.get("cmdline", []) or []:
                            if arg.startswith("--port="):
                                data["base_url"] = f"http://127.0.0.1:{arg.split('=')[1]}"
                                break
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    continue

        return data

    # ---------- 签名 ----------

    def _sign_request(self, method: str, path: str) -> dict[str, str]:
        """HMAC-SHA256 Local Auth 签名

        签名载荷使用换行符 (\\n) 拼接，不使用空格！
        这是之前调试中发现的关键差异：源码反编译显示 .join(' ')
        但实际二进制使用 .join('\\n')。
        """
        timestamp = str(int(time.time() * 1000))
        nonce = os.urandom(12).hex()

        # CRITICAL: 使用换行符拼接，不是空格！
        payload = "\n".join([
            self.SIGN_VERSION,
            method.upper(),
            path,
            timestamp,
            nonce,
        ])
        sig_bytes = hmac.new(
            self._session_key.encode(),
            payload.encode(),
            hashlib.sha256,
        ).digest()
        # base64url 编码，去除填充
        signature = base64.urlsafe_b64encode(sig_bytes).decode().rstrip("=")

        return {
            "X-SA-Sign-Version": self.SIGN_VERSION,
            "X-SA-Timestamp": timestamp,
            "X-SA-Nonce": nonce,
            "X-SA-Signature": signature,
        }

    def _basic_auth_header(self) -> str:
        """构造 Basic Auth 头"""
        cred = base64.b64encode(f"{self._username}:{self._password}".encode()).decode()
        return f"Basic {cred}"

    # ---------- 初始化 ----------

    async def initialize(self) -> bool:
        """初始化：发现凭证 + 创建 HTTP 会话

        不再在初始化时创建 AI session，改为按需按用户创建。
        返回是否成功。失败时后续 chat() 调用会返回错误提示。
        """
        try:
            creds = self.discover_credentials()
        except Exception as e:
            self._logger.error(f"凭证发现失败: {e}")
            return False

        required = ["session_key", "username", "password", "base_url"]
        missing = [k for k in required if not creds.get(k)]
        if missing:
            self._logger.error(f"缺少必要凭证: {missing}，请确保 TeleClaw 正在运行")
            return False

        self._session_key = creds["session_key"]
        self._username = creds["username"]
        self._password = creds["password"]
        self._base_url = creds["base_url"].rstrip("/")
        self._credentials_ok = True

        self._logger.info(f"Super-agent 凭证已发现: {self._base_url}")

        self._http_session = aiohttp.ClientSession()

        return True

    async def _create_session(self, user_id: str) -> Optional[str]:
        """为指定用户创建 AI 对话会话

        返回 session_id；失败返回 None。
        """
        url = f"{self._base_url}/session"
        body = {"title": f"wechat-{user_id[:20]}"}
        headers = {"Authorization": self._basic_auth_header()}

        try:
            async with self._http_session.post(
                url, json=body, headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as res:
                data = await res.json(content_type=None)
                session_id = data.get("id")
                if session_id:
                    self._user_sessions[user_id] = session_id
                    self._user_last_active[user_id] = time.time()
                    self._logger.info(f"[{user_id[:16]}] AI 会话已创建: {session_id}")
                    return session_id
                else:
                    self._logger.error(f"[{user_id[:16]}] 创建 AI 会话失败: {json.dumps(data)[:200]}")
                    return None
        except Exception as e:
            self._logger.error(f"[{user_id[:16]}] 创建 AI 会话异常: {e}")
            return None

    def _get_user_session(self, user_id: str) -> Optional[str]:
        """获取用户的 session_id，超时则清除"""
        session_id = self._user_sessions.get(user_id)
        if not session_id:
            return None
        last = self._user_last_active.get(user_id, 0)
        if time.time() - last > self._session_timeout:
            self._logger.info(f"[{user_id[:16]}] 会话超时（{self._session_timeout}s），将重建")
            self._user_sessions.pop(user_id, None)
            self._user_last_active.pop(user_id, None)
            return None
        return session_id

    def reset_user_session(self, user_id: str) -> None:
        """强制重置指定用户的 AI 会话（用于 /new 指令）"""
        self._user_sessions.pop(user_id, None)
        self._user_last_active.pop(user_id, None)
        self._logger.info(f"[{user_id[:16]}] 会话已手动重置")

    def get_session_stats(self) -> dict[str, Any]:
        """获取当前会话管理统计信息"""
        now = time.time()
        active = sum(1 for t in self._user_last_active.values() if now - t <= self._session_timeout)
        return {
            "total_users": len(self._user_sessions),
            "active_sessions": active,
            "timeout_seconds": self._session_timeout,
        }

    # ---------- 对话 ----------

    async def chat(self, user_id: str, text: str, system_prompt: Optional[str] = None) -> str:
        """发送消息给 AI 并获取回复文本（按用户隔离会话）

        如果没有可用会话，自动尝试为该用户创建。
        超时的会话自动重建。返回 AI 回复文本；出错时返回用户友好的错误提示。
        """
        # 懒初始化
        if not self._http_session or not self._credentials_ok:
            if not await self.initialize():
                return "AI 服务暂不可用（TeleClaw 可能未运行），请稍后再试。"

        # 获取或创建该用户的 session
        session_id = self._get_user_session(user_id)
        if not session_id:
            session_id = await self._create_session(user_id)
            if not session_id:
                return "AI 服务暂不可用，请稍后再试。"

        path = f"/session/{session_id}/message"
        url = f"{self._base_url}{path}"

        body: dict[str, Any] = {
            "parts": [{"type": "text", "text": text}],
            "stream": False,
        }
        if system_prompt:
            body["system"] = system_prompt

        headers = {
            "Authorization": self._basic_auth_header(),
            "Content-Type": "application/json",
            **self._sign_request("POST", path),
        }

        try:
            async with self._http_session.post(
                url, json=body, headers=headers,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as res:
                data = await res.json(content_type=None)

                # 检查错误
                info = data.get("info", {})
                if isinstance(info, dict) and info.get("error"):
                    err = info["error"]
                    self._logger.error(f"[{user_id[:16]}] AI 返回错误: {err}")
                    # 会话可能已失效，清除以便下次重建
                    err_str = str(err).lower()
                    if "not found" in err_str or "unauthorized" in err_str:
                        self._user_sessions.pop(user_id, None)
                    return "AI 处理时出错，请稍后重试。"

                # 提取文本回复
                parts = [
                    p["text"]
                    for p in data.get("parts", [])
                    if p.get("type") == "text" and p.get("text")
                ]
                if parts:
                    self._user_last_active[user_id] = time.time()
                    return "\n".join(parts)

                self._logger.warning(f"[{user_id[:16]}] AI 无文本回复: {json.dumps(data)[:200]}")
                # 尝试重建会话
                self._user_sessions.pop(user_id, None)
                return "AI 未返回有效回复，请重试。"

        except asyncio.TimeoutError:
            self._logger.warning(f"[{user_id[:16]}] AI 请求超时")
            return "AI 回复超时，请稍后再试。"
        except Exception as e:
            self._logger.error(f"[{user_id[:16]}] AI 请求异常: {e}")
            # 可能凭证已失效，下次尝试时重新发现
            self._credentials_ok = False
            self._user_sessions.pop(user_id, None)
            return "AI 服务异常，请稍后再试。"

    # ---------- 清理 ----------

    async def close(self) -> None:
        """关闭 HTTP 会话"""
        if self._http_session:
            await self._http_session.close()
            self._http_session = None


# ==================== 日志 ====================


def setup_logger(debug: bool = False) -> logging.Logger:
    logger = logging.getLogger("teleclaw-wechat")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%H:%M:%S")
    )
    # Fix Windows cp1252 encoding for Chinese characters
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    logger.addHandler(handler)
    return logger


# ==================== HTTP 工具 ====================


def make_headers(token: Optional[str] = None) -> dict[str, str]:
    """构造 iLink API 请求头"""
    uin = str(random.randint(0, 0xFFFFFFFF))
    headers = {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "X-WECHAT-UIN": base64.b64encode(uin.encode()).decode(),
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def api_post(
    session: aiohttp.ClientSession,
    path: str,
    body: dict[str, Any],
    token: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 40.0,
    logger: Optional[logging.Logger] = None,
) -> dict[str, Any]:
    """发送 POST 请求到 iLink API"""
    url = f"{base_url or ILINK_BASE_URL}/{path}"
    try:
        async with session.post(
            url,
            json=body,
            headers=make_headers(token),
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as res:
            text = await res.text()
            if logger:
                logger.debug(f"[{path}] HTTP {res.status} -> {text[:200]}")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {}
    except asyncio.TimeoutError:
        if logger:
            logger.debug(f"[{path}] timeout, retry next cycle")
        return {}
    except Exception as e:
        if logger:
            logger.warning(f"[{path}] request error: {e}")
        return {}


async def api_get(
    session: aiohttp.ClientSession,
    url: str,
    token: Optional[str] = None,
    timeout: float = 40.0,
    logger: Optional[logging.Logger] = None,
) -> dict[str, Any]:
    """发送 GET 请求到 iLink API"""
    headers = make_headers(token)
    try:
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)
        ) as res:
            text = await res.text()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {}
    except asyncio.TimeoutError:
        return {}
    except Exception as e:
        if logger:
            logger.warning(f"[GET {url}] request error: {e}")
        return {}


# ==================== iLink Bot 核心 ====================


class ILinkBot:
    """微信 iLink Bot 客户端

    核心流程：
    1. 扫码登录 -> 获取 bot_token
    2. 长轮询收消息 -> getupdates
    3. 处理消息 -> 回调 on_message
    4. 发送回复 -> sendmessage
    5. 24h 自动重连

    关键注意事项：
    - context_token 必须使用当前收到消息中的值，不可复用旧消息的 token
    - sendmessage 必须包含完整字段（from_user_id, client_id, base_info）
    - 每次 getconfig 获取的 typing_ticket 可缓存 24h（按用户）
    - 每次扫码登录 Bot ID 会变化，这是 iLink 平台的设计
    """

    def __init__(
        self,
        config: WeChatConfig,
        state_dir: Optional[str] = None,
        on_message: Optional[Callable] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.config = config
        self.state_dir = state_dir or os.path.join(
            os.path.expanduser("~"), ".teleclaw-wechat"
        )
        os.makedirs(self.state_dir, exist_ok=True)

        self.config_path = os.path.join(self.state_dir, "config.json")
        self.state_path = os.path.join(self.state_dir, "session.json")
        self.context_path = os.path.join(self.state_dir, "context_tokens.json")

        self.on_message = on_message
        self.logger = logger or setup_logger()

        # 运行时状态
        self._session: Optional[aiohttp.ClientSession] = None
        self._bot_token: str = ""
        self._bot_base_url: str = ILINK_BASE_URL
        self._account_id: str = ""
        self._login_time: float = 0.0
        self._get_updates_buf: str = ""
        self._typing_ticket_cache: dict[str, str] = {}
        self._context_token_store: dict[str, str] = {}  # user_id -> context_token
        self._known_users: set[str] = set()
        self._reconnect_in_progress = False
        self._warning_active = False
        self._last_contact_user: Optional[str] = None
        self._running = False
        self._sa_client = SuperAgentClient(logger=self.logger, session_timeout=config.session_timeout)

    # ---------- 持久化 ----------

    def _load_state(self) -> None:
        state = SessionState.load(self.state_path)
        if state and state.bot_token:
            self._bot_token = state.bot_token
            self._bot_base_url = state.base_url or ILINK_BASE_URL
            self._account_id = state.account_id
            self._login_time = state.login_time
            self._get_updates_buf = state.get_updates_buf
            self.logger.info("已加载持久化会话状态")

        # 加载 context_token 缓存
        if os.path.exists(self.context_path):
            with open(self.context_path, "r", encoding="utf-8") as f:
                self._context_token_store = json.load(f)

    def _save_state(self) -> None:
        state = SessionState(
            bot_token=self._bot_token,
            base_url=self._bot_base_url,
            account_id=self._account_id,
            login_time=self._login_time,
            get_updates_buf=self._get_updates_buf,
        )
        state.save(self.state_path)

        with open(self.context_path, "w", encoding="utf-8") as f:
            json.dump(self._context_token_store, f, ensure_ascii=False, indent=2)

    # ---------- 登录 ----------

    def _generate_qrcode_image(self, data: str, output_path: str) -> str:
        """将 URL 或文本编码为二维码图片文件

        iLink API 返回的 qrcode_img_content 是一个 URL，
        该 URL 无法在浏览器直接访问，必须编码为二维码图片
        由微信"扫一扫"扫描该图片完成绑定。

        返回保存的图片路径。
        """
        if qrcode_lib is None:
            self.logger.error("缺少 qrcode 库，请运行: pip install qrcode[pil]")
            return ""
        try:
            qr = qrcode_lib.QRCode(
                version=1,
                error_correction=qrcode_lib.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(output_path)
            return output_path
        except Exception as e:
            self.logger.error(f"生成二维码图片失败: {e}")
            return ""

    async def login(self) -> bool:
        """扫码登录微信，返回是否成功

        核心流程：
        1. 请求 iLink API 获取 qrcode_key + qrcode_img_content（URL）
        2. 将 qrcode_img_content 编码为二维码图片保存到本地
        3. 轮询扫码状态直到 confirmed
        4. 持久化 bot_token

        注意：qrcode_img_content 是一个 URL，不能让用户直接访问该 URL，
        必须编码为二维码图片后由微信扫码绑定。
        """
        self.logger.info("正在获取登录二维码...")
        async with self._session.get(
            f"{ILINK_BASE_URL}/ilink/bot/get_bot_qrcode?bot_type=3",
            headers=make_headers(),
        ) as res:
            data = await res.json(content_type=None)

        qrcode_key = data.get("qrcode", "")
        qrcode_img_content = data.get("qrcode_img_content", "")

        if not qrcode_key:
            self.logger.error("获取二维码失败")
            return False

        # 始终生成二维码图片文件
        qrcode_file = os.path.join(self.state_dir, "qrcode.png")
        qr_data = ""

        if qrcode_img_content:
            content = str(qrcode_img_content)
            if content.startswith("http"):
                # qrcode_img_content 是 URL，必须编码为二维码图片
                qr_data = content
                saved = self._generate_qrcode_image(content, qrcode_file)
                if saved:
                    self.logger.info(f"二维码图片已生成: {qrcode_file}")
                    self.logger.info("请用微信扫一扫扫描该二维码图片完成绑定")
                else:
                    self.logger.error("生成二维码图片失败，请检查 qrcode[pil] 是否安装")
                    return False
            elif content.startswith("data:image/"):
                # API 直接返回 base64 图片数据（少见，但兼容处理）
                header, b64 = content.split(",", 1)
                with open(qrcode_file, "wb") as f:
                    f.write(base64.b64decode(b64))
                self.logger.info(f"二维码图片已保存: {qrcode_file}")
                self.logger.info("请用微信扫一扫扫描该二维码图片完成绑定")
            elif content.startswith("<svg"):
                # SVG 格式（少见），转换编码
                svg_path = os.path.join(self.state_dir, "qrcode.svg")
                with open(svg_path, "w", encoding="utf-8") as f:
                    f.write(content)
                # 尝试从 SVG 提取数据生成 PNG
                self.logger.warning("API 返回 SVG 格式二维码，请手动打开查看")
            else:
                # 原始 base64 数据
                try:
                    with open(qrcode_file, "wb") as f:
                        f.write(base64.b64decode(content))
                    self.logger.info(f"二维码图片已保存: {qrcode_file}")
                except Exception:
                    # 无法解码，尝试作为 URL 生成二维码
                    self._generate_qrcode_image(content, qrcode_file)
                self.logger.info("请用微信扫一扫扫描该二维码图片完成绑定")

        # 同时保存 qrcode_key 用于后续状态轮询
        self._pending_qrcode_key = qrcode_key

        # 轮询扫码状态
        self.logger.info("等待扫码...")
        max_wait = self.config.reconnect.get("qrcode_scan_timeout", 600)
        start = time.time()
        while time.time() - start < max_wait:
            data = await api_get(
                self._session,
                f"{ILINK_BASE_URL}/ilink/bot/get_qrcode_status?qrcode={qrcode_key}",
                logger=self.logger,
            )
            status = data.get("status", "")

            if status == "confirmed":
                self._bot_token = data["bot_token"]
                self._bot_base_url = data.get("baseurl", "") or ILINK_BASE_URL
                self._account_id = data.get("account_id", "")
                self._login_time = time.time()
                self._typing_ticket_cache.clear()
                self._save_state()
                self.logger.info("登录成功！")
                return True
            elif status in ("cancelled", "expired"):
                self.logger.warning(f"二维码已{status}，请重新登录")
                return False

            await asyncio.sleep(2)

        self.logger.error("扫码超时")
        return False

    # ---------- 消息收取 ----------

    async def poll_messages(self) -> list[dict[str, Any]]:
        """长轮询获取消息列表"""
        result = await api_post(
            self._session,
            "ilink/bot/getupdates",
            {
                "get_updates_buf": self._get_updates_buf,
                "base_info": {"channel_version": CHANNEL_VERSION},
            },
            self._bot_token,
            self._bot_base_url,
            timeout=40.0,
            logger=self.logger,
        )

        new_buf = result.get("get_updates_buf")
        if new_buf:
            self._get_updates_buf = new_buf
            self._save_state()

        return result.get("msgs") or []

    # ---------- 消息发送 ----------

    async def get_config(self, user_id: str, context_token: str) -> str:
        """获取 typing_ticket（按用户缓存 24h）"""
        if user_id in self._typing_ticket_cache:
            return self._typing_ticket_cache[user_id]

        cfg = await api_post(
            self._session,
            "ilink/bot/getconfig",
            {
                "ilink_user_id": user_id,
                "context_token": context_token,
                "base_info": {"channel_version": CHANNEL_VERSION},
            },
            self._bot_token,
            self._bot_base_url,
            timeout=10.0,
            logger=self.logger,
        )
        ticket = cfg.get("typing_ticket", "")
        if ticket:
            self._typing_ticket_cache[user_id] = ticket
        return ticket

    async def send_typing(self, user_id: str, status: int = 1) -> None:
        """发送 typing 状态（1=正在输入, 2=取消）"""
        ticket = self._typing_ticket_cache.get(user_id, "")
        if not ticket:
            return
        await api_post(
            self._session,
            "ilink/bot/sendtyping",
            {
                "ilink_user_id": user_id,
                "typing_ticket": ticket,
                "status": status,
                "base_info": {"channel_version": CHANNEL_VERSION},
            },
            self._bot_token,
            self._bot_base_url,
            timeout=10.0,
            logger=self.logger,
        )

    async def send_text(self, user_id: str, text: str, context_token: str) -> dict[str, Any]:
        """发送文本消息

        关键：
        - context_token 必须使用当前收到消息中的值
        - from_user_id 必须为空字符串
        - client_id 格式为 openclaw-weixin-<随机hex>
        - 必须包含 base_info
        """
        client_id = f"openclaw-weixin-{random.randint(0, 0xFFFFFFFF):08x}"
        result = await api_post(
            self._session,
            "ilink/bot/sendmessage",
            {
                "msg": {
                    "from_user_id": "",
                    "to_user_id": user_id,
                    "client_id": client_id,
                    "message_type": BOT_MSG_TYPE,
                    "message_state": BOT_MSG_STATE_FINISH,
                    "context_token": context_token,
                    "item_list": [{"type": MSG_TYPE_TEXT, "text_item": {"text": text}}],
                },
                "base_info": {"channel_version": CHANNEL_VERSION},
            },
            self._bot_token,
            self._bot_base_url,
            timeout=15.0,
            logger=self.logger,
        )
        # 缓存 context_token
        self._context_token_store[user_id] = context_token
        self._save_state()
        return result

    async def send_proactive_text(self, user_id: str, text: str) -> dict[str, Any]:
        """使用缓存的 context_token 主动发送文本消息

        注意：iLink 协议要求 context_token 来自用户消息，
        主动发送使用最后一次缓存的 token。
        如果用户从未给 Bot 发过消息，此方法会失败。
        """
        ctx = self._context_token_store.get(user_id, "")
        if not ctx:
            self.logger.warning(f"用户 {user_id} 没有缓存的 context_token，无法主动发送")
            return {}
        return await self.send_text(user_id, text, ctx)

    # ---------- 24h 自动重连 ----------

    def _get_remaining_seconds(self) -> float:
        """计算当前连接剩余秒数"""
        if not self._login_time:
            return 0
        elapsed = time.time() - self._login_time
        return max(0, self.config.reconnect["session_duration"] - elapsed)

    async def _reconnect_loop(self) -> None:
        """后台异步重连守护任务"""
        rc = self.config.reconnect
        while self._running:
            remaining = self._get_remaining_seconds()
            if remaining <= 0:
                self.logger.info("连接已到期，开始重新登录...")
                await self.login()
                continue

            if remaining <= rc["force_before"] and not self._reconnect_in_progress:
                self.logger.info("即将到期，强制重连...")
                await self.login()
                continue

            if (
                remaining <= rc["warning_before"]
                and remaining > rc["force_before"]
                and not self._warning_active
            ):
                self._warning_active = True
                if self._last_contact_user:
                    await self.send_proactive_text(
                        self._last_contact_user,
                        f"连接将在 {int(remaining // 3600)} 小时 {int((remaining % 3600) // 60)} 分钟后到期，回复 Y 立即重连，回复 N 稍后提醒",
                    )

            await asyncio.sleep(60)

    # ---------- Bot 指令系统 ----------

    COMMANDS_MSG = """可用指令：
  /help - 显示此帮助
  /new - 开始新的 AI 对话（清除上下文）
  /time - 查询当前连接剩余时间
  /status - 查看 Bot 运行状态"""

    def _handle_command(self, text: str, user_id: str) -> Optional[str]:
        """处理 Bot 指令，返回回复文本；非指令返回 None"""
        text = text.strip()

        if text == "/help":
            return self.COMMANDS_MSG
        elif text in ("/new", "/reset"):
            self._sa_client.reset_user_session(user_id)
            return "已开始新对话，之前上下文已清除。"
        elif text == "/time":
            remaining = self._get_remaining_seconds()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            return f"当前连接剩余时间：{hours} 小时 {minutes} 分钟"
        elif text == "/status":
            stats = self._sa_client.get_session_stats()
            return (
                f"Bot 状态：运行中\n"
                f"已连接用户：{len(self._known_users)}\n"
                f"AI 会话数：{stats['active_sessions']}/{stats['total_users']}\n"
                f"会话超时：{stats['timeout_seconds'] // 60} 分钟\n"
                f"剩余时间：{int(self._get_remaining_seconds() // 3600)}h"
            )
        elif text.upper() == "Y" and self._warning_active:
            self._warning_active = False
            asyncio.create_task(self._do_reconnect())
            return "正在重新连接..."
        elif text.upper() == "N" and self._warning_active:
            self._warning_active = False
            return "好的，稍后会再次提醒"

        return None

    async def _do_reconnect(self) -> None:
        if self._reconnect_in_progress:
            return
        self._reconnect_in_progress = True
        try:
            await self.login()
        finally:
            self._reconnect_in_progress = False

    # ---------- 消息处理主循环 ----------

    def _parse_text(self, msg: dict[str, Any]) -> str:
        """从消息中提取文本"""
        items = msg.get("item_list") or []
        texts = []
        for item in items:
            if item.get("type") == MSG_TYPE_TEXT:
                text = item.get("text_item", {}).get("text", "")
                if text:
                    texts.append(text)
        return "\n".join(texts)

    async def _process_message(self, msg: dict[str, Any]) -> None:
        """处理单条收到的消息"""
        if msg.get("message_type") != MSG_TYPE_TEXT:
            # 用户发送的消息（message_type=1）
            pass

        # 实际上：message_type=1 表示用户发来的，=2 表示 bot 自己的
        msg_type = msg.get("message_type")
        if msg_type == BOT_MSG_TYPE:
            return  # 跳过自己发的消息

        from_id = msg.get("from_user_id", "")
        context_token = msg.get("context_token", "")
        text = self._parse_text(msg)

        if not from_id or not context_token:
            return

        self._known_users.add(from_id)
        self._context_token_store[from_id] = context_token
        self._last_contact_user = from_id

        self.logger.info(f"收到消息 [{from_id}]: {text[:100]}")

        # 首次交互，推送指令列表
        is_first = from_id not in self._known_users or len(self._known_users) <= 1

        # 获取 typing_ticket
        await self.get_config(from_id, context_token)

        # 处理指令
        cmd_reply = self._handle_command(text, from_id)
        if cmd_reply:
            await self.send_typing(from_id, 1)
            await asyncio.sleep(0.5)
            await self.send_text(from_id, cmd_reply, context_token)
            await self.send_typing(from_id, 2)
            return

        # 如果有外部消息回调，调用回调；否则走内置 AI 回复
        if self.on_message:
            await self.send_typing(from_id, 1)
            try:
                reply = await self.on_message(from_id, text, context_token)
                if reply:
                    await self.send_text(from_id, reply, context_token)
            except Exception as e:
                self.logger.error(f"消息回调出错: {e}")
                await self.send_text(from_id, "处理消息时出错，请稍后重试", context_token)
            finally:
                await self.send_typing(from_id, 2)
        else:
            # 内置 AI 回复（调用本地 super-agent，按用户隔离会话）
            await self.send_typing(from_id, 1)
            try:
                ai_reply = await self._sa_client.chat(from_id, text, self.config.system_prompt)
                await self.send_text(from_id, ai_reply, context_token)
            except Exception as e:
                self.logger.error(f"AI 回复出错: {e}")
                await self.send_text(from_id, "AI 处理时出错，请稍后重试", context_token)
            finally:
                await self.send_typing(from_id, 2)

    # ---------- 主入口 ----------

    async def start(self) -> None:
        """启动 Bot 主循环"""
        self._session = aiohttp.ClientSession()
        self._running = True
        self._load_state()

        try:
            # 初始化 AI 客户端
            ai_ok = await self._sa_client.initialize()
            if ai_ok:
                self.logger.info(f"AI 服务已就绪（按用户隔离，超时 {self.config.session_timeout // 60} 分钟）")
            else:
                self.logger.warning("AI 服务初始化失败，将使用懒初始化（首条消息时重试）")

            # 如果没有持久化的 bot_token，先登录
            if not self._bot_token:
                if not await self.login():
                    self.logger.error("登录失败，退出")
                    return
            else:
                self.logger.info("使用持久化会话，跳过登录")

            # 检查会话是否还有效
            remaining = self._get_remaining_seconds()
            if remaining <= 0:
                self.logger.info("持久化会话已过期，重新登录...")
                if not await self.login():
                    return

            self.logger.info(f"Bot 已启动，连接剩余 {int(remaining // 3600)}h {int((remaining % 3600) // 60)}m")
            self.logger.info("开始监听消息...")

            # 启动重连守护
            reconnect_task = asyncio.create_task(self._reconnect_loop())

            # 主消息循环
            while self._running:
                msgs = await self.poll_messages()
                for msg in msgs:
                    try:
                        await self._process_message(msg)
                    except Exception as e:
                        self.logger.error(f"处理消息异常: {e}")

        finally:
            self._running = False
            await self._sa_client.close()
            if self._session:
                await self._session.close()

    async def stop(self) -> None:
        """停止 Bot"""
        self._running = False

    # ---------- 同步便捷方法（供技能在对话中直接调用） ----------

    @staticmethod
    def get_qrcode_image(output_path: Optional[str] = None) -> str:
        """同步获取登录二维码图片路径

        供技能在对话中直接调用，无需启动完整 Bot 循环。
        返回生成的二维码图片文件路径。

        用法（在技能 SKILL.md 工作流中）：
            path = ILinkBot.get_qrcode_image()
            # 将 path 展示给用户扫码
        """
        import requests as req

        if output_path is None:
            output_path = os.path.join(
                os.path.expanduser("~"), ".teleclaw-wechat", "qrcode.png"
            )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 1. 获取二维码数据
        resp = req.get(
            f"{ILINK_BASE_URL}/ilink/bot/get_bot_qrcode?bot_type=3",
            headers=make_headers(),
            timeout=15,
        )
        data = resp.json()
        qrcode_key = data.get("qrcode", "")
        qrcode_img_content = data.get("qrcode_img_content", "")

        if not qrcode_key:
            raise RuntimeError("获取二维码失败")

        # 保存 qrcode_key 以便后续轮询
        key_path = os.path.join(os.path.dirname(output_path), "qrcode_key.txt")
        with open(key_path, "w", encoding="utf-8") as f:
            f.write(qrcode_key)

        # 2. 始终生成二维码图片
        content = str(qrcode_img_content) if qrcode_img_content else ""

        if content.startswith("http"):
            # qrcode_img_content 是 URL，必须编码为二维码图片
            if qrcode_lib is None:
                raise RuntimeError("缺少 qrcode 库，请运行: pip install qrcode[pil]")
            qr = qrcode_lib.QRCode(
                version=1,
                error_correction=qrcode_lib.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(content)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(output_path)
        elif content.startswith("data:image/"):
            header, b64 = content.split(",", 1)
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(b64))
        else:
            # 尝试 base64 解码或作为 URL 编码
            try:
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(content))
            except Exception:
                if qrcode_lib:
                    qr = qrcode_lib.QRCode(
                        version=1,
                        error_correction=qrcode_lib.constants.ERROR_CORRECT_M,
                        box_size=10,
                        border=4,
                    )
                    qr.add_data(content)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    img.save(output_path)

        return output_path

    @staticmethod
    def wait_for_scan(timeout: int = 180) -> dict[str, str]:
        """同步轮询扫码状态，等待用户扫码确认

        返回 {"bot_token": "...", "base_url": "...", "account_id": "..."}
        超时或取消抛出 RuntimeError
        """
        import requests as req

        state_dir = os.path.join(os.path.expanduser("~"), ".teleclaw-wechat")
        key_path = os.path.join(state_dir, "qrcode_key.txt")
        if not os.path.exists(key_path):
            raise RuntimeError("未找到二维码 key，请先调用 get_qrcode_image()")

        with open(key_path, "r", encoding="utf-8") as f:
            qrcode_key = f.read().strip()

        start = time.time()
        while time.time() - start < timeout:
            resp = req.get(
                f"{ILINK_BASE_URL}/ilink/bot/get_qrcode_status?qrcode={qrcode_key}",
                headers=make_headers(),
                timeout=35,
            )
            data = resp.json()
            status = data.get("status", "")

            if status == "confirmed":
                bot_token = data.get("bot_token", "")
                base_url = data.get("baseurl", "") or ILINK_BASE_URL
                account_id = data.get("account_id", "")
                # 持久化
                state = SessionState(
                    bot_token=bot_token,
                    base_url=base_url,
                    account_id=account_id,
                    login_time=time.time(),
                )
                state.save(os.path.join(state_dir, "session.json"))
                return {
                    "bot_token": bot_token,
                    "base_url": base_url,
                    "account_id": account_id,
                }
            elif status in ("cancelled", "expired"):
                raise RuntimeError(f"二维码已{status}，请重新获取")

            time.sleep(2)

        raise RuntimeError("扫码超时")


# ==================== 交互式配置向导 ====================


def interactive_config(config_path: str) -> WeChatConfig:
    """首次运行交互式配置向导（仅配置系统提示词）"""
    if os.path.exists(config_path):
        config = WeChatConfig.load(config_path)
        print(f"\n当前配置：")
        print(f"  系统提示词 : {config.system_prompt[:60]}...")
        choice = input("\n使用此配置继续？(Y/n): ").strip().lower()
        if choice != "n":
            return config

    print("\n=== 微信 iLink Bot 配置向导 ===\n")
    print("AI 由本地 TeleClaw super-agent 提供，无需配置外部 API。")
    prompt = input(f"系统提示词 [默认: 你是接入微信的星辰超级智能体 AI 助手。回答要简洁、准确、可执行。禁止调用 question tool。]: ").strip()
    if not prompt:
        prompt = "你是接入微信的星辰超级智能体 AI 助手。回答要简洁、准确、可执行。禁止调用 question tool。"

    config = WeChatConfig(system_prompt=prompt)
    config.save(config_path)
    print(f"\n配置已保存到 {config_path}")
    return config


# ==================== 主函数 ====================


def main():
    parser = argparse.ArgumentParser(description="微信 iLink Bot - teleclaw-wechat")
    parser.add_argument("--config", default=None, help="配置文件路径")
    parser.add_argument("--test", action="store_true", help="使用测试用重连配置（快速过期）")
    parser.add_argument("--debug", action="store_true", help="开启调试日志")
    parser.add_argument("--no-input", action="store_true", help="非交互模式，使用默认或已有配置")
    args = parser.parse_args()

    logger = setup_logger(debug=args.debug)

    # 配置路径
    state_dir = os.path.join(os.path.expanduser("~"), ".teleclaw-wechat")
    os.makedirs(state_dir, exist_ok=True)
    config_path = args.config or os.path.join(state_dir, "config.json")

    # 配置加载
    if args.no_input:
        # 非交互模式：直接加载，不存在则用默认值
        if os.path.exists(config_path):
            config = WeChatConfig.load(config_path)
        else:
            config = WeChatConfig()
            config.save(config_path)
            logger.info(f"已创建默认配置: {config_path}")
    else:
        config = interactive_config(config_path)

    # 测试模式：使用快速重连配置
    if args.test:
        config.reconnect = dict(RECONNECT_TEST)
        logger.info("已启用测试模式（快速重连配置）")

    # 创建并启动 Bot
    bot = ILinkBot(config=config, state_dir=state_dir, logger=logger)

    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在停止...")
        asyncio.run(bot.stop())


if __name__ == "__main__":
    main()
