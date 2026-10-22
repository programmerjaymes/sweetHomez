from django.db import migrations, models


def set_default_limits(apps, schema_editor):
    Bundle = apps.get_model("users", "Bundle")
    limits = {
        "home_basic": dict(prompts_per_chat=15, prompts_per_day=30, prompts_per_week=150, total_prompts=500, max_houses=0, video_upload_allowed=False, max_photos_per_house=0),
        "home_plus": dict(prompts_per_chat=40, prompts_per_day=100, prompts_per_week=500, total_prompts=2000, max_houses=0, video_upload_allowed=False, max_photos_per_house=0),
        "agent_starter": dict(prompts_per_chat=30, prompts_per_day=75, prompts_per_week=350, total_prompts=1500, max_houses=20, video_upload_allowed=False, max_photos_per_house=8),
        "agent_pro": dict(prompts_per_chat=100, prompts_per_day=300, prompts_per_week=1500, total_prompts=None, max_houses=None, video_upload_allowed=True, max_photos_per_house=12),
    }
    for code, values in limits.items():
        Bundle.objects.filter(code=code).update(**values)


class Migration(migrations.Migration):
    dependencies = [("users", "0011_bundle")]
    operations = [
        migrations.AddField(model_name="bundle", name="prompts_per_chat", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="bundle", name="prompts_per_day", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="bundle", name="prompts_per_week", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="bundle", name="total_prompts", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="bundle", name="max_houses", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="bundle", name="video_upload_allowed", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="bundle", name="max_photos_per_house", field=models.PositiveIntegerField(default=12)),
        migrations.RunPython(set_default_limits, migrations.RunPython.noop),
    ]
