from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SkinType = Literal["dry", "normal", "combination", "oily", "all"]
ProductStatus = Literal["draft", "published", "archived"]


class ProductInput(BaseModel):
    brand: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    variant: str = Field(default="", max_length=120)
    category: Literal["sunscreen", "moisturizer", "cleanser", "treatment", "other"]
    price_satang: int | None = Field(default=None, ge=0, le=100_000_000)
    ingredients_label: str = Field(default="", max_length=10_000)
    ingredients_inci: list[str] = Field(default_factory=list, max_length=100)
    warnings_label: str = Field(default="", max_length=5_000)
    target_skin_types: list[SkinType] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list, max_length=30)
    source_url: str | None = Field(default=None, max_length=1000, pattern=r"^https?://[^\s]+$")
    spf: int | None = Field(default=None, ge=1, le=100)
    broad_spectrum: bool = False
    water_resistant_minutes: int | None = Field(default=None, ge=1, le=120)

    @field_validator("brand", "name", "variant", "category", "ingredients_label", "warnings_label")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("brand", "name", "category")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("ingredients_inci", "concerns")
    @classmethod
    def clean_list(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value or len(value) > 200 for value in cleaned):
            raise ValueError("Entries must be 1–200 characters")
        return list(dict.fromkeys(cleaned))

    @model_validator(mode="after")
    def check_skin_types(self) -> "ProductInput":
        if "all" in self.target_skin_types and len(self.target_skin_types) > 1:
            raise ValueError("All skin types cannot be combined with specific types")
        self.target_skin_types = list(dict.fromkeys(self.target_skin_types))
        return self


class ProductStatusInput(BaseModel):
    status: ProductStatus


class ProductRead(ProductInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: ProductStatus
    price_checked_at: datetime | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
