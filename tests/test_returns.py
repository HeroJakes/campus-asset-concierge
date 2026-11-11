from datetime import timedelta

import pytest

from campus_asset_concierge.agent.reservations import create_reservation_agent
from campus_asset_concierge.domain.reservations import (
    ReservationError, eligible_unit, find_free_compartment, local_clock,
)
from campus_asset_concierge.domain.scenarios import BORROWER_A as BORROWER_A_ID
from campus_asset_concierge.reservations import Reservations
from conftest import BORROWER_A, BORROWER_B, OPERATOR, STAFF

# The seeded active loan is projector-a for borrower-a, and it has NO reservation,
# so returning it exercises the asset-keyed path the spec calls out.
PA = "projector-a"


def return_request(client, asset_id=PA, auth=BORROWER_A):
    return client.post(f"/assets/{asset_id}/return-request", auth=auth)


def return_unlock(client, asset_id, code, auth=BORROWER_A):
    return client.post(f"/assets/{asset_id}/return-unlock", auth=auth, json={"code": code})


def return_drop(client, asset_id=PA, auth=BORROWER_A):
    return client.post(f"/assets/{asset_id}/return-drop", auth=auth)


def verify(client, asset_id=PA, result="pass", auth=STAFF):
    return client.post(f"/assets/{asset_id}/verify-return", auth=auth, json={"result": result})


def advance(client, minutes):
    response = client.post("/local-test/clock/advance", auth=OPERATOR, json={"minutes": minutes})
    assert response.status_code == 204


def my_return(client, asset_id=PA, auth=BORROWER_A):
    returns = client.get("/returns", auth=auth).json()
    return next(item for item in returns if item["asset_id"] == asset_id)


def code_for(client, asset_id=PA, auth=BORROWER_A):
    return my_return(client, asset_id, auth)["code"]


def wrong_code_for(code):
    return "000000" if code != "000000" else "000001"


def state(store):
    return store.load()


def actions(store):
    return [event["action"] for event in state(store).get("audit_events", [])]


def set_loan_status(store, loan_id, status):
    def change(data):
        data["loans"][loan_id]["status"] = status

    store.change(change)


def dropped(client):
    """Drive projector-a to awaiting_check and return its code."""
    assert return_request(client).status_code == 200
    code = code_for(client)
    assert return_unlock(client, PA, code).status_code == 200
    assert return_drop(client).status_code == 200
    return code


def book(client, auth=BORROWER_A, pickup="2026-11-07T13:00", category="projector", minutes=60):
    offer = client.post(
        "/reservation-offers",
        auth=auth,
        json={"category": category, "pickup_at": pickup, "duration_minutes": minutes},
    )
    return offer


# --- HTTP seam: the full flow and its records ---------------------------------


def test_full_flow_return_pass_frees_the_unit(booking_app):
    client, store = booking_app
    assert state(store)["loans"]["active-projector"]["status"] == "active"

    assert return_request(client).status_code == 200
    assert my_return(client)["step"] == "enter_code"
    code = code_for(client)
    assert len(code) == 6

    assert return_unlock(client, PA, code).status_code == 200
    assert my_return(client)["step"] == "confirm_drop"

    dropped_view = return_drop(client).json()
    assert dropped_view["loan_status"] == "awaiting_check"

    passed = verify(client).json()
    assert passed["loan_status"] == "returned"
    assert passed["result"] == "pass"

    saved = state(store)
    assert saved["loans"]["active-projector"]["status"] == "returned"
    assert saved["assets"][PA]["condition"] == "good"
    assert saved["locker"]["compartments"][dropped_view["compartment"]] == "empty"

    # The unit is bookable again, for a window after the seeded next reservation.
    offer = book(client)
    assert offer.status_code == 201
    assert offer.json()["asset_id"] == PA


def test_failed_return_puts_the_unit_on_hold(booking_app):
    client, store = booking_app
    dropped(client)
    assert verify(client, result="fail").json()["result"] == "fail"

    saved = state(store)
    assert saved["loans"]["active-projector"]["status"] == "returned"
    assert saved["assets"][PA]["condition"] == "hold"
    # A held unit is out of new offers.
    now = local_clock(saved)
    assert not eligible_unit(saved, PA, "projector", now + timedelta(hours=4), now + timedelta(hours=5), now)


def test_an_overdue_loan_can_be_returned(booking_app):
    client, store = booking_app
    advance(client, 61)  # past the 11:00 due time
    set_loan_status(store, "active-projector", "overdue")
    dropped(client)
    assert verify(client).json()["loan_status"] == "returned"


# --- roles and ownership ------------------------------------------------------


def test_roles_and_ownership_are_enforced(booking_app):
    client, _ = booking_app
    # Staff and operator cannot run borrower return actions.
    assert return_request(client, auth=STAFF).status_code == 403
    assert return_request(client, auth=OPERATOR).status_code == 403
    # Borrower B has no loan on projector-a.
    assert return_request(client, auth=BORROWER_B).status_code == 404
    # A real request, then a non-staff tries to verify.
    assert return_request(client).status_code == 200
    assert verify(client, auth=BORROWER_A).status_code == 403


# --- the return code ----------------------------------------------------------


def test_return_code_rejections(booking_app):
    client, store = booking_app
    assert return_request(client).status_code == 200
    code = code_for(client)

    # Wrong user does not spend a try.
    assert return_unlock(client, PA, code, auth=BORROWER_B).status_code == 404
    assert state(store)["return_access"][PA]["failed_tries"] == 0
    # Wrong code is rejected and counted.
    assert return_unlock(client, PA, wrong_code_for(code)).status_code == 403
    assert state(store)["return_access"][PA]["failed_tries"] == 1
    # Right code works, and cannot be replayed.
    assert return_unlock(client, PA, code).status_code == 200
    assert return_unlock(client, PA, code).status_code == 409


def test_return_code_expires_after_thirty_minutes(booking_app):
    client, _ = booking_app
    assert return_request(client).status_code == 200
    code = code_for(client)
    advance(client, 31)
    assert return_unlock(client, PA, code).status_code == 409
    assert my_return(client)["step"] == "code_expired"


def test_five_wrong_tries_block_the_return_code(booking_app):
    client, store = booking_app
    assert return_request(client).status_code == 200
    code = code_for(client)
    for _ in range(5):
        assert return_unlock(client, PA, wrong_code_for(code)).status_code == 403
    assert state(store)["return_access"][PA]["failed_tries"] == 5
    blocked = return_unlock(client, PA, code)
    assert blocked.status_code == 409
    assert "blocked" in blocked.json()["detail"]
    assert my_return(client)["step"] == "code_blocked"


# --- compartments: full, idempotent request, reclaim --------------------------


def test_request_rejected_when_both_compartments_are_full(booking_app):
    client, _ = booking_app
    # Occupy both compartments with pickups, not returns.
    first = client.post("/reservation-offers", auth=BORROWER_A,
                        json={"category": "projector", "pickup_at": "2026-11-07T10:30", "duration_minutes": 60})
    second = client.post("/reservation-offers", auth=BORROWER_A,
                        json={"category": "raspberry_pi_kit", "pickup_at": "2026-11-07T10:30", "duration_minutes": 60})
    first_id = client.post(f"/reservation-offers/{first.json()['id']}/confirm", auth=BORROWER_A).json()["id"]
    second_id = client.post(f"/reservation-offers/{second.json()['id']}/confirm", auth=BORROWER_A).json()["id"]
    assert client.post(f"/reservations/{first_id}/load", auth=STAFF).status_code == 200
    assert client.post(f"/reservations/{second_id}/load", auth=STAFF).status_code == 200
    assert return_request(client).status_code == 409


def test_repeated_request_before_drop_keeps_one_code_and_compartment(booking_app):
    client, store = booking_app
    first = return_request(client).json()
    second = return_request(client).json()
    assert second["compartment"] == first["compartment"]
    assert code_for(client) == state(store)["return_access"][PA]["code"]
    occupied = [c for c in state(store)["locker"]["compartments"].values() if c != "empty"]
    assert occupied == ["return_reserved"]


def test_expired_undropped_return_frees_its_compartment(booking_app):
    client, _ = booking_app
    reserved = return_request(client).json()["compartment"]
    # Fill the other compartment with a pickup so the locker is full.
    other = client.post("/reservation-offers", auth=BORROWER_A,
                        json={"category": "raspberry_pi_kit", "pickup_at": "2026-11-07T10:30", "duration_minutes": 60})
    other_id = client.post(f"/reservation-offers/{other.json()['id']}/confirm", auth=BORROWER_A).json()["id"]
    assert client.post(f"/reservations/{other_id}/load", auth=STAFF).status_code == 200
    advance(client, 31)  # the first return code expires, undropped
    again = return_request(client)
    assert again.status_code == 200  # without reclaim the full locker would 409
    assert again.json()["compartment"] == reserved


# --- eligible_unit seam: the unit stays unavailable mid-return ----------------


def test_unit_mid_return_is_not_offered(booking_app):
    client, store = booking_app
    assert return_request(client).status_code == 200  # code issued, not dropped
    saved = state(store)
    now = local_clock(saved)
    assert not eligible_unit(saved, PA, "projector", now + timedelta(hours=4), now + timedelta(hours=5), now)


def test_unit_unavailable_while_awaiting_check_then_available_after_pass(booking_app):
    client, store = booking_app
    dropped(client)
    saved = state(store)
    now = local_clock(saved)
    window = (now + timedelta(hours=4), now + timedelta(hours=5))
    assert not eligible_unit(saved, PA, "projector", window[0], window[1], now)
    assert verify(client).status_code == 200
    saved = state(store)
    assert eligible_unit(saved, PA, "projector", window[0], window[1], local_clock(saved))


# --- idempotency and guards ---------------------------------------------------


def test_repeated_drop_and_verify_make_no_duplicates(booking_app):
    client, store = booking_app
    dropped(client)
    assert return_drop(client).json()["loan_status"] == "awaiting_check"  # repeat drop is safe
    assert verify(client).json()["result"] == "pass"
    assert verify(client).json()["result"] == "pass"  # repeat verify returns the same result
    assert actions(store).count("return_passed") == 1


def test_verify_before_drop_is_rejected(booking_app):
    client, _ = booking_app
    assert return_request(client).status_code == 200
    assert verify(client).status_code == 409


def test_drop_before_unlock_is_rejected(booking_app):
    client, _ = booking_app
    assert return_request(client).status_code == 200
    assert return_drop(client).status_code == 409


# --- the code never leaks -----------------------------------------------------


def test_return_code_stays_out_of_reservations_and_the_agent(booking_app):
    client, store = booking_app
    assert return_request(client).status_code == 200
    code = code_for(client)
    assert code not in client.get("/reservations", auth=BORROWER_A).text

    agent = create_reservation_agent(Reservations(store), BORROWER_A_ID, model="none")
    tool = next(t for t in agent.tools if t.__name__ == "check_return_status")
    result = tool()
    assert result["returns"], "the borrower should have an open return"
    assert code not in str(result)
    assert all("code" not in item for item in result["returns"])


def test_a_second_return_cycle_issues_a_fresh_code(booking_app):
    client, store = booking_app
    dropped(client)
    assert verify(client).status_code == 200  # first return complete, record lingers
    # Simulate the same unit going out on a new loan.
    set_loan_status(store, "active-projector", "active")
    assert return_request(client).status_code == 200
    fresh = my_return(client)
    assert fresh["step"] == "enter_code"  # not stuck on the stale completed record
    assert "code" in fresh


def test_pickup_and_return_audit_events_share_one_shape(booking_app):
    client, store = booking_app
    offer = client.post("/reservation-offers", auth=BORROWER_A,
                        json={"category": "projector", "pickup_at": "2026-11-07T10:30", "duration_minutes": 60})
    rid = client.post(f"/reservation-offers/{offer.json()['id']}/confirm", auth=BORROWER_A).json()["id"]
    assert client.post(f"/reservations/{rid}/load", auth=STAFF).status_code == 200
    assert return_request(client).status_code == 200

    events = state(store)["audit_events"]
    assert all("asset_id" in event and "reservation_id" in event for event in events)
    loaded = next(event for event in events if event["action"] == "loaded")
    requested = next(event for event in events if event["action"] == "return_requested")
    assert loaded["asset_id"] == "projector-b" and loaded["reservation_id"] == rid
    assert requested["asset_id"] == PA and requested["reservation_id"] is None


# --- the staff page survives a reservation-less return event ------------------


def test_staff_page_renders_with_a_return_audit_event(booking_app):
    client, _ = booking_app
    assert return_request(client).status_code == 200  # writes an event with a null reservation_id
    dropped(client)
    page = client.get("/locker", auth=STAFF)
    assert page.status_code == 200
    assert "Returns to check" in page.text  # the awaiting-check item is shown to staff
    assert 'data-open-dialog="return-projector-a"' in page.text
    assert '<dialog class="review-dialog" id="return-projector-a"' in page.text
    assert '/assets/projector-a/verify-return' in page.text
    assert 'data-body=\'{"result":"pass"}\'' in page.text
    assert 'data-body=\'{"result":"fail"}\'' in page.text


# --- compartment reuse: expired, unlocked, and abandoned returns --------------


def _load_booking(client, category, pickup):
    offer = client.post("/reservation-offers", auth=BORROWER_A,
                        json={"category": category, "pickup_at": pickup, "duration_minutes": 60})
    reservation_id = client.post(f"/reservation-offers/{offer.json()['id']}/confirm", auth=BORROWER_A).json()["id"]
    loaded = client.post(f"/reservations/{reservation_id}/load", auth=STAFF)
    assert loaded.status_code == 200
    return reservation_id, loaded.json()["compartment"]


def test_new_return_code_frees_the_old_compartment(booking_app):
    client, store = booking_app
    pickup_id, pickup_compartment = _load_booking(client, "raspberry_pi_kit", "2026-11-07T10:30")
    first = return_request(client).json()["compartment"]
    advance(client, 30)
    code = next(item for item in client.get("/pickups", auth=BORROWER_A).json() if item["id"] == pickup_id)["code"]
    assert client.post(f"/reservations/{pickup_id}/unlock", auth=BORROWER_A, json={"code": code}).status_code == 200
    assert client.post(f"/reservations/{pickup_id}/confirm-pickup", auth=BORROWER_A).status_code == 200
    advance(client, 1)  # the first return code has expired, unused

    second = return_request(client).json()["compartment"]

    assert second == pickup_compartment != first
    assert state(store)["locker"]["compartments"] == {second: "return_reserved", first: "empty"}


def test_unlocked_return_can_still_be_dropped_after_the_code_window(booking_app):
    client, store = booking_app
    _load_booking(client, "raspberry_pi_kit", "2026-11-07T10:30")
    assert return_request(client).status_code == 200
    advance(client, 29)
    assert return_unlock(client, PA, code_for(client)).status_code == 200
    advance(client, 2)

    assert my_return(client)["step"] == "confirm_drop"
    saved = state(store)
    with pytest.raises(ReservationError):  # the open compartment is not reclaimed
        find_free_compartment(saved, local_clock(saved))
    assert return_drop(client).status_code == 200


def test_loading_reclaims_a_compartment_from_an_abandoned_return(booking_app):
    client, _ = booking_app
    abandoned = return_request(client).json()["compartment"]
    _load_booking(client, "projector", "2026-11-07T10:30")
    advance(client, 31)

    _, compartment = _load_booking(client, "raspberry_pi_kit", "2026-11-07T10:45")

    assert compartment == abandoned
