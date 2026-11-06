# Local walkthrough

The full click-through for the local prototype: reset, booking, pickup, return, and overdue recovery. Start the Firestore emulator and the API first — see [Run it locally](../README.md#run-it-locally). All data is fictional.

## Reset and clock

Open the [API docs](http://127.0.0.1:8000/docs) and use **Authorize** to sign in with a local username and password.

As `local-operator`, send `{"scenario":"spare_available"}` or `{"scenario":"spare_unavailable"}` to `POST /local-test/reset`. Use `GET /local-test/clock` to verify the reset and `POST /local-test/clock/advance` with `{"minutes":90}` to advance time. Borrowers can read their own seeded bookings at `GET /reservations`.

## Booking

After a reset, authorize as `borrower-a` and send this body to `POST /reservation-offers`:

```json
{"category":"projector","pickup_at":"2026-11-07T12:00","duration_minutes":60}
```

Review the unit and Malaysia-time window. Use the returned ID in `POST /reservation-offers/{offer_id}/confirm`, then check `GET /reservations`.

For projectors, add `"require_hdmi":true` and/or `"require_built_in_speakers":true` to the offer request. These must be JSON booleans. Omitted or false means not required. At 12:00 in the default scenario, Projector B has HDMI but no speakers; a request requiring speakers has no match. At 13:00, Projector A can meet both requirements. The API, agent confirmation, and locker page show the saved requirements.

## Pickup

Book with `"pickup_at":"2026-11-07T10:30"` instead, then open the [locker page](http://127.0.0.1:8000/locker). Sign in as `equipment-staff` and select **Confirm loading**. In a private browser window, open the same page as `borrower-a` to see the code. Use `POST /local-test/clock/advance` with `{"minutes":30}` to reach the pickup time, refresh the page, enter the code, and confirm pickup.

## Return

Use `borrower-a`, who starts each reset with Projector A on loan. On the borrower locker page, select **Return this item** to get a return code and compartment, enter the code to unlock it, and confirm the drop-off. Then sign in as `equipment-staff` and select **Pass** or **Fail** under "Returns to check". A pass frees the unit; a fail puts it on hold.

## Overdue recovery

Reset as `local-operator` with `{"scenario":"spare_available"}` or `{"scenario":"spare_unavailable"}`, then advance the clock past the seeded 11:00 MYT due time with `POST /local-test/clock/advance` and `{"minutes":61}`. Sign in as `equipment-staff` and open the [locker page](http://127.0.0.1:8000/locker), or read `GET /recovery`.

The spare-available scenario shows a verified Projector B proposal awaiting staff approval. The spare-unavailable scenario shows an escalation owned by Equipment Staff. Both outcomes keep the original reservation confirmed and the Projector A loan overdue. Reminders are simulated and queued in local state; no messages are sent.

To approve the spare-available proposal, sign in as `equipment-staff` after the recovery step and open the [locker page](http://127.0.0.1:8000/locker). Select **Approve and apply**. The reservation moves to Projector B only after the service rechecks current stock and booking rules. `GET /recovery` shows the applied proposal and its `substitution_applied` audit event. Repeating the approval is safe. If Projector B becomes unavailable first, the approval returns a conflict and leaves the original reservation unchanged.

Staff can select **Check substitutes again** on a pending proposal. Unchanged stock keeps the proposal; changed stock can replace it or create a staff-owned escalation. A replacement still needs approval. Direct API approvals must include `{"proposal_id":"<id from GET /recovery>"}` in the request body so an older page cannot approve a different proposal. For the full capability-matching rehearsal, follow the [Stage 2.2 steps](STAGE_2_2_IMPLEMENTATION.md#fictional-fixtures-and-rehearsal).
