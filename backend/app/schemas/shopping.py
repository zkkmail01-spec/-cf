from datetime import date

from app.schemas.common import APIModel


class ShoppingItemRead(APIModel):
    key: str
    name: str
    quantity: str
    unit: str


class ShoppingRead(APIModel):
    range_start: date
    range_end: date
    items: list[ShoppingItemRead]
    checked_keys: list[str]


class ShoppingChecksUpdate(APIModel):
    range_start: date
    range_end: date
    checked_keys: list[str]
