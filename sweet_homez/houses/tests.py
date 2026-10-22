from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import House, HouseTranslation
from assistant.models import SearchConversation
from users.models import Role, User


class PublicHouseApiTests(APITestCase):
    def setUp(self):
        self.client.credentials(HTTP_X_API_KEY=settings.API_KEY)
        role, _ = Role.objects.get_or_create(name="Agent")
        self.agent = User.objects.create_user("agent", "agent@example.com", "StrongPass!234")
        self.agent.roles.add(role)
        self.viewer = User.objects.create_user("viewer", "viewer@example.com", "StrongPass!234")
        self.rental = House.objects.create(
            agent=self.agent,
            title="City apartment",
            listing_type=House.ListingType.RENT,
            bedrooms=2,
            price=Decimal("750.00"),
            price_period=House.PricePeriod.MONTHLY,
            address="Masaki",
            region="Dar es Salaam",
        )
        House.objects.create(
            agent=self.agent,
            title="Family home",
            listing_type=House.ListingType.SALE,
            bedrooms=4,
            price=Decimal("150000.00"),
            address="Njiro",
            region="Arusha",
        )
        House.objects.create(
            agent=self.agent,
            title="Unavailable home",
            listing_type=House.ListingType.RENT,
            bedrooms=2,
            price=Decimal("500.00"),
            price_period=House.PricePeriod.MONTHLY,
            address="Kisasa",
            region="Dodoma",
            is_available=False,
        )
        HouseTranslation.objects.create(
            house=self.rental,
            language_code="sw",
            title="Fleti ya mjini",
            description="Fleti nzuri ya kupangisha.",
            address="Masaki",
        )

    def test_authenticated_user_can_list_available_houses(self):
        self.client.force_authenticate(self.viewer)
        response = self.client.get("/api/houses/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_authenticated_user_can_view_house_details(self):
        self.client.force_authenticate(self.viewer)
        response = self.client.get(f"/api/houses/{self.rental.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["listing_type"], "rent")
        self.assertEqual(response.data["rooms"], 2)
        self.assertEqual(response.data["agent"]["username"], "agent")

    def test_public_user_can_list_and_view_available_houses_without_login(self):
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_X_API_KEY=settings.API_KEY)

        listing = self.client.get("/api/houses/")
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["count"], 2)

        detail = self.client.get(f"/api/houses/{self.rental.pk}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data["id"], self.rental.pk)

    def test_list_can_filter_by_type_and_rooms(self):
        self.client.force_authenticate(self.viewer)
        response = self.client.get("/api/houses/?listing_type=rent&rooms=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.rental.pk)

    def test_agent_can_filter_to_only_their_own_houses(self):
        other_agent = User.objects.create_user("other-agent", "other@example.com", "StrongPass!234")
        other_agent.roles.add(Role.objects.get(name="Agent"))
        House.objects.create(agent=other_agent, title="Another agent home", listing_type="sale", price="900000", address="Mbezi", region="Dar es Salaam")
        self.client.force_authenticate(self.agent)
        response = self.client.get("/api/houses/?mine=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        self.assertTrue(all(item["agent"]["id"] == self.agent.id for item in response.data["results"]))

    def test_query_parameter_returns_swahili_translation(self):
        self.client.force_authenticate(self.viewer)
        response = self.client.get(f"/api/houses/{self.rental.pk}/?lang=sw")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["language"], "sw")
        self.assertEqual(response.data["title"], "Fleti ya mjini")
        self.assertEqual(response.data["listing_type_display"], "Ya kupangisha")

    def test_anonymous_user_cannot_create_house(self):
        response = self.client.post("/api/houses/", {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_house_read_requires_valid_api_key(self):
        self.client.credentials()
        response = self.client.get("/api/houses/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.credentials(HTTP_X_API_KEY="incorrect-key")
        response = self.client.get("/api/houses/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_agent_can_create_owned_house(self):
        self.client.force_authenticate(self.agent)
        response = self.client.post("/api/houses/", {
            "title": "Agent listing", "listing_type": "rent", "price": "300000.00",
            "price_period": "monthly", "advance_payment_months": 3,
            "address": "Mikocheni", "region": "Dar es Salaam", "bedrooms": 2,
            "ensuite_bedrooms": 1, "bathrooms": 2, "kitchens": 1,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(House.objects.get(title="Agent listing").agent, self.agent)

    def test_agent_can_create_house_without_entering_a_title(self):
        self.client.force_authenticate(self.agent)
        response = self.client.post("/api/houses/", {
            "listing_type": "rent", "price": "450000.00", "price_period": "monthly",
            "address": "Mikocheni", "region": "Dar es Salaam", "bedrooms": 2,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "House for rent in Mikocheni")

    @patch("houses.views.update_house_draft")
    def test_agent_listing_chat_returns_the_next_missing_question(self, update_draft):
        self.client.force_authenticate(self.agent)
        update_draft.return_value = {"listing_type": "rent", "address": "Masaki", "region": "Dar es Salaam"}

        response = self.client.post("/api/agent/listing-draft/", {
            "prompt": "Ni ya kupangisha Masaki",
            "language": "sw",
            "conversational": True,
            "draft": {},
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["ready"])
        self.assertEqual(response.data["missing_fields"][0], "price")
        self.assertIn("Tafadhali ongeza taarifa hizi zinazokosekana:", response.data["question"])
        self.assertIn("1. Bei ya nyumba ni kiasi gani kwa TZS?", response.data["question"])
        self.assertIn("Vyumba vingapi vya kulala?", response.data["question"])
        self.assertIn("Vyumba vingapi vina choo ndani?", response.data["question"])
        self.assertIn("Je, kuna jiko la ndani?", response.data["question"])
        self.assertIn("Je, kuna jiko la nje?", response.data["question"])
        self.assertIn("Je, kuna choo cha nje?", response.data["question"])
        self.assertIn("Je, kuna sebule?", response.data["question"])
        conversation = SearchConversation.objects.get(pk=response.data["conversation_id"])
        self.assertEqual(conversation.purpose, SearchConversation.Purpose.LISTING)
        self.assertEqual(conversation.messages.count(), 2)
        self.assertEqual(conversation.listing_draft["address"], "Masaki")
