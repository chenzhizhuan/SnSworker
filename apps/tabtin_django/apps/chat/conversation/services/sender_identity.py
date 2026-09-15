"""共享会话消息「发送者」身份解析。

为 ``share_fork_turns.collect_share_turns`` 提供 user 消息发言人的归属解析。
语义与 ``apps.chat.conversation.api.message._attach_sender_display_names``
保持一致：

- ``resolve_sender_user_id``：解析某条 user 消息的发送者用户 ID；
- ``load_sender_users``：按 ID 批量加载用户对象（dict: str(id) -> user）；
- ``resolve_user_display_name``：把用户对象解析为展示名，查不到时退化为 ID 前 8 位。
"""

from typing import Dict, Iterable, Optional


def resolve_sender_user_id(msg, *, owner_user_id: str) -> str:
    """解析一条 user 消息的发送者用户 ID。

    约定（按优先级）：
    1. ``msg.sender_user_id`` 已持久化（共享会话中 grantee 发言会写入该字段）；
    2. ``msg.metadata`` 里的共享标记 ``_shared_chat_by`` / ``shared_chat_by``
       （兼容旧消息仅存在 metadata 标记、未回填字段的情况）；
    3. 兜底为 ``owner_user_id``（历史消息未回填时归属会话 owner）。

    ``msg`` 为空或无法判定时返回空串。
    """
    if msg is None:
        return ""
    owner = str(owner_user_id or "").strip()

    persisted = str(getattr(msg, "sender_user_id", "") or "").strip()
    if persisted:
        return persisted

    metadata = getattr(msg, "metadata", None)
    if isinstance(metadata, dict):
        shared_by = str(
            metadata.get("_shared_chat_by")
            or metadata.get("shared_chat_by")
            or ""
        ).strip()
        if shared_by:
            return shared_by

    return owner


def load_sender_users(sender_ids: Iterable[str]) -> dict[str, object]:
    """按发送者 ID 批量加载用户对象。

    返回 ``{str(user.id): user}``；未匹配到任何 ID 时返回空 dict。
    """
    from django.contrib.auth import get_user_model

    ids = {str(s).strip() for s in sender_ids if str(s).strip()}
    if not ids:
        return {}
    return {
        str(user.id): user
        for user in get_user_model().objects.filter(id__in=ids)
    }


def resolve_user_display_name(
    sender: Optional[object],
    sender_user_id: str,
) -> str:
    """把发送者对象解析为展示名。

    ``sender`` 命中用户对象时取其 ``get_display_name()``；否则退化为
    ``sender_user_id`` 前 8 位，保证续接卡界面总能展示一个可读标识。
    """
    if sender is not None and hasattr(sender, "get_display_name"):
        try:
            name = str(sender.get_display_name()).strip()
            if name:
                return name
        except Exception:
            pass
    return str(sender_user_id or "")[:8]