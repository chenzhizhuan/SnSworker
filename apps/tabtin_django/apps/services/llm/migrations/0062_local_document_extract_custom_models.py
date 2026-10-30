"""自定义渠道 / BYOK chat 模型开启文档附件（本地文本提取路径）。

背景：
- ``wire_adapter`` 文档门控此前仅对 Moonshot/Kimi 预置（0048），
  自建 vLLM 等 OpenAI 兼容渠道发文档附件会被
  ``capability_gate document unsupported_via`` 拒绝。
- ``docx/xlsx/pptx/txt`` 已支持服务端本地零依赖提取
  （``provider_media_upload.office_text_extractor``），提取文本注入
  system 消息，不再依赖上游 Files API——文档能力因此与上游模型能力
  解耦，任何 chat 端点都能消费。

范围（与 0061 的自定义模型口径一致）：
- 仅覆盖「非内置 provider 渠道」或「user/organization BYOK」的 chat 模型；
  官方目录模型（moonshot/openai/qwen/... 的 provider 预置 migrations）
  的文档能力不受影响。
- 已显式配置 ``wire_adapter.document`` 的模型保留原配置不覆盖。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from django.db import migrations
from django.db.models import Q

# providers/ 目录下注册的内置 provider_key（register.py 的 name）。
# 自建网关 / 中转渠道的 provider_key 不在此集合内。
BUILTIN_PROVIDER_KEYS = frozenset(
    {
        "bytedance",
        "claude",
        "dashscope",
        "deepseek",
        "fal",
        "gemini",
        "kimi_coding",
        "minimax",
        "minimax_bgm",
        "moonshot",
        "openai",
        "codex",
        "zenmux",
        "qwen",
        "replicate",
        "volcengine",
        "zhipu",
        "zhipu_coding_plan",
    }
)

# 与 0048 Kimi 同构；docx/pdf/txt 走本地提取，files_api 仅作为
# 本地不可解析格式（如 .doc/.xls 二进制格式）的回退路径。
DOCUMENT_LOCAL_EXTRACT_WIRE = {
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


def merge_local_document_extract(config: Any) -> dict[str, Any]:
    merged = deepcopy(config) if isinstance(config, dict) else {}
    wire = merged.get("wire_adapter")
    wire_config = dict(wire) if isinstance(wire, dict) else {}
    document = wire_config.get("document")

    if isinstance(document, dict) and document.get("enabled") is True:
        # 已显式启用文档能力（如 admin 高级 JSON 手工配置）：保留原配置
        merged["supports_document_input"] = True
        merged["wire_adapter"] = wire_config
        return merged

    wire_config["document"] = dict(DOCUMENT_LOCAL_EXTRACT_WIRE)
    merged["wire_adapter"] = wire_config
    merged["supports_document_input"] = True
    return merged


def enable_local_document_extract(apps, schema_editor):
    llm_model = apps.get_model("llm", "LLMModel")
    queryset = llm_model.objects.filter(capability_domain="chat").filter(
        Q(provider__scope__in=["user", "organization"])
        | ~Q(provider__provider_key__in=BUILTIN_PROVIDER_KEYS)
    )
    for model in queryset.iterator(chunk_size=500):
        before = model.capabilities_config or {}
        after = merge_local_document_extract(before)
        if before == after:
            continue
        model.capabilities_config = after
        model.save(update_fields=["capabilities_config", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("llm", "0061_custom_chat_json_mode_capability"),
    ]

    operations = [
        migrations.RunPython(
            enable_local_document_extract,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
