# Stage 2.1 — Approve and apply a reassignment

**Status:** Done locally. PR #10 merged into `main`.

## Scope

Stage 2.1 takes the verified substitution proposal created by Stage 1.4 and lets an equipment staff account apply it. The first version supports one proposal at a time and changes only the threatened future reservation. The overdue loan remains open and overdue for staff follow-up.

This implementation assumes P0 recovery has already created a proposal with `pending_staff_approval` status. It does not add borrower notifications, proposal rejection, richer matching, or scheduled recovery.

## Approval contract

Staff approve a proposal with:

```text
POST /recovery/substitution-proposals/{reservation_id}/approve
```

The endpoint requires the `staff` role. Borrowers and local operators receive `403`.

A successful response contains the applied proposal, the updated reservation, and the audit event. Approval is idempotent: repeating the request for an already applied proposal returns the same applied result and does not add another audit event.

## Transaction and revalidation rules

The approval service runs all checks and writes through one `LocalStateStore.change()` transaction:

1. Find the proposal and require `pending_staff_approval`, unless it is already `applied`.
2. Require the reservation to still be `confirmed` and assigned to the proposal's original asset.
3. Recheck the substitute with the shared `eligible_unit()` policy and the current local clock.
4. Change the reservation's `asset_id` to the substitute.
5. Mark the proposal `applied`, recording `approved_by` and `applied_at`.
6. Append one `substitution_applied` audit event with the original and substitute asset IDs.

If the reservation or substitute is no longer valid, the transaction returns `409` and leaves both the reservation and proposal unchanged. A staff member can inspect or resolve the still-pending proposal rather than silently applying a stale reassignment.

The existing pickup-access record is not migrated because Stage 1.4 proposals target future, confirmed reservations before loading. If a reservation has already entered a pickup workflow, the confirmation check rejects the reassignment instead of leaving a compartment record pointing at the wrong asset.

## Staff reporting

`GET /recovery` includes the recovery records and the reverse-chronological `audit_events` list. The staff locker page uses the same data and shows the approval action while a proposal is pending, then shows the applied substitute and approving staff account after success. The general staff activity list also labels `substitution_applied` events.

## Acceptance checks

With the Firestore emulator running:

```powershell
$env:FIRESTORE_EMULATOR_HOST = '127.0.0.1:8080'
uv run --locked pytest
```

Manual acceptance:

1. Reset `spare_available` and advance the local clock 61 minutes.
2. Confirm that `next-projector` has a verified pending proposal for `projector-b` and remains assigned to `projector-a`.
3. Approve the proposal as `equipment-staff`.
4. Confirm that the reservation is confirmed and assigned to `projector-b`, the proposal is `applied`, and one `substitution_applied` audit event appears in `GET /recovery` and `/locker`.
5. Confirm that `active-projector` remains overdue.
6. Repeat approval and confirm that the reservation and audit-event count do not change.
7. Make `projector-b` unavailable between proposal creation and approval. Confirm that approval returns `409` and leaves the proposal pending and reservation unchanged.
