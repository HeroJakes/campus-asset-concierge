from datetime import datetime, timedelta
from secrets import compare_digest, randbelow

from campus_asset_concierge.domain.reservations import (
    equipment_requirements,
    MALAYSIA_TIME,
    ReservationError,
    local_clock,
    malaysia_times,
    uncollected_pickups,
)
from campus_asset_concierge.storage.local_state import LocalStateStore

CODE_WINDOW = timedelta(minutes=30)
MAX_WRONG_TRIES = 5
# Steps where the borrower still needs their code on screen.
CODE_STEPS = {"code_not_open", "enter_code"}


class Pickups:
    def __init__(self, store: LocalStateStore) -> None:
        self.store = store

    def load(self, staff_id: str, reservation_id: str) -> dict:
        # Firestore can rerun a transaction, so choose the code once, outside it.
        code = f"{randbelow(10**6):06d}"

        def confirm_loading(state: dict | None) -> dict:
            state = _required(state)
            reservation = _reservation(state, reservation_id)
            now = local_clock(state)
            access_records = state.setdefault("pickup_access", {})
            if reservation_id not in access_records:
                _check_can_load(state, reservation_id, reservation, now)
                compartment = _first_empty_compartment(state)
                # shortcut: plain text suits fictional local data, replace before real use.
                access_records[reservation_id] = {
                    "code": code,
                    "compartment": compartment,
                    "asset_id": reservation["asset_id"],
                    "due_at": reservation["due_at"],
                    "failed_tries": 0,
                    "used_at": None,
                    "collected_at": None,
                }
                state["locker"]["compartments"][compartment] = "loaded"
                reservation["status"] = "ready_for_pickup"
                _audit(state, now, staff_id, "loaded", reservation_id, reservation["asset_id"])
            return _view(state, reservation_id, reservation, now)

        return self.store.change(confirm_loading)

    def unlock(self, borrower_id: str, reservation_id: str, code: str) -> dict:
        def try_code(state: dict | None) -> dict | ReservationError:
            state = _required(state)
            reservation = _reservation(state, reservation_id)
            now = local_clock(state)
            if reservation["borrower_id"] != borrower_id:
                # Keep this out of the try count so one borrower cannot block another's code.
                _audit(state, now, borrower_id, "code_wrong_user", reservation_id, reservation["asset_id"])
                return ReservationError(404, "Reservation not found.")

            access = state.get("pickup_access", {}).get(reservation_id)
            if access is None:
                raise ReservationError(409, "Staff have not loaded this item yet.")
            if access["used_at"] is not None:
                raise ReservationError(409, "This code has already been used.")
            if access["failed_tries"] >= MAX_WRONG_TRIES:
                raise ReservationError(409, "This code is blocked after too many wrong tries.")
            if now < reservation["pickup_at"]:
                raise ReservationError(409, "This code does not work until the pickup time.")
            if now > _code_closes_at(reservation):
                raise ReservationError(409, "This code has expired.")

            if not compare_digest(access["code"].encode(), code.encode()):
                access["failed_tries"] += 1
                _audit(state, now, borrower_id, "code_wrong", reservation_id, reservation["asset_id"])
                return ReservationError(403, "That code is not correct.")

            access["used_at"] = now
            state["locker"]["compartments"][access["compartment"]] = "unlocked"
            _audit(state, now, borrower_id, "unlocked", reservation_id, reservation["asset_id"])
            return _view(state, reservation_id, reservation, now)

        outcome = self.store.change(try_code)
        # Raising inside the transaction would discard the saved try and audit event.
        if isinstance(outcome, ReservationError):
            raise outcome
        return outcome

    def confirm(self, borrower_id: str, reservation_id: str) -> dict:
        loan_id = f"loan-{reservation_id}"

        def start_loan(state: dict | None) -> dict:
            state = _required(state)
            reservation = _reservation(state, reservation_id)
            if reservation["borrower_id"] != borrower_id:
                raise ReservationError(404, "Reservation not found.")
            existing = state["loans"].get(loan_id)
            if existing is not None:
                return _loan_view(loan_id, existing)

            access = state.get("pickup_access", {}).get(reservation_id)
            if access is None or access["used_at"] is None:
                raise ReservationError(409, "Unlock the compartment with your code first.")
            now = local_clock(state)
            if now >= reservation["due_at"]:
                raise ReservationError(409, "The return time for this booking has passed.")

            loan = {
                "borrower_id": borrower_id,
                "asset_id": reservation["asset_id"],
                "status": "active",
                "picked_up_at": now,
                "due_at": reservation["due_at"],
            }
            state["loans"][loan_id] = loan
            reservation["status"] = "collected"
            access["collected_at"] = now
            state["locker"]["compartments"][access["compartment"]] = "empty"
            _audit(state, now, borrower_id, "picked_up", reservation_id, reservation["asset_id"])
            return _loan_view(loan_id, loan)

        return self.store.change(start_loan)

    def status(self, borrower_id: str) -> list[dict]:
        """Return a borrower's pickups without codes, so chat can safely read them."""
        return _borrower_views(_required(self.store.load()), borrower_id)

    def borrower_page(self, borrower_id: str) -> list[dict]:
        """Add each usable code. Only call this for the signed-in owner."""
        state = _required(self.store.load())
        access_records = state.get("pickup_access", {})
        return [
            pickup | {"code": access_records[pickup["id"]]["code"]}
            if pickup["step"] in CODE_STEPS
            else pickup
            for pickup in _borrower_views(state, borrower_id)
        ]

    def staff_page(self) -> dict:
        state = _required(self.store.load())
        now = local_clock(state)
        reservations = [
            _view(state, reservation_id, reservation, now)
            | {
                "load_blocker": _load_blocker(state, reservation_id, reservation, now),
                "loan_status": state["loans"].get(f"loan-{reservation_id}", {}).get("status"),
            }
            for reservation_id, reservation in _by_pickup_time(state)
        ]
        linked_loans = {f"loan-{reservation_id}" for reservation_id in state["reservations"]}
        # Seeded or imported loans may predate the reservation records.
        for loan_id, loan in sorted(state["loans"].items()):
            if loan_id not in linked_loans:
                reservations.append(_loan_view(loan_id, loan) | {
                    "status": "collected", "step": "collected",
                    "pickup_at": _malaysia_iso(loan["picked_up_at"]),
                    "compartment": None,
                    "loan_status": loan["status"], "load_blocker": None,
                    "pickup_location": state["location"]["name"],
                    **equipment_requirements(loan),
                })
        return {
            "compartments": state["locker"]["compartments"],
            "reservations": sorted(reservations, key=lambda row: row["pickup_at"]),
            "audit_events": [
                event | {"at": _malaysia_iso(event["at"])}
                for event in reversed(state.get("audit_events", []))
            ],
        }

    def current_time(self) -> str:
        return _malaysia_iso(local_clock(_required(self.store.load())))


def _required(state: dict | None) -> dict:
    if state is None:
        raise ReservationError(409, "Load a local test scenario first.")
    return state


def _reservation(state: dict, reservation_id: str) -> dict:
    reservation = state["reservations"].get(reservation_id)
    if reservation is None:
        raise ReservationError(404, "Reservation not found.")
    return reservation


def _code_closes_at(reservation: dict) -> datetime:
    return reservation["pickup_at"] + CODE_WINDOW


def _check_can_load(state: dict, reservation_id: str, reservation: dict, now: datetime) -> None:
    asset_id = reservation["asset_id"]
    if reservation["status"] != "confirmed":
        raise ReservationError(409, "Only a confirmed reservation can be loaded.")
    if now > _code_closes_at(reservation):
        raise ReservationError(409, "The pickup window for this reservation has closed.")
    if state["assets"][asset_id]["condition"] != "good":
        raise ReservationError(409, "This unit is on hold.")
    # Anything except a closed loan blocks loading, including a return awaiting its check.
    if any(
        loan["asset_id"] == asset_id and loan["status"] != "returned"
        for loan in state["loans"].values()
    ):
        raise ReservationError(409, "This unit is still on loan.")
    if uncollected_pickups(state, asset_id):
        raise ReservationError(409, "This unit is already in a compartment.")
    if any(
        other_id != reservation_id
        and other["asset_id"] == asset_id
        and other["status"] in {"confirmed", "ready_for_pickup"}
        and other["pickup_at"] < reservation["pickup_at"]
        and now <= _code_closes_at(other)
        for other_id, other in state["reservations"].items()
    ):
        raise ReservationError(409, "An earlier booking for this unit can still be collected.")


def _load_blocker(state: dict, reservation_id: str, reservation: dict, now: datetime) -> str | None:
    """Tell staff why a booking can't be loaded, so the page can say so before they try."""
    try:
        _check_can_load(state, reservation_id, reservation, now)
        _first_empty_compartment(state)
    except ReservationError as error:
        return str(error)
    return None


def _by_pickup_time(state: dict) -> list[tuple[str, dict]]:
    return sorted(state["reservations"].items(), key=lambda item: item[1]["pickup_at"])


def _first_empty_compartment(state: dict) -> str:
    compartments = state["locker"]["compartments"]
    for compartment in sorted(compartments):
        if compartments[compartment] == "empty":
            return compartment
    raise ReservationError(409, "Both compartments are full.")


def _step(reservation: dict, access: dict | None, now: datetime) -> str:
    if reservation["status"] == "collected":
        return "collected"
    if access is None:
        return "pickup_missed" if now > _code_closes_at(reservation) else "waiting_for_loading"
    if access["used_at"] is not None:
        return "confirm_pickup"
    if access["failed_tries"] >= MAX_WRONG_TRIES:
        return "code_blocked"
    if now > _code_closes_at(reservation):
        return "code_expired"
    if now < reservation["pickup_at"]:
        return "code_not_open"
    return "enter_code"


def _view(state: dict, reservation_id: str, reservation: dict, now: datetime) -> dict:
    access = state.get("pickup_access", {}).get(reservation_id)
    return malaysia_times(
        {
            "id": reservation_id,
            "borrower_id": reservation["borrower_id"],
            "asset_id": reservation["asset_id"],
            "status": reservation["status"],
            "pickup_location": state["location"]["name"],
            "pickup_at": reservation["pickup_at"],
            "due_at": reservation["due_at"],
            "code_closes_at": _malaysia_iso(_code_closes_at(reservation)),
            "compartment": access["compartment"] if access else None,
            "step": _step(reservation, access, now),
            **equipment_requirements(reservation),
        }
    )


def _borrower_views(state: dict, borrower_id: str) -> list[dict]:
    now = local_clock(state)
    return [
        _view(state, reservation_id, reservation, now)
        for reservation_id, reservation in _by_pickup_time(state)
        if reservation["borrower_id"] == borrower_id
    ]


def _loan_view(loan_id: str, loan: dict) -> dict:
    return {
        "id": loan_id,
        **loan,
        "picked_up_at": _malaysia_iso(loan["picked_up_at"]),
        "due_at": _malaysia_iso(loan["due_at"]),
    } | ({"dropped_at": _malaysia_iso(loan["dropped_at"])} if loan.get("dropped_at") else {})


def _audit(
    state: dict, now: datetime, actor: str, action: str, reservation_id: str, asset_id: str
) -> None:
    state.setdefault("audit_events", []).append(
        {
            "at": now,
            "actor": actor,
            "action": action,
            "asset_id": asset_id,
            "reservation_id": reservation_id,
        }
    )


def _malaysia_iso(value: datetime) -> str:
    return value.astimezone(MALAYSIA_TIME).isoformat()
