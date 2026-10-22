from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("houses", "0008_house_kitchen_options_and_zero_defaults"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="house",
            name="moderation_status",
            field=models.CharField(choices=[("pending", "Pending review"), ("approved", "Approved"), ("rejected", "Disapproved")], default="approved", max_length=12),
        ),
        migrations.AddField(
            model_name="house",
            name="moderated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="house",
            name="moderated_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="moderated_house_listings", to=settings.AUTH_USER_MODEL),
        ),
    ]
