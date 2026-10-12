from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from houses.models import House, HouseMedia, HouseTranslation, NearbyFacility
from lookups.models import Ward
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
    {
        "title": "City apartment in Upanga",
        "description": "Bright city apartment near hospitals, offices, restaurants, and public transport.",
        "listing_type": House.ListingType.RENT, "rooms": 2,
        "price": Decimal("1400000.00"), "location": "Upanga, Dar es Salaam",
    },
    {
        "title": "Garden home in Mikocheni",
        "description": "A peaceful family residence with mature gardens, staff quarters, and secure parking.",
        "listing_type": House.ListingType.RENT, "rooms": 4,
        "price": Decimal("3200000.00"), "location": "Mikocheni, Dar es Salaam",
    },
    {
        "title": "Ocean-view apartment in Kawe",
        "description": "Modern apartment with a private balcony, ocean breeze, backup power, and security.",
        "listing_type": House.ListingType.RENT, "rooms": 3,
        "price": Decimal("2200000.00"), "location": "Kawe, Dar es Salaam",
    },
    {
        "title": "Starter apartment in Tabata",
        "description": "Affordable and convenient apartment with reliable water and easy road access.",
        "listing_type": House.ListingType.RENT, "rooms": 2,
        "price": Decimal("550000.00"), "location": "Tabata, Dar es Salaam",
    },
    {
        "title": "New duplex in Tegeta",
        "description": "Newly built duplex with ensuite bedrooms, a fitted kitchen, garden, and parking.",
        "listing_type": House.ListingType.SALE, "rooms": 4,
        "price": Decimal("295000000.00"), "location": "Tegeta, Dar es Salaam",
    },
    {
        "title": "Family bungalow in Bunju",
        "description": "A spacious standalone bungalow on a fenced plot with room for future expansion.",
        "listing_type": House.ListingType.SALE, "rooms": 3,
        "price": Decimal("165000000.00"), "location": "Bunju, Dar es Salaam",
    },
    {
        "title": "Lake-view villa in Mwanza",
        "description": "Elegant hillside villa overlooking Lake Victoria with terraces and landscaped grounds.",
        "listing_type": House.ListingType.SALE, "rooms": 5,
        "price": Decimal("540000000.00"), "location": "Capri Point, Mwanza",
    },
    {
        "title": "Modern townhouse in Mbeya",
        "description": "Contemporary townhouse in a quiet neighbourhood near schools and shopping.",
        "listing_type": House.ListingType.SALE, "rooms": 4,
        "price": Decimal("280000000.00"), "location": "Iyunga, Mbeya",
    },
    {
        "title": "Coastal retreat in Bagamoyo",
        "description": "Relaxed coastal home with a large veranda, tropical garden, and beach access.",
        "listing_type": House.ListingType.SALE, "rooms": 4,
        "price": Decimal("460000000.00"), "location": "Dunda, Bagamoyo",
    },
    {
        "title": "Mountain cottage in Moshi",
        "description": "Cosy furnished cottage with views of Kilimanjaro and a productive garden.",
        "listing_type": House.ListingType.RENT, "rooms": 2,
        "price": Decimal("1100000.00"), "location": "Shanty Town, Moshi",
    },
    {
        "title": "Executive home in Morogoro",
        "description": "Generous executive home with air conditioning, home office space, and security.",
        "listing_type": House.ListingType.RENT, "rooms": 4,
        "price": Decimal("1700000.00"), "location": "Forest Hill, Morogoro",
    },
    {
        "title": "Seaside apartment in Tanga",
        "description": "Comfortable apartment close to the waterfront, market, and city centre.",
        "listing_type": House.ListingType.RENT, "rooms": 2,
        "price": Decimal("800000.00"), "location": "Bombo, Tanga",
    },
    {
        "title": "Quiet home in Iringa",
        "description": "Well-kept family home in a calm area with a garden and covered parking.",
        "listing_type": House.ListingType.SALE, "rooms": 3,
        "price": Decimal("210000000.00"), "location": "Gangilonga, Iringa",
    },
    {
        "title": "Lake residence in Bukoba",
        "description": "A charming residence near Lake Victoria with spacious rooms and green surroundings.",
        "listing_type": House.ListingType.SALE, "rooms": 4,
        "price": Decimal("350000000.00"), "location": "Kashai, Bukoba",
    },
    {
        "title": "Staff apartment in Mtwara",
        "description": "Practical furnished apartment suited to professionals and long-term corporate stays.",
        "listing_type": House.ListingType.RENT, "rooms": 2,
        "price": Decimal("950000.00"), "location": "Shangani, Mtwara",
    },
    {
        "title": "Palm villa in Kigamboni",
        "description": "Private modern villa with a pool, four ensuite bedrooms, and quick beach access.",
        "listing_type": House.ListingType.RENT, "rooms": 4,
        "price": Decimal("4500000.00"), "location": "Kibada, Kigamboni",
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
        agent_profile, _ = AgentProfile.objects.update_or_create(
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
        agent_profile.coverage_wards.set(Ward.objects.filter(is_active=True))

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
            ("Upanga", "Ilala", "Dar es Salaam", "-6.806100", "39.285600"),
            ("Mikocheni", "Kinondoni", "Dar es Salaam", "-6.773200", "39.254900"),
            ("Kawe", "Kinondoni", "Dar es Salaam", "-6.732400", "39.240700"),
            ("Tabata", "Ilala", "Dar es Salaam", "-6.857100", "39.208400"),
            ("Tegeta", "Kinondoni", "Dar es Salaam", "-6.652900", "39.208700"),
            ("Bunju", "Kinondoni", "Dar es Salaam", "-6.638100", "39.180300"),
            ("Capri Point", "Nyamagana", "Mwanza", "-2.509100", "32.900600"),
            ("Iyunga", "Mbeya Urban", "Mbeya", "-8.923900", "33.445700"),
            ("Dunda", "Bagamoyo", "Pwani", "-6.442200", "38.904200"),
            ("Shanty Town", "Moshi Urban", "Kilimanjaro", "-3.331900", "37.329300"),
            ("Forest Hill", "Morogoro Urban", "Morogoro", "-6.822800", "37.661200"),
            ("Bombo", "Tanga Urban", "Tanga", "-5.061300", "39.108900"),
            ("Gangilonga", "Iringa Urban", "Iringa", "-7.769200", "35.700200"),
            ("Kashai", "Bukoba Urban", "Kagera", "-1.327100", "31.807500"),
            ("Shangani", "Mtwara Urban", "Mtwara", "-10.273200", "40.183800"),
            ("Kibada", "Kigamboni", "Dar es Salaam", "-6.896800", "39.309800"),
        ]
        for index, data in enumerate(HOUSES):
            title = data["title"]
            ward, district, region, latitude, longitude = coordinates[index]
            ward_record = Ward.objects.select_related("district__region").filter(name_en=ward).first()
            street = ward_record.localities.filter(locality_type__code="street").first() if ward_record else None
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
                    "parking_spaces": 1 + (index % 3),
                    "price": data["price"],
                    "price_period": House.PricePeriod.MONTHLY if listing_type == House.ListingType.RENT else House.PricePeriod.ONE_TIME,
                    "advance_payment_months": 3 if listing_type == House.ListingType.RENT else 1,
                    "agent_fee_type": House.AgentFeeType.FIXED,
                    "agent_fee_amount": Decimal("50000.00") if listing_type == House.ListingType.RENT else Decimal("500000.00"),
                    "address": f"Sample property, {ward}",
                    "ward": ward,
                    "district": district,
                    "region": region,
                    "region_record": ward_record.district.region if ward_record else None,
                    "district_record": ward_record.district if ward_record else None,
                    "ward_record": ward_record,
                    "street": street,
                    "latitude": Decimal(latitude),
                    "longitude": Decimal(longitude),
                    "electricity_available": True,
                    "water_available": True,
                    "security_available": True,
                    "furnished": index % 4 == 0,
                    "has_garden": data["rooms"] >= 3,
                    "has_balcony": data["rooms"] >= 2,
                    "has_air_conditioning": index % 3 == 0,
                    "has_internet": index % 5 != 0,
                    "is_available": True,
                    "availability_last_confirmed_at": timezone.now(),
                },
            )
            for image_index in range(4):
                HouseMedia.objects.update_or_create(
                    house=house,
                    media_type=HouseMedia.MediaType.IMAGE,
                    display_order=image_index,
                    defaults={
                        "external_url": f"https://picsum.photos/seed/sweethomez-{house.pk}-{image_index + 1}/1200/800",
                        "caption": f"{title} — view {image_index + 1}",
                        "is_primary": image_index == 0,
                    },
                )
            swahili_titles = [
                "Fleti ya kisasa Masaki", "Nyumba ya familia Mbezi Beach",
                "Fleti ya bei nafuu Sinza", "Nyumba ya vyumba vitatu Dodoma",
                "Jumba la kifahari Oyster Bay", "Nyumba mpya ya familia Kigamboni",
                "Nyumba ya makazi Arusha", "Nyumba ya ufukweni Zanzibar",
                "Fleti ya mjini Upanga", "Nyumba yenye bustani Mikocheni",
                "Fleti yenye mandhari ya bahari Kawe", "Fleti ya kuanzia Tabata",
                "Nyumba ya ghorofa Tegeta", "Nyumba ya familia Bunju",
                "Jumba lenye mandhari ya ziwa Mwanza", "Nyumba ya kisasa Mbeya",
                "Nyumba ya mapumziko Bagamoyo", "Nyumba ndogo ya mlima Moshi",
                "Nyumba ya kifahari Morogoro", "Fleti ya pwani Tanga",
                "Nyumba tulivu Iringa", "Nyumba ya ziwani Bukoba",
                "Fleti ya wafanyakazi Mtwara", "Jumba la minazi Kigamboni",
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
