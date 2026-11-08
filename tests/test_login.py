import time

from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner, URLSafeTimedSerializer
import pytest

from campus_asset_concierge.api.app import create_app
from campus_asset_concierge.api.auth import SESSION_COOKIE, SESSION_MAX_AGE


@pytest.fixture
def login_client(monkeypatch):
    monkeypatch.setenv("DEV_LOGIN", "0")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    for label in ("BORROWER_A", "BORROWER_B", "STAFF", "OPERATOR"):
        monkeypatch.setenv(f"LOCAL_{label}_PASSWORD", f"test-{label.lower()}")
    # Authentication must not require any Firestore access.
    with TestClient(create_app(store=object()), base_url="https://campus.example") as client:
        yield client


def sign_in(client, username="borrower-a", password="test-borrower_a", role="borrower", **kwargs):
    return client.post("/login", data={"username": username, "password": password, "role": role},
                       follow_redirects=False, **kwargs)


def test_login_page_is_public_and_locker_redirects(login_client):
    page = login_client.get("/login")
    assert page.status_code == 200
    for text in ("Welcome back", "Student / Borrower", "Equipment Staff", 'autocomplete="username"',
                 'autocomplete="current-password"', 'aria-label="Show password"'):
        assert text in page.text
    assert "Demo only" not in page.text
    for path in ("/", "/locker", "/locker/bookings"):
        response = login_client.get(path, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
        assert "www-authenticate" not in response.headers
    assert page.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("username,password,role", [
    ("borrower-a", "test-borrower_a", "borrower"),
    ("borrower-b", "test-borrower_b", "borrower"),
    ("equipment-staff", "test-staff", "staff"),
])
def test_login_uses_real_account_role_and_secure_cookie(login_client, username, password, role):
    response = sign_in(login_client, username, password, role)
    assert response.status_code == 303
    assert response.headers["location"] == "/locker"
    cookie = response.headers.get_list("set-cookie")[0]
    for flag in ("HttpOnly", "SameSite=strict", "Secure", f"Max-Age={SESSION_MAX_AGE}", "Path=/"):
        assert flag in cookie
    assert password not in cookie
    assert login_client.get("/me").json() == {"username": username, "role": role}
    assert login_client.get("/login", follow_redirects=False).headers["location"] == "/locker"
    forbidden = "/recovery" if role == "borrower" else "/reservations"
    assert login_client.get(forbidden).status_code == 403
    assert login_client.post("/local-test/reset", json={"scenario": "spare_available"}).status_code == 403


@pytest.mark.parametrize("username,password,role", [
    ("borrower-a", "wrong-password", "borrower"),
    ("borrower-a", "test-borrower_a", "staff"),
    ("equipment-staff", "test-staff", "borrower"),
    ("local-operator", "test-operator", "staff"),
    ("missing-user", "anything", "borrower"),
])
def test_bad_credentials_and_role_mismatch_do_not_create_session(login_client, username, password, role):
    response = sign_in(login_client, username, password, role)
    assert response.status_code == 401
    assert "Check your username, password, and account type." in response.text
    assert "www-authenticate" not in response.headers
    assert SESSION_COOKIE not in login_client.cookies
    assert f'value="{password}"' not in response.text


@pytest.mark.parametrize("headers", [
    {"Origin": "https://other.example"}, {"Origin": "null"}, {"Sec-Fetch-Site": "cross-site"},
])
def test_cross_site_login_and_cookie_mutations_are_rejected(login_client, headers):
    assert sign_in(login_client, headers=headers).status_code == 403
    assert SESSION_COOKIE not in login_client.cookies
    assert sign_in(login_client).status_code == 303
    response = login_client.post("/reservation-offers", json={
        "category": "projector", "pickup_at": "2026-11-07T14:00", "duration_minutes": 60,
    }, headers=headers)
    assert response.status_code == 403  # Before any store access.
    assert login_client.get("/logout", headers=headers, follow_redirects=False).status_code == 403


def test_cookie_tampering_expiry_and_password_rotation(login_client, monkeypatch):
    assert sign_in(login_client).status_code == 303
    original = login_client.cookies.get(SESSION_COOKIE)
    login_client.cookies.clear()
    login_client.cookies.set(SESSION_COOKIE, original.replace("borrower-a:", "equipment-staff:", 1))
    assert login_client.get("/me").status_code == 401
    login_client.cookies.clear()
    login_client.cookies.set(SESSION_COOKIE, original)
    now = int(time.time())
    with monkeypatch.context() as expired:
        expired.setattr(TimestampSigner, "get_timestamp", lambda self: now + SESSION_MAX_AGE + 5)
        assert login_client.get("/me").status_code == 401
    monkeypatch.setenv("LOCAL_BORROWER_A_PASSWORD", "rotated-password")
    assert login_client.get("/me").status_code == 401


def test_operator_cannot_use_a_browser_session_and_basic_still_works(login_client):
    signer = URLSafeTimedSerializer("test-operator", salt="campus-browser-session-v1")
    login_client.cookies.set(SESSION_COOKIE, f"local-operator:{signer.dumps('local-operator')}")
    assert login_client.get("/me").status_code == 401
    login_client.cookies.clear()
    for username, password, role in (("equipment-staff", "test-staff", "staff"),
                                     ("local-operator", "test-operator", "operator")):
        assert login_client.get("/me", auth=(username, password)).json()["role"] == role


def test_logout_clears_session_and_uses_account_cookie_before_legacy_basic(login_client):
    assert sign_in(login_client).status_code == 303
    assert login_client.get("/me", auth=("equipment-staff", "test-staff")).json()["role"] == "borrower"
    response = login_client.get("/logout", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert SESSION_COOKIE not in login_client.cookies
    assert login_client.get("/me").status_code == 401


def test_cookie_survives_another_app_instance_and_form_has_no_open_redirect(login_client):
    response = sign_in(login_client, params={"next": "https://other.example"})
    assert response.headers["location"] == "/locker"
    with TestClient(create_app(store=object()), base_url="https://campus.example") as other:
        other.cookies.update(login_client.cookies)
        assert other.get("/me").json()["username"] == "borrower-a"


def test_browser_session_drives_real_locker_views_on_emulator(booking_app):
    client, store = booking_app
    response = sign_in(client)
    assert response.status_code == 303
    assert client.get("/locker").status_code == 200
    assert client.get("/reservations").json() == []
    assert client.get("/recovery").status_code == 403
    client.get("/logout")
    assert sign_in(client, "equipment-staff", "test-staff", "staff").status_code == 303
    assert client.get("/locker").status_code == 200
    assert client.get("/locker/bookings").status_code == 200
    assert client.get("/reservations").status_code == 403
    assert store.load()["scenario"] == "spare_available"
