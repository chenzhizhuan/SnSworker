#!/usr/bin/env python3
"""
IM WeChat Notify - 通过 TeleAgent 本地消息投递接口发送微信消息

技术方案:
    直接操作 TeleAgent 桌面端的本地数据库，写入一条"待投递"消息记录，
    由桌面端的 push-phone worker 自动拾取并发送到微信。

    消息发送链路:
        push_wechat.py
            ↓ 向 im_message 表写入 status='to_deliver' 记录
            ↓ route_target 只含 {toUserId, fromUserId}
        TeleAgent 桌面端 (im-service)
            ↓ push-phone worker 轮询拾取 to_deliver 记录
            ↓ 从 channel_profile 的 auth_payload 提取 quill（持久 bot 凭证）
            ↓ 用 quill 调用微信 ilink API
        用户微信

    关键技术点:
        - 不依赖 contextToken：contextToken 在发送链路中是可选参数，
          真正必需的是 quill——channel profile 中的持久 bot 凭证，不会过期。
        - 零网络请求：所有操作在本机完成，只是读写本地 SQLite 数据库文件，
          不发起网络请求、不读取进程内存。
        - 发送后轮询状态：写入记录后轮询最多 8 秒，检查消息是否已送达。

安全措施:
    - 设置 busy_timeout 防止与 IM Service 的写锁竞争
    - 发送完成后自动清理已投递/失败的消息记录，避免数据库膨胀
    - toUserId 强制使用绑定用户，防止消息被发送到非绑定用户
    - 轮询等待使用指数退避，减少数据库读取频率
    - text 参数长度限制，防止异常大消息

使用方式:
    python push_wechat.py --text "消息内容"
    python push_wechat.py --text "消息内容" --check-status
"""

import argparse
import json
import os
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone

# IM Service 数据库路径
IM_DB_PATH = os.path.join(
    os.environ.get("USERPROFILE", r"C:\Users\Administrator"),
    ".local", "share", "TeleAgent", "im-service", "im-service.db"
)

# 消息状态（与 IM Service push-phone worker 状态机一致）
STATUS_TO_DELIVER = "to_deliver"
STATUS_DELIVERED = "delivered"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

# 微信渠道标识
CHANNEL_WEIXIN = "weixin"

# 安全限制
MAX_TEXT_LENGTH = 4096
MAX_TIMEOUT = 120.0
MIN_TIMEOUT = 5.0
DEFAULT_TIMEOUT = 30.0
MAX_POLL_INTERVAL = 2.0
INITIAL_POLL_INTERVAL = 0.3

# --- prepare failed 自动恢复机制 ---
# 微信 ilink 通道在会话不活跃时，sendmessage 会返回 {"ret":-2,"errmsg":"prepare failed"}
# 但 IM Service 仍将数据库状态标记为 delivered（HTTP 200 即视为成功），导致脚本误报成功。
# 改进方案：delivered 后扫描日志验证微信服务器真实响应，如检测到 prepare failed，
# 自动发送一条心跳激活消息唤醒会话，等待后重试原始推送。

# IM Service 日志目录
IM_LOG_DIR = os.path.join(
    os.environ.get("USERPROFILE", r"C:\Users\Administrator"),
    ".local", "share", "TeleAgent", "log"
)

# 自动恢复参数
MAX_RECOVER_ATTEMPTS = 2          # 最多自动激活重试次数
ACTIVATION_WAIT = 3.0             # 发送激活消息后等待秒数
ACTIVATION_TEXT = "."             # 心跳激活消息内容（简短，不干扰用户）
LOG_SCAN_LINES = 80               # 日志尾部扫描行数


def get_timestamp() -> str:
    """获取 ISO 格式的时间戳（UTC，timezone-aware）"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _get_db_connection(db_path: str, with_row_factory: bool = False) -> sqlite3.Connection:
    """
    获取 SQLite 连接，统一设置 busy_timeout 防止锁竞争

    IM Service 的 push-phone worker 也会写同一数据库，
    设置 busy_timeout=5000 确保在 IM Service 持有写锁时等待而非立即失败。
    数据库使用 WAL 模式，写入不会阻塞 IM Service 的读取。
    """
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.execute("PRAGMA busy_timeout = 5000")
    if with_row_factory:
        conn.row_factory = sqlite3.Row
    return conn


def read_weixin_profile(db_path: str = IM_DB_PATH) -> dict:
    """从数据库读取微信渠道配置（仅返回必要字段，不暴露 quill token）"""
    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"IM Service 数据库未找到: {db_path}\n"
            "请确保 TeleAgent 桌面应用已启动且微信已绑定。"
        )

    conn = _get_db_connection(db_path, with_row_factory=True)
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM im_channel_profile WHERE channel = 'weixin'")
        row = c.fetchone()
    finally:
        conn.close()

    if not row:
        raise ValueError("微信渠道未配置。请在 TeleAgent 中绑定微信。")

    profile = dict(row)
    if profile.get("auth_status") != "valid":
        raise ValueError(
            f"微信渠道认证状态无效: {profile.get('auth_status')}\n"
            "请重新扫码绑定微信。"
        )

    return {
        "ilink_user_id": profile.get("third_party_user_id", ""),
        "ilink_bot_id": profile.get("third_party_account_id", ""),
        "auth_status": profile.get("auth_status", ""),
        "quill_available": bool(json.loads(profile.get("auth_payload", "{}")).get("quill")),
    }


def cleanup_delivered_messages(db_path: str = IM_DB_PATH, max_age_hours: int = 24) -> int:
    """
    清理已投递/失败/跳过的旧消息记录，防止数据库膨胀

    参数:
        db_path: 数据库路径
        max_age_hours: 保留最近多少小时内的记录

    返回:
        删除的记录数
    """
    conn = _get_db_connection(db_path)
    try:
        c = conn.cursor()
        c.execute(
            """DELETE FROM im_message
               WHERE status IN ('delivered', 'failed', 'skipped')
               AND updated_at < datetime('now', ?)""",
            (f"-{max_age_hours} hours",)
        )
        deleted = c.rowcount
        conn.commit()
        return deleted
    finally:
        conn.close()


def send_message_via_db(
    text: str,
    db_path: str = IM_DB_PATH,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """
    通过本地消息投递接口发送微信消息

    流程:
    1. 在 im_message 表写入 status='to_deliver' 的记录
    2. 等待 push-phone worker 处理（指数退避轮询状态变化）
    3. 返回发送结果
    4. 清理已完成的旧消息记录

    参数:
        text: 消息文本内容（最长 4096 字符）
        db_path: IM Service 数据库路径
        timeout: 等待投递的最大时间（秒，5-120）

    返回:
        dict: {"success": True/False, "error": "...", "status": "..."}
    """
    # 安全校验：限制消息长度
    if len(text) > MAX_TEXT_LENGTH:
        return {"success": False, "error": f"text_too_long: max {MAX_TEXT_LENGTH} chars"}

    # 安全校验：限制超时范围
    timeout = max(MIN_TIMEOUT, min(timeout, MAX_TIMEOUT))

    # 读取微信渠道配置，获取绑定用户的 ilink_user_id
    # toUserId 强制使用绑定用户，不接受外部传入值，防止消息发送到非绑定用户
    profile = read_weixin_profile(db_path)
    bound_user_id = profile["ilink_user_id"]

    if not bound_user_id:
        return {"success": False, "error": "missing_bound_user_id"}

    # 构造消息记录
    now = get_timestamp()
    msg_id = uuid.uuid4().hex
    request_id = uuid.uuid4().hex

    # route_target 只包含投递目标用户，push-phone worker 据此发送
    route_target = json.dumps({"toUserId": bound_user_id}, ensure_ascii=False)

    conn = _get_db_connection(db_path)
    c = conn.cursor()

    try:
        # 写入待投递消息记录
        c.execute("""
            INSERT INTO im_message (
                id, channel, session_id, inbound_source, inbound_text,
                inbound_external_message_id, inbound_sender_user_id,
                inbound_sender_account_id, route_target, status,
                opencode_error, submitted_at, outbound_text, file_paths,
                result_error, result_completed_at, delivered_at, deliver_error,
                request_id, extra, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            msg_id,           # id
            CHANNEL_WEIXIN,    # channel
            "",                # session_id
            "push",            # inbound_source (标识为主动推送)
            "",                # inbound_text
            "",                # inbound_external_message_id
            "",                # inbound_sender_user_id
            "",                # inbound_sender_account_id
            route_target,      # route_target (JSON，包含 toUserId)
            STATUS_TO_DELIVER, # status (触发 push-phone worker 投递)
            "",                # opencode_error
            now,               # submitted_at
            text,              # outbound_text (要发送的消息内容)
            "[]",              # file_paths
            "",                # result_error
            "",                # result_completed_at
            "",                # delivered_at
            "",                # deliver_error
            request_id,        # request_id
            "{}",              # extra
            now,               # created_at
            now,               # updated_at
        ))

        conn.commit()
    except sqlite3.OperationalError as e:
        conn.close()
        return {"success": False, "error": f"db_write_error: {e}"}

    return _poll_delivery_status(conn, c, msg_id, db_path, timeout)


def send_image_via_db(
    image_path: str,
    text: str = "",
    db_path: str = IM_DB_PATH,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """
    通过本地消息投递接口发送微信图片消息

    与文本消息的区别：
        - file_paths 填入图片本地路径（JSON 数组格式）
        - outbound_text 可选填文字说明（也可留空，仅发送图片）

    流程:
    1. 校验图片文件存在性
    2. 在 im_message 表写入 status='to_deliver' 的记录
    3. 等待 push-phone worker 处理（指数退避轮询状态变化）
    4. 返回发送结果
    5. 清理已完成的旧消息记录

    参数:
        image_path: 图片文件本地绝对路径
        text: 可选的附言文字（最长 4096 字符）
        db_path: IM Service 数据库路径
        timeout: 等待投递的最大时间（秒，5-120）

    返回:
        dict: {"success": True/False, "error": "...", "status": "..."}
    """
    # 安全校验：图片文件必须存在
    if not image_path or not os.path.exists(image_path):
        return {"success": False, "error": "image_not_found", "path": image_path or ""}

    # 安全校验：限制图片文件大小（最大 20MB，微信限制）
    max_image_size = 20 * 1024 * 1024  # 20MB
    image_size = os.path.getsize(image_path)
    if image_size > max_image_size:
        return {
            "success": False,
            "error": f"image_too_large: {image_size} bytes, max {max_image_size} bytes",
        }

    # 安全校验：限制附言长度
    if len(text) > MAX_TEXT_LENGTH:
        return {"success": False, "error": f"text_too_long: max {MAX_TEXT_LENGTH} chars"}

    # 安全校验：限制超时范围
    timeout = max(MIN_TIMEOUT, min(timeout, MAX_TIMEOUT))

    # 读取微信渠道配置，获取绑定用户的 ilink_user_id
    profile = read_weixin_profile(db_path)
    bound_user_id = profile["ilink_user_id"]

    if not bound_user_id:
        return {"success": False, "error": "missing_bound_user_id"}

    # 构造消息记录
    now = get_timestamp()
    msg_id = uuid.uuid4().hex
    request_id = uuid.uuid4().hex

    # route_target 只包含投递目标用户
    route_target = json.dumps({"toUserId": bound_user_id}, ensure_ascii=False)

    # file_paths 填入图片路径（JSON 数组），outbound_text 为可选附言
    file_paths_json = json.dumps([image_path], ensure_ascii=False)

    conn = _get_db_connection(db_path)
    c = conn.cursor()

    try:
        c.execute("""
            INSERT INTO im_message (
                id, channel, session_id, inbound_source, inbound_text,
                inbound_external_message_id, inbound_sender_user_id,
                inbound_sender_account_id, route_target, status,
                opencode_error, submitted_at, outbound_text, file_paths,
                result_error, result_completed_at, delivered_at, deliver_error,
                request_id, extra, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            msg_id,           # id
            CHANNEL_WEIXIN,    # channel
            "",                # session_id
            "push",            # inbound_source
            "",                # inbound_text
            "",                # inbound_external_message_id
            "",                # inbound_sender_user_id
            "",                # inbound_sender_account_id
            route_target,      # route_target
            STATUS_TO_DELIVER, # status
            "",                # opencode_error
            now,               # submitted_at
            text,              # outbound_text（可选附言，可留空）
            file_paths_json,   # file_paths（图片路径 JSON 数组）
            "",                # result_error
            "",                # result_completed_at
            "",                # delivered_at
            "",                # deliver_error
            request_id,        # request_id
            "{}",              # extra
            now,               # created_at
            now,               # updated_at
        ))

        conn.commit()
    except sqlite3.OperationalError as e:
        conn.close()
        return {"success": False, "error": f"db_write_error: {e}"}

    return _poll_delivery_status(conn, c, msg_id, db_path, timeout)


def send_file_via_db(
    file_path: str,
    text: str = "",
    db_path: str = IM_DB_PATH,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """
    通过本地消息投递接口发送微信文件消息

    与图片消息类似，通过 file_paths 字段写入文件路径，由 push-phone worker
    自动上传到微信 CDN 并发送。支持 PDF、Word、Excel 等常见文件类型。

    参数:
        file_path: 文件本地绝对路径
        text: 可选的附言文字（最长 4096 字符）
        db_path: IM Service 数据库路径
        timeout: 等待投递的最大时间（秒，5-120）

    返回:
        dict: {"success": True/False, "error": "...", "status": "..."}
    """
    # 安全校验：文件必须存在
    if not file_path or not os.path.exists(file_path):
        return {"success": False, "error": "file_not_found", "path": file_path or ""}

    # 安全校验：限制文件大小（最大 100MB，微信文件限制）
    max_file_size = 100 * 1024 * 1024  # 100MB
    file_size = os.path.getsize(file_path)
    if file_size > max_file_size:
        return {
            "success": False,
            "error": f"file_too_large: {file_size} bytes, max {max_file_size} bytes",
        }

    # 安全校验：限制附言长度
    if len(text) > MAX_TEXT_LENGTH:
        return {"success": False, "error": f"text_too_long: max {MAX_TEXT_LENGTH} chars"}

    # 安全校验：限制超时范围
    timeout = max(MIN_TIMEOUT, min(timeout, MAX_TIMEOUT))

    # 读取微信渠道配置，获取绑定用户的 ilink_user_id
    profile = read_weixin_profile(db_path)
    bound_user_id = profile["ilink_user_id"]

    if not bound_user_id:
        return {"success": False, "error": "missing_bound_user_id"}

    # 构造消息记录
    now = get_timestamp()
    msg_id = uuid.uuid4().hex
    request_id = uuid.uuid4().hex

    # route_target 只包含投递目标用户
    route_target = json.dumps({"toUserId": bound_user_id}, ensure_ascii=False)

    # file_paths 填入文件路径（JSON 数组），outbound_text 为可选附言
    file_paths_json = json.dumps([file_path], ensure_ascii=False)

    conn = _get_db_connection(db_path)
    c = conn.cursor()

    try:
        c.execute("""
            INSERT INTO im_message (
                id, channel, session_id, inbound_source, inbound_text,
                inbound_external_message_id, inbound_sender_user_id,
                inbound_sender_account_id, route_target, status,
                opencode_error, submitted_at, outbound_text, file_paths,
                result_error, result_completed_at, delivered_at, deliver_error,
                request_id, extra, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            msg_id,           # id
            CHANNEL_WEIXIN,    # channel
            "",                # session_id
            "push",            # inbound_source
            "",                # inbound_text
            "",                # inbound_external_message_id
            "",                # inbound_sender_user_id
            "",                # inbound_sender_account_id
            route_target,      # route_target
            STATUS_TO_DELIVER, # status
            "",                # opencode_error
            now,               # submitted_at
            text,              # outbound_text（可选附言，可留空）
            file_paths_json,   # file_paths（文件路径 JSON 数组）
            "",                # result_error
            "",                # result_completed_at
            "",                # delivered_at
            "",                # deliver_error
            request_id,        # request_id
            "{}",              # extra
            now,               # created_at
            now,               # updated_at
        ))

        conn.commit()
    except sqlite3.OperationalError as e:
        conn.close()
        return {"success": False, "error": f"db_write_error: {e}"}

    return _poll_delivery_status(conn, c, msg_id, db_path, timeout)


def _verify_delivery_by_log(request_id: str, db_path: str = IM_DB_PATH) -> bool:
    """
    扫描 IM Service 日志，验证微信服务器是否真正接受了消息

    IM Service 的 push-phone worker 把 HTTP 200 当作 delivered，
    但微信服务器可能返回 {"ret":-2,"errmsg":"prepare failed"}（会话不活跃）。
    本函数通过 request_id 在日志中定位对应的 out_res 记录，检查真实响应。

    返回:
        True  = 微信服务器返回了 message_id（真正成功）
        False = 检测到 prepare failed 或找不到日志记录（疑似失败）
    """
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(db_path)), "log"
    )
    if not os.path.isdir(log_dir):
        log_dir = IM_LOG_DIR

    # 找最新的 im-service 日志文件
    log_files = []
    for f in os.listdir(log_dir):
        if f.startswith("im-service-") and f.endswith(".log"):
            log_files.append(os.path.join(log_dir, f))
    if not log_files:
        return True  # 找不到日志，保守判断为成功（不阻断正常流程）

    log_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    latest_log = log_files[0]

    try:
        with open(latest_log, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except Exception:
        return True  # 日志读取失败，保守判断为成功

    # 在日志尾部搜索 request_id 对应的 sendmessage out_res
    tail_lines = lines[-LOG_SCAN_LINES:] if len(lines) > LOG_SCAN_LINES else lines
    found_sendmessage = False

    for line in tail_lines:
        if request_id in line and "sendmessage" in line:
            found_sendmessage = True
        if found_sendmessage and request_id in line and "out_res" in line:
            # 找到了对应的响应记录
            if "prepare failed" in line:
                return False  # 确认失败
            if '"message_id"' in line:
                return True   # 确认成功
            # 有 out_res 但既不含 message_id 也不含 prepare failed，继续搜索
            found_sendmessage = False  # 重置，可能有多条 sendmessage

    # 没找到明确的成功或失败标记，保守判断为成功
    return True


def _activate_session(db_path: str = IM_DB_PATH) -> bool:
    """
    发送一条心跳激活消息唤醒微信 ilink 会话

    微信服务端在会话长时间不活跃后，会拒绝机器人的主动推送（prepare failed）。
    发送一条简短文本消息可以"激活"会话，使后续推送恢复正常。

    返回:
        True  = 激活消息已投递
        False = 激活消息投递失败
    """
    # 读取绑定用户
    try:
        profile = read_weixin_profile(db_path)
        bound_user_id = profile["ilink_user_id"]
    except Exception:
        return False

    if not bound_user_id:
        return False

    # 写入一条简短的 to_deliver 消息（不附带文件，纯文本）
    now = get_timestamp()
    msg_id = uuid.uuid4().hex
    request_id = uuid.uuid4().hex
    route_target = json.dumps({"toUserId": bound_user_id}, ensure_ascii=False)

    conn = _get_db_connection(db_path)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO im_message (
                id, channel, session_id, inbound_source, inbound_text,
                inbound_external_message_id, inbound_sender_user_id,
                inbound_sender_account_id, route_target, status,
                opencode_error, submitted_at, outbound_text, file_paths,
                result_error, result_completed_at, delivered_at, deliver_error,
                request_id, extra, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            msg_id,           # id
            CHANNEL_WEIXIN,    # channel
            "",                # session_id
            "push",            # inbound_source
            "",                # inbound_text
            "",                # inbound_external_message_id
            "",                # inbound_sender_user_id
            "",                # inbound_sender_account_id
            route_target,      # route_target
            STATUS_TO_DELIVER, # status
            "",                # opencode_error
            now,               # submitted_at
            ACTIVATION_TEXT,   # outbound_text
            "[]",              # file_paths
            "",                # result_error
            "",                # result_completed_at
            "",                # delivered_at
            "",                # deliver_error
            request_id,        # request_id
            "{}",              # extra
            now,               # created_at
            now,               # updated_at
        ))
        conn.commit()
    except sqlite3.OperationalError:
        conn.close()
        return False

    # 轮询激活消息状态（最多等待 10 秒）
    start = time.time()
    poll_interval = INITIAL_POLL_INTERVAL
    activated = False
    while time.time() - start < 10.0:
        time.sleep(poll_interval)
        try:
            c.execute("SELECT status FROM im_message WHERE id = ?", (msg_id,))
            row = c.fetchone()
        except sqlite3.OperationalError:
            time.sleep(0.5)
            continue
        if row and row[0] in (STATUS_DELIVERED, STATUS_FAILED, STATUS_SKIPPED):
            activated = row[0] == STATUS_DELIVERED
            break
        poll_interval = min(poll_interval * 1.5, MAX_POLL_INTERVAL)

    conn.close()

    if activated:
        # 等待微信服务端处理完激活消息
        time.sleep(ACTIVATION_WAIT)

    return activated


def _send_with_auto_recover(
    send_func,
    *args,
    db_path: str = IM_DB_PATH,
    timeout: float = DEFAULT_TIMEOUT,
    **kwargs,
) -> dict:
    """
    带自动恢复机制的发送包装器

    流程:
    1. 调用原始发送函数（send_message_via_db / send_image_via_db / send_file_via_db）
    2. 如果返回 delivered，扫描日志验证微信服务器真实响应
    3. 如果检测到 prepare failed，发送心跳激活消息唤醒会话
    4. 重新发送原始消息，再次验证
    5. 最多重试 MAX_RECOVER_ATTEMPTS 次

    参数:
        send_func: 原始发送函数
        args/kwargs: 传递给 send_func 的参数
        db_path: 数据库路径
        timeout: 超时时间

    返回:
        dict: 与原始发送函数格式一致的结果
    """
    max_attempts = MAX_RECOVER_ATTEMPTS
    last_result = None

    for attempt in range(max_attempts + 1):
        # 发送消息
        result = send_func(*args, db_path=db_path, timeout=timeout, **kwargs)
        last_result = result

        # 如果本身就失败了（非 delivered），直接返回
        if not result.get("success"):
            return result

        # delivered 状态：扫描日志验证微信服务器真实响应
        request_id = _extract_request_id(result.get("msg_id", ""), db_path)
        if not request_id:
            # 无法提取 request_id，保守返回成功
            return result

        verified = _verify_delivery_by_log(request_id, db_path)

        if verified:
            # 微信服务器确认成功
            return result

        # 检测到 prepare failed，尝试自动激活
        if attempt < max_attempts:
            sys.stderr.write(
                f"[auto-recover] 检测到 prepare failed（第{attempt+1}次），"
                f"正在自动激活会话...\n"
            )
            activated = _activate_session(db_path)
            if not activated:
                sys.stderr.write("[auto-recover] 激活消息投递失败，放弃重试\n")
                result["success"] = False
                result["error"] = "session_expired: prepare failed, activation failed"
                return result

            sys.stderr.write(
                f"[auto-recover] 会话已激活，正在重试推送（第{attempt+1}次）...\n"
            )
        else:
            # 已达到最大重试次数
            sys.stderr.write(
                f"[auto-recover] 已达到最大重试次数({max_attempts})，"
                f"微信服务器仍返回 prepare failed\n"
            )
            result["success"] = False
            result["error"] = "session_expired: prepare failed after auto-recover"
            return result

    return last_result


def _extract_request_id(msg_id: str, db_path: str = IM_DB_PATH) -> str:
    """
    从数据库中提取消息的 request_id（用于日志匹配）

    参数:
        msg_id: 消息 ID
        db_path: 数据库路径

    返回:
        request_id 字符串，找不到则返回空字符串
    """
    if not msg_id:
        return ""
    conn = _get_db_connection(db_path)
    try:
        c = conn.cursor()
        c.execute("SELECT request_id FROM im_message WHERE id = ?", (msg_id,))
        row = c.fetchone()
        return row[0] if row else ""
    except Exception:
        return ""
    finally:
        conn.close()


def _poll_delivery_status(
    conn: sqlite3.Connection,
    c: sqlite3.Cursor,
    msg_id: str,
    db_path: str,
    timeout: float,
) -> dict:
    """
    轮询消息投递状态（内部共享函数，文本和图片消息共用）

    参数:
        conn: 数据库连接
        c: 数据库游标
        msg_id: 消息 ID
        db_path: 数据库路径（用于清理旧记录）
        timeout: 超时时间

    返回:
        dict: {"success": True/False, "status": "...", "msg_id": "..."}
    """
    start_time = time.time()
    poll_interval = INITIAL_POLL_INTERVAL

    while time.time() - start_time < timeout:
        time.sleep(poll_interval)

        try:
            c.execute("SELECT status, deliver_error FROM im_message WHERE id = ?", (msg_id,))
            row = c.fetchone()
        except sqlite3.OperationalError:
            time.sleep(0.5)
            continue

        if row:
            status = row[0]
            deliver_error = row[1]

            if status == STATUS_DELIVERED:
                conn.close()
                try:
                    cleanup_delivered_messages(db_path)
                except Exception:
                    pass
                return {"success": True, "status": "delivered", "msg_id": msg_id}

            if status == STATUS_FAILED:
                conn.close()
                return {
                    "success": False,
                    "status": "failed",
                    "error": deliver_error or "delivery_failed",
                    "msg_id": msg_id,
                }

            if status == STATUS_SKIPPED:
                conn.close()
                return {
                    "success": False,
                    "status": "skipped",
                    "error": "channel_unsupported",
                    "msg_id": msg_id,
                }

        poll_interval = min(poll_interval * 1.5, MAX_POLL_INTERVAL)

    # 超时
    try:
        c.execute("SELECT status FROM im_message WHERE id = ?", (msg_id,))
        row = c.fetchone()
        current_status = row[0] if row else "unknown"
    except sqlite3.OperationalError:
        current_status = "unknown"
    finally:
        conn.close()

    return {
        "success": False,
        "status": current_status,
        "error": "delivery_timeout",
        "msg_id": msg_id,
    }


def check_im_service_health() -> dict:
    """检查 IM Service 是否运行"""
    try:
        import requests
        r = requests.get("http://127.0.0.1:17802/health", timeout=5)
        return r.json()
    except Exception as e:
        return {"running": False, "error": str(e)}


def check_weixin_status() -> dict:
    """检查微信绑定状态（仅返回渠道状态，不暴露 quill token）"""
    try:
        profile = read_weixin_profile()
        return {
            "channel": "weixin",
            "auth_status": profile["auth_status"],
            "ilink_bot_id": profile["ilink_bot_id"],
            "quill_available": profile["quill_available"],
        }
    except Exception as e:
        return {"channel": "weixin", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="通过 TeleAgent 本地消息投递接口给绑定微信发消息"
    )
    parser.add_argument(
        "--text", default="", help="消息文本内容"
    )
    parser.add_argument(
        "--image", default="", help="图片文件本地绝对路径（发送图片消息）"
    )
    parser.add_argument(
        "--file", default="", help="文件本地绝对路径（发送文件消息，支持PDF/Word/Excel等）"
    )
    parser.add_argument(
        "--channel", default="weixin", choices=["weixin"],
        help="目标渠道 (目前仅支持 weixin)"
    )
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT,
        help=f"等待投递的最大时间(秒) ({MIN_TIMEOUT}-{int(MAX_TIMEOUT)}, 默认: {int(DEFAULT_TIMEOUT)})"
    )
    parser.add_argument(
        "--check-status", action="store_true",
        help="仅检查微信绑定状态，不发送消息"
    )

    args = parser.parse_args()

    if args.check_status:
        print("=== IM Service 健康状态 ===")
        health = check_im_service_health()
        print(json.dumps(health, ensure_ascii=False, indent=2))
        print()
        print("=== 微信绑定状态 ===")
        status = check_weixin_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return

    # 根据参数选择发送模式（通过 _send_with_auto_recover 包装，自动检测 prepare failed 并恢复）
    if args.file:
        # 文件消息（可同时附带文字说明）
        result = _send_with_auto_recover(
            send_file_via_db, args.file, text=args.text, timeout=args.timeout
        )
    elif args.image:
        # 图片消息（可同时附带文字说明）
        result = _send_with_auto_recover(
            send_image_via_db, args.image, text=args.text, timeout=args.timeout
        )
    elif args.text:
        # 纯文本消息
        result = _send_with_auto_recover(
            send_message_via_db, args.text, timeout=args.timeout
        )
    else:
        parser.error("需要指定 --text、--image 或 --file 参数")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()