from django.contrib.auth.models import Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import AgentProfile, Role, User
from .serializers import AgentProfileSerializer, AgentRegisterSerializer, ChangePasswordSerializer, LogoutSerializer, PermissionSerializer, RegisterSerializer, RoleSerializer, UserSerializer


users_crud_schema = extend_schema_view(
    list=extend_schema(tags=["Users"]),
    retrieve=extend_schema(tags=["Users"]),
    create=extend_schema(tags=["Users"]),
    update=extend_schema(tags=["Users"]),
    partial_update=extend_schema(tags=["Users"]),
    destroy=extend_schema(tags=["Users"]),
)

users_read_schema = extend_schema_view(
    list=extend_schema(tags=["Users"]),
    retrieve=extend_schema(tags=["Users"]),
)


@extend_schema_view(post=extend_schema(tags=["Users"]))
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


@extend_schema_view(post=extend_schema(tags=["Users"]))
class AgentRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = AgentRegisterSerializer


@extend_schema_view(
    get=extend_schema(tags=["Users"]),
    put=extend_schema(tags=["Users"]),
    patch=extend_schema(tags=["Users"]),
)
class CurrentAgentProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = AgentProfileSerializer

    def get_object(self):
        return AgentProfile.objects.get(user=self.request.user)


@extend_schema_view(post=extend_schema(tags=["Users"]))
class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]


@extend_schema_view(post=extend_schema(tags=["Users"]))
class RefreshTokenView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]


@extend_schema_view(post=extend_schema(tags=["Users"]))
class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except Exception:
            return Response({"detail": "Invalid or expired refresh token."}, status=400)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    get=extend_schema(tags=["Users"]),
    put=extend_schema(tags=["Users"]),
    patch=extend_schema(tags=["Users"]),
)
class CurrentUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


@extend_schema_view(post=extend_schema(tags=["Users"]))
class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response({"old_password": ["Password is incorrect."]}, status=400)
        new_password = serializer.validated_data["new_password"]
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return Response({"new_password": list(exc.messages)}, status=400)
        user.set_password(new_password)
        user.save(update_fields=["password"])
        return Response({"detail": "Password changed successfully."})


@users_crud_schema
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.prefetch_related("groups", "user_permissions").order_by("id")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    @extend_schema(tags=["Users"])
    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response(self.get_serializer(user).data)


@users_crud_schema
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.prefetch_related("permissions").order_by("name")
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAdminUser]


@users_read_schema
class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.select_related("content_type").order_by("content_type__app_label", "codename")
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAdminUser]
