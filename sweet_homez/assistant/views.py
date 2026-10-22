from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houses.models import House
from houses.serializers import HouseSerializer
from users.limits import enforce_prompt_limits

from .models import Inquiry, SearchConversation, SearchMessage, SearchRequirements, ViewingRequest
from .serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    ConversationHistorySerializer,
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


def get_conversation_for_request(request, conversation_id):
    conversation = get_object_or_404(SearchConversation, pk=conversation_id)
    if conversation.user_id and conversation.user_id != getattr(request.user, "id", None):
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied("This conversation belongs to another user.")
    return conversation


def get_remembered_houses(conversation):
    """Return the last displayed houses in the same order as their cards."""
    ids = conversation.last_recommended_house_ids or []
    houses = House.objects.filter(pk__in=ids).select_related(
        "agent", "agent__agent_profile", "region_record", "district_record", "ward_record", "street"
    ).prefetch_related("media", "nearby_facilities", "translations")
    by_id = {house.pk: house for house in houses}
    return [by_id[house_id] for house_id in ids if house_id in by_id]


def property_memory(houses):
    memory = []
    for position, house in enumerate(houses, start=1):
        profile = house.agent.agent_profile if hasattr(house.agent, "agent_profile") else None
        memory.append({
            "position": position,
            "id": house.pk,
            "title": house.title,
            "location": house.location,
            "listing_type": house.listing_type,
            "price_tzs": str(house.price),
            "price_period": house.price_period,
            "agent": {
                "name": house.agent.get_full_name() or house.agent.username,
                "agency": profile.agency_name if profile else "",
                "phone": profile.phone_number if profile else "",
                "whatsapp": profile.whatsapp_number if profile else "",
                "verified": profile.is_verified if profile else False,
            },
        })
    return memory


def is_agent_contact_question(message):
    normalized = message.casefold()
    return any(term in normalized for term in (
        "phone", "number", "contact", "call", "whatsapp",
        "namba", "simu", "mawasiliano", "wakala", "agent",
    ))


def is_greeting(message):
    normalized = " ".join(message.casefold().strip().split()).strip("!,.?")
    greetings = {"hi", "hello", "hey", "habari", "mambo", "hujambo", "salama", "good morning", "good afternoon", "good evening"}
    additions = {"sweetie", "dear", "rafiki", "friend", "sweethome", "sweethomez"}
    return normalized in greetings or any(
        normalized == f"{greeting} {addition}" for greeting in greetings for addition in additions
    )


def is_agent_own_listings_request(message):
    normalized = " ".join(message.casefold().split())
    ownership = any(term in normalized for term in (
        "nilizopost", "nilizochapisha", "nilizotangaza", "nyumba zangu", "matangazo yangu",
        "my houses", "my homes", "my properties", "my listings", "i posted", "i published",
    ))
    view_action = any(term in normalized for term in (
        "onyesha", "nionyeshe", "nataka kuona", "angalia", "show", "view", "see", "list",
    ))
    return ownership and view_action


def contact_reply(house, language):
    profile = house.agent.agent_profile if hasattr(house.agent, "agent_profile") else None
    phone = (profile.whatsapp_number or profile.phone_number) if profile else ""
    agency = profile.agency_name if profile and profile.agency_name else (
        house.agent.get_full_name() or house.agent.username
    )
    if language == "sw":
        if phone:
            return f"Namba ya wakala wa {house.title} ni {phone} ({agency})."
        return f"Samahani, namba ya wakala wa {house.title} haijawekwa bado."
    if phone:
        return f"The agent for {house.title} is {agency}. You can contact them at {phone}."
    return f"Sorry, the agent contact number for {house.title} is not available yet."


class ChatView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["AI Assistant"],
        request=ChatRequestSerializer,
        responses={200: ChatResponseSerializer},
    )
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation_id = serializer.validated_data.get("conversation_id")
        message = serializer.validated_data["message"]

        if conversation_id:
            conversation = get_conversation_for_request(request, conversation_id)
        else:
            enforce_prompt_limits(request.user)
            conversation = SearchConversation.objects.create(
                user=request.user if request.user.is_authenticated else None
            )
        enforce_prompt_limits(request.user, conversation)

        requirements, _ = SearchRequirements.objects.get_or_create(conversation=conversation)
        remembered_matches = get_remembered_houses(conversation)
        current = requirement_values(requirements)
        SearchMessage.objects.create(
            conversation=conversation, role=SearchMessage.Role.USER, content=message
        )
        if (
            request.user.is_authenticated
            and hasattr(request.user, "agent_profile")
            and is_agent_own_listings_request(message)
        ):
            language = "sw" if any(term in message.casefold() for term in ("nyumba", "nionyeshe", "onyesha", "matangazo", "nilizo")) else "en"
            matches = list(
                House.objects.filter(agent=request.user)
                .select_related("agent", "agent__agent_profile", "region_record", "district_record", "ward_record", "street")
                .prefetch_related("media", "nearby_facilities", "translations")[:30]
            )
            conversation.language = language
            conversation.last_recommended_house_ids = [house.pk for house in matches]
            conversation.save(update_fields=["language", "last_recommended_house_ids", "updated_at"])
            if language == "sw":
                reply = f"Hizi ni nyumba zako zilizopo. Una matangazo {len(matches)}." if matches else "Bado hujachapisha nyumba yoyote. Unaweza kuanza kwa kuchagua ‘Post nyumba’."
            else:
                reply = f"Here are your existing properties. You have {len(matches)} listings." if matches else "You have not published any properties yet. You can start by selecting ‘Post a house’."
            SearchMessage.objects.create(conversation=conversation, role=SearchMessage.Role.ASSISTANT, content=reply)
            return Response({
                "conversation_id": conversation.pk,
                "message": reply,
                "requirements": SearchRequirementsSerializer(requirements).data,
                "matches": HouseSerializer(matches, many=True, context={"request": request}).data,
                "recommended_agents": [],
                "missing_requirements": [],
            })
        history = list(
            conversation.messages.order_by("-created_at", "-id")[:10].values("role", "content")
        )
        history.reverse()

        try:
            extracted = extract_requirements(
                message,
                current,
                history=history,
                recent_properties=property_memory(remembered_matches),
            )
        except AssistantConfigurationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except RequirementExtractionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        if extracted.intent == "property_search" and not extracted.location_explicitly_provided:
            extracted.location = None
        # General questions and greetings must not erase the active house search.
        if extracted.intent in {"property_search", "search_refinement"}:
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
        if searched:
            conversation.last_recommended_house_ids = [house.pk for house in matches]
            conversation.save(update_fields=["last_recommended_house_ids", "updated_at"])
        recommended_agents = (
            list(find_covering_agents(requirements.location))
            if searched and not matches and requirements.location
            else []
        )
        conversational_reply = extracted.assistant_reply
        if (
            extracted.intent == "casual_conversation"
            and is_greeting(message)
            and request.user.is_authenticated
            and hasattr(request.user, "agent_profile")
        ):
            conversational_reply = (
                "Habari! Karibu tena SweetHomez. Kama wakala, naweza kukusaidia kupost nyumba mpya, kuendelea na rasimu ya tangazo, kusimamia taarifa za nyumba zako, au kujibu swali lolote kuhusu kazi yako ya uwakala. Ungependa kufanya nini?"
                if extracted.language == "sw" else
                "Hello! Welcome back to SweetHomez. As an agent, I can help you post a new property, continue a listing draft, manage your property information, or answer any agent-related question. What would you like to do?"
            )
        if (
            extracted.intent == "property_question"
            and is_agent_contact_question(message)
            and len(remembered_matches) == 1
        ):
            conversational_reply = contact_reply(remembered_matches[0], extracted.language)
            matches = remembered_matches
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

    @extend_schema(tags=["AI Assistant"], responses={200: SearchConversationSerializer})
    def get(self, request, conversation_id):
        conversation = get_conversation_for_request(request, conversation_id)
        return Response(SearchConversationSerializer(conversation).data)


class ConversationHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["AI Assistant"], responses={200: ConversationHistorySerializer(many=True)})
    def get(self, request):
        conversations = (
            SearchConversation.objects.filter(user=request.user, messages__isnull=False)
            .annotate(message_count=Count("messages"))
            .prefetch_related("messages")
            .order_by("-updated_at")[:30]
        )
        return Response(ConversationHistorySerializer(conversations, many=True).data)

    def delete(self, request):
        conversations = SearchConversation.objects.filter(user=request.user)
        deleted_count = conversations.count()
        conversations.delete()
        return Response({"deleted_count": deleted_count})


@extend_schema_view(post=extend_schema(tags=["AI Assistant"]))
class InquiryCreateView(generics.CreateAPIView):
    queryset = Inquiry.objects.all()
    serializer_class = InquirySerializer
    permission_classes = [permissions.AllowAny]


@extend_schema_view(post=extend_schema(tags=["AI Assistant"]))
class ViewingRequestCreateView(generics.CreateAPIView):
    queryset = ViewingRequest.objects.all()
    serializer_class = ViewingRequestSerializer
    permission_classes = [permissions.AllowAny]
