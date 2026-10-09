from django.urls import path

from .views import ChatView, ConversationDetailView, InquiryCreateView, ViewingRequestCreateView

app_name = "assistant"

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat"),
    path("conversations/<uuid:conversation_id>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path("inquiries/", InquiryCreateView.as_view(), name="inquiry-create"),
    path("viewings/", ViewingRequestCreateView.as_view(), name="viewing-create"),
]
