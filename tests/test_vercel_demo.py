import os
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient
from google.api_core.exceptions import AlreadyExists
import pytest

from campus_asset_concierge import vercel_demo
from campus_asset_concierge.domain.scenarios import TestScenario as Scenario
from campus_asset_concierge.reassignment import Reassignment
from campus_asset_concierge.storage.local_state import LocalStateStore
from conftest import OPERATOR, STAFF


@pytest.fixture
def demo_environment(monkeypatch):
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
    monkeypatch.setenv("DEV_LOGIN", "0")
    monkeypatch.setenv("FIRESTORE_DOCUMENT_ID", vercel_demo.DEMO_DOCUMENT_ID)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "campus-asset-concierge")
    monkeypatch.setenv("GOOGLE_CREDENTIALS_JSON", "{}")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://demo.example")
    for account in ("BORROWER_A", "BORROWER_B", "STAFF", "OPERATOR"):
        monkeypatch.setenv(f"LOCAL_{account}_PASSWORD", f"test-{account.lower()}-" + "x" * 32)
    credentials = object()
    monkeypatch.setattr(vercel_demo.Credentials, "from_service_account_info", lambda data: credentials)
    factory = Mock(return_value=SimpleNamespace(document=SimpleNamespace(
        path=f"demo/{vercel_demo.DEMO_DOCUMENT_ID}")))
    monkeypatch.setattr(vercel_demo, "DemoStateStore", factory)
    return factory, credentials


@pytest.mark.parametrize("name,value", [
    ("FIRESTORE_DOCUMENT_ID", "current"),
    ("FIRESTORE_DOCUMENT_ID", "vercel-test-anything"),
    ("FIRESTORE_DOCUMENT_ID", ""),
    ("GOOGLE_CLOUD_PROJECT", "another-project"),
    ("FIRESTORE_EMULATOR_HOST", ""),
    ("DEV_LOGIN", "1"),
    ("LOCAL_OPERATOR_PASSWORD", "short"),
    ("LOCAL_STAFF_PASSWORD", ""),
    ("LOCAL_BORROWER_A_PASSWORD", "short"),
    ("LOCAL_BORROWER_B_PASSWORD", "short"),
    ("PUBLIC_BASE_URL", "http://demo.example"),
    ("PUBLIC_BASE_URL", "https://demo.example/mcp"),
    ("PUBLIC_BASE_URL", "https://user:password@demo.example"),
    ("PUBLIC_BASE_URL", "https://demo.example?token=secret"),
])
def test_demo_rejects_unsafe_configuration(demo_environment, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError):
        vercel_demo.create_demo_app()
    demo_environment[0].assert_not_called()


def test_demo_auth_browser_protection_and_public_mcp(demo_environment):
    with TestClient(vercel_demo.create_demo_app(), base_url="https://demo.example") as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/locker", follow_redirects=False).headers["location"] == "/login"
        assert client.get("/local-test/clock").status_code == 404
        assert client.post("/local-test/clock/advance", json={"minutes": 1}).status_code == 404
        assert client.get("/dev-login").status_code == 404
        operator = (OPERATOR[0], os.environ["LOCAL_OPERATOR_PASSWORD"])
        assert client.get("/me", auth=operator).json()["role"] == "operator"
        for headers in ({"Origin": "https://other.example"}, {"Origin": "null"},
                        {"Sec-Fetch-Site": "cross-site"}):
            assert client.post("/local-test/reset", auth=operator, headers=headers,
                               json={"scenario": "spare_available"}).status_code == 403
        client.headers["Accept"] = "application/json, text/event-stream"
        tools = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert tools.status_code == 200
        assert len(tools.json()["result"]["tools"]) == 5
        assert tools.headers["Cache-Control"] == "no-store"
        assert client.post("/mcp", headers={"Host": "other.example"}, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/list",
        }).status_code == 421
        login = client.post("/login", data={
            "username": "equipment-staff", "password": os.environ["LOCAL_STAFF_PASSWORD"],
            "role": "staff",
        }, headers={"Origin": "https://demo.example"}, follow_redirects=False)
        assert login.status_code == 303
        assert "Secure" in login.headers.get_list("set-cookie")[0]
        assert client.get("/me").json()["role"] == "staff"
    factory, credentials = demo_environment
    factory.assert_called_once_with(credentials=credentials)


def test_reset_checks_the_document_at_the_write_boundary():
    store = object.__new__(vercel_demo.DemoStateStore)
    store.document = SimpleNamespace(path="demo/current")
    store.seed = Mock()
    with pytest.raises(RuntimeError, match="restricted"):
        store.reset(Scenario.SPARE_AVAILABLE)
    store.seed.assert_not_called()


@pytest.mark.parametrize("username,password,role", [
    ("borrower-a", "BorrowerA2026!", "borrower"),
    ("borrower-b", "BorrowerB2026!", "borrower"),
    ("equipment-staff", "Staff2026!", "staff"),
])
def test_public_judge_accounts_keep_operator_and_internal_secrets_private(
    demo_environment, username, password, role,
):
    with TestClient(vercel_demo.create_demo_app(), base_url="https://demo.example") as client:
        page = client.get("/login")
        assert username in page.text and password in page.text
        assert "local-operator" not in page.text
        for label in ("STAFF", "BORROWER_A", "BORROWER_B", "OPERATOR"):
            assert os.environ[f"LOCAL_{label}_PASSWORD"] not in page.text
        form = {"username": username, "password": password, "role": role}
        assert client.post("/login", data=form, headers={"Origin": "https://other.example"}).status_code == 403
        assert client.post("/login", data=form, follow_redirects=False).status_code == 303
        assert client.get("/me").json() == {"username": username, "role": role}
        assert client.post("/local-test/reset", json={"scenario": "spare_available"}).status_code == 403
        client.get("/logout")
        assert client.get("/me", auth=(username, password)).json()["role"] == role
        assert client.get("/me", auth=("local-operator", password)).status_code == 401
        failed = client.post("/login", data={**form, "password": "incorrect"})
        assert failed.status_code == 401
        assert "Try an account" in failed.text


def test_first_seed_stops_if_the_document_exists(monkeypatch):
    store = Mock()
    store.seed.side_effect = AlreadyExists("already seeded")
    monkeypatch.setattr(vercel_demo, "_demo_store", lambda: store)
    recovery = Mock()
    monkeypatch.setattr(vercel_demo, "Recovery", recovery)
    with pytest.raises(AlreadyExists):
        vercel_demo.seed_demo()
    store.seed.assert_called_once_with(Scenario.SPARE_AVAILABLE, advance_minutes=61)
    recovery.assert_not_called()


def test_demo_reset_restores_the_showcase_only_on_the_emulator(monkeypatch):
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        pytest.skip("Start the Firestore emulator for the hosted-demo reset test.")
    # Construct the real store while the emulator setting is still present. The app's
    # hosted configuration is mocked below; this test never creates a cloud client.
    emulator_store = LocalStateStore(vercel_demo.DEMO_DOCUMENT_ID)
    if emulator_store.load() is not None:
        pytest.skip("The emulator demo document already exists; leave it untouched.")
    store = object.__new__(vercel_demo.DemoStateStore)
    store.client, store.document = emulator_store.client, emulator_store.document
    current = LocalStateStore("current").document
    current_before = current.get()
    monkeypatch.setattr(vercel_demo, "_demo_store", lambda: store)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://demo.example")
    for account in ("BORROWER_A", "BORROWER_B", "STAFF", "OPERATOR"):
        monkeypatch.setenv(f"LOCAL_{account}_PASSWORD", "test-" + account + "x" * 32)
    operator = (OPERATOR[0], os.environ["LOCAL_OPERATOR_PASSWORD"])
    staff = (STAFF[0], os.environ["LOCAL_STAFF_PASSWORD"])
    try:
        vercel_demo.seed_demo()
        initial = store.load()
        assert initial["elapsed_minutes"] == 61
        assert initial["loans"]["active-projector"]["status"] == "overdue"
        proposal = initial["substitution_proposals"]["next-projector"]
        assert proposal["status"] == "pending_staff_approval"
        with pytest.raises(AlreadyExists):
            vercel_demo.seed_demo()
        assert store.load() == initial
        Reassignment(store).approve(STAFF[0], "next-projector", proposal["id"])
        assert store.load()["reservations"]["next-projector"]["asset_id"] == "projector-b"
        with TestClient(vercel_demo.create_demo_app(), base_url="https://demo.example") as client:
            payload = {"scenario": "spare_available"}
            assert client.post("/local-test/reset", json=payload).status_code == 401
            assert client.post("/local-test/reset", auth=staff, json=payload).status_code == 403
            assert client.post("/local-test/reset", auth=operator, json=payload,
                               headers={"Origin": "https://demo.example"}).status_code == 204
            restored = store.load()
            assert restored["reservations"]["next-projector"]["asset_id"] == "projector-a"
            assert restored["substitution_proposals"]["next-projector"]["status"] == "pending_staff_approval"
            assert restored["elapsed_minutes"] == 61
            assert client.post("/recovery/run", auth=staff).status_code == 200
            assert store.load() == restored
            current_after = current.get()
            assert current_after.to_dict() == current_before.to_dict()
            assert current_after.update_time == current_before.update_time
    finally:
        store.document.delete()
