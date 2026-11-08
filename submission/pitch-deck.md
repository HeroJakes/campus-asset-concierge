# Pitch deck content

The text to put on each slide. `Say:` lines are what to speak, not slide text.
Keep slides light — bullets, not paragraphs.

---

## Slide 1 — Title

**Campus Asset Concierge**
*Book campus equipment by chat. Overdue items recover themselves.*

Track 1 — Smart Campus & Student Experience
[Team name] · [Member 1] · [Member 2] · [Member 3]
Live demo: campus-asset-concierge-demo.vercel.app

> Say: "We built an AI concierge for campus equipment lending — students book in plain language, and overdue items are chased automatically."

---

## Slide 2 — Problem

**Borrowing campus equipment is slow, manual, and leaky**

- Students wait on staff or forms to borrow a projector or Pi kit — no self-service
- Staff track who has what, and chase overdue items by hand
- Overdue gear goes missing, so the next student's booking fails

**~50+ manual loans a week — and every overdue item blocks the next booking.**
*(Prototype estimate: one projector type alone runs ~6–7 loans/week at a real campus; projectors + laptops + kits + cameras add up fast.)*

> Say: "A campus lends 50-plus items a week — projectors, laptops, kits — and today every booking is processed by staff by hand. When an item is late, it blocks the next student who booked it."
>
> Defend if asked: "students need staff to book for them" is real local practice — **UTAR's equipment loan page says exactly this** (itisc.utar.edu.my/Equipment-Loan.php); the per-item rate is grounded in a published loan report (EdUHK); "late returns block others" is documented practice (Wake Forest). The 50+/week total is our stated prototype assumption.
>
> ⭐ Best upgrade: ask one APU lab/library staff member "how many items go out a week, how long chasing late ones?" — one real sentence beats any estimate.

---

## Slide 3 — Solution

**One assistant handles the whole loan — end to end**

- 💬 Book by chat — "I need a projector tomorrow 2pm" → it finds and offers one
- ✅ You confirm — one tap books it; pick up with a one-time code
- 🔄 Auto-recovery — a daily job spots overdue items and proposes a substitute for staff to approve

*Live: AI booking chat · Simulated: pickup-code email*

> Say: "The student books in plain English, taps Confirm, and gets a pickup code. Behind the scenes a daily agent finds overdue items and proposes substitutes — staff just approve."

---

## Slide 4 — Architecture

**(image)** — `submission/architecture.png`

On-slide heading: *How it works — and where the human stays in control*

> Say: "The model decides which tool to call, but it cannot book anything — it proposes, the human confirms. One-time codes never reach the model. That stop line is deliberate."

---

## Slide 5 — Agent & Prompting

**(demo)**

> Show live: the borrower types a request → the model picks `find_equipment` → an offer comes back → explain the system-prompt intent (book one item, ask for missing info, never reveal codes) and how bad input is rejected.

---

## Slide 6 — Output checks

**(demo)**

> Show live, three cases: normal booking works · hard case (nothing available → substitution proposed) · missing-data/failure (bad time → assistant re-asks; no key → graceful fallback).

---

## Slide 7 — Business value & adoption

**Protect the next booking. Cut manual follow-up.**

| Who benefits | Value |
| --- | --- |
| Students | Clearer self-service borrowing; fewer disrupted bookings |
| Equipment staff | Less manual searching for replacements and fixing booking conflicts |
| University | Clear visibility of availability, usage, and responsibility |

**How much:** at ~50 loans/week, the daily job **detects 100% of overdue items automatically** and **proposes a substitute in ~80% of cases**, instead of staff chasing by hand — an estimated **~3 staff-hours/week saved** on detection and matching (staff still approve). We confirm these in the pilot.

**Running cost:** near-zero to pilot — the booking brain runs on the **free Gemini Flash tier**, on low-cost hosting. Ongoing: hosting, AI usage, notifications, maintenance. Physical lockers are a later option.

**Adoption plan**
- Pilot at one campus equipment desk, using existing equipment and counters.
- Keep staff approval for replacements and return checks (human in the loop).
- Measure booking fulfilment, staff handling time, recovery success, operating cost.
- Expand to other departments once value is shown.

**Business model:** university-funded pilot → annual departmental licence covering onboarding and support.

**Market evidence:** Malaysian universities already run equipment-loan services — and they are manual. UTAR's IT equipment loan (projectors, laptops) states **students need a staff member to book for them** (itisc.utar.edu.my/Equipment-Loan.php). That is exactly the gap we remove: self-service for students, less manual work for staff.

*Honesty: benefits and adoption are proposed; savings and demand are not yet measured.*

> Say: "At fifty-plus loans a week, the system catches every overdue item and proposes a swap in about eighty percent of cases — roughly three staff-hours a week saved, with staff still approving. It runs on the free Gemini tier, so a pilot costs almost nothing. We'd pilot at one desk and measure the real savings before expanding."
>
> Numbers are labelled estimates for the prototype — the 100% detection is factual (deterministic daily scan); the ~80% and ~3 hrs are demo estimates to confirm in a pilot.

---

## Slide 8 — Gemini + Antigravity + closing

**Tools we used**

- **Gemini** — powers the borrower booking chat. The model reads the plain-language request, decides which tool to call (`find_equipment`, `check_pickup_status`, `check_return_status`), and proposes a booking offer for the student to confirm.
- **Antigravity** — our development IDE. We used it to build and iterate on the app throughout.

**Closing**

*A campus concierge that books in seconds and recovers overdue gear on its own — self-service for students, hands-off for staff.*

> Say: "Gemini runs the booking brain; we built it in Antigravity. The result: students book in seconds, and overdue equipment recovers itself — with a human always in control."
