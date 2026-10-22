from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from lookups.models import District, Locality, LookupCategory, LookupValue, Region, Ward


TABLES = {"regions", "districts", "wards", "streets"}


def mysql_rows(values_sql):
    """Parse the VALUES portion of a mysqldump INSERT without executing SQL."""
    row, value, rows = [], [], []
    quoted = escaped = False
    in_row = False
    for char in values_sql:
        if not in_row:
            if char == "(":
                in_row = True
                row, value = [], []
            continue
        if quoted:
            if escaped:
                translations = {"n": "\n", "r": "\r", "t": "\t", "0": "\0"}
                value.append(translations.get(char, char))
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "'":
                quoted = False
            else:
                value.append(char)
            continue
        if char == "'":
            quoted = True
        elif char == ",":
            raw = "".join(value).strip()
            row.append(None if raw.upper() == "NULL" else raw)
            value = []
        elif char == ")":
            raw = "".join(value).strip()
            row.append(None if raw.upper() == "NULL" else raw)
            rows.append(row)
            row, value, in_row = [], [], False
        else:
            value.append(char)
    return rows


def read_dump(path):
    found = {}
    with path.open("r", encoding="utf-8") as dump:
        for line in dump:
            if not line.startswith("INSERT INTO `"):
                continue
            table = line.split("`", 2)[1]
            if table not in TABLES:
                continue
            marker = " VALUES "
            if marker not in line:
                raise CommandError(f"Unsupported INSERT format for {table}.")
            values = line.split(marker, 1)[1].rstrip().removesuffix(";")
            found.setdefault(table, []).extend(mysql_rows(values))
    missing = TABLES - found.keys()
    if missing:
        raise CommandError(f"Backup is missing: {', '.join(sorted(missing))}.")
    return found


def preferred_name(primary, tamisemi):
    return str(tamisemi or primary or "").strip()


class Command(BaseCommand):
    help = "Synchronize Tanzania regions, districts, wards and streets from the supplied MySQL dump."

    def add_arguments(self, parser):
        parser.add_argument("sql_file", type=Path)
        parser.add_argument("--dry-run", action="store_true", help="Parse and validate the backup without changing the database.")

    def handle(self, *args, **options):
        path = options["sql_file"].expanduser().resolve()
        if not path.is_file():
            raise CommandError(f"SQL backup not found: {path}")

        data = read_dump(path)
        counts = {name: len(rows) for name, rows in data.items()}
        self.stdout.write(
            "Parsed " + ", ".join(f"{counts[name]:,} {name}" for name in ("regions", "districts", "wards", "streets"))
        )
        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Backup parsed successfully; no database changes were made."))
            return

        with transaction.atomic():
            category, _ = LookupCategory.objects.update_or_create(
                code="locality_type",
                defaults={"name_en": "Locality type", "name_sw": "Aina ya eneo", "is_active": True},
            )
            street_type, _ = LookupValue.objects.update_or_create(
                category=category,
                code="street",
                defaults={"name_en": "Street", "name_sw": "Mtaa", "is_active": True},
            )

            regions = {}
            for row in data["regions"]:
                code, name = row[8], preferred_name(row[9], row[10])
                if code and name:
                    regions[code] = Region(code=code, name_en=name, name_sw=name, country_code="TZ", is_active=True)
            Region.objects.bulk_create(
                regions.values(), batch_size=1000, update_conflicts=True,
                unique_fields=["code"], update_fields=["name_en", "name_sw", "country_code", "is_active"],
            )
            region_map = Region.objects.in_bulk(regions, field_name="code")

            districts, missing_regions = {}, set()
            for row in data["districts"]:
                region_code, code, name = row[1], row[2], preferred_name(row[3], row[4])
                region = region_map.get(region_code)
                if not region:
                    missing_regions.add(region_code)
                elif code and name:
                    districts[code] = District(code=code, region=region, name_en=name, name_sw=name, is_active=True)
            if missing_regions:
                raise CommandError(f"Districts reference unknown regions: {', '.join(sorted(missing_regions))}")
            District.objects.bulk_create(
                districts.values(), batch_size=1000, update_conflicts=True,
                unique_fields=["code"], update_fields=["region", "name_en", "name_sw", "is_active"],
            )
            district_map = District.objects.in_bulk(districts, field_name="code")

            wards, missing_districts = {}, set()
            for row in data["wards"]:
                district_code, code, name = row[1], row[2], preferred_name(row[3], row[4])
                district = district_map.get(district_code)
                if not district:
                    missing_districts.add(district_code)
                elif code and name:
                    wards[code] = Ward(code=code, district=district, name_en=name, name_sw=name, is_active=True)
            if missing_districts:
                raise CommandError(f"Wards reference unknown districts: {', '.join(sorted(missing_districts))}")
            Ward.objects.bulk_create(
                wards.values(), batch_size=2000, update_conflicts=True,
                unique_fields=["code"], update_fields=["district", "name_en", "name_sw", "is_active"],
            )
            ward_map = Ward.objects.in_bulk(wards, field_name="code")

            streets, missing_wards = {}, set()
            for row in data["streets"]:
                code, name, ward_code = row[1], preferred_name(row[2], row[3]), row[9]
                ward = ward_map.get(ward_code)
                if not ward:
                    missing_wards.add(ward_code)
                elif code and name:
                    streets[code] = Locality(
                        code=code, ward=ward, locality_type=street_type,
                        name_en=name, name_sw=name, is_active=True,
                    )
            if missing_wards:
                sample = ", ".join(sorted(str(code) for code in missing_wards)[:10])
                raise CommandError(f"Streets reference {len(missing_wards)} unknown wards (sample: {sample}).")
            Locality.objects.bulk_create(
                streets.values(), batch_size=3000, update_conflicts=True,
                unique_fields=["code"], update_fields=["ward", "locality_type", "name_en", "name_sw", "is_active"],
            )

        self.stdout.write(self.style.SUCCESS(
            f"Administrative areas synchronized: {len(regions):,} regions, {len(districts):,} districts, "
            f"{len(wards):,} wards and {len(streets):,} streets."
        ))
