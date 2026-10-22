from django.contrib.auth.models import Permission
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from .models import Role, User


ADMIN_ROLE_NAME = "Admin"


def assign_administrator_role(user):
    """Give a superuser the application Administrator role and every permission."""
    if not user.is_superuser:
        return
    role, _ = Role.objects.get_or_create(
        name=ADMIN_ROLE_NAME,
        defaults={"description": "SweetHomez administrator with full platform access."},
    )
    role.permissions.set(Permission.objects.all())
    user.roles.add(role)


@receiver(post_save, sender=User)
def assign_role_to_new_superuser(sender, instance, **kwargs):
    assign_administrator_role(instance)


@receiver(post_migrate)
def synchronize_administrator_role(sender, **kwargs):
    """Include newly-created model permissions and repair existing superusers."""
    role, _ = Role.objects.get_or_create(
        name=ADMIN_ROLE_NAME,
        defaults={"description": "SweetHomez administrator with full platform access."},
    )
    role.permissions.set(Permission.objects.all())
    for user in User.objects.filter(is_superuser=True).iterator():
        user.roles.add(role)
