"""The MCP tools are thin wrappers, so we test them at the same seam as the ADK agent:
call the tool functions directly against the emulator and check parity with the API."""

import asyncio

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from campus_asset_concierge.domain.scenarios import BORROWER_A as BORROWER_A_ID
from campus_asset_concierge.mcp_server import build_tools, create_mcp_server
from conftest import BORROWER_A


def tools(store):
    return {tool.__name__: tool for tool in build_tools(store)}


def test_mcp_preserves_and_validates_projector_requirements(booking_app):
    _, store = booking_app
    tool = tools(store)
    find = tool["find_equipment"]
    assert "error" in find(BORROWER_A_ID, "projector", "2026-11-07T12:00", duration_minutes=60, require_built_in_speakers=True)
    offer = find(BORROWER_A_ID, "projector", "2026-11-07T13:00", duration_minutes=60, require_hdmi=True)
    reservation = tool["confirm_booking"](BORROWER_A_ID, offer["id"])
    assert reservation["require_hdmi"] is True
    assert "error" in find(BORROWER_A_ID, "projector", "2026-11-07T13:00", duration_minutes=60, require_hdmi="yes")


def test_mcp_transport_rejects_numeric_requirement_before_coercion(booking_app):
    _, store = booking_app
    server = create_mcp_server(store)
    with pytest.raises(ToolError, match="boolean"):
        asyncio.run(server.call_tool("find_equipment", {
            "borrower_id": BORROWER_A_ID, "category": "projector",
            "pickup_at": "2026-11-07T13:00", "duration_minutes": 60, "require_hdmi": 1,
        }))


def test_find_equipment_matches_the_api_offer(booking_app):
    _, store = booking_app
    offer = tools(store)["find_equipment"](
        BORROWER_A_ID, "projector", "2026-11-07T12:00", duration_minutes=60
    )
    assert offer["asset_id"] == "projector-b"
    assert offer["pickup_at"] == "2026-11-07T12:00:00+08:00"
    assert offer["due_at"] == "2026-11-07T13:00:00+08:00"


def test_confirm_booking_books_the_offer(booking_app):
    _, store = booking_app
    tool = tools(store)
    offer_id = tool["find_equipment"](BORROWER_A_ID, "projector", "2026-11-07T12:00", duration_minutes=60)["id"]

    reservation = tool["confirm_booking"](BORROWER_A_ID, offer_id)
    assert reservation["asset_id"] == "projector-b"
    assert reservation["status"] == "confirmed"
    # A repeated confirm returns the same reservation, never a second one.
    assert tool["confirm_booking"](BORROWER_A_ID, offer_id) == reservation


def test_find_equipment_returns_an_error_for_bad_input(booking_app):
    _, store = booking_app
    find = tools(store)["find_equipment"]
    # Unknown category -> pydantic ValidationError path.
    assert "error" in find(BORROWER_A_ID, "banana", "2026-11-07T12:00", duration_minutes=60)
    # Pickup before the seeded clock -> ReservationError path.
    assert "error" in find(BORROWER_A_ID, "raspberry_pi_kit", "2026-11-07T09:59", duration_minutes=60)


def test_status_tools_never_return_a_code(booking_app):
    client, store = booking_app
    tool = tools(store)
    # Start a real return so a code exists in state, then confirm the tool hides it.
    assert client.post("/assets/projector-a/return-request", auth=BORROWER_A).status_code == 200
    code = store.load()["return_access"]["projector-a"]["code"]

    returns_view = tool["check_return_status"](BORROWER_A_ID)["returns"]
    assert returns_view, "borrower-a starts with Projector A on loan"
    assert all("code" not in item for item in returns_view)
    assert code not in str(returns_view)
    assert all("code" not in item for item in tool["check_pickup_status"](BORROWER_A_ID)["pickups"])


def test_run_overdue_recovery_detects_and_proposes(booking_app):
    _, store = booking_app
    # Move the clock past the due time WITHOUT the API's recovery pass, so the tool must run it.
    store.advance(61)

    overdue = tools(store)["run_overdue_recovery"]()
    assert [loan["id"] for loan in overdue["overdue_loans"]] == ["active-projector"]
    assert overdue["substitution_proposals"][0]["substitute_asset_id"] == "projector-b"


def test_create_mcp_server_registers_the_tools(booking_app):
    _, store = booking_app
    server = create_mcp_server(store)
    assert server.name == "campus-asset-concierge"
