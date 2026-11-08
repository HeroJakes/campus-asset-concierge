# Campus Asset Concierge

A late equipment return can leave the next student without the projector they booked.
Campus Asset Concierge detects that conflict and gives staff a verified replacement
to approve, or a clear escalation when no suitable spare exists.

## What works today

The lending backend and virtual locker are live on Vercel with fictional data in Firestore.

- Reserve a projector or Raspberry Pi kit, with optional HDMI and speaker requirements.
- Load, collect, and return equipment using one-time codes and a staff condition check.
- Detect overdue loans, propose a substitute, and apply it only after staff approval.
- Run recovery daily through cron-job.org at 09:00 Malaysia time; the owner confirmed the job works.

The MCP endpoint exposes these lending tools for the planned Gemini Enterprise
agent. **Gemini chat, its workflow, and Gmail delivery are still pending the licence
and integration checks.** Automatic pickup/return-code email is not connected yet.

## Try the demo

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

## How it fits together

The planned Gemini agent handles the conversation and calls our MCP tools.
The existing FastAPI services enforce lending rules and save transactions in
Firestore. The locker page uses those same services. Recovery emails are planned
through Gemini's Gmail connector; the current scheduler runs backend recovery only.

The intended benefit is fewer disrupted bookings and less manual substitute-finding.
No measured recovery-rate claim is made yet.

## Team

Ivan Lee leads reservations and matching; Bing Hang leads pickup and the locker;
Jordan leads returns; Yew Shan leads recovery and rehearsal. The team reviews each
other's changes and tests the connected flow.

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
