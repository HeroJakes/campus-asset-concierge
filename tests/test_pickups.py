import pytest

from campus_asset_concierge.agent.reservations import create_reservation_agent
from campus_asset_concierge.domain.scenarios import BORROWER_A as BORROWER_A_ID
from campus_asset_concierge.reservations import Reservations
from conftest import BORROWER_A, BORROWER_B, OPERATOR, STAFF

PICKUP = "2026-11-07T10:30"  # 30 minutes after the seeded clock starts
# The kit has one unit, so a booking can't quietly land on another one.
KIT = "raspberry_pi_kit"


def book(client, auth=BORROWER_A, pickup=PICKUP, category="projector", minutes=60):
    offer = client.post(
        "/reservation-offers",
        auth=auth,
        json={"category": category, "pickup_at": pickup, "duration_minutes": minutes},
    )
    assert offer.status_code == 201, offer.text
    confirmed = client.post(f"/reservation-offers/{offer.json()['id']}/confirm", auth=auth)
    assert confirmed.status_code == 200, confirmed.text
    return confirmed.json()["id"]


def load(client, reservation_id, auth=STAFF):
    return client.post(f"/reservations/{reservation_id}/load", auth=auth)


def unlock(client, reservation_id, code, auth=BORROWER_A):
    return client.post(f"/reservations/{reservation_id}/unlock", auth=auth, json={"code": code})


def pick_up(client, reservation_id, auth=BORROWER_A):
    return client.post(f"/reservations/{reservation_id}/confirm-pickup", auth=auth)


def advance(client, minutes):
    response = client.post("/local-test/clock/advance", auth=OPERATOR, json={"minutes": minutes})
    assert response.status_code == 204


def my_pickup(client, reservation_id, auth=BORROWER_A):
    pickups = client.get("/pickups", auth=auth).json()
    return next(pickup for pickup in pickups if pickup["id"] == reservation_id)


def code_for(client, reservation_id, auth=BORROWER_A):
    return my_pickup(client, reservation_id, auth)["code"]


def wrong_code_for(code):
    return "000000" if code != "000000" else "000001"


def state(store):
    return store.load()


def actions(store):
    return [event["action"] for event in state(store).get("audit_events", [])]


def loaded_and_open(client):
    reservation_id = book(client)
    assert load(client, reservation_id).status_code == 200
    advance(client, 30)
    return reservation_id, code_for(client, reservation_id)


def test_full_flow_from_reservation_to_active_loan(booking_app):
    client, store = booking_app
    reservation_id = book(client)
    assert my_pickup(client, reservation_id)["step"] == "waiting_for_loading"

    loaded = load(client, reservation_id)
    assert loaded.status_code == 200
    assert loaded.json()["status"] == "ready_for_pickup"
    assert loaded.json()["compartment"] == "a1"
    assert state(store)["locker"]["compartments"]["a1"] == "loaded"
    assert my_pickup(client, reservation_id)["step"] == "code_not_open"

    advance(client, 30)
    code = code_for(client, reservation_id)
    assert len(code) == 6
    unlocked = unlock(client, reservation_id, code)
    assert unlocked.status_code == 200
    assert unlocked.json()["step"] == "confirm_pickup"
    assert state(store)["locker"]["compartments"]["a1"] == "unlocked"
    # Unlocking alone must not start the loan.
    assert f"loan-{reservation_id}" not in state(store)["loans"]

    picked_up = pick_up(client, reservation_id)
    assert picked_up.status_code == 200
    loan = picked_up.json()
    assert loan["id"] == f"loan-{reservation_id}"
    assert loan["status"] == "active"
    assert loan["asset_id"] == "projector-b"
    assert loan["picked_up_at"] == "2026-11-07T10:30:00+08:00"
    assert loan["due_at"] == "2026-11-07T11:30:00+08:00"
    assert state(store)["locker"]["compartments"]["a1"] == "empty"
    assert my_pickup(client, reservation_id)["step"] == "collected"
    assert "code" not in my_pickup(client, reservation_id)
    assert actions(store) == ["loaded", "unlocked", "picked_up"]


@pytest.mark.parametrize("auth", [BORROWER_A, BORROWER_B, OPERATOR])
def test_only_staff_can_load(booking_app, auth):
    client, store = booking_app
    reservation_id = book(client)
    assert load(client, reservation_id, auth).status_code == 403
    assert "pickup_access" not in state(store)


def test_staff_and_operator_cannot_use_borrower_actions(booking_app):
    client, _ = booking_app
    reservation_id, code = loaded_and_open(client)
    for auth in (STAFF, OPERATOR):
        assert client.get("/pickups", auth=auth).status_code == 403
        assert unlock(client, reservation_id, code, auth).status_code == 403
        assert pick_up(client, reservation_id, auth).status_code == 403


def test_cannot_load_a_unit_still_on_loan(booking_app):
    client, _ = booking_app
    # The seeded booking is for Projector A, which the seeded loan still holds.
    response = load(client, "next-projector")
    assert response.status_code == 409
    assert "on loan" in response.json()["detail"]


def test_cannot_load_a_unit_on_hold(booking_app):
    client, store = booking_app
    reservation_id = book(client)

    def hold(saved):
        saved["assets"]["projector-b"]["condition"] = "hold"

    store.change(hold)
    assert load(client, reservation_id).status_code == 409


def test_cannot_load_unknown_or_closed_window(booking_app):
    client, _ = booking_app
    assert load(client, "missing").status_code == 404
    reservation_id = book(client)
    advance(client, 61)
    assert load(client, reservation_id).status_code == 409


def test_cannot_load_a_later_booking_before_an_earlier_one(booking_app):
    client, _ = booking_app
    earlier = book(client, category=KIT, pickup="2026-11-07T10:30", minutes=30)
    later = book(client, auth=BORROWER_B, category=KIT, pickup="2026-11-07T11:00", minutes=30)

    response = load(client, later)
    assert response.status_code == 409
    assert "earlier booking" in response.json()["detail"]

    # Once the earlier window closes, the later booking is no longer blocked by it.
    advance(client, 61)
    assert load(client, earlier).status_code == 409
    assert load(client, later).status_code == 200


def test_cannot_load_a_unit_already_in_a_compartment(booking_app):
    client, store = booking_app
    first = book(client, category=KIT, pickup="2026-11-07T10:30", minutes=30)
    assert load(client, first).status_code == 200
    later = book(client, auth=BORROWER_B, category=KIT, pickup="2026-11-07T11:00", minutes=30)
    response = load(client, later)
    assert response.status_code == 409
    assert "already in a compartment" in response.json()["detail"]
    assert state(store)["locker"]["compartments"] == {"a1": "loaded", "a2": "empty"}


def test_rejects_loading_when_both_compartments_are_full(booking_app):
    client, store = booking_app
    assert load(client, book(client)).status_code == 200
    assert load(client, book(client, category="raspberry_pi_kit")).status_code == 200
    assert state(store)["locker"]["compartments"] == {"a1": "loaded", "a2": "loaded"}

    def add_third_unit(saved):
        saved["assets"]["projector-c"] = {"category": "projector", "condition": "good"}

    store.change(add_third_unit)
    response = load(client, book(client, auth=BORROWER_B))
    assert response.status_code == 409
    assert "full" in response.json()["detail"]


def test_repeated_loading_keeps_one_code_and_one_compartment(booking_app):
    client, store = booking_app
    reservation_id = book(client)
    first = load(client, reservation_id)
    code = state(store)["pickup_access"][reservation_id]["code"]
    second = load(client, reservation_id)
    assert second.status_code == 200
    assert second.json() == first.json()
    assert state(store)["pickup_access"][reservation_id]["code"] == code
    assert state(store)["locker"]["compartments"] == {"a1": "loaded", "a2": "empty"}
    assert actions(store) == ["loaded"]


def test_wrong_user_code_is_rejected_and_cannot_block_the_owner(booking_app):
    client, store = booking_app
    reservation_id, code = loaded_and_open(client)
    for _ in range(6):
        assert unlock(client, reservation_id, code, BORROWER_B).status_code == 404
    assert state(store)["pickup_access"][reservation_id]["failed_tries"] == 0
    assert actions(store).count("code_wrong_user") == 6
    assert unlock(client, reservation_id, code).status_code == 200


def test_other_borrowers_cannot_see_a_pickup_or_its_code(booking_app):
    client, _ = booking_app
    reservation_id, _ = loaded_and_open(client)
    pickups = client.get("/pickups", auth=BORROWER_B).json()
    assert reservation_id not in {pickup["id"] for pickup in pickups}


def test_code_is_rejected_before_loading_and_before_pickup_time(booking_app):
    client, store = booking_app
    reservation_id = book(client)
    assert unlock(client, reservation_id, "123456").status_code == 409
    assert load(client, reservation_id).status_code == 200
    code = code_for(client, reservation_id)
    response = unlock(client, reservation_id, code)
    assert response.status_code == 409
    assert "until the pickup time" in response.json()["detail"]
    assert state(store)["pickup_access"][reservation_id]["used_at"] is None


def test_code_works_until_thirty_minutes_after_pickup_then_expires(booking_app):
    client, _ = booking_app
    reservation_id = book(client)
    assert load(client, reservation_id).status_code == 200
    code = code_for(client, reservation_id)
    advance(client, 61)  # one minute past the 10:30 + 30 minute window

    response = unlock(client, reservation_id, code)
    assert response.status_code == 409
    assert "expired" in response.json()["detail"]
    pickup = my_pickup(client, reservation_id)
    assert pickup["step"] == "code_expired"
    assert "code" not in pickup


def test_code_still_works_at_the_exact_closing_time(booking_app):
    client, _ = booking_app
    reservation_id = book(client)
    assert load(client, reservation_id).status_code == 200
    code = code_for(client, reservation_id)
    advance(client, 60)
    assert unlock(client, reservation_id, code).status_code == 200


def test_used_code_cannot_be_replayed(booking_app):
    client, store = booking_app
    reservation_id, code = loaded_and_open(client)
    assert unlock(client, reservation_id, code).status_code == 200
    replay = unlock(client, reservation_id, code)
    assert replay.status_code == 409
    assert "already been used" in replay.json()["detail"]
    assert actions(store).count("unlocked") == 1
    assert state(store)["pickup_access"][reservation_id]["failed_tries"] == 0


def test_five_wrong_tries_block_the_code_and_the_count_is_saved(booking_app):
    client, store = booking_app
    reservation_id, code = loaded_and_open(client)
    wrong = wrong_code_for(code)
    for tries in range(1, 6):
        assert unlock(client, reservation_id, wrong).status_code == 403
        # Each rejected try must survive the transaction.
        assert state(store)["pickup_access"][reservation_id]["failed_tries"] == tries
    assert actions(store).count("code_wrong") == 5

    blocked = unlock(client, reservation_id, code)
    assert blocked.status_code == 409
    assert "blocked" in blocked.json()["detail"]
    assert state(store)["pickup_access"][reservation_id]["failed_tries"] == 5
    pickup = my_pickup(client, reservation_id)
    assert pickup["step"] == "code_blocked"
    assert "code" not in pickup


def test_four_wrong_tries_still_let_the_right_code_work(booking_app):
    client, _ = booking_app
    reservation_id, code = loaded_and_open(client)
    for _ in range(4):
        assert unlock(client, reservation_id, wrong_code_for(code)).status_code == 403
    assert unlock(client, reservation_id, code).status_code == 200


def test_pickup_needs_the_owner_and_an_unlocked_compartment(booking_app):
    client, store = booking_app
    reservation_id, code = loaded_and_open(client)
    assert pick_up(client, reservation_id).status_code == 409
    assert unlock(client, reservation_id, code).status_code == 200
    assert pick_up(client, reservation_id, BORROWER_B).status_code == 404
    assert pick_up(client, "missing").status_code == 404
    assert f"loan-{reservation_id}" not in state(store)["loans"]


def test_pickup_is_rejected_at_the_return_time(booking_app):
    client, store = booking_app
    reservation_id, code = loaded_and_open(client)
    assert unlock(client, reservation_id, code).status_code == 200
    advance(client, 60)  # now equal to the 11:30 due time
    response = pick_up(client, reservation_id)
    assert response.status_code == 409
    assert f"loan-{reservation_id}" not in state(store)["loans"]


def test_repeated_pickup_returns_the_same_loan(booking_app):
    client, store = booking_app
    reservation_id, code = loaded_and_open(client)
    assert unlock(client, reservation_id, code).status_code == 200
    first = pick_up(client, reservation_id)
    advance(client, 5)
    second = pick_up(client, reservation_id)
    assert second.status_code == 200
    assert second.json() == first.json()
    assert len(state(store)["loans"]) == 2  # the seeded loan and this one
    assert actions(store).count("picked_up") == 1


def test_code_stays_out_of_reservations_and_staff_data(booking_app):
    client, _ = booking_app
    reservation_id, code = loaded_and_open(client)
    assert code not in client.get("/reservations", auth=BORROWER_A).text
    assert code not in load(client, reservation_id).text
    assert code not in unlock(client, reservation_id, wrong_code_for(code)).text


def test_unit_stays_unavailable_for_overlapping_windows_at_every_step(booking_app):
    client, _ = booking_app

    def can_book_overlap():
        offer = client.post(
            "/reservation-offers",
            auth=BORROWER_B,
            json={"category": KIT, "pickup_at": "2026-11-07T11:00", "duration_minutes": 15},
        )
        return offer.status_code == 201

    assert can_book_overlap()
    reservation_id = book(client, category=KIT)
    assert not can_book_overlap()
    assert load(client, reservation_id).status_code == 200
    assert not can_book_overlap()
    advance(client, 30)
    assert unlock(client, reservation_id, code_for(client, reservation_id)).status_code == 200
    assert not can_book_overlap()
    assert pick_up(client, reservation_id).status_code == 200
    assert not can_book_overlap()


def test_loaded_unit_cannot_be_booked_for_an_earlier_window(booking_app):
    client, _ = booking_app
    window = {"category": KIT, "pickup_at": "2026-11-07T10:15", "duration_minutes": 15}
    before_loading = client.post("/reservation-offers", auth=BORROWER_B, json=window)
    assert before_loading.status_code == 201

    reservation_id = book(client, category=KIT, pickup="2026-11-07T11:00", minutes=30)
    assert load(client, reservation_id).status_code == 200
    # This window ends before the loaded booking starts, but the unit is in a compartment.
    after_loading = client.post("/reservation-offers", auth=BORROWER_B, json=window)
    assert after_loading.status_code == 409


def test_new_loan_counts_as_open_for_later_loading(booking_app):
    client, store = booking_app
    reservation_id = book(client, category=KIT)
    assert load(client, reservation_id).status_code == 200
    advance(client, 30)
    code = code_for(client, reservation_id)
    later = book(client, auth=BORROWER_B, category=KIT, pickup="2026-11-07T11:30", minutes=30)
    assert unlock(client, reservation_id, code).status_code == 200
    assert pick_up(client, reservation_id).status_code == 200

    response = load(client, later)
    assert response.status_code == 409
    assert "on loan" in response.json()["detail"]

    def close_loan(saved):
        saved["loans"][f"loan-{reservation_id}"]["status"] = "returned"

    store.change(close_loan)
    assert load(client, later).status_code == 200


def test_reset_clears_pickup_records(booking_app):
    client, store = booking_app
    loaded_and_open(client)
    response = client.post("/local-test/reset", auth=OPERATOR, json={"scenario": "spare_available"})
    assert response.status_code == 204
    saved = state(store)
    assert "pickup_access" not in saved
    assert "audit_events" not in saved
    assert saved["locker"]["compartments"] == {"a1": "empty", "a2": "empty"}


def test_locker_page_shows_staff_their_actions_without_any_code(booking_app):
    client, _ = booking_app
    reservation_id = book(client)
    page = client.get("/locker", auth=STAFF)
    assert page.status_code == 200
    assert "Confirm loading" in page.text
    assert f"/reservations/{reservation_id}/load" in page.text
    # The seeded booking can't load yet, and the page says why instead of offering the button.
    assert "/reservations/next-projector/load" not in page.text
    assert "This unit is still on loan." in page.text

    assert load(client, reservation_id).status_code == 200
    advance(client, 30)
    code = code_for(client, reservation_id)
    page = client.get("/locker", auth=STAFF).text
    assert code not in page
    assert "Loaded, waiting for borrower" in page
    assert "Equipment Staff confirmed loading" in page


def test_locker_page_shows_only_the_owner_their_code(booking_app):
    client, _ = booking_app
    reservation_id, code = loaded_and_open(client)
    owner = client.get("/locker", auth=BORROWER_A)
    assert owner.status_code == 200
    assert code in owner.text
    assert "Simulated delivery" in owner.text
    assert f"/reservations/{reservation_id}/unlock" in owner.text
    assert reservation_id not in client.get("/locker", auth=BORROWER_B).text

    assert unlock(client, reservation_id, code).status_code == 200
    opened = client.get("/locker", auth=BORROWER_A).text
    assert code not in opened
    assert "Confirm pickup" in opened


def test_locker_page_needs_a_staff_or_borrower_sign_in(booking_app):
    client, _ = booking_app
    assert client.get("/locker").status_code == 401
    assert client.get("/locker", auth=OPERATOR).status_code == 403
    assert client.get("/static/locker.css").status_code == 200
    assert client.get("/static/locker.js").status_code == 200


def test_chat_tool_shows_status_without_the_code(booking_app):
    client, store = booking_app
    reservation_id, code = loaded_and_open(client)
    agent = create_reservation_agent(Reservations(store), BORROWER_A_ID, model="none")
    tool = next(tool for tool in agent.tools if tool.__name__ == "check_pickup_status")

    result = tool()

    pickup = next(item for item in result["pickups"] if item["id"] == reservation_id)
    assert pickup["step"] == "enter_code"
    assert pickup["compartment"] == "a1"
    assert code not in str(result)
    assert "code" not in pickup
