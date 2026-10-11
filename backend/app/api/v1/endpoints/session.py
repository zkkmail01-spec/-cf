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
    if member and hasattr(session, "store"):
        family = await session.store.get("families", member.family_id)
    else:
        family = await session.get(Family, member.family_id) if member else None
    family_read = None
    if family:
        family_read = FamilyRead(
            id=family.get("_id") if isinstance(family, dict) else family.id,
            name=family["name"] if isinstance(family, dict) else family.name,
            avatar_file_id=family.get("avatar_file_id") if isinstance(family, dict) else family.avatar_file_id,
        )
    return SessionRead(
        identity=IdentityRead(openid=identity.openid, appid=identity.appid),
        family=family_read,
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
