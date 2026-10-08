import hmac

from django.conf import settings
from django.http import JsonResponse


class RequireAPIKeyMiddleware:
    """Require the application API key before dispatching any business API."""

    exempt_paths = ("/api/schema/",)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/") and not request.path.startswith(self.exempt_paths):
            supplied_key = request.headers.get("X-API-Key", "")
            expected_key = settings.API_KEY
            if not supplied_key or not hmac.compare_digest(supplied_key, expected_key):
                response = JsonResponse(
                    {"detail": "A valid X-API-Key header is required."},
                    status=401,
                )
                response["WWW-Authenticate"] = "ApiKey"
                return response
        return self.get_response(request)
