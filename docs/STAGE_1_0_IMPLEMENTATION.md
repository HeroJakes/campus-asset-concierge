# Stage 1.0 — Shared rules and demo data

These decisions give all four feature leads the same starting point. See the [build stages](BUILD_STAGES.md) for feature ownership and the [glossary](../GLOSSARY.md) for shared terms.

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

1. Share the rules and fixture names with the four feature leads.
2. Prepare the fictional accounts and both local data fixtures, with a repeatable reset to the starting clock.
3. Verify the two scenarios reset consistently and the borrower, staff, and demo operator permissions stay separate. The feature leads build and test the lending and recovery flows in their own stages.
