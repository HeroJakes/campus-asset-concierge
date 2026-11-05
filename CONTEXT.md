# Design context

## Stage 2.2 — Richer equipment matching

Status: scope confirmed and implementation plan written. Implementation has not started.

### Agreed scope

- Capture borrower requirements and use them for both new bookings and overdue-recovery substitutes.
- Keep matching within one equipment category and the existing single location.
- Defer multiple booking choices, bundles, alternate locations, waitlists, and QR pickup.

### Agreed matching rules

- Projectors support two optional borrower requirements: HDMI support and built-in speakers. The user chose these familiar yes/no capabilities instead of brightness. Numeric matching is outside this stage.
- Raspberry Pi kits keep category-only matching in this stage.
- Supplied requirements are mandatory. Do not silently relax them.
- If no suitable unit exists, a new booking reports no match and recovery creates a staff-owned escalation.
- When no requirements are recorded, including existing bookings, keep category-only matching. Do not infer requirements from the assigned asset.
- If several units qualify, use the existing stable asset-ID order and offer the first suitable unit. Do not add ranking or a list of choices.
- An unknown asset capability cannot satisfy a required capability. It does not exclude the unit when that capability is not required.
- Save borrower requirements with the offer and reservation. Recheck them at booking confirmation and staff reassignment approval.
- If the shown unit no longer qualifies, reject the action and keep the booking unchanged. Choosing another unit requires a fresh offer or proposal and confirmation or staff approval.
- Chat captures requirements the borrower mentions; it does not always ask about both capabilities. Show the requirements with the offer before confirmation.
- A capability that is not required is unrestricted: an asset may have it or lack it. Do not treat this as a request to exclude that capability.
- Add a staff-only "Check substitutes again" action for a pending proposal. Recheck the reservation's requirements and current availability, then replace the pending proposal or create a staff-owned escalation. The booking remains unchanged until staff approve a suitable proposal.

### Scope confirmation

The user accepted the recommendations for Q3–Q9, chose HDMI support and built-in speakers for Q2, and confirmed the complete scope before authorizing the plan.

The [Stage 2.2 implementation plan](docs/STAGE_2_2_IMPLEMENTATION.md) covers the shared matching rule, saved requirements, API and agent tools, recovery and reassignment, staff and borrower displays, fictional fixture data, and acceptance checks. It reuses the current category, availability, authorization, transaction, and audit rules.
