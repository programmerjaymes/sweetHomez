import json
from typing import Literal

from django.conf import settings
from pydantic import BaseModel, Field


class HousePromptDraft(BaseModel):
    title: str = Field(max_length=200)
    description: str = ""
    listing_type: Literal["rent", "sale"]
    price: float = Field(ge=0)
    price_period: Literal["one_time", "daily", "weekly", "monthly", "quarterly", "semiannual", "annual"]
    address: str
    ward: str = ""
    district: str = ""
    region: str
    bedrooms: int = Field(default=0, ge=0)
    bathrooms: int = Field(default=0, ge=0)
    outdoor_toilets: int = Field(default=0, ge=0)
    ensuite_bedrooms: int = Field(default=0, ge=0)
    has_living_room: bool = False
    kitchens: int = Field(default=0, ge=0)
    has_indoor_kitchen: bool = False
    has_outdoor_kitchen: bool = False
    parking_spaces: int = Field(default=0, ge=0)
    furnished: bool = False
    electricity_available: bool = False
    water_available: bool = False
    security_available: bool = False
    has_garden: bool = False
    has_balcony: bool = False
    has_air_conditioning: bool = False
    has_internet: bool = False
    image_urls: list[str] = []


class HousePromptProgress(BaseModel):
    title: str | None = None
    description: str | None = None
    listing_type: Literal["rent", "sale"] | None = None
    price: float | None = Field(default=None, ge=0)
    price_period: Literal["one_time", "daily", "weekly", "monthly", "quarterly", "semiannual", "annual"] | None = None
    address: str | None = None
    ward: str | None = None
    district: str | None = None
    region: str | None = None
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    outdoor_toilets: int | None = Field(default=None, ge=0)
    ensuite_bedrooms: int | None = Field(default=None, ge=0)
    has_living_room: bool | None = None
    kitchens: int | None = Field(default=None, ge=0)
    has_indoor_kitchen: bool | None = None
    has_outdoor_kitchen: bool | None = None
    parking_spaces: int | None = Field(default=None, ge=0)
    furnished: bool | None = None
    electricity_available: bool | None = None
    water_available: bool | None = None
    security_available: bool | None = None
    has_garden: bool | None = None
    has_balcony: bool | None = None
    has_air_conditioning: bool | None = None
    has_internet: bool | None = None
    image_urls: list[str] | None = None


def update_house_draft(message: str, current_draft: dict, language: str) -> dict:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    from openai import OpenAI
    response = OpenAI(api_key=settings.OPENAI_API_KEY).responses.parse(
        model=settings.OPENAI_MODEL,
        reasoning={"effort": "low"},
        instructions=(
            "Update a Tanzanian property listing draft from the agent's latest chat answer. "
            "Return only facts explicitly supplied in the latest message or already present in current_draft. "
            "Preserve existing facts unless the agent clearly corrects them. Never invent missing facts. "
            "Prices are TZS unless stated otherwise. Extract public image URLs exactly. "
            "In Swahili, 'choo cha nje' means outdoor_toilets and bedrooms with an inside toilet/bathroom means ensuite_bedrooms. "
            "When both are supplied, bathrooms is their sum unless the agent explicitly gives a different total. "
            "In Swahili, 'sebule' means a living room; store whether it exists in has_living_room. "
            "Store 'jiko la ndani' in has_indoor_kitchen and 'jiko la nje' in has_outdoor_kitchen. "
            "Interpret Ndiyo as true and Hapana/Hamna as false. Interpret 'hamna chumba cha kulala' as bedrooms=0 "
            "and 'vyumba havina choo' as ensuite_bedrooms=0."
        ),
        input=json.dumps({"current_draft": current_draft, "latest_message": message, "language": language}, ensure_ascii=False),
        text_format=HousePromptProgress,
        store=False,
    )
    if response.output_parsed is None:
        raise RuntimeError("The assistant returned no listing information.")
    updates = response.output_parsed.model_dump(exclude_none=True)
    return {**current_draft, **updates}


def create_house_draft(prompt: str, language: str) -> HousePromptDraft:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    from openai import OpenAI
    response = OpenAI(api_key=settings.OPENAI_API_KEY).responses.parse(
        model=settings.OPENAI_MODEL,
        reasoning={"effort": "low"},
        instructions=(
            "Convert a Tanzanian property agent's natural-language listing into a factual structured draft. "
            "Never invent facts. Use sensible model defaults only where the schema provides them. Prices are TZS unless stated otherwise. "
            "Rent must use a recurring price period; sale must use one_time. Preserve public image URLs exactly. "
            f"Write the title and description in {'Swahili' if language == 'sw' else 'English'}."
        ),
        input=json.dumps({"prompt": prompt}, ensure_ascii=False),
        text_format=HousePromptDraft,
        store=False,
    )
    if response.output_parsed is None:
        raise RuntimeError("The assistant returned no listing draft.")
    return response.output_parsed
