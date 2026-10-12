from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("users", "0005_user_identity_fields_phoneverificationcode")]

    operations = [
        migrations.AddField(model_name="agentprofile", name="coverage_areas", field=models.TextField(blank=True, help_text="Comma-separated areas served by this agent")),
        migrations.CreateModel(
            name="Subscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("account_type", models.CharField(max_length=20)),
                ("plan_code", models.CharField(max_length=40)),
                ("plan_name", models.CharField(max_length=100)),
                ("amount", models.PositiveIntegerField()),
                ("payment_phone", models.CharField(max_length=30)),
                ("payment_reference", models.CharField(max_length=80, unique=True)),
                ("status", models.CharField(choices=[("active", "Active"), ("expired", "Expired")], default="active", max_length=20)),
                ("starts_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="subscription", to="users.user")),
            ],
        ),
    ]
