from sqlalchemy import func, select

from app.models.dish import Dish, DishCategory
from app.models.family import Family, FamilyMember
from scripts.seed_demo import DEMO_OWNER_OPENID, seed_demo


async def test_demo_seed_is_deterministic_and_idempotent(session_factory):
    async with session_factory() as session:
        first = await seed_demo(session)
        second = await seed_demo(session)

        assert first is True
        assert second is False
        family = await session.scalar(
            select(Family).where(Family.owner_openid == DEMO_OWNER_OPENID)
        )
        assert family is not None
        assert family.name == "温馨小家"
        assert await session.scalar(select(func.count(FamilyMember.id))) == 2
        assert await session.scalar(select(func.count(DishCategory.id))) == 4
        assert await session.scalar(select(func.count(Dish.id))) == 6
