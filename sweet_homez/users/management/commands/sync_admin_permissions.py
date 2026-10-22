from django.core.management.base import BaseCommand

from users.signals import synchronize_administrators


class Command(BaseCommand):
    help = "Assign every permission to the Admin role and attach it to all superusers."

    def handle(self, *args, **options):
        role, superuser_count, permission_count = synchronize_administrators()
        assigned_count = role.permissions.count()
        if assigned_count != permission_count:
            self.stderr.write(self.style.ERROR(
                f"Admin role has {assigned_count}/{permission_count} permissions."
            ))
            return
        self.stdout.write(self.style.SUCCESS(
            f"Admin synchronized: {assigned_count}/{permission_count} permissions; "
            f"assigned to {superuser_count} superuser(s)."
        ))
