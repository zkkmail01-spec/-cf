from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from types import SimpleNamespace
from datetime import datetime, timezone

from app.api.deps import CurrentMember, find_current_member
from app.core.errors import AppError
from app.core.identity import CurrentIdentity
from app.models.family import Family, FamilyMember
from app.schemas.family import FamilyCreate, FamilyUpdate, MemberUpdate


def _entity(row: dict) -> SimpleNamespace:
    return SimpleNamespace(id=row["_id"], **{k: v for k, v in row.items() if k != "_id"})


async def create_family(
    session: AsyncSession,
    identity: CurrentIdentity,
    payload: FamilyCreate,
) -> tuple[Family, FamilyMember]:
    if hasattr(session, "store"):
        existing = await find_current_member(identity, session)
        if existing is not None:
            raise AppError("ALREADY_IN_FAMILY", "你已经加入了一个家庭", 409)
        now = datetime.now(timezone.utc).isoformat()
        family = await session.store.create("families", {"name": payload.name.strip(), "owner_openid": identity.openid, "avatar_file_id": None, "created_at": now})
        member = await session.store.create("family_members", {"family_id": family["_id"], "openid": identity.openid, "nickname": payload.nickname.strip(), "avatar_url": payload.avatar_url, "role": "chef", "status": "active", "joined_at": now})
        return _entity(family), _entity(member)
    existing = await find_current_member(identity, session)
    if existing is not None:
        raise AppError("ALREADY_IN_FAMILY", "你已经加入了一个家庭", 409)

    family = Family(name=payload.name.strip(), owner_openid=identity.openid)
    member = FamilyMember(
        family=family,
        openid=identity.openid,
        nickname=payload.nickname.strip(),
        avatar_url=payload.avatar_url,
        role="chef",
        status="active",
    )
    session.add(family)
    await session.commit()
    await session.refresh(family)
    await session.refresh(member)
    return family, member


async def get_family(session: AsyncSession, member: CurrentMember) -> Family:
    if hasattr(session, "store"):
        family = await session.store.get("families", member.family_id)
        if family is None:
            raise AppError("FAMILY_NOT_FOUND", "家庭不存在", 404)
        return _entity(family)
    family = await session.get(Family, member.family_id)
    if family is None:
        raise AppError("FAMILY_NOT_FOUND", "家庭不存在", 404)
    return family


async def update_family(
    session: AsyncSession,
    member: CurrentMember,
    payload: FamilyUpdate,
) -> Family:
    if hasattr(session, "store"):
        family = await get_family(session, member)
        patch = {}
        if payload.name is not None:
            patch["name"] = payload.name.strip()
        if "avatar_file_id" in payload.model_fields_set:
            patch["avatar_file_id"] = payload.avatar_file_id
        row = await session.store.update("families", family.id, patch) if patch else await session.store.get("families", family.id)
        return _entity(row)
    family = await get_family(session, member)
    if payload.name is not None:
        family.name = payload.name.strip()
    if "avatar_file_id" in payload.model_fields_set:
        family.avatar_file_id = payload.avatar_file_id
    await session.commit()
    await session.refresh(family)
    return family


async def update_member_profile(
    session: AsyncSession,
    member: CurrentMember,
    payload: MemberUpdate,
) -> FamilyMember:
    if hasattr(session, "store"):
        rows = await session.store.list("family_members", {"_id": member.member_id, "status": "active"})
        if not rows:
            raise AppError("NOT_FAMILY_MEMBER", "你还没有加入家庭", 403)
        patch = {}
        if payload.nickname is not None:
            patch["nickname"] = payload.nickname.strip()
        if "avatar_url" in payload.model_fields_set:
            patch["avatar_url"] = payload.avatar_url
        row = await session.store.update("family_members", member.member_id, patch) if patch else rows[0]
        return _entity(row)
    db_member = await session.get(FamilyMember, member.member_id)
    if db_member is None or db_member.status != "active":
        raise AppError("NOT_FAMILY_MEMBER", "你还没有加入家庭", 403)
    if payload.nickname is not None:
        db_member.nickname = payload.nickname.strip()
    if "avatar_url" in payload.model_fields_set:
        db_member.avatar_url = payload.avatar_url
    await session.commit()
    await session.refresh(db_member)
    return db_member


async def leave_family(session: AsyncSession, member: CurrentMember) -> None:
    if hasattr(session, "store"):
        active = await session.store.list("family_members", {"family_id": member.family_id, "status": "active"})
        if member.role == "chef" and sum(row.get("role") == "chef" for row in active) == 1:
            raise AppError("SOLE_CHEF_CANNOT_LEAVE", "唯一的厨师长不能退出家庭", 409)
        await session.store.update("family_members", member.member_id, {"status": "left"})
        return
    if member.role == "chef":
        result = await session.execute(
            select(FamilyMember.id).where(
                FamilyMember.family_id == member.family_id,
                FamilyMember.role == "chef",
                FamilyMember.status == "active",
            )
        )
        if len(result.scalars().all()) == 1:
            raise AppError(
                "SOLE_CHEF_CANNOT_LEAVE",
                "唯一的厨师长不能退出家庭",
                409,
            )
    db_member = await session.get(FamilyMember, member.member_id)
    if db_member is None:
        raise AppError("NOT_FAMILY_MEMBER", "你还没有加入家庭", 403)
    db_member.status = "left"
    await session.commit()
