from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("houses", "0005_house_availability_last_confirmed_at_and_more")]

    operations = [
        migrations.AddField(
            model_name="house",
            name="outdoor_toilets",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
