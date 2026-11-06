# Gemini Enterprise build sheet

Paste-ready content for building the Gemini Enterprise app when the licence arrives. This sheet is the **exact text and field values** to enter. For the reasoning behind each choice, see [GEMINI_BUILD_PLAN.md](GEMINI_BUILD_PLAN.md); this sheet does not repeat it.

Fill the two placeholders before you start:

- `<MCP_URL>` — the deployed connector URL, for example `https://campus-mcp-xxxx.run.app/mcp`.
- `<STAFF_EMAIL>` — the equipment-staff address that receives recovery emails.

## 1. App and connectors

| Field | Value |
| --- | --- |
| App type | Gemini Enterprise app with chat agents and workflows enabled |
| Connector A (third-party) | MCP connector at `<MCP_URL>` — exposes `find_equipment`, `confirm_booking`, `check_pickup_status`, `check_return_status`, `run_overdue_recovery` |
| Connector B (first-party) | Gmail — used by the workflow to draft the staff email |
| Model (both agent and workflow) | Flash tier (current 3.x Flash in the model selector) |

## 2. Chat agent

**Name:** `campus_asset_concierge`

**Tools (from the MCP connector):** `find_equipment`, `confirm_booking`, `check_pickup_status`, `check_return_status`. Do **not** give the chat agent `run_overdue_recovery` (that is staff/workflow only).

**Instruction (paste verbatim):**

```
Help the signed-in borrower reserve one item. Ask for missing pickup time and
return time or duration. Interpret times in Malaysia time. Resolve relative dates
only when the reference date is known, or ask for the exact date. Show the offered
asset, location, pickup time, and return time before asking for confirmation.
Capture HDMI and built-in speaker requirements only when the borrower mentions
those needs; do not always ask about both. Show the requirements with the offer,
or say No extra requirements. False means not required, not forbidden.
Only call confirm_booking after the borrower explicitly agrees to that offer.
If availability changed, offer to check again and show any new offer for review.
Use check_pickup_status for questions about pickup and check_return_status for
questions about returning an item. The borrower sees their code, enters it, and
confirms pickup or drop-off on the locker page, not in this chat.
```

This is the `booking_instructions` text from `agent/reservations.py`, with the tool name changed to the MCP name `confirm_booking`. The code injects the current test time as a prefix; in Gemini the tools return times, so no prefix is needed.

**Identity note:** the MCP tools take `borrower_id` as their first argument. Mapping the trusted Gemini session identity to a `borrower_id` is Stage 1.5. Until then, a fixed fictional id (for example `borrower-a`) is passed for the demo.

### Pickup code delivery (Gmail)

When staff load an item, the borrower's one-time pickup code is emailed to them through the **Gmail 1P connector** — it is never returned to the chat agent. The borrower enters that code on the locker screen to open the compartment.

- **To:** the borrower's email.
- **Subject:** `Your pickup code for {asset_name}`
- **Body:** the code, the compartment, and the valid-from time.

Open item: the chat-safe `check_pickup_status` tool hides the code by design, so delivering it needs a **staff/workflow-scoped** code lookup (a small added MCP tool, or a step in the load action). Until that exists, read the code locally from the borrower's `/pickups` status (it would be emailed in production). See the student flow in [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

## 3. Maximizing workflow

**Name:** `overdue-recovery`
**Schedule:** daily (the maximizing pattern). For the demo, trigger a run on demand after advancing the test clock — see [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

**Steps:**

1. **Call** `run_overdue_recovery` (MCP). It returns `overdue_loans`, `at_risk_reservations`, `substitution_proposals`, and `escalations`.
2. **Condition:** continue only if `substitution_proposals` or `escalations` is non-empty.
3. **For each `substitution_proposals` item**, draft the proposal email (below) in Gmail.
4. **For each `escalations` item**, draft the escalation email (below) in Gmail.
5. **Approval step** routed to `<STAFF_EMAIL>`. On approve, send or log the simulated notification. On reject, do nothing.
6. Label every action **simulated**. The booking is not changed here; applying a substitute is Stage 2.1 on the locker page.

### Proposal email

- **To:** `<STAFF_EMAIL>`
- **Subject:** `Action needed: substitute ready for booking {reservation_id}`
- **Body:**

```
A loaned item is overdue and threatens an upcoming booking. A verified substitute is ready.

Overdue loan: {overdue_loan_id} (asset {original_asset_id})
Threatened booking: {reservation_id}
Proposed substitute: {substitute_asset_id}
Requirements: {requirements}

Approve to notify the borrower and let staff apply the substitute on the locker page.
This message is simulated for the prototype.
```

Field map: `overdue_loan_id` = `overdue_loans[].id`; `original_asset_id`, `reservation_id`, `substitute_asset_id`, and `requirements` come from the matching `substitution_proposals[]` item.

### Escalation email

- **To:** `<STAFF_EMAIL>`
- **Subject:** `Action needed: no substitute for booking {reservation_id}`
- **Body:**

```
A loaned item is overdue and threatens an upcoming booking. No substitute is available.

Overdue loan: {overdue_loan_id} (asset {original_asset_id})
Threatened booking: {reservation_id}
Requirements: {requirements}
Owner: {owner}

Staff action is needed. This message is simulated for the prototype.
```

Field map: values come from the matching `escalations[]` item (`reservation_id`, `owner`, `requirements`); `overdue_loan_id` and `original_asset_id` come from `overdue_loans[]`.

## 4. Assembly checklist

1. Create the app; enable chat agents and workflows.
2. Deploy the MCP connector (items 2/5 of the readiness plan) and register it as the third-party connector with `<MCP_URL>`.
3. Configure the Gmail connector.
4. Build the chat agent: name, four borrower tools, the instruction above, Flash.
5. Build the workflow: the steps above, both email templates, approval to `<STAFF_EMAIL>`, Flash.
6. Run both demo scenarios from [DEMO_SCRIPT.md](DEMO_SCRIPT.md) and record the video.

## Blocked on the licence

Building the agent and workflow in Gemini Enterprise, hosting the connector, and the full round-trip are Stage 1.5. This sheet is ready to execute the moment the licence and a connector host exist.
