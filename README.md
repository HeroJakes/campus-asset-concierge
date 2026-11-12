# Campus Asset Concierge

**Track 1 — Smart Campus & Student Experience**

Students book shared campus equipment by chatting with an AI assistant, then collect and
return it from a locker with one-time codes. When an item comes back late, the system
catches it before the next student's booking and suggests a spare for staff to approve.

**Live demo:** https://campus-asset-concierge-demo.vercel.app/login
(click **Try an account**. Test logins are shown on the page.)

## The problem

When borrowed equipment comes back late, the next student who booked it is left without
it. Staff usually find out only when that student turns up, and then search for a spare by hand.

## What it does

- **MiMi, the booking assistant** (Gemini API): understands "a projector with HDMI, 2–3pm",
  asks for missing details, checks availability with tools, and offers a unit.
  The booking happens only when the student presses **Confirm**.
- **Locker pickup and return:** staff load the item, and the student gets a one-time code
  by email (Gmail API). Returns use a new code, and staff check the item's condition
  before it is lent again.
- **Overdue recovery:** a daily check finds late loans that put a future booking at risk.
  It proposes a checked spare for staff to approve, or flags the case to staff when no spare fits.
- **Staff dashboard:** items to load, the locker, returns to check, recovery, bookings,
  equipment use, and an activity log.
- **MCP server:** the same lending tools at `/mcp`, so other AI tools can use them.

The AI never books, changes a booking, or sees a code on its own. Staff approve every change.

## Try it

1. Sign in as **equipment-staff**. Projector A is overdue, and a spare (Projector B) is proposed.
   Click **Review substitute proposal**, then **Approve and apply**.
2. Sign in as **borrower-a** in a private window. Open **MiMi** and ask for a Raspberry Pi kit
   today from 11:01 for one hour, then confirm.
3. As staff, click **Confirm loading**. As the borrower, enter the code, collect the kit, then return it.

The full walkthrough is in the [demo guide](docs/DEMO_GUIDE.md).

## Live or simulated

| Live | Simulated for the demo |
| --- | --- |
| MiMi chat, booking, pickup/return codes, code emails, recovery, staff approval, return checks | People and equipment (fictional), the clock (fixed at Nov 7 2026, 11:01), the locker (no hardware), overdue reminder emails |

We use the Gemini API because Gemini Enterprise access was not provided.

## Built with

Python 3.12, FastAPI, Cloud Firestore, Gemini API, Gmail API, MCP, hosted on Vercel.
The recovery check runs daily at 09:00 MYT through cron-job.org.

## Run locally

```bash
cp .env.example .env   # fill in your own values
uv run dev             # http://127.0.0.1:8000/login
```

Tests need the Firestore emulator. See [Development](docs/DEVELOPMENT.md).

## Team

| Member | Led |
| --- | --- |
| Ivan Lee | Booking, requirement matching, Gemini integration |
| Bing Hang | Pickup flow and locker interface |
| Jordan | Returns and condition checks |
| Yew Shan | Overdue recovery and substitutes |

## More docs

[Build stages](docs/BUILD_STAGES.md) · [Development](docs/DEVELOPMENT.md) ·
[Demo guide](docs/DEMO_GUIDE.md) · [Operations](docs/OPERATIONS.md) · [Gmail setup](docs/GMAIL_DEMO.md)
