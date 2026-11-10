# Campus Asset Concierge

A late equipment return can leave the next student without the projector they booked.
Campus Asset Concierge detects that conflict early and gives staff a verified
replacement to approve, or a clear escalation when no suitable spare exists.

## Problem

Universities lend shared equipment — projectors, Raspberry Pi kits, cameras, and
more. When an item comes back late, the next person who booked it loses their slot.
Today staff usually notice the clash only when the borrower turns up, then scramble
to find a spare or apologise by hand. Nothing spots the conflict early or offers a fix.

## Solution

A booking-and-recovery service for shared campus assets, designed to run with
**Gemini Enterprise** where it fits:

- **Borrower chat (Gemini agent)** — a student books in plain language ("a projector
  with HDMI, 2–3pm today"). The agent matches the requirements, offers a unit, and
  confirms the booking.
- **Overdue-recovery workflow (the "maximizing" pattern)** — runs on a daily schedule.
  It finds loans that are overdue *and* threaten an upcoming booking, then either
  proposes a **verified substitute** or **escalates to staff**, each behind an
  approval step. Read a source, take action, keep a human in the loop, run 24/7.
- **Connectors** — our lending backend is exposed as an **MCP connector** (third-party)
  that the agent and workflow call; **Gmail** (first-party) drafts recovery emails.
- **Virtual locker page** — a small web page where staff load items and borrowers
  pick up and return them with a one-time code.

The same flow extends to other shared assets — rooms, lab kits, sports gear — by
adding a category rather than rebuilding the agent.

## What works today

The lending backend and virtual locker are live on Vercel with fictional data in Firestore.

- Reserve a projector or Raspberry Pi kit, with optional HDMI and speaker requirements.
- Load, collect, and return equipment using one-time codes and a staff condition check.
- Detect overdue loans, propose a substitute, and apply it only after staff approval.
- Run recovery daily through cron-job.org at 09:00 Malaysia time; the job is verified working.

The MCP endpoint exposes these lending tools for the Gemini Enterprise agent.
**Gemini Enterprise chat, its workflow, and recovery email remain pending.**
The Gemini API borrower chat is deployed; a live status query passed on November 10.
Gmail API pickup/return-code delivery is enabled on the hosted demo. Sender
authorization and a direct test email to Borrower A's inbox are verified; the
automatic code flow still needs a live rehearsal. It does not require Gemini
Enterprise. See [Gmail demo setup](docs/GMAIL_DEMO.md).

The borrower interface includes responsive side-by-side pickup/return panels,
compartment states, and six-box code entry. An interim Gemini API booking chat reuses the booking rules,
requires the borrower to confirm an offer, and keeps one-time codes out of model
status results. Its page includes quick prompts, booking summaries, and tips.
Replies show bold text and animated thinking dots. The latest 100 chat entries are
saved per borrower in the current browser, with a Clear chat button; they do not sync across
devices. Signing out returns to the login page. Passwordless dev login is removed.
Gemini availability and quotas can limit chat; API booking remains the fallback.
Without Gmail configured, the borrower page links to the borrower's own status API
for codes and labels this as a demo stand-in. With Gmail enabled, loading and
return requests email the existing code. The page shows delivery status and lets
the borrower retry a definite failure. Uncertain sends are not retried automatically.

Staff Active bookings includes loans without a reservation record, overdue items,
and returns awaiting a condition check. Requesting a return reserves a compartment;
it does not mean the item has been dropped off.

## How we built it (and what we researched)

1. **Read the brief first.** We studied the enablement session and event rules:
   Gemini Enterprise is encouraged, "maximizing" workflows are favoured, and
   connectors are the scoring axis. That shaped the agent-plus-workflow design.
2. **Kept the lending logic, exposed it as a connector.** We built the booking and
   recovery rules once and wrapped the backend as an **MCP server** so the Gemini
   agent and workflow reuse it instead of us rebuilding the logic as a chat script.
3. **Built and proved the backend.** Python 3.12, FastAPI, and Cloud Firestore
   (emulator for local dev and CI). We verified booking, pickup, returns, and both
   recovery outcomes end to end, and deployed it live on Vercel.
4. **Made the Gemini build paste-ready.** The agent instruction, tool list, email
   templates, and a two-scenario demo story are written up so the Gemini Enterprise
   app can be assembled the moment the licence arrives — see the [demo guide](docs/DEMO_GUIDE.md).

## Teamwork

We are a team of four. Each person led one feature end to end — its rules, screens
or tools, tests, and demo evidence — and reviewed the others' pull requests before merging:

- **Ivan Lee (lead)** — find-and-reserve booking flow and richer requirement matching
  (HDMI, speakers); coordinated the Gemini Enterprise connector work.
- **Bing Hang** — load-and-collect pickup flow and the virtual locker web page.
- **Jordan** — equipment returns and staff condition checks.
- **Yew Shan** — overdue recovery and substitute reassignment; coordinated the rehearsal and demo.

## Impact

- **Target: resolve 80% of overdue-driven booking conflicts automatically.** The
  workflow hands staff a ready-to-approve substitute instead of a manual scramble,
  and escalates only the cases where no spare exists.
- **Better for students:** no silent lost bookings; a substitute is offered before
  the pickup time.
- **Less manual work for staff:** detection, substitute-finding, and the first draft
  of every email are automated, with staff keeping the final approval.

> The 80% figure is our projected target for the prototype, based on the seeded
> scenarios. We will replace it with measured numbers once the app sees real use.

## Try the demo

The [login page](https://campus-asset-concierge-demo.vercel.app/login) is live.
Use **Try an account** to fill in a borrower or staff login. The page shows the
test usernames and passwords; no sign-up is needed. Browser sessions last
eight hours; sign out before switching accounts in the same browser session.

1. Open the [virtual locker](https://campus-asset-concierge-demo.vercel.app/locker).
   Choose Borrower A, Borrower B, or equipment staff on the login page.
2. As staff, review the overdue Projector A loan and the replacement proposal.
   Approve it to protect the next student's booking.
3. Follow the [demo guide](docs/DEMO_GUIDE.md) for Borrower A's booking, pickup,
   return, and the separate no-spare scenario.

The [API docs](https://campus-asset-concierge-demo.vercel.app/docs) provide booking
until Gemini is connected; the borrower locker page has no booking form.
The [MCP endpoint](https://campus-asset-concierge-demo.vercel.app/mcp) is for tool
clients and is not a chat page.

The hosted clock is fixed at **November 7, 2026, 11:01 MYT**. The live document is
`demo/hackathon-20261111`. A protected operator reset restores the showcase between
runs. MCP has no authentication for this fictional demo. Browser users sign in
through the login page; REST clients and operator tools still support HTTP Basic.
Gemini app and video links will be added after verification and recording.

## Project guide

| Document | Use it for |
| --- | --- |
| [Build stages and progress](docs/BUILD_STAGES.md) | What is implemented, what is left, and who owns it |
| [Development](docs/DEVELOPMENT.md) | Architecture, lending rules, local startup, and emulator tests |
| [Demo guide](docs/DEMO_GUIDE.md) | Presentation sequence and Gemini/Gmail assembly |
| [Operations](docs/OPERATIONS.md) | Deployment, credentials, reset, cron, and verification |
| [Gmail demo setup](docs/GMAIL_DEMO.md) | Authorize a sender and deliver pickup/return codes |
| [Submission checklist](submission/README.md) | Video, deck, app link, and write-up |

With your local `.env` configured, run `uv run dev` from the repository root and
open [the login page](http://127.0.0.1:8000/login). It reloads when code changes.
The page shows the same borrower and staff test accounts as the hosted demo.
This uses the database selected in `.env`; it does not seed or reset data.
For first-time setup, follow [Development](docs/DEVELOPMENT.md#local-setup).
No cloud account is needed for emulator-based development.

An [emulator-only collection layout](docs/DEVELOPMENT.md#collection-layout-review-emulator-only)
is available for review with `uv run dev-collections`. It separates equipment,
bookings, loans, locker access, and recovery records. Hosted Firestore stays on
the existing layout; no cloud migration has been approved.
