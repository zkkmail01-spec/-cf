from __future__ import annotations

from app.core.config import Settings
from app.storage.cloudbase_client import CloudBaseAdminClient
from app.storage.cloudbase_store import CloudBaseDocumentStore
from app.storage.memory import MemoryDocumentStore


def create_document_store(settings: Settings):
    if settings.storage_backend == "cloudbase":
        client = CloudBaseAdminClient(
            env_id=settings.cloudbase_env_id or "",
            region=settings.cloudbase_region,
            secret_id=settings.tencentcloud_secretid or "",
            secret_key=settings.tencentcloud_secretkey or "",
        )
        return CloudBaseDocumentStore(client)
    return MemoryDocumentStore()
