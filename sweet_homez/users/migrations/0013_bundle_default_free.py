from datetime import timedelta
from uuid import uuid4

from django.db import migrations, models
from django.utils import timezone


def create_free_bundle(apps, schema_editor):
    Bundle = apps.get_model("users", "Bundle")
    Bundle.objects.update(is_default=False)
    free, _ = Bundle.objects.update_or_create(
        code="free",
        defaults={
            "name":"Free", "audience":"home_seeker", "description":"Default free access with minimum chat usage.",
            "amount":0, "duration_days":36500, "advantages":["Basic AI home search", "Up to 5 prompts per chat", "Up to 10 prompts per day"],
            "is_active":True, "is_default":True, "display_order":0,
            "prompts_per_chat":5, "prompts_per_day":10, "prompts_per_week":30, "total_prompts":100,
            "max_houses":0, "video_upload_allowed":False, "max_photos_per_house":0,
        },
    )
    User = apps.get_model("users", "User")
    Subscription = apps.get_model("users", "Subscription")
    Role = apps.get_model("users", "Role")
    home_role, _ = Role.objects.get_or_create(name="Home seeker", defaults={"description":"SweetHomez home seeker account"})
    for user in User.objects.filter(is_staff=False, subscription__isnull=True):
        Subscription.objects.create(user=user, account_type="home_seeker", plan_code=free.code, plan_name=free.name, amount=0, payment_phone=user.phone_number or "FREE", payment_reference=f"FREE-{uuid4().hex.upper()}", expires_at=timezone.now()+timedelta(days=free.duration_days))
        user.roles.add(home_role)


class Migration(migrations.Migration):
    dependencies=[("users","0012_bundle_usage_limits")]
    operations=[
        migrations.AddField(model_name="bundle",name="is_default",field=models.BooleanField(default=False)),
        migrations.RunPython(create_free_bundle,migrations.RunPython.noop),
    ]
