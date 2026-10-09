import asyncio
import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.family import FamilyMember
from app.models.invitation import Invitation
from tests.conftest import wx_headers
from tests.test_dishes_api import create_family


def create_invitation(client, chef: str = "chef-a", max_uses: int = 3) -> dict:
    response = client.post(
        "/api/v1/invitations",
        headers=wx_headers(chef),
        json={"expiresInHours": 24, "maxUses": max_uses},
    )
    assert response.status_code == 201
    return response.json()


def join(client, code: str, openid: str, nickname: str = "新成员"):
    return client.post(
        f"/api/v1/invitations/{code}/join",
        headers=wx_headers(openid),
        json={"nickname": nickname},
    )


def test_invitation_stores_only_sha256_and_preview_is_neutral(client, session_factory):
    family = create_family(client, "chef-a")
    invitation = create_invitation(client)

    async def load_record():
        async with session_factory() as session:
            return await session.get(Invitation, invitation["id"])

    record = asyncio.run(load_record())
    assert record.code_hash == hashlib.sha256(invitation["code"].encode()).hexdigest()
    assert record.code_hash != invitation["code"]

    preview = client.get(
        f"/api/v1/invitations/{invitation['code']}/preview",
        headers=wx_headers("guest"),
    )
    assert preview.status_code == 200
    assert preview.json() == {
        "familyName": family["name"],
        "familyAvatarFileId": None,
        "inviterNickname": "chef-a",
        "expiresAt": invitation["expiresAt"],
    }


def test_member_cannot_create_revoke_or_remove_members(client, session_factory):
    family = create_family(client, "chef-a")
    invitation = create_invitation(client)
    joined = join(client, invitation["code"], "member-a")
    assert joined.status_code == 200

    create_attempt = client.post(
        "/api/v1/invitations",
        headers=wx_headers("member-a"),
        json={"expiresInHours": 24, "maxUses": 1},
    )
    revoke_attempt = client.delete(
        f"/api/v1/invitations/{invitation['id']}",
        headers=wx_headers("member-a"),
    )
    remove_attempt = client.delete(
        f"/api/v1/members/{family['currentMember']['id']}",
        headers=wx_headers("member-a"),
    )

    assert create_attempt.status_code == 403
    assert revoke_attempt.status_code == 403
    assert remove_attempt.status_code == 403


def test_join_increments_usage_and_repeated_join_is_distinct(client):
    create_family(client, "chef-a")
    invitation = create_invitation(client)

    first = join(client, invitation["code"], "member-a", "爸爸")
    repeated = join(client, invitation["code"], "member-a", "爸爸")

    assert first.status_code == 200
    assert first.json()["role"] == "member"
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "ALREADY_JOINED"


def test_invitation_expired_revoked_and_exhausted_errors(client, session_factory):
    create_family(client, "chef-a")

    expired = create_invitation(client)

    async def expire_record():
        async with session_factory() as session:
            record = await session.get(Invitation, expired["id"])
            record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            await session.commit()

    asyncio.run(expire_record())
    expired_join = join(client, expired["code"], "guest-expired")
    assert expired_join.status_code == 410
    assert expired_join.json()["error"]["code"] == "INVITE_EXPIRED"

    revoked = create_invitation(client)
    assert client.delete(
        f"/api/v1/invitations/{revoked['id']}", headers=wx_headers("chef-a")
    ).status_code == 204
    revoked_join = join(client, revoked["code"], "guest-revoked")
    assert revoked_join.status_code == 410
    assert revoked_join.json()["error"]["code"] == "INVITE_REVOKED"

    exhausted = create_invitation(client, max_uses=1)
    assert join(client, exhausted["code"], "first-guest").status_code == 200
    exhausted_join = join(client, exhausted["code"], "second-guest")
    assert exhausted_join.status_code == 410
    assert exhausted_join.json()["error"]["code"] == "INVITE_EXHAUSTED"


def test_user_in_another_family_gets_already_in_family(client):
    create_family(client, "chef-a", "A家")
    invitation_a = create_invitation(client, "chef-a")
    create_family(client, "chef-b", "B家")

    response = join(client, invitation_a["code"], "chef-b")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ALREADY_IN_FAMILY"


def test_chef_can_list_and_remove_member_but_not_self(client):
    family = create_family(client, "chef-a")
    invitation = create_invitation(client)
    joined = join(client, invitation["code"], "member-a", "爸爸").json()

    members = client.get("/api/v1/members", headers=wx_headers("chef-a"))
    assert [row["nickname"] for row in members.json()] == ["chef-a", "爸爸"]

    removed = client.delete(
        f"/api/v1/members/{joined['id']}", headers=wx_headers("chef-a")
    )
    remove_self = client.delete(
        f"/api/v1/members/{family['currentMember']['id']}",
        headers=wx_headers("chef-a"),
    )

    assert removed.status_code == 204
    assert remove_self.status_code == 409
    assert remove_self.json()["error"]["code"] == "CANNOT_REMOVE_CHEF"
