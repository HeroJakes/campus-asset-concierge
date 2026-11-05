# Stage 1.3 — Return equipment

A borrower returns an open loan into the virtual locker with a one-time return code. Staff then retrieve the item and run a condition check. A passing item becomes available again; a failing item is closed as returned and put on condition hold. This stage starts from an active loan from Stage 1.2 (or an overdue loan from Stage 1.4) and ends with a closed loan.

Return uses a locker drop-off that mirrors Stage 1.2 pickup, rather than a direct staff hand-off at the desk. See [ADR 0001](adr/0001-return-uses-locker-drop-off.md) for why.

## Flow

| Step | Who | Loan | Compartment | Return record |
| --- | --- | --- | --- | --- |
| Start | — | `active` or `overdue` | `empty` | none — item is with the borrower |
| Request return | Borrower | unchanged | `return_reserved` | created with a code and `issued_at` |
| Enter code | Borrower | unchanged | `unlocked` | `used_at` set |
| Confirm drop | Borrower | `awaiting_check` | `returned` | `dropped_at` set |
| Verify return — pass | Staff | `returned` | `empty` | `checked_at` set; asset stays `good`, unit available |
| Verify return — fail | Staff | `returned` | `empty` | `checked_at` set; asset set to `hold`, unit unavailable |

Keep the loan open (`active`/`overdue`) until the borrower confirms the drop. Only then does it become `awaiting_check`. The unit must stay unavailable from the moment a return is requested until the check finishes or the request is reclaimed (see below).

## Data records

Returns need their own record, because Stage 1.2's view layer is keyed by `reservation_id` (`_reservation`, `_view`, `_borrower_views` in `pickups.py`) and the seeded overdue-demo loan `active-projector` (`scenarios.py`) has **no reservation**. Routing returns through the reservation-keyed path would drop that loan.

Store a `return_access` map in the state document, **keyed by `asset_id`** (one open return per asset — see below):

```text
return_access[asset_id] = {
    "loan_id":      <the open loan's id, e.g. "active-projector" or "loan-<reservation_id>">,
    "borrower_id":  <owner of the loan>,
    "code":         <6-digit plain-text code>,
    "compartment":  <"a1" | "a2">,
    "issued_at":    <datetime the code was created>,
    "failed_tries": <int>,
    "used_at":      <datetime the code was entered, or null>,
    "dropped_at":   <datetime the drop was confirmed, or null>,
    "checked_at":   <datetime staff verified, or null>,
}
```

Build the borrower's return view and the staff view **from `return_access` and the loans**, keyed by asset, not from reservations. Do not reuse the reservation-keyed `_view`/`_borrower_views` for returns.

## Address returns by asset

A borrower returns a specific physical unit, so address every return action by `asset_id`. Inside the transaction, find the asset's one open loan — status `active`, `overdue`, or `awaiting_check`. There is at most one open loan per asset, but this is an **invariant maintained by guards** (`_check_can_load` rejects loading a unit with a non-`returned` loan; `eligible_unit` blocks overlaps), not a structural constraint. Make the find deterministic (first open loan for the asset) so a future violation fails predictably rather than picking at random, and treat "no open loan" as a 404.

## Request return and the return code

- Only the borrower who holds the open loan can request its return.
- Create a 6-digit code with Python's `secrets` module, before the Firestore transaction, as `offer` and `load` do, because a transaction can run more than once.
- Reject or short-circuit the request in these cases:
  - The asset has no open loan for this borrower → 404.
  - The loan is already `returned` → 409.
  - A **live** return is already in progress for this asset (a `return_access` record exists whose `dropped_at` is null and whose code has not expired) → **return the existing code and compartment**, do not allocate a second one. This keeps a repeated request idempotent before the drop, the way `load()` guards with `if reservation_id not in access_records`.
  - The loan is already `awaiting_check` (item dropped, waiting for staff) → return the existing record's view.
  - No compartment is free → 409, loan unchanged, borrower keeps the item.
- When allocating: pick the first free compartment (see reclaim), set it to `return_reserved`, and write the `return_access` record with `issued_at = local_clock(state)`.
- The code is stored as plain text, in `return_access`, separate from the reservation and the loan. Add a `shortcut:` comment saying this suits fictional local data only and must change before real use.
- Show the code only to the signed-in borrower on their locker page, labelled as simulated.
- The code works from `issued_at` until 30 minutes later, measured with `local_clock`. There is no "not open yet" gate — unlike pickup, a return code is usable the moment it is issued, because there is no future pickup time to wait for.

## Enter code and confirm drop

- Enter code and confirm drop are two borrower steps, mirroring Stage 1.2 unlock and pickup.
- Reject a code that is wrong, belongs to another borrower, has expired (`now > issued_at + 30 min`), or has already been used.
  - Compare codes with `compare_digest`.
  - Five wrong tries blocks the code (reuse `MAX_WRONG_TRIES`).
  - A wrong try must still save the try count. As in Stage 1.2 unlock, save the count inside the transaction and raise the error **after** it finishes, because `LocalStateStore.change` discards all changes when the function raises.
  - Keep a wrong-user try out of the count, so one borrower cannot block another's code.
- Entering the code sets the compartment to `unlocked` and `used_at` on the record.
- Confirm drop sets the loan to `awaiting_check`, the compartment to `returned`, and `dropped_at` on the record. Only the borrower who unlocked it can confirm the drop.
- A repeated drop returns the same state and never creates a second record.

## Verify return (staff)

- Only staff can verify a return.
- Verify takes a result of `pass` or `fail` and is rejected unless the loan is `awaiting_check`.
- On `pass`: set the loan to `returned`, set `checked_at`, empty the compartment, leave the asset condition `good`. The unit is bookable again.
- On `fail`: set the loan to `returned`, set `checked_at`, empty the compartment, set the asset condition to `hold`. The unit stays unavailable. There is no release path in P0; un-hold and repair belong to Stage 3.2.
- Use the loan's existing id, so a repeated verify returns the same closed loan and never flips the condition twice.

## Keeping the unit unavailable

`eligible_unit` today blocks a unit only on an `active` or `overdue` loan, and the `active` check is **window-scoped** (`loan["due_at"] < now or pickup < loan["due_at"]`). That leaves a hole: once a return is requested but not yet dropped, the loan is still `active`, so a booking for a window starting after `due_at` would be offered for a unit that is mid-return. Close it with two additions to `eligible_unit`:

1. Block the unit **unconditionally** (not window-scoped) when its open loan is `awaiting_check`, the same way `overdue` is blocked.
2. Block the unit when a **live `return_access` record** exists for it (code issued, `dropped_at` null, not expired) — the item is already on its way back and must not be offered to anyone else.

A `fail` keeps the unit out through its `hold` condition. A `pass` clears both the loan and the record, so the unit returns to circulation.

## Compartment reclaim

There is no background job, and `local_clock` is lazy, so an abandoned return (requested, or unlocked, but never dropped) would strand a compartment forever. Reclaim lazily: a compartment counts as **free** when its `return_access` record has `dropped_at == null` and the code has expired (`now > issued_at + 30 min`). Apply this rule in the one place that chooses a free compartment and in the full-locker check, so an expired, undropped return releases its slot the next time any borrower requests a return. This covers both the never-unlocked and the unlocked-but-never-dropped cases with one condition.

## Audit events

Record `return_requested`, `return_unlocked`, `returned_dropped`, `return_passed`, `return_failed`, and a `return_code_wrong` try.

The Stage 1.2 `_audit(state, now, actor, action, reservation_id)` has a required `reservation_id` and no asset. Returns are addressed by asset and the seeded loan has no reservation, so:

- Extend `_audit` to take `asset_id` and make `reservation_id` optional (default null).
- Pass `asset_id` on **every** audit call, including the five existing Stage 1.2 call sites, so the shared format is uniform rather than split between stages.
- A return action logs `asset_id` and a null `reservation_id`.

This changes the shared audit format, so agree it with C and D before coding.

## Screens and tools

- Extend the `/locker` page:
  - A borrower sees a **Return** action for each of their open loans, then the return code and the enter-code and confirm-drop steps, built from `return_access` (asset-keyed), not from the reservation list.
  - Staff see items sitting in compartments awaiting a check, with **Verify return — Pass** and **Verify return — Fail** actions.
- Fix the template for the new data, or it will break:
  - `locker.html` renders `{{ event.reservation_id[-8:] }}`; with a null `reservation_id` this raises `TypeError`. Guard it, and show the `asset_id` for return events.
  - The booking-step label map uses a hard `[booking.step]` subscript, and the audit-action map covers only pickup actions. Add the return steps and actions, or fall back to a safe default, so a new string does not raise.
  - The staff compartment-occupant lookup matches a *reservation* to a compartment; a reservation-less return shows a blank label and unstyled state. Resolve the occupant from `return_access` too, and style the `return_reserved`/`returned` compartment states.
- Extend the read-only ADK tool so a borrower can see a loan's return progress. It never returns the code. Test it directly, as Stage 1.1 and 1.2 do.
- The backend checks every action against the signed-in role and the loan owner.

## Build and verify

Test these cases against the Firestore emulator:

- The full flow from an active loan to a passed return and an available unit.
- A failed return putting the unit on hold and out of new offers.
- Returning an `overdue` loan after advancing the clock.
- Non-borrower requesting, unlocking, or dropping; non-staff verifying; a borrower acting on another borrower's loan.
- Return code wrong, wrong user, expired after 30 minutes, and already used.
- A code blocked after five wrong tries, with the count saved.
- Request rejected when both compartments are full.
- **A repeated request before the drop returns the same code and compartment** (no second compartment taken).
- **An expired, undropped return frees its compartment** for the next request.
- **A unit mid-return (code issued, not dropped) is not offered** for a later window — the in-progress-return block in `eligible_unit`.
- Repeated drop and repeated verify creating no duplicate loans or holds.
- The unit staying out of new offers while `awaiting_check`, then available again after a pass.
- The code staying out of `GET /reservations`, the borrower pickup view, and the ADK tool.
- The seeded `active-projector` loan, which has no reservation, returning by asset id end to end.
- **A return audit event (null `reservation_id`) renders on the staff page without error**, and staff can see what sits in a return compartment.

Projector A is seeded on an active loan, so it is the natural unit to return. Stage 1.4 needs Projector A to go overdue for its own demo, so return and overdue are separate demo paths on the same seeded unit.

## To confirm with the team

- **Audit format:** adding `asset_id` to every event and allowing a null `reservation_id` changes the Stage 1.2 format. Agree it with C and D, and update their call sites in the same change.
- **At-risk reservations:** check with D whether returning an overdue unit should clear the at-risk flag Stage 1.4 sets, or whether that stays Stage 1.4's job.
- **Locker contention:** return shares the two compartments with pickup loading. Confirm the team is fine demoing with this limit; a waitlist is later work.

Un-hold and repair, partial or graded condition, missing items, a waitlist for a full locker, and return through chat are out of scope for this stage.
