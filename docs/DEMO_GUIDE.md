# Demo guide

Follow Borrower A and equipment staff. Borrower B appears as the next booking
affected by the overdue item; opening Borrower B's interface is unnecessary.
Use [Operations](OPERATIONS.md) for credentials/reset and [Build stages](BUILD_STAGES.md)
for what is still pending.

## Prepared fictional scenario

The live clock is fixed at **November 7, 2026, 11:01 MYT**. Local emulator reset
starts at 10:00; only the local operator can advance it. Do not try clock-advance
instructions on Vercel.

| Item | Starting story |
| --- | --- |
| Borrower A | Holds Projector A, due 11:00 and now overdue |
| Borrower B | Has Projector A booked 12:00–13:00 |
| Projector A | HDMI and built-in speakers; still with Borrower A |
| Projector B | HDMI, no built-in speakers; free in `spare_available` |
| Raspberry Pi kit | Free for a new Borrower A booking |
| Six compartments (A1 to A6) | All empty after reset; temporary handover spaces |

`presentation` is the main showcase. It keeps the `spare_available` story above and adds
a morning of fictional history so every staff panel has content:

| Extra item | Starting story |
| --- | --- |
| Projector B | Lent to Borrower A 07:30–08:45, returned and checked; still the free spare |
| Raspberry Pi Kit B | Lent to Borrower B 08:00–09:30, returned and checked; Borrower A has it booked 14:00–16:00 (waiting to be loaded) |
| Projector C | Borrower B dropped it off in A2 at 10:20; **waiting for a return check** |
| Raspberry Pi Kit C | Loaded in A1 at 10:45 for Borrower B's 11:30 pickup |

`spare_available` prepares a Projector B proposal awaiting staff approval.
`spare_unavailable` also books Projector B for noon, so recovery prepares an
escalation owned by `equipment-staff`. Proposals do not change a booking until
staff approve them. Pickup frees its compartment; a return occupies one until
staff finish the condition check.

## Presentation sequence

Use separate browser sessions for staff (`equipment-staff`), Borrower A
(`borrower-a`), and the backstage operator (`local-operator`). All use the live
locker URL except operator/API actions at `/docs`. The login page lists borrower
and staff test passwords, as tiles you can click to fill the form. Only the operator password
is supplied privately.

Staff and borrowers use `/login` and choose their account type.
Keep the operator in a separate session with Basic authorization at `/docs`;
the login form does not grant operator access.

Before recording, operator POST `/local-test/reset` with
`{"scenario":"presentation"}`. Refresh the staff and borrower pages.
Reset clears previous activity. Do not reseed cloud data or change the clock.

1. **Show the problem on staff's screen.** Projector A is overdue; Borrower B needs it at noon. Say: "We detect the conflict before the next student arrives." Leave the proposal pending.
2. **Book the kit as Borrower A.** With Gemini connected, request a Raspberry Pi kit on November 7 from 11:01 to 12:01, review the offer, then confirm. Without Gemini, use the API fallback below and label it as backend functionality.
3. **Load and collect.** Refresh staff's Bookings page, find the kit, and select **Confirm loading**. On Borrower A's locker page, open the **pickup status** link at the bottom to read that kit's code. Go back, refresh the locker, enter it, select **Unlock compartment**, then **Confirm pickup**. The loan starts and the compartment becomes empty.
4. **Recover the projector booking.** On staff's overview select **Review substitute proposal**, explain the eligible Projector B, then **Approve and apply**. Show `next-projector` on staff's Bookings page now assigned to Projector B. The original Projector A loan remains overdue.
5. **Return the kit.** On Borrower A's page select the **Raspberry Pi kit**, then **Return this item**. Get its code from the **return status** link (borrower-owned GET `/returns`), enter it, unlock, and **Confirm drop-off**. Staff refresh, select **Check return**, then **Pass**. Explain that an item is not available until its condition check passes; **Fail** would put it on hold.
6. **Show the other outcome as a separate scenario.** Operator reset with `{"scenario":"spare_unavailable"}`. Refresh staff's screen and show **Staff-owned escalation**. Say: "When no suitable spare exists, the case has a clear staff owner." This clears the earlier demo actions.
7. **Close.** "Booking, controlled collection, checked returns, and recovery protect the next student's booking." Restore `presentation` backstage for the next judge.

Optional extra on the `presentation` seed: on staff's **Returns to check**, select
**Check return** for Projector C and **Pass** to show a checked return without
waiting for a new drop-off. The Equipment use panel shows each unit's loans and time on loan.

Show recovery before returning the original overdue projector. Returning the kit
instead keeps that story intact. Use an 11:01 pickup for immediate collection:
a future booking will remain too early forever on the fixed hosted clock.
Show Firestore only briefly if needed as persistence evidence; actions and outcomes
are the main presentation.

Until Gmail is connected, say: "I am reading the code from the borrower's own
status API as a demo stand-in." Neither the current locker nor chat displays the
code, and no email is actually sent. Prepare a full rehearsal, then record the
preliminary video within the event's 10-minute maximum.

## API booking fallback

The borrower locker has no booking form. At the live `/docs`, authorize as
`borrower-a` and POST `/reservation-offers`:

```json
{
  "category": "raspberry_pi_kit",
  "pickup_at": "2026-11-07T11:01",
  "duration_minutes": 60
}
```

Copy the returned offer `id` into POST
`/reservation-offers/{offer_id}/confirm`. Then refresh the locker page.
This creates a real persisted fictional booking, not an AI conversation.

To demonstrate requirements separately, request a projector for November 7 at
14:00 with `require_hdmi=true`. Projector B has HDMI but cannot satisfy a request
requiring speakers in the overdue fixture. Choose the kit for the main immediate
pickup sequence so a new booking does not consume the recovery spare.

## Gemini assembly

Status: planned, licence and real connector verification pending. Do not present
the following configuration as a completed integration.

| Field | Planned setting |
| --- | --- |
| MCP URL | `https://campus-asset-concierge-demo.vercel.app/mcp` |
| Connector authentication | **No authentication**, approved only for fictional demo data |
| Chat agent | `campus_asset_concierge` |
| Borrower tools | `find_equipment`, `confirm_booking`, `check_pickup_status`, `check_return_status` |
| Workflow | `overdue-recovery`; give it `run_overdue_recovery` |
| First-party connector | Gmail; use a controlled staff test inbox for `<STAFF_EMAIL>` |
| Model | Original plan: Flash tier; verify the available model and tool use in the event app |

1. Create the Gemini Enterprise app with chat agents/workflows enabled.
2. Register MCP, enable the intended tools, and verify a status call before connecting writes.
3. Add the borrower agent instructions below. Explicitly use fictional `borrower-a` for this demo; trusted session-to-borrower identity is not implemented.
4. Configure Gmail and the workflow steps below. Test draft, approval, and delivery with controlled inboxes.
5. Replay both scenarios and a booking against the same live demo document. Record the result and judge-access/app links in the submission checklist.
6. OAuth can be added later against the real connector. No identity verification is provided by the current borrower-ID parameter.

### Borrower instructions

```text
For this fictional demo use borrower_id borrower-a. The backend reference time is
November 7, 2026, 11:01 Malaysia time. Do not use the real calendar date as its clock.
Help the borrower reserve one item. Ask for missing pickup time and return time
or duration. Interpret times in Malaysia time. Resolve relative dates only against
the known demo reference, or ask for the exact date.
Show the offered asset, location, pickup time, return time, and requirements.
Capture HDMI and built-in speaker requirements only when mentioned. False means
not required, not forbidden. Say "No extra requirements" when neither is required.
Only call confirm_booking after the borrower explicitly agrees to the shown offer.
If availability changed, offer to check again and ask them to review a fresh offer.
Use check_pickup_status and check_return_status for status questions.
Codes, unlocking, pickup confirmation, and drop-off happen outside this chat.
Never invent a code, claim an email was sent without a verified delivery step,
or approve a staff substitution.
```

### Recovery workflow and email

Call `run_overdue_recovery`; continue if proposals or escalations exist. For each
outcome, draft the corresponding email and route it to equipment staff for
approval. Only an approved delivery step may send; rejection does nothing.
Notification approval is separate from **Approve and apply** on the staff locker,
which changes the booking. Keep the borrower chat agent away from recovery tools.

The existing cron job already runs backend recovery daily at 09:00 Malaysia time.
A later Gemini workflow is separate: validate its schedule and prevent repeat
emails for the same outcome. Backend recovery idempotency does not prove email
delivery idempotency. The fixed demo clock does not move on a schedule.

To `<STAFF_EMAIL>`, subject `Action needed: substitute ready for booking {reservation_id}`:

```text
A loaned item is overdue and threatens the next booking.
Overdue loan: {overdue_loan_id}; original asset: {original_asset_id}
Threatened booking: {reservation_id}
Verified substitute: {substitute_asset_id}
Requirements: {requirements}
Approve the notification, then review/apply the substitute on the staff locker.
This message is part of a fictional prototype demonstration.
```

To `<STAFF_EMAIL>`, subject `Action needed: no substitute for booking {reservation_id}`:

```text
A loaned item is overdue and no eligible substitute is available.
Overdue loan: {overdue_loan_id}; original asset: {original_asset_id}
Threatened booking: {reservation_id}
Requirements: {requirements}; staff owner: {owner}
Staff action is needed. This is a fictional prototype demonstration.
```

Map `overdue_loan_id` from `overdue_loans[].id`. Match proposal/escalation
`reservation_id` to its at-risk booking/loan; use the proposal's original/substitute
asset and saved requirements. For escalation, original asset comes from the
matched overdue loan and owner/requirements from the escalation. Do not assume
array positions identify related records.

### Pickup and return email gap

The optional direct Gmail API implementation can deliver these codes without
Gemini Enterprise. Follow [Gmail setup](GMAIL_DEMO.md), authorize the sender, and
verify receipt before claiming this is live. When enabled, the borrower sees
delivery status and can retry a definite failure. The manual API lookup remains
the fallback. Recovery workflow email below is still planned.

The intended Gmail message contains the borrower's code, compartment, and valid
time, addressed to their controlled test inbox. Subject:
`Your pickup code for {asset_name}` or `Your return code for {asset_name}`.

The current MCP status tools intentionally omit codes. Automatic delivery needs
an approved authenticated staff/workflow lookup or a load/return integration.
Do not expose a code-returning tool on the no-auth public MCP endpoint. Until this
is designed and tested, use only the borrower-owned API stand-in described above.

## Before submission

Check the [submission checklist](../submission/README.md): app access, private demo
credentials, fixed-clock instructions, reset arrangements, deck, video, and write-up.
Label the virtual locker, fictional data, planned Gemini integration, and simulated
email honestly. Do not claim the earlier 80% recovery target is a measured result.

If the licence never arrives, ask organisers about an ADK/Gemini API fallback.
That agent exists in code, but an isolated-data connection, model access, full
rehearsal, and submission eligibility still need verification.
