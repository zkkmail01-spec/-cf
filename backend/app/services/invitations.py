import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from types import SimpleNamespace

from app.api.deps import CurrentMember, find_current_member
from app.core.errors import AppError
from app.core.identity import CurrentIdentity
from app.db.base import utc_now
from app.models.family import Family, FamilyMember
from app.models.invitation import Invitation
from app.schemas.invitation import InvitationCreate, InvitationJoin


def _entity(row: dict) -> SimpleNamespace:
    return SimpleNamespace(id=row["_id"], **{k: v for k, v in row.items() if k != "_id"})


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def aware(value: datetime) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def validate_invitation_state(invitation: Invitation) -> None:
    if invitation.status == "revoked":
        raise AppError("INVITE_REVOKED", "邀请已被撤销", 410)
    if invitation.status == "expired" or aware(invitation.expires_at) <= utc_now():
        raise AppError("INVITE_EXPIRED", "邀请已过期", 410)
    if invitation.used_count >= invitation.max_uses:
        raise AppError("INVITE_EXHAUSTED", "邀请使用次数已用完", 410)


async def create_invitation(
    session: AsyncSession,
    member: CurrentMember,
    payload: InvitationCreate,
) -> tuple[Invitation, str]:
    if hasattr(session, "store"):
        code = secrets.token_urlsafe(24)
        row = await session.store.create("invitations", {"family_id": member.family_id, "created_by": member.openid, "code_hash": hash_code(code), "expires_at": (utc_now() + timedelta(hours=payload.expires_in_hours)).isoformat(), "max_uses": payload.max_uses, "used_count": 0, "status": "active"})
        return _entity(row), code
    code = secrets.token_urlsafe(24)
    invitation = Invitation(
        family_id=member.family_id,
        created_by=member.openid,
        code_hash=hash_code(code),
        expires_at=utc_now() + timedelta(hours=payload.expires_in_hours),
        max_uses=payload.max_uses,
        used_count=0,
        status="active",
    )
    session.add(invitation)
    await session.commit()
    await session.refresh(invitation)
    return invitation, code


async def get_by_code(
    session: AsyncSession, code: str, *, lock: bool = False
) -> Invitation:
    if hasattr(session, "store"):
        rows = await session.store.list("invitations", {"code_hash": hash_code(code)})
        if not rows:
            raise AppError("INVITE_NOT_FOUND", "邀请不存在", 404)
        return _entity(rows[0])
    statement = select(Invitation).where(Invitation.code_hash == hash_code(code))
    if lock:
        statement = statement.with_for_update()
    invitation = await session.scalar(statement)
    if invitation is None:
        raise AppError("INVITE_NOT_FOUND", "邀请不存在", 404)
    return invitation


async def preview_invitation(session: AsyncSession, code: str) -> dict:
    invitation = await get_by_code(session, code)
    validate_invitation_state(invitation)
    if hasattr(session, "store"):
        family = await session.store.get("families", invitation.family_id)
        members = await session.store.list("family_members", {"family_id": invitation.family_id, "openid": invitation.created_by})
        inviter = members[0] if members else None
        if family is None or inviter is None:
            raise AppError("INVITE_NOT_FOUND", "邀请不存在", 404)
        return {"familyName": family["name"], "familyAvatarFileId": family.get("avatar_file_id"), "inviterNickname": inviter["nickname"], "expiresAt": invitation.expires_at}
    family = await session.get(Family, invitation.family_id)
    inviter = await session.scalar(
        select(FamilyMember).where(
            FamilyMember.family_id == invitation.family_id,
            FamilyMember.openid == invitation.created_by,
        )
    )
    if family is None or inviter is None:
        raise AppError("INVITE_NOT_FOUND", "邀请不存在", 404)
    return {
        "familyName": family.name,
        "familyAvatarFileId": family.avatar_file_id,
        "inviterNickname": inviter.nickname,
        "expiresAt": invitation.expires_at.isoformat(),
    }


async def join_family(
    session: AsyncSession,
    identity: CurrentIdentity,
    code: str,
    payload: InvitationJoin,
) -> FamilyMember:
    if hasattr(session, "store"):
        invitation = await get_by_code(session, code)
        existing = await find_current_member(identity, session)
        if existing is not None:
            code_value = "ALREADY_JOINED" if existing.family_id == invitation.family_id else "ALREADY_IN_FAMILY"
            raise AppError(code_value, "你已经加入该家庭" if code_value == "ALREADY_JOINED" else "你已经加入其他家庭", 409)
        validate_invitation_state(invitation)
        row = await session.store.create("family_members", {"family_id": invitation.family_id, "openid": identity.openid, "nickname": payload.nickname.strip(), "avatar_url": payload.avatar_url, "role": "member", "status": "active", "joined_at": utc_now().isoformat()})
        await session.store.update("invitations", invitation.id, {"used_count": invitation.used_count + 1})
        return _entity(row)
    invitation = await get_by_code(session, code, lock=True)
    existing = await find_current_member(identity, session)
    if existing is not None:
        error_code = (
            "ALREADY_JOINED"
            if existing.family_id == invitation.family_id
            else "ALREADY_IN_FAMILY"
        )
        message = "你已经加入该家庭" if error_code == "ALREADY_JOINED" else "你已经加入其他家庭"
        raise AppError(error_code, message, 409)
    validate_invitation_state(invitation)
    member = await session.scalar(
        select(FamilyMember)
        .where(
            FamilyMember.family_id == invitation.family_id,
            FamilyMember.openid == identity.openid,
        )
        .with_for_update()
    )
    if member is None:
        member = FamilyMember(
            family_id=invitation.family_id,
            openid=identity.openid,
            nickname=payload.nickname.strip(),
            avatar_url=payload.avatar_url,
            role="member",
            status="active",
        )
        session.add(member)
    else:
        member.nickname = payload.nickname.strip()
        member.avatar_url = payload.avatar_url
        member.role = "member"
        member.status = "active"
        member.joined_at = utc_now()
    invitation.used_count += 1
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        active = await find_current_member(identity, session)
        if active is not None:
            code = "ALREADY_JOINED" if active.family_id == invitation.family_id else "ALREADY_IN_FAMILY"
            message = "你已经加入该家庭" if code == "ALREADY_JOINED" else "你已经加入其他家庭"
            raise AppError(code, message, 409)
        raise
    await session.refresh(member)
    return member


async def revoke_invitation(
    session: AsyncSession, member: CurrentMember, invitation_id: str
) -> None:
    if hasattr(session, "store"):
        rows = await session.store.list("invitations", {"_id": invitation_id, "family_id": member.family_id})
        if not rows:
            raise AppError("INVITE_NOT_FOUND", "邀请不存在", 404)
        await session.store.update("invitations", invitation_id, {"status": "revoked"})
        return
    invitation = await session.scalar(
        select(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.family_id == member.family_id,
        )
    )
    if invitation is None:
        raise AppError("INVITE_NOT_FOUND", "邀请不存在", 404)
    invitation.status = "revoked"
    await session.commit()


async def list_members(
    session: AsyncSession, member: CurrentMember
) -> list[FamilyMember]:
    if hasattr(session, "store"):
        rows = await session.store.list("family_members", {"family_id": member.family_id, "status": "active"})
        return [_entity(row) for row in sorted(rows, key=lambda r: (0 if r.get("role") == "chef" else 1, r.get("joined_at", "")))]
    result = await session.execute(
        select(FamilyMember)
        .where(
            FamilyMember.family_id == member.family_id,
            FamilyMember.status == "active",
        )
        .order_by(
            case((FamilyMember.role == "chef", 0), else_=1),
            FamilyMember.joined_at,
        )
    )
    return list(result.scalars().all())


async def remove_member(
    session: AsyncSession, chef: CurrentMember, member_id: str
) -> None:
    if hasattr(session, "store"):
        rows = await session.store.list("family_members", {"_id": member_id, "family_id": chef.family_id, "status": "active"})
        if not rows:
            raise AppError("MEMBER_NOT_FOUND", "家庭成员不存在", 404)
        if rows[0].get("role") == "chef":
            raise AppError("CANNOT_REMOVE_CHEF", "不能移除厨师长", 409)
        await session.store.update("family_members", member_id, {"status": "left"})
        return
    target = await session.scalar(
        select(FamilyMember).where(
            FamilyMember.id == member_id,
            FamilyMember.family_id == chef.family_id,
            FamilyMember.status == "active",
        )
    )
    if target is None:
        raise AppError("MEMBER_NOT_FOUND", "家庭成员不存在", 404)
    if target.role == "chef":
        raise AppError("CANNOT_REMOVE_CHEF", "不能移除厨师长", 409)
    target.status = "left"
    await session.commit()
