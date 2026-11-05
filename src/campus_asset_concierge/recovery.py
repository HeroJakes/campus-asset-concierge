from datetime import datetime

from campus_asset_concierge.domain.reservations import (
    MALAYSIA_TIME,
    ReservationError,
    eligible_unit,
    local_clock,
)
from campus_asset_concierge.storage.local_state import LocalStateStore


RECOVERY_ACTOR = "overdue-recovery"
STAFF_OWNER = "equipment-staff"


class Recovery:
    """Detect overdue loans and record the P0 recovery outcome."""

    def __init__(self, store: LocalStateStore) -> None:
        self.store = store

    def process(self) -> dict:
        """Run an idempotent recovery pass against the current local clock."""

        def recover(state: dict | None) -> dict:
            if state is None:
                raise ReservationError(409, "Load a local test scenario first.")

            now = local_clock(state)
            state.setdefault("reminders", {})
            state.setdefault("at_risk_reservations", {})
            state.setdefault("substitution_proposals", {})
            state.setdefault("escalations", {})

            for loan_id, loan in state["loans"].items():
                if loan["status"] == "active" and loan["due_at"] < now:
                    loan["status"] = "overdue"
                    next_booking = _next_booking(state, loan["asset_id"], now)
                    reservation_id = next_booking[0] if next_booking else loan_id
                    _audit(state, now, "overdue_marked", reservation_id, loan["asset_id"], loan_id=loan_id)

                if loan["status"] != "overdue":
                    continue

                next_booking = _next_booking(state, loan["asset_id"], now)
                if next_booking is None:
                    continue

                reservation_id, reservation = next_booking
                _queue_reminder(state, now, loan_id, reservation_id)
                _flag_at_risk(state, now, loan_id, reservation_id, reservation)
                if reservation_id in state["substitution_proposals"] or reservation_id in state["escalations"]:
                    continue
                _record_outcome(state, now, loan_id, reservation_id, reservation)

            return _result(state, now)

        return self.store.change(recover)

    def staff_page(self) -> dict:
        state = self.store.load()
        if state is None:
            raise ReservationError(409, "Load a local test scenario first.")
        now = local_clock(state)
        return _result(state, now)


def _next_booking(state: dict, asset_id: str, now: datetime) -> tuple[str, dict] | None:
    # shortcut: only the next booking whose pickup is still ahead; a clock jump past that pickup
    # skips it. Fine for the demo's 61-minute advance, revisit if advances cross a booking window.
    bookings = [
        (reservation_id, reservation)
        for reservation_id, reservation in state["reservations"].items()
        if reservation["asset_id"] == asset_id
        and reservation["status"] == "confirmed"
        and reservation["pickup_at"] >= now
    ]
    return min(bookings, key=lambda item: item[1]["pickup_at"]) if bookings else None


def _queue_reminder(state: dict, now: datetime, loan_id: str, reservation_id: str) -> None:
    reminder_id = f"overdue-{loan_id}"
    if reminder_id in state["reminders"]:
        return
    state["reminders"][reminder_id] = {
        "id": reminder_id,
        "loan_id": loan_id,
        "reservation_id": reservation_id,
        "status": "queued",
        "simulated": True,
        "queued_at": now,
    }
    _audit(state, now, "reminder_queued", reservation_id, state["loans"][loan_id]["asset_id"], loan_id=loan_id)


def _flag_at_risk(
    state: dict, now: datetime, loan_id: str, reservation_id: str, reservation: dict
) -> None:
    if reservation_id in state["at_risk_reservations"]:
        return
    state["at_risk_reservations"][reservation_id] = {
        "id": reservation_id,
        "reservation_id": reservation_id,
        "loan_id": loan_id,
        "asset_id": reservation["asset_id"],
        "status": reservation["status"],
        "flagged_at": now,
    }
    _audit(state, now, "booking_at_risk", reservation_id, reservation["asset_id"], loan_id=loan_id)


def _record_outcome(
    state: dict, now: datetime, loan_id: str, reservation_id: str, reservation: dict
) -> None:
    category = state["assets"][reservation["asset_id"]]["category"]
    # shortcut: does not skip a spare already proposed to another overdue loan this pass; safe for
    # <=2 units per category, revisit before a category has 3+ units (overlaps Stage 2.1).
    for asset_id in sorted(state["assets"]):
        if asset_id == reservation["asset_id"]:
            continue
        if eligible_unit(
            state,
            asset_id,
            category,
            reservation["pickup_at"],
            reservation["due_at"],
            now,
        ):
            proposal_id = f"proposal-{reservation_id}"
            state["substitution_proposals"][reservation_id] = {
                "id": proposal_id,
                "reservation_id": reservation_id,
                "loan_id": loan_id,
                "original_asset_id": reservation["asset_id"],
                "substitute_asset_id": asset_id,
                "status": "pending_staff_approval",
                "verified": True,
                "verified_at": now,
            }
            _audit(state, now, "substitute_proposed", reservation_id, reservation["asset_id"], loan_id=loan_id)
            return

    escalation_id = f"escalation-{reservation_id}"
    state["escalations"][reservation_id] = {
        "id": escalation_id,
        "reservation_id": reservation_id,
        "loan_id": loan_id,
        "asset_id": reservation["asset_id"],
        "status": "open",
        "owner": STAFF_OWNER,
        "owner_role": "staff",
        "reason": "No eligible substitute is available for the at-risk booking.",
        "created_at": now,
    }
    _audit(state, now, "escalation_created", reservation_id, reservation["asset_id"], loan_id=loan_id)


def _result(state: dict, now: datetime) -> dict:
    return {
        "current_time": now.astimezone(MALAYSIA_TIME).isoformat(),
        "overdue_loans": [
            {"id": loan_id, **_times(loan, "picked_up_at", "due_at")}
            for loan_id, loan in state["loans"].items()
            if loan["status"] == "overdue"
        ],
        "reminders": [_times(record, "queued_at") for record in state.get("reminders", {}).values()],
        "at_risk_reservations": [
            _times(record, "flagged_at")
            for record in state.get("at_risk_reservations", {}).values()
        ],
        "substitution_proposals": [
            _times(record, "verified_at", "applied_at")
            for record in state.get("substitution_proposals", {}).values()
        ],
        "escalations": [
            _times(record, "created_at") for record in state.get("escalations", {}).values()
        ],
        "audit_events": [_times(event, "at") for event in reversed(state.get("audit_events", []))],
    }


def _times(record: dict, *fields: str) -> dict:
    result = dict(record)
    for field in fields:
        value = result.get(field)
        if isinstance(value, datetime):
            result[field] = value.astimezone(MALAYSIA_TIME).isoformat()
    return result


def _audit(
    state: dict, now: datetime, action: str, reservation_id: str, asset_id: str, *, loan_id: str
) -> None:
    # asset_id keeps the shared audit shape from stages 1.2/1.3; loan_id is extra recovery context.
    state.setdefault("audit_events", []).append(
        {
            "at": now,
            "actor": RECOVERY_ACTOR,
            "action": action,
            "asset_id": asset_id,
            "reservation_id": reservation_id,
            "loan_id": loan_id,
        }
    )
