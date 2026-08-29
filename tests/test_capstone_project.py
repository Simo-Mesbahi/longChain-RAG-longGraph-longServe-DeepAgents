import importlib.util
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

PROJECT_DIR = Path("projects/07-asteria-investigation-platform")
FRONTEND_DIR = PROJECT_DIR / "frontend"


class IdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del tag
        for name, value in attrs:
            if name == "id" and value:
                self.ids.append(value)


def load_api_module():
    pytest.importorskip("fastapi")
    api_path = PROJECT_DIR / "api.py"
    spec = importlib.util.spec_from_file_location("asteria_capstone_api", api_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frontend_has_unique_ids_and_local_assets() -> None:
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    collector = IdCollector()
    collector.feed(html)

    assert len(collector.ids) == len(set(collector.ids))
    assert 'href="/assets/styles.css"' in html
    assert 'src="/assets/app.js"' in html
    assert "view-cockpit" in html
    assert "view-scenarios" in html
    assert "view-architecture" in html


def test_frontend_renders_untrusted_content_as_text() -> None:
    javascript = (FRONTEND_DIR / "assets/app.js").read_text(encoding="utf-8")

    assert ".textContent" in javascript
    assert ".innerHTML" not in javascript
    assert "/api/v1/investigations" in javascript
    assert "/api/v1/evaluations" in javascript


def test_frontend_design_has_responsive_and_motion_safe_states() -> None:
    css = (FRONTEND_DIR / "assets/styles.css").read_text(encoding="utf-8")

    assert "@media (max-width: 820px)" in css
    assert "@media (max-width: 560px)" in css
    assert "prefers-reduced-motion" in css
    assert "linear-gradient" not in css
    assert "radial-gradient" not in css
    assert re.search(r"\.result-panel\s*\{", css)


def test_deployment_artifacts_export_graph_and_drop_root() -> None:
    config = json.loads((PROJECT_DIR / "langgraph.json").read_text(encoding="utf-8"))
    dockerfile = (PROJECT_DIR / "Dockerfile").read_text(encoding="utf-8")

    assert config["graphs"]["asteria_investigation"] == "./agent.py:graph"
    assert "HEALTHCHECK" in dockerfile
    assert "USER asteria" in dockerfile
    assert "uvicorn" in dockerfile


def test_api_health_readiness_and_security_headers() -> None:
    from fastapi.testclient import TestClient

    module = load_api_module()
    client = TestClient(module.app)

    health = client.get("/health")
    ready = client.get("/ready")
    cockpit = client.get("/")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert ready.json()["status"] == "ready"
    assert cockpit.status_code == 200
    assert "default-src 'self'" in cockpit.headers["content-security-policy"]
    assert cockpit.headers["x-frame-options"] == "DENY"


def test_api_runs_investigation_and_enforces_configured_token(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    module = load_api_module()
    client = TestClient(module.app)
    payload = {"question": "Quelle est la franchise pour un degat des eaux ?"}

    response = client.post("/api/v1/investigations", json=payload)
    assert response.status_code == 200
    assert response.json()["mode_used"] == "rag"

    monkeypatch.setenv("ASTERIA_API_TOKEN", "test-token-with-enough-entropy")
    assert client.post("/api/v1/investigations", json=payload).status_code == 401
    authorized = client.post(
        "/api/v1/investigations",
        json=payload,
        headers={"Authorization": "Bearer test-token-with-enough-entropy"},
    )
    assert authorized.status_code == 200


def test_api_business_evaluation_is_a_green_release_gate() -> None:
    from fastapi.testclient import TestClient

    module = load_api_module()
    client = TestClient(module.app)

    response = client.post("/api/v1/evaluations")

    assert response.status_code == 200
    assert response.json()["release_gate_passed"] is True
    assert response.json()["pass_rate"] == 1.0
