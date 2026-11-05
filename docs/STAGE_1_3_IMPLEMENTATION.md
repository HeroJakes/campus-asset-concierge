# Stage 1.3 — Return equipment

A borrower returns an open loan into the virtual locker with a one-time return code. Staff then retrieve the item and run a condition check. A passing item becomes available again; a failing item is closed as returned and put on condition hold. This stage starts from an active loan from Stage 1.2 (or an overdue loan from Stage 1.4) and ends with a closed loan.

Return uses a locker drop-off that mirrors Stage 1.2 pickup, rather than a direct staff hand-off at the desk. See [ADR 0001](adr/0001-return-uses-locker-drop-off.md) for why.

## Flow

| Step | Who | Loan | Compartment | Other records |
| --- | --- | --- | --- | --- |
| Start | — | `active` or `overdue` | `empty` | Item is with the borrower |
| Request return | Borrower | unchanged | `return_reserved` | Return code created |
| Enter code | Borrower | unchanged | `unlocked` | Code marked as used |
| Confirm drop | Borrower | `awaiting_check` | `returned` | Item is in the compartment |
| Verify return — pass | Staff | `returned` | `empty` | Asset condition stays `good`, unit available |
| Verify return — fail | Staff | `returned` | `empty` | Asset condition set to `hold`, unit unavailable |

Keep the loan open (`active`/`overdue`) until the borrower confirms the drop. Only then does it become `awaiting_check`. The asset must stay unavailable from the moment the item is dropped until the check finishes.

## Address returns by asset

A borrower returns a specific physical unit, and there is at most one open loan per asset, so address every return action by `asset_id`. This also handles the seeded overdue-demo loan `active-projector`, which has no backing reservation and so cannot be addressed by reservation id. Find the asset's one open loan (`active`, `overdue`, or `awaiting_check`) inside the transaction.

## Request return and the return code

- Only the borrower who holds the open loan can request its return.
- Reject the request in these cases:
  - The asset has no open loan for this borrower.
  - The loan is already `awaiting_check` (return already in progress) — return the existing code and compartment instead of a new one.
  - The loan is already `returned`.
  - Both compartments are full. The loan stays unchanged and the borrower keeps the item.
- Create a 6-digit code with Python's `secrets` module, before the Firestore transaction, as `offer` and `load` do, because a transaction can run more than once.
- The system picks the first empty compartment and sets it to `return_reserved`.
- The code is stored as plain text in its own record, separate from the reservation and the loan. Add a `shortcut:` comment saying this suits fictional local data only and must change before real use.
- Show the code only to the signed-in borrower on their locker page, and label the delivery as simulated.
- The code works from the moment it is issued until 30 minutes later, measured with `local_clock`. On expiry, free the compartment so the borrower can request again. No reissue beyond re-requesting in P0.

## Enter code and confirm drop

- Enter code and confirm drop are two borrower steps, mirroring Stage 1.2 unlock and pickup.
- Reject a code that is wrong, belongs to another borrower, has expired, or has already been used.
  - Compare codes with `compare_digest`.
  - Five wrong tries blocks the code (reuse `MAX_WRONG_TRIES`).
  - A wrong try must still save the try count. As in Stage 1.2 unlock, save the count inside the transaction and raise the error after it finishes, because `LocalStateStore.change` discards all changes when the function raises.
  - Keep a wrong-user try out of the count, so one borrower cannot block another's code.
- Entering the code sets the compartment to `unlocked` and marks the code used.
- Confirm drop sets the loan to `awaiting_check` and the compartment to `returned`. Only the borrower who unlocked it can confirm the drop.
- A repeated drop returns the same state and never creates a second record.

## Verify return (staff)

- Only staff can verify a return.
- Verify takes a result of `pass` or `fail`.
- Verify is rejected unless the loan is `awaiting_check`.
- On `pass`: set the loan to `returned`, empty the compartment, leave the asset condition `good`. The unit is available for new bookings again.
- On `fail`: set the loan to `returned`, empty the compartment, set the asset condition to `hold`. The unit stays unavailable. There is no release path in P0; un-hold and repair belong to Stage 3.2.
- Use the loan's existing id, so a repeated verify returns the same closed loan and never flips the condition twice.

## Keeping the unit unavailable

`eligible_unit` today blocks a unit on an `active` or `overdue` loan. Extend it to also block a unit whose open loan is `awaiting_check`, so a dropped-but-unchecked unit cannot be booked. A `fail` already blocks the unit through its `hold` condition. A `pass` leaves no blocker, so the unit returns to circulation.

## Audit events

Record `return_requested`, `return_unlocked`, `returned_dropped`, `return_passed`, and `return_failed`, plus a `return_code_wrong` try. Reuse the Stage 1.2 format but **add `asset_id`**, because the seeded loan has no reservation id. `reservation_id` may be null for a return action. This extends the shared audit format, so agree it with C and D.

## Screens and tools

- Extend the `/locker` page. A borrower sees a **Return** action for each of their open loans, then the return code and the enter-code and confirm-drop steps, reusing the Stage 1.2 code-entry pattern. Staff see items sitting in compartments awaiting a check, with **Verify return — Pass** and **Verify return — Fail** actions.
- Extend the read-only ADK tool so a borrower can see a loan's return progress. It never returns the code. Test it directly, as Stage 1.1 and 1.2 do.
- The backend checks every action against the signed-in role and loan owner.

## Build and verify

Test these cases against the Firestore emulator:

- The full flow from an active loan to a passed return and an available unit.
- A failed return putting the unit on hold and out of new offers.
- Returning an `overdue` loan after advancing the clock.
- Non-borrower requesting, unlocking, or dropping; non-staff verifying; a borrower acting on another borrower's loan.
- Return code wrong, wrong user, expired after 30 minutes, and already used.
- A code blocked after five wrong tries, with the count saved.
- Request rejected when both compartments are full.
- Repeated request, drop, and verify creating no duplicate loans or holds.
- The unit staying out of new offers while `awaiting_check`, then available again after a pass.
- The code staying out of `GET /reservations`, the borrower pickup view, and the ADK tool.
- The seeded `active-projector` loan, which has no reservation, returning by asset id.

Projector A is seeded on an active loan, so it is the natural unit to return. Stage 1.4 needs Projector A to go overdue for its own demo, so return and overdue are separate demo paths on the same seeded unit.

## To confirm with the team

- **Audit format:** adding `asset_id` and allowing a null `reservation_id` changes the shared format from Stage 1.2. Agree it with C and D.
- **At-risk reservations:** check with D whether returning an overdue unit should clear the at-risk flag Stage 1.4 sets, or whether that stays Stage 1.4's job.
- **Locker contention:** return shares the two compartments with pickup loading. Confirm the team is fine demoing with this limit; a waitlist is later work.

Un-hold and repair, partial or graded condition, missing items, a waitlist for a full locker, and return through chat are out of scope for this stage.
