from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_header_identity_mode_is_not_exposed_by_local_compose() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    runbook = (ROOT / "docs/deployment/cloudbase.md").read_text(encoding="utf-8")

    assert '"127.0.0.1:8000:8000"' in compose
    assert '"8000:80"' not in compose
    assert "生产服务必须禁止公网直连容器端口" in runbook
    assert "不能直接信任请求头" in runbook


def test_container_uses_unprivileged_port_for_non_root_user() -> None:
    dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert '"--port", "8000"' in dockerfile
