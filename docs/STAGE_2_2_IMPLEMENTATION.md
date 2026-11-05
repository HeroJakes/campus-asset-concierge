# Stage 2.2 — Richer equipment matching

**Status:** Implemented locally. Teammate review pending in PR #12.

Stage 2.1 is merged in PR #10. This plan records the agreed interview decisions and extends its matching rules using terms in the [glossary](../GLOSSARY.md). It covers local development only.

## Result

A borrower can ask for a projector with HDMI, built-in speakers, or both. Booking and overdue recovery select only units that meet the stated needs. Those needs stay attached to the reservation when staff approve a substitute.

For example, a borrower requests HDMI and speakers. An available projector with HDMI but no speakers must not be offered or proposed. If no suitable substitute exists, recovery creates a staff-owned escalation.

## Scope and rules

- Support HDMI and built-in speakers for projectors only. Raspberry Pi kits retain category-only matching.
- Requirements are optional. Omitted or false means the capability is not required; it does not mean the asset must lack it.
- Every required capability must be explicitly recorded as present on the asset. Missing specifications cannot satisfy a requirement.
- Existing bookings and offers without requirements retain category-only matching. Never infer requirements from the assigned asset.
- Keep the current condition, loan, locker, time-window, and overlapping-reservation rules. Requirements add checks; they do not replace availability checks.
- Choose the first suitable unit in the existing sorted asset-ID order. Offers and proposals do not hold inventory.
- Recheck saved requirements against current asset specifications at confirmation and reassignment approval. A failed check returns a conflict without changing the reservation.
- Chat captures needs the borrower mentions. It does not always ask about both capabilities. Show the requirements before requesting confirmation.
- Add a staff-only action to check substitutes again for a pending proposal. It cannot apply a substitute automatically.

Defer numeric matching, ranked recommendations, multiple choices, bundles, more locations, waitlists, QR pickup, scheduling, real notifications, and cloud deployment. Do not add an asset-specification editing screen or endpoint.

## Request and stored data

Extend `ReservationRequest` with two optional fields, both strict booleans with a default of `false`:

```json
{
  "category": "projector",
  "pickup_at": "2026-11-07T12:00",
  "duration_minutes": 60,
  "require_hdmi": true,
  "require_built_in_speakers": true
}
```

Reject strings, numbers, and null for these fields with `422`. Reject a true projector requirement for a Raspberry Pi kit with `422`; both false remains a valid category-only request. Continue rejecting unknown request fields.

Store both requirement fields on new offers and copy them unchanged to confirmed reservations. Read absent fields on older records as false. There is no requirements-editing operation in this stage; a borrower changing their needs requests a new offer and confirms it.

Projector assets gain `has_hdmi` and `has_built_in_speakers` boolean specifications. Missing fields mean unknown. Requirement checks must use an explicit true value, not general truthiness.

Keep category fallback for seeded reservations: these currently omit `category`, so recovery and reassignment can still obtain it from the original asset. Requirements always come from the reservation, never from that asset.

## Shared matching and booking

Extend the existing `domain/reservations.py:eligible_unit()` with the two requirement arguments, defaulting to false for compatibility. Keep capability checks in this shared function so booking, recovery, and approval use the same rule.

- `Reservations.offer()` passes validated request requirements and saves them with the offered unit.
- `Reservations.confirm()` passes the saved offer requirements in its existing transaction. Never silently switch the offered unit if it fails.
- `Reservations.preview()` includes the saved requirements for confirmation text.
- `Recovery.process()` passes reservation requirements when selecting a substitute.
- `Reassignment.approve()` passes reservation requirements when rechecking the substitute. Applying it changes the asset ID while retaining the requirements and existing loan and audit behavior.

Reuse the existing sorted candidate scan. Share the recovery outcome selection between normal recovery and the new staff action; do not copy the proposal/escalation logic into another service.

## Checking substitutes again

Add `Recovery.recheck(staff_id, reservation_id)` and this local staff endpoint:

```text
POST /recovery/substitution-proposals/{reservation_id}/recheck
```

Run validation and all writes in one `LocalStateStore.change()` transaction:

1. Require an existing pending proposal (`404` if absent, `409` if already applied or otherwise not pending).
2. Require the same original confirmed reservation, no pickup access record, a pickup time not before the local clock, and an overdue original loan that still threatens that reservation. Otherwise return `409` without writes.
3. Recheck current stock and saved requirements. Exclude the original asset and use the shared matching rule in sorted asset-ID order.
4. If the selected unit and saved requirements are unchanged, retain the existing proposal and return it. Do not add an audit event just for a repeated click.
5. If the selected unit changes, replace the pending proposal with a newly identified, verified proposal. Record the previous and new proposal and substitute IDs in one `substitute_rechecked` audit event, including the staff actor and time.
6. If no unit qualifies, remove the pending proposal and create the usual staff-owned escalation. Record the retired proposal ID and former substitute in the recheck audit event; retain the at-risk flag and original overdue loan. A repeat request then returns `404` because there is no pending proposal.

The response contains the current proposal or escalation and the reservation, with the existing Malaysia-time serialization. Only equipment staff can call this endpoint. Borrowers and local operators receive `403`; unauthenticated callers receive `401`.

Normal recovery remains retry-safe and does not automatically replace existing outcomes. Keep applied proposals intact. Reopening escalations is outside this first scope.

### Prevent approval of a replaced proposal

A staff member may have an older locker page open when another staff member checks substitutes again. The approval must identify the proposal that was actually shown, rather than approve whichever proposal now belongs to the reservation.

Keep the existing approval URL, but require a body containing `proposal_id`:

```json
{"proposal_id": "the-id-returned-with-the-proposal"}
```

Give changed proposals a fresh ID. In the approval transaction, compare the submitted ID with the stored proposal before applying or returning an already-applied result. A different ID returns `409`; the user must refresh and review the replacement. A repeated approval of the same applied proposal remains idempotent. Require a nonempty strict string; a missing body or invalid ID value returns `422`.

This changes the local approval request contract. Update the locker button, API model, service callers, tests, README instructions, and Stage 2.1 doc together. Do not leave a path that approves a replacement without its ID.

## API, agent tools, and displays

| Surface | Change |
| --- | --- |
| `POST /reservation-offers` | Accept and validate optional requirement fields through `ReservationRequest` |
| Offer, preview, confirmation, and `GET /reservations` | Return saved requirements; old records remain readable |
| ADK and MCP `find_equipment` | Add the same optional boolean arguments and pass them through the existing model validation |
| ADK confirmation and booking instructions | State required capabilities or “No extra requirements”; keep explicit borrower confirmation |
| MCP confirmation | Keep the existing `offer_id` contract; confirm the saved offer requirements |
| Recovery API and MCP recovery result | Include reservation requirements with proposals and escalations so staff can understand the outcome |
| Pickup views and `/locker` | Carry requirements from the reservation into borrower and staff views; share one template macro for the requirement text |
| Staff proposal display | Show requirements, existing approval action with the displayed proposal ID, and “Check substitutes again” for pending proposals |
| Staff activity | Label `substitute_rechecked` and retain existing audit actions |

Reuse `locker.js`'s existing `data-post` and `data-body` support for both staff buttons. No new JavaScript transport is needed. Keep the error alert and keyboard-accessible buttons.

Keep locker codes out of agent and MCP status results. The new staff action is available only through the authenticated local API and locker page, not the unauthenticated MCP connector. Gemini hosting and trusted identity binding remain Stage 1.5 work.

## Fictional fixtures and rehearsal

Add simple specifications to the existing projector fixtures: Projector A has HDMI and speakers; Projector B has HDMI but no speakers. Leave existing seeded bookings without requirements so both current reset scenarios keep their behavior.

Use test-specific copies of the existing fixture to cover missing specifications, another suitable projector, and changed specifications. Do not add more reset modes or a general inventory editor.

Manual rehearsal after implementation:

1. Reset `spare_available` at 10:00 MYT. As borrower B, offer and confirm a projector from 13:00 to 14:00 requiring HDMI and speakers. Projector A qualifies after the seeded next booking ends at 13:00; B does not meet the speaker requirement.
2. Advance 61 minutes. Recovery first protects the seeded 12:00 booking. Approve that proposal as staff, moving the seeded booking to Projector B.
3. Advance one more minute to run recovery again. The new 13:00 booking is now the next threatened booking on Projector A. Show its staff-owned escalation: Projector B lacks speakers even though its booking ends at 13:00.
4. Reset and repeat with HDMI required and speakers not required. After approving the seeded proposal and running recovery again, the 13:00 booking can receive a Projector B proposal.
5. On that pending proposal, select “Check substitutes again.” Unchanged stock retains the proposal; approve it and show that the reservation keeps its saved requirements while the original loan remains overdue.

Changed-stock and replacement-proposal paths use controlled test fixtures. The manual demo does not need a new data-editing interface.

## Implementation order

1. Add strict request fields, asset specifications, saved requirements, and shared eligibility checks. Cover no-requirement compatibility and both capability checks.
2. Wire requirements through booking, recovery, and reassignment. Extend transaction tests for changed specifications and preservation of requirements.
3. Add the staff recheck transaction, audit event, proposal-specific approval body, and authorization checks. Test stale pages and concurrent approval/recheck before adding the button.
4. Update ADK/MCP tools, instructions, confirmation text, and shared locker displays. Reuse current validation and browser action handling.
5. Update README demo steps, Stage 2.1 approval contract, MCP and Gemini tool plans, and the stage board. Mark Stage 2.2 done only after validation and teammate review.

## Acceptance checks

Use the current pytest fixtures and Firestore emulator. Add focused cases to the existing test modules rather than a parallel test harness.

Extend `test_reservations.py`, `test_recovery.py`, `test_reassignment.py`, `test_agent_reservations.py`, and `test_mcp_server.py` for their respective flows. Add requirement-display assertions to `test_pickups.py`; keep `test_returns.py` and `test_local_foundation.py` in the full regression run.

| Area | Required evidence |
| --- | --- |
| Inputs | Omitted and false flags work; non-booleans, unknown fields, and true projector requirements on kits return `422` |
| Matching | HDMI-only, speakers-only, and both-required requests choose suitable units; false does not exclude extra capabilities; unknown cannot satisfy true; stable ordering holds |
| Compatibility | Old offers and seeded bookings still confirm/recover; existing spare-available and spare-unavailable scenarios retain their outcomes |
| Booking transactions | Requirements persist; changed capability or stock causes `409` without reservation writes; last-unit competition still has one winner |
| Recovery | Suitable proposals include requirements; a capability mismatch produces an escalation; repeated processing does not duplicate outcomes or reminders |
| Reassignment | Staff approval rechecks capabilities, retains requirements, clears the at-risk flag, keeps the original loan overdue, and writes one application event |
| Recheck | Same result is a no-op; changed candidate replaces only the pending proposal; no match creates an escalation; invalid booking, loan, pickup state, or applied proposal is rejected without writes |
| Stale and concurrent actions | Old proposal IDs cannot approve replacements; repeated approval of the same ID succeeds without another event; racing approval/recheck cannot overwrite an applied proposal or move a booking to an unreviewed unit |
| Roles | Recheck and approval reject unauthenticated callers, borrowers, and operators using existing authentication behavior |
| Tools and views | ADK/MCP pass flags and return validation errors; confirmation shows needs; locker shows needs and pending-only recheck; code privacy remains intact |

Run focused tests during implementation, then the existing full suite:

```powershell
$env:FIRESTORE_EMULATOR_HOST = '127.0.0.1:8080'
uv run --locked pytest
```

Run against the local emulator and fictional data only. `uv sync --locked` restores the pinned environment when needed. Focused API, recovery, reassignment, tool, and locker-view tests cover the checks above; the full suite is the final regression check.

Local verification on 2026-11-05: all 122 tests passed against the Firestore emulator, including both rehearsal outcomes and changed-stock approval/recheck races. Python compilation and Git whitespace checks passed. Independent standards and spec reviews found repeated applicability checks and a missing changed-stock race test; both were fixed. No static type checker is configured. Live Gemini chat and a visual browser rehearsal remain unverified.

## Completion and limits

Finish when the acceptance checks pass, both existing reset scenarios still work, the new rehearsal demonstrates capability-based matching, and a teammate reviews the implementation PR.

No new dependency or database service is needed. The user authorized implementation on the existing `docs/stage-2-2-planning` branch and PR #12. Cloud deployment remains out of scope.

Keep the existing recovery limits explicit: only the next future booking is considered, proposals do not reserve units, and separate pending proposals can compete for a spare. Transaction-time approval must still prevent overlapping applied reservations. This stage does not add global allocation or process bookings skipped by a clock jump.
