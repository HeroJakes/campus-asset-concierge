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
| `find_equipment` | `borrower_id`, `category`, `pickup_at`, `due_at?`, `duration_minutes?`, `require_hdmi?`, `require_built_in_speakers?` | `Reservations.offer` | Yes (offer) | Offer, or `{"error"}` |
| `confirm_booking` | `borrower_id`, `offer_id` | `Reservations.confirm` | Yes (reservation) | Reservation, or `{"error"}` |
| `check_pickup_status` | `borrower_id` | `Pickups.status` | No | Pickups, never the code |
| `check_return_status` | `borrower_id` | `Returns.status` | No | Returns, never the code |
| `run_overdue_recovery` | — | `Recovery.process` | Yes (idempotent) | Overdue loans, at-risk bookings, proposals, escalations |

`find_equipment`, `check_pickup_status`, and `check_return_status` mirror the existing ADK tools. `run_overdue_recovery` is the staff / maximizing-workflow tool: it runs the recovery pass (detect overdue, flag at-risk, record a proposal or escalation) and returns the current picture, so the workflow does not depend on the operator clock-advance having run it first. It is idempotent. The locker device actions (load, unlock, drop, verify) stay on the staff locker page and are **not** exposed over MCP.

Stage 2.2 adds strict boolean projector requirements. True means required; false or omitted is unrestricted. Offers and reservations retain the flags, and recovery results include them with proposals and escalations. Shared request validation returns `{"error"}` for invalid direct tool inputs; malformed MCP arguments can be rejected earlier as MCP tool errors. Staff recheck and approval actions stay on the authenticated API and locker page.

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
- Local HTTP: set `MCP_TRANSPORT=streamable-http` and follow the [container and seeding guide](MCP_LOCAL_CONTAINER.md). The server uses stateless HTTP at `/mcp` with host/origin checks. Hosting and trusted caller identity remain pending.
- Add the official `mcp` package to `pyproject.toml` dependencies.

## Testing

`tests/test_mcp_server.py`, against the Firestore emulator, mirroring `tests/test_agent_reservations.py`:

- Build the tools over a test store (the `booking_app` fixture).
- `find_equipment` returns the same offer the API returns; `confirm_booking` returns a confirmed reservation; a repeated confirm returns the same reservation.
- `check_pickup_status` and `check_return_status` never include the code.
- Bad input returns `{"error": ...}`, not a raised exception.
- After the clock moves past a due time, `run_overdue_recovery` detects the overdue loan on its own and returns the proposal (spare available) or escalation (spare unavailable).

## Identity and security (shortcut)

- The connector has **no caller authentication** in P0. `borrower_id` is trusted from each call, so a caller can act for or read any borrower (find, confirm, pickup, return), and `run_overdue_recovery` returns staff data to any caller.
- `shortcut: no caller auth yet; before real use, bind identity and role from the authenticated Gemini session (Stage 1.5), not free parameters.`
- `shortcut: find_equipment writes an offer per call and offers are never pruned; fine for the demo (a reset clears them), add offer expiry before real use.`

## Dependencies and ordering

- **Depends on Stage 1.4 (Recovery) being on `main`** for `list_overdue`. Build this after Stage 1.4 merges, or base the connector branch on the Stage 1.4 branch.
- Does **not** need the Gemini Enterprise licence to build or test standalone. The full Gemini round-trip is verified in Stage 1.5, which is blocked by the licence delay.

## Out of scope

- Hosting and deploy (Cloud Run) — done later, when wiring Gemini.
- Locker device actions over MCP — they stay on the staff locker page.
- Real trusted-identity binding — Stage 1.5.

The Gemini + MCP decision is recorded in [ARCHITECTURE.md](ARCHITECTURE.md); this plan does not need a separate ADR.
