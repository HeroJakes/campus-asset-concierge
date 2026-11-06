# Campus Asset Concierge

A Gemini Enterprise assistant that stops late equipment returns from costing the next student their booking.

## Problem

Universities lend shared equipment — projectors, Raspberry Pi kits, cameras. When an item comes back late, the next person who booked it loses their slot. Today staff usually notice the clash only when the borrower turns up, then scramble to find a spare or apologise by hand. Nothing spots the conflict early or offers a fix.

## Solution

Campus Asset Concierge is built inside **Gemini Enterprise** (the hackathon's required platform), with no application code at its core:

- **Borrower chat agent** — a student books in plain language ("a projector with HDMI, 2–3pm today"). The agent matches the requirements, offers a unit, and confirms the booking.
- **Overdue-recovery workflow (the "maximizing" pattern)** — runs on a daily schedule. It finds loans that are overdue *and* threaten an upcoming booking, then either proposes a **verified substitute** or **escalates to staff by email**, each behind an approval step. Read a source, take action, keep a human in the loop, run 24/7 — exactly the pattern the judges asked for.
- **Connectors** — our lending backend is exposed as an **MCP connector** (third-party) that the agent and workflow call; **Gmail** is the first-party connector used to draft recovery emails.
- **Virtual locker page** — a small web page where staff load items and borrowers pick up and return them with a one-time code.

All demo data is fictional.

## How we built it (and what we researched)

1. **Read the brief first.** We studied the enablement session and event rules: Gemini Enterprise is mandatory, the solution must be no-code at its core, "maximizing" workflows are favoured, and connectors are the scoring axis. That ruled out shipping a hand-coded app as the deliverable.
2. **Pivoted the architecture.** We kept our lending logic but moved the agent and workflow into Gemini Enterprise, re-using the backend as an MCP connector instead of as the product itself.
3. **Built and proved the connector.** Python 3.12, FastAPI, and Cloud Firestore (emulator for local dev and CI), wrapped as a Streamable-HTTP **MCP server** (FastMCP) in a non-root Docker image. We verified it end to end in a container: booking, pickup, returns, and both recovery outcomes over HTTP.
4. **Made the Gemini build paste-ready.** The agent instruction, tool list, email templates, and a two-scenario demo story are written up so the Gemini Enterprise app can be assembled the moment the licence arrives — see the [build sheet](docs/GEMINI_BUILD_SHEET.md) and [demo script](docs/DEMO_SCRIPT.md).

## Teamwork

We are a team of `<N>` (`<fill in names>`). We split the work by surface and reviewed each other's pull requests before merging:

- **`<Person A — leader>`**: architecture pivot, staff and borrower locker web UI, MCP connector hardening, and docs.
- **`<Person B>`**: core lending rules — reservations, pickups, returns, and overdue recovery.
- **`<Person C>`**: Gemini Enterprise agent and workflow build, and the connectors.
- **`<Person D>`**: demo, video, and pitch deck.

> Fill in the real names and adjust the split before submitting. Every stage ran on a feature branch with a pull request and a teammate review — see [Build Stages](docs/BUILD_STAGES.md).

## Impact

- **Target: resolve 80% of overdue-driven booking conflicts automatically.** The workflow hands staff a ready-to-approve substitute instead of a manual scramble, and escalates only the cases where no spare exists.
- **Better for students:** no silent lost bookings; a substitute is offered before the pickup time.
- **Less manual work for staff:** detection, substitute-finding, and the first draft of every email are automated, with staff keeping the final approval.

> The 80% figure is our projected target for the prototype, based on the seeded scenarios. Replace it with measured numbers once the app sees real use.

## Demo

- **Live app (Gemini Enterprise):** _added once the licence is provisioned._
- **Video (3–4 min):** _link._
- **Architecture:** [Target architecture](docs/ARCHITECTURE.md) · [MCP connector](docs/MCP_LOCAL_CONTAINER.md)

## Run it locally

The local prototype runs the lending backend and the locker page without any Google Cloud or Gemini account. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and the [Firebase Firestore emulator](https://firebase.google.com/docs/emulator-suite/install_and_configure), then start the emulator in one shell:

```sh
uv sync --locked
firebase emulators:start --only firestore --project demo-campus-asset-concierge
```

In a second shell, set four local passwords and start the API on loopback (PowerShell 7):

```powershell
$env:FIRESTORE_EMULATOR_HOST = '127.0.0.1:8080'
$env:LOCAL_BORROWER_A_PASSWORD = Read-Host 'Password for borrower-a' -MaskInput
$env:LOCAL_BORROWER_B_PASSWORD = Read-Host 'Password for borrower-b' -MaskInput
$env:LOCAL_STAFF_PASSWORD = Read-Host 'Password for equipment-staff' -MaskInput
$env:LOCAL_OPERATOR_PASSWORD = Read-Host 'Password for local-operator' -MaskInput
uv run --locked uvicorn campus_asset_concierge.api.app:create_app --factory --host 127.0.0.1
```

Open the [locker page](http://127.0.0.1:8000/locker) and the [API docs](http://127.0.0.1:8000/docs). For the full click-through — booking, pickup, return, and overdue recovery — follow the **[local walkthrough](docs/LOCAL_WALKTHROUGH.md)**. To run the backend as the MCP connector in a container, use the [MCP container guide](docs/MCP_LOCAL_CONTAINER.md).

## Tests

```sh
node --test tests/booking_search.test.cjs   # locker search behaviour
uv run --locked pytest                       # with FIRESTORE_EMULATOR_HOST set
```

GitHub Actions runs both on every pull request into `main`.

## Project layout

```text
src/campus_asset_concierge/
  agent/      ADK agent and typed tool adapters
  api/        FastAPI entry points and request handling
  domain/     Lending rules and workflows
  storage/    Firestore persistence
  templates/  Server-rendered locker views
  static/     Locker styles and browser scripts
tests/        pytest and Node test suites
```

## Status and roadmap

See [Build Stages](docs/BUILD_STAGES.md) for team ownership, the prototype stop line, and the roadmap. Hosted deployment (Cloud Run, managed Firestore, Agent Runtime) is on hold pending the licence and the host decision; the [readiness plan](docs/MCP_CLOUD_RUN_IMPLEMENTATION.md) tracks it. No cloud deployment has started.
