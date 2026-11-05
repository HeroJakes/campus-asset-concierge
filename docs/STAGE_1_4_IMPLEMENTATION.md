# Stage 1.4 implementation · Overdue recovery

## Scope

Stage 1.4 detects a late active loan when the local test clock advances. It keeps the loan overdue, flags the next confirmed booking for the same asset, queues one simulated reminder, and records one P0 outcome:

- a verified substitute proposal when another unit passes the existing booking eligibility rules; or
- an open escalation owned by equipment staff when no substitute passes those rules.

The original reservation remains assigned to its original asset and remains `confirmed`. Applying a proposal is Stage 2.1 and is not part of this implementation.

## State records

Recovery stores records in the shared local Firestore document:

- `reminders` is keyed by `overdue-{loan_id}` and records a queued, simulated reminder.
- `at_risk_reservations` is keyed by reservation ID and records the overdue loan that threatens it.
- `substitution_proposals` is keyed by reservation ID and records a verified proposal with `pending_staff_approval` status.
- `escalations` is keyed by reservation ID and records an open escalation with `equipment-staff` as owner.

Recovery also appends the existing audit-event shape. The recovery actions are `overdue_marked`, `reminder_queued`, `booking_at_risk`, `substitute_proposed`, and `escalation_created`.

## Trigger and idempotency

`POST /local-test/clock/advance` runs the recovery pass after advancing the clock. The pass uses `LocalStateStore.change()` and stable record IDs. Repeating the clock advance or recovery pass does not create duplicate records or audit events. A loan changes from `active` to `overdue` only when the local clock is past its due time.

The current P0 implementation performs the clock update and recovery in two local transactions. Recovery records are retry-safe, and the local operator endpoint is the only clock mutation surface.

## Substitute verification

For the next confirmed booking, recovery checks every other asset in stable ID order with `domain.reservations.eligible_unit()`. This applies the same condition, loan, pickup-access, and overlapping-reservation checks used by booking. A proposal records the original asset, substitute asset, verification time, and `verified: true`; it does not change the reservation.

## Staff surfaces

Staff can read `GET /recovery` and see the same records in the staff locker page at `/locker`. The locker page labels reminders as simulated and proposals as awaiting staff approval. Borrowers and local operators cannot read the staff recovery endpoint.

## Acceptance checks

With the Firestore emulator running:

```powershell
$env:FIRESTORE_EMULATOR_HOST = '127.0.0.1:8080'
uv run --locked pytest tests/test_recovery.py
uv run --locked pytest
```

Reset `spare_available`, advance 61 minutes, and show the verified Projector B proposal. Reset `spare_unavailable`, advance 61 minutes, and show the staff-owned escalation. In both cases, the Projector A loan is overdue and the original next booking remains confirmed and assigned to Projector A.
