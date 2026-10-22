from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("houses", "0007_house_has_living_room")]

    operations = [
        migrations.AlterField(model_name="house", name="bedrooms", field=models.PositiveSmallIntegerField(default=0)),
        migrations.AlterField(model_name="house", name="bathrooms", field=models.PositiveSmallIntegerField(default=0)),
        migrations.AlterField(model_name="house", name="kitchens", field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name="house", name="has_indoor_kitchen", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="house", name="has_outdoor_kitchen", field=models.BooleanField(default=False)),
    ]
