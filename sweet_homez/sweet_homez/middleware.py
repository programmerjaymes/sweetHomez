import hmac
import logging

from django.conf import settings
from django.http import JsonResponse


logger = logging.getLogger("sweet_homez.api_auth")


class RequireAPIKeyMiddleware:
    """Require the application API key before dispatching any business API."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            supplied_key = request.headers.get("X-API-Key", "")
            expected_key = settings.API_KEY
            if not supplied_key or not hmac.compare_digest(supplied_key, expected_key):
                logger.warning(
                    "API key rejected method=%s path=%s supplied=%s",
                    request.method,
                    request.path,
                    bool(supplied_key),
                )
                response = JsonResponse(
                    {"detail": "A valid X-API-Key header is required."},
                    status=401,
                )
                response["WWW-Authenticate"] = "ApiKey"
                return response
            logger.info("API key accepted method=%s path=%s", request.method, request.path)
        return self.get_response(request)
