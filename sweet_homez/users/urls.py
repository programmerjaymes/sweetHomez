from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChangePasswordView, CurrentUserView, LoginView, LogoutView, PermissionViewSet, RefreshTokenView, RegisterView, RoleViewSet, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("roles", RoleViewSet, basename="role")
router.register("permissions", PermissionViewSet, basename="permission")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/token/refresh/", RefreshTokenView.as_view(), name="token-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", CurrentUserView.as_view(), name="current-user"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("", include(router.urls)),
]
