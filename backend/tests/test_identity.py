import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers

from app.core.config import Settings
from app.core.identity import CurrentIdentity, identity_from_headers


def test_trusted_cloud_header_resolves_identity():
    identity = identity_from_headers(
        Headers({"x-wx-openid": "wx-user", "x-wx-appid": "wx-app"}),
        Settings(_env_file=None),
    )

    assert identity == CurrentIdentity(openid="wx-user", appid="wx-app")


def test_missing_identity_is_unauthorized():
    with pytest.raises(HTTPException) as error:
        identity_from_headers(Headers(), Settings(_env_file=None))

    assert error.value.status_code == 401


def test_mock_identity_requires_local_mode_and_explicit_flag():
    allowed = Settings(allow_mock_identity=True, _env_file=None)

    identity = identity_from_headers(Headers({"x-mock-openid": "local-user"}), allowed)

    assert identity.openid == "local-user"

    blocked = Settings(allow_mock_identity=False, _env_file=None)
    with pytest.raises(HTTPException) as error:
        identity_from_headers(Headers({"x-mock-openid": "local-user"}), blocked)
    assert error.value.status_code == 401
