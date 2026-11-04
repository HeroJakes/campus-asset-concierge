# Build Stages — Campus Asset Concierge

Campus Asset Concierge helps staff protect future equipment bookings when a borrower returns an item late. The hackathon demo follows one asset from reservation to pickup, then shows what happens when its loan goes overdue.

The scaffold is ready. P0 is the hackathon build. P1–P3 describe the rest of the roadmap.

Stage numbers are stable. Use them in feature discussions and status updates.

## Table of contents

- [Status](#status)
  - [Parallel work](#parallel-work)
- [Phase 0 — Foundation](#phase-0--foundation)
- [Phase 1 — Hackathon prototype (P0)](#phase-1--hackathon-prototype-p0)
  - [P0 stop line](#p0-stop-line)
- [Phase 2 — Optional follow-up (P1)](#phase-2--optional-follow-up-p1)
- [Phase 3 — Full university product (P2)](#phase-3--full-university-product-p2)
- [Phase 4 — Multi-organization platform (P3)](#phase-4--multi-organization-platform-p3)

## Status

| Stage | Goal | Owner | Status | Depends on |
| --- | --- | --- | --- | --- |
| [0.1](#stage-01--project-scaffold) | Project scaffold | Team | Done | — |
| [1.0](#stage-10--shared-rules-and-demo-data) | Shared rules and demo data | All four | Planned | 0.1 |
| [1.1](#stage-11--find-and-reserve-equipment) | Find and reserve equipment | A | Planned | 1.0 |
| [1.2](#stage-12--load-and-collect-equipment) | Load and collect equipment | B | Planned | 1.0, then 1.1 for integration |
| [1.3](#stage-13--return-equipment) | Return equipment | C | Planned | 1.0, then 1.2 for integration |
| [1.4](#stage-14--recover-an-at-risk-booking) | Recover an at-risk booking | D | Planned | 1.0, then 1.1 and 1.2 for integration |
| [1.5](#stage-15--gemini-enterprise-access-check) | Gemini Enterprise access check | A + D | Waiting for event access | 1.1 inventory lookup and organizer access |
| [1.6](#stage-16--rehearsal-and-submission) | Rehearsal and submission | All four, D coordinates | Planned | 1.1–1.4 and an outcome for 1.5 |

### Parallel work

Each teammate leads one feature end to end, including the rules, chat tools or screens it needs, tests, and demo evidence. Teammates can pair across features. A–D are placeholders for the four names.

Before starting each numbered feature, run a short Grill Me round on its rules, failure cases, and acceptance checks. Keep detailed designs with that feature. Review the README when setup, demo steps, or project status changes.

| Track | Feature | Handoff |
| --- | --- | --- |
| A | 1.1 Reservation | Share the booking flow and inventory lookup with B and D. |
| B | 1.2 Pickup | Share confirmed pickup and active loan records with C and D. |
| C | 1.3 Return | Share verified return and condition status with A and D. |
| D | 1.4 Overdue recovery | Connect booking and loan records. Coordinate rehearsal in 1.6. |
| A + D | 1.5 Gemini Enterprise | Run the first inventory check together when event access arrives. |

After 1.0, all four leads can start with agreed demo data and connect their features as the earlier flows land. Start with the existing Python, ADK, FastAPI, and Firestore emulator scaffold. Confirm the choices in the relevant feature round. If hosting is approved later, the current option is Cloud Run for the backend, hosted Firestore, and Agent Runtime for the registered agent.

---

## Phase 0 — Foundation

### Stage 0.1 — Project scaffold

**Depends on** · —

**Done when** · The package installs from the lockfile and the README explains local setup.

## Phase 1 — Hackathon prototype (P0)

One asset per reservation, one location, fictional data, and a virtual locker. Keep the prototype local while event access is pending. The locker view and agent use the same backend state.

### Stage 1.0 — Shared rules and demo data

**Depends on** · 0.1

**Done when** · The team agrees on reservation and loan states, borrower and staff permissions, and resettable demo data with and without a spare unit.

### Stage 1.1 — Find and reserve equipment

**Depends on** · 1.0

**Done when** · A borrower can ask for equipment, see an eligible unit and time window, then confirm. Exactly one of two overlapping requests for the last unit succeeds.

### Stage 1.2 — Load and collect equipment

**Depends on** · 1.0, then 1.1 for integration

**Done when** · Staff confirm loading before access is issued. A valid one-time code unlocks the virtual locker, and separate pickup confirmation starts the loan. Wrong-user, expired, and replayed codes are rejected.

### Stage 1.3 — Return equipment

**Depends on** · 1.0, then 1.2 for integration

**Done when** · Staff verify receipt and condition. A passing item becomes available again. A failed check keeps it on hold.

### Stage 1.4 — Recover an at-risk booking

**Depends on** · 1.0, then 1.1 and 1.2 for integration

**Done when** · Advancing the demo clock marks the loan overdue, queues one simulated reminder, and finds the next booking at risk. The system records a verified substitute proposal or a staff-owned escalation. The original loan stays overdue.

### Stage 1.5 — Gemini Enterprise access check

**Depends on** · 1.1 inventory lookup and organizer access

**Done when** · A read-only tool works inside Gemini Enterprise before the rest of the chat flow is connected. If access is blocked, document the blocker and check whether local ADK is accepted for submission.

### Stage 1.6 — Rehearsal and submission

**Depends on** · 1.1–1.4 and an outcome for 1.5

**Done when** · The team can reset and replay both overdue outcomes, show a verified return, and prepare the repository and pitch deck for submission.

### P0 stop line

**Stop the hackathon build once all P0 acceptance checks pass.** The team must be able to:

- Reset the demo and show reservation, staff loading, virtual pickup, and an overdue event that puts the next booking at risk.
- Show a verified substitute proposal awaiting staff approval and replay the case with no eligible substitute to show an owned escalation. The proposal leaves the booking unchanged.
- Show a verified return and condition check. Verify the last-unit booking race, invalid or replayed credentials, unauthorized changes, and repeat actions that could otherwise duplicate loans or reminders.
- Match the chat and locker display to persisted records and audit events. Label simulated actions and queued reminders clearly.
- Have submission materials ready and record the Gemini Enterprise result. If integration is blocked, document and escalate the access issue and identify local ADK clearly in any fallback demo.

---

## Phase 2 — Optional follow-up (P1)

Start only after P0 is accepted and the team approves more work.

### Stage 2.1 — Approve and apply a reassignment

Let authorized staff approve a proposal. Recheck stock and policy before moving the booking in one transaction, then verify the result.

### Stage 2.2 — Expand booking choices

Add bundles, richer substitute matching, split or alternate pickup locations, waitlists, and optional QR pickup.

### Stage 2.3 — Run automation on a schedule

Add durable scheduling and retries, notification delivery to consenting accounts, and clearer locker status.

### Stage 2.4 — Improve staff visibility

Add utilization and overdue reporting, more failure scenarios, and stronger concurrency and monitoring checks.

## Phase 3 — Full university product (P2)

### Stage 3.1 — Expand campus operations

Support departments and campuses, shared asset pools, institutional sign-in, training, approvals, deposits, and loan limits.

### Stage 3.2 — Manage equipment through its lifecycle

Track kit components, condition, maintenance, damaged or missing items, recurring loans, and other pickup methods.

### Stage 3.3 — Handle more disruptions

Recover from locker faults, wrong loads, damaged returns, no-shows, and demand spikes with clear staff escalation and retry rules.

### Stage 3.4 — Connect real systems

Pilot authorized inventory and identity integrations, staff notifications, and secure smart-locker adapters. Validate device events and physical custody with pilot partners.

## Phase 4 — Multi-organization platform (P3)

### Stage 4.1 — Separate organizations and policies

Give each organization isolated data, its own roles and policies, and configurable audit and retention settings.

### Stage 4.2 — Prepare for enterprise operations

Add reliability targets, backups and restore tests, incident response, and privacy and sector reviews.

### Stage 4.3 — Validate the commercial offering

Measure staff effort and recovery outcomes with real pilots. Use the results to decide on licensing, onboarding, and which integrations to support.
