from tests.conftest import wx_headers


def test_complete_two_member_family_meal_journey_is_isolated(client):
    family = client.post(
        "/api/v1/families",
        headers=wx_headers("journey-chef"),
        json={"name": "周末小家", "nickname": "妈妈"},
    )
    assert family.status_code == 201

    category = client.post(
        "/api/v1/categories",
        headers=wx_headers("journey-chef"),
        json={"name": "热菜", "sortOrder": 10},
    )
    assert category.status_code == 201

    dish = client.post(
        "/api/v1/dishes",
        headers=wx_headers("journey-chef"),
        json={
            "categoryId": category.json()["id"],
            "name": "番茄炒蛋",
            "ingredients": [
                {"name": "番茄", "quantity": "2", "unit": "个"},
                {"name": "鸡蛋", "quantity": "3", "unit": "个"},
            ],
        },
    )
    assert dish.status_code == 201

    invitation = client.post(
        "/api/v1/invitations",
        headers=wx_headers("journey-chef"),
        json={"expiresInHours": 24, "maxUses": 2},
    )
    assert invitation.status_code == 201
    joined = client.post(
        f"/api/v1/invitations/{invitation.json()['code']}/join",
        headers=wx_headers("journey-member"),
        json={"nickname": "爸爸"},
    )
    assert joined.status_code == 200

    path = f"/api/v1/meals/2026-10-10/lunch/selections/{dish.json()['id']}"
    chef_selection = client.put(
        path,
        headers={**wx_headers("journey-chef"), "Idempotency-Key": "journey-chef-lunch"},
    )
    member_selection = client.put(
        path,
        headers={**wx_headers("journey-member"), "Idempotency-Key": "journey-member-lunch"},
    )
    assert chef_selection.status_code == member_selection.status_code == 200

    history = client.get(
        "/api/v1/meals/2026-10-10", headers=wx_headers("journey-member")
    )
    lunch_items = history.json()["meals"]["lunch"]["items"]
    assert len(lunch_items) == 1
    assert {row["nickname"] for row in lunch_items[0]["selectors"]} == {"妈妈", "爸爸"}

    shopping = client.get(
        "/api/v1/shopping?start=2026-10-10&end=2026-10-10",
        headers=wx_headers("journey-member"),
    )
    assert {(row["name"], row["unit"]): row["quantity"] for row in shopping.json()["items"]} == {
        ("番茄", "个"): "2",
        ("鸡蛋", "个"): "3",
    }

    other_family = client.post(
        "/api/v1/families",
        headers=wx_headers("other-chef"),
        json={"name": "另一家", "nickname": "邻居"},
    )
    assert other_family.status_code == 201
    cross_family_dish = client.get(
        f"/api/v1/dishes/{dish.json()['id']}", headers=wx_headers("other-chef")
    )
    cross_family_history = client.get(
        "/api/v1/meals/2026-10-10", headers=wx_headers("other-chef")
    )
    cross_family_shopping = client.get(
        "/api/v1/shopping?start=2026-10-10&end=2026-10-10",
        headers=wx_headers("other-chef"),
    )
    assert cross_family_dish.status_code == 404
    assert cross_family_history.json()["meals"]["lunch"]["items"] == []
    assert cross_family_shopping.json()["items"] == []
