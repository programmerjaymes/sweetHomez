from django.contrib.auth.models import Permission
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from lookups.models import District, Locality, Region, Ward

from .models import AgentProfile, Role, User


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
            user_data = {
                key: attrs[key]
                for key in ("username", "email", "first_name", "last_name")
                if key in attrs
            }
            django_validate_password(attrs["password"], user=User(**user_data))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class AgentProfileSerializer(serializers.ModelSerializer):
    coverage_regions = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.filter(is_active=True), many=True, required=False
    )
    coverage_districts = serializers.PrimaryKeyRelatedField(
        queryset=District.objects.filter(is_active=True), many=True, required=False
    )
    coverage_wards = serializers.PrimaryKeyRelatedField(
        queryset=Ward.objects.filter(is_active=True), many=True, required=False
    )
    coverage_localities = serializers.PrimaryKeyRelatedField(
        queryset=Locality.objects.filter(is_active=True), many=True, required=False
    )

    class Meta:
        model = AgentProfile
        fields = [
            "agency_name", "phone_number", "whatsapp_number", "license_number", "bio",
            "is_verified", "coverage_regions", "coverage_districts", "coverage_wards",
            "coverage_localities",
        ]
        read_only_fields = ["is_verified"]

    def validate(self, attrs):
        instance = self.instance
        coverage_fields = (
            "coverage_regions", "coverage_districts", "coverage_wards", "coverage_localities"
        )
        supplied = any(attrs.get(field) for field in coverage_fields)
        existing = instance and any(getattr(instance, field).exists() for field in coverage_fields)
        if not supplied and not existing:
            raise serializers.ValidationError(
                "Select at least one region, district, ward, or street that you cover."
            )
        return attrs


class AgentRegisterSerializer(RegisterSerializer):
    agent_profile = AgentProfileSerializer()

    class Meta(RegisterSerializer.Meta):
        fields = [*RegisterSerializer.Meta.fields, "agent_profile"]

    def create(self, validated_data):
        profile_data = validated_data.pop("agent_profile")
        user = super().create(validated_data)
        agent_role, _ = Role.objects.get_or_create(
            name="Agent", defaults={"description": "Can publish and manage property listings"}
        )
        user.roles.add(agent_role)
        many_to_many = {
            field: profile_data.pop(field, [])
            for field in (
                "coverage_regions", "coverage_districts", "coverage_wards", "coverage_localities"
            )
        }
        profile = AgentProfile.objects.create(user=user, **profile_data)
        for field, values in many_to_many.items():
            getattr(profile, field).set(values)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
