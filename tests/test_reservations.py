from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from conftest import BORROWER_A, BORROWER_B, OPERATOR


def offer(client, auth, pickup="2026-11-07T12:00", **fields):
    return client.post(
        "/reservation-offers",
        auth=auth,
        json={"category": "projector", "pickup_at": pickup, "duration_minutes": 60} | fields,
    )


def confirm(client, auth, offer_id):
    return client.post(f"/reservation-offers/{offer_id}/confirm", auth=auth)


def test_borrower_reviews_and_confirms_one_unit(booking_app):
    client, _ = booking_app
    response = offer(client, BORROWER_A)
    assert response.status_code == 201
    proposal = response.json()
    assert proposal["asset_id"] == "projector-b"
    assert proposal["pickup_location"] == "Campus Loan Desk"
    assert proposal["pickup_at"] == "2026-11-07T12:00:00+08:00"
    assert proposal["due_at"] == "2026-11-07T13:00:00+08:00"
    assert client.get("/reservations", auth=BORROWER_A).json() == []
    assert confirm(client, BORROWER_B, proposal["id"]).status_code == 404

    response = confirm(client, BORROWER_A, proposal["id"])
    assert response.status_code == 200
    reservation = response.json()
    assert reservation["asset_id"] == "projector-b"
    assert reservation["status"] == "confirmed"
    assert confirm(client, BORROWER_A, proposal["id"]).json() == reservation
    saved = client.get("/reservations", auth=BORROWER_A).json()
    assert saved == [reservation]


@pytest.mark.parametrize(
    ("pickup", "fields"),
    [
        (None, {}),
        ("2026-11-07", {}),
        ("2026-11-07T09:59", {}),
        ("2026-11-07T12:00", {"duration_minutes": None}),
        ("2026-11-07T12:00", {"duration_minutes": 0}),
        (
            "2026-11-07T12:00",
            {"duration_minutes": None, "due_at": "2026-11-07T12:00"},
        ),
    ],
)
def test_rejects_missing_or_invalid_times(booking_app, pickup, fields):
    client, _ = booking_app
    assert offer(client, BORROWER_A, pickup, **fields).status_code == 422


def test_on_schedule_loan_allows_booking_between_due_time_and_next_pickup(booking_app):
    client, _ = booking_app
    response = offer(
        client, BORROWER_B, "2026-11-07T11:00",
        duration_minutes=None, due_at="2026-11-07T12:00",
    )
    assert response.status_code == 201
    proposal = response.json()
    assert proposal["asset_id"] == "projector-a"
    assert confirm(client, BORROWER_B, proposal["id"]).status_code == 200


def test_confirmation_rechecks_overdue_loan_and_condition(booking_app):
    client, store = booking_app
    proposal = offer(client, BORROWER_B, "2026-11-07T11:30", duration_minutes=30).json()
    assert proposal["asset_id"] == "projector-a"
    advance = client.post("/local-test/clock/advance", auth=OPERATOR, json={"minutes": 61})
    assert advance.status_code == 204
    assert confirm(client, BORROWER_B, proposal["id"]).status_code == 409

    spare = offer(client, BORROWER_B).json()
    assert spare["asset_id"] == "projector-b"

    def hold_spare(state):
        state["assets"]["projector-b"]["condition"] = "hold"

    store.change(hold_spare)
    assert confirm(client, BORROWER_B, spare["id"]).status_code == 409
    assert offer(client, BORROWER_B).status_code == 409


def test_only_one_borrower_can_confirm_the_last_unit(booking_app):
    client, _ = booking_app
    auths = (BORROWER_A, BORROWER_B)
    offers = [offer(client, auth).json() for auth in auths]
    assert [proposal["asset_id"] for proposal in offers] == ["projector-b", "projector-b"]
    start = Barrier(2)

    def compete(auth, offer_id):
        start.wait(timeout=5)
        return confirm(client, auth, offer_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts = [
            pool.submit(compete, auth, proposal["id"])
            for auth, proposal in zip(auths, offers, strict=True)
        ]
        outcomes = [attempt.result(timeout=20) for attempt in attempts]

    assert sorted(result.status_code for result in outcomes) == [200, 409]
    assert offer(client, BORROWER_A).status_code == 409
    bookings = [client.get("/reservations", auth=auth).json() for auth in auths]
    assert sum(item["asset_id"] == "projector-b" for items in bookings for item in items) == 1
