from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import Throttled

from .models import Bundle, Subscription


def bundle_for_user(user):
    if not user or not user.is_authenticated or user.is_staff or user.is_superuser:
        return None
    subscription = Subscription.objects.filter(
        user=user, status=Subscription.Status.ACTIVE, expires_at__gt=timezone.now()
    ).first()
    latest_subscription = subscription or Subscription.objects.filter(user=user).order_by("-expires_at").first()
    usage_started_at = subscription.starts_at if subscription else (
        max(user.date_joined, latest_subscription.expires_at) if latest_subscription else user.date_joined
    )
    if subscription:
        bundle = Bundle.objects.filter(code=subscription.plan_code).first()
        if bundle:
            return bundle
    return Bundle.objects.filter(is_default=True, audience=Bundle.Audience.HOME_SEEKER, is_active=True).order_by("display_order", "id").first()


def enforce_prompt_limits(user, conversation=None):
    bundle = bundle_for_user(user)
    if not bundle:
        return
    from assistant.models import SearchMessage

    subscription = Subscription.objects.filter(
        user=user, status=Subscription.Status.ACTIVE, expires_at__gt=timezone.now()
    ).first()
    prompts = SearchMessage.objects.filter(
        conversation__user=user,
        role=SearchMessage.Role.USER,
        created_at__gte=usage_started_at,
    )
    checks = []
    if bundle.prompts_per_chat is not None and conversation is not None:
        checks.append((prompts.filter(conversation=conversation).count(), bundle.prompts_per_chat, "this chat session"))
    now = timezone.now()
    if bundle.prompts_per_day is not None:
        checks.append((prompts.filter(created_at__gte=now - timedelta(days=1)).count(), bundle.prompts_per_day, "the last 24 hours"))
    if bundle.prompts_per_week is not None:
        checks.append((prompts.filter(created_at__gte=now - timedelta(days=7)).count(), bundle.prompts_per_week, "the last 7 days"))
    if bundle.total_prompts is not None:
        checks.append((prompts.count(), bundle.total_prompts, "your bundle"))
    for used, limit, period in checks:
        if used >= limit:
            raise Throttled(detail=f"You have reached the {limit}-prompt limit for {period}. Upgrade or renew your bundle to continue.")
