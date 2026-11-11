from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

from conftest import STAFF
from test_pickups import advance, book, code_for, load, pick_up, unlock
from test_returns import code_for as return_code_for
from test_returns import return_drop, return_request, return_unlock, verify

from campus_asset_concierge.domain import scenarios
from campus_asset_concierge.usage import equipment_usage


def units(report):
    return {unit["asset_id"]: unit for unit in report["units"]}


def test_usage_reports_each_unit_from_the_seeded_state():
    report = equipment_usage(scenarios.starting_state(scenarios.TestScenario.SPARE_AVAILABLE))

    by_id = units(report)
    assert (by_id["projector-a"]["status"], by_id["projector-a"]["loan_minutes"]) == ("On loan", 60)
    assert by_id["projector-a"]["upcoming"] == 1
    assert by_id["projector-b"]["status"] == "Available"
    assert by_id["projector-b"]["loans"] == 0
    assert (report["in_use"], report["total_loans"], report["loan_minutes"]) == (1, 1, 60)


def test_usage_marks_overdue_loans_and_held_units():
    state = scenarios.starting_state(scenarios.TestScenario.SPARE_AVAILABLE)
    state["elapsed_minutes"] = 90
    # Recovery has not run, but the loan is already past due.
    state["assets"]["projector-b"]["condition"] = "hold"

    by_id = units(equipment_usage(state))

    assert by_id["projector-a"]["status"] == "Overdue"
    assert by_id["projector-a"]["loan_minutes"] == 150
    assert by_id["projector-b"]["status"] == "On hold after failed check"
    assert by_id["projector-b"]["busy"] is False


def test_upcoming_counts_only_bookings_that_can_still_be_collected():
    state = scenarios.starting_state(scenarios.TestScenario.SPARE_AVAILABLE)
    state["elapsed_minutes"] = 150  # next-projector pickup 12:00, code window closes 12:30
    assert units(equipment_usage(state))["projector-a"]["upcoming"] == 1
    state["elapsed_minutes"] = 151
    assert units(equipment_usage(state))["projector-a"]["upcoming"] == 0


def test_returned_loan_without_its_return_record_counts_until_due_time():
    state = scenarios.starting_state(scenarios.TestScenario.SPARE_AVAILABLE)
    loan = state["loans"]["active-projector"]
    loan["status"] = "returned"
    state["elapsed_minutes"] = 600

    unit = units(equipment_usage(state))["projector-a"]

    assert unit["loan_minutes"] == (loan["due_at"] - loan["picked_up_at"]) // timedelta(minutes=1)
    assert unit["status"] == "Available"


def test_staff_dashboard_shows_usage_through_loading_pickup_and_return(booking_app):
    client, _ = booking_app
    reservation_id = book(client)
    assert load(client, reservation_id).status_code == 200
    assert "Loaded in locker" in client.get("/locker", auth=STAFF).text

    advance(client, 30)
    assert unlock(client, reservation_id, code_for(client, reservation_id)).status_code == 200
    assert pick_up(client, reservation_id).status_code == 200
    advance(client, 15)
    assert return_request(client, "projector-b").status_code == 200
    assert return_unlock(client, "projector-b", return_code_for(client, "projector-b")).status_code == 200
    assert return_drop(client, "projector-b").status_code == 200
    advance(client, 20)
    html = client.get("/locker", auth=STAFF).text
    assert "Equipment use" in html
    assert "Awaiting return check" in html
    # Loan time stops at drop-off, not when staff check the item.
    assert "0 h 15 min" in html

    assert verify(client, "projector-b").status_code == 200
    assert "0 h 15 min" in client.get("/locker", auth=STAFF).text


def test_recovery_records_its_last_run_for_staff(booking_app):
    client, store = booking_app
    assert "Recovery check has not run yet" in client.get("/locker", auth=STAFF).text

    store.advance(61)
    first = client.post("/recovery/run", auth=STAFF).json()["last_run"]
    assert first["new_events"] == 4
    assert first["clock_at"].startswith("2026-11-07T11:01")

    second = client.post("/recovery/run", auth=STAFF).json()["last_run"]
    assert second["new_events"] == 0
    assert second["ran_at"] >= first["ran_at"]
    assert "0 new activity events" in client.get("/locker", auth=STAFF).text


def test_two_recovery_runs_at_once_record_one_outcome(booking_app):
    # The daily scheduler and a staff click can overlap.
    client, store = booking_app
    store.advance(61)
    start = Barrier(2)

    def run():
        start.wait(timeout=5)
        return client.post("/recovery/run", auth=STAFF)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = [pool.submit(run) for _ in range(2)]
        changes = sorted(outcome.result(timeout=20).json()["last_run"]["new_events"] for outcome in outcomes)

    assert changes == [0, 4]
    saved = store.load()
    assert len(saved["substitution_proposals"]) == 1
    assert len(saved["audit_events"]) == 4
