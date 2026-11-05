"""MCP connector: a second entry point that exposes the backend to Gemini Enterprise.

The tools reuse the same domain classes as the FastAPI app. See
docs/MCP_CONNECTOR_IMPLEMENTATION.md.
"""

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from campus_asset_concierge.domain.reservations import ReservationError, ReservationRequest
from campus_asset_concierge.pickups import Pickups
from campus_asset_concierge.recovery import Recovery
from campus_asset_concierge.reservations import Reservations
from campus_asset_concierge.returns import Returns
from campus_asset_concierge.storage.local_state import LocalStateStore


def build_tools(store: LocalStateStore) -> list[Callable]:
    """Return the connector's tool functions bound to one store, for the server and for tests."""
    reservations = Reservations(store)
    pickups = Pickups(store)
    returns = Returns(store)
    recovery = Recovery(store)

    # shortcut: no caller authentication yet. borrower_id is trusted from each call, so a caller
    # can act for or read any borrower (find/confirm/pickup/return), and run_overdue_recovery
    # exposes staff data to any caller. Bind real identity and role from the Gemini session
    # before real use (Stage 1.5).
    def find_equipment(
        borrower_id: str,
        category: str,
        pickup_at: str,
        due_at: str | None = None,
        duration_minutes: int | None = None,
    ) -> dict:
        """Find a reservation offer for a borrower. Category is projector or raspberry_pi_kit; use a full local date and time."""
        # shortcut: each call writes an offer that is never pruned; fine for the demo (a reset
        # clears offers), revisit with offer expiry before real use.
        try:
            request = ReservationRequest.model_validate(
                {
                    "category": category,
                    "pickup_at": pickup_at,
                    "due_at": due_at,
                    "duration_minutes": duration_minutes,
                }
            )
            return reservations.offer(borrower_id, request)
        except ValidationError:
            return {"error": "Check the equipment category, pickup time, and return time or duration."}
        except ReservationError as error:
            return {"error": str(error)}

    def confirm_booking(borrower_id: str, offer_id: str) -> dict:
        """Confirm a reservation offer. Only call this after the borrower agrees to the shown offer."""
        try:
            return reservations.confirm(borrower_id, offer_id)
        except ReservationError as error:
            return {"error": str(error)}

    def check_pickup_status(borrower_id: str) -> dict:
        """Show the borrower's pickups. This never returns a one-time code."""
        try:
            return {"pickups": pickups.status(borrower_id)}
        except ReservationError as error:
            return {"error": str(error)}

    def check_return_status(borrower_id: str) -> dict:
        """Show the borrower's open loans and return progress. This never returns a code."""
        try:
            return {"returns": returns.status(borrower_id)}
        except ReservationError as error:
            return {"error": str(error)}

    def run_overdue_recovery() -> dict:
        """Run the overdue-recovery check and return overdue loans, at-risk bookings, substitute proposals, and escalations for staff. Safe to call repeatedly."""
        try:
            return recovery.process()
        except ReservationError as error:
            return {"error": str(error)}

    return [find_equipment, confirm_booking, check_pickup_status, check_return_status, run_overdue_recovery]


def create_mcp_server(store: LocalStateStore | None = None) -> FastMCP:
    mcp = FastMCP("campus-asset-concierge")
    for tool in build_tools(store if store is not None else LocalStateStore()):
        mcp.tool()(tool)
    return mcp


def main() -> None:
    create_mcp_server().run()


if __name__ == "__main__":
    main()
