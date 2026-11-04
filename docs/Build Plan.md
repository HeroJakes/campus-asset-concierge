# Build Plan

Campus Asset Concierge helps staff protect future equipment bookings when a borrower returns an item late. The hackathon demo follows one asset from reservation to pickup, then shows what happens when its loan goes overdue.

The scaffold is ready. P0 is the hackathon build. P1–P3 describe the rest of the roadmap.

## How the team works

Each teammate leads one feature end to end, including the rules, chat tools or screens it needs, tests, and demo evidence. Teammates can pair across features. A–D are placeholders for the four names.

Before starting each numbered feature, run a short Grill Me round on its rules, failure cases, and acceptance checks. Keep detailed designs with that feature. Review the README when setup, demo steps, or project status changes.

## P0 · Hackathon prototype

One asset per reservation, one location, fictional data, and a virtual locker. Keep the prototype local while event access is pending. The locker view and agent use the same backend state.

| Stage | Owner | Status | Depends on | Done when |
| --- | --- | --- | --- | --- |
| **0.1 · Project scaffold** | Team | Done | — | The package installs from the lockfile and the README explains local setup. |
| **1.0 · Shared rules and demo data** | All four | Planned | 0.1 | The team agrees on reservation and loan states, borrower and staff permissions, and resettable demo data with and without a spare unit. |
| **1.1 · Find and reserve equipment** | A | Planned | 1.0 | A borrower can ask for equipment, see an eligible unit and time window, then confirm. Exactly one of two overlapping requests for the last unit succeeds. |
| **1.2 · Load and collect equipment** | B | Planned | 1.0, then 1.1 for integration | Staff confirm loading before access is issued. A valid one-time code unlocks the virtual locker, and separate pickup confirmation starts the loan. Wrong-user, expired, and replayed codes are rejected. |
| **1.3 · Return equipment** | C | Planned | 1.0, then 1.2 for integration | Staff verify receipt and condition. A passing item becomes available again. A failed check keeps it on hold. |
| **1.4 · Recover an at-risk booking** | D | Planned | 1.0, then 1.1 and 1.2 for integration | Advancing the demo clock marks the loan overdue, queues one simulated reminder, and finds the next booking at risk. The system records a verified substitute proposal or a staff-owned escalation. The original loan stays overdue. |
| **1.5 · Gemini Enterprise access check** | A + D | Waiting for event access | 1.1 inventory lookup and organizer access | A read-only tool works inside Gemini Enterprise before the rest of the chat flow is connected. If access is blocked, document the blocker and check whether local ADK is accepted for submission. |
| **1.6 · Rehearsal and submission** | All four, D coordinates | Planned | 1.1–1.4 and an outcome for 1.5 | The team can reset and replay both overdue outcomes, show a verified return, and prepare the repository and pitch deck for submission. |

After 1.0, all four leads can start with agreed demo data and connect their features as the earlier flows land. Start with the existing Python, ADK, FastAPI, and Firestore emulator scaffold. Confirm the choices in the relevant feature round. If hosting is approved later, the current option is Cloud Run for the backend, hosted Firestore, and Agent Runtime for the registered agent.

### P0 stop line

**Stop the hackathon build once all P0 acceptance checks pass.** The team must be able to:

- Reset the demo and show reservation, staff loading, virtual pickup, and an overdue event that puts the next booking at risk.
- Show a verified substitute proposal awaiting staff approval and replay the case with no eligible substitute to show an owned escalation. The proposal leaves the booking unchanged.
- Show a verified return and condition check. Verify the last-unit booking race, invalid or replayed credentials, unauthorized changes, and repeat actions that could otherwise duplicate loans or reminders.
- Match the chat and locker display to persisted records and audit events. Label simulated actions and queued reminders clearly.
- Have submission materials ready and record the Gemini Enterprise result. If integration is blocked, document and escalate the access issue and identify local ADK clearly in any fallback demo.

## P1 · Optional follow-up

Start only after P0 is accepted and the team approves more work.

| Stage | Goal |
| --- | --- |
| **2.1 · Approve and apply a reassignment** | Let authorized staff approve a proposal. Recheck stock and policy before moving the booking in one transaction, then verify the result. |
| **2.2 · Expand booking choices** | Add bundles, richer substitute matching, split or alternate pickup locations, waitlists, and optional QR pickup. |
| **2.3 · Run automation on a schedule** | Add durable scheduling and retries, notification delivery to consenting accounts, and clearer locker status. |
| **2.4 · Improve staff visibility** | Add utilization and overdue reporting, more failure scenarios, and stronger concurrency and monitoring checks. |

## P2 · Full university product

| Stage | Goal |
| --- | --- |
| **3.1 · Expand campus operations** | Support departments and campuses, shared asset pools, institutional sign-in, training, approvals, deposits, and loan limits. |
| **3.2 · Manage equipment through its lifecycle** | Track kit components, condition, maintenance, damaged or missing items, recurring loans, and other pickup methods. |
| **3.3 · Handle more disruptions** | Recover from locker faults, wrong loads, damaged returns, no-shows, and demand spikes with clear staff escalation and retry rules. |
| **3.4 · Connect real systems** | Pilot authorized inventory and identity integrations, staff notifications, and secure smart-locker adapters. Validate device events and physical custody with pilot partners. |

## P3 · Multi-organization platform

| Stage | Goal |
| --- | --- |
| **4.1 · Separate organizations and policies** | Give each organization isolated data, its own roles and policies, and configurable audit and retention settings. |
| **4.2 · Prepare for enterprise operations** | Add reliability targets, backups and restore tests, incident response, and privacy and sector reviews. |
| **4.3 · Validate the commercial offering** | Measure staff effort and recovery outcomes with real pilots. Use the results to decide on licensing, onboarding, and which integrations to support. |
