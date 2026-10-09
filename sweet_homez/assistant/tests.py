from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from houses.models import House, HouseMedia
from lookups.models import District, Region, Ward
from users.models import AgentProfile, User

from .models import Inquiry, SearchConversation, SearchRequirements, ViewingRequest
from .schemas import ExtractedRequirements


class AssistantApiTests(APITestCase):
    def setUp(self):
        self.client.credentials(HTTP_X_API_KEY=settings.API_KEY)
        self.agent = User.objects.create_user("assistant-agent", "assistant-agent@example.com", "pass")
        self.match = House.objects.create(
            agent=self.agent,
            title="Mbezi three-bedroom home",
            listing_type=House.ListingType.RENT,
            price=Decimal("750000"),
            price_period=House.PricePeriod.MONTHLY,
            address="Mbezi",
            ward="Mbezi",
            district="Kinondoni",
            region="Dar es Salaam",
            bedrooms=3,
            parking_spaces=1,
            water_available=True,
        )
        HouseMedia.objects.create(
            house=self.match,
            media_type=HouseMedia.MediaType.IMAGE,
            external_url="https://example.com/mbezi-house.jpg",
            is_primary=True,
        )
        House.objects.create(
            agent=self.agent,
            title="Expensive Mbezi home",
            listing_type=House.ListingType.RENT,
            price=Decimal("1200000"),
            price_period=House.PricePeriod.MONTHLY,
            address="Mbezi",
            ward="Mbezi",
            district="Kinondoni",
            region="Dar es Salaam",
            bedrooms=3,
            parking_spaces=1,
            water_available=True,
        )

    @patch("assistant.views.extract_requirements")
    def test_chat_extracts_requirements_and_returns_database_matches(self, extract):
        extract.return_value = ExtractedRequirements(
            intent="property_search",
            assistant_reply="I’ll search those requirements.",
            location_explicitly_provided=True,
            language="en",
            listing_type="rent",
            location="Mbezi",
            maximum_price=800000,
            price_period="monthly",
            bedrooms=3,
            minimum_parking_spaces=1,
            water_required=True,
        )

        response = self.client.post("/api/assistant/chat/", {
            "message": "I need a three-bedroom house in Mbezi below TSh 800,000 with parking and water."
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["matches"]), 1)
        self.assertEqual(response.data["matches"][0]["id"], self.match.pk)
        self.assertEqual(
            response.data["matches"][0]["media"][0]["external_url"],
            "https://example.com/mbezi-house.jpg",
        )
        self.assertEqual(response.data["requirements"]["bedrooms"], 3)
        self.assertTrue(SearchConversation.objects.filter(pk=response.data["conversation_id"]).exists())

    @patch("assistant.views.extract_requirements")
    def test_follow_up_reuses_conversation(self, extract):
        conversation = SearchConversation.objects.create()
        extract.return_value = ExtractedRequirements(
            intent="search_refinement", language="en", location="Mbezi", bedrooms=3
        )
        response = self.client.post("/api/assistant/chat/", {
            "conversation_id": str(conversation.pk), "message": "Make that three bedrooms."
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data["conversation_id"]), str(conversation.pk))

    @patch("assistant.views.extract_requirements")
    def test_greeting_asks_for_requirements_without_returning_every_house(self, extract):
        extract.return_value = ExtractedRequirements(
            intent="casual_conversation",
            assistant_reply="Hello! How can I help you find a home today?",
            language="en",
        )

        response = self.client.post(
            "/api/assistant/chat/", {"message": "hello"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["matches"], [])
        self.assertEqual(response.data["message"], "Hello! How can I help you find a home today?")

    @patch("assistant.views.extract_requirements")
    def test_property_question_gets_conversational_answer_without_search(self, extract):
        extract.return_value = ExtractedRequirements(
            intent="property_question",
            assistant_reply="Advance rent is the rent paid before your tenancy period begins.",
            language="en",
        )
        response = self.client.post(
            "/api/assistant/chat/", {"message": "What is advance rent?"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["matches"], [])
        self.assertIn("Advance rent", response.data["message"])

    @patch("assistant.views.extract_requirements")
    def test_no_house_match_returns_verified_agent_covering_location(self, extract):
        region = Region.objects.create(code="DSM", name_en="Dar es Salaam")
        district = District.objects.create(region=region, code="KIN", name_en="Kinondoni")
        ward = Ward.objects.create(district=district, code="MBZ", name_en="Mbezi Beach")
        covering_user = User.objects.create_user(
            "covering-agent", "covering-agent@example.com", "pass"
        )
        profile = AgentProfile.objects.create(
            user=covering_user,
            agency_name="Mbezi Property Help",
            phone_number="+255700000003",
            is_verified=True,
        )
        profile.coverage_wards.add(ward)
        extract.return_value = ExtractedRequirements(
            intent="property_search",
            assistant_reply="I’ll check that area.",
            location_explicitly_provided=True,
            language="en",
            listing_type="rent",
            location="Mbezi",
            maximum_price=100,
        )

        response = self.client.post(
            "/api/assistant/chat/",
            {"message": "Find rent in Mbezi below TSh 100"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["matches"], [])
        self.assertEqual(len(response.data["recommended_agents"]), 1)
        self.assertEqual(
            response.data["recommended_agents"][0]["phone_number"], "+255700000003"
        )

    @patch("assistant.views.extract_requirements")
    def test_price_only_search_asks_for_location_and_does_not_search(self, extract):
        extract.return_value = ExtractedRequirements(
            intent="property_search",
            assistant_reply="Nitajie eneo unalopendelea.",
            language="sw",
            listing_type="rent",
            minimum_price=200000,
            maximum_price=300000,
        )
        response = self.client.post(
            "/api/assistant/chat/",
            {"message": "Nataka nyumba ya 200,000 hadi 300,000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["matches"], [])
        self.assertEqual(response.data["requirements"]["location"], "")
        self.assertIn("Tafadhali nitajie eneo", response.data["message"])

    @patch("assistant.views.extract_requirements")
    def test_new_search_can_clear_location_from_previous_search(self, extract):
        conversation = SearchConversation.objects.create()
        SearchRequirements.objects.create(conversation=conversation, location="Mbezi")
        extract.return_value = ExtractedRequirements(
            intent="property_search", language="sw", minimum_price=200000, maximum_price=300000
        )
        response = self.client.post(
            "/api/assistant/chat/",
            {"conversation_id": str(conversation.pk), "message": "Nataka nyumba ya 200,000 hadi 300,000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["requirements"]["location"], "")

    @patch("assistant.views.extract_requirements")
    def test_backend_rejects_location_inherited_by_model_for_new_search(self, extract):
        conversation = SearchConversation.objects.create()
        SearchRequirements.objects.create(conversation=conversation, location="Mbezi")
        extract.return_value = ExtractedRequirements(
            intent="property_search",
            language="sw",
            location="Mbezi",
            location_explicitly_provided=False,
            minimum_price=200000,
            maximum_price=600000,
        )
        response = self.client.post(
            "/api/assistant/chat/",
            {
                "conversation_id": str(conversation.pk),
                "message": "Nataka nyumba ya 200,000 hadi 600,000",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["requirements"]["location"], "")
        self.assertEqual(response.data["matches"], [])

    @patch("assistant.views.extract_requirements")
    def test_fifth_consecutive_off_topic_question_gets_short_warning(self, extract):
        conversation = SearchConversation.objects.create(consecutive_off_topic_count=4)
        extract.return_value = ExtractedRequirements(
            intent="off_topic",
            assistant_reply="I focus on helping you find property.",
            language="en",
        )
        response = self.client.post(
            "/api/assistant/chat/",
            {"conversation_id": str(conversation.pk), "message": "Tell me another unrelated thing"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"],
            "Sorry, you have asked too many unrelated questions. I can only help with houses and property.",
        )
        conversation.refresh_from_db()
        self.assertEqual(conversation.consecutive_off_topic_count, 5)

    @patch("assistant.views.extract_requirements")
    def test_relevant_question_resets_off_topic_counter(self, extract):
        conversation = SearchConversation.objects.create(consecutive_off_topic_count=4)
        extract.return_value = ExtractedRequirements(
            intent="property_question",
            assistant_reply="Advance rent is paid before the tenancy period.",
            language="en",
        )
        response = self.client.post(
            "/api/assistant/chat/",
            {"conversation_id": str(conversation.pk), "message": "What is advance rent?"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        conversation.refresh_from_db()
        self.assertEqual(conversation.consecutive_off_topic_count, 0)

    def test_api_key_is_required(self):
        self.client.credentials()
        response = self.client.post("/api/assistant/chat/", {"message": "Find a house"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(OPENAI_API_KEY="")
    def test_missing_openai_key_returns_service_unavailable(self):
        response = self.client.post("/api/assistant/chat/", {"message": "Find a house"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_customer_can_create_inquiry_and_viewing(self):
        inquiry = self.client.post("/api/assistant/inquiries/", {
            "house": self.match.pk,
            "customer_name": "Asha",
            "phone_number": "+255700000001",
            "message": "Please call me.",
        }, format="json")
        self.assertEqual(inquiry.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Inquiry.objects.count(), 1)

        viewing = self.client.post("/api/assistant/viewings/", {
            "house": self.match.pk,
            "customer_name": "Asha",
            "phone_number": "+255700000001",
            "preferred_at": "2026-10-12T10:00:00Z",
        }, format="json")
        self.assertEqual(viewing.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ViewingRequest.objects.count(), 1)

    def test_local_test_page_includes_configured_application_key(self):
        response = self.client.get("/assistant/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, settings.API_KEY)
