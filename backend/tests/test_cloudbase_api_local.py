from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.main import create_app
from app.storage.memory import MemoryDocumentStore


class LocalDocumentSession:
    def __init__(self):
        self.store = MemoryDocumentStore()

    async def commit(self):
        pass

    async def rollback(self):
        pass


def test_document_backend_core_flow():
    app = create_app()
    session = LocalDocumentSession()

    async def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    headers = {"x-wx-openid": "cloud-user", "x-wx-appid": "wx-test"}
    with TestClient(app) as client:
        created = client.post("/api/v1/families", headers=headers, json={"name": "云端家庭", "nickname": "厨师长"})
        assert created.status_code == 201
        assert client.get("/api/v1/session", headers=headers).json()["family"]["name"] == "云端家庭"
        category = client.post("/api/v1/categories", headers=headers, json={"name": "热菜"})
        assert category.status_code == 201
        dish = client.post("/api/v1/dishes", headers=headers, json={"categoryId": category.json()["id"], "name": "番茄炒蛋", "ingredients": [{"name": "番茄", "quantity": "2", "unit": "个"}]})
        assert dish.status_code == 201
        selected = client.put("/api/v1/meals/2026-10-11/lunch/selections/" + dish.json()["id"], headers={**headers, "Idempotency-Key": "k1"})
        assert selected.status_code == 200
        assert selected.json()["meals"]["lunch"]["items"][0]["dishName"] == "番茄炒蛋"
