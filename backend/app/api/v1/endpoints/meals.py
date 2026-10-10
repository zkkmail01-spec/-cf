from datetime import date
from typing import Annotated, Awaitable, Callable, Literal

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentMember, require_member
from app.core.errors import AppError
from app.db.session import get_session
from app.schemas.meal import CalendarRead, DayMealsRead, FrequentDishRead, RepeatMealRequest
from app.schemas.shopping import ShoppingChecksUpdate, ShoppingRead
from app.services import meals as meal_service
from app.services import shopping as shopping_service


router = APIRouter(tags=["meals"])
MealType = Literal["breakfast", "lunch", "dinner"]


async def idempotent_result(
    session: AsyncSession,
    member: CurrentMember,
    key: str,
    fingerprint_source: str,
):
    fingerprint = meal_service.request_fingerprint(fingerprint_source)
    replay = await meal_service.get_idempotent_response(session, member, key, fingerprint)
    return fingerprint, replay


async def execute_idempotent(
    session: AsyncSession,
    member: CurrentMember,
    key: str,
    fingerprint_source: str,
    mutate: Callable[[], Awaitable[None]],
    read_response: Callable[[], Awaitable[dict]],
):
    fingerprint = meal_service.request_fingerprint(fingerprint_source)
    for attempt in range(3):
        try:
            replay = await meal_service.get_idempotent_response(
                session, member, key, fingerprint
            )
            if replay is not None:
                return replay
            await meal_service.claim_idempotency_key(
                session, member, key, fingerprint
            )
            await mutate()
            response = await read_response()
            await meal_service.save_idempotent_response(
                session, member, key, fingerprint, response
            )
            await session.commit()
            return response
        except IntegrityError:
            await session.rollback()
            if attempt == 2:
                raise AppError("MEAL_CONFLICT", "菜单已被更新，请重试", 409)
        except Exception:
            await session.rollback()
            raise


@router.get("/dishes/frequent", response_model=list[FrequentDishRead])
async def frequent_dishes(
    member: Annotated[CurrentMember, Depends(require_member)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict]:
    return await meal_service.frequent_dishes(session, member)


@router.put("/meals/{meal_date}/{meal_type}/selections/{dish_id}", response_model=DayMealsRead)
async def add_selection(
    meal_date: date,
    meal_type: MealType,
    dish_id: str,
    member: Annotated[CurrentMember, Depends(require_member)],
    session: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
):
    return await execute_idempotent(
        session,
        member,
        idempotency_key,
        f"PUT:{meal_date}:{meal_type}:{dish_id}",
        lambda: meal_service.add_selection(session, member, meal_date, meal_type, dish_id),
        lambda: meal_service.get_day(session, member, meal_date),
    )


@router.delete("/meals/{meal_date}/{meal_type}/selections/{dish_id}", response_model=DayMealsRead)
async def remove_selection(
    meal_date: date,
    meal_type: MealType,
    dish_id: str,
    member: Annotated[CurrentMember, Depends(require_member)],
    session: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
):
    return await execute_idempotent(
        session,
        member,
        idempotency_key,
        f"DELETE:{meal_date}:{meal_type}:{dish_id}",
        lambda: meal_service.remove_selection(session, member, meal_date, meal_type, dish_id),
        lambda: meal_service.get_day(session, member, meal_date),
    )


@router.get("/meals/calendar", response_model=CalendarRead)
async def meal_calendar(
    month: Annotated[str, Query(pattern=r"^\d{4}-\d{2}$")],
    member: Annotated[CurrentMember, Depends(require_member)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return {"month": month, "dates": await meal_service.calendar_dates(session, member, month)}


@router.post("/meals/repeat", response_model=DayMealsRead)
async def repeat_meal(
    payload: RepeatMealRequest,
    member: Annotated[CurrentMember, Depends(require_member)],
    session: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
):
    source = (
        f"REPEAT:{payload.source_date}:{payload.source_meal_type}:"
        f"{payload.target_date}:{payload.target_meal_type}"
    )
    return await execute_idempotent(
        session,
        member,
        idempotency_key,
        source,
        lambda: meal_service.repeat_meal(
            session,
            member,
            payload.source_date,
            payload.source_meal_type,
            payload.target_date,
            payload.target_meal_type,
        ),
        lambda: meal_service.get_day(session, member, payload.target_date),
    )


@router.get("/meals/{meal_date}", response_model=DayMealsRead)
async def get_day(
    meal_date: date,
    member: Annotated[CurrentMember, Depends(require_member)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await meal_service.get_day(session, member, meal_date)


@router.get("/shopping", response_model=ShoppingRead)
async def shopping_list(
    start: date,
    end: date,
    member: Annotated[CurrentMember, Depends(require_member)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await shopping_service.build_shopping_list(session, member, start, end)


@router.put("/shopping/checks", response_model=ShoppingRead)
async def save_shopping_checks(
    payload: ShoppingChecksUpdate,
    member: Annotated[CurrentMember, Depends(require_member)],
    session: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
):
    source = f"CHECKS:{payload.model_dump_json(by_alias=True)}"
    return await execute_idempotent(
        session,
        member,
        idempotency_key,
        source,
        lambda: shopping_service.save_checks(
            session,
            member,
            payload.range_start,
            payload.range_end,
            payload.checked_keys,
        ),
        lambda: shopping_service.build_shopping_list(
            session, member, payload.range_start, payload.range_end
        ),
    )
