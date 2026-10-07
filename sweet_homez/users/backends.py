from django.contrib.auth.backends import ModelBackend


class RolePermissionBackend(ModelBackend):
    """Include permissions assigned through the application's Role model."""

    def get_group_permissions(self, user_obj, obj=None):
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()
        if not hasattr(user_obj, "_role_perm_cache"):
            permissions = user_obj.roles.values_list(
                "permissions__content_type__app_label", "permissions__codename"
            )
            user_obj._role_perm_cache = {
                f"{app_label}.{codename}"
                for app_label, codename in permissions
                if app_label and codename
            }
        return user_obj._role_perm_cache
