from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any
from uuid import uuid4


class VersionConflictError(RuntimeError):
    pass


class MemoryDocumentStore:
    def __init__(self) -> None:
        self._collections: dict[str, dict[str, dict[str, Any]]] = {}
        self._idempotency: dict[tuple[str, str], dict[str, Any]] = {}

    async def create(self, collection: str, document: Mapping[str, Any]) -> dict[str, Any]:
        record = deepcopy(dict(document))
        record.setdefault("_id", str(uuid4()))
        record.setdefault("version", 1)
        self._collections.setdefault(collection, {})[record["_id"]] = record
        return deepcopy(record)

    async def get(self, collection: str, document_id: str) -> dict[str, Any] | None:
        value = self._collections.get(collection, {}).get(document_id)
        return deepcopy(value) if value is not None else None

    async def list(self, collection: str, filters: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
        filters = filters or {}
        values = self._collections.get(collection, {}).values()
        return [deepcopy(value) for value in values if all(value.get(k) == v for k, v in filters.items())]

    async def update(self, collection: str, document_id: str, patch: Mapping[str, Any], expected_version: int | None = None) -> dict[str, Any]:
        record = self._collections.get(collection, {}).get(document_id)
        if record is None:
            raise KeyError(document_id)
        if expected_version is not None and record.get("version", 1) != expected_version:
            raise VersionConflictError(document_id)
        record.update(deepcopy(dict(patch)))
        record["version"] = record.get("version", 1) + 1
        return deepcopy(record)

    async def delete(self, collection: str, document_id: str) -> None:
        self._collections.get(collection, {}).pop(document_id, None)

    async def put_idempotency(self, family_id: str, key: str, value: Mapping[str, Any]) -> dict[str, Any]:
        token = (family_id, key)
        self._idempotency.setdefault(token, deepcopy(dict(value)))
        return deepcopy(self._idempotency[token])
