# Build Stages — Campus Asset Concierge

Campus Asset Concierge helps staff protect future equipment bookings when a borrower returns an item late. The hackathon demo follows one asset from reservation to pickup, then shows what happens when its loan goes overdue.

The shared foundation and local reservation flow are on main. P0 is the hackathon build. P1–P3 describe the rest of the roadmap.

Stage numbers are stable. Use them in feature discussions and status updates.

## Table of contents

- [Parallel work](#parallel-work)
- [Status](#status)
- [Phase 0 — Foundation](#phase-0--foundation)
- [Phase 1 — Hackathon prototype (P0)](#phase-1--hackathon-prototype-p0)
  - [P0 stop line](#p0-stop-line)
- [Phase 2 — Optional follow-up (P1)](#phase-2--optional-follow-up-p1)
- [Phase 3 — Full university product (P2)](#phase-3--full-university-product-p2)
- [Phase 4 — Multi-organization platform (P3)](#phase-4--multi-organization-platform-p3)

## Parallel work

Each teammate leads one feature end to end, including the rules, chat tools or screens it needs, tests, and demo evidence. Teammates can pair across features. A–D are placeholders for the four names.

Before starting each numbered feature, run a short Grill Me round on its rules, failure cases, and acceptance checks. Keep detailed designs with that feature. Review the README when setup, demo steps, or project status changes.

| Teammate | P0 · Hackathon prototype | P1 · Optional follow-up | P2 · University product |
| --- | --- | --- | --- |
| A | [1.1 · Reservation](#stage-11--find-and-reserve-equipment) | [2.2 · Booking choices](#stage-22--expand-booking-choices) | [3.1 · Campus operations](#stage-31--expand-campus-operations) |
| B | [1.2 · Pickup](#stage-12--load-and-collect-equipment) | [2.3 · Scheduled automation](#stage-23--run-automation-on-a-schedule) | [3.4 · Real system integrations](#stage-34--connect-real-systems) |
| C | [1.3 · Return](#stage-13--return-equipment) | [2.4 · Staff visibility](#stage-24--improve-staff-visibility) | [3.2 · Equipment lifecycle](#stage-32--manage-equipment-through-its-lifecycle) |
| D | [1.4 · Overdue recovery](#stage-14--recover-an-at-risk-booking) | [2.1 · Reassignment](#stage-21--approve-and-apply-a-reassignment) | [3.3 · Disruption recovery](#stage-33--handle-more-disruptions) |
| Shared | A and D run the [Gemini Enterprise check](#stage-15--gemini-enterprise-access-check). All four rehearse, with D coordinating. | Agree on matching rules and reporting events. | Agree on pilot scope, access rules, and trusted device and inventory events. |

For P0, A shares the booking flow and inventory lookup with B and D. B shares pickup and active loan records with C and D. C shares verified return and condition status with A and D. See the P1 and P2 sections for their first deliverables and handoffs.

After 1.0, all four leads can start with agreed local test data and connect their features as the earlier flows land. Start with the existing Python, ADK, FastAPI, and Firestore emulator scaffold. Confirm the choices in the relevant feature round. If hosting is approved later, the current option is Cloud Run for the backend, hosted Firestore, and Agent Runtime for the registered agent.

## Status

| Stage | Goal | Status | Depends on |
| --- | --- | --- | --- |
| [0.1](#stage-01--project-scaffold) | Project scaffold | Done | — |
| [1.0](#stage-10--shared-project-foundation) | Shared project foundation | Done | 0.1 |
| [1.1](#stage-11--find-and-reserve-equipment) | Find and reserve equipment | Done locally · PR #2 merged | 1.0 |
| [1.2](#stage-12--load-and-collect-equipment) | Load and collect equipment | Done locally · PR #5 merged | 1.0, then 1.1 for integration |
| [1.3](#stage-13--return-equipment) | Return equipment | Done locally · not yet merged | 1.0, then 1.2 for integration |
| [1.4](#stage-14--recover-an-at-risk-booking) | Recover an at-risk booking | Planned | 1.0, then 1.1 and 1.2 for integration |
| [1.5](#stage-15--gemini-enterprise-access-check) | Gemini Enterprise access check | Blocked by licence delay | 1.1 inventory lookup, event app access, and Agent Runtime permissions |
| [1.6](#stage-16--rehearsal-and-submission) | Rehearsal and submission | Planned | 1.1–1.4 and an outcome for 1.5 |
| [2.1](#stage-21--approve-and-apply-a-reassignment) | Apply a reassignment | Deferred · P1 | P0 sign-off and approval to start P1 |
| [2.2](#stage-22--expand-booking-choices) | Expand booking choices | Deferred · P1 | P0 sign-off and approval to start P1 |
| [2.3](#stage-23--run-automation-on-a-schedule) | Schedule overdue checks | Deferred · P1 | P0 sign-off and approval to start P1 |
| [2.4](#stage-24--improve-staff-visibility) | Improve staff visibility | Deferred · P1 | P0 sign-off. Add outcomes as 2.1 and 2.3 land. |
| [3.1](#stage-31--expand-campus-operations) | Expand campus operations | Deferred · P2 | P1 review and pilot agreement |
| [3.2](#stage-32--manage-equipment-through-its-lifecycle) | Manage equipment lifecycle | Deferred · P2 | P1 review and pilot agreement |
| [3.3](#stage-33--handle-more-disruptions) | Handle more disruptions | Deferred · P2 | P1 review and pilot agreement. Connect 3.2 and 3.4 events as they land. |
| [3.4](#stage-34--connect-real-systems) | Connect real systems | Deferred · P2 | P2 pilot approval. Use 3.1 access rules for integration. |
| [4.1](#stage-41--separate-organizations-and-policies) | Separate organizations and policies | Deferred · P3 | — |
| [4.2](#stage-42--prepare-for-enterprise-operations) | Prepare for enterprise operations | Deferred · P3 | — |
| [4.3](#stage-43--validate-the-commercial-offering) | Validate the commercial offering | Deferred · P3 | — |

Stage 1.1 passed local API and direct ADK tool checks. Live Gemini chat and Gemini Enterprise integration are still pending.

---

## Phase 0 — Foundation

### Stage 0.1 — Project scaffold

**Depends on** · —

**Done when** · The package installs from the lockfile and the README explains local setup.

## Phase 1 — Hackathon prototype (P0)

One asset per reservation, one location, fictional data, and a virtual locker. Keep the prototype local while event access is pending. The locker view and agent use the same backend state.

### What can start now

- **Stages 1.0–1.4** can proceed locally. Build and test reservations, locker pickup, returns, and overdue recovery with fictional data and the Firestore emulator. Test the agent tools directly. Live local ADK chat needs separate Gemini model access.
- **Stage 1.5** is blocked for now. The organizers reported a licence distribution delay with no confirmed date. Cloud credit details are still pending. Deploying the agent to Agent Runtime and testing it inside Gemini Enterprise depend on access to the event app and the required Cloud permissions.
- **Stage 1.6** can start with local rehearsal and submission prep. The final demo format depends on the outcome of 1.5 and whether the organizers accept the local fallback.

### Demo interfaces

Gemini Enterprise provides the chat screen when our agent is registered. The team builds a small local web page for the virtual locker and staff actions. It shows the compartment state, lets staff confirm loading, and gives the borrower a place to enter the one-time code and confirm pickup. The page reads and updates the same backend state as the agent. Local ADK can provide the fallback chat screen if separate Gemini model access is available.

### Stage 1.0 — Shared project foundation

See the [Stage 1.0 implementation doc](STAGE_1_0_IMPLEMENTATION.md) for the agreed rules and fixture setup.

**Depends on** · 0.1

**Done when** · The team agrees on reservation and loan states, borrower and staff permissions, and resettable local test data with and without a spare unit.

### Stage 1.1 — Find and reserve equipment

See the [Stage 1.1 implementation doc](STAGE_1_1_IMPLEMENTATION.md) for the agreed booking rules and acceptance checks.

**Depends on** · 1.0

**Done when** · A borrower can ask for equipment, see an eligible unit and time window, then confirm. Exactly one of two overlapping requests for the last unit succeeds.

### Stage 1.2 — Load and collect equipment

See the [Stage 1.2 implementation doc](STAGE_1_2_IMPLEMENTATION.md) for the agreed pickup rules and acceptance checks.

**Depends on** · 1.0, then 1.1 for integration

**Done when** · Staff confirm loading before access is issued. A valid one-time code unlocks the virtual locker, and separate pickup confirmation starts the loan. Wrong-user, expired, and replayed codes are rejected.

### Stage 1.3 — Return equipment

**Depends on** · 1.0, then 1.2 for integration

**Done when** · Staff verify receipt and condition. A passing item becomes available again. A failed check keeps it on hold.

### Stage 1.4 — Recover an at-risk booking

**Depends on** · 1.0, then 1.1 and 1.2 for integration

**Done when** · Advancing the local test clock marks the loan overdue, queues one simulated reminder, and finds the next booking at risk. The system records a verified substitute proposal or a staff-owned escalation. The original loan stays overdue.

### Stage 1.5 — Gemini Enterprise access check

**Depends on** · 1.1 inventory lookup, event app access, and Agent Runtime permissions.

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

The four leads can start their features in parallel after sign-off.

### Stage 2.1 — Approve and apply a reassignment

Start with one substitution proposal. Let authorized staff approve it and share the audit event with staff reporting. Recheck stock and policy before moving the booking in one transaction, then verify the result.

### Stage 2.2 — Expand booking choices

Start with richer substitute matching and agree on shared matching rules with 2.1. Then add bundles, split or alternate pickup locations, waitlists, and optional QR pickup.

### Stage 2.3 — Run automation on a schedule

Start by scheduling the existing overdue check with safe retries. Share job outcomes with 2.4, then add permitted notification delivery and clearer locker status.

### Stage 2.4 — Improve staff visibility

Start with a staff view of overdue items, at-risk bookings, and outcomes. Add utilization reporting, more failure scenarios, and stronger concurrency and monitoring checks.

## Phase 3 — Full university product (P2)

After P1, review the results and agree on the first university pilot before starting P2. Keep real system access and hardware work subject to institutional approval.

A and C can start the shared rules and lifecycle work in parallel. D can test recovery with simulated events while B prepares the approved integration. Each lead stays responsible for their full feature through pilot verification.

### Stage 3.1 — Expand campus operations

Start with a second department and its own equipment pool and rules. Agree on location, identity, and permissions before adding more campuses, institutional sign-in, training, approvals, deposits, and loan limits.

### Stage 3.2 — Manage equipment through its lifecycle

Start with kit components and maintenance for damaged returns. Share condition and maintenance events with 3.3. Later cover missing items, recurring loans, and more pickup methods.

### Stage 3.3 — Handle more disruptions

Start with a simulated damaged return and show how to recover the next booking. Later cover locker faults, wrong loads, no-shows, and demand spikes, with clear escalation and retry rules.

### Stage 3.4 — Connect real systems

Prove one workflow with an approved pilot integration. Use 3.1 access rules and agree on trusted events with 3.2 and 3.3. Later expand to inventory and identity integrations, notifications, and secure smart-locker adapters. Validate device events and physical custody with pilot partners.

## Phase 4 — Multi-organization platform (P3)

### Stage 4.1 — Separate organizations and policies

Give each organization isolated data, its own roles and policies, and configurable audit and retention settings.

### Stage 4.2 — Prepare for enterprise operations

Add reliability targets, backups and restore tests, incident response, and privacy and sector reviews.

### Stage 4.3 — Validate the commercial offering

Measure staff effort and recovery outcomes with real pilots. Use the results to decide on licensing, onboarding, and which integrations to support.
