"""Custom chat model capability defaults shared by model CRUD boundaries."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .provider_profiles import list_provider_profiles


_MAIN_CHAT_DEFAULT_MAX_OUTPUT_TOKENS = 16_384
_STRUCTURED_CAPABILITY_PATHS = {
    "supports_streaming": ("wire", "stream_supported"),
    "supports_function_calling": ("tool", "enabled"),
    "supports_vision": ("image", "enabled"),
}

# 与 0062 迁移同构：自定义渠道 chat 模型的本地文档提取 wire 配置。
# docx/pdf/txt 走本地提取，files_api 仅作为本地不可解析格式的回退路径。
_DOCUMENT_LOCAL_EXTRACT_WIRE: dict[str, Any] = {
    "enabled": True,
    "upload_mode": "file_extract",
    "files_api": {
        "endpoint": "/files",
        "purpose": "file-extract",
        "url_scheme": "ms://",
        "id_field": "id",
        "timeout_s": 180.0,
    },
    "max_size_mb": 100,
    "max_extract_chars": 200000,
    "inject_role": "system",
    "cache_extracted_text": True,
}

# 顶层 supports_vision=true 但 wire_adapter.image 未启用时的默认段
# （与 admindash 表单产出的结构同构）。
_DEFAULT_IMAGE_WIRE: dict[str, Any] = {
    "enabled": True,
    "formats": ["jpeg", "png", "webp"],
    "input_via": ["base64"],
    "upload_mode": "inline_base64",
    "request_shape": "openai_image_url",
}


def _merge_wire_section(
    config: dict[str, Any],
    section: str,
    defaults: dict[str, Any],
) -> bool:
    """补齐 wire_adapter.<section> 结构段；已显式启用时保留原配置。

    Returns:
        是否发生了修改（用于调用方决定是否持久化）。
    """
    raw_wire = config.get("wire_adapter")
    wire = dict(raw_wire) if isinstance(raw_wire, dict) else {}
    existing = wire.get(section)

    if isinstance(existing, dict) and existing.get("enabled") is True:
        return False

    merged = deepcopy(defaults)
    if isinstance(existing, dict):
        merged.update(existing)
    merged["enabled"] = True
    wire[section] = merged
    config["wire_adapter"] = wire
    return True


def ensure_custom_chat_document_capability(config: Any) -> dict[str, Any]:
    """自定义渠道 chat 模型默认开启文档附件（本地提取路径）。

    与 0062 迁移口径一致：存量模型由迁移无条件开启，新建模型在此对齐，
    避免「存量全开、新建全关」的不一致。已显式启用的配置不覆盖。
    """
    normalized = deepcopy(config) if isinstance(config, dict) else {}
    if _merge_wire_section(normalized, "document", _DOCUMENT_LOCAL_EXTRACT_WIRE):
        normalized["supports_document_input"] = True
    return normalized


def ensure_wire_capability_switch_sync(config: Any) -> dict[str, Any]:
    """顶层 supports_* 开关与 wire_adapter 结构段对齐。

    wire gate（ResolvedCapabilities.from_json）只读 ``wire_adapter.*.enabled``；
    管理后台表单勾选只写顶层兼容字段（supports_vision / supports_document_input）。
    顶层声明 true 而 wire 段未启用（缺失，或历史数据显式 false）时补默认结构段，
    保证勾选真正生效——矛盾态以顶层开关（用户最新显式意图）为准。
    """
    normalized = deepcopy(config) if isinstance(config, dict) else {}
    if normalized.get("supports_vision"):
        _merge_wire_section(normalized, "image", _DEFAULT_IMAGE_WIRE)
    if normalized.get("supports_document_input"):
        _merge_wire_section(normalized, "document", _DOCUMENT_LOCAL_EXTRACT_WIRE)
    return normalized


def _known_provider_profile(provider_name: str) -> dict[str, Any] | None:
    provider_key = str(provider_name or "").strip().lower()
    if not provider_key:
        return None
    return next(
        (
            item
            for item in list_provider_profiles()
            if str(item.get("provider") or "").strip().lower() == provider_key
        ),
        None,
    )


def _has_explicit_capability(config: dict[str, Any], capability: str) -> bool:
    if capability in config:
        return True
    structured_path = _STRUCTURED_CAPABILITY_PATHS.get(capability)
    if structured_path is None:
        return False
    section = config.get(structured_path[0])
    return isinstance(section, dict) and structured_path[1] in section


def ensure_custom_chat_json_capability(config: Any) -> dict[str, Any]:
    """Register the JSON-object capability required by background AI scenes."""
    normalized = deepcopy(config) if isinstance(config, dict) else {}
    normalized["supports_json_mode"] = True
    json_mode = normalized.get("json_mode")
    json_mode_config = dict(json_mode) if isinstance(json_mode, dict) else {}
    existing_modes = json_mode_config.get("modes")
    modes = list(existing_modes) if isinstance(existing_modes, (list, tuple)) else []
    if "json_object" not in modes:
        modes.append("json_object")
    json_mode_config["modes"] = modes
    normalized["json_mode"] = json_mode_config
    return normalized


def ensure_known_provider_chat_capabilities(
    *,
    provider_name: str,
    config: Any,
) -> dict[str, Any]:
    """Fill missing chat capabilities from an explicitly selected profile.

    Unknown provider names stay untouched.  Existing user declarations win over
    profile defaults; structured capability sections remain authoritative in the
    shared resolver.
    """
    normalized = deepcopy(config) if isinstance(config, dict) else {}
    profile = _known_provider_profile(provider_name)
    if profile is None:
        return normalized

    capabilities = profile.get("capabilities")
    if not isinstance(capabilities, dict):
        return normalized
    for capability, default_value in capabilities.items():
        if not _has_explicit_capability(normalized, capability):
            normalized[capability] = deepcopy(default_value)
    return normalized


def resolve_known_provider_chat_max_output_tokens(
    *,
    provider_name: str,
    context_window_tokens: int,
    explicit_max_output_tokens: int | None,
) -> int | None:
    """Bridge the existing model form's context-only limit for known profiles."""
    if explicit_max_output_tokens is not None:
        return explicit_max_output_tokens
    if _known_provider_profile(provider_name) is None:
        return None
    return min(context_window_tokens, _MAIN_CHAT_DEFAULT_MAX_OUTPUT_TOKENS)
