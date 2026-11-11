# Demo script

Live demo only, about 7–8 minutes. It follows the `presentation` data on the hosted site.

**Say** = read this out. **Do** = what to click.

## Before you record

- Reset the hosted demo to `presentation` (operator, `/docs`, POST `/local-test/reset` with `{"scenario":"presentation"}`).
- Open three browser windows:
  1. **Staff**, signed in as `equipment-staff`, on `/locker`.
  2. **Borrower A**, signed in as `borrower-a`, on `/locker`.
  3. **Borrower A's email inbox**, for the code emails.
- Use a private window for Borrower A so the two sessions do not mix.
- The clock is fixed at **November 7, 11:01**. Do not try to change it.

---

## 1. Staff dashboard (about 1 min)

**Do:** Show the staff Locker page. Scroll slowly from top to bottom.

**Say:**
> "This is the staff dashboard for Locker A. It is 11:01 on the test clock.
> At the top, staff see the next item to load and any returns waiting for a check.
> The locker has six compartments. Right now A1 holds a Raspberry Pi kit waiting for
> pickup, and A2 holds a projector that was just dropped off.
> Below that are all bookings, how much each unit has been used, and a live activity log."

## 2. The problem: an overdue item (about 1 min)

**Do:** Point at the **Overdue recovery** panel.

**Say:**
> "Here is the problem we solve. Borrower A still has Projector A. It was due back at 11:00,
> so it is now overdue. But Borrower B has booked the same projector for 12:00.
> Normally staff only find out when Borrower B arrives and the projector is not there.
> Our system checks for this every day at 9 a.m. and also when staff ask.
> It has already found the conflict and checked for a spare.
> Projector B is free and meets Borrower B's needs, so it is proposed as a substitute.
> Nothing changes yet. Staff stay in control and must approve it."

**Do:** Leave the proposal pending for now.

## 3. Book with MiMi (about 1.5 min)

**Do:** Switch to Borrower A. Click **MiMi** in the top bar.

**Say:**
> "Now the borrower side. This is MiMi, our booking assistant, built on the Gemini API.
> Students book in plain language instead of filling in forms."

**Do:** Type: `Book a Raspberry Pi kit today from 11:01 for one hour`

**Say (while MiMi replies):**
> "MiMi uses the same booking rules as the rest of the system.
> It finds a unit that is free for the whole time and shows an offer."

**Do:** Click **Confirm booking** on the offer card.

**Say:**
> "The booking only happens when the student confirms. MiMi cannot book on its own,
> and it never sees the one-time locker codes."

*If MiMi is slow or unavailable:* say "The assistant uses the same booking API, so I will
book through the API instead", and book at `/docs` with the API booking fallback in the demo guide.

## 4. Load and collect (about 1.5 min)

**Do:** Switch to Staff. Refresh. On **Next to load**, find Borrower A's Raspberry Pi kit
(or open **Bookings**) and click **Confirm loading**.

**Say:**
> "Staff put the kit into a free compartment and confirm it. The system picks the
> compartment and creates a one-time pickup code."

**Do:** Switch to Borrower A's inbox and open the pickup email.

**Say:**
> "The code goes straight to the borrower by email, using the Gmail API.
> Staff never see the code."

*If the email has not arrived:* on Borrower A's locker page, open the **pickup status** link
at the bottom and say "For the demo I am reading the code from the borrower's own status page."

**Do:** On Borrower A's locker page, refresh, type the six-digit code, click **Unlock compartment**,
then **Confirm pickup**.

**Say:**
> "The code works only for this borrower, only once, and only during the pickup window.
> After pickup, the loan starts and the compartment is free again."

## 5. Approve the substitute (about 1 min)

**Do:** Switch to Staff. In **Overdue recovery**, click **Review substitute proposal**.

**Say:**
> "Back to the overdue projector. Staff review the proposal. Projector B has been checked
> against the booking time and Borrower B's needs."

**Do:** Click **Approve and apply**.

**Say:**
> "When staff approve, the system checks everything again before it changes the booking.
> Borrower B's 12:00 booking now uses Projector B, so they still get a projector.
> The original loan stays overdue so staff can follow up with Borrower A."

**Do:** Open **Bookings** and show the 12:00 booking now on Projector B.

## 6. Return and condition check (about 1.5 min)

**Do:** Switch to Borrower A's locker page. On the Raspberry Pi kit, click **Return this item**.

**Say:**
> "Returning works the same way. The borrower asks to return the kit, and a compartment
> is held for them with a new one-time code."

**Do:** Get the return code (email, or the **return status** link). Enter it,
click **Unlock compartment**, then **Confirm drop-off**.

**Do:** Switch to Staff. Refresh. Under **Returns to check**, click **Check return** for the
kit, then **Pass**.

**Say:**
> "An item is not available again until staff check its condition.
> A pass returns it to service. A fail puts it on hold so a damaged item is never lent out."

**Do (optional):** Also click **Check return** for **Projector C** and **Pass**.

## 7. Equipment use and activity (about 30 s)

**Do:** Scroll to **Equipment use** and **Activity**.

**Say:**
> "Staff can see each unit's state, how often it is lent, and for how long.
> Every action, by staff, borrowers, or the recovery check, is recorded here."

## 8. When there is no spare (optional, about 1 min)

**Do:** Operator resets to `{"scenario":"spare_unavailable"}`. Refresh the staff page.

**Say:**
> "Sometimes there is no suitable spare. Here Projector B is already booked.
> Instead of guessing, the system creates an escalation with a clear staff owner,
> so the case is never lost."

**Do:** After recording, reset back to `presentation`.

## Close (about 20 s)

**Say:**
> "So: students book in plain language with MiMi, collect and return with one-time codes,
> and staff check every return. Most importantly, the system spots a late return before
> the next student arrives, and gives staff a checked substitute to approve.
> All the data in this demo is fictional."

---

## Notes

- Say "Gemini API". Gemini Enterprise access was not provided.
- Recovery reminders are simulated; only pickup and return codes are emailed.
- Do not claim the 80% figure as a result. It is a target, not a measurement.
