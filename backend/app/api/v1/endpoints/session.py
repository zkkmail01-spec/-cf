from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import find_current_member
from app.core.identity import CurrentIdentity, require_identity
from app.db.session import get_session
from app.models.family import Family
from app.schemas.family import FamilyRead, IdentityRead, MemberRead, SessionRead


router = APIRouter(tags=["session"])


@router.get("/session", response_model=SessionRead)
async def get_current_session(
    identity: Annotated[CurrentIdentity, Depends(require_identity)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SessionRead:
    member = await find_current_member(identity, session)
    family = await session.get(Family, member.family_id) if member else None
    return SessionRead(
        identity=IdentityRead(openid=identity.openid, appid=identity.appid),
        family=FamilyRead.model_validate(family) if family else None,
        member=(
            MemberRead(
                id=member.member_id,
                openid=member.openid,
                nickname=member.nickname,
                avatar_url=member.avatar_url,
                role=member.role,
            )
            if member
            else None
        ),
    )
