from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext
from pydantic import ValidationError

from campus_asset_concierge.domain.reservations import (
    MALAYSIA_TIME,
    ReservationError,
    ReservationRequest,
)
from campus_asset_concierge.pickups import Pickups
from campus_asset_concierge.reservations import Reservations


def create_reservation_agent(reservations: Reservations, borrower_id: str, model: str) -> Agent:
    """Bind a server-authenticated borrower to this agent before running a chat."""
    pickups = Pickups(reservations.store)

    def find_equipment(
        category: str,
        pickup_at: str,
        due_at: str | None = None,
        duration_minutes: int | None = None,
    ) -> dict:
        """Find an offer for projector or raspberry_pi_kit using a full local date and time."""
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

    def confirm_reservation(offer_id: str, tool_context: ToolContext) -> dict:
        """Confirm the exact offer shown to the borrower."""
        try:
            approval = tool_context.tool_confirmation
            if approval is None:
                offer = reservations.preview(borrower_id, offer_id)
                tool_context.request_confirmation(
                    hint=(
                        f"Reserve {offer['asset_id']} at {offer['pickup_location']} from "
                        f"{offer['pickup_at']} to {offer['due_at']} (Malaysia time)?"
                    ),
                    payload={"offer_id": offer_id},
                )
                tool_context.actions.skip_summarization = True
                return {"status": "awaiting_confirmation"}
            if not approval.confirmed:
                return {"status": "declined"}
            return reservations.confirm(borrower_id, offer_id)
        except ReservationError as error:
            return {"error": str(error)}

    def check_pickup_status() -> dict:
        """Show the signed-in borrower's pickups. This never returns a one-time code."""
        try:
            return {"pickups": pickups.status(borrower_id)}
        except ReservationError as error:
            return {"error": str(error)}

    def booking_instructions(_: ReadonlyContext) -> str:
        now = reservations.current_time()
        reference = (
            f"The current local test time is {now.astimezone(MALAYSIA_TIME).isoformat()}. "
            if now is not None
            else ""
        )
        return reference + (
            "Help the signed-in borrower reserve one item. Ask for missing pickup time and "
            "return time or duration. Interpret times in Malaysia time. Resolve relative dates "
            "only when the reference date is known, or ask for the exact date. Show the offered "
            "asset, location, pickup time, and return time before asking for confirmation. "
            "Only call confirm_reservation after the borrower explicitly agrees to that offer. "
            "If availability changed, offer to check again and show any new offer for review. "
            "Use check_pickup_status for questions about pickup. The borrower sees their code, "
            "enters it, and confirms pickup on the locker page, not in this chat."
        )

    return Agent(
        name="campus_asset_concierge",
        model=model,
        instruction=booking_instructions,
        tools=[find_equipment, confirm_reservation, check_pickup_status],
    )
