from django.contrib.auth.models import Permission
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Role, User


class PermissionSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(source="content_type.app_label", read_only=True)

    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "app_label"]


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(queryset=Permission.objects.all(), many=True, required=False)

    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions"]


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    roles = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), many=True, required=False)
    permissions = serializers.PrimaryKeyRelatedField(source="user_permissions", queryset=Permission.objects.all(), many=True, required=False)
    effective_permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "first_name", "last_name", "is_active", "is_staff", "roles", "permissions", "effective_permissions", "date_joined"]
        read_only_fields = ["id", "effective_permissions", "date_joined"]

    def get_effective_permissions(self, obj) -> list[str]:
        return sorted(obj.get_all_permissions())

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if not request or not request.user.is_staff:
            for name in ("is_active", "is_staff", "roles", "permissions"):
                fields[name].read_only = True
        return fields

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        roles = validated_data.pop("roles", [])
        permissions = validated_data.pop("user_permissions", [])
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        user.roles.set(roles)
        user.user_permissions.set(permissions)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=["password"])
        return instance

    def validate_password(self, value):
        try:
            django_validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password", "password_confirm"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        try:
            django_validate_password(attrs["password"], user=User(**{key: value for key, value in attrs.items() if key != "password"}))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
