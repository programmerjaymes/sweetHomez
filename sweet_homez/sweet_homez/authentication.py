import logging

from rest_framework_simplejwt.authentication import JWTAuthentication


logger = logging.getLogger("sweet_homez.api_auth")


class LoggedJWTAuthentication(JWTAuthentication):
    """Log API authentication outcomes without ever logging the JWT itself."""

    def authenticate(self, request):
        path = request.path
        try:
            result = super().authenticate(request)
        except Exception as exc:
            logger.warning(
                "JWT authentication failed method=%s path=%s error=%s detail=%s",
                request.method,
                path,
                type(exc).__name__,
                str(exc),
            )
            raise
        if result is None:
            logger.warning(
                "API request has no Bearer credentials method=%s path=%s",
                request.method,
                path,
            )
        else:
            user, _ = result
            logger.info(
                "JWT authentication successful method=%s path=%s user_id=%s username=%s superuser=%s",
                request.method,
                path,
                user.pk,
                user.username,
                user.is_superuser,
            )
        return result
