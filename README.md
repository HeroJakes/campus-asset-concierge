# Campus Asset Concierge

When shared equipment comes back late, the next borrower can lose their booking. Campus Asset Concierge aims to flag that conflict and help staff find an available substitute or escalate the case.

**Current status** — Borrowers can find and confirm a reservation through the local API. Staff can load it into a virtual locker, and the borrower can unlock it with a one-time code and confirm pickup on the local locker page. The borrower can also return an item through the locker, and staff verify its condition to close the loan. The shared foundation provides sign-in, a local test clock, and two resettable scenarios. Overdue recovery is planned.

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

## Run the local prototype

With the emulator running, set four distinct local passwords using ASCII characters and start the API on loopback. For PowerShell 7:

```powershell
$env:FIRESTORE_EMULATOR_HOST = '127.0.0.1:8080'
$env:LOCAL_BORROWER_A_PASSWORD = Read-Host 'Password for borrower-a' -MaskInput
$env:LOCAL_BORROWER_B_PASSWORD = Read-Host 'Password for borrower-b' -MaskInput
$env:LOCAL_STAFF_PASSWORD = Read-Host 'Password for equipment-staff' -MaskInput
$env:LOCAL_OPERATOR_PASSWORD = Read-Host 'Password for local-operator' -MaskInput
uv run --locked uvicorn campus_asset_concierge.api.app:create_app --factory --host 127.0.0.1
```

Open [local API docs](http://127.0.0.1:8000/docs) and use **Authorize** to enter a local username and password. As `local-operator`, send `{"scenario":"spare_available"}` or `{"scenario":"spare_unavailable"}` to `POST /local-test/reset`. Use `GET /local-test/clock` to verify the reset and `POST /local-test/clock/advance` with `{"minutes":90}` to advance time. Borrowers can read their own seeded bookings at `GET /reservations`.

To try booking after a reset, authorize as `borrower-a` and send this body to `POST /reservation-offers`.

```json
{"category":"projector","pickup_at":"2026-11-07T12:00","duration_minutes":60}
```

Review the unit and Malaysia-time window. Use the returned ID in `POST /reservation-offers/{offer_id}/confirm`, then check `GET /reservations`.

To try pickup, book with `"pickup_at":"2026-11-07T10:30"` instead, then open the [locker page](http://127.0.0.1:8000/locker). Sign in as `equipment-staff` and select **Confirm loading**. In a private browser window, open the same page as `borrower-a` to see the code. Use `POST /local-test/clock/advance` with `{"minutes":30}` to reach the pickup time, refresh the page, enter the code, and confirm pickup.

To try a return, use `borrower-a`, who starts each reset with Projector A on loan. On the borrower locker page, select **Return this item** to get a return code and compartment, enter the code to unlock it, and confirm the drop-off. Then sign in as `equipment-staff` and select **Pass** or **Fail** under "Returns to check". A pass frees the unit; a fail puts it on hold.

Run `uv run --locked pytest` in a shell with `FIRESTORE_EMULATOR_HOST` set to test sign-in, resets, booking, pickup, and return, including two borrowers competing for the last unit.

GitHub Actions runs the same tests with the Firestore emulator on pull requests into `main`.

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
