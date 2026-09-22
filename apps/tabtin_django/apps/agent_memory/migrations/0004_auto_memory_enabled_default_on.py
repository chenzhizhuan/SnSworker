from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("agent_memory", "0003_backfill_existing_workspace_memory_settings"),
    ]

    operations = [
        # 内部部署产品策略：自动记忆增强对新建 Workspace 默认开启，
        # 记忆模型默认走智算方舟官方默认绑定（official_default）。
        # 仅调整 schema default 与 lazy-create 语义，不改动存量行——
        # 存量身份已由 0003 数据迁移回填开启。
        migrations.AlterField(
            model_name="workspacememorysettings",
            name="auto_memory_enabled",
            field=models.BooleanField(
                default=True,
                help_text="新 Workspace 默认开启（默认使用智算方舟官方默认记忆模型）；存量兼容由独立数据迁移显式回填开启。",
                verbose_name="自动记忆增强",
            ),
        ),
    ]
