from typing import Literal

from pydantic import BaseModel, Field


class ExtractedRequirements(BaseModel):
    intent: Literal[
        "property_search",
        "search_refinement",
        "property_question",
        "casual_conversation",
        "off_topic",
    ] = "casual_conversation"
    assistant_reply: str = Field(
        default="",
        description="A natural Sweet Homez response in the customer's language",
    )
    location_explicitly_provided: bool = Field(
        default=False,
        description="True only when the newest customer message itself states a location",
    )
    language: Literal["en", "sw"] = Field(description="Language used by the customer")
    listing_type: Literal["rent", "sale"] | None = None
    location: str | None = Field(default=None, description="Region, district, ward, street, or area")
    minimum_price: int | None = Field(default=None, ge=0)
    maximum_price: int | None = Field(default=None, ge=0)
    price_period: Literal[
        "one_time", "daily", "weekly", "monthly", "quarterly", "semiannual", "annual"
    ] | None = None
    bedrooms: int | None = Field(default=None, ge=0)
    minimum_bathrooms: int | None = Field(default=None, ge=0)
    minimum_parking_spaces: int | None = Field(default=None, ge=0)
    maximum_advance_months: int | None = Field(default=None, ge=0)
    water_required: bool | None = None
    electricity_required: bool | None = None
    security_required: bool | None = None
    furnished_required: bool | None = None
    internet_required: bool | None = None
    nearby_facility: Literal[
        "atm",
        "police",
        "gym",
        "fuel_station",
        "pharmacy",
        "hospital",
        "school",
        "market",
        "public_transport",
        "restaurant",
        "other",
    ] | None = None
    maximum_facility_distance_km: float | None = Field(default=None, ge=0)


REQUIREMENT_FIELDS = tuple(
    field
    for field in ExtractedRequirements.model_fields
    if field not in {"intent", "assistant_reply", "location_explicitly_provided", "language"}
)
