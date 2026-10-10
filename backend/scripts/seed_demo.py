import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionFactory
from app.models.dish import Dish, DishCategory, DishIngredient
from app.models.family import Family, FamilyMember


DEMO_OWNER_OPENID = "demo-chef-openid"

DEMO_CATALOG = {
    "热菜": [
        ("番茄炒蛋", [("番茄", "2", "个"), ("鸡蛋", "3", "个")]),
        ("糖醋排骨", [("排骨", "500", "克"), ("冰糖", "30", "克")]),
    ],
    "凉菜": [
        ("拍黄瓜", [("黄瓜", "2", "根"), ("大蒜", "3", "瓣")]),
    ],
    "汤类": [
        ("玉米排骨汤", [("玉米", "2", "根"), ("排骨", "400", "克")]),
        ("紫菜蛋花汤", [("紫菜", "15", "克"), ("鸡蛋", "2", "个")]),
    ],
    "主食": [
        ("扬州炒饭", [("米饭", "3", "碗"), ("鸡蛋", "2", "个")]),
    ],
}


async def seed_demo(session: AsyncSession) -> bool:
    existing = await session.scalar(
        select(Family.id).where(Family.owner_openid == DEMO_OWNER_OPENID)
    )
    if existing:
        return False

    family = Family(name="温馨小家", owner_openid=DEMO_OWNER_OPENID)
    family.members.extend(
        [
            FamilyMember(
                openid=DEMO_OWNER_OPENID,
                nickname="妈妈",
                role="chef",
                status="active",
            ),
            FamilyMember(
                openid="demo-member-openid",
                nickname="爸爸",
                role="member",
                status="active",
            ),
        ]
    )
    session.add(family)
    await session.flush()

    for sort_order, (category_name, dishes) in enumerate(DEMO_CATALOG.items(), start=1):
        category = DishCategory(
            family_id=family.id,
            name=category_name,
            sort_order=sort_order * 10,
        )
        session.add(category)
        await session.flush()
        for dish_name, ingredients in dishes:
            dish = Dish(
                family_id=family.id,
                category_id=category.id,
                name=dish_name,
                description="家庭演示菜品",
                created_by=DEMO_OWNER_OPENID,
            )
            dish.ingredients = [
                DishIngredient(
                    name=name,
                    quantity=Decimal(quantity),
                    unit=unit,
                    sort_order=index,
                )
                for index, (name, quantity, unit) in enumerate(ingredients)
            ]
            session.add(dish)

    await session.commit()
    return True


async def main() -> None:
    async with SessionFactory() as session:
        created = await seed_demo(session)
    print("演示数据已创建" if created else "演示数据已存在，未重复创建")


if __name__ == "__main__":
    asyncio.run(main())
