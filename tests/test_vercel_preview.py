from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest

from campus_asset_concierge import vercel_preview
from campus_asset_concierge.storage.local_state import LocalStateStore


@pytest.fixture
def preview_environment(monkeypatch):
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
    monkeypatch.delenv("DEV_LOGIN", raising=False)
    monkeypatch.delenv("VERCEL_URL", raising=False)
    monkeypatch.setenv("VERCEL_TEST_DOCUMENT_ID", "vercel-test-unit")
    monkeypatch.setenv("PREVIEW_ACCESS_TOKEN", "a" * 32)
    monkeypatch.setenv("GOOGLE_CREDENTIALS_JSON", "{}")
    credentials = object()
    monkeypatch.setattr(vercel_preview.Credentials, "from_service_account_info", lambda data: credentials)
    store_factory = Mock(return_value=SimpleNamespace(document=SimpleNamespace(path="demo/vercel-test-unit")))
    monkeypatch.setattr(vercel_preview, "LocalStateStore", store_factory)
    return store_factory, credentials


@pytest.mark.parametrize("name,value", [
    ("VERCEL_TEST_DOCUMENT_ID", "current"),
    ("VERCEL_TEST_DOCUMENT_ID", "vercel-test-nested/path"),
    ("PREVIEW_ACCESS_TOKEN", "short"),
    ("FIRESTORE_EMULATOR_HOST", ""),
    ("DEV_LOGIN", "1"),
])
def test_preview_rejects_unsafe_configuration(preview_environment, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError):
        vercel_preview.create_preview_app()
    preview_environment[0].assert_not_called()


def test_preview_protects_api_static_and_mcp_and_initializes_protocol(preview_environment):
    with TestClient(vercel_preview.create_preview_app(), base_url="http://127.0.0.1:8001") as client:
        for path in ("/", "/mcp", "/docs", "/static/locker.css", "/local-test/clock"):
            assert client.get(path).status_code == 401
        client.headers["x-preview-token"] = "a" * 32
        assert client.get("/").json() == {"status": "preview", "document": "demo/vercel-test-unit"}
        assert client.get("/dev-login").status_code == 404
        client.headers["Accept"] = "application/json, text/event-stream"
        initialized = client.post("/mcp", json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "preview-test", "version": "1"}},
        })
        assert initialized.status_code == 200
        assert "result" in initialized.json()
        tools = client.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert tools.status_code == 200
        assert len(tools.json()["result"]["tools"]) == 5
    factory, credentials = preview_environment
    factory.assert_called_once_with("vercel-test-unit", credentials=credentials)


def test_cloud_store_uses_supplied_credentials(monkeypatch):
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "campus-asset-concierge")
    client = Mock()
    monkeypatch.setattr("campus_asset_concierge.storage.local_state.firestore.Client", client)
    credentials = object()
    LocalStateStore("vercel-test-unit", credentials=credentials)
    client.assert_called_once_with(project="campus-asset-concierge", credentials=credentials)
