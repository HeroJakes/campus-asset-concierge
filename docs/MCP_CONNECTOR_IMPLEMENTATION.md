# MCP connector implementation plan

## Purpose

Expose the existing backend to Gemini Enterprise as an **MCP connector** (a third-party connector), so the Gemini chat agent and the maximizing workflow can call our booking, pickup, return, and overdue-recovery logic. See [ARCHITECTURE.md](ARCHITECTURE.md) for how this fits the whole system.

The connector is a **second entry point** to the same domain code the FastAPI app already uses. It is not a new backend.

```text
Gemini agent ──(MCP)──► mcp_server.py ──► domain classes ──► LocalStateStore ──► Firestore
                        (thin wrapper)     (Reservations, Pickups,
                                            Returns, Recovery — reused)
```

## Decisions (agreed in the design grill)

- **In-process reuse.** A new `src/campus_asset_concierge/mcp_server.py` builds the domain classes over one shared `LocalStateStore` and exposes their methods as tools. No HTTP self-calls.
- **Five tools** (below). Reuse the same logic the ADK tools in `agent/reservations.py` already wrap.
- **Identity by parameter for now.** Borrower tools take a `borrower_id` argument. Real trusted identity from Gemini is Stage 1.5.
- **FastMCP** (the official `mcp` Python SDK). Tools are transport-agnostic: stdio for the local MCP Inspector now, HTTP for Gemini later.
- **`confirm_booking` is one call.** Human approval is handled by the agent's instructions (show the offer from `find_equipment`, confirm only after the borrower agrees), the same wording already in `booking_instructions`.
- **Errors:** catch `ReservationError` and validation errors and return `{"error": message}`; let unexpected errors propagate as normal MCP tool errors.
- **Writes** go through the existing `store.change` transactions, so the booking race protection still holds.

## Tools

| Tool | Parameters | Wraps | Writes? | Returns |
| --- | --- | --- | --- | --- |
| `find_equipment` | `borrower_id`, `category`, `pickup_at`, `due_at?`, `duration_minutes?` | `Reservations.offer` | Yes (offer) | Offer, or `{"error"}` |
| `confirm_booking` | `borrower_id`, `offer_id` | `Reservations.confirm` | Yes (reservation) | Reservation, or `{"error"}` |
| `check_pickup_status` | `borrower_id` | `Pickups.status` | No | Pickups, never the code |
| `check_return_status` | `borrower_id` | `Returns.status` | No | Returns, never the code |
| `list_overdue` | — | `Recovery.staff_page` | No | Overdue loans, at-risk bookings, proposals, escalations |

`find_equipment`, `check_pickup_status`, and `check_return_status` mirror the existing ADK tools. `list_overdue` is the staff / maximizing-workflow read. The locker device actions (load, unlock, drop, verify) stay on the staff locker page and are **not** exposed over MCP.

## Code shape

- `mcp_server.py`:
  - Construct `LocalStateStore` and the domain classes once.
  - Define a `FastMCP` app and the five tool functions. FastMCP turns each function's type hints and docstring into the tool schema Gemini sees, so write clear docstrings (reuse the ADK tool docstrings).
  - Each tool catches `ReservationError`/validation and returns `{"error": message}`.
  - Status tools call `Pickups.status` / `Returns.status`, which already omit the one-time code.
  - A `main()` entry point runs the server (stdio by default).
- The ADK tool bodies in `agent/reservations.py` are already thin wrappers over the domain classes. The MCP tools call the domain classes the same way, so the two stay parallel without new shared abstractions.

## Running it

- Local test with the MCP Inspector (stdio): `uv run python -m campus_asset_concierge.mcp_server`.
- HTTP for Gemini (later): run FastMCP's HTTP transport on a port and host it (Cloud Run) when wiring Gemini. Hosting is out of scope for this stage.
- Add the official `mcp` package to `pyproject.toml` dependencies.

## Testing

`tests/test_mcp_server.py`, against the Firestore emulator, mirroring `tests/test_agent_reservations.py`:

- Build the tools over a test store (the `booking_app` fixture).
- `find_equipment` returns the same offer the API returns; `confirm_booking` returns a confirmed reservation; a repeated confirm returns the same reservation.
- `check_pickup_status` and `check_return_status` never include the code.
- Bad input returns `{"error": ...}`, not a raised exception.
- After a clock advance, `list_overdue` returns the proposal (spare available) or escalation (spare unavailable).

## Identity and security (shortcut)

- `borrower_id` is trusted from the tool argument in P0.
- `shortcut: borrower_id is trusted from the call, which lets a caller act for any borrower; before real use, bind the borrower from the authenticated Gemini session (Stage 1.5), not a free parameter.`

## Dependencies and ordering

- **Depends on Stage 1.4 (Recovery) being on `main`** for `list_overdue`. Build this after Stage 1.4 merges, or base the connector branch on the Stage 1.4 branch.
- Does **not** need the Gemini Enterprise licence to build or test standalone. The full Gemini round-trip is verified in Stage 1.5, which is blocked by the licence delay.

## Out of scope

- Hosting and deploy (Cloud Run) — done later, when wiring Gemini.
- Locker device actions over MCP — they stay on the staff locker page.
- Real trusted-identity binding — Stage 1.5.

The Gemini + MCP decision is recorded in [ARCHITECTURE.md](ARCHITECTURE.md); this plan does not need a separate ADR.
