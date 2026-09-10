"""#6353：默认 Agent 名「多能工」→「小智」（已 apply 0004 的环境补迁）。"""

from __future__ import annotations

from django.db import migrations


LEGACY_DEFAULT_AGENT_NAME = "多能工"
DEFAULT_ONBOARDING_AGENT_NAME = "小智"


def rename_wanneng_to_xiaotin(apps, schema_editor):
    Agent = apps.get_model("agent", "Agent")
    Agent.objects.filter(name=LEGACY_DEFAULT_AGENT_NAME).update(
        name=DEFAULT_ONBOARDING_AGENT_NAME,
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("agent", "0004b_agent_one_active_default_constraint"),
    ]

    operations = [
        migrations.RunPython(rename_wanneng_to_xiaotin, noop_reverse),
    ]
