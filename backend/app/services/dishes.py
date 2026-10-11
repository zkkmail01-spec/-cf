from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from types import SimpleNamespace
from uuid import uuid4

from app.api.deps import CurrentMember
from app.core.errors import AppError
from app.models.dish import Dish, DishCategory, DishIngredient
from app.schemas.dish import (
    CategoryCreate,
    CategoryUpdate,
    DishCreate,
    DishUpdate,
    IngredientWrite,
)


def _entity(row: dict) -> SimpleNamespace:
    return SimpleNamespace(id=row["_id"], **{k: v for k, v in row.items() if k != "_id"})


def _dish_entity(row: dict, category: dict, ingredients: list[dict]) -> SimpleNamespace:
    obj = _entity(row)
    obj.category = _entity(category)
    obj.ingredients = [_entity({**item, "sort_order": item.get("sort_order", index)}) for index, item in enumerate(ingredients)]
    return obj


async def list_categories(
    session: AsyncSession, member: CurrentMember
) -> list[DishCategory]:
    if hasattr(session, "store"):
        rows = await session.store.list("dish_categories", {"family_id": member.family_id, "is_active": True})
        return [_entity(row) for row in sorted(rows, key=lambda r: (r.get("sort_order", 0), r.get("name", "")))]
    result = await session.execute(
        select(DishCategory)
        .where(
            DishCategory.family_id == member.family_id,
            DishCategory.is_active.is_(True),
        )
        .order_by(DishCategory.sort_order, DishCategory.name)
    )
    return list(result.scalars().all())


async def create_category(
    session: AsyncSession, member: CurrentMember, payload: CategoryCreate
) -> DishCategory:
    if hasattr(session, "store"):
        row = await session.store.create("dish_categories", {"family_id": member.family_id, "name": payload.name, "sort_order": payload.sort_order, "is_active": True})
        return _entity(row)
    category = DishCategory(
        family_id=member.family_id,
        name=payload.name,
        sort_order=payload.sort_order,
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


async def get_category(
    session: AsyncSession,
    member: CurrentMember,
    category_id: str,
    *,
    active_only: bool = True,
) -> DishCategory:
    if hasattr(session, "store"):
        rows = await session.store.list("dish_categories", {"_id": category_id, "family_id": member.family_id})
        category = rows[0] if rows and (not active_only or rows[0].get("is_active", True)) else None
        if category is None:
            raise AppError("CATEGORY_NOT_FOUND", "菜品分类不存在", 404)
        return _entity(category)
    query = select(DishCategory).where(
        DishCategory.id == category_id,
        DishCategory.family_id == member.family_id,
    )
    if active_only:
        query = query.where(DishCategory.is_active.is_(True))
    category = await session.scalar(query)
    if category is None:
        raise AppError("CATEGORY_NOT_FOUND", "菜品分类不存在", 404)
    return category


async def update_category(
    session: AsyncSession,
    member: CurrentMember,
    category_id: str,
    payload: CategoryUpdate,
) -> DishCategory:
    if hasattr(session, "store"):
        category = await get_category(session, member, category_id)
        patch = payload.model_dump(exclude_unset=True)
        row = await session.store.update("dish_categories", category.id, patch) if patch else await session.store.get("dish_categories", category.id)
        return _entity(row)
    category = await get_category(session, member, category_id)
    if payload.name is not None:
        category.name = payload.name
    if payload.sort_order is not None:
        category.sort_order = payload.sort_order
    await session.commit()
    await session.refresh(category)
    return category


async def deactivate_category(
    session: AsyncSession, member: CurrentMember, category_id: str
) -> None:
    if hasattr(session, "store"):
        category = await get_category(session, member, category_id)
        await session.store.update("dish_categories", category.id, {"is_active": False})
        return
    category = await get_category(session, member, category_id)
    category.is_active = False
    await session.commit()


def ingredient_model(payload: IngredientWrite, index: int) -> DishIngredient:
    return DishIngredient(
        name=payload.name,
        quantity=payload.quantity,
        unit=payload.unit,
        note=payload.note,
        sort_order=index,
    )


def dish_query():
    return select(Dish).options(
        selectinload(Dish.category),
        selectinload(Dish.ingredients),
    )


async def list_dishes(
    session: AsyncSession,
    member: CurrentMember,
    query: str | None = None,
    category_id: str | None = None,
) -> list[Dish]:
    if hasattr(session, "store"):
        categories = {row["_id"]: row for row in await session.store.list("dish_categories", {"family_id": member.family_id})}
        dishes = await session.store.list("dishes", {"family_id": member.family_id, "is_active": True})
        result = []
        for row in dishes:
            if category_id and row.get("category_id") != category_id:
                continue
            if query and query.strip() and query.casefold() not in row.get("name", "").casefold() and not any(query.casefold() in i.get("name", "").casefold() for i in row.get("ingredients", [])):
                continue
            result.append(_dish_entity(row, categories.get(row["category_id"], {"_id": row["category_id"], "name": ""}), [{"_id": f"{row['_id']}-{i}", **item} for i, item in enumerate(row.get("ingredients", []))]))
        return sorted(result, key=lambda d: d.name)
    statement = (
        dish_query()
        .where(Dish.family_id == member.family_id, Dish.is_active.is_(True))
        .order_by(Dish.name)
    )
    if category_id:
        statement = statement.where(Dish.category_id == category_id)
    if query and query.strip():
        pattern = f"%{query.strip()}%"
        statement = (
            statement.outerjoin(Dish.ingredients)
            .where(or_(Dish.name.ilike(pattern), DishIngredient.name.ilike(pattern)))
            .distinct()
        )
    result = await session.execute(statement)
    return list(result.scalars().unique().all())


async def get_dish(
    session: AsyncSession,
    member: CurrentMember,
    dish_id: str,
    *,
    active_only: bool = True,
) -> Dish:
    if hasattr(session, "store"):
        rows = await session.store.list("dishes", {"_id": dish_id, "family_id": member.family_id})
        row = rows[0] if rows and (not active_only or rows[0].get("is_active", True)) else None
        if row is None:
            raise AppError("DISH_NOT_FOUND", "菜品不存在", 404)
        category = (await session.store.get("dish_categories", row["category_id"])) or {"_id": row["category_id"], "name": ""}
        return _dish_entity(row, category, [{"_id": f"{row['_id']}-{i}", **item} for i, item in enumerate(row.get("ingredients", []))])
    statement = dish_query().where(
        Dish.id == dish_id,
        Dish.family_id == member.family_id,
    )
    if active_only:
        statement = statement.where(Dish.is_active.is_(True))
    dish = (await session.execute(statement)).scalar_one_or_none()
    if dish is None:
        raise AppError("DISH_NOT_FOUND", "菜品不存在", 404)
    return dish


async def create_dish(
    session: AsyncSession,
    member: CurrentMember,
    payload: DishCreate,
) -> Dish:
    if hasattr(session, "store"):
        await get_category(session, member, payload.category_id)
        row = await session.store.create("dishes", {"family_id": member.family_id, "category_id": payload.category_id, "name": payload.name, "image_file_id": payload.image_file_id, "description": payload.description.strip() if payload.description else None, "created_by": member.openid, "ingredients": [ingredient.model_dump() for ingredient in payload.ingredients], "is_active": True})
        return await get_dish(session, member, row["_id"])
    await get_category(session, member, payload.category_id)
    dish = Dish(
        family_id=member.family_id,
        category_id=payload.category_id,
        name=payload.name,
        image_file_id=payload.image_file_id,
        description=payload.description.strip() if payload.description else None,
        created_by=member.openid,
        ingredients=[
            ingredient_model(ingredient, index)
            for index, ingredient in enumerate(payload.ingredients)
        ],
    )
    session.add(dish)
    await session.commit()
    return await get_dish(session, member, dish.id)


async def update_dish(
    session: AsyncSession,
    member: CurrentMember,
    dish_id: str,
    payload: DishUpdate,
) -> Dish:
    if hasattr(session, "store"):
        dish = await get_dish(session, member, dish_id)
        patch = {}
        if payload.category_id is not None:
            await get_category(session, member, payload.category_id)
            patch["category_id"] = payload.category_id
        if payload.name is not None:
            patch["name"] = payload.name
        if "image_file_id" in payload.model_fields_set:
            patch["image_file_id"] = payload.image_file_id
        if "description" in payload.model_fields_set:
            patch["description"] = payload.description.strip() if payload.description else None
        if payload.ingredients is not None:
            patch["ingredients"] = [ingredient.model_dump() for ingredient in payload.ingredients]
        if patch:
            await session.store.update("dishes", dish.id, patch)
        return await get_dish(session, member, dish.id)
    dish = await get_dish(session, member, dish_id)
    if payload.category_id is not None:
        await get_category(session, member, payload.category_id)
        dish.category_id = payload.category_id
    if payload.name is not None:
        dish.name = payload.name
    if "image_file_id" in payload.model_fields_set:
        dish.image_file_id = payload.image_file_id
    if "description" in payload.model_fields_set:
        dish.description = payload.description.strip() if payload.description else None
    if payload.ingredients is not None:
        dish.ingredients.clear()
        dish.ingredients.extend(
            ingredient_model(ingredient, index)
            for index, ingredient in enumerate(payload.ingredients)
        )
    await session.commit()
    return await get_dish(session, member, dish.id)


async def deactivate_dish(
    session: AsyncSession, member: CurrentMember, dish_id: str
) -> None:
    if hasattr(session, "store"):
        dish = await get_dish(session, member, dish_id)
        await session.store.update("dishes", dish.id, {"is_active": False})
        return
    dish = await get_dish(session, member, dish_id)
    dish.is_active = False
    await session.commit()
