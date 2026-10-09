from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.identity import CurrentIdentity, require_identity
from app.db.session import get_session
from app.models.family import FamilyMember


@dataclass(frozen=True, slots=True)
class CurrentMember:
    member_id: str
    family_id: str
    openid: str
    nickname: str
    avatar_url: str | None
    role: str


async def find_current_member(
    identity: CurrentIdentity,
    session: AsyncSession,
) -> CurrentMember | None:
    result = await session.execute(
        select(FamilyMember).where(
            FamilyMember.openid == identity.openid,
            FamilyMember.status == "active",
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        return None
    return CurrentMember(
        member_id=member.id,
        family_id=member.family_id,
        openid=member.openid,
        nickname=member.nickname,
        avatar_url=member.avatar_url,
        role=member.role,
    )


async def require_member(
    identity: Annotated[CurrentIdentity, Depends(require_identity)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentMember:
    member = await find_current_member(identity, session)
    if member is None:
        raise AppError("NOT_FAMILY_MEMBER", "你还没有加入家庭", 403)
    return member


async def require_chef(
    member: Annotated[CurrentMember, Depends(require_member)],
) -> CurrentMember:
    if member.role != "chef":
        raise AppError("CHEF_REQUIRED", "只有厨师长可以执行此操作", 403)
    return member
