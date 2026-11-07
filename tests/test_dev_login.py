import pytest
from fastapi.testclient import TestClient

from campus_asset_concierge.api.app import create_app


@pytest.fixture
def dev_client(monkeypatch):
    monkeypatch.setenv("DEV_LOGIN", "1")
    # These login and permission checks must never read or write a database.
    with TestClient(create_app(store=object()), base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
        yield client


@pytest.mark.parametrize("label,username,role", [
    ("borrower_a", "borrower-a", "borrower"),
    ("borrower_b", "borrower-b", "borrower"),
    ("staff", "equipment-staff", "staff"),
])
def test_dev_login_selects_an_existing_account_without_password(dev_client, label, username, role):
    page = dev_client.get("/dev-login")
    assert page.status_code == 200
    assert "No password is needed" in page.text
    login = dev_client.post(f"/dev-login/{label}", follow_redirects=False)
    assert login.status_code == 303
    assert "HttpOnly" in login.headers["set-cookie"]
    assert "SameSite=strict" in login.headers["set-cookie"]
    assert dev_client.get("/me").json() == {"username": username, "role": role}
    assert dev_client.get("/local-test/clock").status_code == 403
    if role == "borrower":
        assert dev_client.get("/recovery").status_code == 403
    else:
        assert dev_client.get("/reservations").status_code == 403
    assert dev_client.get("/logout", follow_redirects=False).status_code == 303
    assert dev_client.get("/me").status_code == 401


def test_dev_login_redirects_locker_and_rejects_unknown_or_cross_origin_accounts(dev_client):
    response = dev_client.get("/locker", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/dev-login"
    assert dev_client.post("/dev-login/local-operator").status_code == 404
    assert dev_client.post("/dev-login/staff", headers={"Origin": "https://other.example"}).status_code == 403
    dev_client.cookies.set("dev_account", "local-operator")
    assert dev_client.get("/me").status_code == 401


@pytest.mark.parametrize("enabled,host,peer", [
    ("0", "localhost", "127.0.0.1"),
    ("1", "public.example", "127.0.0.1"),
    ("1", "localhost", "192.0.2.1"),
])
def test_dev_login_is_unavailable_outside_enabled_loopback_mode(monkeypatch, enabled, host, peer):
    monkeypatch.setenv("DEV_LOGIN", enabled)
    monkeypatch.setenv("LOCAL_STAFF_PASSWORD", "test-staff")
    with TestClient(create_app(store=object()), base_url=f"http://{host}", client=(peer, 50000)) as client:
        assert client.get("/dev-login").status_code == 404
        assert client.post("/dev-login/staff", follow_redirects=False).status_code == 404
        client.cookies.set("dev_account", "staff")
        assert client.get("/me").status_code == 401
        assert client.get("/me", auth=("equipment-staff", "test-staff")).status_code == 200
