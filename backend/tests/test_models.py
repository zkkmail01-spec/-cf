from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.family import Family, FamilyMember
from app.models.idempotency import IdempotencyRecord
from app.models.invitation import Invitation
from app.models.meal import MealItemSelector, MealOrder, MealOrderItem


@pytest.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db_session:
        yield db_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_family_member_openid_is_unique_within_family(session):
    family = Family(name="幸福小家", owner_openid="chef-openid")
    session.add(family)
    await session.flush()
    session.add_all(
        [
            FamilyMember(
                family_id=family.id,
                openid="member-openid",
                nickname="妈妈",
                role="member",
            ),
            FamilyMember(
                family_id=family.id,
                openid="member-openid",
                nickname="妈妈2",
                role="member",
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_one_meal_order_exists_per_family_date_and_type(session):
    family = Family(name="幸福小家", owner_openid="chef-openid")
    session.add(family)
    await session.flush()
    session.add_all(
        [
            MealOrder(
                family_id=family.id,
                meal_date=date(2026, 10, 9),
                meal_type="lunch",
            ),
            MealOrder(
                family_id=family.id,
                meal_date=date(2026, 10, 9),
                meal_type="lunch",
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_selector_is_unique_per_meal_item_and_openid(session):
    family = Family(name="幸福小家", owner_openid="chef-openid")
    order = MealOrder(
        family=family,
        meal_date=date(2026, 10, 9),
        meal_type="dinner",
    )
    item = MealOrderItem(
        meal_order=order,
        dish_name="番茄炒蛋",
        category_name="热菜",
        ingredients_snapshot=[],
    )
    item.selectors.extend(
        [
            MealItemSelector(openid="member-openid", nickname="妈妈"),
            MealItemSelector(openid="member-openid", nickname="妈妈"),
        ]
    )
    session.add(family)

    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_openid_can_have_only_one_active_family_membership(session):
    family_a = Family(name="A家", owner_openid="chef-a")
    family_b = Family(name="B家", owner_openid="chef-b")
    session.add_all([family_a, family_b])
    await session.flush()
    session.add_all(
        [
            FamilyMember(
                family_id=family_a.id,
                openid="same-openid",
                nickname="成员",
                role="member",
                status="active",
            ),
            FamilyMember(
                family_id=family_b.id,
                openid="same-openid",
                nickname="成员",
                role="member",
                status="active",
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        await session.commit()


def test_all_utc_datetime_columns_are_timezone_aware():
    assert FamilyMember.__table__.c.joined_at.type.timezone is True
    assert Invitation.__table__.c.expires_at.type.timezone is True
    assert Invitation.__table__.c.created_at.type.timezone is True
    assert MealItemSelector.__table__.c.selected_at.type.timezone is True
    assert IdempotencyRecord.__table__.c.created_at.type.timezone is True
