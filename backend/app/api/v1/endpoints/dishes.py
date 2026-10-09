from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentMember, require_chef, require_member
from app.db.session import get_session
from app.models.dish import Dish
from app.schemas.dish import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    DishCreate,
    DishRead,
    DishUpdate,
    IngredientRead,
)
from app.services import dishes as dish_service


router = APIRouter(tags=["catalog"])


def dish_read(dish: Dish) -> DishRead:
    return DishRead(
        id=dish.id,
        category_id=dish.category_id,
        category_name=dish.category.name,
        name=dish.name,
        image_file_id=dish.image_file_id,
        description=dish.description,
        ingredients=[IngredientRead.model_validate(item) for item in dish.ingredients],
    )


@router.get("/categories", response_model=list[CategoryRead])
async def list_categories(
    member: Annotated[CurrentMember, Depends(require_member)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[CategoryRead]:
    return [
        CategoryRead.model_validate(item)
        for item in await dish_service.list_categories(session, member)
    ]


@router.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    member: Annotated[CurrentMember, Depends(require_chef)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CategoryRead:
    return CategoryRead.model_validate(
        await dish_service.create_category(session, member, payload)
    )


@router.patch("/categories/{category_id}", response_model=CategoryRead)
async def patch_category(
    category_id: str,
    payload: CategoryUpdate,
    member: Annotated[CurrentMember, Depends(require_chef)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CategoryRead:
    return CategoryRead.model_validate(
        await dish_service.update_category(session, member, category_id, payload)
    )


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    member: Annotated[CurrentMember, Depends(require_chef)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    await dish_service.deactivate_category(session, member, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/dishes", response_model=list[DishRead])
async def list_dishes(
    member: Annotated[CurrentMember, Depends(require_member)],
    session: Annotated[AsyncSession, Depends(get_session)],
    query: Annotated[str | None, Query(max_length=120)] = None,
    category_id: Annotated[str | None, Query(alias="categoryId")] = None,
) -> list[DishRead]:
    dishes = await dish_service.list_dishes(session, member, query, category_id)
    return [dish_read(dish) for dish in dishes]


@router.get("/dishes/{dish_id}", response_model=DishRead)
async def get_dish(
    dish_id: str,
    member: Annotated[CurrentMember, Depends(require_member)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DishRead:
    return dish_read(await dish_service.get_dish(session, member, dish_id))


@router.post("/dishes", response_model=DishRead, status_code=status.HTTP_201_CREATED)
async def create_dish(
    payload: DishCreate,
    member: Annotated[CurrentMember, Depends(require_chef)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DishRead:
    return dish_read(await dish_service.create_dish(session, member, payload))


@router.patch("/dishes/{dish_id}", response_model=DishRead)
async def patch_dish(
    dish_id: str,
    payload: DishUpdate,
    member: Annotated[CurrentMember, Depends(require_chef)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DishRead:
    return dish_read(await dish_service.update_dish(session, member, dish_id, payload))


@router.delete("/dishes/{dish_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dish(
    dish_id: str,
    member: Annotated[CurrentMember, Depends(require_chef)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    await dish_service.deactivate_dish(session, member, dish_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
