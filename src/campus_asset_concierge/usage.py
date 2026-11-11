"""Stage 2.4 equipment use report: what each unit is doing now and how much it has been lent."""

from datetime import datetime

from campus_asset_concierge.domain.reservations import local_clock

# Most urgent loan state wins when describing a unit.
LOAN_STATUS_LABELS = {"overdue": "Overdue", "awaiting_check": "Awaiting return check", "active": "On loan"}
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
    loans = {loan_id: loan for loan_id, loan in state["loans"].items() if loan["asset_id"] == asset_id}
    statuses = {loan["status"] for loan in loans.values()}
    status = next((label for key, label in LOAN_STATUS_LABELS.items() if key in statuses), None)
    if status is None and any(
        access["asset_id"] == asset_id and access["collected_at"] is None
        for access in state.get("pickup_access", {}).values()
    ):
        status = "Loaded in locker"
    if status is None:
        status = "Available" if asset["condition"] == "good" else "On hold after failed check"
    return {
        "asset_id": asset_id,
        "category": asset["category"],
        "status": status,
        "busy": status not in {"Available", "On hold after failed check"},
        "loans": len(loans),
        "loan_minutes": sum(_loan_minutes(state, loan_id, loan, now) for loan_id, loan in loans.items()),
        "upcoming": sum(
            reservation["asset_id"] == asset_id and reservation["status"] in UPCOMING
            and reservation["due_at"] > now
            for reservation in state["reservations"].values()
        ),
    }


def _loan_minutes(state: dict, loan_id: str, loan: dict, now: datetime) -> int:
    # A loan ends when the borrower drops the item off; otherwise it is still running.
    access = state.get("return_access", {}).get(loan["asset_id"])
    if access and access["loan_id"] == loan_id and access["dropped_at"]:
        ended = access["dropped_at"]
    elif loan["status"] in {"returned", "awaiting_check"}:
        # shortcut: return_access keeps only the latest return per unit, so older loans count to due time.
        ended = min(loan["due_at"], now)
    else:
        ended = now
    return max(0, int((ended - loan["picked_up_at"]).total_seconds() // 60))
