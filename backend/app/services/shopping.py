from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentMember
from app.core.errors import AppError
from app.models.meal import MealOrder, MealOrderItem
from app.models.shopping import ShoppingCheck


async def build_shopping_list(
    session: AsyncSession,
    member: CurrentMember,
    range_start: date,
    range_end: date,
) -> dict:
    if hasattr(session, "store"):
        if range_start > range_end:
            raise AppError("INVALID_DATE_RANGE", "开始日期不能晚于结束日期", 422)
        orders = await session.store.list("meal_orders", {"family_id": member.family_id})
        totals: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
        labels: dict[tuple[str, str], str] = {}; units: dict[tuple[str, str], str] = {}
        for order in orders:
            current = date.fromisoformat(order["meal_date"])
            if not range_start <= current <= range_end:
                continue
            for item in order.get("items", []):
                for ingredient in item.get("ingredients", []):
                    name = ingredient["name"].strip(); unit = ingredient["unit"].strip(); key = (name.casefold(), unit.casefold())
                    labels[key] = name; units[key] = unit; totals[key] += Decimal(str(ingredient["quantity"]))
        checks = await session.store.list("shopping_checks", {"family_id": member.family_id, "range_start": range_start.isoformat(), "range_end": range_end.isoformat()})
        return {"rangeStart": range_start.isoformat(), "rangeEnd": range_end.isoformat(), "items": [{"key": f"{labels[k]}|{units[k]}", "name": labels[k], "quantity": str(v.normalize()), "unit": units[k]} for k, v in sorted(totals.items())], "checkedKeys": checks[0].get("checked_keys", []) if checks else []}
    if range_start > range_end:
        raise AppError("INVALID_DATE_RANGE", "开始日期不能晚于结束日期", 422)
    result = await session.execute(
        select(MealOrder)
        .options(selectinload(MealOrder.items))
        .where(
            MealOrder.family_id == member.family_id,
            MealOrder.meal_date >= range_start,
            MealOrder.meal_date <= range_end,
        )
    )
    orders = list(result.scalars().unique().all())
    totals: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    labels: dict[tuple[str, str], str] = {}
    units: dict[tuple[str, str], str] = {}
    for order in orders:
        for item in order.items:
            for ingredient in item.ingredients_snapshot:
                name = ingredient["name"].strip()
                unit = ingredient["unit"].strip()
                key = (name.casefold(), unit.casefold())
                labels[key] = name
                units[key] = unit
                totals[key] += Decimal(str(ingredient["quantity"]))
    check = await session.scalar(
        select(ShoppingCheck).where(
            ShoppingCheck.family_id == member.family_id,
            ShoppingCheck.range_start == range_start,
            ShoppingCheck.range_end == range_end,
        )
    )
    items = [
        {
            "key": f"{labels[key]}|{units[key]}",
            "name": labels[key],
            "quantity": str(quantity.normalize()),
            "unit": units[key],
        }
        for key, quantity in sorted(totals.items())
    ]
    return {
        "rangeStart": range_start.isoformat(),
        "rangeEnd": range_end.isoformat(),
        "items": items,
        "checkedKeys": check.checked_keys if check else [],
    }


async def save_checks(
    session: AsyncSession,
    member: CurrentMember,
    range_start: date,
    range_end: date,
    checked_keys: list[str],
) -> None:
    if hasattr(session, "store"):
        if range_start > range_end:
            raise AppError("INVALID_DATE_RANGE", "开始日期不能晚于结束日期", 422)
        rows = await session.store.list("shopping_checks", {"family_id": member.family_id, "range_start": range_start.isoformat(), "range_end": range_end.isoformat()})
        data = {"family_id": member.family_id, "range_start": range_start.isoformat(), "range_end": range_end.isoformat(), "checked_keys": sorted(set(checked_keys)), "updated_by": member.openid}
        if rows:
            await session.store.update("shopping_checks", rows[0]["_id"], data)
        else:
            await session.store.create("shopping_checks", data)
        return
    if range_start > range_end:
        raise AppError("INVALID_DATE_RANGE", "开始日期不能晚于结束日期", 422)
    check = await session.scalar(
        select(ShoppingCheck).where(
            ShoppingCheck.family_id == member.family_id,
            ShoppingCheck.range_start == range_start,
            ShoppingCheck.range_end == range_end,
        )
    )
    if check is None:
        check = ShoppingCheck(
            family_id=member.family_id,
            range_start=range_start,
            range_end=range_end,
            updated_by=member.openid,
        )
        session.add(check)
    check.checked_keys = sorted(set(checked_keys))
    check.updated_by = member.openid
    await session.flush()
