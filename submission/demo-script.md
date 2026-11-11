# Demo script

Live demo only, about 4 minutes. It follows the `presentation` data on the hosted site.

**Say** = read this out. **Do** = what to click.

## Before you record

- Reset the hosted demo to `presentation` (operator, `/docs`, POST `/local-test/reset` with `{"scenario":"presentation"}`).
- Open three windows: **Staff** (`equipment-staff`) on `/locker`, **Borrower A** (`borrower-a`,
  private window) on `/locker`, and **Borrower A's email inbox**.
- The clock is fixed at **November 7, 11:01**.

---

## 1. The problem (about 35 s)

**Do:** Show the staff Locker page. Point at **Overdue recovery**.

**Say:**
> "This is the staff dashboard. Borrower A still has Projector A. It was due at 11:00,
> but Borrower B has booked it for 12:00. Our system spotted this conflict before
> Borrower B arrives, and found that Projector B is free and meets their needs.
> It is only a proposal. Staff stay in control."

## 2. Book with MiMi (about 1 min)

**Do:** Switch to Borrower A. Click **MiMi**. Type an incomplete request:
`Book a Raspberry Pi kit`

**Say (while MiMi replies):**
> "Students book in plain language with MiMi, our assistant built on the Gemini API.
> I left out the time on purpose. MiMi does not guess. It asks for what is missing."

**Do:** Reply: `Today from 11:01 for one hour`

**Say (while MiMi replies):**
> "Now MiMi has enough, so it decides to call our find-equipment tool. The tool checks
> the real booking rules and returns a unit that is free for the whole hour."

**Do:** Point at the offer card, then click **Confirm booking**.

**Say:**
> "This is where the AI stops. MiMi can only offer. The booking happens when the student
> presses Confirm, and the server checks availability again at that moment."

*If MiMi is slow:* book through `/docs` with the API booking fallback in the demo guide.

## 3. Load and collect (about 50 s)

**Do:** Switch to Staff. Refresh. Click **Confirm loading** on Borrower A's kit.

**Say:**
> "Staff load the kit into a free compartment. The borrower gets a one-time code by email.
> Staff never see it, and MiMi never sees it either. Codes are removed from everything the AI reads."

**Do:** Show the code email. On Borrower A's locker page, refresh, enter the code,
click **Unlock compartment**, then **Confirm pickup**.

*If the email has not arrived:* use the **pickup status** link at the bottom of the locker page.

**Say:**
> "The code works once, only for this borrower. The loan has started."

## 4. Approve the substitute (about 45 s)

**Do:** Switch to Staff. Click **Review substitute proposal**, then **Approve and apply**.

**Say:**
> "The recovery check found the problem and picked the spare, but it cannot change a booking
> on its own. Staff approve, and the system checks the spare again before applying it.
> Borrower B's 12:00 booking now uses Projector B, so they still get a projector.
> If no spare fits, it creates a staff-owned escalation instead."

## 5. Return and check (about 35 s)

**Do:** On Borrower A's page, click **Return this item** on the kit. Enter the return code,
**Unlock compartment**, then **Confirm drop-off**. On Staff, refresh, click **Check return**, then **Pass**.

**Say:**
> "Returns use a new one-time code. The item is not lent again until staff check its condition.
> A fail would put it on hold."

## Close (about 15 s)

**Do:** Scroll to **Activity**.

**Say:**
> "Every action is recorded here. MiMi books, the recovery check catches late returns
> before the next student arrives, and people approve every change. All data is fictional."

---

## Notes

- Say "Gemini API". Gemini Enterprise access was not provided.
- Do not claim the 80% figure as a result. It is a target, not a measurement.
- After recording, reset back to `presentation`.
