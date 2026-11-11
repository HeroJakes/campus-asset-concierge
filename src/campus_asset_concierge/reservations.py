from datetime import UTC, datetime
from uuid import uuid4

from campus_asset_concierge.domain.reservations import (
    ReservationError,
    ReservationRequest,
    eligible_unit,
    equipment_requirements,
    local_clock,
    malaysia_times,
)
from campus_asset_concierge.domain.scenarios import BORROWER_A, BORROWER_B
from campus_asset_concierge.storage.local_state import LocalStateStore


# Public demo logins can create offers freely; cap what one borrower can store in the shared document.
MAX_OPEN_OFFERS = 5


def _drop_old_offers(state: dict, offers: dict, borrower_id: str) -> None:
    """Keep room for one more unconfirmed offer; confirmed offers stay so a repeat confirm still works."""
    open_offers = sorted(
        (offer.get("offered_at", datetime.min.replace(tzinfo=UTC)), offer_id)
        for offer_id, offer in offers.items()
        if offer["borrower_id"] == borrower_id and f"reservation-{offer_id}" not in state["reservations"]
    )
    for _, offer_id in open_offers[: max(0, len(open_offers) - MAX_OPEN_OFFERS + 1)]:
        del offers[offer_id]


def _offer_terms(offer: dict) -> dict:
    return {key: value for key, value in offer.items() if key != "offered_at"}


class Reservations:
    def __init__(self, store: LocalStateStore) -> None:
        self.store = store

    def current_time(self) -> datetime | None:
        state = self.store.load()
        return local_clock(state) if state is not None else None

    def offer(self, borrower_id: str, request: ReservationRequest) -> dict:
        self._check_borrower(borrower_id)
        pickup, due = request.window()
        offer_id = uuid4().hex
        requirements = equipment_requirements(request.model_dump())

        def make_offer(state: dict | None) -> dict:
            if state is None:
                raise ReservationError(409, "Load a local test scenario first.")
            now = local_clock(state)
            if pickup < now:
                raise ReservationError(422, "Pickup time cannot be in the past.")
            for asset_id in sorted(state["assets"]):
                if eligible_unit(state, asset_id, request.category, pickup, due, now, **requirements):
                    offer = {
                        "borrower_id": borrower_id,
                        "asset_id": asset_id,
                        "category": request.category.value,
                        "pickup_location": state["location"]["name"],
                        "pickup_at": pickup,
                        "due_at": due,
                        **requirements,
                    }
                    offers = state.setdefault("reservation_offers", {})
                    _drop_old_offers(state, offers, borrower_id)
                    offers[offer_id] = offer | {"offered_at": datetime.now(UTC)}
                    return {"id": offer_id, **malaysia_times(offer)}
            raise ReservationError(409, "No eligible unit is available for that window.")

        return self.store.change(make_offer)

    def confirm(self, borrower_id: str, offer_id: str) -> dict:
        self._check_borrower(borrower_id)
        reservation_id = f"reservation-{offer_id}"

        def confirm_offer(state: dict | None) -> dict:
            if state is None:
                raise ReservationError(409, "Load a local test scenario first.")
            offer = self._owned_offer(state, borrower_id, offer_id)
            existing = state["reservations"].get(reservation_id)
            if existing is not None:
                return {"id": reservation_id, **malaysia_times(existing)}

            now = local_clock(state)
            pickup, due = offer["pickup_at"], offer["due_at"]
            if pickup < now or not eligible_unit(
                state, offer["asset_id"], offer["category"], pickup, due, now,
                **equipment_requirements(offer),
            ):
                raise ReservationError(409, "Availability changed. Check again for a fresh offer.")
            reservation = {**_offer_terms(offer), "status": "confirmed"}
            state["reservations"][reservation_id] = reservation
            return {"id": reservation_id, **malaysia_times(reservation)}

        return self.store.change(confirm_offer)

    def preview(self, borrower_id: str, offer_id: str) -> dict:
        self._check_borrower(borrower_id)
        state = self.store.load()
        if state is None:
            raise ReservationError(409, "Load a local test scenario first.")
        return malaysia_times(_offer_terms(self._owned_offer(state, borrower_id, offer_id)))

    @staticmethod
    def _owned_offer(state: dict, borrower_id: str, offer_id: str) -> dict:
        offer = state.get("reservation_offers", {}).get(offer_id)
        if offer is None or offer["borrower_id"] != borrower_id:
            raise ReservationError(404, "Reservation offer not found.")
        return offer

    @staticmethod
    def _check_borrower(borrower_id: str) -> None:
        if borrower_id not in {BORROWER_A, BORROWER_B}:
            raise ReservationError(403, "Only a borrower can make a reservation.")
