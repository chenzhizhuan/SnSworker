"""注册欢迎点券赠送集成回归测试（TABTIN_REGISTER_WELCOME_CREDITS，默认 1000）。

跑在 settings_share_test（in-memory SQLite + syncdb）：注册链路真实执行
（create_user → signal → ensure_personal_organization → 真实 grant_credits
落库），断言钱包余额与 WalletTransaction 流水。与既有 onboarding 测试同模式
断开 create_user_profile 信号、mock 掉与赠送无关的市场 app 安装副作用。

覆盖：
- 新用户注册 → 钱包真实到账 1000 + grant 流水（幂等：仅一条）
- 重复 onboarding 不重发
- 配置为 0 时关闭赠送（余额保持 0）
- 非法配置安全跳过
- 赠送异常不阻断注册
"""
from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.test import TestCase, override_settings

from apps.services.common.db_router import postgres_app_db_alias
from apps.tabtinspace.models import Organization
from apps.tabtinspace.services.organization_service import OrganizationService
from apps.users.wallet.models import WalletTransaction
from apps.users.wallet.services.organization_wallet_service import (
    OrganizationWalletService,
)

# 与既有 DefaultSpaceOnboardingTests 相同的 onboarding 副作用屏蔽面：
# - provision_billing：isolated 双库布局下 sync 会跨 alias 查 Organization
#   必挂（真 PG 无此问题）；钱包改由 grant 的 get_or_create 兜底创建，落库
#   路径依然真实。
# - _schedule_balance_increase_side_effects：余额联动（通知/解锁/低余额
#   告警）与赠送落库无关，且在 share_test 下会拉 payment 域模块。
# - auto_install_core_apps / provision_builtin_extensions：市场 app 安装，与赠送无关。
_ONBOARDING_PATCHES = (
    patch(
        "apps.tabtinspace.services.app_catalog_service."
        "OrganizationAppCatalogService.auto_install_core_apps"
    ),
    patch.object(OrganizationService, "provision_builtin_extensions"),
    patch.object(OrganizationService, "provision_billing"),
    patch(
        "apps.users.wallet.services.organization_wallet_service."
        "OrganizationWalletService._schedule_balance_increase_side_effects"
    ),
)


class RegisterWelcomeCreditsIntegrationTests(TestCase):
    databases = {"default", "postgresql"}

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        from apps.users.auth.signals import create_user_profile

        cls._create_user_profile_signal = create_user_profile
        post_save.disconnect(receiver=create_user_profile, sender=get_user_model())

    @classmethod
    def tearDownClass(cls) -> None:
        post_save.connect(receiver=cls._create_user_profile_signal, sender=get_user_model())
        super().tearDownClass()

    def _start_patches(self) -> None:
        for p in _ONBOARDING_PATCHES:
            p.start()
            self.addCleanup(p.stop)

    def _create_user(self, label: str):
        User = get_user_model()
        return User.objects.db_manager(postgres_app_db_alias()).create_user(
            email=f"{label}-{uuid4().hex[:8]}@tabtin.test",
            password="TabtinTest#2026",
            nickname="Welcome User",
            is_active=True,
        )

    def _get_personal_org(self, user) -> Organization:
        return Organization.objects.get(
            owner_id=user.id,
            type=Organization.OrganizationType.PERSONAL,
        )

    def _wallet_credits(self, organization_id: str):
        wallet = OrganizationWalletService().get_or_create_wallet(organization_id)
        return wallet.credits

    def test_new_user_registration_grants_default_1000(self) -> None:
        self._start_patches()
        user = self._create_user("welcome-credits")

        organization = self._get_personal_org(user)
        org_id = str(organization.id)

        self.assertEqual(self._wallet_credits(org_id), 1000)

        txs = WalletTransaction.objects.filter(
            organization_id=org_id, transaction_type="grant",
        )
        self.assertEqual(txs.count(), 1)
        tx = txs.first()
        self.assertEqual(tx.amount, 1000)
        self.assertEqual(tx.description, "注册欢迎赠送")

    def test_repeated_onboarding_does_not_regrant(self) -> None:
        self._start_patches()
        user = self._create_user("welcome-idempotent")
        org_id = str(self._get_personal_org(user).id)

        _org, created = OrganizationService.ensure_personal_organization(user)
        self.assertFalse(created)

        self.assertEqual(self._wallet_credits(org_id), 1000)
        self.assertEqual(
            WalletTransaction.objects.filter(
                organization_id=org_id, transaction_type="grant",
            ).count(),
            1,
        )

    @override_settings(TABTIN_REGISTER_WELCOME_CREDITS=0)
    def test_zero_config_disables_grant(self) -> None:
        self._start_patches()
        user = self._create_user("welcome-disabled")
        org_id = str(self._get_personal_org(user).id)

        self.assertEqual(self._wallet_credits(org_id), 0)
        self.assertEqual(
            WalletTransaction.objects.filter(
                organization_id=org_id, transaction_type="grant",
            ).count(),
            0,
        )

    @override_settings(TABTIN_REGISTER_WELCOME_CREDITS="not-a-number")
    def test_invalid_config_skips_grant_safely(self) -> None:
        self._start_patches()
        user = self._create_user("welcome-invalid")
        org_id = str(self._get_personal_org(user).id)

        self.assertEqual(self._wallet_credits(org_id), 0)

    def test_grant_failure_does_not_block_registration(self) -> None:
        self._start_patches()
        with patch(
            "apps.users.wallet.services.organization_wallet_service."
            "OrganizationWalletService.grant_credits",
            side_effect=RuntimeError("wallet down"),
        ):
            user = self._create_user("welcome-failure")

        # 赠送失败：注册链路未被阻断，个人组织正常创建，钱包保持 0
        self.assertTrue(
            Organization.objects.filter(
                owner_id=user.id,
                type=Organization.OrganizationType.PERSONAL,
            ).exists()
        )
        self.assertEqual(self._wallet_credits(str(self._get_personal_org(user).id)), 0)
