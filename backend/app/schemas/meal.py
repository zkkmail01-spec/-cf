from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import APIModel


MealType = Literal["breakfast", "lunch", "dinner"]


class SelectorRead(APIModel):
    openid: str
    nickname: str
    selected_at: datetime


class MealItemRead(APIModel):
    id: str
    dish_id: str | None
    dish_name: str
    image_file_id: str | None
    category_name: str
    ingredients: list[dict]
    selectors: list[SelectorRead]


class MealRead(APIModel):
    id: str | None
    meal_type: MealType
    version: int
    items: list[MealItemRead]


class DayMealsRead(APIModel):
    date: date
    meals: dict[MealType, MealRead]


class CalendarRead(APIModel):
    month: str
    dates: list[date]


class RepeatMealRequest(APIModel):
    source_date: date
    source_meal_type: MealType
    target_date: date
    target_meal_type: MealType


class FrequentDishRead(APIModel):
    dish_id: str
    dish_name: str
    image_file_id: str | None
    count: int = Field(ge=1)
