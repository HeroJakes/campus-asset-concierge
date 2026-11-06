# Demo script

One tight, fictional storyline for the live demo and the video. It shows the two capabilities — the borrower **chat agent** and the **maximizing recovery workflow** — using the seeded data in `domain/scenarios.py`. All data is fictional.

## The world (seeded fixtures)

Local test clock starts at **10:00 MYT on 2026-11-07**.

| Thing | Detail |
| --- | --- |
| Projector A | good; **HDMI + built-in speakers** |
| Projector B | good; **HDMI only** (no speakers) |
| Raspberry Pi kit | good |
| Borrower A | has **Projector A** on loan, **due 11:00** |
| Borrower B | has a **confirmed booking** for a projector, **12:00–13:00** (on Projector A) |

The two scenarios differ in one thing:

- **`spare_available`** — Projector B is free, so it can cover Borrower B's booking.
- **`spare_unavailable`** — Projector B is also booked 12:00–13:00, so no spare exists.

## Act 1 — Borrower books in chat (chat agent)

Shows natural-language booking with requirement matching.

> **Borrower B:** "I need a projector with HDMI from 2pm to 3pm today."

1. The agent calls `find_equipment(category=projector, pickup_at=2026-11-07T14:00, duration_minutes=60, require_hdmi=true)`.
2. It offers **Projector B** and shows the asset, location (Campus Loan Desk), pickup 14:00, return 15:00, and **Requirements: HDMI**.
3. The borrower agrees; the agent calls `confirm_booking`. The booking is confirmed with its requirement saved.

Talking point: the borrower never sees locker codes in chat — pickup and drop-off happen on the locker page.

## Act 2 — Equipment runs late (maximizing workflow)

Borrower A does not return Projector A by 11:00. Advance the clock one minute past the due time so the loan is overdue, then run the daily workflow.

### Scenario A — spare available (proposal)

1. Seed and advance the clock:
   ```powershell
   docker exec campus-mcp python -m campus_asset_concierge.seed_demo spare_available --advance-minutes 61
   ```
   The clock is now **11:01 MYT**; Projector A's loan (due 11:00) is overdue.
2. Run the workflow (it calls `run_overdue_recovery`). Expected result:
   - `overdue_loans` → **active-projector** (Projector A).
   - `at_risk_reservations` → Borrower B's 12:00 booking (**next-projector**).
   - `substitution_proposals` → verified substitute **Projector B** for that booking.
   - `escalations` → empty.
3. The workflow drafts the **proposal email** to equipment staff and routes it for approval.
4. On the locker page, staff **approve** the substitution (Stage 2.1). Borrower B's booking moves to **Projector B**; Projector A's loan stays overdue for follow-up.

### Scenario B — no spare (escalation)

1. Seed the other scenario (Projector B is also booked):
   ```powershell
   docker exec campus-mcp python -m campus_asset_concierge.seed_demo spare_unavailable --replace --advance-minutes 61
   ```
2. Run the workflow. Expected result:
   - `overdue_loans` → **active-projector**.
   - `at_risk_reservations` → Borrower B's 12:00 booking.
   - `substitution_proposals` → empty.
   - `escalations` → one, owner **equipment-staff**.
3. The workflow drafts the **escalation email**: no substitute, staff action needed.

Talking point: same overdue event, two outcomes — the system either hands staff a ready-to-approve fix or escalates clearly. Every action is labelled simulated.

## Running without the Gemini app

Until the Gemini Enterprise app is built, drive the same story through the MCP connector directly:

```powershell
uv run --locked python tests/mcp_http_smoke.py http://127.0.0.1:18081/mcp spare_available
uv run --locked python tests/mcp_http_smoke.py http://127.0.0.1:18081/mcp spare_unavailable
```

See [MCP_LOCAL_CONTAINER.md](MCP_LOCAL_CONTAINER.md) for starting the container, and [GEMINI_BUILD_SHEET.md](GEMINI_BUILD_SHEET.md) for building the agent and workflow.

## Notes

- Overdue detection uses the **test clock**, so the demo advances it on demand. A real daily schedule maps to real time only after the prototype.
- `--advance-minutes` builds the clock offset into the seed; recovery does not run during seeding, so the first workflow run is the detection moment.
- Reseed with `--replace` before repeating a scenario, because the smoke run and approvals change the demo state.
