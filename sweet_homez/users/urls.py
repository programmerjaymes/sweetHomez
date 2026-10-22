from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AgentRegisterView, BundleViewSet, ChangePasswordView, CurrentAgentProfileView, CurrentUserView, LoginView, LogoutView, PermissionViewSet, RefreshTokenView, RegisterView, RoleViewSet, UserViewSet, admin_conversation_detail, admin_dashboard, admin_records, complete_onboarding, google_login, onboarding_session, request_phone_code, verify_phone_code

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("roles", RoleViewSet, basename="role")
router.register("permissions", PermissionViewSet, basename="permission")
router.register("bundles", BundleViewSet, basename="bundle")

urlpatterns = [
    path("admin/dashboard/", admin_dashboard, name="admin-dashboard"),
    path("admin/records/", admin_records, name="admin-records"),
    path("admin/conversations/<uuid:conversation_id>/", admin_conversation_detail, name="admin-conversation-detail"),
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
