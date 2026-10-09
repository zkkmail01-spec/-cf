from datetime import datetime

from pydantic import Field

from app.schemas.common import APIModel


class InvitationCreate(APIModel):
    expires_in_hours: int = Field(default=72, ge=1, le=168)
    max_uses: int = Field(default=10, ge=1, le=50)


class InvitationCreated(APIModel):
    id: str
    code: str
    expires_at: datetime
    max_uses: int
    used_count: int
    status: str


class InvitationPreview(APIModel):
    family_name: str
    family_avatar_file_id: str | None
    inviter_nickname: str
    expires_at: datetime


class InvitationJoin(APIModel):
    nickname: str = Field(min_length=1, max_length=80)
    avatar_url: str | None = Field(default=None, max_length=1024)
