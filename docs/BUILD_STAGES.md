# Build stages and progress

This is the single progress record. Updated November 10, 2026.
The live backend is ready; the Gemini Enterprise app and final submission are not yet complete.

| Read next | Purpose |
| --- | --- |
| [Development](DEVELOPMENT.md) | Architecture, implemented rules, local setup, and tests |
| [Demo guide](DEMO_GUIDE.md) | Rehearsal, Gemini instructions, and email templates |
| [Operations](OPERATIONS.md) | Live configuration, reset, cron, and deployment evidence |

## Stage status

Stage numbers stay stable. "Done" describes the scope shown, not a complete university product.

| Stage | Scope | Current status |
| --- | --- | --- |
| 0.1 | Package, lockfile, and CI scaffold | Done |
| 1.0 | Shared state, roles, fixtures, and test clock | Done |
| 1.1 | Find and reserve equipment | Done: API, ADK tools, and Gemini API borrower chat. Live MCP booking and Gemini status query verified; Enterprise chat pending. |
| 1.2 | Staff loading, one-time code, and confirmed pickup | Done: locker and API, with emulator coverage |
| 1.3 | Borrower drop-off and staff condition check | Done: pass returns equipment to service; fail puts it on hold |
| 1.4 | Overdue recovery | Done: verified substitute proposal or staff-owned escalation |
| 1.5 | Gemini Enterprise integration | Partly done: MCP, Firestore, and Vercel are live. Licence, connector registration, agent, workflow, and Gmail round-trip remain pending. |
| 1.6 | Rehearsal and submission | In progress: fixtures and sequence ready; full recorded rehearsal, deck, video, and final links pending |
| 2.1 | Approve and apply a substitute | Done: staff approval revalidates stock and applies one transaction |
| 2.2 | Richer booking choices | Done for HDMI/speaker matching and staff recheck. Bundles, waitlists, and more locations deferred. |
| 2.3 | Scheduled recovery | Done for the demo: daily cron-job.org POST at 09:00 Malaysia time; owner confirmed it works. Email delivery remains pending. |
| 2.4 | Staff visibility | Partly done: locker overview, bookings search/filter, recovery, and audit activity. Utilization reporting and broader monitoring deferred. |
| 3.1 | More campus departments, locations, and borrowing policies | Deferred; needs pilot approval |
| 3.2 | Maintenance, repairs, kit components, and equipment lifecycle | Deferred |
| 3.3 | Recovery from no-shows, damage, locker faults, and demand spikes | Deferred |
| 3.4 | Institutional identity, inventory, and physical locker integrations | Deferred |
| 4.1 | Multiple organizations and separate policies/data | Deferred |
| 4.2 | Enterprise reliability, restore procedures, and incident response | Deferred |
| 4.3 | Pilot measurements and commercial offering | Deferred |

## Implemented milestones

- Stage 1.5 Gmail API code delivery: automatic email after loading/return requests,
  borrower delivery status, and guarded retries. Uses a separately authorized
  sender without Gemini Enterprise. Merged in PR #34 and deployed November 10;
  sender authorization and direct test-email receipt are verified. Automatic code
  delivery still needs a live rehearsal. See
  [Gmail setup](GMAIL_DEMO.md). Recovery reminders still do not send email.

- On `chore/short-dev-command` (PR #30, awaiting review): `uv run dev`, local test
  account hints, animated assistant dots, bold replies, browser-saved chat per
  borrower, and logout to `/login`. Passwordless dev login is removed. Staff
  bookings include seeded loans and show returns awaiting a check; reserving a
  return compartment is labelled separately from dropping an item off.
- Firestore naming review in PR #30 on `chore/short-dev-command`: separate
  collections under emulator-only environment workspaces, with the existing
  workflows tested against both layouts. Cloud migration and deployment remain
  unapproved; the hosted single-document layout stays in use.

- Reservation, pickup, return, and recovery: PRs #2, #5, #6, and #7.
- MCP tools, substitute approval, capability matching, and local container: PRs #9, #10, #12, and #13.
- Staff overview and Bookings workspace: PR #15.
- Cloud-connected local startup and loopback-only dev login: PR #18.
- Vercel/Firestore compatibility experiment: PR #20; its superseded harness was removed in PR #23.
- Stable Vercel demo and staff-only recovery trigger: PR #21; deployment evidence recorded in PR #22.
- November 8: owner confirmed cron works; obsolete Vercel test project removed. Documentation and leftover-file cleanup is on this branch.
- November 8: borrower/staff login merged in PR #25 and deployed from `84d0dce`. All three accounts, sign-out, secure cookies, Basic clients, and five MCP tools passed 38 live HTTPS checks. Both hosted demo documents were unchanged.

The merged login feature's CI passed **194 Python tests on the Firestore emulator
and five browser tests**. Historical counts differ because tests changed with
each feature. See [operations evidence](OPERATIONS.md#release-evidence)
for the separate live HTTPS checks. Automated tests never use hosted Firestore.

November 8: the hosted login page now lists public borrower/staff test accounts
with form-fill buttons. No sign-up is needed. Operator access stays private;
existing internal passwords and cron credentials are unchanged.

Borrower UI redesign is implemented on `feat/borrower-locker-ui`, awaiting review
and deployment: pickup/return cards, real compartment states, responsive layout,
and six-box code entry. Lending rules and the staff workspace are unchanged.

Borrower booking assistant is implemented on `feat/borrower-assistant`, awaiting
review and deployment: a Gemini-API (free Flash) chat on its own page that books in
plain language over the existing reservation logic — an interim stand-in for the
Gemini Enterprise agent. See [the plan](BORROWER_ASSISTANT_PLAN.md) and
[ADR 0001](adr/0001-interim-gemini-api-chat.md). It degrades to a friendly fallback
when `GEMINI_API_KEY` is absent, so the rest of the app is unaffected.

## Team ownership

| Lead | Main responsibility |
| --- | --- |
| Ivan Lee | Reservation, capability matching, and Gemini integration |
| Bing Hang | Loading, pickup, and locker interface |
| Jordan | Return flow and condition checks |
| Yew Shan | Recovery, reassignment, and rehearsal coordination |
| All four | Feature reviews, integration rehearsal, and submission |

## What to do next

1. Rehearse the hosted Borrower A and staff sequence in the [demo guide](DEMO_GUIDE.md#presentation-sequence).
2. When the licence arrives, register MCP and build the Gemini agent, recovery workflow, and Gmail connector.
3. Rehearse automatic pickup/return email on the hosted demo. Gmail is configured; the borrower-owned API lookup remains the demo fallback.
4. Record both recovery outcomes, the return check, the video, and judge access instructions.
5. Fill the [submission checklist](../submission/README.md). Report measured results rather than presenting the earlier 80% target as evidence.

If no licence arrives, ask the organisers whether the existing ADK agent with Gemini
API access is eligible. That fallback still needs isolated-data configuration and
a full rehearsal. A Gemini-only no-code fallback also requires the licence.

## P0 stop line

Stop the hackathon build when the agreed prototype checks pass. New roadmap work
or a new cloud deployment needs approval.

- Replay booking, staff loading, pickup, and a verified return.
- Show an at-risk booking, a pending substitute proposal, staff approval, and the no-spare escalation.
- Keep chat/locker results consistent with persisted state and audit events.
- Keep last-unit competition, ownership checks, invalid/replayed codes, and repeat actions covered by emulator tests.
- Label fictional data and simulated notifications clearly.
- Record the real Gemini integration result or the approved fallback, and finish submission materials.

Current limits remain deliberate: one item per booking, one location, three asset
units, two virtual compartments, a fixed demo clock, and no physical locker hardware.
