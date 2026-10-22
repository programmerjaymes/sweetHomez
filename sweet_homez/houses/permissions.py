from rest_framework import permissions


def is_agent(user):
    return user.is_authenticated and user.roles.filter(name__iexact="Agent").exists()


class IsAgentOwnerOrReadOnly(permissions.BasePermission):
    permission_actions = {
        "POST": "add",
        "PUT": "change",
        "PATCH": "change",
        "DELETE": "delete",
    }

    def required_permission(self, request, view):
        model = view.get_queryset().model
        action = self.permission_actions.get(request.method)
        return f"{model._meta.app_label}.{action}_{model._meta.model_name}" if action else None

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        permission_name = self.required_permission(request, view)
        return is_agent(request.user) or bool(permission_name and request.user.has_perm(permission_name))

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = obj.agent if hasattr(obj, "agent") else obj.house.agent
        permission_name = self.required_permission(request, view)
        return owner_id(owner) == request.user.id or bool(permission_name and request.user.has_perm(permission_name))


def owner_id(user):
    return user.id
