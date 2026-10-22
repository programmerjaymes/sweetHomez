from django.contrib.auth.hashers import make_password
from django.db import migrations


ADMIN_EMAIL = "programmerjames12@gmail.com"
ADMIN_USERNAME = "programmerjames12"
ADMIN_PASSWORD = "Tehama@2025"


def seed_admin(apps, schema_editor):
    User = apps.get_model("users", "User")
    Role = apps.get_model("users", "Role")

    user = User.objects.filter(email__iexact=ADMIN_EMAIL).first()
    if user is None:
        username = ADMIN_USERNAME
        if User.objects.filter(username=username).exists():
            username = f"{ADMIN_USERNAME}_admin"
        user = User.objects.create(
            username=username,
            email=ADMIN_EMAIL,
            password=make_password(ADMIN_PASSWORD),
            first_name="James",
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
    else:
        update_fields = []
        for field, value in (
            ("is_active", True),
            ("is_staff", True),
            ("is_superuser", True),
        ):
            if getattr(user, field) != value:
                setattr(user, field, value)
                update_fields.append(field)
        if update_fields:
            user.save(update_fields=update_fields)

    admin_role, _ = Role.objects.get_or_create(
        name="Admin",
        defaults={"description": "SweetHomez administrator with full platform access."},
    )
    user.roles.add(admin_role)


class Migration(migrations.Migration):
    dependencies = [("users", "0006_agentprofile_coverage_areas_subscription")]

    operations = [
        migrations.RunPython(seed_admin, migrations.RunPython.noop),
    ]
