import asyncio

from sqlalchemy import select

from app.models.dish import Dish
from app.models.family import FamilyMember
from tests.conftest import wx_headers


def create_family(client, openid: str, name: str = "幸福小家") -> dict:
    response = client.post(
        "/api/v1/families",
        headers=wx_headers(openid),
        json={"name": name, "nickname": openid},
    )
    assert response.status_code == 201
    return response.json()


async def seed_member(session_factory, family_id: str, openid: str) -> None:
    async with session_factory() as session:
        session.add(
            FamilyMember(
                family_id=family_id,
                openid=openid,
                nickname="家庭成员",
                role="member",
                status="active",
            )
        )
        await session.commit()


def create_category(client, chef: str, name: str, sort_order: int = 0) -> dict:
    response = client.post(
        "/api/v1/categories",
        headers=wx_headers(chef),
        json={"name": name, "sortOrder": sort_order},
    )
    assert response.status_code == 201
    return response.json()


def create_dish(
    client,
    chef: str,
    category_id: str,
    name: str = "番茄炒蛋",
    ingredients: list[dict] | None = None,
) -> dict:
    response = client.post(
        "/api/v1/dishes",
        headers=wx_headers(chef),
        json={
            "name": name,
            "categoryId": category_id,
            "imageFileId": "cloud://images/tomato.jpg",
            "description": "少糖",
            "ingredients": ingredients
            or [
                {"name": "番茄", "quantity": "2", "unit": "个"},
                {"name": "鸡蛋", "quantity": "3", "unit": "个"},
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_categories_are_sorted_and_members_can_list(client, session_factory):
    family = create_family(client, "chef-a")
    asyncio.run(seed_member(session_factory, family["id"], "member-a"))
    create_category(client, "chef-a", "汤类", 20)
    create_category(client, "chef-a", "热菜", 10)

    response = client.get("/api/v1/categories", headers=wx_headers("member-a"))

    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["热菜", "汤类"]


def test_member_cannot_mutate_catalog(client, session_factory):
    family = create_family(client, "chef-a")
    asyncio.run(seed_member(session_factory, family["id"], "member-a"))

    response = client.post(
        "/api/v1/categories",
        headers=wx_headers("member-a"),
        json={"name": "热菜", "sortOrder": 1},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CHEF_REQUIRED"


def test_dish_searches_by_name_or_ingredient(client):
    create_family(client, "chef-a")
    category = create_category(client, "chef-a", "热菜")
    create_dish(client, "chef-a", category["id"])
    create_dish(
        client,
        "chef-a",
        category["id"],
        "清蒸鲈鱼",
        [{"name": "鲈鱼", "quantity": "1", "unit": "条"}],
    )

    by_name = client.get(
        "/api/v1/dishes?query=鲈鱼", headers=wx_headers("chef-a")
    )
    by_ingredient = client.get(
        "/api/v1/dishes?query=鸡蛋", headers=wx_headers("chef-a")
    )

    assert [dish["name"] for dish in by_name.json()] == ["清蒸鲈鱼"]
    assert [dish["name"] for dish in by_ingredient.json()] == ["番茄炒蛋"]


def test_dish_replaces_ingredients_in_one_update(client):
    create_family(client, "chef-a")
    category = create_category(client, "chef-a", "热菜")
    dish = create_dish(client, "chef-a", category["id"])

    response = client.patch(
        f"/api/v1/dishes/{dish['id']}",
        headers=wx_headers("chef-a"),
        json={
            "ingredients": [
                {"name": "番茄", "quantity": "3", "unit": "个", "note": "熟透"}
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["ingredients"] == [
        {
            "id": response.json()["ingredients"][0]["id"],
            "name": "番茄",
            "quantity": "3",
            "unit": "个",
            "note": "熟透",
            "sortOrder": 0,
        }
    ]


def test_cross_family_category_is_rejected(client):
    create_family(client, "chef-a", "A家")
    create_family(client, "chef-b", "B家")
    category_b = create_category(client, "chef-b", "热菜")

    response = client.post(
        "/api/v1/dishes",
        headers=wx_headers("chef-a"),
        json={
            "name": "越权菜",
            "categoryId": category_b["id"],
            "ingredients": [{"name": "盐", "quantity": "1", "unit": "克"}],
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CATEGORY_NOT_FOUND"


def test_non_positive_ingredient_quantity_is_rejected(client):
    create_family(client, "chef-a")
    category = create_category(client, "chef-a", "热菜")

    response = client.post(
        "/api/v1/dishes",
        headers=wx_headers("chef-a"),
        json={
            "name": "错误菜品",
            "categoryId": category["id"],
            "ingredients": [{"name": "盐", "quantity": "0", "unit": "克"}],
        },
    )

    assert response.status_code == 422


def test_deactivated_dish_disappears_but_row_is_retained(client, session_factory):
    create_family(client, "chef-a")
    category = create_category(client, "chef-a", "热菜")
    dish = create_dish(client, "chef-a", category["id"])

    deleted = client.delete(
        f"/api/v1/dishes/{dish['id']}", headers=wx_headers("chef-a")
    )
    listed = client.get("/api/v1/dishes", headers=wx_headers("chef-a"))

    assert deleted.status_code == 204
    assert listed.json() == []

    async def load_soft_deleted():
        async with session_factory() as session:
            return await session.scalar(select(Dish).where(Dish.id == dish["id"]))

    retained = asyncio.run(load_soft_deleted())
    assert retained is not None
    assert retained.is_active is False
