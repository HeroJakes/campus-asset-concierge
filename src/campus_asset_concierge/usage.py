"""Stage 2.4 equipment use report: what each unit is doing now and how much it has been lent."""

from datetime import datetime

from campus_asset_concierge.domain.reservations import local_clock, uncollected_pickups
from campus_asset_concierge.pickups import CODE_WINDOW

# Most urgent loan state wins when describing a unit.
LOAN_STATUS_LABELS = {"overdue": "Overdue", "awaiting_check": "Awaiting return check", "active": "On loan"}
CLOSED_LOAN = {"returned", "awaiting_check"}
UPCOMING = {"confirmed", "ready_for_pickup"}


def equipment_usage(state: dict) -> dict:
    now = local_clock(state)
    units = [_unit(state, asset_id, asset, now) for asset_id, asset in sorted(state["assets"].items())]
    return {
        "units": units,
        "in_use": sum(unit["busy"] for unit in units),
        "total_loans": sum(unit["loans"] for unit in units),
        "loan_minutes": sum(unit["loan_minutes"] for unit in units),
    }


def _unit(state: dict, asset_id: str, asset: dict, now: datetime) -> dict:
    loans = [loan for loan in state["loans"].values() if loan["asset_id"] == asset_id]
    # Recovery may not have run yet, so a past-due active loan already counts as overdue.
    statuses = {
        "overdue" if loan["status"] == "active" and loan["due_at"] < now else loan["status"]
        for loan in loans
    }
    status = next((label for key, label in LOAN_STATUS_LABELS.items() if key in statuses), None)
    busy = status is not None
    if not busy and uncollected_pickups(state, asset_id):
        status, busy = "Loaded in locker", True
    if not busy:
        status = "Available" if asset["condition"] == "good" else "On hold after failed check"
    return {
        "asset_id": asset_id,
        "category": asset["category"],
        "status": status,
        "busy": busy,
        "loans": len(loans),
        "loan_minutes": sum(_loan_minutes(loan, now) for loan in loans),
        "upcoming": sum(
            reservation["asset_id"] == asset_id and reservation["status"] in UPCOMING
            and now <= reservation["pickup_at"] + CODE_WINDOW
            for reservation in state["reservations"].values()
        ),
    }


def _loan_minutes(loan: dict, now: datetime) -> int:
    # A loan ends when the borrower drops the item off; otherwise it is still running.
    if loan.get("dropped_at"):
        ended = loan["dropped_at"]
    elif loan["status"] in CLOSED_LOAN:
        # shortcut: loans closed before drop times were saved count to due time; fine for demo data.
        ended = min(loan["due_at"], now)
    else:
        ended = now
    return max(0, int((ended - loan["picked_up_at"]).total_seconds() // 60))
