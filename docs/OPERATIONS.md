# Live operations

Use this file for the hosted demo. Use [Development](DEVELOPMENT.md#local-setup)
for emulator-only work and [Build stages](BUILD_STAGES.md) for progress.

## Live target

| Setting | Value |
| --- | --- |
| Project | `campus-asset-concierge-demo`, Ivan Lee's projects, Vercel Hobby |
| Locker | https://campus-asset-concierge-demo.vercel.app/locker |
| REST schemas / operator reset | https://campus-asset-concierge-demo.vercel.app/docs |
| MCP | https://campus-asset-concierge-demo.vercel.app/mcp |
| Health | https://campus-asset-concierge-demo.vercel.app/health |
| Runtime | Python 3.12, FastAPI, Singapore `sin1`, 60-second cap |
| Firebase | `campus-asset-concierge`, Spark, no billing account linked at setup |
| Database | `(default)`, Standard / Native, Singapore `asia-southeast1` |
| Live document | `demo/hackathon-20261111` |
| Deployed source | Reviewed main commit `7baf36a96860eb95c902224c6346f526afa7e2b6` |
| Deployment | `dpl_J2NACJqHk9GuxooMzo4VjF5H3Bg3` |

The obsolete `campus-asset-concierge-vercel-test` project was deleted November 8.
The local `.vercel/project.json` points to the live demo. Do not recreate the test
project as a routine setup step.

## Data boundaries

- Hosted `demo/hackathon-20261111`: all live locker/MCP reads and writes; protected operator reset may replace it.
- Hosted `demo/current`: preserved legacy fictional seed; never point tests, reset, or a new seed at it.
- Hosted `vercel-test-*`: historical experiment data, left untouched.
- Emulator project `demo-campus-asset-concierge`: local tests and resettable rehearsals only.

There is no automatic sync between emulator and cloud. The standard store's
default document is `current`, so never use an unconfigured local startup as if it
were the hosted demo. A legacy private local `.env` may use
`GOOGLE_CLOUD_PROJECT` plus an outside-repo `GOOGLE_APPLICATION_CREDENTIALS` path
to access cloud `demo/current`; it is not the test or hosted-demo profile.
Keep its operator password empty. Prefer the live URL or emulator for routine work.

Firestore rules deny direct client access. Server credentials use IAM instead of
those rules. No browser Firebase SDK, Firebase Authentication, or Storage setup is
needed by this Python backend. Keep key files outside the repository.

## Authentication

The recorded live release below uses HTTP Basic. The new `/login` page on
`feat/borrower-staff-login` is awaiting review and deployment. After release,
browser users select borrower/staff and sign in with these same account credentials;
REST Basic remains available for cron and operator clients.

Existing accounts:

| Account | Role |
| --- | --- |
| `borrower-a`, `borrower-b` | Own bookings, pickup, and return |
| `equipment-staff` | Load, condition checks, recovery, approval, and recheck |
| `local-operator` | Reset only on the hosted demo |

MCP deliberately uses **No authentication** for fictional data. Anyone with the
URL can call its five tools and supply either fictional borrower ID. Host/origin
checks are not caller identity checks. It exposes neither reset nor clock/device
actions. OAuth and trusted borrower roles are deferred until tested with the real
connector; real data must not use this demo exception.

Vercel account-login protection is disabled so judges and Gemini can reach the
app. Public `/health` reads no database data. HTTP Basic introduces no session
cookie in the recorded live version. The new login uses an eight-hour HttpOnly,
SameSite=Strict cookie, Secure over HTTPS. It reuses the configured account secret
for purpose-specific signatures, with no new environment variable. Rotation revokes
that account's cookies. Browser mutations reject a supplied foreign Origin or cross-site Fetch
Metadata. Non-browser requests without Origin still need Basic for protected REST.
Responses are not cached. MCP accepts only the configured stable host/origin.

The operator is excluded from browser login. Use a separate browser session for
operator `/docs` actions; a signed-in borrower/staff cookie takes precedence over
Basic credentials. Login-page UI has no test-mode notice; the data/clock constraints
remain documented here and the hosted dev-login guard is unchanged.

## Environment and secrets

All nine variables are sensitive and Production-only on the dedicated project:

| Variable | Value |
| --- | --- |
| `GOOGLE_CLOUD_PROJECT` | `campus-asset-concierge` |
| `FIRESTORE_DOCUMENT_ID` | `hackathon-20261111` |
| `GOOGLE_CREDENTIALS_JSON` | Service-account JSON |
| `DEV_LOGIN` | `0` |
| `PUBLIC_BASE_URL` | `https://campus-asset-concierge-demo.vercel.app` |
| `LOCAL_STAFF_PASSWORD` | Unique generated password, at least 32 characters |
| `LOCAL_BORROWER_A_PASSWORD` | Unique generated password, at least 32 characters |
| `LOCAL_BORROWER_B_PASSWORD` | Unique generated password, at least 32 characters |
| `LOCAL_OPERATOR_PASSWORD` | Unique generated password, at least 32 characters |

Do not set `FIRESTORE_EMULATOR_HOST`, `GOOGLE_APPLICATION_CREDENTIALS`,
`VERCEL_TEST_DOCUMENT_ID`, `PREVIEW_ACCESS_TOKEN`, or OAuth variables in Vercel.
The entrypoint rejects the wrong project/document, emulator configuration,
`DEV_LOGIN=1`, short passwords, and an invalid HTTPS base URL.

Private account passwords are outside the repo in
`~/.codex/private/campus-asset-concierge-demo-access.json`. Release evidence and
one-off helpers are in `~/.codex/private/campus-asset-concierge-demo-evidence/`.
Neither belongs in Git, chat, logs, or deployment uploads. The service-account JSON
was passed in memory to the sensitive variable; no key file was added to the repo.
`.vercelignore` uploads only source and build inputs.

## Seed and reset

The live seed is **already complete**. Startup never seeds or resets state.
For a separately approved first setup only, with the hosted environment securely
loaded in a dedicated operator process:

```powershell
uv run --locked python -c "from campus_asset_concierge.vercel_demo import seed_demo; seed_demo()"
```

This pins the exact live document, calls Firestore create-only, then runs recovery.
If the document exists, stop. Do not add a replace flag or use the generic seed CLI
against hosted Firestore. If creation succeeded but recovery failed, finish with
the protected recovery trigger rather than overwrite the document.

Between demonstrations, authorize as `local-operator` in `/docs`, then POST
`/local-test/reset` with:

```json
{"scenario":"spare_available"}
```

Use `spare_unavailable` only to show the no-spare outcome. Reset checks the exact
document at the destructive boundary, replaces previous demo activity, sets
61 elapsed minutes, and runs recovery. It restores the chosen proposal/escalation.
Never expose the operator password as a public judge credential.

The clock remains **November 7, 2026, 11:01 MYT**. Clock read/advance and dev-login
routes return 404 on this deployment. Dates in bookings must follow that demo
clock. New future pickups will not become collectable by waiting in real time.

## Daily scheduler

The owner confirmed on November 8 that cron-job.org is configured and working.
The coding agent has not independently inspected its execution history.

| Field | Value |
| --- | --- |
| URL | `https://campus-asset-concierge-demo.vercel.app/recovery/run` |
| Method | `POST` |
| Time zone | `Asia/Kuala_Lumpur` |
| Schedule | Daily 09:00; `0 9 * * *` in that time zone, 01:00 UTC |
| HTTP Basic | `equipment-staff` and the same private staff password as Vercel |
| Expected response | HTTP 200; repeat runs do not duplicate recovery records |

Keep the job enabled through November 11–14 judging and check failure history.
There is no keep-awake job and no Vercel Cron configuration. The daily POST does
not advance the fixed clock, reset activity, approve substitutes, or send Gmail.
The later Gemini/Gmail workflow needs its own integration and delivery checks.

## Release evidence

Live HTTPS checks on November 7 used no Vercel account session or preview token:

| Check | Result |
| --- | --- |
| First measured health request | 200, `{"status":"ok"}`, 0.443 seconds |
| Locker without Basic / staff and borrower pages | 401 challenge / both 200 |
| First Firestore-backed locker read | 0.820 seconds |
| Clock read/advance and dev login | 404, including as operator |
| MCP initialization / tool discovery | 200, all five tools |
| Booking persistence | Raspberry Pi booking verified through Firebase MCP |
| Recovery | 401 anonymous, 403 borrower, identical repeated staff results |
| Reset | 401 anonymous, 403 staff, operator 204 in 0.144 seconds |
| Restored showcase | Approve, reset, and Firebase read confirmed pending proposal |
| Cross-origin reset / cross-site request | 403 / 403 |
| Cross-origin MCP / wrong MCP hostname | 403 / 421 |

The slowest measured request was 0.820 seconds, below the 60-second cap.
Preview checks separately exercised first Firestore requests on a fresh deployment.
Idle time alone does not prove instance eviction. These results do not verify
the pending Gemini Enterprise handshake.

The smoke booking `reservation-bfa601fe977f4d2b96fba84a531a4ee7` was read directly
from Firebase, then cleared by operator reset. The clean snapshot contained only
`next-projector`, the overdue original loan, and its pending substitute at minute 61.

Hosted `demo/current` matched before seeding and after all live mutation checks:

- Update timestamp, before and after: `2026-11-06T09:19:18.605177Z`.
- SHA-256, before and after: `9df5b70dffc20cc5d314d63e90a38740e9be1db059846cb490d2fa73388a37c1`.
- Hash input: typed Firestore `fields`, UTF-8 JSON, sorted keys, compact separators.

A read-only check after removing the test project on November 8 confirmed the same
update timestamp. The active demo's health, Basic challenge, and five MCP tools
also passed after deletion. No Firestore writes or resets were part of cleanup.

## Changes and troubleshooting

Before any approved release, verify team/project, reviewed commit, target document,
sensitive variables, and stable base URL. Deploy the reviewed source from main,
verify HTTPS and one isolated persisted write, restore the showcase, and compare
`demo/current` again before relying on the schedule. Record any new release here.

For failures: check `/health`, Vercel build/runtime logs, project credentials, and
the stable MCP URL. A 401 on protected REST means Basic is missing/incorrect;
a 421 on MCP can mean the hostname is wrong. Do not reseed to fix access errors.
Keep a recorded demo ready. A new host/database or broader feature work requires
approval and rehearsal.
