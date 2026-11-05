from datetime import datetime

from campus_asset_concierge.domain.reservations import (
    MALAYSIA_TIME,
    ReservationError,
    eligible_unit,
    local_clock,
    malaysia_times,
)
from campus_asset_concierge.storage.local_state import LocalStateStore


class Reassignment:
    """Approve and apply one verified substitution proposal."""

    def __init__(self, store: LocalStateStore) -> None:
        self.store = store

    def approve(self, staff_id: str, reservation_id: str) -> dict:
        """Recheck and apply a proposal in the same Firestore transaction."""

        def apply(state: dict | None) -> dict:
            if state is None:
                raise ReservationError(409, "Load a local test scenario first.")

            proposal = state.get("substitution_proposals", {}).get(reservation_id)
            if proposal is None:
                raise ReservationError(404, "Substitution proposal not found.")

            reservation = state.get("reservations", {}).get(reservation_id)
            if reservation is None:
                raise ReservationError(409, "The reservation for this proposal no longer exists.")

            if proposal["status"] == "applied":
                return _approval_result(state, reservation_id, reservation, proposal)
            if proposal["status"] != "pending_staff_approval":
                raise ReservationError(409, "This substitution proposal is no longer pending.")

            original_asset_id = proposal["original_asset_id"]
            substitute_asset_id = proposal["substitute_asset_id"]
            if (
                reservation["status"] != "confirmed"
                or reservation["asset_id"] != original_asset_id
                or original_asset_id == substitute_asset_id
            ):
                raise ReservationError(409, "This substitution proposal is no longer applicable.")

            original_asset = state.get("assets", {}).get(original_asset_id)
            if original_asset is None:
                raise ReservationError(409, "The original asset for this proposal no longer exists.")

            now = local_clock(state)
            if not eligible_unit(
                state,
                substitute_asset_id,
                original_asset["category"],
                reservation["pickup_at"],
                reservation["due_at"],
                now,
            ):
                raise ReservationError(409, "The proposed substitute is no longer eligible.")

            reservation["asset_id"] = substitute_asset_id
            proposal.update(
                {
                    "status": "applied",
                    "approved_by": staff_id,
                    "applied_at": now,
                }
            )
            # The booking is resolved onto the substitute, so it is no longer at risk.
            state.get("at_risk_reservations", {}).pop(reservation_id, None)
            event = _audit(
                state,
                now,
                staff_id,
                reservation_id,
                original_asset_id,
                substitute_asset_id,
            )
            return _approval_result(state, reservation_id, reservation, proposal, event)

        return self.store.change(apply)


def _approval_result(
    state: dict,
    reservation_id: str,
    reservation: dict,
    proposal: dict,
    event: dict | None = None,
) -> dict:
    if event is None:
        event = next(
            (
                item
                for item in reversed(state.get("audit_events", []))
                if item["action"] == "substitution_applied"
                and item["reservation_id"] == reservation_id
            ),
            None,
        )
    return {
        "proposal": _times(proposal, "verified_at", "applied_at"),
        "reservation": {"id": reservation_id, **malaysia_times(reservation)},
        "audit_event": _times(event, "at") if event else None,
    }


def _audit(
    state: dict,
    now: datetime,
    staff_id: str,
    reservation_id: str,
    original_asset_id: str,
    substitute_asset_id: str,
) -> dict:
    event = {
        "at": now,
        "actor": staff_id,
        "action": "substitution_applied",
        "asset_id": substitute_asset_id,
        "reservation_id": reservation_id,
        "original_asset_id": original_asset_id,
        "substitute_asset_id": substitute_asset_id,
    }
    state.setdefault("audit_events", []).append(event)
    return event


def _times(record: dict, *fields: str) -> dict:
    result = dict(record)
    for field in fields:
        value = result.get(field)
        if isinstance(value, datetime):
            result[field] = value.astimezone(MALAYSIA_TIME).isoformat()
    return result
