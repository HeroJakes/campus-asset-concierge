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


def test_projector_requirements_are_saved_and_rechecked(booking_app):
    client, store = booking_app
    assert offer(client, BORROWER_A, require_built_in_speakers=True).status_code == 409
    response = offer(client, BORROWER_A, require_hdmi=True)
    assert response.status_code == 201
    offered = response.json()
    assert offered["require_hdmi"] is True
    assert offered["require_built_in_speakers"] is False

    def remove_hdmi(state):
        state["assets"]["projector-b"].pop("has_hdmi")

    store.change(remove_hdmi)
    assert confirm(client, BORROWER_A, offered["id"]).status_code == 409
    assert client.get("/reservations", auth=BORROWER_A).json() == []
    assert offer(client, BORROWER_A).status_code == 201


@pytest.mark.parametrize("field", ["require_hdmi", "require_built_in_speakers"])
@pytest.mark.parametrize("value", ["true", "false", 1, 0, None])
def test_requirements_reject_non_boolean_values(booking_app, field, value):
    client, _ = booking_app
    assert offer(client, BORROWER_A, **{field: value}).status_code == 422


@pytest.mark.parametrize("field", ["require_hdmi", "require_built_in_speakers"])
def test_projector_requirements_cannot_be_applied_to_kits(booking_app, field):
    client, _ = booking_app
    assert offer(client, BORROWER_A, category="raspberry_pi_kit", **{field: True}).status_code == 422
    assert offer(client, BORROWER_A, category="raspberry_pi_kit", **{field: False}).status_code == 201


@pytest.mark.parametrize("hdmi,speakers", [(True, False), (False, True), (True, True), (False, False)])
def test_all_requirement_combinations_use_stable_unit_order(booking_app, hdmi, speakers):
    client, _ = booking_app
    offered = offer(client, BORROWER_A, "2026-11-07T13:00", require_hdmi=hdmi, require_built_in_speakers=speakers).json()
    assert offered["asset_id"] == "projector-a"
    booked = confirm(client, BORROWER_A, offered["id"]).json()
    assert booked["require_hdmi"] is hdmi
    assert booked["require_built_in_speakers"] is speakers


def test_existing_offer_without_requirements_still_confirms(booking_app):
    client, store = booking_app
    offered = offer(client, BORROWER_A).json()

    def old_offer(state):
        saved = state["reservation_offers"][offered["id"]]
        del saved["require_hdmi"]
        del saved["require_built_in_speakers"]

    store.change(old_offer)
    assert confirm(client, BORROWER_A, offered["id"]).status_code == 200


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


def test_open_offers_per_borrower_are_capped_but_confirmed_ones_stay(booking_app):
    client, store = booking_app
    confirmed = offer(client, BORROWER_A, pickup="2026-11-07T14:00").json()["id"]
    assert confirm(client, BORROWER_A, confirmed).status_code == 200
    ids = [offer(client, BORROWER_A).json()["id"] for _ in range(7)]
    other = offer(client, BORROWER_B).json()["id"]

    offers = store.load()["reservation_offers"]
    assert [offer_id in offers for offer_id in ids] == [False, False, True, True, True, True, True]
    assert other in offers and confirmed in offers
    assert confirm(client, BORROWER_A, ids[0]).status_code == 404
    assert confirm(client, BORROWER_A, confirmed).status_code == 200  # repeat confirm still works
    assert "offered_at" not in confirm(client, BORROWER_A, ids[-1]).json()
