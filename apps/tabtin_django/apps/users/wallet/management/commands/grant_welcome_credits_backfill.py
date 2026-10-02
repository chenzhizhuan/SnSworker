"""为存量个人组织补发注册欢迎点券。

背景：注册即送（TABTIN_REGISTER_WELCOME_CREDITS）上线前注册的存量用户，
其个人组织钱包没有欢迎赠流水。本命令按流水判重幂等补发，可安全重复执行。

用法（生产容器内）：
    python manage.py grant_welcome_credits_backfill --dry-run   # 只统计
    python manage.py grant_welcome_credits_backfill             # 实际补发
    python manage.py grant_welcome_credits_backfill --amount 500

判重口径：WalletTransaction 存在 transaction_type='grant' 且
description='注册欢迎赠送' 的组织视为已发放，跳过——与注册链路
（OrganizationService._grant_register_welcome_credits）产出的流水一致，
新注册用户不会被重复补发。
"""
from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

GRANT_DESCRIPTION = "注册欢迎赠送"


class Command(BaseCommand):
    help = (
        "为存量个人组织补发注册欢迎点券（幂等：凭「注册欢迎赠送」grant 流水"
        "判重，可安全重复执行）。--dry-run 只统计不发放。"
    )

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="只统计待补发组织数量，不实际发放。",
        )
        parser.add_argument(
            "--amount",
            type=int,
            default=None,
            help="补发额度；缺省读 settings.TABTIN_REGISTER_WELCOME_CREDITS。",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from django.conf import settings

        from apps.services.common.db_router import postgres_app_db_alias
        from apps.tabtinspace.models import Organization
        from apps.users.wallet.models import WalletTransaction
        from apps.users.wallet.services.organization_wallet_service import (
            OrganizationWalletService,
        )

        amount = options["amount"]
        if amount is None:
            amount = getattr(settings, "TABTIN_REGISTER_WELCOME_CREDITS", 1000)
        if amount <= 0:
            raise CommandError(
                f"补发额度必须大于 0（当前 amount={amount}）；如需关闭请直接不执行本命令。",
            )

        dry_run: bool = options["dry_run"]

        personal_orgs = list(
            Organization.objects.using(postgres_app_db_alias())
            .filter(type=Organization.OrganizationType.PERSONAL)
            .values_list("id", "owner_id"),
        )

        total = len(personal_orgs)
        granted = skipped = failed = 0
        self.stdout.write(
            f"{'[DRY-RUN] ' if dry_run else ''}"
            f"扫描个人组织 {total} 个，补发额度 {amount} 点券"
        )

        for org_id, owner_id in personal_orgs:
            org_key = str(org_id)
            already_granted = WalletTransaction.objects.filter(
                organization_id=org_key,
                transaction_type="grant",
                description=GRANT_DESCRIPTION,
            ).exists()
            if already_granted:
                skipped += 1
                continue
            if dry_run:
                granted += 1
                continue
            try:
                OrganizationWalletService().grant_credits(
                    org_key,
                    amount,
                    description=GRANT_DESCRIPTION,
                    user_id=str(owner_id) if owner_id else None,
                )
                granted += 1
                self.stdout.write(f"已补发 {org_key} +{amount}")
            except Exception as exc:  # noqa: BLE001 —— 单组织失败不中断整体
                failed += 1
                self.stderr.write(f"补发失败 {org_key}: {exc}")

        summary = (
            f"{'[DRY-RUN] ' if dry_run else ''}"
            f"total={total} granted={granted} skipped={skipped} failed={failed}"
        )
        if failed:
            self.stdout.write(self.style.WARNING(summary))
        else:
            self.stdout.write(self.style.SUCCESS(summary))
