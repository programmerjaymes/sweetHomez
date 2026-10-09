import json
from dataclasses import dataclass

from django.conf import settings
from django.db.models import Q, QuerySet

from houses.models import House
from users.models import User

from .models import SearchRequirements
from .schemas import ExtractedRequirements, REQUIREMENT_FIELDS


ASSISTANT_INSTRUCTIONS = """
You are Sweet Homez, a bilingual Tanzanian property-search assistant.
Hold a natural, friendly conversation in English or Kiswahili and classify the intent.
You may answer greetings, thanks, and general questions about finding, renting, buying,
viewing, and evaluating homes. For unrelated topics, briefly and politely redirect the
customer to property matters. Never claim to be a human and never invent listings,
prices, availability, providers, or search results. Your assistant_reply must not claim
that a database search has run; the application adds verified match information later.
When information is missing for a requested search, ask one concise follow-up question.

Also extract the customer's complete, current search requirements.
The input includes the saved requirements. If intent is search_refinement, preserve
requirements the customer did not change and replace the ones they changed. If intent is
property_search, treat it as a new independent search: do not carry forward saved values
that are absent from the newest request. Set those absent values to null. Never invent a
location or any other value. Location is mandatory for searching; when a property search
does not state a location, leave location null, set location_explicitly_provided to false,
and politely ask which area they prefer. Set location_explicitly_provided to true only
when the newest customer message itself names an area; an area appearing only in saved
requirements or conversation history does not count.
Interpret amounts as Tanzanian shillings unless the customer clearly specifies otherwise.
Interpret 'per month' as monthly and ordinary home-search requests as rent when the wording
clearly discusses rent or monthly payments. Normalize facility names to the allowed values.
Return only the structured result.
""".strip()


class AssistantConfigurationError(RuntimeError):
    pass


class RequirementExtractionError(RuntimeError):
    pass


def requirement_values(requirements: SearchRequirements | None) -> dict:
    if requirements is None:
        return {field: None for field in REQUIREMENT_FIELDS}
    values = {}
    for field in REQUIREMENT_FIELDS:
        value = getattr(requirements, field)
        if hasattr(value, "as_tuple"):
            value = float(value)
        values[field] = None if value == "" else value
    return values


def extract_requirements(
    message: str, current: dict, history: list[dict[str, str]] | None = None
) -> ExtractedRequirements:
    if not settings.OPENAI_API_KEY:
        raise AssistantConfigurationError("OPENAI_API_KEY is not configured.")

    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        response = client.responses.parse(
            model=settings.OPENAI_MODEL,
            reasoning={"effort": "low"},
            instructions=ASSISTANT_INSTRUCTIONS,
            input=(
                f"Saved requirements:\n{json.dumps(current, ensure_ascii=False)}\n\n"
                f"Recent conversation:\n{json.dumps(history or [], ensure_ascii=False)}\n\n"
                f"Newest customer message:\n{message}"
            ),
            text_format=ExtractedRequirements,
            store=False,
        )
    except Exception as exc:
        if getattr(exc, "code", "") == "credit_balance_exhausted":
            raise RequirementExtractionError(
                "The OpenAI project has no API credits. Add credits in the OpenAI billing settings."
            ) from exc
        if exc.__class__.__name__ == "AuthenticationError":
            raise RequirementExtractionError(
                "The configured OpenAI API key was rejected. Check OPENAI_API_KEY."
            ) from exc
        raise RequirementExtractionError("The property assistant could not understand the request.") from exc
    if response.output_parsed is None:
        raise RequirementExtractionError("The property assistant returned no search requirements.")
    return response.output_parsed


def save_requirements(instance: SearchRequirements, extracted: ExtractedRequirements) -> None:
    data = extracted.model_dump()
    data.pop("language", None)
    for field, value in data.items():
        setattr(instance, field, "" if value is None and field in {
            "listing_type", "location", "price_period", "nearby_facility"
        } else value)
    instance.save()


def search_houses(requirements: SearchRequirements) -> QuerySet[House]:
    queryset = House.objects.filter(is_available=True).select_related(
        "agent", "agent__agent_profile", "region_record", "district_record", "ward_record", "street"
    ).prefetch_related("media", "nearby_facilities", "translations")

    if requirements.listing_type:
        queryset = queryset.filter(listing_type=requirements.listing_type)
    if requirements.location:
        location = requirements.location.strip()
        queryset = queryset.filter(
            Q(address__icontains=location)
            | Q(ward__icontains=location)
            | Q(district__icontains=location)
            | Q(region__icontains=location)
            | Q(region_record__name_en__icontains=location)
            | Q(region_record__name_sw__icontains=location)
            | Q(district_record__name_en__icontains=location)
            | Q(district_record__name_sw__icontains=location)
            | Q(ward_record__name_en__icontains=location)
            | Q(ward_record__name_sw__icontains=location)
            | Q(street__name_en__icontains=location)
            | Q(street__name_sw__icontains=location)
        )
    if requirements.minimum_price is not None:
        queryset = queryset.filter(price__gte=requirements.minimum_price)
    if requirements.maximum_price is not None:
        queryset = queryset.filter(price__lte=requirements.maximum_price)
    if requirements.price_period:
        queryset = queryset.filter(price_period=requirements.price_period)
    if requirements.bedrooms is not None:
        queryset = queryset.filter(bedrooms=requirements.bedrooms)
    if requirements.minimum_bathrooms is not None:
        queryset = queryset.filter(bathrooms__gte=requirements.minimum_bathrooms)
    if requirements.minimum_parking_spaces is not None:
        queryset = queryset.filter(parking_spaces__gte=requirements.minimum_parking_spaces)
    if requirements.maximum_advance_months is not None:
        queryset = queryset.filter(advance_payment_months__lte=requirements.maximum_advance_months)

    for requirement_field, house_field in (
        ("water_required", "water_available"),
        ("electricity_required", "electricity_available"),
        ("security_required", "security_available"),
        ("furnished_required", "furnished"),
        ("internet_required", "has_internet"),
    ):
        if getattr(requirements, requirement_field) is True:
            queryset = queryset.filter(**{house_field: True})

    if requirements.nearby_facility:
        queryset = queryset.filter(
            nearby_facilities__facility_type=requirements.nearby_facility
        )
        if requirements.maximum_facility_distance_km is not None:
            queryset = queryset.filter(
                nearby_facilities__distance_km__lte=requirements.maximum_facility_distance_km
            )
    return queryset.distinct().order_by("price", "-updated_at")


def has_search_criteria(requirements: SearchRequirements) -> bool:
    return any(
        value not in (None, "", False)
        for value in requirement_values(requirements).values()
    )


def find_covering_agents(location: str, limit: int = 5) -> QuerySet[User]:
    if not location:
        return User.objects.none()
    return User.objects.filter(
        is_active=True,
        agent_profile__is_verified=True,
    ).filter(
        Q(agent_profile__coverage_regions__name_en__icontains=location)
        | Q(agent_profile__coverage_regions__name_sw__icontains=location)
        | Q(agent_profile__coverage_districts__name_en__icontains=location)
        | Q(agent_profile__coverage_districts__name_sw__icontains=location)
        | Q(agent_profile__coverage_wards__name_en__icontains=location)
        | Q(agent_profile__coverage_wards__name_sw__icontains=location)
        | Q(agent_profile__coverage_localities__name_en__icontains=location)
        | Q(agent_profile__coverage_localities__name_sw__icontains=location)
    ).select_related("agent_profile").distinct()[:limit]


@dataclass(frozen=True)
class MatchExplanation:
    message: str
    missing_requirements: list[str]


def explain_matches(
    requirements: SearchRequirements,
    match_count: int,
    language: str,
    searched: bool = True,
    conversational_reply: str = "",
    agent_count: int = 0,
) -> MatchExplanation:
    missing = []
    if not requirements.location:
        missing.append("location")
    if requirements.bedrooms is None:
        missing.append("bedrooms")
    if requirements.maximum_price is None:
        missing.append("maximum_price")

    if not searched:
        message = conversational_reply.strip() or (
            "Habari! Mimi ni Sweet Homez. Ninawezaje kukusaidia kuhusu nyumba?"
            if language == "sw"
            else "Hi! I’m Sweet Homez. How can I help you with your property search?"
        )
        return MatchExplanation(message=message, missing_requirements=missing)

    if language == "sw":
        if match_count:
            message = f"Nimepata nyumba {match_count} zinazolingana na mahitaji yako."
        else:
            message = "Sijapata nyumba inayolingana na masharti yote."
            if agent_count:
                message += f" Nimepata mawakala {agent_count} wanaohudumia eneo hilo; unaweza kuwasiliana nao hapa chini."
            else:
                message += " Jaribu kuongeza bajeti au kubadilisha eneo."
        if missing:
            message += " Unaweza pia kuongeza " + ", ".join(missing) + "."
    else:
        if match_count:
            message = f"I found {match_count} available propert{'y' if match_count == 1 else 'ies'} matching your requirements."
        else:
            message = "I couldn't find an available property matching every requirement."
            if agent_count:
                message += f" I found {agent_count} verified agent{'s' if agent_count != 1 else ''} covering that area; you can contact them below."
            else:
                message += " Try increasing the budget or changing the location."
        if missing:
            message += " You can refine the search by adding: " + ", ".join(missing) + "."
    return MatchExplanation(message=message, missing_requirements=missing)
