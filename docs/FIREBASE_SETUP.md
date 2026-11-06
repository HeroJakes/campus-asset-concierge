# Firebase setup

The Firebase project `campus-asset-concierge` was created on 2026-11-06 for the free Spark plan. No billing account was linked.

- [Project console](https://console.firebase.google.com/project/campus-asset-concierge/overview)
- Database: `(default)`, Standard edition, Firestore Native mode.
- Location: Singapore (`asia-southeast1`). This database location cannot be changed.
- Data: empty. No demo data or credentials were uploaded.
- Security Rules: all direct client reads and writes are denied. Python server access uses Google Cloud IAM permissions instead of these rules.

## Local development

Keep using the README's emulator commands with `demo-campus-asset-concierge`. The new cloud database does not change local development or tests. The `spark-demo` alias in `.firebaserc` points to the real project; it is not the default project.

To check the database or publish the checked-in rules:

```powershell
npx -y firebase-tools@latest firestore:databases:get '(default)' --project campus-asset-concierge
npx -y firebase-tools@latest deploy --only firestore:rules --project campus-asset-concierge --dry-run --non-interactive
npx -y firebase-tools@latest deploy --only firestore:rules --project campus-asset-concierge --non-interactive
```

## What still needs work

`LocalStateStore` currently requires a loopback emulator and anonymous credentials. Connecting the backend needs explicit cloud configuration, Google credentials outside Git, and a deliberate seed of fictional data. Do not point local tests or reset commands at the hosted database.

Firebase Authentication, web app registration, Storage, and backend hosting are not set up. The Python backend does not need a Firebase browser SDK configuration. Cloud Run requires billing and is outside this free-plan setup. See [Firebase pricing plans](https://firebase.google.com/docs/projects/billing/firebase-pricing-plans).
