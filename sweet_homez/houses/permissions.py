from rest_framework import permissions


def is_agent(user):
    return user.is_authenticated and (user.is_staff or user.roles.filter(name__iexact="Agent").exists())


class IsAgentOwnerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return is_agent(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = obj.agent if hasattr(obj, "agent") else obj.house.agent
        return request.user.is_staff or owner_id(owner) == request.user.id


def owner_id(user):
    return user.id
