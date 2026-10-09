from decimal import Decimal

from pydantic import Field, field_validator

from app.schemas.common import APIModel


class CategoryCreate(APIModel):
    name: str = Field(min_length=1, max_length=80)
    sort_order: int = 0

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("分类名称不能为空")
        return cleaned


class CategoryUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    sort_order: int | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("分类名称不能为空")
        return cleaned


class CategoryRead(APIModel):
    id: str
    name: str
    sort_order: int


class IngredientWrite(APIModel):
    name: str = Field(min_length=1, max_length=120)
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit: str = Field(min_length=1, max_length=32)
    note: str | None = Field(default=None, max_length=255)

    @field_validator("name", "unit")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("字段不能为空")
        return cleaned

    @field_validator("note")
    @classmethod
    def clean_note(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class IngredientRead(APIModel):
    id: str
    name: str
    quantity: Decimal
    unit: str
    note: str | None
    sort_order: int


class DishCreate(APIModel):
    category_id: str
    name: str = Field(min_length=1, max_length=120)
    image_file_id: str | None = Field(default=None, max_length=512)
    description: str | None = None
    ingredients: list[IngredientWrite] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("菜品名称不能为空")
        return cleaned


class DishUpdate(APIModel):
    category_id: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    image_file_id: str | None = Field(default=None, max_length=512)
    description: str | None = None
    ingredients: list[IngredientWrite] | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("菜品名称不能为空")
        return cleaned


class DishRead(APIModel):
    id: str
    category_id: str
    category_name: str
    name: str
    image_file_id: str | None
    description: str | None
    ingredients: list[IngredientRead]
