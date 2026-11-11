"""Assert the MCP protocol and demo outcomes against an explicitly supplied local URL."""

import argparse
import asyncio
from contextlib import asynccontextmanager
import json

import httpx

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def call(session, name, arguments):
    result = await session.call_tool(name, arguments)
    assert not result.isError, result.content
    return json.loads(result.content[0].text)


@asynccontextmanager
async def connected_session(url: str, *, http_client: httpx.AsyncClient | None = None):
    async with streamable_http_client(url, http_client=http_client) as (read, write, session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            assert session_id() is None
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == {
                "find_equipment", "confirm_booking", "check_pickup_status",
                "check_return_status", "run_overdue_recovery",
            }
            yield session


async def check(url: str, scenario: str, *, http_client: httpx.AsyncClient | None = None) -> None:
    async with connected_session(url, http_client=http_client) as session:
        recovery = await call(session, "run_overdue_recovery", {})
        assert recovery["overdue_loans"][0]["id"] == "active-projector"
        if scenario != "spare_unavailable":  # presentation keeps the spare_available story
            assert recovery["substitution_proposals"][0]["substitute_asset_id"] == "projector-b"
            assert recovery["escalations"] == []
        else:
            assert recovery["substitution_proposals"] == []
            assert recovery["escalations"][0]["owner"] == "equipment-staff"
        rerun = await call(session, "run_overdue_recovery", {})
        # Only the run record changes on a rerun; the lending outcome must not.
        assert rerun.pop("last_run")["new_events"] == 0
        assert rerun == {key: value for key, value in recovery.items() if key != "last_run"}
        offer = await call(session, "find_equipment", {
            "borrower_id": "borrower-a", "category": "projector",
            "pickup_at": "2026-11-07T14:00", "duration_minutes": 60, "require_hdmi": True,
        })
        assert offer["asset_id"] == "projector-b"
        arguments = {"borrower_id": "borrower-a", "offer_id": offer["id"]}
        reservation = await call(session, "confirm_booking", arguments)
        assert reservation["require_hdmi"] is True
        assert await call(session, "confirm_booking", arguments) == reservation
        for tool, key in (("check_pickup_status", "pickups"), ("check_return_status", "returns")):
            status = await call(session, tool, {"borrower_id": "borrower-a"})
            assert all("code" not in item for item in status[key])
    print(f"MCP HTTP checks passed: {scenario}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("scenario", choices=["spare_available", "spare_unavailable", "presentation"])
    args = parser.parse_args()
    asyncio.run(check(args.url, args.scenario))
