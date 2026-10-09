from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentMember, require_chef, require_member
from app.core.identity import CurrentIdentity, require_identity
from app.db.session import get_session
from app.models.family import FamilyMember
from app.schemas.family import MemberRead
from app.schemas.invitation import (
    InvitationCreate,
    InvitationCreated,
    InvitationJoin,
    InvitationPreview,
)
from app.services import invitations as invitation_service


router = APIRouter(tags=["invitations"])


def member_read(member: FamilyMember) -> MemberRead:
    return MemberRead(
        id=member.id,
        openid=member.openid,
        nickname=member.nickname,
        avatar_url=member.avatar_url,
        role=member.role,
    )


@router.post(
    "/invitations",
    response_model=InvitationCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    payload: InvitationCreate,
    member: Annotated[CurrentMember, Depends(require_chef)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    invitation, code = await invitation_service.create_invitation(session, member, payload)
    return InvitationCreated(
        id=invitation.id,
        code=code,
        expires_at=invitation.expires_at,
        max_uses=invitation.max_uses,
        used_count=invitation.used_count,
        status=invitation.status,
    )


@router.get("/invitations/{code}/preview", response_model=InvitationPreview)
async def preview_invitation(
    code: str,
    _identity: Annotated[CurrentIdentity, Depends(require_identity)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await invitation_service.preview_invitation(session, code)


@router.post("/invitations/{code}/join", response_model=MemberRead)
async def join_family(
    code: str,
    payload: InvitationJoin,
    identity: Annotated[CurrentIdentity, Depends(require_identity)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return member_read(await invitation_service.join_family(session, identity, code, payload))


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    invitation_id: str,
    member: Annotated[CurrentMember, Depends(require_chef)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    await invitation_service.revoke_invitation(session, member, invitation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/members", response_model=list[MemberRead])
async def list_members(
    member: Annotated[CurrentMember, Depends(require_member)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[MemberRead]:
    return [
        member_read(row)
        for row in await invitation_service.list_members(session, member)
    ]


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: str,
    chef: Annotated[CurrentMember, Depends(require_chef)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    await invitation_service.remove_member(session, chef, member_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
