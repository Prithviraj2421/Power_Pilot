from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.frontend import mount_frontend


@pytest.fixture
def site(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>SPA SHELL</html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('app')", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg>icon</svg>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("TOP SECRET", encoding="utf-8")
    return dist


@pytest.fixture
def client(site: Path) -> TestClient:
    app = FastAPI()

    @app.get("/api/v1/ping")
    def ping() -> dict:
        return {"pong": True}

    @app.get("/health")
    def health() -> dict:
        return {"status": "healthy"}

    mount_frontend(app, site)
    return TestClient(app)


def test_the_root_and_client_side_routes_return_the_app_shell(client: TestClient) -> None:
    for path in ("/", "/live", "/workspace", "/some/deep/route"):
        response = client.get(path)
        assert response.status_code == 200 and "SPA SHELL" in response.text, path


def test_built_assets_and_root_files_are_served_as_themselves(client: TestClient) -> None:
    assert client.get("/assets/app.js").text == "console.log('app')"
    assert client.get("/favicon.svg").text == "<svg>icon</svg>"


def test_api_routes_still_win_over_the_fallback(client: TestClient) -> None:
    assert client.get("/api/v1/ping").json() == {"pong": True}
    assert client.get("/health").json() == {"status": "healthy"}


def test_an_unknown_api_path_is_a_404_not_the_app_shell(client: TestClient) -> None:
    for path in ("/api/v1/nope", "/api/", "/docs-x", "/openapi.json.bak", "/healthz"):
        assert client.get(path).status_code == 404, path


def test_fastapis_own_documents_are_not_shadowed_by_the_fallback(client: TestClient) -> None:
    assert client.get("/openapi.json").json()["info"]["title"]
    assert "swagger" in client.get("/docs").text.lower()


def test_paths_that_climb_out_of_the_site_never_leak_files(client: TestClient) -> None:
    for path in ("/../secret.txt", "/..%2Fsecret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"):
        response = client.get(path)
        assert "TOP SECRET" not in response.text, path


def test_a_missing_build_fails_loudly_instead_of_serving_nothing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="npm run build"):
        mount_frontend(FastAPI(), tmp_path / "nowhere")
