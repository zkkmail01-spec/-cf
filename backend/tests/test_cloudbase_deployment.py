from pathlib import Path


def test_cloudbase_deployment_docs_describe_secret_safe_configuration():
    root = Path(__file__).parents[2]
    env = (root / "backend" / ".env.example").read_text(encoding="utf-8")
    docs = (root / "docs" / "deployment" / "cloudbase.md").read_text(encoding="utf-8")
    assert "STORAGE_BACKEND=cloudbase" in env
    assert "TENCENTCLOUD_SECRETKEY" in env
    assert "idempotency_records" in docs
    assert "不能提交" in docs
