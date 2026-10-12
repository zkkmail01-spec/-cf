from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from app.storage.memory import VersionConflictError


def _decode_json_value(value: Any, *, parse_strings: bool = True) -> Any:
    if isinstance(value, str):
        if not parse_strings:
            return value
        try:
            return _decode_json_value(json.loads(value), parse_strings=True)
        except (TypeError, ValueError):
            return value
    if isinstance(value, list):
        return [_decode_json_value(item, parse_strings=True) for item in value]
    if isinstance(value, dict):
        envelope_keys = {"Data", "data", "Document", "document", "Documents", "documents", "List", "list"}
        return {key: _decode_json_value(item, parse_strings=key in envelope_keys) for key, item in value.items()}
    return value


def _response_data(result: Mapping[str, Any]) -> dict[str, Any]:
    response = _decode_json_value(dict(result.get("Response", {})))
    nested = response.get("Data") or response.get("data")
    nested = _decode_json_value(nested)
    base = {key: value for key, value in response.items() if key not in {"Data", "data"}}
    if isinstance(nested, dict):
        return {**base, **nested}
    if isinstance(nested, list):
        return {**base, "Documents": nested}
    return response


def _document_from(result: Mapping[str, Any]) -> dict[str, Any] | None:
    response = _response_data(result)
    document = response.get("Document") or response.get("document")
    if isinstance(document, dict):
        return document
    documents = response.get("list") or response.get("List") or response.get("Documents") or response.get("documents")
    if isinstance(documents, list):
        first = next((item for item in documents if isinstance(item, dict)), None)
        if first is not None:
            return first
    return response if isinstance(response.get("_id"), str) else None


def _documents_from(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    response = _response_data(result)
    documents = (
        response.get("Documents")
        or response.get("documents")
        or response.get("List")
        or response.get("list")
        or []
    )
    return [item for item in _decode_json_value(documents) if isinstance(item, dict)] if isinstance(documents, list) else []


def _json_payload(value: Mapping[str, Any]) -> str:
    """CloudBase database admin actions expect EJSON as a JSON string."""
    def default(item: Any) -> Any:
        if isinstance(item, datetime):
            return {"$date": int(item.timestamp() * 1000)}
        if isinstance(item, date):
            return {"$date": int(datetime.combine(item, datetime.min.time()).timestamp() * 1000)}
        raise TypeError(f"Object of type {type(item).__name__} is not JSON serializable")

    return json.dumps(dict(value), ensure_ascii=False, separators=(",", ":"), default=default)


class CloudBaseDocumentStore:
    def __init__(self, client: Any) -> None:
        self.client = client

    async def create(self, collection: str, document: Mapping[str, Any]) -> dict[str, Any]:
        # CloudBase 的插入接口可能只返回 RequestId。预先写入 _id，确保
        # 返回给业务层的 ID 与实际保存的文档 ID 是同一个。
        data = deepcopy(dict(document))
        data.setdefault("_id", uuid4().hex)
        # CloudBase database.insertDocument expects an array of EJSON strings.
        result = await self.client.request(
            "database.insertDocument",
            {"collectionName": collection, "data": [_json_payload(data)]},
        )
        response = _response_data(result)
        created = _document_from(result) or {}

        if not created:
            created = dict(data)
        document_id = (
            created.get("_id")
            or response.get("DocumentId")
            or response.get("documentId")
            or response.get("InsertedId")
            or response.get("insertedId")
            or (response.get("insertedIds") or [None])[0]
            or (response.get("InsertedIds") or [None])[0]
            or response.get("_id")
        )
        if not document_id:
            document_id = data["_id"]
        created.setdefault("_id", document_id)
        return created

    async def get(self, collection: str, document_id: str) -> dict[str, Any] | None:
        result = await self.client.request(
            "database.getDocument",
            {
                "collectionName": collection,
                "query": _json_payload({"_id": document_id}),
                "queryType": "DOC",
                "limit": 1,
            },
        )
        return _document_from(result)

    async def list(self, collection: str, filters: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
        result = await self.client.request(
            "database.getDocument",
            {
                "collectionName": collection,
                "query": _json_payload(filters or {}),
                "queryType": "WHERE",
                "limit": 100,
            },
        )
        documents = _documents_from(result)
        if filters:
            documents = [row for row in documents if all(row.get(key) == value for key, value in filters.items())]
        return documents

    async def update(self, collection: str, document_id: str, patch: Mapping[str, Any], expected_version: int | None = None) -> dict[str, Any]:
        current = await self.get(collection, document_id)
        if current is None:
            raise KeyError(document_id)
        current_version = current.get("version", 1)
        if expected_version is not None and current_version != expected_version:
            raise VersionConflictError(document_id)
        data = deepcopy(dict(patch))
        data["version"] = current_version + 1
        result = await self.client.request(
            "database.modifyDocument",
            {
                "collectionName": collection,
                "query": _json_payload({"_id": document_id}),
                "queryType": "DOC",
                "data": _json_payload(data),
                "multi": False,
                "merge": True,
                "upsert": False,
            },
        )
        return _document_from(result) or {**current, **data, "_id": document_id}

    async def delete(self, collection: str, document_id: str) -> None:
        await self.client.request(
            "database.removeDocument",
            {
                "collectionName": collection,
                "query": _json_payload({"_id": document_id}),
                "queryType": "DOC",
                "multi": False,
            },
        )

    async def put_idempotency(self, family_id: str, key: str, value: Mapping[str, Any]) -> dict[str, Any]:
        result = await self.client.request(
            "database.insertDocument",
            {
                "collectionName": "idempotency_records",
                "data": [_json_payload({"family_id": family_id, "key": key, **dict(value)})],
            },
        )
        return _document_from(result) or {}
