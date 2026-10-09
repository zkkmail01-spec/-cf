from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from starlette.datastructures import Headers

from app.core.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class CurrentIdentity:
    openid: str
    appid: str | None = None


def identity_from_headers(headers: Headers, settings: Settings) -> CurrentIdentity:
    trusted_openid = headers.get("x-wx-openid")
    if trusted_openid:
        return CurrentIdentity(
            openid=trusted_openid,
            appid=headers.get("x-wx-appid"),
        )

    mock_openid = headers.get("x-mock-openid")
    if settings.app_env == "local" and settings.allow_mock_identity and mock_openid:
        return CurrentIdentity(openid=mock_openid, appid="local-mock")

    raise HTTPException(status_code=401, detail="WeChat identity is required")


async def require_identity(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> CurrentIdentity:
    return identity_from_headers(request.headers, settings)
