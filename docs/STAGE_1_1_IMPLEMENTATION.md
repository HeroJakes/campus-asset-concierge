# Stage 1.1 — Find and reserve equipment

A signed-in borrower can ask for one item, review a reservation offer, and confirm it. This stage ends with a saved reservation. Staff loading and pickup belong to Stage 1.2.

## Request and offer

- Accept one equipment category per request. Both local borrower accounts can request a projector or Raspberry Pi kit. The system chooses a specific eligible unit.
- Ask for the pickup time and either the return time or loan duration when missing. Interpret and show dates and times in Malaysia time. Reject pickup times in the past and return times at or before pickup.
- Show the unit, pickup location, and exact pickup and return times before asking for confirmation. A reservation offer leaves the unit available until a borrower confirms.
- Allow back-to-back windows. A booking can start at the exact time the previous window ends. Actual pickup still requires staff to confirm that the unit is available and loaded.
- An item on an active loan can be offered for a window starting at or after its due time if the loan is still on schedule. Exclude overdue items and items on condition hold from new offers. A later overdue event can still put an existing reservation at risk.

## Confirm and save

1. Use the signed-in borrower to check offer ownership. Only that borrower can confirm it.
2. On confirmation, check current eligibility, time, loan and condition state, and overlapping bookings again. Perform the check and reservation write in one Firestore transaction.
3. Save the exact unit and window the borrower saw. If availability changed, explain what happened and ask the borrower to review a fresh offer.
4. Return the same reservation when the borrower retries a successful confirmation. Show the saved reservation in the borrower's reservation list.

## Build and verify

- Reuse the Stage 1.0 accounts, test clock, and Firestore emulator. Add local API operations for lookup and confirmation, then connect the same operations to ADK tools.
- Test a successful lookup and confirmation, missing or invalid times, back-to-back windows, overlapping bookings, an on-schedule loan, and exclusions for overdue items and condition holds.
- Test two borrowers confirming offers for the last unit at the same time. Exactly one succeeds. Test repeated confirmation and rejection when a borrower tries to confirm someone else's offer.
- Use the local API as the required verification path. Run a live ADK chat check when Gemini model access is available. Verify the Gemini Enterprise connection separately in Stage 1.5.

Opening hours, loan-length limits, category-specific borrowing rules, and multi-item requests are later work. The local API and ADK tools cover this stage's booking flow.
