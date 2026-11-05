# Return uses a locker drop-off, not a direct staff hand-off

For Stage 1.3, a borrower returns an item by dropping it into a virtual locker compartment with a one-time return code, and staff then retrieve and check it. We chose this over the simpler option of the borrower handing the item to staff at the desk while staff record the return in one action.

## Why

We want the prototype to behave like a real smart-locker return and to stay consistent with Stage 1.2 pickup, which already uses compartments and one-time codes. Mirroring that flow in reverse (borrower issues a code and drops off; staff retrieve and inspect) reuses the Stage 1.2 code machinery and reads as one coherent locker story in the demo.

## Consequences

- Return competes with pickup loading for the only two compartments, so a return can be rejected when the locker is full. Accepted for P0; a waitlist is later work.
- A new intermediate loan status, `awaiting_check`, is needed for an item that is dropped but not yet inspected, and `eligible_unit` must treat it as blocking.
- The shared audit format gains an `asset_id` field, because returns are addressed by asset and the seeded overdue-demo loan has no reservation id.

## Considered and rejected

A direct staff hand-off (borrower gives the item to staff; staff record receipt and condition in one action) is less code and avoids compartment contention, but it drops the locker from the return story and diverges from the Stage 1.2 pickup flow. We chose realism and consistency over the smaller build.
