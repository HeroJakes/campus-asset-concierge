from datetime import UTC, datetime, timedelta
from enum import StrEnum

BORROWER_A = "borrower-a"
BORROWER_B = "borrower-b"


class TestScenario(StrEnum):
    SPARE_AVAILABLE = "spare_available"
    SPARE_UNAVAILABLE = "spare_unavailable"
    # spare_available plus a morning of fictional history, so every staff panel has content.
    PRESENTATION = "presentation"


def starting_state(scenario: TestScenario) -> dict:
    # 10:00 in Kuala Lumpur. Firestore stores timestamps in UTC.
    start = datetime(2026, 11, 7, 2, tzinfo=UTC)
    due = start + timedelta(hours=1)
    next_pickup = start + timedelta(hours=2)
    next_due = start + timedelta(hours=3)
    reservations = {
        "next-projector": {
            "borrower_id": BORROWER_B,
            "asset_id": "projector-a",
            "status": "confirmed",
            "pickup_at": next_pickup,
            "due_at": next_due,
        }
    }
    if scenario == TestScenario.SPARE_UNAVAILABLE:
        reservations["spare-projector"] = {
            **reservations["next-projector"],
            "borrower_id": BORROWER_A,
            "asset_id": "projector-b",
        }

    state = {
        "scenario": scenario.value,
        "starts_at": start,
        "elapsed_minutes": 0,
        "location": {"id": "campus-loan-desk", "name": "Campus Loan Desk"},
        "locker": {
            "id": "locker-a",
            "compartments": {f"a{number}": "empty" for number in range(1, 7)},
        },
        "assets": {
            "projector-a": {
                "category": "projector", "condition": "good",
                "has_hdmi": True, "has_built_in_speakers": True,
            },
            "projector-b": {
                "category": "projector", "condition": "good",
                "has_hdmi": True, "has_built_in_speakers": False,
            },
            "raspberry-pi-kit": {"category": "raspberry_pi_kit", "condition": "good"},
        },
        "reservations": reservations,
        "loans": {
            "active-projector": {
                "borrower_id": BORROWER_A,
                "asset_id": "projector-a",
                "status": "active",
                "picked_up_at": start - timedelta(hours=1),
                "due_at": due,
            }
        },
    }
    if scenario == TestScenario.PRESENTATION:
        _add_presentation_history(state)
    return state


STAFF = "equipment-staff"


def _add_presentation_history(state: dict) -> None:
    """Add records shaped exactly like the ones the lending actions write.

    Projector B, the recovery spare, gets no future booking, so the substitute story still works.
    """
    def at(hour: int, minute: int = 0) -> datetime:
        return state["starts_at"] + timedelta(hours=hour - 10, minutes=minute)  # starts_at is 10:00 MYT

    state["assets"] |= {
        "projector-c": {
            "category": "projector", "condition": "good",
            "has_hdmi": True, "has_built_in_speakers": True,
        },
        "raspberry-pi-kit-b": {"category": "raspberry_pi_kit", "condition": "good"},
        "raspberry-pi-kit-c": {"category": "raspberry_pi_kit", "condition": "good"},
    }
    # (reservation, borrower, asset, pickup, due, status)
    bookings = [
        ("morning-lecture", BORROWER_A, "projector-b", at(7, 30), at(8, 45), "collected"),
        ("morning-kit", BORROWER_B, "raspberry-pi-kit-b", at(8), at(9, 30), "collected"),
        ("early-projector", BORROWER_B, "projector-c", at(8, 30), at(10, 30), "collected"),
        ("afternoon-kit", BORROWER_B, "raspberry-pi-kit-c", at(11, 30), at(13, 30), "ready_for_pickup"),
        ("lab-kit", BORROWER_A, "raspberry-pi-kit-b", at(14), at(16), "confirmed"),
    ]
    for reservation_id, borrower_id, asset_id, pickup, due, status in bookings:
        state["reservations"][reservation_id] = {
            "borrower_id": borrower_id, "asset_id": asset_id, "status": status,
            "pickup_at": pickup, "due_at": due,
        }

    # (reservation, compartment, loaded, unlocked/collected, return compartment, requested,
    #  unlocked, dropped, checked)
    loans = [
        ("morning-lecture", "a4", at(7, 20), at(7, 32), "a4", at(8, 35), at(8, 39), at(8, 40), at(8, 55)),
        ("morning-kit", "a5", at(7, 50), at(8, 3), "a6", at(9, 12), at(9, 18), at(9, 20), at(9, 35)),
        ("early-projector", "a6", at(8, 20), at(8, 33), "a2", at(10, 12), at(10, 18), at(10, 20), None),
    ]
    state["pickup_access"], state["return_access"], events = {}, {}, []
    for index, (reservation_id, compartment, loaded, collected, back, requested, unlocked, dropped,
                checked) in enumerate(loans):
        booking = state["reservations"][reservation_id]
        borrower_id, asset_id = booking["borrower_id"], booking["asset_id"]
        state["pickup_access"][reservation_id] = {
            "code": f"{index + 1}{index + 1}0{index + 3}2{index + 5}", "compartment": compartment,
            "asset_id": asset_id, "due_at": booking["due_at"], "failed_tries": 0,
            "used_at": collected - timedelta(minutes=1), "collected_at": collected,
        }
        state["loans"][f"loan-{reservation_id}"] = {
            "borrower_id": borrower_id, "asset_id": asset_id,
            "status": "returned" if checked else "awaiting_check",
            "picked_up_at": collected, "due_at": booking["due_at"], "dropped_at": dropped,
        }
        state["return_access"][asset_id] = {
            "loan_id": f"loan-{reservation_id}", "borrower_id": borrower_id,
            "code": f"7{index + 2}{index + 4}91{index}", "compartment": back, "issued_at": requested,
            "failed_tries": 0, "used_at": unlocked, "dropped_at": dropped,
            "checked_at": checked, "result": "pass" if checked else None,
        }
        events += [
            (loaded, STAFF, "loaded", reservation_id, asset_id),
            (collected - timedelta(minutes=1), borrower_id, "unlocked", reservation_id, asset_id),
            (collected, borrower_id, "picked_up", reservation_id, asset_id),
            (requested, borrower_id, "return_requested", None, asset_id),
            (unlocked, borrower_id, "return_unlocked", None, asset_id),
            (dropped, borrower_id, "returned_dropped", None, asset_id),
        ]
        if checked:
            events.append((checked, STAFF, "return_passed", None, asset_id))

    state["pickup_access"]["afternoon-kit"] = {
        "code": "640318", "compartment": "a1", "asset_id": "raspberry-pi-kit-c",
        "due_at": at(13, 30), "failed_tries": 0, "used_at": None, "collected_at": None,
    }
    events.append((at(10, 45), STAFF, "loaded", "afternoon-kit", "raspberry-pi-kit-c"))
    state["locker"]["compartments"] |= {"a1": "loaded", "a2": "returned"}
    state["audit_events"] = [
        {"at": when, "actor": actor, "action": action, "asset_id": asset_id, "reservation_id": reservation_id}
        for when, actor, action, reservation_id, asset_id in sorted(events, key=lambda event: event[0])
    ]
