# Deployment plan (do-it-yourself runbook)

Goal: take the working prototype from "local only" to "live on the internet on real Firestore," ready for the demo. Gemini Enterprise is added **last**, as a bonus, when the trial licence arrives.

Order: merge the Firebase branch → verify real Firestore → seed once → host the app → add a daily recovery trigger → (later) Gemini Enterprise.

## Before you start

- Firebase project `campus-asset-concierge`, Firestore in Singapore, empty. (Done.)
- Your service-account key JSON is on your machine (in Downloads). Keep it secret; never commit it.
- `FIRESTORE_EMULATOR_HOST` must be **unset** in any shell that talks to real Firestore. If it is set, open a new shell or run `Remove-Item Env:FIRESTORE_EMULATOR_HOST`.

## Step 1 — Merge the Firebase code branch

`chore/firebase-spark-setup` holds the code that lets the backend use real Firestore (and config, rules, docs).

1. Open a PR into `main` and get a teammate to review:
   ```powershell
   gh pr create --base main --head chore/firebase-spark-setup --fill
   ```
2. Merge it on GitHub.

## Step 2 — Verify the real connection (read-only, writes nothing)

In a fresh PowerShell:

```powershell
$env:GOOGLE_CLOUD_PROJECT = 'campus-asset-concierge'
$env:GOOGLE_APPLICATION_CREDENTIALS = 'C:\Users\Ivan Lee\Downloads\campus-asset-concierge-firebase-adminsdk-fbsvc-ab25e0842c.json'
uv run --locked python -c "from campus_asset_concierge.storage.local_state import LocalStateStore; print('exists:', LocalStateStore().document.get().exists)"
```

Expect `exists: False` (connected; database still empty). A credentials error means the key path is wrong.

## Step 3 — Seed the real database once

Keep the two env vars from Step 2 set (emulator var still unset):

```powershell
uv run --locked python -m campus_asset_concierge.seed_demo spare_available
```

This writes one `demo/current` document of fictional data. It refuses if data already exists; add `--replace` to overwrite on purpose. Re-run Step 2's check — it should now print `exists: True`.

⚠️ Only seed the real database deliberately. Never point tests or the `reset` route at it.

## Step 4 — Host the app on Render (free)

Hosts the FastAPI app: the locker page + booking API + recovery.

1. On [render.com](https://render.com) → **New → Web Service** → connect this repo (branch `main`).
2. Runtime **Docker**, or Python with start command:
   ```
   uv run --locked uvicorn campus_asset_concierge.api.app:create_app --factory --host 0.0.0.0 --port $PORT
   ```
3. **Environment variables:**
   - `GOOGLE_CLOUD_PROJECT = campus-asset-concierge`
   - `LOCAL_BORROWER_A_PASSWORD`, `LOCAL_BORROWER_B_PASSWORD`, `LOCAL_STAFF_PASSWORD`, `LOCAL_OPERATOR_PASSWORD` — pick strong values.
   - Do **not** set `FIRESTORE_EMULATOR_HOST`.
4. **Secret File** for the key: add a Secret File holding the JSON, e.g. at `/etc/secrets/firebase.json`, then set:
   - `GOOGLE_APPLICATION_CREDENTIALS = /etc/secrets/firebase.json`
5. Deploy. Note the public URL (e.g. `https://campus-asset-concierge.onrender.com`).
6. Open `<url>/locker`, sign in — your live app on real Firestore.

⚠️ Free Render sleeps after ~15 min idle (≈1 min cold start). See Step 6 to keep it awake for judging.

## Step 5 — Student booking front door (decide)

- **Primary:** Gemini Enterprise chat (Step 7, when the licence arrives).
- **Backup:** a simple coded chat page using a free Gemini API key — build only if the licence is late. Ask me to add it.

## Step 6 — Daily overdue recovery + keep-awake

The "maximizing" automation = run recovery once a day.

1. Expose a staff endpoint that runs recovery (e.g. `POST /run-recovery`). This does not exist yet — **ask me to add it.**
2. Use a free scheduler ([cron-job.org](https://cron-job.org)) to call it daily. A ping every ~10 min during judging (Nov 11–14) also keeps the free host awake.

## Step 7 — Gemini Enterprise (when the licence arrives)

Follow [GEMINI_BUILD_SHEET.md](GEMINI_BUILD_SHEET.md):

1. Deploy/point the MCP connector (`mcp_server`) at the same backend and Firestore.
2. Build the chat agent + recovery workflow; register the **MCP** (3P) and **Gmail** (1P) connectors.
3. Rehearse with [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

## Guardrails

- Never commit the key (it is gitignored; keep it in Render's secrets).
- Tests and CI stay on the **emulator** — do not set the real env vars there.
- Fictional data only.
