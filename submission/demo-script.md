# Demo script

Live demo only, about 4 minutes. It follows the `presentation` data on the hosted site.

**Say** = read this out. **Do** = what to click.

## Before you record

- Reset the hosted demo to `presentation` (operator, `/docs`, POST `/local-test/reset` with `{"scenario":"presentation"}`).
- Open three windows: **Staff** (`equipment-staff`) on `/locker`, **Borrower A** (`borrower-a`,
  private window) on `/locker`, and **Borrower A's email inbox**.
- The clock is fixed at **November 7, 11:01**.

---

## 1. The problem (about 40 s)

**Do:** Show the staff Locker page. Point at **Overdue recovery**.

**Say:**
> "This is the staff dashboard. Borrower A still has Projector A. It was due at 11:00,
> but Borrower B has booked it for 12:00. Our system spotted this conflict before
> Borrower B arrives, and found that Projector B is free and meets their needs.
> It is only a proposal. Staff stay in control."

## 2. Book with MiMi (about 50 s)

**Do:** Switch to Borrower A. Click **MiMi**. Type:
`Book a Raspberry Pi kit today from 11:01 for one hour`

**Say (while MiMi replies):**
> "Students book in plain language with MiMi, our assistant built on the Gemini API.
> It uses the same booking rules and only offers a unit that is free."

**Do:** Click **Confirm booking**.

**Say:**
> "Nothing is booked until the student confirms."

*If MiMi is slow:* book through `/docs` with the API booking fallback in the demo guide.

## 3. Load and collect (about 50 s)

**Do:** Switch to Staff. Refresh. Click **Confirm loading** on Borrower A's kit.

**Say:**
> "Staff load the kit into a free compartment. The borrower gets a one-time code by email.
> Staff never see it."

**Do:** Show the code email. On Borrower A's locker page, refresh, enter the code,
click **Unlock compartment**, then **Confirm pickup**.

*If the email has not arrived:* use the **pickup status** link at the bottom of the locker page.

**Say:**
> "The code works once, only for this borrower. The loan has started."

## 4. Approve the substitute (about 40 s)

**Do:** Switch to Staff. Click **Review substitute proposal**, then **Approve and apply**.

**Say:**
> "Staff approve the substitute. The system checks everything again first.
> Borrower B's 12:00 booking now uses Projector B, so they still get a projector."

## 5. Return and check (about 40 s)

**Do:** On Borrower A's page, click **Return this item** on the kit. Enter the return code,
**Unlock compartment**, then **Confirm drop-off**. On Staff, refresh, click **Check return**, then **Pass**.

**Say:**
> "Returns use a new one-time code. The item is not lent again until staff check its condition.
> A fail would put it on hold."

## Close (about 20 s)

**Do:** Scroll to **Equipment use** and **Activity**.

**Say:**
> "Staff can see every unit and every action here. So: easy booking with MiMi,
> safe pickup and return with one-time codes, and late returns caught before the next
> student arrives. All data in this demo is fictional."

---

## Notes

- Say "Gemini API". Gemini Enterprise access was not provided.
- Do not claim the 80% figure as a result. It is a target, not a measurement.
- After recording, reset back to `presentation`.
