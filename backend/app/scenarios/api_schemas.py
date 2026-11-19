from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.scenarios.taxonomy import CAPABILITIES, DATA_CLASSES, INDUSTRIES

Item = Field(default_factory=list, max_length=25)


def _clean_list(values: list[str]) -> list[str]:
    cleaned = []
    for value in values:
        text = " ".join(str(value).split())
        if not text:
            continue
        if len(text) > 200:
            raise ValueError("Keep each entry under 200 characters.")
        if text not in cleaned:
            cleaned.append(text)
    return cleaned


class ProfileWrite(BaseModel):
    industry: str
    description: str = Field(default="", max_length=4000)
    purpose: str = Field(min_length=10, max_length=1000)
    responsibilities: list[str] = Item
    tools: list[str] = Item
    permissions: list[str] = Item
    data_types: list[str] = Item
    authorised_actions: list[str] = Item
    risk_sensitivity: Literal["low", "moderate", "high", "critical"] = "moderate"
    capabilities: list[str] | None = Field(default=None, max_length=len(CAPABILITIES))

    @field_validator("industry")
    @classmethod
    def known_industry(cls, value: str) -> str:
        if value not in INDUSTRIES:
            raise ValueError("Choose a supported industry.")
        return value

    @field_validator("description", "purpose")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("responsibilities", "tools", "permissions", "authorised_actions")
    @classmethod
    def clean_lists(cls, value: list[str]) -> list[str]:
        return _clean_list(value)

    @field_validator("data_types")
    @classmethod
    def known_data(cls, value: list[str]) -> list[str]:
        unknown = [item for item in value if item not in DATA_CLASSES]
        if unknown:
            raise ValueError("Unknown data type.")
        return list(dict.fromkeys(value))

    @field_validator("capabilities")
    @classmethod
    def known_capabilities(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        unknown = [item for item in value if item not in CAPABILITIES]
        if unknown:
            raise ValueError("Unknown capability.")
        return list(dict.fromkeys(value))


class ProfileAnalyse(BaseModel):
    industry: str = ""
    description: str = Field(default="", max_length=4000)
    purpose: str = Field(default="", max_length=1000)
    responsibilities: list[str] = Item
    tools: list[str] = Item
    permissions: list[str] = Item
    data_types: list[str] = Item
    authorised_actions: list[str] = Item


class ProgrammeCreate(BaseModel):
    agent_id: str = Field(min_length=36, max_length=36)
    intensity: Literal["focused", "standard", "extended"] = "standard"
    include_generic: bool = False


class ProgrammeUpdate(BaseModel):
    intensity: Literal["focused", "standard", "extended"] | None = None
    selected: list[str] | None = Field(default=None, max_length=200)
    include_generic: bool | None = None
    generic_categories: list[str] | None = Field(default=None, max_length=20)


class ProgrammeLaunch(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    authorised: bool
    authorisation_note: str = Field(min_length=10, max_length=500)

    @field_validator("name", "authorisation_note")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Enter at least 2 characters.")
        return cleaned
