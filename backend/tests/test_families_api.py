from sqlalchemy import select

from app.models.family import Family
from tests.conftest import wx_headers


def test_session_requires_identity(client):
    response = client.get("/api/v1/session")

    assert response.status_code == 401


def test_create_family_also_creates_chef_membership(client):
    response = client.post(
        "/api/v1/families",
        headers=wx_headers("chef-a"),
        json={"name": "幸福小家", "nickname": "妈妈", "familyId": "forged"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "幸福小家"
    assert body["currentMember"]["role"] == "chef"
    assert body["currentMember"]["openid"] == "chef-a"
    assert body["id"] != "forged"

    session = client.get("/api/v1/session", headers=wx_headers("chef-a"))
    assert session.status_code == 200
    assert session.json()["family"]["id"] == body["id"]


def test_non_member_cannot_read_current_family(client):
    response = client.get(
        "/api/v1/families/current", headers=wx_headers("not-a-member")
    )

    assert response.status_code == 403


def test_forged_family_id_is_ignored_and_cannot_cross_family(client):
    family_a = client.post(
        "/api/v1/families",
        headers=wx_headers("chef-a"),
        json={"name": "A家", "nickname": "A"},
    ).json()
    family_b = client.post(
        "/api/v1/families",
        headers=wx_headers("chef-b"),
        json={"name": "B家", "nickname": "B"},
    ).json()

    response = client.patch(
        "/api/v1/families/current",
        headers=wx_headers("chef-a"),
        json={"name": "A家新名字", "familyId": family_b["id"]},
    )

    assert response.status_code == 200
    assert response.json()["id"] == family_a["id"]
    assert response.json()["name"] == "A家新名字"
    unchanged_b = client.get(
        "/api/v1/families/current", headers=wx_headers("chef-b")
    ).json()
    assert unchanged_b["name"] == "B家"


def test_member_can_update_only_own_profile(client):
    client.post(
        "/api/v1/families",
        headers=wx_headers("chef-a"),
        json={"name": "幸福小家", "nickname": "旧昵称"},
    )

    response = client.patch(
        "/api/v1/members/me",
        headers=wx_headers("chef-a"),
        json={"nickname": "新昵称", "avatarUrl": "https://example.test/avatar.png"},
    )

    assert response.status_code == 200
    assert response.json()["nickname"] == "新昵称"
    assert response.json()["avatarUrl"].endswith("avatar.png")


def test_sole_chef_cannot_leave_family(client):
    client.post(
        "/api/v1/families",
        headers=wx_headers("chef-a"),
        json={"name": "幸福小家", "nickname": "妈妈"},
    )

    response = client.post(
        "/api/v1/families/current/leave", headers=wx_headers("chef-a")
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SOLE_CHEF_CANNOT_LEAVE"
