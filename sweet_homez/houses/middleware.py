from django.conf import settings
from django.middleware.locale import LocaleMiddleware
from django.utils import translation


class QueryParameterLocaleMiddleware(LocaleMiddleware):
    """Support `?lang=sw` in addition to Django's Accept-Language handling."""

    def process_request(self, request):
        super().process_request(request)
        requested_language = request.GET.get("lang")
        supported = {code for code, _name in settings.LANGUAGES}
        if requested_language in supported:
            translation.activate(requested_language)
            request.LANGUAGE_CODE = requested_language
