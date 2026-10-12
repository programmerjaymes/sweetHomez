from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AgentRegisterView, ChangePasswordView, CurrentAgentProfileView, CurrentUserView, LoginView, LogoutView, PermissionViewSet, RefreshTokenView, RegisterView, RoleViewSet, UserViewSet, complete_onboarding, google_login, onboarding_session, request_phone_code, verify_phone_code

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("roles", RoleViewSet, basename="role")
router.register("permissions", PermissionViewSet, basename="permission")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/register-agent/", AgentRegisterView.as_view(), name="register-agent"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/google/", google_login, name="google-login"),
    path("auth/onboarding/complete/", complete_onboarding, name="complete-onboarding"),
    path("auth/onboarding/session/", onboarding_session, name="onboarding-session"),
    path("auth/phone/request/", request_phone_code, name="phone-request"),
    path("auth/phone/verify/", verify_phone_code, name="phone-verify"),
    path("auth/token/refresh/", RefreshTokenView.as_view(), name="token-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", CurrentUserView.as_view(), name="current-user"),
    path("agent-profile/me/", CurrentAgentProfileView.as_view(), name="current-agent-profile"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("", include(router.urls)),
]
