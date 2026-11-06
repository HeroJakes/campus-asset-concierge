# Firebase setup

The Firebase project `campus-asset-concierge` was created on 2026-11-06 for the free Spark plan. No billing account was linked.

- [Project console](https://console.firebase.google.com/project/campus-asset-concierge/overview)
- Database: `(default)`, Standard edition, Firestore Native mode.
- Location: Singapore (`asia-southeast1`). This database location cannot be changed.
- Data: `demo/current` contains the fictional `spare_available` scenario, seeded once on 2026-11-06. No credentials were uploaded.
- Security Rules: all direct client reads and writes are denied. Python server access uses Google Cloud IAM permissions instead of these rules.

## Local development

Keep using the README's emulator commands with `demo-campus-asset-concierge`. The new cloud database does not change local development or tests. The `spark-demo` alias in `.firebaserc` points to the real project; it is not the default project.

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

## What still needs work

Backend hosting (Render or similar) and the Gemini integration are still pending.

Firebase Authentication, web app registration, Storage, and backend hosting are not set up. The Python backend does not need a Firebase browser SDK configuration. Cloud Run requires billing and is outside this free-plan setup. See [Firebase pricing plans](https://firebase.google.com/docs/projects/billing/firebase-pricing-plans).
