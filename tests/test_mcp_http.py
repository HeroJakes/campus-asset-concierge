import asyncio
import multiprocessing
import os
import sys
from contextlib import contextmanager
import socket
from threading import Thread
import time

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import pytest
import uvicorn

from campus_asset_concierge.mcp_server import create_mcp_server
from campus_asset_concierge.domain.scenarios import TestScenario as Scenario
from campus_asset_concierge.domain.reservations import ReservationError
from campus_asset_concierge.reservations import Reservations
from campus_asset_concierge.storage.local_state import LocalStateStore
from mcp_http_smoke import call, check, connected_session


@contextmanager
def running_server(store, monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        server = uvicorn.Server(uvicorn.Config(
            create_mcp_server(store).streamable_http_app(), log_level="error",
        ))
        thread = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started:
                if not thread.is_alive() or time.monotonic() >= deadline:
                    raise AssertionError("MCP HTTP server did not start.")
                time.sleep(0.01)
            yield f"http://127.0.0.1:{listener.getsockname()[1]}/mcp"
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            assert not thread.is_alive(), "MCP HTTP server did not stop."


def test_http_protocol_preserves_booking_and_rejects_untrusted_hosts(booking_app, monkeypatch):
    _, store = booking_app
    with running_server(store, monkeypatch) as url:
        assert httpx.post(url, headers={"Host": "attacker.example"}, json={}).status_code == 421
        assert httpx.post(url, headers={"Origin": "https://attacker.example"}, json={}).status_code == 403
        assert httpx.get(url.replace("/mcp", "/locker")).status_code == 404

        async def exercise():
            async with connected_session(url) as session:
                offer = await call(session, "find_equipment", {
                    "borrower_id": "borrower-a", "category": "projector",
                    "pickup_at": "2026-11-07T13:00", "duration_minutes": 60,
                    "require_built_in_speakers": True,
                })
                assert offer["asset_id"] == "projector-a"
                booking = await call(session, "confirm_booking", {
                    "borrower_id": "borrower-a", "offer_id": offer["id"],
                })
                assert booking["require_built_in_speakers"] is True

        asyncio.run(exercise())


@pytest.mark.parametrize("name,value", [("MCP_TRANSPORT", "sse"), ("PORT", "0"), ("PORT", "65536"), ("PORT", "bad")])
def test_invalid_http_configuration_fails_before_startup(booking_app, monkeypatch, name, value):
    _, store = booking_app
    monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        create_mcp_server(store)


@pytest.mark.parametrize("scenario", list(Scenario))
def test_http_recovery_outcomes(booking_app, monkeypatch, scenario):
    _, store = booking_app
    store.seed(scenario, replace=True, advance_minutes=61)
    with running_server(store, monkeypatch) as url:
        asyncio.run(check(url, scenario.value))


def test_http_startup_does_not_create_missing_demo_state(local_app, monkeypatch):
    _, store = local_app

    async def exercise(url):
        async with connected_session(url) as session:
            result = await call(session, "run_overdue_recovery", {})
            assert "Load a local test scenario first" in result["error"]

    with running_server(store, monkeypatch) as url:
        asyncio.run(exercise(url))
    assert store.load() is None


@pytest.mark.parametrize("name,value", [
    ("MCP_ALLOWED_HOSTS", "*"), ("MCP_ALLOWED_HOSTS", ""),
    ("MCP_ALLOWED_HOSTS", "http://localhost:8081/path"),
    ("MCP_ALLOWED_ORIGINS", "https://*.example"),
    ("MCP_ALLOWED_ORIGINS", "https://example/path"),
])
def test_invalid_host_configuration_is_rejected(booking_app, monkeypatch, name, value):
    _, store = booking_app
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        create_mcp_server(store)


def test_module_defaults_to_stdio_without_http_port(booking_app):
    async def exercise():
        parameters = StdioServerParameters(
            command=sys.executable, args=["-m", "campus_asset_concierge.mcp_server"],
            env={"FIRESTORE_EMULATOR_HOST": os.environ["FIRESTORE_EMULATOR_HOST"], "PORT": "invalid"},
        )
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                assert len((await session.list_tools()).tools) == 5

    asyncio.run(exercise())


def confirm_in_process(emulator, document_id, borrower, offer_id, start, results):
    os.environ["FIRESTORE_EMULATOR_HOST"] = emulator
    reservations = Reservations(LocalStateStore(document_id))
    start.wait(timeout=15)
    try:
        reservations.confirm(borrower, offer_id)
        results.put(200)
    except ReservationError as error:
        results.put(error.status)


def test_transactions_protect_last_unit_across_processes(booking_app):
    client, store = booking_app
    borrowers = ["borrower-a", "borrower-b"]
    offers = [client.post("/reservation-offers", auth=(borrower, f"test-{borrower.replace('-', '_')}"),
                         json={"category": "projector", "pickup_at": "2026-11-07T12:00", "duration_minutes": 60}).json()
              for borrower in borrowers]
    context = multiprocessing.get_context("spawn")
    start, results = context.Barrier(2), context.Queue()
    workers = [context.Process(target=confirm_in_process, args=(
        os.environ["FIRESTORE_EMULATOR_HOST"], store.document.id, borrower, offer["id"], start, results,
    )) for borrower, offer in zip(borrowers, offers, strict=True)]
    try:
        for worker in workers:
            worker.start()
        outcomes = sorted(results.get(timeout=60) for _ in workers)
        assert outcomes in ([200, 409], [409, 409])
        for worker in workers:
            worker.join(timeout=10)
            assert worker.exitcode == 0
        # The emulator can abort both contenders; retry after its locks are released.
        service = Reservations(store)
        final_outcomes = []
        for borrower, offer in zip(borrowers, offers, strict=True):
            try:
                service.confirm(borrower, offer["id"])
                final_outcomes.append(200)
            except ReservationError as error:
                final_outcomes.append(error.status)
        assert sorted(final_outcomes) == [200, 409]
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=5)
        results.close()
