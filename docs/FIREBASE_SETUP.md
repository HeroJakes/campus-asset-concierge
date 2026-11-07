# Firebase setup

The Firebase project `campus-asset-concierge` was created on 2026-11-06 for the free Spark plan. No billing account was linked.

- [Project console](https://console.firebase.google.com/project/campus-asset-concierge/overview)
- Database: `(default)`, Standard edition, Firestore Native mode.
- Location: Singapore (`asia-southeast1`). This database location cannot be changed.
- Data: `demo/current` contains the fictional `spare_available` scenario, seeded once on 2026-11-06. No credentials were uploaded.
- Security Rules: all direct client reads and writes are denied. Python server access uses Google Cloud IAM permissions instead of these rules.

## Local development

Use cloud-connected startup below for the shared demo database. Keep using the README's emulator commands with `demo-campus-asset-concierge` for automated tests and resettable rehearsals. The `spark-demo` alias in `.firebaserc` points to the real project; it is not the default project.

To check the database or publish the checked-in rules:

```powershell
npx -y firebase-tools@latest firestore:databases:get '(default)' --project campus-asset-concierge
npx -y firebase-tools@latest deploy --only firestore:rules --project campus-asset-concierge --dry-run --non-interactive
npx -y firebase-tools@latest deploy --only firestore:rules --project campus-asset-concierge --non-interactive
```

## Connecting the backend

`LocalStateStore` now uses the **emulator** when `FIRESTORE_EMULATOR_HOST` is set (local dev, tests, CI) and **hosted Firestore** when it is not. For hosted mode, set:

- `GOOGLE_CLOUD_PROJECT=campus-asset-concierge`
- `GOOGLE_APPLICATION_CREDENTIALS=<path to the service-account key JSON>` — kept out of Git, set as a host secret.

Do **not** set these for local tests or `reset` commands; those stay on the emulator so they never touch the hosted database. The real connection, create-only seed, and read-back were verified on 2026-11-06. The demo clock starts at `elapsed_minutes=0`; recovery has not run. See [Deployment plan](DEPLOYMENT_PLAN.md) for the completed checks and repeatable commands.

## Cloud-connected local startup

The app runs on your laptop and reads and writes the shared cloud database directly. It does not need public hosting. Cloud data and emulator data do not sync.

On Ivan's machine, `.env.cloud` contains the local credential path and demo passwords. Git ignores this file. Open it locally to find the passwords for `borrower-a`, `borrower-b`, and `equipment-staff`; do not share or commit it.

For another machine, create a private `.env.cloud` with these settings, filling in a valid credential path and three passwords:

```dotenv
GOOGLE_CLOUD_PROJECT=campus-asset-concierge
GOOGLE_APPLICATION_CREDENTIALS="C:/path/to/your/service-account-key.json"
LOCAL_BORROWER_A_PASSWORD=your-borrower-a-password
LOCAL_BORROWER_B_PASSWORD=your-borrower-b-password
LOCAL_STAFF_PASSWORD=your-staff-password
LOCAL_OPERATOR_PASSWORD=
```

Leave the operator password empty to disable operator reset and clock actions in this profile. This also means the stored demo clock will not advance by itself. Do not put `FIRESTORE_EMULATOR_HOST` in this file, even with an empty value: the Firestore SDK treats its presence as an emulator setting.

Start from the repo root in PowerShell:

```powershell
Remove-Item Env:FIRESTORE_EMULATOR_HOST -ErrorAction SilentlyContinue
uv run --locked --env-file .env.cloud uvicorn campus_asset_concierge.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Open [the locker](http://127.0.0.1:8000/locker) or [the API docs](http://127.0.0.1:8000/docs). Bookings and locker actions use `campus-asset-concierge/(default)/demo/current`. Stop the server with Ctrl+C before switching profiles. Start tests in a separate shell with the emulator configuration, without `--env-file .env.cloud`.

Verified on 2026-11-07: a read of the cloud document found the `spare_available` scenario with 3 assets, 1 reservation, and 1 loan. No seed or replacement was run during setup.

## What still needs work

Backend hosting (Render or similar) and the Gemini integration are still pending.

Firebase Authentication, web app registration, Storage, and backend hosting are not set up. The Python backend does not need a Firebase browser SDK configuration. Cloud Run requires billing and is outside this free-plan setup. See [Firebase pricing plans](https://firebase.google.com/docs/projects/billing/firebase-pricing-plans).
