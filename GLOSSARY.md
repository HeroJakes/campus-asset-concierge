# Campus Asset Concierge

Campus Asset Concierge tracks shared equipment from reservation through return and helps staff handle lending exceptions.

## Language

**Equipment requirement**
A borrower-specified capability that an asset unit must have for a reservation. The requirement also applies to any substitute for that reservation.
_Avoid_: preference

**Asset specification**
A recorded capability of an asset unit, such as HDMI support or built-in speakers.

**Asset unit**
A single tracked piece of equipment, such as Projector A. A category such as projector can contain several asset units.

**Reservation**
A confirmed booking for an asset unit and a time window. A reservation can exist before the borrower collects the asset.

**Reservation offer**
An available asset unit, pickup location, and time window shown to a borrower for confirmation. The offer does not hold the unit. Availability is checked again when the borrower confirms.

**One-time code**
A code that lets one borrower unlock the locker compartment holding their reserved asset for pickup. It works once, from the pickup time until 30 minutes later.
_Avoid_: pickup code

**Return code**
A one-time code that lets a borrower unlock a locker compartment to drop off an item they are returning. It works once, from the moment it is issued until 30 minutes later.

**Loan**
The record of an asset in a borrower's custody. It starts when pickup is confirmed and stays open until the return check is done.

**Return check**
The staff inspection of a returned asset that closes its loan. A pass returns the unit to service; a fail places it on condition hold. A loan is awaiting its return check from when the borrower drops the item off until staff inspect it.
_Avoid_: inspection, QA

**Condition hold**
The status of an asset that failed its return check. The returned loan is closed, and the asset stays unavailable pending staff follow-up.

**At-risk reservation**
A future booking that may be disrupted because its assigned asset is overdue.

**Substitution proposal**
A verified option to fulfill an at-risk reservation with another eligible asset unit. The proposal leaves the reservation unchanged until a reassignment is approved and applied.

**Escalation**
A case assigned to a staff owner when the system cannot find an eligible substitute.
