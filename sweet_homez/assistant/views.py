from django.conf import settings
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houses.serializers import HouseSerializer

from .models import Inquiry, SearchConversation, SearchMessage, SearchRequirements, ViewingRequest
from .serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    InquirySerializer,
    RecommendedAgentSerializer,
    SearchConversationSerializer,
    SearchRequirementsSerializer,
    ViewingRequestSerializer,
)
from .services import (
    AssistantConfigurationError,
    RequirementExtractionError,
    explain_matches,
    extract_requirements,
    find_covering_agents,
    has_search_criteria,
    requirement_values,
    save_requirements,
    search_houses,
)


class AssistantTestView(TemplateView):
    template_name = "assistant/chat.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["application_api_key"] = settings.API_KEY
        return context


def get_conversation_for_request(request, conversation_id):
    conversation = get_object_or_404(SearchConversation, pk=conversation_id)
    if conversation.user_id and conversation.user_id != getattr(request.user, "id", None):
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied("This conversation belongs to another user.")
    return conversation


class ChatView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=ChatRequestSerializer, responses={200: ChatResponseSerializer})
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation_id = serializer.validated_data.get("conversation_id")
        message = serializer.validated_data["message"]

        if conversation_id:
            conversation = get_conversation_for_request(request, conversation_id)
        else:
            conversation = SearchConversation.objects.create(
                user=request.user if request.user.is_authenticated else None
            )

        requirements, _ = SearchRequirements.objects.get_or_create(conversation=conversation)
        current = requirement_values(requirements)
        SearchMessage.objects.create(
            conversation=conversation, role=SearchMessage.Role.USER, content=message
        )
        history = list(
            conversation.messages.order_by("-created_at", "-id")[:10].values("role", "content")
        )
        history.reverse()

        try:
            extracted = extract_requirements(message, current, history=history)
        except AssistantConfigurationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except RequirementExtractionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        if extracted.intent == "property_search" and not extracted.location_explicitly_provided:
            extracted.location = None
        save_requirements(requirements, extracted)
        conversation.language = extracted.language
        if extracted.intent == "off_topic":
            conversation.consecutive_off_topic_count += 1
        else:
            conversation.consecutive_off_topic_count = 0
        conversation.save(
            update_fields=["language", "consecutive_off_topic_count", "updated_at"]
        )

        search_intent = extracted.intent in {"property_search", "search_refinement"}
        searched = search_intent and bool(requirements.location.strip()) and has_search_criteria(requirements)
        matches = list(search_houses(requirements)[:10]) if searched else []
        recommended_agents = (
            list(find_covering_agents(requirements.location))
            if searched and not matches and requirements.location
            else []
        )
        conversational_reply = extracted.assistant_reply
        if extracted.intent == "off_topic" and conversation.consecutive_off_topic_count >= 5:
            conversational_reply = (
                "Samahani, umeuliza maswali mengi yasiyohusiana na nyumba. Ninaweza kusaidia tu kuhusu nyumba na mali."
                if extracted.language == "sw"
                else "Sorry, you have asked too many unrelated questions. I can only help with houses and property."
            )
        if search_intent and not requirements.location.strip():
            conversational_reply = (
                "Tafadhali nitajie eneo unalotaka kutafuta nyumba—kwa mfano mkoa, wilaya, kata au mtaa."
                if extracted.language == "sw"
                else "Please tell me the location where you want a house—for example the region, district, ward, or street."
            )
        explanation = explain_matches(
            requirements,
            len(matches),
            extracted.language,
            searched=searched,
            conversational_reply=conversational_reply,
            agent_count=len(recommended_agents),
        )
        SearchMessage.objects.create(
            conversation=conversation,
            role=SearchMessage.Role.ASSISTANT,
            content=explanation.message,
        )

        payload = {
            "conversation_id": conversation.pk,
            "message": explanation.message,
            "requirements": SearchRequirementsSerializer(requirements).data,
            "matches": HouseSerializer(matches, many=True, context={"request": request}).data,
            "recommended_agents": RecommendedAgentSerializer(recommended_agents, many=True).data,
            "missing_requirements": explanation.missing_requirements,
        }
        return Response(payload)


class ConversationDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses={200: SearchConversationSerializer})
    def get(self, request, conversation_id):
        conversation = get_conversation_for_request(request, conversation_id)
        return Response(SearchConversationSerializer(conversation).data)


class InquiryCreateView(generics.CreateAPIView):
    queryset = Inquiry.objects.all()
    serializer_class = InquirySerializer
    permission_classes = [permissions.AllowAny]


class ViewingRequestCreateView(generics.CreateAPIView):
    queryset = ViewingRequest.objects.all()
    serializer_class = ViewingRequestSerializer
    permission_classes = [permissions.AllowAny]
