# Stage 1.0 — Shared rules and demo data

These decisions give all four feature leads the same starting point. See the [build stages](BUILD_STAGES.md) for feature ownership and the [glossary](../GLOSSARY.md) for shared terms.

## Readiness and follow-up

Stage 1.0 can start locally. Use demo accounts, fictional data, and the Firestore emulator. The local prerequisites are Python through `uv`, the Firebase CLI, and Java for the emulator. Follow the [README setup steps](../README.md) and verify the emulator starts before testing fixture resets.

| Pending item | How we proceed now | What to revisit when available |
| --- | --- | --- |
| Gemini Enterprise licence and event sign-in | Use local demo usernames and passwords. Keep borrower, staff, and demo operator checks in the backend. | In Stage 1.5, verify the identity Gemini Enterprise passes to the agent. Map approved event accounts to the existing roles and retest booking ownership and staff-only actions. Update this doc and any affected stage docs with the verified setup. |
| Agent Runtime access and Cloud credits | Run the foundation locally against the emulator. | In Stage 1.5, confirm permissions and quota for agent registration. If hosting is approved, verify the hosted backend and data setup, then update the setup and demo instructions. |
| Gemini model access for live local chat | Test role checks and fixture resets directly. | Run a local chat smoke test once model access is available. Verify that tool calls use the signed-in actor and follow the same permission rules. |

Before closing Stage 1.0, add any other deferred dependency here with the local approach and the check to run once it is available.

## Reservation, pickup, and return

- Track the reservation, locker compartment, loan, and asset condition separately.
- A confirmed reservation becomes ready for pickup after staff confirm loading. A valid one-time code unlocks the compartment. Separate pickup confirmation starts the loan.
- When a late return threatens the next booking, keep that reservation confirmed and flag it as at risk. Block pickup until its assigned unit is available and staff have loaded it. A substitute proposal leaves the booking unchanged in P0.
- After staff receive an item, keep it unavailable until the condition check finishes. A pass closes the loan and returns the unit to circulation. A fail closes the loan as returned and puts the unit on hold for staff follow-up.

## Demo sign-in and permissions

| Demo role | Allowed actions |
| --- | --- |
| Borrower | Request and confirm their own reservations, view their own bookings, and collect their assigned equipment. |
| Staff | Confirm loading, verify returns and condition, and view escalations. |
| Demo operator | Reset the demo and advance its clock using a separate demo admin permission. |

Use two fictional borrower accounts and one fictional staff account for local sign-in with demo usernames and passwords. The backend determines roles from the signed-in account and checks permissions on each action. Keep demo passwords out of Git. The locker page uses this local sign-in for P0.

When event access arrives, verify which sign-in the organizers use and what trusted identity Gemini Enterprise provides to the agent. Then map approved event accounts to the same backend roles. Keep role selection outside chat.

## Resettable demo data

Use one campus location, one virtual locker with two compartments, two projectors, and one Raspberry Pi kit. Use the same starting clock and booking windows on each reset.

| Scenario | Starting data | Expected result after the loan goes overdue |
| --- | --- | --- |
| Spare available | Borrower A has Projector A on loan. Borrower B has the next reservation for Projector A. Projector B is free and eligible. | Flag the reservation as at risk, queue one reminder, and record a verified proposal for Projector B. |
| Spare unavailable | Same starting point, with Projector B booked for an overlapping window. | Flag the reservation as at risk, queue one reminder, and create a staff-owned escalation. |

In both scenarios, Borrower A's loan stays overdue and Borrower B's reservation keeps its original assignment.

## Foundation setup

See the [README](../README.md#run-the-stage-10-demo) for local setup and API checks. The four feature leads can use the `spare_available` and `spare_unavailable` scenarios. Both start at 10:00 MYT. The active loan is due at 11:00 MYT, and the next pickup is at 12:00 MYT.

The foundation checks demo credentials and protects clock and reset actions with the demo operator role. Borrowers can read their own seeded reservations. The feature leads add and test the lending and recovery actions in their own stages.
