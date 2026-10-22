from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("houses", "0009_house_moderation")]
    operations = [
        migrations.AlterModelOptions(
            name="house",
            options={
                "ordering": ["-created_at"],
                "permissions": [("moderate_house", "Can approve or reject house listings")],
            },
        ),
    ]
