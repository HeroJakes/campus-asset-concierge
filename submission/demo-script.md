# Demo script

Live demo only, about 4 minutes. It shows live what the slides explain. It follows the `presentation` data on the hosted site.

**Say** = read this out. **Do** = what to click.

## Before you record

- Reset the hosted demo to `presentation` (operator, `/docs`, POST `/local-test/reset` with `{"scenario":"presentation"}`).
- Open three windows: **Staff** (`equipment-staff`) on `/locker`, **Borrower A** (`borrower-a`,
  private window) on `/locker`, and **Borrower A's Gmail inbox**.
- The clock is fixed at **November 7, 11:01**.

---

## 1. Start on the staff screen (about 30 s)

**Do:** Show the staff Locker page. Point at **Overdue recovery**.

**Say:**
> "This is our live app, running on Vercel. The people and equipment are test data, the clock
> is fixed for the demo, and the locker is virtual.
> Right away you can see the problem from our slides. Projector A is overdue, and Borrower B
> needs a projector at 12:00. Our recovery check has already spotted this and found
> Projector B as a spare. We'll come back to that. First, let's book something as a student."

## 2. Book with MiMi (about 1 min)

*Use the same messages as the Run Log slide.*

**Do:** Switch to Borrower A. Click **MiMi**. Type: `Book a Raspberry Pi kit`

**Say (while MiMi replies):**
> "This is MiMi, our booking assistant, built on the Gemini API. I've asked for a kit,
> but I didn't say when. MiMi doesn't guess. It asks me for the time."

**Do:** Reply: `Today from 11:01 for one hour`

**Say (while MiMi replies):**
> "Now MiMi has everything it needs, so it calls our find-equipment tool. That tool checks
> the real booking rules and finds a kit that's free for the whole hour."

**Do:** Point at the offer card, then click **Confirm booking**.

**Say:**
> "Notice that MiMi only makes an offer. It can't book on its own. The booking happens when
> I press Confirm, and the server checks availability again at that moment."

*If MiMi is slow:* book through `/docs` with the API booking fallback in the demo guide.

## 3. Load and collect (about 1 min)

**Do:** Switch to Staff. Refresh. Click **Confirm loading** on Borrower A's kit.

**Say:**
> "Over on the staff side, the booking has arrived. Staff put the kit in a free compartment
> and confirm loading. The moment they do, the system sends a one-time pickup code to
> the student's Gmail."

**Do:** Switch to the Gmail inbox. Open the pickup code email.

**Say:**
> "And here it is in Gmail. Only the student gets this code. Staff never see it, and
> MiMi never sees it either."

**Do:** Switch to Borrower A's locker page. Refresh, enter the code, click
**Unlock compartment**, then **Confirm pickup**.

**Say:**
> "Back at the locker, the student types in the code, the compartment opens, and they take
> the kit. The code works only once, and only for this student. The loan has started."

*If the email has not arrived:* use the **pickup status** link at the bottom of the locker page.

## 4. Approve the substitute (about 40 s)

**Do:** Switch to Staff. Click **Review substitute proposal**, then **Approve and apply**.

**Say:**
> "Now back to that overdue projector. The recovery check found the problem and picked a
> spare, but it can't change anyone's booking without a person saying yes. Staff approve,
> the system checks the spare one more time, and Borrower B's 12:00 booking now uses
> Projector B. They still get their projector on time.
> When no spare fits, the case goes straight to staff instead. That case is in our test results."

## 5. Return and check (about 40 s)

**Do:** Switch to Borrower A. Click **Return this item** on the kit.

**Say:**
> "When the student is done, they tap Return. Again, a new one-time code goes to their Gmail."

**Do:** Show the return code email in Gmail. Back on Borrower A's page, enter the code,
click **Unlock compartment**, then **Confirm drop-off**.

**Do:** Switch to Staff. Refresh, click **Check return**, then **Pass**.

**Say:**
> "The kit is back in the locker, but it isn't lent out again until staff check its
> condition. If it failed the check, it would be put on hold."

## Close (about 15 s)

**Do:** Scroll to **Activity**.

**Say:**
> "Every step we just did is recorded here. To sum up: MiMi handles the booking, codes go
> straight to the student's Gmail, late returns are caught before the next student arrives,
> and staff approve every change."

---

## Notes

- Say "Gemini API". Gemini Enterprise access was not provided.
- Live: booking, MiMi chat, pickup and return codes, code emails to Gmail, recovery, approval, return checks.
  Test or simulated: fictional people and items, the fixed clock, the virtual locker, and
  overdue reminders (queued, not sent). Planned work is on the Limits & Roadmap slide.
- Do not claim the 80% figure as a result. It is a target, not a measurement.
- After recording, reset back to `presentation`.
