from app.core.config import Settings
from app.storage.cloudbase_store import CloudBaseDocumentStore
from app.storage.factory import create_document_store
from app.storage.memory import MemoryDocumentStore


def test_storage_backend_selects_cloudbase_or_memory_without_fallback():
    cloudbase = Settings(
        app_env="local", storage_backend="cloudbase", cloudbase_env_id="env-1",
        tencentcloud_secretid="sid", tencentcloud_secretkey="skey",
    )
    assert isinstance(create_document_store(cloudbase), CloudBaseDocumentStore)
    sql = Settings(app_env="local", storage_backend="sql")
    assert isinstance(create_document_store(sql), MemoryDocumentStore)
