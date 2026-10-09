from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentMember, require_chef, require_member
from app.core.identity import CurrentIdentity, require_identity
from app.db.session import get_session
from app.models.family import Family, FamilyMember
from app.schemas.family import (
    FamilyContextRead,
    FamilyCreate,
    FamilyRead,
    FamilyUpdate,
    MemberRead,
    MemberUpdate,
)
from app.services import families as family_service


router = APIRouter(tags=["families"])


def member_read(member: FamilyMember | CurrentMember) -> MemberRead:
    return MemberRead(
        id=member.id if isinstance(member, FamilyMember) else member.member_id,
        openid=member.openid,
        nickname=member.nickname,
        avatar_url=member.avatar_url,
        role=member.role,
    )


def family_context(family: Family, member: FamilyMember | CurrentMember) -> FamilyContextRead:
    return FamilyContextRead(
        id=family.id,
        name=family.name,
        avatar_file_id=family.avatar_file_id,
        current_member=member_read(member),
    )


@router.post("/families", response_model=FamilyContextRead, status_code=status.HTTP_201_CREATED)
async def create_family(
    payload: FamilyCreate,
    identity: Annotated[CurrentIdentity, Depends(require_identity)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FamilyContextRead:
    family, member = await family_service.create_family(session, identity, payload)
    return family_context(family, member)


@router.get("/families/current", response_model=FamilyContextRead)
async def get_current_family(
    member: Annotated[CurrentMember, Depends(require_member)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FamilyContextRead:
    family = await family_service.get_family(session, member)
    return family_context(family, member)


@router.patch("/families/current", response_model=FamilyContextRead)
async def patch_current_family(
    payload: FamilyUpdate,
    member: Annotated[CurrentMember, Depends(require_chef)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FamilyContextRead:
    family = await family_service.update_family(session, member, payload)
    return family_context(family, member)


@router.patch("/members/me", response_model=MemberRead)
async def patch_current_member(
    payload: MemberUpdate,
    member: Annotated[CurrentMember, Depends(require_member)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MemberRead:
    updated = await family_service.update_member_profile(session, member, payload)
    return member_read(updated)


@router.post("/families/current/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_current_family(
    member: Annotated[CurrentMember, Depends(require_member)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    await family_service.leave_family(session, member)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
