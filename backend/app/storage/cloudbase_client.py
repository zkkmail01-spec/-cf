from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import date, datetime
from typing import Any

import httpx


class CloudBaseAPIError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"CloudBase API error {code}: {message}")
        self.code = code
        self.message = message


def _ejson_encode(value: Any) -> Any:
    if isinstance(value, datetime):
        return {"$date": int(value.timestamp() * 1000)}
    if isinstance(value, date):
        return {"$date": int(datetime.combine(value, datetime.min.time()).timestamp() * 1000)}
    if isinstance(value, dict):
        return {key: _ejson_encode(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_ejson_encode(item) for item in value]
    return value


def _ejson_decode(value: Any) -> Any:
    if isinstance(value, dict) and set(value) == {"$date"}:
        return datetime.fromtimestamp(value["$date"] / 1000)
    if isinstance(value, dict):
        return {key: _ejson_decode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_ejson_decode(item) for item in value]
    return value


class CloudBaseAdminClient:
    """Small async CloudBase Admin API client using Tencent TC3 signing."""

    def __init__(
        self,
        *,
        env_id: str,
        region: str,
        secret_id: str,
        secret_key: str,
        http_client: httpx.AsyncClient | None = None,
        timestamp: int | None = None,
    ) -> None:
        self.env_id = env_id
        self.region = region
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.http_client = http_client or httpx.AsyncClient(timeout=15.0)
        self.timestamp = timestamp

    async def request(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        body_payload = {"action": action, "envName": self.env_id, **_ejson_encode(payload)}
        body = json.dumps(body_payload, ensure_ascii=False, separators=(",", ":"))
        timestamp = self.timestamp or int(time.time())
        service = "tcb"
        host = "tcb-api.tencentcloudapi.com"
        algorithm = "TC3-HMAC-SHA256"
        date_stamp = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
        content_type = "application/json; charset=utf-8"
        canonical_headers = f"content-type:{content_type}\nhost:{host}\n"
        signed_headers = "content-type;host"
        payload_hash = hashlib.sha256(body.encode()).hexdigest()
        canonical_request = f"POST\n/admin\nenv={self.env_id}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        credential_scope = f"{date_stamp}/{service}/tc3_request"
        string_to_sign = "\n".join([
            algorithm,
            str(timestamp),
            credential_scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        ])
        secret_date = hmac.new(("TC3" + self.secret_key).encode(), date_stamp.encode(), hashlib.sha256).digest()
        secret_service = hmac.new(secret_date, service.encode(), hashlib.sha256).digest()
        secret_signing = hmac.new(secret_service, b"tc3_request", hashlib.sha256).digest()
        signature = hmac.new(secret_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()
        authorization = (
            f"{algorithm} Credential={self.secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        response = await self.http_client.post(
            f"https://{host}/admin",
            params={"env": self.env_id},
            content=body.encode(),
            headers={
                "Content-Type": content_type,
                "Host": host,
                "X-TC-Action": action,
                "X-TC-Version": "2018-06-08",
                "X-TC-Region": self.region,
                "X-TC-Timestamp": str(timestamp),
                "Authorization": authorization,
            },
        )
        response.raise_for_status()
        result = response.json()
        api_error = result.get("Response", {}).get("Error")
        if api_error:
            raise CloudBaseAPIError(
                str(api_error.get("Code", "UNKNOWN")),
                str(api_error.get("Message", "CloudBase request failed")),
            )
        if "Response" in result:
            result["Response"] = _ejson_decode(result["Response"])
        return result
