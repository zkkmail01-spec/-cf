import json

import httpx
import pytest

from app.core.config import Settings
from app.storage.cloudbase_client import CloudBaseAdminClient


def test_cloudbase_settings_require_credentials():
    with pytest.raises(ValueError, match="CLOUDBASE_ENV_ID"):
        Settings(app_env="production", storage_backend="cloudbase", database_url="sqlite:///x")

    with pytest.raises(ValueError, match="TENCENTCLOUD_SECRETID"):
        Settings(
            app_env="production",
            storage_backend="cloudbase",
            database_url="sqlite:///x",
            cloudbase_env_id="env-1",
        )


def test_cloudbase_production_does_not_require_sql_database_url():
    settings = Settings(
        app_env="production",
        storage_backend="cloudbase",
        cloudbase_env_id="env-1",
        tencentcloud_secretid="sid",
        tencentcloud_secretkey="skey",
    )
    assert settings.database_url is None


@pytest.mark.asyncio
async def test_request_builds_signed_cloudbase_admin_request():
    seen = {}

    async def handler(request: httpx.Request):
        seen["request"] = request
        return httpx.Response(200, json={"Response": {"RequestId": "r1", "Document": {"_id": "a"}}})

    client = CloudBaseAdminClient(
        env_id="env-1",
        region="ap-shanghai",
        secret_id="sid",
        secret_key="skey",
        timestamp=1735689600,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    result = await client.request(
        "database.insertDocument",
        {"collectionName": "families", "data": {"name": "测试"}},
    )
    request = seen["request"]
    body = json.loads(request.content)
    assert request.url.path == "/admin"
    assert request.url.params["env"] == "env-1"
    assert body["action"] == "database.insertDocument"
    assert body["envName"] == "env-1"
    assert body["collectionName"] == "families"
    assert request.headers["X-TC-Action"] == "database.insertDocument"
    assert request.headers["X-TC-Region"] == "ap-shanghai"
    assert request.headers["Authorization"].startswith("TC3-HMAC-SHA256 Credential=sid/")
    assert result["Response"]["RequestId"] == "r1"
