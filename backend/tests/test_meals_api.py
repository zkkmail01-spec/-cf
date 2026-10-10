import asyncio
from datetime import date

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import get_session
from app.api.deps import CurrentMember
from app.db.base import Base
from app.main import create_app
from app.models.dish import Dish, DishCategory, DishIngredient
from app.models.family import FamilyMember
from app.models.family import Family
from tests.conftest import wx_headers
from tests.test_dishes_api import create_category, create_dish, create_family
from app.services import meals as meal_service


async def seed_member(session_factory, family_id: str, openid: str, nickname: str) -> None:
    async with session_factory() as session:
        session.add(
            FamilyMember(
                family_id=family_id,
                openid=openid,
                nickname=nickname,
                role="member",
                status="active",
            )
        )
        await session.commit()


def select_dish(client, openid: str, dish_id: str, key: str, meal_type: str = "lunch"):
    return client.put(
        f"/api/v1/meals/2026-10-09/{meal_type}/selections/{dish_id}",
        headers={**wx_headers(openid), "Idempotency-Key": key},
    )


def setup_catalog(client):
    family = create_family(client, "chef-a")
    category = create_category(client, "chef-a", "热菜")
    dish = create_dish(client, "chef-a", category["id"])
    return family, dish


def test_invalid_date_and_meal_type_are_rejected(client):
    _, dish = setup_catalog(client)

    bad_date = client.put(
        f"/api/v1/meals/not-a-date/lunch/selections/{dish['id']}",
        headers={**wx_headers("chef-a"), "Idempotency-Key": "bad-date"},
    )
    bad_type = client.put(
        f"/api/v1/meals/2026-10-09/snack/selections/{dish['id']}",
        headers={**wx_headers("chef-a"), "Idempotency-Key": "bad-type"},
    )

    assert bad_date.status_code == 422
    assert bad_type.status_code == 422


def test_two_members_share_one_item_and_cancel_independently(client, session_factory):
    family, dish = setup_catalog(client)
    asyncio.run(seed_member(session_factory, family["id"], "member-b", "爸爸"))

    first = select_dish(client, "chef-a", dish["id"], "select-chef")
    second = select_dish(client, "member-b", dish["id"], "select-member")

    assert first.status_code == 200
    assert second.status_code == 200
    item = second.json()["meals"]["lunch"]["items"][0]
    assert item["dishName"] == "番茄炒蛋"
    assert {selector["openid"] for selector in item["selectors"]} == {
        "chef-a",
        "member-b",
    }
    assert second.json()["meals"]["lunch"]["version"] == 2

    remove_first = client.delete(
        f"/api/v1/meals/2026-10-09/lunch/selections/{dish['id']}",
        headers={**wx_headers("chef-a"), "Idempotency-Key": "remove-chef"},
    )
    assert [s["openid"] for s in remove_first.json()["meals"]["lunch"]["items"][0]["selectors"]] == ["member-b"]

    remove_last = client.delete(
        f"/api/v1/meals/2026-10-09/lunch/selections/{dish['id']}",
        headers={**wx_headers("member-b"), "Idempotency-Key": "remove-member"},
    )
    assert remove_last.json()["meals"]["lunch"]["items"] == []


def test_repeated_idempotency_key_returns_first_result_without_duplicate(client):
    _, dish = setup_catalog(client)

    first = select_dish(client, "chef-a", dish["id"], "same-key")
    second = select_dish(client, "chef-a", dish["id"], "same-key")

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    selectors = second.json()["meals"]["lunch"]["items"][0]["selectors"]
    assert len(selectors) == 1
    assert second.json()["meals"]["lunch"]["version"] == 1


def test_idempotency_key_cannot_be_reused_for_different_request(client):
    _, dish = setup_catalog(client)
    select_dish(client, "chef-a", dish["id"], "reused-key", "lunch")

    response = select_dish(client, "chef-a", dish["id"], "reused-key", "dinner")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_history_keeps_snapshot_after_dish_changes(client):
    _, dish = setup_catalog(client)
    select_dish(client, "chef-a", dish["id"], "snapshot")
    client.patch(
        f"/api/v1/dishes/{dish['id']}",
        headers=wx_headers("chef-a"),
        json={"name": "改名后的菜"},
    )
    client.delete(f"/api/v1/dishes/{dish['id']}", headers=wx_headers("chef-a"))

    history = client.get("/api/v1/meals/2026-10-09", headers=wx_headers("chef-a"))

    assert history.status_code == 200
    assert history.json()["meals"]["lunch"]["items"][0]["dishName"] == "番茄炒蛋"


def test_calendar_repeat_and_frequent_are_family_scoped(client):
    _, dish_a = setup_catalog(client)
    select_dish(client, "chef-a", dish_a["id"], "a-lunch")
    repeated = client.post(
        "/api/v1/meals/repeat",
        headers={**wx_headers("chef-a"), "Idempotency-Key": "repeat-a"},
        json={
            "sourceDate": "2026-10-09",
            "sourceMealType": "lunch",
            "targetDate": "2026-10-10",
            "targetMealType": "dinner",
        },
    )
    assert repeated.status_code == 200
    assert repeated.json()["meals"]["dinner"]["items"][0]["dishName"] == "番茄炒蛋"

    calendar = client.get(
        "/api/v1/meals/calendar?month=2026-10", headers=wx_headers("chef-a")
    )
    assert calendar.json()["dates"] == ["2026-10-09", "2026-10-10"]

    create_family(client, "chef-b", "B家")
    category_b = create_category(client, "chef-b", "热菜")
    dish_b = create_dish(client, "chef-b", category_b["id"], "B家菜")
    select_dish(client, "chef-b", dish_b["id"], "b-lunch")

    frequent_a = client.get("/api/v1/dishes/frequent", headers=wx_headers("chef-a"))
    assert [(row["dishName"], row["count"]) for row in frequent_a.json()] == [
        ("番茄炒蛋", 2)
    ]


@pytest.mark.asyncio
async def test_concurrent_selectors_are_merged_without_duplicate_items(tmp_path):
    database_url = f"sqlite+aiosqlite:///{(tmp_path / 'concurrent.db').as_posix()}"
    engine = create_async_engine(database_url, connect_args={"timeout": 10})
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as session:
        family = Family(name="并发家庭", owner_openid="chef-a")
        family.members.extend(
            [
                FamilyMember(openid="chef-a", nickname="妈妈", role="chef"),
                FamilyMember(openid="member-b", nickname="爸爸", role="member"),
            ]
        )
        session.add(family)
        await session.flush()
        category = DishCategory(family_id=family.id, name="热菜")
        dish = Dish(
            family_id=family.id,
            category=category,
            name="番茄炒蛋",
            created_by="chef-a",
            ingredients=[DishIngredient(name="番茄", quantity=2, unit="个")],
        )
        session.add(dish)
        await session.commit()
        dish_id = dish.id

    app = create_app()

    async def override_session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
        path = f"/api/v1/meals/2026-10-09/lunch/selections/{dish_id}"
        responses = await asyncio.gather(
            api.put(path, headers={**wx_headers("chef-a"), "Idempotency-Key": "c-a"}),
            api.put(path, headers={**wx_headers("member-b"), "Idempotency-Key": "c-b"}),
        )
        assert [response.status_code for response in responses] == [200, 200]
        final = await api.get("/api/v1/meals/2026-10-09", headers=wx_headers("chef-a"))

    items = final.json()["meals"]["lunch"]["items"]
    assert len(items) == 1
    assert {row["openid"] for row in items[0]["selectors"]} == {"chef-a", "member-b"}
    await engine.dispose()


@pytest.mark.asyncio
async def test_stale_cancellation_does_not_remove_another_members_selection(tmp_path):
    database_url = f"sqlite+aiosqlite:///{(tmp_path / 'stale-cancel.db').as_posix()}"
    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as setup:
        family = Family(name="并发家庭", owner_openid="member-a")
        family.members.extend(
            [
                FamilyMember(openid="member-a", nickname="A", role="chef"),
                FamilyMember(openid="member-b", nickname="B", role="member"),
            ]
        )
        setup.add(family)
        await setup.flush()
        category = DishCategory(family_id=family.id, name="热菜")
        dish = Dish(
            family_id=family.id,
            category=category,
            name="番茄炒蛋",
            created_by="member-a",
            ingredients=[DishIngredient(name="鸡蛋", quantity=2, unit="个")],
        )
        setup.add(dish)
        await setup.commit()
        family_id, dish_id = family.id, dish.id

    member_a = CurrentMember("a-id", family_id, "member-a", "A", None, "chef")
    member_b = CurrentMember("b-id", family_id, "member-b", "B", None, "member")
    async with factory() as session_a:
        await meal_service.add_selection(
            session_a, member_a, date(2026, 10, 10), "lunch", dish_id
        )
        await session_a.commit()
        await meal_service.get_order(session_a, family_id, date(2026, 10, 10), "lunch")
        async with factory() as session_b:
            await meal_service.add_selection(
                session_b, member_b, date(2026, 10, 10), "lunch", dish_id
            )
            await session_b.commit()
        await meal_service.remove_selection(
            session_a, member_a, date(2026, 10, 10), "lunch", dish_id
        )
        await session_a.commit()

    async with factory() as verify:
        final = await meal_service.get_day(verify, member_b, date(2026, 10, 10))
    selectors = final["meals"]["lunch"]["items"][0]["selectors"]
    assert [row["openid"] for row in selectors] == ["member-b"]
    await engine.dispose()


def test_mutation_rolls_back_when_idempotency_record_cannot_be_saved(client, monkeypatch):
    _, dish = setup_catalog(client)

    async def fail_to_save(*_args, **_kwargs):
        raise RuntimeError("simulated crash before idempotency persistence")

    monkeypatch.setattr(meal_service, "save_idempotent_response", fail_to_save)
    with pytest.raises(RuntimeError):
        select_dish(client, "chef-a", dish["id"], "atomic-key")

    history = client.get(
        "/api/v1/meals/2026-10-09", headers=wx_headers("chef-a")
    )
    assert history.json()["meals"]["lunch"]["items"] == []
