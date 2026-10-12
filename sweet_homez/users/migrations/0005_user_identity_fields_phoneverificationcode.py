from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("users", "0004_agentprofile_coverage_districts_and_more")]

    operations = [
        migrations.AddField(model_name="user", name="google_sub", field=models.CharField(blank=True, max_length=255, null=True, unique=True)),
        migrations.AddField(model_name="user", name="phone_number", field=models.CharField(blank=True, max_length=30, null=True, unique=True)),
        migrations.AddField(model_name="user", name="phone_verified", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="user", name="profile_image_url", field=models.URLField(blank=True)),
        migrations.CreateModel(
            name="PhoneVerificationCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phone_number", models.CharField(db_index=True, max_length=30)),
                ("code_hash", models.CharField(max_length=128)),
                ("expires_at", models.DateTimeField()),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
