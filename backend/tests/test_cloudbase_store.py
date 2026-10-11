import json

import pytest

from app.storage.cloudbase_store import CloudBaseDocumentStore


class FakeClient:
    def __init__(self):
        self.calls = []

    async def request(self, action, payload):
        self.calls.append((action, payload))
        if action == "database.insertDocument":
            data = payload["data"]
            if isinstance(data, str):
                data = json.loads(data)
            return {"Response": {"Document": {"_id": "d1", **data}}}
        if action == "database.getDocument":
            return {"Response": {"Document": {"_id": payload["documentId"], "family_id": "f1"}}}
        if action == "database.queryDocument":
            return {"Response": {"Documents": [{"_id": "d1", "family_id": "f1"}]}}
        if action == "database.modifyDocument":
            data = payload["data"]
            if isinstance(data, str):
                data = json.loads(data)
            return {"Response": {"Document": {"_id": payload["documentId"], **data}}}
        return {"Response": {}}


@pytest.mark.asyncio
async def test_cloudbase_store_maps_collections_and_filters():
    client = FakeClient()
    store = CloudBaseDocumentStore(client)
    created = await store.create("dishes", {"family_id": "f1", "name": "鱼香肉丝"})
    assert created["_id"] == json.loads(client.calls[0][1]["data"])["_id"]
    await store.get("dishes", "d1")
    await store.list("dishes", {"family_id": "f1"})
    await store.update("dishes", "d1", {"name": "宫保鸡丁"}, expected_version=1)
    assert client.calls[0][1]["collectionName"] == "dishes"
    assert json.loads(client.calls[2][1]["query"]) == {"family_id": "f1"}
    assert json.loads(client.calls[4][1]["data"])["version"] == 2


@pytest.mark.asyncio
async def test_cloudbase_create_keeps_persisted_id_when_api_returns_only_request_id():
    class RequestIdOnlyClient:
        async def request(self, action, payload):
            self.inserted = payload["data"]
            return {"Response": {"RequestId": "r1"}}

    client = RequestIdOnlyClient()
    created = await CloudBaseDocumentStore(client).create("families", {"name": "测试家庭"})
    assert created["_id"] == json.loads(client.inserted)["_id"]


@pytest.mark.asyncio
async def test_cloudbase_list_decodes_stringified_response_data_and_filters_rows():
    class DataClient:
        async def request(self, _action, _payload):
            return {
                "Response": {
                    "Data": '{"list":["{\\"_id\\":\\"m1\\",\\"openid\\":\\"user-1\\",\\"status\\":\\"active\\"}","{\\"_id\\":\\"m2\\",\\"openid\\":\\"user-2\\",\\"status\\":\\"active\\"}"]}'
                }
            }

    rows = await CloudBaseDocumentStore(DataClient()).list(
        "family_members", {"openid": "user-1", "status": "active"}
    )
    assert rows == [{"_id": "m1", "openid": "user-1", "status": "active"}]


@pytest.mark.asyncio
async def test_cloudbase_list_preserves_string_fields_inside_documents():
    class DataClient:
        async def request(self, _action, _payload):
            return {"Response": {"Data": '{"list":["{\\"_id\\":\\"d1\\",\\"quantity\\":\\"2\\"}"]}'}}

    rows = await CloudBaseDocumentStore(DataClient()).list("dishes")

    assert rows == [{"_id": "d1", "quantity": "2"}]


@pytest.mark.asyncio
async def test_cloudbase_store_serializes_document_api_payloads_as_json_strings():
    client = FakeClient()
    store = CloudBaseDocumentStore(client)

    await store.create("families", {"name": "测试家庭", "quantity": "2"})
    await store.list("family_members", {"openid": "user-1", "status": "active"})
    await store.update("families", "d1", {"name": "新名称"})

    insert_payload = client.calls[0][1]
    query_payload = client.calls[1][1]
    update_payload = client.calls[3][1]
    assert isinstance(insert_payload["data"], str)
    assert json.loads(insert_payload["data"])["name"] == "测试家庭"
    assert json.loads(insert_payload["data"])["quantity"] == "2"
    assert isinstance(query_payload["query"], str)
    assert json.loads(query_payload["query"]) == {"openid": "user-1", "status": "active"}
    assert isinstance(update_payload["data"], str)
    assert json.loads(update_payload["data"])["name"] == "新名称"


@pytest.mark.asyncio
async def test_cloudbase_store_reads_a_document_returned_directly_in_response_data():
    class DirectDocumentClient:
        async def request(self, _action, _payload):
            return {"Response": {"Data": '{"_id":"f1","name":"测试家庭"}'}}

    document = await CloudBaseDocumentStore(DirectDocumentClient()).get("families", "f1")

    assert document == {"_id": "f1", "name": "测试家庭"}
