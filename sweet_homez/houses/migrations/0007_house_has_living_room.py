from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("houses", "0006_house_outdoor_toilets")]

    operations = [
        migrations.AddField(
            model_name="house",
            name="has_living_room",
            field=models.BooleanField(default=False),
        ),
    ]
