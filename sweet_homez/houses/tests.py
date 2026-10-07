from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from .models import House, HouseTranslation
from users.models import Role, User


class PublicHouseApiTests(APITestCase):
    def setUp(self):
        role, _ = Role.objects.get_or_create(name="Agent")
        self.agent = User.objects.create_user("agent", "agent@example.com", "StrongPass!234")
        self.agent.roles.add(role)
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

    def test_anonymous_user_can_list_available_houses(self):
        response = self.client.get("/api/houses/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_anonymous_user_can_view_house_details(self):
        response = self.client.get(f"/api/houses/{self.rental.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["listing_type"], "rent")
        self.assertEqual(response.data["rooms"], 2)
        self.assertEqual(response.data["agent"]["username"], "agent")

    def test_list_can_filter_by_type_and_rooms(self):
        response = self.client.get("/api/houses/?listing_type=rent&rooms=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.rental.pk)

    def test_query_parameter_returns_swahili_translation(self):
        response = self.client.get(f"/api/houses/{self.rental.pk}/?lang=sw")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["language"], "sw")
        self.assertEqual(response.data["title"], "Fleti ya mjini")
        self.assertEqual(response.data["listing_type_display"], "Ya kupangisha")

    def test_anonymous_user_cannot_create_house(self):
        response = self.client.post("/api/houses/", {})
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
