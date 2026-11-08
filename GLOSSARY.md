# Campus Asset Concierge

Shared language for the campus equipment lending prototype. These are the terms
specific to this project; use them consistently in code, UI text, and docs.

## Booking lifecycle

**Offer**:
A specific unit the system proposes for a borrower's request, held but not yet
booked. An offer becomes a reservation only when the borrower confirms it.
_Avoid_: suggestion, quote, hold.

**Reservation**:
A confirmed booking of one unit for one borrower and one time window.
_Avoid_: booking (fine as a casual verb — "book a projector" — but the entity is a reservation).

**Loan**:
An item in a borrower's possession after pickup, until it is returned and checked in.
_Avoid_: checkout, rental, borrow.

## People

**Borrower**:
A student who reserves, picks up, and returns equipment. Only `borrower-a` and
`borrower-b` exist in the fictional demo.
_Avoid_: user, client.

**Equipment staff**:
The role that loads items, runs condition checks on returns, and approves recovery
actions. Never sees one-time codes.
_Avoid_: admin, librarian.

## Locker and handover

**Compartment**:
One slot in the locker that holds a single item. Shown with a state (loaded,
open, returned) on the locker page.
_Avoid_: door, locker (the whole cabinet is the locker; one slot is a compartment).

**One-time code**:
A single-use code, delivered to the borrower by email, that unlocks a compartment
for one pickup or one return. Never shown on the kiosk and never visible to staff.
_Avoid_: PIN, password, OTP.

**Pickup**:
Collecting a loaded item by entering its one-time code, then confirming. Starts the loan.

**Return**:
Dropping a loaned item into a compartment by entering its one-time return code,
then confirming. The loan ends only after staff pass the condition check.

## Recovery

**Overdue recovery**:
The scheduled pass that detects loans which are overdue *and* threaten an upcoming
reservation, then produces a substitution proposal or an escalation.
_Avoid_: reminder, chase.

**Substitution proposal**:
A verified alternative unit offered to protect a threatened reservation when an
overdue loan blocks the original item. Takes effect only after staff approval.
_Avoid_: swap, replacement.

**Escalation**:
The outcome when no eligible substitute exists, so staff must act directly.

## Interfaces

**Assistant**:
The borrower-facing chat that understands a plain-language request and produces an
offer for the borrower to confirm. It books; it does not pick up, return, or recover.
_Avoid_: bot, agent (reserve "agent" for the Gemini Enterprise build).

**Connector (MCP)**:
The backend exposed as tools a Gemini Enterprise agent can call. The same booking
and recovery logic the Assistant and locker page use.
