from django.urls import path

from .views import AssistantTestView

urlpatterns = [
    path("", AssistantTestView.as_view(), name="assistant-test-ui"),
]
