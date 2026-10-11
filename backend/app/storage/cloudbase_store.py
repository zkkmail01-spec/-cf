from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from app.storage.memory import VersionConflictError


class CloudBaseDocumentStore:
    def __init__(self, client: Any) -> None:
        self.client = client

    async def create(self, collection: str, document: Mapping[str, Any]) -> dict[str, Any]:
        result = await self.client.request("database.insertDocument", {"collectionName": collection, "data": deepcopy(dict(document))})
        return result.get("Response", {}).get("Document") or result.get("Response", {}).get("document") or {}

    async def get(self, collection: str, document_id: str) -> dict[str, Any] | None:
        result = await self.client.request("database.getDocument", {"collectionName": collection, "documentId": document_id})
        return result.get("Response", {}).get("Document")

    async def list(self, collection: str, filters: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
        result = await self.client.request("database.queryDocument", {"collectionName": collection, "query": dict(filters or {})})
        return result.get("Response", {}).get("Documents", [])

    async def update(self, collection: str, document_id: str, patch: Mapping[str, Any], expected_version: int | None = None) -> dict[str, Any]:
        current = await self.get(collection, document_id)
        if current is None:
            raise KeyError(document_id)
        current_version = current.get("version", 1)
        if expected_version is not None and current_version != expected_version:
            raise VersionConflictError(document_id)
        data = deepcopy(dict(patch))
        data["version"] = current_version + 1
        result = await self.client.request("database.modifyDocument", {"collectionName": collection, "documentId": document_id, "data": data})
        return result.get("Response", {}).get("Document") or {**current, **data, "_id": document_id}

    async def delete(self, collection: str, document_id: str) -> None:
        await self.client.request("database.removeDocument", {"collectionName": collection, "documentId": document_id})

    async def put_idempotency(self, family_id: str, key: str, value: Mapping[str, Any]) -> dict[str, Any]:
        result = await self.client.request("database.insertDocument", {"collectionName": "idempotency_records", "data": {"family_id": family_id, "key": key, **dict(value)}})
        return result.get("Response", {}).get("Document") or {}
