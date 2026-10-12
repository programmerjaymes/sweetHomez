import base64
import logging
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

import jwt
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.contrib.auth.models import Permission
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.utils import timezone

from .models import AgentProfile, PhoneVerificationCode, Role, Subscription, User
from .serializers import AgentProfileSerializer, AgentRegisterSerializer, ChangePasswordSerializer, EmailOrUsernameTokenObtainPairSerializer, LogoutSerializer, PermissionSerializer, RegisterSerializer, RoleSerializer, UserSerializer

logger = logging.getLogger(__name__)
google_jwk_client = jwt.PyJWKClient("https://www.googleapis.com/oauth2/v3/certs", cache_keys=True)
ONBOARDING_PLANS = {
    "home_basic": {"account_type": "home_seeker", "name": "Home Basic", "amount": 5000},
    "home_plus": {"account_type": "home_seeker", "name": "Home Plus", "amount": 10000},
    "agent_starter": {"account_type": "agent", "name": "Agent Starter", "amount": 20000},
    "agent_pro": {"account_type": "agent", "name": "Agent Pro", "amount": 35000},
}


def _tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token), "user": UserSerializer(user).data}


def _unique_username(seed):
    base = "".join(char for char in seed.lower() if char.isalnum() or char in "._-")[:120] or "user"
    candidate, suffix = base, 1
    while User.objects.filter(username=candidate).exists():
        suffix += 1
        candidate = f"{base[:110]}-{suffix}"
    return candidate


def _normalize_phone(value):
    phone = "".join(char for char in str(value or "") if char.isdigit() or char == "+")
    if phone.startswith("0"):
        phone = "+255" + phone[1:]
    if not phone.startswith("+"):
        phone = "+" + phone
    if len(phone) < 10 or len(phone) > 16:
        raise ValueError("Enter a valid phone number including the country code.")
    return phone


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def google_login(request):
    if not settings.GOOGLE_CLIENT_ID:
        return Response({"detail": "Google login is not configured."}, status=503)
    credential = request.data.get("credential", "")
    if not credential:
        return Response({"detail": "Google did not return an ID token. Please try again."}, status=400)
    try:
        key = google_jwk_client.get_signing_key_from_jwt(credential)
        claims = jwt.decode(credential, key.key, algorithms=["RS256"], audience=settings.GOOGLE_CLIENT_ID, issuer=["accounts.google.com", "https://accounts.google.com"])
    except jwt.ExpiredSignatureError:
        return Response({"detail": "The Google sign-in expired. Please choose your account again."}, status=400)
    except jwt.InvalidAudienceError:
        logger.warning("Google login rejected: token audience does not match GOOGLE_CLIENT_ID")
        return Response({"detail": "Google client ID mismatch. Restart both SweetHomez servers after updating the client ID."}, status=400)
    except jwt.InvalidIssuerError:
        logger.warning("Google login rejected: invalid token issuer")
        return Response({"detail": "Google returned an invalid token issuer."}, status=400)
    except jwt.PyJWKClientError as exc:
        logger.warning("Google signing-key lookup failed: %s", type(exc).__name__)
        return Response({"detail": "Google signing keys are temporarily unavailable. Please try again."}, status=503)
    except jwt.InvalidTokenError as exc:
        logger.warning("Google token verification failed: %s", type(exc).__name__)
        return Response({"detail": "Google returned an invalid sign-in token. Please choose your account again."}, status=400)
    except Exception as exc:
        logger.exception("Unexpected Google login verification error: %s", type(exc).__name__)
        return Response({"detail": "Google sign-in could not be verified because of a server error."}, status=500)
    email = str(claims.get("email", "")).lower()
    if not email or not claims.get("email_verified") or not claims.get("sub"):
        return Response({"detail": "A verified Google email address is required."}, status=400)
    user = User.objects.filter(google_sub=claims["sub"]).first() or User.objects.filter(email__iexact=email).first()
    if not user or not hasattr(user, "subscription"):
        onboarding_token = signing.dumps({"sub": claims["sub"], "email": email, "first_name": claims.get("given_name", ""), "last_name": claims.get("family_name", ""), "picture": claims.get("picture", ""), "existing_user_id": user.pk if user else None}, salt="google-onboarding")
        return Response({"requires_onboarding": True, "onboarding_token": onboarding_token, "profile": {"email": email, "first_name": claims.get("given_name", ""), "last_name": claims.get("family_name", ""), "picture": claims.get("picture", "")}})
    user.google_sub = claims["sub"]
    user.first_name = claims.get("given_name", user.first_name)
    user.last_name = claims.get("family_name", user.last_name)
    user.profile_image_url = claims.get("picture", user.profile_image_url)
    user.save()
    return Response(_tokens_for(user))


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def complete_onboarding(request):
    try:
        identity = signing.loads(request.data.get("onboarding_token", ""), salt="google-onboarding", max_age=900)
        phone = _normalize_phone(request.data.get("phone_number"))
    except signing.SignatureExpired:
        return Response({"detail": "Your Google registration session expired. Please sign in again."}, status=400)
    except (signing.BadSignature, ValueError):
        return Response({"detail": "Invalid registration session or phone number."}, status=400)
    plan_code = request.data.get("plan_code", "")
    plan = ONBOARDING_PLANS.get(plan_code)
    if not plan:
        return Response({"detail": "Choose a valid bundle."}, status=400)
    existing_user_id = identity.get("existing_user_id")
    upgrading_agent = bool(identity.get("upgrade_agent"))
    if not existing_user_id and (User.objects.filter(email__iexact=identity["email"]).exists() or User.objects.filter(google_sub=identity["sub"]).exists()):
        return Response({"detail": "This Google account is already registered. Please log in."}, status=409)
    if plan["account_type"] == "agent" and not str(request.data.get("coverage_areas", "")).strip():
        return Response({"detail": "Agents must provide at least one coverage area."}, status=400)
    with transaction.atomic():
        if existing_user_id:
            user = User.objects.select_for_update().get(pk=existing_user_id, email__iexact=identity["email"])
            if hasattr(user, "subscription") and not upgrading_agent:
                return Response({"detail": "This account has already completed registration."}, status=409)
            if not user.phone_number:
                user.phone_number = phone
        else:
            user = User.objects.create_user(username=_unique_username(identity["email"].split("@")[0]), email=identity["email"], phone_number=phone)
            user.set_unusable_password()
        if identity.get("sub") and not str(identity["sub"]).startswith("user:"):
            user.google_sub = identity["sub"]
        user.first_name = identity.get("first_name", "")
        user.last_name = identity.get("last_name", "")
        user.profile_image_url = identity.get("picture", "")
        user.phone_verified = True
        user.save()
        role_name = "Agent" if plan["account_type"] == "agent" else "Home seeker"
        role, _ = Role.objects.get_or_create(name=role_name, defaults={"description": f"SweetHomez {role_name.lower()} account"})
        user.roles.add(role)
        if plan["account_type"] == "agent" and not upgrading_agent:
            AgentProfile.objects.create(user=user, agency_name=str(request.data.get("agency_name", "")).strip(), phone_number=phone, whatsapp_number=phone, coverage_areas=str(request.data.get("coverage_areas", "")).strip())
        if upgrading_agent:
            if plan["account_type"] != "agent":
                return Response({"detail": "Choose an agent bundle to upgrade."}, status=400)
            AgentProfile.objects.update_or_create(user=user, defaults={"agency_name": str(request.data.get("agency_name", "")).strip(), "phone_number": phone, "whatsapp_number": phone, "coverage_areas": str(request.data.get("coverage_areas", "")).strip()})
            subscription = user.subscription
            subscription.account_type = "agent"
            subscription.plan_code = plan_code
            subscription.plan_name = plan["name"]
            subscription.amount = plan["amount"]
            subscription.payment_phone = phone
            subscription.payment_reference = f"DUMMY-{secrets.token_hex(8).upper()}"
            subscription.status = Subscription.Status.ACTIVE
            subscription.expires_at = timezone.now() + timedelta(days=30)
            subscription.save()
        else:
            Subscription.objects.create(user=user, account_type=plan["account_type"], plan_code=plan_code, plan_name=plan["name"], amount=plan["amount"], payment_phone=phone, payment_reference=f"DUMMY-{secrets.token_hex(8).upper()}", expires_at=timezone.now() + timedelta(days=30))
    data = _tokens_for(user)
    data["payment"] = {"status": "completed", "provider": "dummy", "amount": plan["amount"], "plan": plan["name"]}
    return Response(data, status=201)


@api_view(["POST"])
def onboarding_session(request):
    user = request.user
    upgrade_agent = request.data.get("upgrade_to") == "agent"
    if upgrade_agent and getattr(getattr(user, "subscription", None), "account_type", None) == "agent":
        return Response({"detail": "This account is already an agent."}, status=409)
    if not upgrade_agent and hasattr(user, "subscription") and user.subscription.status == Subscription.Status.ACTIVE and user.subscription.expires_at > timezone.now():
        return Response({"detail": "Registration is already complete."}, status=409)
    token = signing.dumps({"sub": user.google_sub or f"user:{user.pk}", "email": user.email, "first_name": user.first_name, "last_name": user.last_name, "picture": user.profile_image_url, "existing_user_id": user.pk, "upgrade_agent": upgrade_agent}, salt="google-onboarding")
    return Response({"onboarding_token": token})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def request_phone_code(request):
    try:
        phone = _normalize_phone(request.data.get("phone_number"))
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)
    if PhoneVerificationCode.objects.filter(phone_number=phone, created_at__gte=timezone.now() - timedelta(seconds=60)).exists():
        return Response({"detail": "Please wait one minute before requesting another code."}, status=429)
    code = f"{secrets.randbelow(1000000):06d}"
    PhoneVerificationCode.objects.filter(phone_number=phone).delete()
    PhoneVerificationCode.objects.create(phone_number=phone, code_hash=make_password(code), expires_at=timezone.now() + timedelta(minutes=10))
    if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER:
        data = urllib.parse.urlencode({"To": phone, "From": settings.TWILIO_FROM_NUMBER, "Body": f"Your SweetHomez verification code is {code}. It expires in 10 minutes."}).encode()
        url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
        auth = base64.b64encode(f"{settings.TWILIO_ACCOUNT_SID}:{settings.TWILIO_AUTH_TOKEN}".encode()).decode()
        try:
            urllib.request.urlopen(urllib.request.Request(url, data=data, headers={"Authorization": f"Basic {auth}"}), timeout=10).read()
        except (urllib.error.URLError, TimeoutError):
            return Response({"detail": "The verification message could not be sent. Please try again."}, status=502)
    elif settings.DEBUG:
        return Response({"detail": "Verification code created for development.", "debug_code": code})
    else:
        return Response({"detail": "Phone verification is not configured."}, status=503)
    return Response({"detail": "Verification code sent."})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def verify_phone_code(request):
    try:
        phone = _normalize_phone(request.data.get("phone_number"))
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)
    record = PhoneVerificationCode.objects.filter(phone_number=phone).first()
    if not record or record.expires_at <= timezone.now() or record.attempts >= 5:
        return Response({"detail": "This verification code is invalid or expired."}, status=400)
    record.attempts += 1
    record.save(update_fields=["attempts"])
    if not check_password(str(request.data.get("code", "")), record.code_hash):
        return Response({"detail": "The verification code is incorrect."}, status=400)
    user = User.objects.filter(phone_number=phone).first()
    if not user:
        user = User.objects.create_user(username=_unique_username(f"phone-{phone[-9:]}"), email=f"phone-{phone[-9:]}@users.sweethomez.local", phone_number=phone)
        user.set_unusable_password()
    user.phone_verified = True
    user.save(update_fields=["phone_verified"])
    record.delete()
    return Response(_tokens_for(user))


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
    serializer_class = EmailOrUsernameTokenObtainPairSerializer


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
