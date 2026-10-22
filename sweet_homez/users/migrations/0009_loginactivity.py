from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("users", "0008_set_seeded_admin_password")]
    operations = [migrations.CreateModel(name="LoginActivity", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),("identifier", models.CharField(blank=True, max_length=254)),("ip_address", models.GenericIPAddressField(blank=True, null=True)),("user_agent", models.TextField(blank=True)),("successful", models.BooleanField(default=False)),("created_at", models.DateTimeField(auto_now_add=True)),("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="login_activities", to=settings.AUTH_USER_MODEL))], options={"verbose_name_plural":"login activities","ordering":["-created_at"]})]
