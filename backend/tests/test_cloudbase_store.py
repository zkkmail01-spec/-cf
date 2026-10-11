import pytest

from app.storage.cloudbase_store import CloudBaseDocumentStore


class FakeClient:
    def __init__(self):
        self.calls = []

    async def request(self, action, payload):
        self.calls.append((action, payload))
        if action == "database.insertDocument":
            return {"Response": {"Document": {"_id": "d1", **payload["data"]}}}
        if action == "database.getDocument":
            return {"Response": {"Document": {"_id": payload["documentId"], "family_id": "f1"}}}
        if action == "database.queryDocument":
            return {"Response": {"Documents": [{"_id": "d1", "family_id": "f1"}]}}
        if action == "database.modifyDocument":
            return {"Response": {"Document": {"_id": payload["documentId"], **payload["data"]}}}
        return {"Response": {}}


@pytest.mark.asyncio
async def test_cloudbase_store_maps_collections_and_filters():
    client = FakeClient()
    store = CloudBaseDocumentStore(client)
    created = await store.create("dishes", {"family_id": "f1", "name": "鱼香肉丝"})
    assert created["_id"] == "d1"
    await store.get("dishes", "d1")
    await store.list("dishes", {"family_id": "f1"})
    await store.update("dishes", "d1", {"name": "宫保鸡丁"}, expected_version=1)
    assert client.calls[0][1]["collectionName"] == "dishes"
    assert client.calls[2][1]["query"] == {"family_id": "f1"}
    assert client.calls[4][1]["data"]["version"] == 2
