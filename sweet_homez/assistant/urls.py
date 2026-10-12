from django.urls import path

from .views import ChatView, ConversationDetailView, ConversationHistoryView, InquiryCreateView, ViewingRequestCreateView

app_name = "assistant"

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat"),
    path("conversations/", ConversationHistoryView.as_view(), name="conversation-history"),
    path("conversations/<uuid:conversation_id>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path("inquiries/", InquiryCreateView.as_view(), name="inquiry-create"),
    path("viewings/", ViewingRequestCreateView.as_view(), name="viewing-create"),
]
