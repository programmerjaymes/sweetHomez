from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import exceptions, permissions, status, viewsets
from rest_framework.decorators import action
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import House, HouseMedia, HouseTranslation, NearbyFacility
from .permissions import IsAgentOwnerOrReadOnly
from .ai import create_house_draft, update_house_draft
from .serializers import HouseMediaSerializer, HouseSerializer, HouseTranslationSerializer, NearbyFacilitySerializer
from assistant.models import SearchConversation, SearchMessage
from users.limits import bundle_for_user, enforce_prompt_limits
from users.permissions import permission_required


houses_schema = extend_schema_view(
    list=extend_schema(tags=["Houses"]),
    retrieve=extend_schema(tags=["Houses"]),
    create=extend_schema(tags=["Houses"]),
    update=extend_schema(tags=["Houses"]),
    partial_update=extend_schema(tags=["Houses"]),
    destroy=extend_schema(tags=["Houses"]),
)


@houses_schema
class HouseViewSet(viewsets.ModelViewSet):
    """Public browsing; Agent-role users manage their own listings."""

    serializer_class = HouseSerializer
    permission_classes = [IsAgentOwnerOrReadOnly]

    def get_queryset(self):
        queryset = House.objects.select_related("agent", "agent__agent_profile").prefetch_related("media", "nearby_facilities", "translations")
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_available=True, moderation_status=House.ModerationStatus.APPROVED)
        elif not (
            self.request.user.has_perm("houses.view_house")
            or self.request.user.has_perm("houses.moderate_house")
        ):
            queryset = queryset.filter(Q(is_available=True, moderation_status=House.ModerationStatus.APPROVED) | Q(agent=self.request.user))
        if self.request.query_params.get("mine", "").lower() in {"1", "true", "yes"}:
            if not self.request.user.is_authenticated:
                return queryset.none()
            queryset = queryset.filter(agent=self.request.user)
        listing_type = self.request.query_params.get("listing_type")
        rooms = self.request.query_params.get("rooms") or self.request.query_params.get("bedrooms")
        region = self.request.query_params.get("region")
        if listing_type in House.ListingType.values:
            queryset = queryset.filter(listing_type=listing_type)
        if rooms and rooms.isdigit():
            queryset = queryset.filter(bedrooms=int(rooms))
        if region:
            queryset = queryset.filter(region__iexact=region)
        return queryset

    def perform_create(self, serializer):
        bundle = bundle_for_user(self.request.user)
        if bundle and bundle.max_houses is not None and House.objects.filter(agent=self.request.user).count() >= bundle.max_houses:
            raise exceptions.ValidationError({"detail": f"Your {bundle.name} bundle allows up to {bundle.max_houses} houses."})
        moderation_status = House.ModerationStatus.APPROVED if self.request.user.has_perm("houses.moderate_house") else House.ModerationStatus.PENDING
        serializer.save(agent=self.request.user, moderation_status=moderation_status)

    @action(detail=True, methods=["post"], permission_classes=[permission_required("houses.moderate_house")])
    def moderate(self, request, pk=None):
        house = self.get_object()
        decision = str(request.data.get("status", "")).lower()
        if decision not in {House.ModerationStatus.APPROVED, House.ModerationStatus.REJECTED}:
            return Response({"detail": "Choose approved or rejected."}, status=status.HTTP_400_BAD_REQUEST)
        house.moderation_status = decision
        house.moderated_at = timezone.now()
        house.moderated_by = request.user
        house.save(update_fields=["moderation_status", "moderated_at", "moderated_by", "updated_at"])
        return Response(self.get_serializer(house).data)


class AgentListingDraftView(APIView):
    permission_classes = [IsAgentOwnerOrReadOnly]

    def post(self, request):
        prompt = str(request.data.get("prompt", "")).strip()
        if not prompt:
            return Response({"detail": "Describe the property you want to publish."}, status=status.HTTP_400_BAD_REQUEST)
        language = "sw" if request.data.get("language") == "sw" else "en"
        conversation_id = request.data.get("conversation_id")
        if conversation_id:
            conversation = SearchConversation.objects.filter(pk=conversation_id, user=request.user, purpose=SearchConversation.Purpose.LISTING).first()
            if not conversation:
                return Response({"detail": "Listing conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            conversation = SearchConversation.objects.create(user=request.user, language=language, purpose=SearchConversation.Purpose.LISTING)
        enforce_prompt_limits(request.user, conversation)
        SearchMessage.objects.create(conversation=conversation, role=SearchMessage.Role.USER, content=prompt)
        current_draft = conversation.listing_draft or {}
        try:
            if request.data.get("conversational"):
                if request.data.get("start"):
                    guide = (
                        "Eleza taarifa za nyumba kwenye ujumbe mmoja: ikiwa ni ya kupangisha au kuuza, bei na kipindi cha malipo, eneo/anwani, mkoa, idadi ya vyumba vya kulala, vyumba vyenye choo ndani na vyoo vya nje. Pia sema Ndiyo au Hapana kwa sebule, jiko la ndani na jiko la nje. Picha na video fupi utaongeza kwenye fomu ya mwisho."
                        if language == "sw" else
                        "Describe the property in one message: whether it is for rent or sale, price and payment period, area/address, region, bedrooms, ensuite bedrooms, and outdoor toilets. Also answer Yes or No for a living room, indoor kitchen, and outdoor kitchen. Add photos and a short video on the final form."
                    )
                    SearchMessage.objects.create(conversation=conversation, role=SearchMessage.Role.ASSISTANT, content=guide)
                    return Response({"conversation_id": conversation.pk, "draft": current_draft, "missing_fields": [], "question": guide, "ready": False})
                draft = update_house_draft(prompt, current_draft, language)
                if draft.get("listing_type") == "sale":
                    draft["price_period"] = "one_time"
                if draft.get("outdoor_toilets") is not None and draft.get("ensuite_bedrooms") is not None:
                    draft["bathrooms"] = draft["outdoor_toilets"] + draft["ensuite_bedrooms"]
                if draft.get("has_indoor_kitchen") is not None and draft.get("has_outdoor_kitchen") is not None:
                    draft["kitchens"] = int(draft["has_indoor_kitchen"]) + int(draft["has_outdoor_kitchen"])
                required = ["listing_type", "price", "address", "region", "bedrooms", "ensuite_bedrooms", "outdoor_toilets", "has_living_room", "has_indoor_kitchen", "has_outdoor_kitchen"]
                if draft.get("listing_type") == "rent":
                    required.append("price_period")
                missing = [field for field in required if draft.get(field) is None or draft.get(field) == ""]
                questions = {
                    "listing_type": {"sw": "Nyumba hii ni ya kupangisha au kuuza?", "en": "Is this property for rent or for sale?"},
                    "price": {"sw": "Bei ya nyumba ni kiasi gani kwa TZS?", "en": "What is the property price in TZS?"},
                    "address": {"sw": "Nyumba ipo eneo au anwani gani?", "en": "What is the property's area or address?"},
                    "region": {"sw": "Nyumba ipo mkoa gani?", "en": "Which region is the property in?"},
                    "bedrooms": {"sw": "Vyumba vingapi vya kulala?", "en": "How many bedrooms are there?"},
                    "ensuite_bedrooms": {"sw": "Vyumba vingapi vina choo ndani?", "en": "How many bedrooms are ensuite?"},
                    "outdoor_toilets": {"sw": "Je, kuna choo cha nje? Kama kipo, ni vingapi?", "en": "Is there an outdoor toilet? If yes, how many?"},
                    "has_living_room": {"sw": "Je, kuna sebule? (Ndiyo/Hapana)", "en": "Is there a living room? (Yes/No)"},
                    "has_indoor_kitchen": {"sw": "Je, kuna jiko la ndani? (Ndiyo/Hapana)", "en": "Is there an indoor kitchen? (Yes/No)"},
                    "has_outdoor_kitchen": {"sw": "Je, kuna jiko la nje? (Ndiyo/Hapana)", "en": "Is there an outdoor kitchen? (Yes/No)"},
                    "price_period": {"sw": "Kodi hiyo ni kwa siku, wiki, mwezi au mwaka?", "en": "Is that rent daily, weekly, monthly, or annually?"},
                }
                question = None
                if missing:
                    heading = "Tafadhali ongeza taarifa hizi zinazokosekana:" if language == "sw" else "Please add these missing details:"
                    question = heading + "\n\n" + "\n".join(
                        f"{index}. {questions[field][language]}" for index, field in enumerate(missing, start=1)
                    )
                conversation.language = language
                conversation.listing_draft = draft
                conversation.listing_ready = not missing
                conversation.save(update_fields=["language", "listing_draft", "listing_ready", "updated_at"])
                reply = question or ("Taarifa muhimu zimekamilika. Hakiki rasimu kabla ya kuchapisha." if language == "sw" else "The required details are complete. Review the draft before publishing.")
                SearchMessage.objects.create(conversation=conversation, role=SearchMessage.Role.ASSISTANT, content=reply)
                return Response({"conversation_id": conversation.pk, "draft": draft, "missing_fields": missing, "question": question, "ready": not missing})
            draft = create_house_draft(prompt, language)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(draft.model_dump())


@houses_schema
class HouseMediaViewSet(viewsets.ModelViewSet):
    queryset = HouseMedia.objects.select_related("house", "house__agent")
    serializer_class = HouseMediaSerializer
    permission_classes = [IsAgentOwnerOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(house__is_available=True, house__moderation_status=House.ModerationStatus.APPROVED)
        house_id = self.request.query_params.get("house")
        return queryset.filter(house_id=house_id) if house_id else queryset

    def perform_create(self, serializer):
        house = serializer.validated_data["house"]
        if house.agent_id != self.request.user.id and not self.request.user.has_perm("houses.add_housemedia"):
            raise exceptions.PermissionDenied("You can add media only to your own listings.")
        bundle = bundle_for_user(self.request.user)
        media_type = serializer.validated_data["media_type"]
        if bundle and media_type == HouseMedia.MediaType.VIDEO and not bundle.video_upload_allowed:
            raise exceptions.ValidationError({"detail": f"Video uploads are not included in the {bundle.name} bundle."})
        if bundle and media_type == HouseMedia.MediaType.IMAGE and house.media.filter(media_type=HouseMedia.MediaType.IMAGE).count() >= bundle.max_photos_per_house:
            raise exceptions.ValidationError({"detail": f"The {bundle.name} bundle allows up to {bundle.max_photos_per_house} photos per house."})
        serializer.save()


@houses_schema
class HouseTranslationViewSet(viewsets.ModelViewSet):
    queryset = HouseTranslation.objects.select_related("house", "house__agent")
    serializer_class = HouseTranslationSerializer
    permission_classes = [IsAgentOwnerOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(house__is_available=True, house__moderation_status=House.ModerationStatus.APPROVED)
        house_id = self.request.query_params.get("house")
        return queryset.filter(house_id=house_id) if house_id else queryset

    def perform_create(self, serializer):
        house = serializer.validated_data["house"]
        if house.agent_id != self.request.user.id and not self.request.user.has_perm("houses.add_housetranslation"):
            raise exceptions.PermissionDenied("You can translate only your own listings.")
        serializer.save()


@houses_schema
class NearbyFacilityViewSet(viewsets.ModelViewSet):
    queryset = NearbyFacility.objects.select_related("house", "house__agent")
    serializer_class = NearbyFacilitySerializer
    permission_classes = [IsAgentOwnerOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(house__is_available=True, house__moderation_status=House.ModerationStatus.APPROVED)
        house_id = self.request.query_params.get("house")
        return queryset.filter(house_id=house_id) if house_id else queryset

    def perform_create(self, serializer):
        house = serializer.validated_data["house"]
        if house.agent_id != self.request.user.id and not self.request.user.has_perm("houses.add_nearbyfacility"):
            raise exceptions.PermissionDenied("You can add facilities only to your own listings.")
        serializer.save()
