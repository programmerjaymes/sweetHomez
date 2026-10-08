from decimal import Decimal

from django.conf import settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import House, HouseTranslation
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

    def test_house_read_without_api_key_is_rejected(self):
        self.client.credentials()
        response = self.client.get("/api/houses/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json()["detail"], "A valid X-API-Key header is required.")

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
