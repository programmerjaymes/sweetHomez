from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("lookups", "0001_initial")]
    operations = [
        migrations.AlterModelOptions(
            name="region",
            options={"ordering": ["name_en"], "permissions": [
                ("sync_administrative_areas", "Can synchronize administrative areas"),
            ]},
        ),
    ]
