# Campus Asset Concierge

When shared equipment comes back late, the next borrower can lose their booking. Campus Asset Concierge aims to flag that conflict and help staff find an available substitute or escalate the case.

**Current status** — The local demo foundation supports sign-in, a demo clock, and two resettable scenarios. Booking, locker pickup, and overdue recovery are planned.

The organizers reported a delay in Gemini Enterprise licences with no confirmed date. Cloud credit details are still pending. The lending features and locker page can be built locally while the in-app integration waits for access.

Gemini Enterprise is the planned chat interface. Our prototype will have a separate virtual locker page for staff loading, one-time code entry, and pickup confirmation.

See the [Build Stages](docs/BUILD_STAGES.md) for team ownership, the prototype stop line, and the full roadmap.

## Local setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run these commands from the repository root. uv can install the pinned Python version if needed.

```sh
uv sync --locked
uv run --locked python -c "import campus_asset_concierge; print('Package import OK')"
```

Local setup works without a Google Cloud or Gemini Enterprise account.

## Firestore emulator

For local database development, install the [Firebase CLI and emulator prerequisites](https://firebase.google.com/docs/emulator-suite/install_and_configure), then start the emulator with a demo project ID.

```sh
firebase emulators:start --only firestore --project demo-campus-asset-concierge
```

## Run the Stage 1.0 demo

With the emulator running, set four distinct demo passwords using ASCII characters and start the API on loopback. For PowerShell 7:

```powershell
$env:FIRESTORE_EMULATOR_HOST = '127.0.0.1:8080'
$env:DEMO_BORROWER_A_PASSWORD = Read-Host 'Password for borrower-a' -MaskInput
$env:DEMO_BORROWER_B_PASSWORD = Read-Host 'Password for borrower-b' -MaskInput
$env:DEMO_STAFF_PASSWORD = Read-Host 'Password for staff-demo' -MaskInput
$env:DEMO_OPERATOR_PASSWORD = Read-Host 'Password for demo-operator' -MaskInput
uv run --locked uvicorn campus_asset_concierge.api.demo:create_app --factory --host 127.0.0.1
```

Open [local API docs](http://127.0.0.1:8000/docs) and use **Authorize** to enter a demo username and password. As `demo-operator`, send `{"scenario":"spare_available"}` or `{"scenario":"spare_unavailable"}` to `POST /demo/reset`. Use `GET /demo/clock` to verify the reset and `POST /demo/clock/advance` with `{"minutes":90}` to advance time. Borrowers can read their own seeded bookings at `GET /demo/reservations`.

Run `uv run --locked pytest` in a shell with `FIRESTORE_EMULATOR_HOST` set to test sign-in, role checks, and both resets.

## Project layout

```text
src/campus_asset_concierge/
  agent/      ADK agent and typed tool adapters
  api/        FastAPI entry points and request handling
  domain/     Lending rules and workflows
  storage/    Firestore persistence
  templates/  Server-rendered locker views
  static/     Locker styles and browser scripts
tests/        pytest test suite location
```

## Hosting later

Local development is the current target. The intended hosted setup is Cloud Run for FastAPI, Cloud Firestore for shared persistence, and Agent Runtime for the ADK agent registered in Gemini Enterprise. The hosted integration depends on the event account's permissions and quota.
