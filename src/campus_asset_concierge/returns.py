from datetime import datetime
from secrets import compare_digest, randbelow

from campus_asset_concierge.domain.reservations import (
    MALAYSIA_TIME,
    RETURN_CODE_WINDOW,
    ReservationError,
    claim_free_compartment,
    local_clock,
    return_live,
)
from campus_asset_concierge.pickups import MAX_WRONG_TRIES
from campus_asset_concierge.storage.local_state import LocalStateStore

# Loan states that still hold the unit and so can be returned.
OPEN_LOAN = {"active", "overdue", "awaiting_check"}
# The one step where the borrower still needs the return code on screen.
CODE_STEPS = {"enter_code"}


class Returns:
    def __init__(self, store: LocalStateStore) -> None:
        self.store = store

    def request(self, borrower_id: str, asset_id: str) -> dict:
        # Firestore can rerun a transaction, so choose the code once, outside it.
        code = f"{randbelow(10**6):06d}"

        def request_return(state: dict | None) -> dict:
            state = _required(state)
            now = local_clock(state)
            loan_id, loan = _open_loan(state, asset_id)
            if loan is None:
                if any(
                    other["asset_id"] == asset_id and other["status"] == "returned"
                    for other in state["loans"].values()
                ):
                    raise ReservationError(409, "This item has already been returned.")
                raise ReservationError(404, "You have no item to return for that unit.")
            if loan["borrower_id"] != borrower_id:
                raise ReservationError(404, "You have no item to return for that unit.")

            access = _access_for(state, loan_id, asset_id)
            if access is not None and return_live(access, now):
                # Idempotent before the drop: keep the existing code and compartment.
                return _view(asset_id, loan, access, now)
            if access is not None and access["checked_at"] is None:
                # An expired, unused code: free its compartment so it is not orphaned.
                state["locker"]["compartments"][access["compartment"]] = "empty"

            compartment = claim_free_compartment(state, now)
            # shortcut: plain text code suits fictional local data, replace before real use.
            access = {
                "loan_id": loan_id,
                "borrower_id": borrower_id,
                "code": code,
                "compartment": compartment,
                "issued_at": now,
                "failed_tries": 0,
                "used_at": None,
                "dropped_at": None,
                "checked_at": None,
                "result": None,
            }
            state.setdefault("return_access", {})[asset_id] = access
            state["locker"]["compartments"][compartment] = "return_reserved"
            _audit(state, now, borrower_id, "return_requested", asset_id)
            return _view(asset_id, loan, access, now)

        return self.store.change(request_return)

    def unlock(self, borrower_id: str, asset_id: str, code: str) -> dict:
        def try_code(state: dict | None) -> dict | ReservationError:
            state = _required(state)
            now = local_clock(state)
            access = state.get("return_access", {}).get(asset_id)
            if access is None:
                raise ReservationError(409, "There is no return in progress for that item.")
            if access["borrower_id"] != borrower_id:
                # Keep this out of the try count so one borrower cannot block another's code.
                _audit(state, now, borrower_id, "return_code_wrong_user", asset_id)
                return ReservationError(404, "Return not found.")
            if access["used_at"] is not None:
                raise ReservationError(409, "This return code has already been used.")
            if access["failed_tries"] >= MAX_WRONG_TRIES:
                raise ReservationError(409, "This return code is blocked after too many wrong tries.")
            if now > _code_closes_at(access):
                raise ReservationError(409, "This return code has expired.")

            if not compare_digest(access["code"].encode(), code.encode()):
                access["failed_tries"] += 1
                _audit(state, now, borrower_id, "return_code_wrong", asset_id)
                return ReservationError(403, "That code is not correct.")

            access["used_at"] = now
            state["locker"]["compartments"][access["compartment"]] = "unlocked"
            _audit(state, now, borrower_id, "return_unlocked", asset_id)
            return _view(asset_id, state["loans"][access["loan_id"]], access, now)

        outcome = self.store.change(try_code)
        # Raising inside the transaction would discard the saved try and audit event.
        if isinstance(outcome, ReservationError):
            raise outcome
        return outcome

    def drop(self, borrower_id: str, asset_id: str) -> dict:
        def confirm_drop(state: dict | None) -> dict:
            state = _required(state)
            now = local_clock(state)
            access = state.get("return_access", {}).get(asset_id)
            if access is None:
                raise ReservationError(409, "There is no return in progress for that item.")
            if access["borrower_id"] != borrower_id:
                raise ReservationError(404, "Return not found.")
            loan = state["loans"][access["loan_id"]]
            if access["dropped_at"] is not None:
                return _view(asset_id, loan, access, now)
            if access["used_at"] is None:
                raise ReservationError(409, "Unlock the compartment with your code first.")

            access["dropped_at"] = now
            loan["status"] = "awaiting_check"
            loan["dropped_at"] = now
            state["locker"]["compartments"][access["compartment"]] = "returned"
            _audit(state, now, borrower_id, "returned_dropped", asset_id)
            return _view(asset_id, loan, access, now)

        return self.store.change(confirm_drop)

    def verify(self, staff_id: str, asset_id: str, result: str) -> dict:
        if result not in {"pass", "fail"}:
            raise ReservationError(422, "Result must be pass or fail.")

        def verify_return(state: dict | None) -> dict:
            state = _required(state)
            now = local_clock(state)
            access = state.get("return_access", {}).get(asset_id)
            if access is None:
                raise ReservationError(404, "There is nothing to verify for that item.")
            loan = state["loans"][access["loan_id"]]
            if loan["status"] == "returned":
                return _result_view(asset_id, loan, access)
            if loan["status"] != "awaiting_check":
                raise ReservationError(409, "This item has not been dropped off yet.")

            loan["status"] = "returned"
            access["checked_at"] = now
            access["result"] = result
            state["locker"]["compartments"][access["compartment"]] = "empty"
            if result == "fail":
                state["assets"][asset_id]["condition"] = "hold"
            _audit(state, now, staff_id, f"return_{'passed' if result == 'pass' else 'failed'}", asset_id)
            return _result_view(asset_id, loan, access)

        return self.store.change(verify_return)

    def status(self, borrower_id: str) -> list[dict]:
        """Return a borrower's returns without codes, so chat can safely read them."""
        return _borrower_views(_required(self.store.load()), borrower_id)

    def borrower_page(self, borrower_id: str) -> list[dict]:
        """Add the usable return code. Only call this for the signed-in owner."""
        state = _required(self.store.load())
        returns = state.get("return_access", {})
        return [
            view | {"code": returns[view["asset_id"]]["code"]}
            if view["step"] in CODE_STEPS
            else view
            for view in _borrower_views(state, borrower_id)
        ]

    def staff_returns(self) -> list[dict]:
        state = _required(self.store.load())
        now = local_clock(state)
        returns = state.get("return_access", {})
        return [
            _view(asset_id, state["loans"][access["loan_id"]], access, now)
            | {"borrower_id": access["borrower_id"]}
            for asset_id, access in sorted(returns.items())
        ]


def _required(state: dict | None) -> dict:
    if state is None:
        raise ReservationError(409, "Load a local test scenario first.")
    return state


def _open_loan(state: dict, asset_id: str) -> tuple[str | None, dict | None]:
    # Deterministic (sorted) so a broken "one open loan per asset" invariant fails predictably.
    for loan_id, loan in sorted(state["loans"].items()):
        if loan["asset_id"] == asset_id and loan["status"] in OPEN_LOAN:
            return loan_id, loan
    return None, None


def _access_for(state: dict, loan_id: str, asset_id: str) -> dict | None:
    # Return records are kept per unit, so one left by an earlier loan of the unit is not this loan's.
    access = state.get("return_access", {}).get(asset_id)
    return access if access is not None and access["loan_id"] == loan_id else None


def _code_closes_at(access: dict) -> datetime:
    return access["issued_at"] + RETURN_CODE_WINDOW


def _step(loan: dict, access: dict | None, now: datetime) -> str:
    if loan["status"] == "returned":
        return "returned"
    if access is None:
        return "can_return"
    if access["dropped_at"] is not None:
        return "awaiting_check"
    # Once unlocked, the borrower can finish the drop even after the code window.
    if access["used_at"] is not None:
        return "confirm_drop"
    if access["failed_tries"] >= MAX_WRONG_TRIES:
        return "code_blocked"
    if now > _code_closes_at(access):
        return "code_expired"
    return "enter_code"


def _view(asset_id: str, loan: dict, access: dict | None, now: datetime) -> dict:
    return {
        "asset_id": asset_id,
        "loan_id": access["loan_id"] if access else None,
        "loan_status": loan["status"],
        "due_at": _malaysia_iso(loan["due_at"]),
        "compartment": access["compartment"] if access else None,
        "code_closes_at": _malaysia_iso(_code_closes_at(access)) if access else None,
        "step": _step(loan, access, now),
    }


def _result_view(asset_id: str, loan: dict, access: dict) -> dict:
    return {
        "asset_id": asset_id,
        "loan_id": access["loan_id"],
        "loan_status": loan["status"],
        "result": access["result"],
    }


def _borrower_views(state: dict, borrower_id: str) -> list[dict]:
    now = local_clock(state)
    return [
        _view(loan["asset_id"], loan, _access_for(state, loan_id, loan["asset_id"]), now)
        for loan_id, loan in sorted(state["loans"].items())
        if loan["borrower_id"] == borrower_id and loan["status"] in OPEN_LOAN
    ]


def _audit(state: dict, now: datetime, actor: str, action: str, asset_id: str) -> None:
    state.setdefault("audit_events", []).append(
        {"at": now, "actor": actor, "action": action, "asset_id": asset_id, "reservation_id": None}
    )


def _malaysia_iso(value: datetime) -> str:
    return value.astimezone(MALAYSIA_TIME).isoformat()
