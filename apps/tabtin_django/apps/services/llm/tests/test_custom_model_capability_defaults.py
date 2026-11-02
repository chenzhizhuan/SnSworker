from django.test import SimpleTestCase

from apps.services.llm.utils.custom_model_capabilities import (
    ensure_custom_chat_document_capability,
    ensure_custom_chat_json_capability,
    ensure_known_provider_chat_capabilities,
    ensure_wire_capability_switch_sync,
    resolve_known_provider_chat_max_output_tokens,
)


class CustomModelCapabilityDefaultsTests(SimpleTestCase):
    def test_registers_json_object_and_preserves_unrelated_metadata(self):
        original = {
            "supports_streaming": True,
            "json_mode": {"modes": ["vendor_json"], "keep": True},
        }

        result = ensure_custom_chat_json_capability(original)

        self.assertTrue(result["supports_json_mode"])
        self.assertEqual(
            result["json_mode"]["modes"],
            ["vendor_json", "json_object"],
        )
        self.assertTrue(result["json_mode"]["keep"])
        self.assertNotIn("supports_json_mode", original)

    def test_replaces_legacy_false_with_the_product_default(self):
        result = ensure_custom_chat_json_capability({
            "supports_json_mode": False,
            "supports_streaming": True,
        })

        self.assertTrue(result["supports_json_mode"])
        self.assertEqual(result["json_mode"]["modes"], ["json_object"])

    def test_known_provider_profile_fills_only_missing_capabilities(self):
        original = {
            "tool": {"enabled": False},
        }

        result = ensure_known_provider_chat_capabilities(
            provider_name="openai",
            config=original,
        )

        self.assertNotIn("supports_function_calling", result)
        self.assertEqual(result["tool"], {"enabled": False})
        self.assertTrue(result["supports_streaming"])
        self.assertNotIn("supports_streaming", original)

    def test_unknown_provider_is_not_inferred(self):
        original = {"supports_streaming": True}

        result = ensure_known_provider_chat_capabilities(
            provider_name="private-gateway",
            config=original,
        )

        self.assertEqual(result, original)
        self.assertIsNone(
            resolve_known_provider_chat_max_output_tokens(
                provider_name="private-gateway",
                context_window_tokens=200_000,
                explicit_max_output_tokens=None,
            )
        )

    def test_known_provider_output_default_preserves_explicit_value(self):
        self.assertEqual(
            resolve_known_provider_chat_max_output_tokens(
                provider_name="openai",
                context_window_tokens=200_000,
                explicit_max_output_tokens=None,
            ),
            16_384,
        )
        self.assertEqual(
            resolve_known_provider_chat_max_output_tokens(
                provider_name="openai",
                context_window_tokens=200_000,
                explicit_max_output_tokens=8_192,
            ),
            8_192,
        )

    def test_document_capability_registered_by_default(self):
        """创建路径：自定义渠道 chat 模型默认开启文档附件（对齐 0062 迁移）。"""
        result = ensure_custom_chat_document_capability({"supports_streaming": True})

        document = result["wire_adapter"]["document"]
        self.assertTrue(result["supports_document_input"])
        self.assertTrue(document["enabled"])
        self.assertEqual(document["upload_mode"], "file_extract")
        self.assertEqual(document["inject_role"], "system")
        self.assertEqual(document["files_api"]["purpose"], "file-extract")

    def test_document_explicit_config_preserved(self):
        """已显式启用文档能力（含自定义参数）时保留原配置。"""
        original = {
            "supports_document_input": True,
            "wire_adapter": {
                "document": {
                    "enabled": True,
                    "upload_mode": "file_extract",
                    "max_size_mb": 250,
                }
            },
        }

        result = ensure_custom_chat_document_capability(original)

        self.assertEqual(
            result["wire_adapter"]["document"]["max_size_mb"], 250
        )
        self.assertNotIn("files_api", result["wire_adapter"]["document"])

    def test_switch_sync_fills_document_wire_when_top_level_true(self):
        """后台勾选只写顶层开关：supports_document_input=true → 补 wire 段。"""
        original = {
            "supports_document_input": True,
            "supports_vision": False,
        }

        result = ensure_wire_capability_switch_sync(original)

        self.assertTrue(result["wire_adapter"]["document"]["enabled"])

    def test_switch_sync_fills_image_wire_when_top_level_vision_true(self):
        """supports_vision=true 而 wire.image 缺失 → 补默认 image 段。"""
        original = {
            "supports_vision": True,
            "wire_adapter": {"wire": {"stream_supported": True}},
        }

        result = ensure_wire_capability_switch_sync(original)

        image = result["wire_adapter"]["image"]
        self.assertTrue(image["enabled"])
        self.assertEqual(image["formats"], ["jpeg", "png", "webp"])
        self.assertEqual(image["input_via"], ["base64"])
        # 原有 wire 段保留
        self.assertTrue(result["wire_adapter"]["wire"]["stream_supported"])

    def test_switch_sync_noop_when_switches_off(self):
        """顶层开关均为 false/缺失时不写任何 wire 段。"""
        original = {
            "supports_vision": False,
            "supports_streaming": True,
        }

        result = ensure_wire_capability_switch_sync(original)

        self.assertNotIn("wire_adapter", result)

    def test_switch_sync_overrides_explicitly_disabled_wire(self):
        """矛盾态（顶层 true + wire 显式 false）以顶层开关为准。"""
        original = {
            "supports_document_input": True,
            "wire_adapter": {"document": {"enabled": False}},
        }

        result = ensure_wire_capability_switch_sync(original)

        self.assertTrue(result["wire_adapter"]["document"]["enabled"])
