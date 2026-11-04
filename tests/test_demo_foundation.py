import os

import pytest
from fastapi.testclient import TestClient

from campus_asset_concierge.api.demo import create_app
from campus_asset_concierge.storage.demo import DemoStore


@pytest.fixture
def demo(monkeypatch):
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        pytest.skip("Start the Firestore emulator to run the Stage 1.0 tests.")
    from uuid import uuid4

    for account in ("BORROWER_A", "BORROWER_B", "STAFF", "OPERATOR"):
        monkeypatch.setenv(f"DEMO_{account}_PASSWORD", f"test-{account.lower()}")
    store = DemoStore(document_id=f"test-{uuid4().hex}")
    with TestClient(create_app(store)) as client:
        yield client, store


def test_demo_sign_in_and_operator_permissions(demo):
    client, _ = demo
    assert client.get("/demo/me").status_code == 401
    assert client.get("/demo/me", auth=("staff-demo", "wrong")).status_code == 401
    for username, password, role in (
        ("borrower-a", "test-borrower_a", "borrower"),
        ("borrower-b", "test-borrower_b", "borrower"),
        ("staff-demo", "test-staff", "staff"),
        ("demo-operator", "test-operator", "demo_operator"),
    ):
        auth = (username, password)
        assert client.get("/demo/me", auth=auth).json() == {
            "username": username,
            "role": role,
        }
        if role != "demo_operator":
            assert client.get("/demo/clock", auth=auth).status_code == 403
            reset = client.post("/demo/reset", auth=auth, json={"scenario": "spare_available"})
            assert reset.status_code == 403
            advance = client.post("/demo/clock/advance", auth=auth, json={"minutes": 30})
            assert advance.status_code == 403
        if role != "borrower":
            assert client.get("/demo/reservations", auth=auth).status_code == 403


def test_reset_restores_clock_and_booking_data(demo):
    client, store = demo
    operator = ("demo-operator", "test-operator")
    borrower_a = ("borrower-a", "test-borrower_a")
    borrower_b = ("borrower-b", "test-borrower_b")
    assert client.get("/demo/clock", auth=operator).status_code == 409
    for scenario in ("spare_available", "spare_unavailable", "spare_available"):
        response = client.post("/demo/reset", auth=operator, json={"scenario": scenario})
        assert response.status_code == 204
        assert client.get("/demo/clock", auth=operator).json() == {
            "scenario": scenario,
            "current_time": "2026-11-07T02:00:00Z",
        }
        state = store.load()
        assert state is not None
        assert set(state["assets"]) == {"projector-a", "projector-b", "raspberry-pi-kit"}
        assert state["locker"]["compartments"] == {"a1": "empty", "a2": "empty"}
        assert state["loans"]["active-projector"]["status"] == "active"
        next_booking = client.get("/demo/reservations", auth=borrower_b).json()
        assert [booking["asset_id"] for booking in next_booking] == ["projector-a"]
        own_bookings = client.get("/demo/reservations", auth=borrower_a).json()
        expected = ["projector-b"] if scenario == "spare_unavailable" else []
        assert [booking["asset_id"] for booking in own_bookings] == expected
        if own_bookings:
            assert own_bookings[0]["pickup_at"] == next_booking[0]["pickup_at"]
            assert own_bookings[0]["due_at"] == next_booking[0]["due_at"]
        response = client.post("/demo/clock/advance", auth=operator, json={"minutes": 90})
        assert response.status_code == 204
        assert client.get("/demo/clock", auth=operator).json()["current_time"] == "2026-11-07T03:30:00Z"
