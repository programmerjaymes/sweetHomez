from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assistant", "0002_searchconversation_consecutive_off_topic_count"),
    ]

    operations = [
        migrations.AddField(
            model_name="searchconversation",
            name="last_recommended_house_ids",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
