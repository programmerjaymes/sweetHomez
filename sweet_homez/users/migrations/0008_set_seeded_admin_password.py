from django.contrib.auth.hashers import make_password
from django.db import migrations


ADMIN_EMAIL = "programmerjames12@gmail.com"
ADMIN_PASSWORD = "Tehama@2025"


def set_seeded_admin_password(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(email__iexact=ADMIN_EMAIL).update(
        password=make_password(ADMIN_PASSWORD),
        is_active=True,
        is_staff=True,
        is_superuser=True,
    )


class Migration(migrations.Migration):
    dependencies = [("users", "0007_seed_programmerjames_admin")]

    operations = [
        migrations.RunPython(set_seeded_admin_password, migrations.RunPython.noop),
    ]
