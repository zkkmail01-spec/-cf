from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.main import create_app


def test_health_endpoint_reports_ok():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_errors_use_stable_envelope():
    app = create_app()

    @app.get("/boom")
    async def boom():
        raise AppError(code="BOOM", message="出错了", status_code=409)

    response = TestClient(app).get("/boom")

    assert response.status_code == 409
    assert response.json() == {"error": {"code": "BOOM", "message": "出错了"}}
