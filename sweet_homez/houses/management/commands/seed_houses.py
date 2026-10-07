from decimal import Decimal

from django.core.management.base import BaseCommand

from houses.models import House, HouseMedia, HouseTranslation, NearbyFacility
from users.models import AgentProfile, Role, User


HOUSES = [
    {
        "title": "Modern apartment in Masaki",
        "description": "Furnished apartment near shops and the ocean, with parking and security.",
        "listing_type": House.ListingType.RENT,
        "rooms": 2,
        "price": Decimal("1800000.00"),
        "location": "Masaki, Dar es Salaam",
    },
    {
        "title": "Family house in Mbezi Beach",
        "description": "Spacious family home with a garden, parking, and a secure perimeter wall.",
        "listing_type": House.ListingType.RENT,
        "rooms": 4,
        "price": Decimal("2500000.00"),
        "location": "Mbezi Beach, Dar es Salaam",
    },
    {
        "title": "Affordable apartment in Sinza",
        "description": "Well-maintained apartment close to public transport and local markets.",
        "listing_type": House.ListingType.RENT,
        "rooms": 1,
        "price": Decimal("650000.00"),
        "location": "Sinza, Dar es Salaam",
    },
    {
        "title": "Three-bedroom home in Dodoma",
        "description": "Quiet residential property with reliable utilities and ample parking.",
        "listing_type": House.ListingType.RENT,
        "rooms": 3,
        "price": Decimal("900000.00"),
        "location": "Kisasa, Dodoma",
    },
    {
        "title": "Luxury villa in Oyster Bay",
        "description": "Premium villa with a swimming pool, landscaped garden, and ocean views.",
        "listing_type": House.ListingType.SALE,
        "rooms": 5,
        "price": Decimal("1250000000.00"),
        "location": "Oyster Bay, Dar es Salaam",
    },
    {
        "title": "New family home in Kigamboni",
        "description": "Recently completed home on a fenced plot near the main road.",
        "listing_type": House.ListingType.SALE,
        "rooms": 3,
        "price": Decimal("185000000.00"),
        "location": "Kigamboni, Dar es Salaam",
    },
    {
        "title": "Residential house in Arusha",
        "description": "Comfortable property with mountain views and easy access to the city centre.",
        "listing_type": House.ListingType.SALE,
        "rooms": 4,
        "price": Decimal("320000000.00"),
        "location": "Njiro, Arusha",
    },
    {
        "title": "Beach house in Zanzibar",
        "description": "Beachfront property suitable for a private home or holiday investment.",
        "listing_type": House.ListingType.SALE,
        "rooms": 6,
        "price": Decimal("780000000.00"),
        "location": "Paje, Zanzibar",
    },
]


class Command(BaseCommand):
    help = "Create or update sample house listings"

    def handle(self, *args, **options):
        agent_role, _ = Role.objects.get_or_create(
            name="Agent", defaults={"description": "Can publish and manage property listings"}
        )
        agent, created = User.objects.get_or_create(
            username="sample_agent",
            defaults={
                "email": "agent@sweethomez.local",
                "first_name": "Amina",
                "last_name": "Mashauri",
            },
        )
        if created:
            agent.set_unusable_password()
            agent.save(update_fields=["password"])
        agent.roles.add(agent_role)
        AgentProfile.objects.update_or_create(
            user=agent,
            defaults={
                "agency_name": "SweetHomez Realty",
                "phone_number": "+255 700 000 000",
                "whatsapp_number": "+255 700 000 000",
                "license_number": "SHZ-AGENT-001",
                "bio": "Verified residential property agent.",
                "is_verified": True,
            },
        )

        created_count = 0
        updated_count = 0
        coordinates = [
            ("Masaki", "Kinondoni", "Dar es Salaam", "-6.751600", "39.275300"),
            ("Mbezi Beach", "Kinondoni", "Dar es Salaam", "-6.703100", "39.225900"),
            ("Sinza", "Ubungo", "Dar es Salaam", "-6.780800", "39.218100"),
            ("Kisasa", "Dodoma Urban", "Dodoma", "-6.163000", "35.751600"),
            ("Oyster Bay", "Kinondoni", "Dar es Salaam", "-6.770200", "39.286700"),
            ("Kigamboni", "Kigamboni", "Dar es Salaam", "-6.823500", "39.317000"),
            ("Njiro", "Arusha Urban", "Arusha", "-3.407300", "36.717000"),
            ("Paje", "Kusini", "Zanzibar South", "-6.266600", "39.533300"),
        ]
        for index, data in enumerate(HOUSES):
            title = data["title"]
            ward, district, region, latitude, longitude = coordinates[index]
            listing_type = data["listing_type"]
            house, created = House.objects.update_or_create(
                title=title,
                defaults={
                    "agent": agent,
                    "description": data["description"],
                    "listing_type": listing_type,
                    "bedrooms": data["rooms"],
                    "ensuite_bedrooms": max(0, data["rooms"] - 2),
                    "bathrooms": max(1, data["rooms"] - 1),
                    "kitchens": 1,
                    "parking_spaces": 2,
                    "price": data["price"],
                    "price_period": House.PricePeriod.MONTHLY if listing_type == House.ListingType.RENT else House.PricePeriod.ONE_TIME,
                    "advance_payment_months": 3 if listing_type == House.ListingType.RENT else 1,
                    "agent_fee_type": House.AgentFeeType.FIXED,
                    "agent_fee_amount": Decimal("50000.00") if listing_type == House.ListingType.RENT else Decimal("500000.00"),
                    "address": f"Sample property, {ward}",
                    "ward": ward,
                    "district": district,
                    "region": region,
                    "latitude": Decimal(latitude),
                    "longitude": Decimal(longitude),
                    "electricity_available": True,
                    "water_available": True,
                    "security_available": True,
                    "furnished": index in (0, 4, 7),
                    "has_garden": data["rooms"] >= 3,
                    "has_balcony": data["rooms"] >= 2,
                    "has_air_conditioning": index in (0, 4, 7),
                    "has_internet": True,
                    "is_available": True,
                },
            )
            HouseMedia.objects.update_or_create(
                house=house,
                external_url=f"https://picsum.photos/seed/sweethomez-{house.pk}/1200/800",
                defaults={"media_type": HouseMedia.MediaType.IMAGE, "caption": title, "is_primary": True},
            )
            swahili_titles = [
                "Fleti ya kisasa Masaki", "Nyumba ya familia Mbezi Beach",
                "Fleti ya bei nafuu Sinza", "Nyumba ya vyumba vitatu Dodoma",
                "Jumba la kifahari Oyster Bay", "Nyumba mpya ya familia Kigamboni",
                "Nyumba ya makazi Arusha", "Nyumba ya ufukweni Zanzibar",
            ]
            HouseTranslation.objects.update_or_create(
                house=house,
                language_code=HouseTranslation.Language.ENGLISH,
                defaults={"title": title, "description": data["description"], "address": f"Sample property, {ward}"},
            )
            HouseTranslation.objects.update_or_create(
                house=house,
                language_code=HouseTranslation.Language.SWAHILI,
                defaults={
                    "title": swahili_titles[index],
                    "description": "Nyumba nzuri yenye huduma muhimu, sehemu ya maegesho na mazingira salama.",
                    "address": f"Nyumba ya mfano, {ward}",
                },
            )
            for facility_type, name, distance in (
                (NearbyFacility.FacilityType.ATM, "Nearby ATM", "0.80"),
                (NearbyFacility.FacilityType.PHARMACY, "Local pharmacy", "1.20"),
                (NearbyFacility.FacilityType.POLICE, "Police station", "2.50"),
                (NearbyFacility.FacilityType.FUEL_STATION, "Fuel station", "1.70"),
            ):
                NearbyFacility.objects.update_or_create(
                    house=house,
                    facility_type=facility_type,
                    defaults={"name": name, "distance_km": Decimal(distance)},
                )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"House seed complete: {created_count} created, {updated_count} updated."
            )
        )
