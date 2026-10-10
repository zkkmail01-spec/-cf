import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentMember, find_current_member
from app.core.errors import AppError
from app.core.identity import CurrentIdentity
from app.db.base import utc_now
from app.models.family import Family, FamilyMember
from app.models.invitation import Invitation
from app.schemas.invitation import InvitationCreate, InvitationJoin


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def aware(value: datetime) -> datetime:
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
