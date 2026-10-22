from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("assistant", "0003_searchconversation_last_recommended_house_ids")]

    operations = [
        migrations.AddField(
            model_name="searchconversation",
            name="purpose",
            field=models.CharField(choices=[("search", "Property search"), ("listing", "Agent listing")], default="search", max_length=12),
        ),
        migrations.AddField(
            model_name="searchconversation",
            name="listing_draft",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="searchconversation",
            name="listing_ready",
            field=models.BooleanField(default=False),
        ),
    ]
