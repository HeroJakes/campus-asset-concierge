# Gemini Enterprise build plan

The hackathon deliverable is built **inside Gemini Enterprise**: one borrower chat agent and one scheduled overdue-recovery workflow, both using our MCP connector. This is the design to execute when the Gemini Enterprise licence arrives (Stage 1.5 is blocked until then). See [ARCHITECTURE.md](ARCHITECTURE.md) and [MCP_CONNECTOR_IMPLEMENTATION.md](MCP_CONNECTOR_IMPLEMENTATION.md).

## Decisions (from the design grill)

- **One chat agent + one workflow** for P0. Adding more is easy later (no-code), so scale only when a real need appears.
- **Chat agent** reuses the MCP connector tools and instructions adapted from the existing `booking_instructions` in `agent/reservations.py`.
- **Workflow** runs on a schedule, calls `run_overdue_recovery`, drafts a staff email for each at-risk booking, and routes it through an approval step. It never auto-sends, and the booking stays unchanged (applying a reassignment is Stage 2.1).
- **Model: the Flash tier** (the current 3.x Flash in the Gemini Enterprise model selector). The tasks are tool-use and light drafting, not heavy reasoning, so Flash is the most suitable: strong tool use, fast, efficient. Not Pro (overkill) and not Flash-Lite (weaker on ambiguous multi-step tasks). It is a one-click change if Flash struggles.
- **Two connectors:** the MCP connector (third-party, our backend) and Gmail (first-party, for the staff email).
- **Borrower identity** comes from the Gemini session. Mapping that trusted identity to a `borrower_id` for the MCP tools is Stage 1.5.

## Chat agent

- **Tools (from the MCP connector):** `find_equipment`, `confirm_booking`, `check_pickup_status`, `check_return_status`.
- **Instructions** (adapted from `booking_instructions`): help the signed-in borrower reserve one item; ask for a missing pickup time and a return time or duration; interpret times in Malaysia time; show the offered asset, location, and pickup and return times before asking for confirmation; only call `confirm_booking` after the borrower explicitly agrees; use the status tools for pickup and return questions. Codes, pickup, and drop-off happen on the locker page, not in chat.
- **Identity:** the borrower comes from the Gemini session (Stage 1.5), then maps to `borrower_id`.

Stage 2.2 adds optional `require_hdmi` and `require_built_in_speakers` booleans to `find_equipment` for projectors. Capture needs the borrower mentions without always asking both questions. Show required capabilities with the offered unit before confirmation, or say "No extra requirements." False means not required, not forbidden. Recovery and approval recheck the saved requirements. Staff can check a pending proposal again on the locker page; this action is not an MCP tool.

## Maximizing workflow

Purpose: protect the next booking when equipment is late, without a human watching. Each run detects overdue loans and hands staff a ready-to-approve recovery action.

- **Schedule:** daily (the maximizing pattern). Demo note: overdue detection uses the local **test clock**, so during the demo we trigger a run on demand after advancing the clock; a real daily schedule maps to real time only after the prototype.
- **Steps:**
  1. Call `run_overdue_recovery` (MCP) → overdue loans, at-risk bookings, substitute proposals, and escalations.
  2. If there are at-risk bookings, for each one draft a staff email (Gmail):
     - **Proposal:** name the overdue loan, the threatened booking, and the verified substitute unit — "approve to proceed".
     - **Escalation:** name the overdue loan and threatened booking, and that no substitute is available — needs staff action.
  3. **Approval step** routed to equipment staff. On approve, send the simulated notification or log the decision. On reject, do nothing.
  4. Label every action simulated.
- **In P0, approval only authorizes the notification.** Applying a substitute (moving the booking) is Stage 2.1. The booking stays unchanged.
- **Model:** Flash.

## Connectors to configure

- **MCP connector** (third-party): the hosted backend (Cloud Run, set up when wiring Gemini). Exposes `find_equipment`, `confirm_booking`, `check_pickup_status`, `check_return_status`, and `run_overdue_recovery`.
- **Gmail** (first-party): to draft the staff email.

## Build steps when the licence arrives

1. Create the Gemini Enterprise app; enable chat agents and workflows.
2. Deploy the MCP connector to Cloud Run and register it as a third-party connector (OAuth client id, secret, redirect URL).
3. Configure the Gmail connector.
4. Build the chat agent: the instructions above, the four borrower tools, Flash model.
5. Build the workflow: schedule → `run_overdue_recovery` → condition on at-risk bookings → draft email → approval, Flash model.
6. Test both scenarios — spare available (verified Projector B proposal) and spare unavailable (staff escalation) — and record the demo.

## Ready vs blocked

- **Ready now:** the MCP connector and its tools, the recovery logic, the agent instructions (already in code), and this design.
- **Blocked on the licence:** building the agent and workflow in Gemini Enterprise, hosting the connector, and the full round-trip — all Stage 1.5.

## Out of scope

- Applying reassignments (Stage 2.1).
- More agents or workflows (scale later).
- Real-time scheduling — the prototype runs on the test clock.
