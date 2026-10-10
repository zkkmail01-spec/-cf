import hashlib
from datetime import date
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentMember
from app.core.errors import AppError
from app.models.dish import Dish
from app.models.idempotency import IdempotencyRecord
from app.models.meal import MealItemSelector, MealOrder, MealOrderItem


MEAL_TYPES = ("breakfast", "lunch", "dinner")


def request_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def get_idempotent_response(
    session: AsyncSession,
    member: CurrentMember,
    key: str,
    fingerprint: str,
) -> dict[str, Any] | None:
    record = await session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.family_id == member.family_id,
            IdempotencyRecord.openid == member.openid,
            IdempotencyRecord.key == key,
        )
    )
    if record is None:
        return None
    if record.request_fingerprint != fingerprint:
        raise AppError(
            "IDEMPOTENCY_KEY_REUSED",
            "同一个幂等键不能用于不同请求",
            409,
        )
    return record.response_json


async def save_idempotent_response(
    session: AsyncSession,
    member: CurrentMember,
    key: str,
    fingerprint: str,
    response: dict[str, Any],
) -> None:
    record = await session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.family_id == member.family_id,
            IdempotencyRecord.openid == member.openid,
            IdempotencyRecord.key == key,
        )
    )
    if record is None:
        record = IdempotencyRecord(
            family_id=member.family_id,
            openid=member.openid,
            key=key,
            request_fingerprint=fingerprint,
            status_code=102,
            response_json={},
        )
        session.add(record)
    record.status_code = 200
    record.response_json = response
    await session.flush()


async def claim_idempotency_key(
    session: AsyncSession,
    member: CurrentMember,
    key: str,
    fingerprint: str,
) -> None:
    session.add(
        IdempotencyRecord(
            family_id=member.family_id,
            openid=member.openid,
            key=key,
            request_fingerprint=fingerprint,
            status_code=102,
            response_json={},
        )
    )
    await session.flush()


def meal_order_query():
    return select(MealOrder).options(
        selectinload(MealOrder.items).selectinload(MealOrderItem.selectors)
    )


async def get_order(
    session: AsyncSession,
    family_id: str,
    meal_date: date,
    meal_type: str,
    *,
    lock: bool = False,
) -> MealOrder | None:
    statement = meal_order_query().where(
        MealOrder.family_id == family_id,
        MealOrder.meal_date == meal_date,
        MealOrder.meal_type == meal_type,
    )
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    return (
        await session.execute(statement)
    ).scalar_one_or_none()


async def add_selection(
    session: AsyncSession,
    member: CurrentMember,
    meal_date: date,
    meal_type: str,
    dish_id: str,
) -> None:
    dish = (
        await session.execute(
            select(Dish)
            .options(selectinload(Dish.category), selectinload(Dish.ingredients))
            .where(
                Dish.id == dish_id,
                Dish.family_id == member.family_id,
                Dish.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if dish is None:
        raise AppError("DISH_NOT_FOUND", "菜品不存在", 404)

    order = await get_order(session, member.family_id, meal_date, meal_type, lock=True)
    if order is None:
        order = MealOrder(
            family_id=member.family_id,
            meal_date=meal_date,
            meal_type=meal_type,
            version=0,
        )
        session.add(order)
    item = next((row for row in order.items if row.dish_id == dish_id), None)
    if item is None:
        item = MealOrderItem(
            dish_id=dish.id,
            dish_name=dish.name,
            image_file_id=dish.image_file_id,
            category_name=dish.category.name,
            ingredients_snapshot=[
                {
                    "name": ingredient.name,
                    "quantity": str(ingredient.quantity.normalize()),
                    "unit": ingredient.unit,
                    "note": ingredient.note,
                }
                for ingredient in dish.ingredients
            ],
        )
        order.items.append(item)
    if not any(row.openid == member.openid for row in item.selectors):
        item.selectors.append(
            MealItemSelector(openid=member.openid, nickname=member.nickname)
        )
        order.version += 1
    await session.flush()


async def remove_selection(
    session: AsyncSession,
    member: CurrentMember,
    meal_date: date,
    meal_type: str,
    dish_id: str,
) -> None:
    order = await get_order(session, member.family_id, meal_date, meal_type, lock=True)
    if order is None:
        return
    item = next((row for row in order.items if row.dish_id == dish_id), None)
    if item is None:
        return
    selector = next((row for row in item.selectors if row.openid == member.openid), None)
    if selector is None:
        return
    item.selectors.remove(selector)
    if not item.selectors:
        order.items.remove(item)
    order.version += 1
    await session.flush()


def order_to_dict(order: MealOrder | None, meal_type: str) -> dict[str, Any]:
    if order is None:
        return {"id": None, "mealType": meal_type, "version": 0, "items": []}
    items = []
    for item in order.items:
        items.append(
            {
                "id": item.id,
                "dishId": item.dish_id,
                "dishName": item.dish_name,
                "imageFileId": item.image_file_id,
                "categoryName": item.category_name,
                "ingredients": item.ingredients_snapshot,
                "selectors": [
                    {
                        "openid": selector.openid,
                        "nickname": selector.nickname,
                        "selectedAt": selector.selected_at.isoformat(),
                    }
                    for selector in sorted(item.selectors, key=lambda row: row.openid)
                ],
            }
        )
    return {
        "id": order.id,
        "mealType": meal_type,
        "version": order.version,
        "items": items,
    }


async def get_day(
    session: AsyncSession, member: CurrentMember, meal_date: date
) -> dict[str, Any]:
    result = await session.execute(
        meal_order_query().where(
            MealOrder.family_id == member.family_id,
            MealOrder.meal_date == meal_date,
        )
    )
    by_type = {order.meal_type: order for order in result.scalars().unique().all()}
    return {
        "date": meal_date.isoformat(),
        "meals": {
            meal_type: order_to_dict(by_type.get(meal_type), meal_type)
            for meal_type in MEAL_TYPES
        },
    }


async def calendar_dates(
    session: AsyncSession, member: CurrentMember, month: str
) -> list[date]:
    try:
        year, month_number = (int(part) for part in month.split("-"))
        start = date(year, month_number, 1)
        end = date(year + (month_number == 12), 1 if month_number == 12 else month_number + 1, 1)
    except (ValueError, TypeError):
        raise AppError("INVALID_MONTH", "月份格式应为 YYYY-MM", 422)
    result = await session.execute(
        select(MealOrder.meal_date)
        .where(
            MealOrder.family_id == member.family_id,
            MealOrder.meal_date >= start,
            MealOrder.meal_date < end,
        )
        .distinct()
        .order_by(MealOrder.meal_date)
    )
    return list(result.scalars().all())


async def repeat_meal(
    session: AsyncSession,
    member: CurrentMember,
    source_date: date,
    source_type: str,
    target_date: date,
    target_type: str,
) -> None:
    source = await get_order(session, member.family_id, source_date, source_type)
    if source is None:
        raise AppError("SOURCE_MEAL_EMPTY", "来源餐次没有菜品", 404)
    target = await get_order(session, member.family_id, target_date, target_type, lock=True)
    if target is None:
        target = MealOrder(
            family_id=member.family_id,
            meal_date=target_date,
            meal_type=target_type,
            version=0,
        )
        session.add(target)
    changed = False
    for source_item in source.items:
        target_item = next(
            (item for item in target.items if item.dish_id == source_item.dish_id), None
        )
        if target_item is None:
            target_item = MealOrderItem(
                dish_id=source_item.dish_id,
                dish_name=source_item.dish_name,
                image_file_id=source_item.image_file_id,
                category_name=source_item.category_name,
                ingredients_snapshot=source_item.ingredients_snapshot,
            )
            target.items.append(target_item)
        if not any(row.openid == member.openid for row in target_item.selectors):
            target_item.selectors.append(
                MealItemSelector(openid=member.openid, nickname=member.nickname)
            )
            changed = True
    if changed:
        target.version += 1
    await session.flush()


async def frequent_dishes(
    session: AsyncSession, member: CurrentMember, limit: int = 6
) -> list[dict[str, Any]]:
    result = await session.execute(
        select(
            MealOrderItem.dish_id,
            MealOrderItem.dish_name,
            MealOrderItem.image_file_id,
            func.count(MealOrderItem.id).label("count"),
        )
        .join(MealOrder, MealOrder.id == MealOrderItem.meal_order_id)
        .join(Dish, Dish.id == MealOrderItem.dish_id)
        .where(MealOrder.family_id == member.family_id, Dish.is_active.is_(True))
        .group_by(
            MealOrderItem.dish_id,
            MealOrderItem.dish_name,
            MealOrderItem.image_file_id,
        )
        .order_by(func.count(MealOrderItem.id).desc(), MealOrderItem.dish_name)
        .limit(limit)
    )
    return [
        {
            "dishId": row.dish_id,
            "dishName": row.dish_name,
            "imageFileId": row.image_file_id,
            "count": row.count,
        }
        for row in result
    ]
