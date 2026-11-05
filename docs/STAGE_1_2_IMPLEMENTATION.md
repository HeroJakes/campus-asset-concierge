# Stage 1.2 — Load and collect equipment

Staff load a reserved item into the virtual locker. The borrower then unlocks the compartment with a one-time code and confirms pickup, which starts the loan. This stage starts from a confirmed reservation from Stage 1.1 and ends with an active loan for Stage 1.3 and Stage 1.4.

## Flow

| Step | Who | Reservation | Compartment | Other records |
| --- | --- | --- | --- | --- |
| Start | — | `confirmed` | `empty` | — |
| Confirm loading | Staff | `ready_for_pickup` | `loaded` | One-time code created |
| Enter code | Borrower | `ready_for_pickup` | `unlocked` | Code marked as used |
| Confirm pickup | Borrower | `collected` | `empty` | Loan created as `active` |

Keep the reservation as `ready_for_pickup` until pickup. `eligible_unit` only treats `confirmed` and `ready_for_pickup` bookings as holding a unit, so a new `unlocked` reservation status would let another borrower book it. Record the unlock on the compartment instead.

## Staff loading

- Only staff can confirm loading.
- Staff can load at any time until the code window closes.
- Reject loading in these cases:
  - The reservation isn't `confirmed`.
  - The unit's condition isn't `good`.
  - The unit is on an open loan or already in a compartment.
  - An earlier booking for the same unit can still be collected.
  - Both compartments are full.
- The system picks the first empty compartment.
- Blocking units on an open loan also blocks pickup for an at-risk reservation, as Stage 1.0 requires.

## One-time code

- Create a 6-digit code with Python's `secrets` module when staff confirm loading.
- Create the code before the Firestore transaction, as `offer` does with its ID, because a transaction can run more than once.
- Show the code only to the signed-in borrower on their locker page, and label the delivery as simulated.
- Store the code in its own record, separate from the reservation. `GET /reservations` returns every reservation field, so a code stored there would be exposed.
- The code is stored as plain text. Add a `shortcut:` comment saying this suits fictional local data only and must change before real use.
- The code works from the pickup time until 30 minutes later, measured with `local_clock`.
- An expired code stays rejected, with no reissue in P0. No-show handling belongs to Stage 3.3.

## Rejected codes

Reject a code that is wrong, belongs to another borrower, is too early, has expired, or has already been used.

- Compare codes with `compare_digest`.
- Five wrong tries blocks the code.
- Record each wrong try in the audit events.
- A rejected request must still save the try count. `LocalStateStore.change` discards all changes when the function raises an error, so save the count first and raise the error after the transaction finishes.

## Pickup confirmation

- Only the borrower who unlocked the compartment can confirm pickup.
- Confirmation works until the booking's due time, then is rejected. This prevents a loan that is overdue the moment it starts.
- Confirmation sets the reservation to `collected`, empties the compartment, and creates the loan.
- Use the ID `loan-{reservation_id}`, so a repeated confirmation returns the same loan and never creates a second one.
- A new loan uses the same fields as the seeded loan: `borrower_id`, `asset_id`, `status`, `picked_up_at`, and `due_at`. `due_at` comes from the reservation.

## Screens and tools

- Add one `/locker` page using the Stage 1.0 local sign-in. Staff see compartments and loading actions. Borrowers see only their own code and pickup steps. The backend still checks every action.
- Add one read-only ADK tool that shows a borrower their pickup status. It never returns the code. Test it directly, as Stage 1.1 does.
- Loading, code entry, and pickup confirmation stay on the locker page in P0.

## Audit events

Record loading, wrong code tries, unlocks, and pickups with the time, the signed-in user, the action, and the reservation ID. Stage 1.2 is the first stage to add audit events, so C and D should reuse the same format.

## Build and verify

Test these cases against the Firestore emulator:

- The full flow from a confirmed reservation to an active loan.
- Non-staff users trying to load.
- Each reason staff loading can be rejected.
- Wrong-user, wrong, too-early, expired, and used codes.
- A code blocked after five wrong tries, with the count saved.
- Pickup confirmation by another borrower, before unlock, and after the due time.
- Repeated loading, unlocking, and confirmation creating no duplicate records.
- The code staying out of `GET /reservations` and the ADK tool.
- A unit staying unavailable for new bookings at every step.

Seeded Projector A stays on loan until Stage 1.3 exists, so test with a new booking for Projector B or the Raspberry Pi kit.

## To confirm with the team

- **Locker page owner:** the build plan doesn't name one. This doc assumes Teammate B owns the page and that C and D add their staff actions to it.
- **Audit format:** agree the format above with C and D.
- **Loan handoff:** a unit received in Stage 1.3 but not yet checked must count as an open loan, so staff can't load it.
- **At-risk reservations:** check with D that blocking units on an open loan is enough for Stage 1.4.

Staff reissue, loading time limits, no-show handling, and code entry in chat are out of scope for this stage.
