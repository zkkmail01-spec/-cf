import pytest

from app.storage.memory import MemoryDocumentStore, VersionConflictError


@pytest.mark.asyncio
async def test_memory_store_scopes_and_updates_documents_with_versions():
    store = MemoryDocumentStore()
    created = await store.create("dishes", {"family_id": "f1", "name": "番茄炒蛋", "version": 1})
    assert created["_id"]
    assert len(await store.list("dishes", {"family_id": "f1"})) == 1
    assert await store.list("dishes", {"family_id": "f2"}) == []
    updated = await store.update("dishes", created["_id"], {"name": "青椒炒蛋"}, expected_version=1)
    assert updated["name"] == "青椒炒蛋"
    assert updated["version"] == 2
    with pytest.raises(VersionConflictError):
        await store.update("dishes", created["_id"], {"name": "冲突"}, expected_version=1)


@pytest.mark.asyncio
async def test_memory_store_idempotency_returns_same_record():
    store = MemoryDocumentStore()
    first = await store.put_idempotency("f1", "key-1", {"order_id": "o1"})
    second = await store.put_idempotency("f1", "key-1", {"order_id": "o2"})
    assert first == second
