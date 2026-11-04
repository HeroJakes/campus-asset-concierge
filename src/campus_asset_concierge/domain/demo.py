from datetime import UTC, datetime, timedelta
from enum import StrEnum

BORROWER_A = "borrower-a"
BORROWER_B = "borrower-b"


class DemoScenario(StrEnum):
    SPARE_AVAILABLE = "spare_available"
    SPARE_UNAVAILABLE = "spare_unavailable"


def starting_state(scenario: DemoScenario) -> dict:
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
    if scenario == DemoScenario.SPARE_UNAVAILABLE:
        reservations["spare-projector"] = {
            **reservations["next-projector"],
            "borrower_id": BORROWER_A,
            "asset_id": "projector-b",
        }

    return {
        "scenario": scenario.value,
        "starts_at": start,
        "elapsed_minutes": 0,
        "location": {"id": "campus-loan-desk", "name": "Campus Loan Desk"},
        "locker": {
            "id": "locker-a",
            "compartments": {"a1": "empty", "a2": "empty"},
        },
        "assets": {
            "projector-a": {"category": "projector", "condition": "good"},
            "projector-b": {"category": "projector", "condition": "good"},
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
