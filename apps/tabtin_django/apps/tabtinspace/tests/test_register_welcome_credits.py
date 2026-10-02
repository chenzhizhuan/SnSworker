"""注册欢迎点券赠送回归测试（TABTIN_REGISTER_WELCOME_CREDITS，默认 1000）。

被测单元：OrganizationService._grant_register_welcome_credits —— 赠送金额读
settings、失败不阻断注册。编排层（ensure_personal_organization 首建分支调用
本方法、幂等不重发）由生产容器端到端验证：在真实注册链路创建用户后核对
钱包余额 1000 与 grant 流水（见部署验证脚本）。

纯单元级（SimpleTestCase，不建库）：本仓库 isolated settings
（tabtin.settings_share_test）的最小 app 集当前无法承载 wallet 域
（billing 模型 FK wallet.OrganizationWallet → wallet FK conversation 域，
补链会持续扩大 isolated 集合），故 wallet service 以 patch 真实路径的方式
替代，断言注册链路以正确参数调用了赠送。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from apps.tabtinspace.services.organization_service import OrganizationService

_GRANT_PATH = (
    "apps.users.wallet.services.organization_wallet_service."
    "OrganizationWalletService.grant_credits"
)


class RegisterWelcomeCreditsUnitTests(SimpleTestCase):
    """_grant_register_welcome_credits 行为单元。"""

    def setUp(self) -> None:
        super().setUp()
        self._grant = patch(_GRANT_PATH)
        self.mock_grant = self._grant.start()
        self.addCleanup(self._grant.stop)

    def test_grants_default_1000_with_expected_args(self) -> None:
        OrganizationService._grant_register_welcome_credits(
            "org-123", user_id="user-9",
        )

        self.mock_grant.assert_called_once()
        args, kwargs = self.mock_grant.call_args
        self.assertEqual(args[0], "org-123")
        self.assertEqual(args[1], 1000)
        self.assertEqual(kwargs.get("description"), "注册欢迎赠送")
        self.assertEqual(kwargs.get("user_id"), "user-9")

    def test_explicit_config_amount_is_passed_through(self) -> None:
        with override_settings(TABTIN_REGISTER_WELCOME_CREDITS=2500):
            OrganizationService._grant_register_welcome_credits("org-456")

        args, _kwargs = self.mock_grant.call_args
        self.assertEqual(args[1], 2500)

    @override_settings(TABTIN_REGISTER_WELCOME_CREDITS=0)
    def test_zero_config_disables_grant(self) -> None:
        OrganizationService._grant_register_welcome_credits("org-789")

        self.mock_grant.assert_not_called()

    @override_settings(TABTIN_REGISTER_WELCOME_CREDITS="not-a-number")
    def test_invalid_config_skips_grant_safely(self) -> None:
        OrganizationService._grant_register_welcome_credits("org-abc")

        self.mock_grant.assert_not_called()

    def test_grant_failure_does_not_raise(self) -> None:
        self.mock_grant.side_effect = RuntimeError("wallet down")

        # 赠送失败仅记日志，不得阻断注册链路
        OrganizationService._grant_register_welcome_credits("org-down", user_id="u1")

        self.mock_grant.assert_called_once()


class FakeWalletInjectionGuardTests(SimpleTestCase):
    """防御性校验：_GRANT_PATH patch 的是真实模块方法，不存在假模块注入。"""

    def test_patch_target_is_real_service_method(self) -> None:
        from apps.users.wallet.services import organization_wallet_service as mod

        self.assertTrue(hasattr(mod.OrganizationWalletService, "grant_credits"))
        self.assertIsNotNone(getattr(mod.OrganizationWalletService, "grant_credits"))
