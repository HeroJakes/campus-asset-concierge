"""Cover the ADK agent tools without Gemini: they must reach the same booking
logic the API does. Live chat is verified later in Stage 1.5."""

from campus_asset_concierge.agent.reservations import create_reservation_agent
from campus_asset_concierge.domain.scenarios import BORROWER_A
from campus_asset_concierge.reservations import Reservations


class FakeActions:
    skip_summarization = False


class FakeApproval:
    def __init__(self, confirmed: bool) -> None:
        self.confirmed = confirmed


class FakeToolContext:
    """Stand in for ADK's ToolContext so confirm_reservation runs offline."""

    def __init__(self, approval: FakeApproval | None = None) -> None:
        self.tool_confirmation = approval
        self.actions = FakeActions()
        self.requested: dict | None = None

    def request_confirmation(self, hint: str, payload: dict) -> None:
        self.requested = {"hint": hint, "payload": payload}


def _tool(agent, name: str):
    for tool in agent.tools:
        func = tool if callable(tool) and hasattr(tool, "__name__") else getattr(tool, "func", None)
        if func is not None and func.__name__ == name:
            return func
    raise AssertionError(f"Tool {name} not registered on the agent")


def _agent(store):
    return create_reservation_agent(Reservations(store), BORROWER_A, model="none")


def test_agent_captures_requirements_and_shows_them_for_confirmation(booking_app):
    _, store = booking_app
    agent = _agent(store)
    find = _tool(agent, "find_equipment")
    assert "error" in find("projector", "2026-11-07T12:00", duration_minutes=60, require_built_in_speakers=True)
    offer = find("projector", "2026-11-07T13:00", duration_minutes=60, require_hdmi=True, require_built_in_speakers=True)
    pending = FakeToolContext()
    _tool(agent, "confirm_reservation")(offer["id"], pending)
    assert "HDMI" in pending.requested["hint"]
    assert "Built-in speakers" in pending.requested["hint"]
    assert "error" in find("projector", "2026-11-07T13:00", duration_minutes=60, require_hdmi="yes")


def test_find_equipment_tool_matches_the_api_offer(booking_app):
    _, store = booking_app
    find = _tool(_agent(store), "find_equipment")

    offer = find("projector", "2026-11-07T12:00", duration_minutes=60)

    assert offer["asset_id"] == "projector-b"
    assert offer["pickup_at"] == "2026-11-07T12:00:00+08:00"
    assert offer["due_at"] == "2026-11-07T13:00:00+08:00"


def test_find_equipment_tool_returns_error_for_bad_input(booking_app):
    _, store = booking_app
    find = _tool(_agent(store), "find_equipment")

    # Unknown category -> pydantic ValidationError path
    assert "error" in find("banana", "2026-11-07T12:00", duration_minutes=60)
    # No eligible unit for the window -> ReservationError path
    assert "error" in find("raspberry_pi_kit", "2026-11-07T09:59", duration_minutes=60)


def test_confirm_reservation_tool_asks_then_applies_approval(booking_app):
    _, store = booking_app
    agent = _agent(store)
    find = _tool(agent, "find_equipment")
    confirm = _tool(agent, "confirm_reservation")
    offer_id = find("projector", "2026-11-07T12:00", duration_minutes=60)["id"]

    # No approval yet: the tool must pause and ask, not book.
    pending = FakeToolContext(approval=None)
    assert confirm(offer_id, pending) == {"status": "awaiting_confirmation"}
    assert pending.requested is not None
    assert pending.requested["payload"] == {"offer_id": offer_id}
    assert pending.actions.skip_summarization is True

    # Declined approval leaves no reservation.
    assert confirm(offer_id, FakeToolContext(FakeApproval(confirmed=False))) == {"status": "declined"}

    # Approval books the exact offer.
    reservation = confirm(offer_id, FakeToolContext(FakeApproval(confirmed=True)))
    assert reservation["asset_id"] == "projector-b"
    assert reservation["status"] == "confirmed"

    # An approved confirm for an unknown offer surfaces the booking error.
    assert "error" in confirm("missing", FakeToolContext(FakeApproval(confirmed=True)))


def test_booking_instructions_report_the_local_test_time(booking_app):
    _, store = booking_app
    instruction = _agent(store).instruction

    text = instruction(None)

    assert "Malaysia time" in text
    assert "2026-11-07" in text  # the reset clock leaks into the reference line
