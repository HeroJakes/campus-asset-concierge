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
**Gemini chat, its workflow, and Gmail delivery are still pending the trial licence
and integration checks.** Automatic pickup/return-code email is not connected yet.

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

The borrower/staff login page is implemented on `feat/borrower-staff-login` and
awaits deployment. It uses the existing account credentials at `/login`, with a
role selector, an eight-hour browser session, and sign-out. The live release below
still uses its original Basic login until that change is reviewed and deployed.

1. Open the [virtual locker](https://campus-asset-concierge-demo.vercel.app/locker).
   Staff and borrower credentials are supplied privately.
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
runs. MCP has no authentication for this fictional demo; locker and REST actions
use HTTP Basic. Gemini app and video links will be added after verification and recording.

## Project guide

| Document | Use it for |
| --- | --- |
| [Build stages and progress](docs/BUILD_STAGES.md) | What is implemented, what is left, and who owns it |
| [Development](docs/DEVELOPMENT.md) | Architecture, lending rules, local startup, and emulator tests |
| [Demo guide](docs/DEMO_GUIDE.md) | Presentation sequence and Gemini/Gmail assembly |
| [Operations](docs/OPERATIONS.md) | Deployment, credentials, reset, cron, and verification |
| [Submission checklist](submission/README.md) | Video, deck, app link, and write-up |

For local use, follow [Development](docs/DEVELOPMENT.md#local-setup).
No cloud account is needed for emulator-based development.
