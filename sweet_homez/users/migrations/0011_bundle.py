from django.db import migrations, models


def seed_bundles(apps, schema_editor):
    Bundle = apps.get_model("users", "Bundle")
    defaults = [
        ("home_basic", "Home Basic", "home_seeker", 5000, ["AI home search", "Save conversations", "Contact verified agents"], 1),
        ("home_plus", "Home Plus", "home_seeker", 10000, ["Everything in Basic", "Priority home matching", "Unlimited saved homes"], 2),
        ("agent_starter", "Agent Starter", "agent", 20000, ["Verified agent profile", "Publish property listings", "Receive buyer inquiries"], 1),
        ("agent_pro", "Agent Pro", "agent", 35000, ["Everything in Starter", "Priority property visibility", "Advanced buyer inquiries"], 2),
    ]
    for code, name, audience, amount, advantages, order in defaults:
        Bundle.objects.get_or_create(code=code, defaults={"name": name, "audience": audience, "amount": amount, "duration_days": 30, "advantages": advantages, "display_order": order})


class Migration(migrations.Migration):
    dependencies = [("users", "0010_audittrail")]
    operations = [
        migrations.CreateModel(
            name="Bundle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("audience", models.CharField(choices=[("home_seeker", "Normal user"), ("agent", "Agent")], max_length=20)),
                ("description", models.TextField(blank=True)),
                ("amount", models.PositiveIntegerField()),
                ("duration_days", models.PositiveIntegerField(default=30)),
                ("advantages", models.JSONField(blank=True, default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("display_order", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["audience", "display_order", "amount", "name"]},
        ),
        migrations.RunPython(seed_bundles, migrations.RunPython.noop),
    ]
