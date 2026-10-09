from pydantic import Field

from app.schemas.common import APIModel


class FamilyCreate(APIModel):
    name: str = Field(min_length=1, max_length=80)
    nickname: str = Field(min_length=1, max_length=80)
    avatar_url: str | None = Field(default=None, max_length=1024)


class FamilyUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    avatar_file_id: str | None = Field(default=None, max_length=512)


class MemberUpdate(APIModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=80)
    avatar_url: str | None = Field(default=None, max_length=1024)


class IdentityRead(APIModel):
    openid: str
    appid: str | None = None


class MemberRead(APIModel):
    id: str
    openid: str
    nickname: str
    avatar_url: str | None
    role: str


class FamilyRead(APIModel):
    id: str
    name: str
    avatar_file_id: str | None


class FamilyContextRead(FamilyRead):
    current_member: MemberRead


class SessionRead(APIModel):
    identity: IdentityRead
    family: FamilyRead | None
    member: MemberRead | None
