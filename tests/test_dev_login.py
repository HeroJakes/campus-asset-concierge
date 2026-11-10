import pytest
from fastapi.testclient import TestClient

from campus_asset_concierge.api.app import create_app


@pytest.mark.parametrize("enabled", ["0", "1"])
def test_removed_dev_login_cannot_authenticate_or_change_logout_target(monkeypatch, enabled):
    monkeypatch.setenv("DEV_LOGIN", enabled)
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setenv("LOCAL_STAFF_PASSWORD", "test-staff")
    with TestClient(create_app(store=object()), base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
        assert client.get("/dev-login").status_code == 404
        assert client.post("/dev-login/staff").status_code == 404
        client.cookies.set("dev_account", "staff")
        assert client.get("/me").status_code == 401
        assert client.get("/locker", follow_redirects=False).headers["location"] == "/login"
        assert client.get("/me", auth=("equipment-staff", "test-staff")).status_code == 200
        assert client.get("/logout", follow_redirects=False).headers["location"] == "/login"
