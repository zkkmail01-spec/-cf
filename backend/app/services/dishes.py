from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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


async def list_categories(
    session: AsyncSession, member: CurrentMember
) -> list[DishCategory]:
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
    dish = await get_dish(session, member, dish_id)
    dish.is_active = False
    await session.commit()
