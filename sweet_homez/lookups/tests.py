from django.conf import settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import District, LookupCategory, LookupValue, Region
from users.models import User


class PublicLookupApiTests(APITestCase):
    def setUp(self):
        self.client.credentials(HTTP_X_API_KEY=settings.API_KEY)
        self.user = User.objects.create_user("lookup-user", "lookup@example.com", "StrongPass!234")
        category = LookupCategory.objects.create(code="listing_type", name_en="Listing type", name_sw="Aina ya tangazo")
        LookupValue.objects.create(category=category, code="rent", name_en="For rent", name_sw="Ya kupangisha")
        self.region = Region.objects.create(code="DSM", name_en="Dar es Salaam", name_sw="Dar es Salaam")
        District.objects.create(region=self.region, code="KIN", name_en="Kinondoni", name_sw="Kinondoni")

    def test_lookups_require_authentication_and_are_localized(self):
        unauthenticated = self.client.get("/api/lookup-values/?category=listing_type&lang=sw")
        self.assertEqual(unauthenticated.status_code, status.HTTP_401_UNAUTHORIZED)
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/lookup-values/?category=listing_type&lang=sw")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["name"], "Ya kupangisha")

    def test_districts_filter_by_region(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/districts/?region={self.region.pk}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
