from rest_framework import permissions


class ModelActionPermissions(permissions.DjangoModelPermissions):
    """Apply Django model permissions to every CRUD verb, including reads."""

    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        required = getattr(view, "action_permissions", {}).get(getattr(view, "action", None))
        if required:
            return request.user.has_perms(required)
        return super().has_permission(request, view)


def permission_required(*permission_names):
    """Create a DRF permission class for a non-model endpoint/action."""

    class RequiredPermission(permissions.BasePermission):
        message = "You do not have permission to perform this action."

        def has_permission(self, request, view):
            return bool(
                request.user
                and request.user.is_authenticated
                and request.user.has_perms(permission_names)
            )

    return RequiredPermission


class AdminRecordPermission(permissions.BasePermission):
    """Require the view permission matching the requested administrator report."""

    section_permissions = {
        "chat-histories": "assistant.view_searchconversation",
        "subscriptions": "users.view_subscription",
        "login-activities": "users.view_loginactivity",
        "audit-trails": "users.view_audittrail",
    }

    def has_permission(self, request, view):
        permission_name = self.section_permissions.get(request.query_params.get("section", ""))
        return bool(
            permission_name
            and request.user
            and request.user.is_authenticated
            and request.user.has_perm(permission_name)
        )
