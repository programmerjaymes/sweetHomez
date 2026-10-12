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
    bedrooms: int = Field(default=1, ge=0)
    bathrooms: int = Field(default=1, ge=0)
    kitchens: int = Field(default=1, ge=0)
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
