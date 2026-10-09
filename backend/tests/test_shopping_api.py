from tests.conftest import wx_headers
from tests.test_dishes_api import create_category, create_dish, create_family
from tests.test_meals_api import select_dish


def test_shopping_aggregates_same_name_and_unit_but_keeps_units_separate(client):
    create_family(client, "chef-a")
    category = create_category(client, "chef-a", "热菜")
    dish_a = create_dish(
        client,
        "chef-a",
        category["id"],
        "番茄炒蛋",
        [
            {"name": "番茄", "quantity": "2", "unit": "个"},
            {"name": "盐", "quantity": "3", "unit": "克"},
        ],
    )
    dish_b = create_dish(
        client,
        "chef-a",
        category["id"],
        "番茄汤",
        [
            {"name": "番茄", "quantity": "1", "unit": "个"},
            {"name": "盐", "quantity": "1", "unit": "勺"},
        ],
    )
    select_dish(client, "chef-a", dish_a["id"], "shop-a")
    select_dish(client, "chef-a", dish_b["id"], "shop-b")

    response = client.get(
        "/api/v1/shopping?start=2026-10-09&end=2026-10-09",
        headers=wx_headers("chef-a"),
    )

    assert response.status_code == 200
    rows = {(row["name"], row["unit"]): row["quantity"] for row in response.json()["items"]}
    assert rows[("番茄", "个")] == "3"
    assert rows[("盐", "克")] == "3"
    assert rows[("盐", "勺")] == "1"


def test_shopping_checked_keys_persist_per_family_and_range(client):
    create_family(client, "chef-a")

    saved = client.put(
        "/api/v1/shopping/checks",
        headers={**wx_headers("chef-a"), "Idempotency-Key": "checks-a"},
        json={
            "rangeStart": "2026-10-09",
            "rangeEnd": "2026-10-10",
            "checkedKeys": ["番茄|个"],
        },
    )
    loaded = client.get(
        "/api/v1/shopping?start=2026-10-09&end=2026-10-10",
        headers=wx_headers("chef-a"),
    )

    assert saved.status_code == 200
    assert loaded.json()["checkedKeys"] == ["番茄|个"]

    create_family(client, "chef-b", "B家")
    other = client.get(
        "/api/v1/shopping?start=2026-10-09&end=2026-10-10",
        headers=wx_headers("chef-b"),
    )
    assert other.json()["checkedKeys"] == []
