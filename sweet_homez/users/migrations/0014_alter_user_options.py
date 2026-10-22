from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("users", "0013_bundle_default_free")]
    operations = [
        migrations.AlterModelOptions(
            name="user",
            options={"permissions": [
                ("view_admin_dashboard", "Can view the administrator dashboard"),
                ("reset_user_password", "Can regenerate user passwords"),
            ]},
        ),
    ]
