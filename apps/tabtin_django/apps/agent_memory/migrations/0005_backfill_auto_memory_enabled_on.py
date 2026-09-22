from __future__ import annotations

from django.db import migrations
from django.utils import timezone


def backfill_auto_memory_enabled_on(apps, schema_editor):
    """内部部署产品策略：统一刷开存量中仍关闭的自动记忆增强。

    仅刷 ``auto_memory_enabled``；``memory_model_mode`` 保持各行原值
    （official_default 行走官方默认绑定，explicit_model 行继续用已绑定的
    具体模型）。无法区分「从未开启」与「Owner 明确关闭」，因此 reverse
    为 noop——迁移回滚不会撤销刷写。新增身份由 0004 后的模型默认值
    （default=True）+ lazy-create 保证开启，不经过这里。
    """
    WorkspaceMemorySettings = apps.get_model("agent_memory", "WorkspaceMemorySettings")
    database = schema_editor.connection.alias
    WorkspaceMemorySettings.objects.using(database).filter(
        auto_memory_enabled=False
    ).update(auto_memory_enabled=True, updated_at=timezone.now())


class Migration(migrations.Migration):

    dependencies = [
        ("agent_memory", "0004_auto_memory_enabled_default_on"),
    ]

    operations = [
        migrations.RunPython(
            backfill_auto_memory_enabled_on,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
