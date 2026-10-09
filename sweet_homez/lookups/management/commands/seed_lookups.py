from django.core.management.base import BaseCommand

from lookups.models import District, Locality, LookupCategory, LookupValue, Region, Ward


LOOKUPS = {
    "listing_type": ("Listing type", "Aina ya tangazo", [("rent", "For rent", "Ya kupangisha"), ("sale", "For sale", "Ya kuuzwa")]),
    "price_period": ("Price period", "Kipindi cha bei", [("one_time", "One-time", "Mara moja"), ("daily", "Daily", "Kwa siku"), ("weekly", "Weekly", "Kwa wiki"), ("monthly", "Monthly", "Kwa mwezi"), ("quarterly", "Three months", "Miezi mitatu"), ("semiannual", "Six months", "Miezi sita"), ("annual", "Annual", "Kwa mwaka")]),
    "agent_fee_type": ("Agent fee type", "Aina ya ada ya wakala", [("none", "No fee", "Hakuna ada"), ("fixed", "Fixed amount", "Kiasi maalum"), ("percentage", "Percentage", "Asilimia")]),
    "media_type": ("Media type", "Aina ya media", [("image", "Image", "Picha"), ("video", "Video", "Video")]),
    "facility_type": ("Nearby facility", "Huduma ya karibu", [("atm", "ATM", "ATM"), ("police", "Police station", "Kituo cha polisi"), ("gym", "Gym", "Ukumbi wa mazoezi"), ("fuel_station", "Fuel station", "Kituo cha mafuta"), ("pharmacy", "Pharmacy", "Duka la dawa"), ("hospital", "Hospital or clinic", "Hospitali au kliniki"), ("school", "School", "Shule"), ("market", "Market", "Soko"), ("public_transport", "Public transport", "Usafiri wa umma"), ("restaurant", "Restaurant", "Mkahawa"), ("other", "Other", "Nyingine")]),
    "locality_type": ("Locality type", "Aina ya eneo", [("village", "Village", "Kijiji"), ("street", "Street", "Mtaa")]),
}

PLACES = [
    ("DSM", "Dar es Salaam", "Dar es Salaam", [("KIN", "Kinondoni", [("MAS", "Masaki"), ("MBZ", "Mbezi Beach"), ("OYB", "Oyster Bay")]), ("UBG", "Ubungo", [("SNZ", "Sinza")]), ("KGM", "Kigamboni", [("KGM-W", "Kigamboni")])]),
    ("DOM", "Dodoma", "Dodoma", [("DOD-U", "Dodoma Urban", [("KSS", "Kisasa")])]),
    ("ARU", "Arusha", "Arusha", [("ARU-U", "Arusha Urban", [("NJR", "Njiro")])]),
    ("ZAN-S", "Zanzibar South", "Kusini Unguja", [("KUS", "Kusini", [("PAJ", "Paje")])]),
]


class Command(BaseCommand):
    help = "Create or update property and geographic lookup values"

    def handle(self, *args, **options):
        for category_code, (name_en, name_sw, values) in LOOKUPS.items():
            category, _ = LookupCategory.objects.update_or_create(code=category_code, defaults={"name_en": name_en, "name_sw": name_sw, "is_active": True})
            for position, (code, value_en, value_sw) in enumerate(values):
                LookupValue.objects.update_or_create(category=category, code=code, defaults={"name_en": value_en, "name_sw": value_sw, "sort_order": position, "is_active": True})

        locality_type = LookupValue.objects.get(category__code="locality_type", code="street")
        for region_code, region_en, region_sw, districts in PLACES:
            region, _ = Region.objects.update_or_create(code=region_code, defaults={"name_en": region_en, "name_sw": region_sw})
            for district_code, district_name, wards in districts:
                district, _ = District.objects.update_or_create(code=district_code, defaults={"region": region, "name_en": district_name, "name_sw": district_name})
                for ward_code, ward_name in wards:
                    ward, _ = Ward.objects.update_or_create(code=ward_code, defaults={"district": district, "name_en": ward_name, "name_sw": ward_name})
                    Locality.objects.update_or_create(code=f"{ward_code}-ST", defaults={"ward": ward, "locality_type": locality_type, "name_en": f"{ward_name} Street", "name_sw": f"Mtaa wa {ward_name}"})

        self.stdout.write(self.style.SUCCESS("Lookup seed complete."))
