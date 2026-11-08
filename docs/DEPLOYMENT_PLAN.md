# Stable hackathon deployment

Stage 1.5. Vercel is the chosen host for the locker, REST API, and MCP endpoint.
Judging runs November 11–14, 2026. This plan replaces the older Render runbook.

## Status

The reviewed entrypoint and recovery trigger were merged in PR #21. The stable
demo is deployed from `main` commit `7baf36a96860eb95c902224c6346f526afa7e2b6`.
The create-only seed and live HTTPS checks passed on November 7, 2026. The project
owner confirmed the daily cron-job.org recovery job is working on November 8.
The obsolete Vercel test project was deleted on November 8. No keep-awake job is used.

| Target | Setting |
| --- | --- |
| Vercel project | `campus-asset-concierge-demo`, in Ivan Lee's projects, Hobby |
| Runtime | Python 3.12, FastAPI, Singapore (`sin1`), 60-second request cap |
| Firebase | `campus-asset-concierge`, `(default)`, Singapore (`asia-southeast1`), Spark |
| Live document | `demo/hackathon-20261111` only |
| Locker | `/locker`, HTTP Basic |
| MCP | `/mcp`, Streamable HTTP, no authentication for this fictional demo |
| Health | `/health`, public, no database read or write |
| Live URL | https://campus-asset-concierge-demo.vercel.app |

`vercel_demo.py` requires the exact project and document. Startup never seeds or
resets data. MCP mounting and lifespan setup are shared through `vercel_app.py`.

## Live verification — November 7, 2026

Deployment: `dpl_J2NACJqHk9GuxooMzo4VjF5H3Bg3`, Production, ready. This is a separate
project from the experimental preview. Vercel's account-login barrier is disabled.
All nine configured environment variables are sensitive and Production-only.
No emulator or preview-gate variables are configured. No secrets were committed.

| Check | HTTPS result |
| --- | --- |
| Public `/health` | 200, `{"status":"ok"}`, 0.443 seconds on the first measured request |
| Locker without credentials | 401 with a Basic challenge |
| Staff and borrower locker pages | Both 200; first Firestore-backed locker read 0.820 seconds |
| Clock read/advance and dev-login | 404, including with operator credentials |
| MCP initialization and discovery | 200 without auth; all five tools returned |
| MCP booking | Confirmed a Raspberry Pi kit reservation; direct Firebase MCP read verified persistence |
| Recovery trigger | 401 without auth; 403 as borrower; repeat staff calls returned identical results |
| Operator reset | 401 without auth; 403 as staff; valid operator request returned 204 in 0.144 seconds |
| Showcase restoration | Approved a substitute, then reset; Firebase confirmed the original booking and pending proposal restored |
| Cross-origin reset / cross-site browser request | Both 403 |
| Cross-origin MCP / wrong MCP hostname | 403 / 421 |
| Slowest measured request | 0.820 seconds, below the 60-second cap |

The smoke booking was `reservation-bfa601fe977f4d2b96fba84a531a4ee7`. After verifying
its persistence, operator reset removed it and restored the clean showcase. The
final Firebase MCP read found only `next-projector`, the overdue active loan, and
the substitute proposal in `pending_staff_approval`, at 61 elapsed minutes.

Hosted `demo/current` was read before seeding and after all live mutation checks:

| Baseline | Before | After |
| --- | --- | --- |
| Update timestamp | `2026-11-06T09:19:18.605177Z` | `2026-11-06T09:19:18.605177Z` |
| Content SHA-256 | `9df5b70dffc20cc5d314d63e90a38740e9be1db059846cb490d2fa73388a37c1` | `9df5b70dffc20cc5d314d63e90a38740e9be1db059846cb490d2fa73388a37c1` |

The hash covers Firestore's typed `fields`, encoded as UTF-8 JSON with sorted keys
and compact separators. Full snapshots and smoke measurements are kept in private
verification files outside the repo. Account passwords are also stored outside the repo;
the service-account JSON was passed in memory to Vercel's sensitive variable.
The `vercel-test-*` document was not written or reset.

These checks used the public HTTPS address, with no Vercel login or preview token.
They do not prove the later Gemini Enterprise handshake. Cold starts were checked
separately: a freshly deployed instance served its first Firestore request in under
a second; idle time alone cannot prove instance eviction. The unchanged reviewed code passed all
183 Python tests on the emulator and all five browser tests before release.

## Authentication and browser requests

- REST and locker accounts use the existing Basic roles: `equipment-staff`,
  `borrower-a`, `borrower-b`, and `local-operator`. Share credentials privately.
- `/local-test/reset` requires the operator password. It checks the document again
  before replacing state. It cannot reset `demo/current` or an arbitrary document.
- Hosted clock routes and dev-login routes are removed. `DEV_LOGIN=1` stops startup.
- Unsafe browser requests must have the correct Origin when one is supplied.
  Cross-site Fetch Metadata is rejected too. Command-line clients and the scheduler
  may omit Origin, but protected REST routes still require Basic credentials.
- Hosted Basic authentication adds no session cookie. The existing local dev cookie
  remains SameSite=Strict and is unavailable in the hosted app.
- Responses are not cached. MCP accepts only the configured host and browser origin.
  There is no blanket `x-preview-token` gate.

Unauthenticated MCP is an explicit demo exception. Anyone with the URL can use all
five tools, select either fictional borrower, and run recovery. MCP cannot reset or
advance the clock. Add OAuth and caller roles later against the real Gemini
Enterprise connector. In Gemini, choose **No authentication**; leave OAuth fields
empty. Real connector verification waits for the licence.

## Vercel environment

Set these on the `campus-asset-concierge-demo` project's Production environment.
Verify the team and project before changing settings. Do not copy the local `.env`,
where dev login may be enabled.

| Variable | Value |
| --- | --- |
| `GOOGLE_CLOUD_PROJECT` | `campus-asset-concierge` |
| `FIRESTORE_DOCUMENT_ID` | `hackathon-20261111` |
| `GOOGLE_CREDENTIALS_JSON` | Service-account JSON, **sensitive** |
| `DEV_LOGIN` | `0` |
| `LOCAL_STAFF_PASSWORD` | Unique generated password, at least 32 characters, **sensitive** |
| `LOCAL_BORROWER_A_PASSWORD` | Unique generated password, at least 32 characters, **sensitive** |
| `LOCAL_BORROWER_B_PASSWORD` | Unique generated password, at least 32 characters, **sensitive** |
| `LOCAL_OPERATOR_PASSWORD` | Unique generated password, at least 32 characters, **sensitive** |
| `PUBLIC_BASE_URL` | The project's stable HTTPS origin, with no path |

Do not set `FIRESTORE_EMULATOR_HOST`, `GOOGLE_APPLICATION_CREDENTIALS`,
`VERCEL_TEST_DOCUMENT_ID`, `PREVIEW_ACCESS_TOKEN`, `MCP_GOOGLE_CLIENT_ID`, or
`MCP_ALLOWED_EMAILS`. The app reads the JSON secret directly, without a key file.
The stable production URL must be reachable without a Vercel account sign-in;
application Basic authentication still protects the REST and locker routes.

## Release order after review

1. Get teammate review and merge PR #21 into `main`. Deploy only the reviewed commit.
2. Record the full content and update timestamp of hosted `demo/current`, using a
   read-only Firebase MCP call. Keep verification artifacts private.
3. Configure the dedicated Vercel project and sensitive variables above.
4. Seed only the fresh document. With the approved environment securely loaded in a
   dedicated operator process, run:

   ```powershell
   uv run --locked python -c "from campus_asset_concierge.vercel_demo import seed_demo; seed_demo()"
   ```

   `seed_demo()` uses Firestore's create-only operation. If the document exists,
   stop and inspect it; never add a replace flag. It seeds `spare_available` at
   61 elapsed minutes, then runs recovery so an overdue loan and pending substitute
   proposal are ready. If that recovery call fails after creation, use the protected
   recovery endpoint to finish it; do not overwrite the document.
5. Deploy `main.py`, which exports `create_demo_app()`. Keep the existing 60-second
   cap and Singapore region. `.vercelignore` excludes credentials and local files.
6. Verify over HTTPS before adding any schedule:
   - `/health` returns 200 without credentials; `/locker` returns 401 without Basic.
   - Staff and borrower locker pages render with their own credentials.
   - MCP initialization and `tools/list` work without a preview token or OAuth.
   - A booking write persists, verified by a direct Firebase MCP read of the demo doc.
   - Recovery is staff-only and idempotent. A first Firestore request is comfortably
     under 60 seconds; idle time alone is not proof that Vercel evicted an instance.
   - Cross-origin mutations are rejected. Clock and dev-login paths return 404.
   - Approve a substitute, then use the operator reset and verify the pending
     proposal is restored. Restore the showcase after other smoke-test writes too.
   - `demo/current` has exactly the recorded content and update timestamp.
7. Record the live URL, deployed commit, timings, data comparison, and scheduler
   outcome here. Check the staged diff for secrets before committing.

## Operator reset between judges

Send `POST /local-test/reset` with Basic authentication as `local-operator` and JSON
`{"scenario":"spare_available"}`. The existing API docs at `/docs` can send this
request after the operator enters their credentials. Keep that password private.
Use `spare_unavailable` only when deliberately showing the no-spare scenario.

Reset always restores the chosen fictional fixture at 11:01 Malaysia time on
November 7, 2026, then runs recovery to prepare its proposal or escalation. The
clock stays fixed. Dates in bookings must follow that demo clock. The daily job
does not advance time, send Gmail messages, approve proposals, or reset the data.
State is shared and changes persist between judges until the operator resets it.

## Daily scheduler

The project owner confirmed this cron-job.org job is configured and working.
Execution history has not been independently inspected by the coding agent.

| Field | Value |
| --- | --- |
| URL | `https://campus-asset-concierge-demo.vercel.app/recovery/run` |
| Method | `POST` |
| Time zone | `Asia/Kuala_Lumpur` |
| Schedule | Daily at 09:00 (`0 9 * * *`; 01:00 UTC) |
| HTTP Basic username | `equipment-staff` |
| HTTP Basic password | Same sensitive staff password as Vercel, entered privately |
| Expected result | HTTP 200; repeat calls do not duplicate recovery records |

Run one manual scheduler test and check its execution history before relying on it.
No keep-awake job is planned or needed. `/health` is available for manual checks.
Vercel Cron is not configured; it sends GET, while this endpoint requires POST.
Keep the job enabled through judging and check its execution history for failures.

## Data and test guardrails

- Fictional data only. Never seed, reset, or write hosted `demo/current`.
- Baseline read on November 7: `demo/current` update timestamp is
  `2026-11-06T09:19:18.605177Z`; scenario `spare_available`, elapsed minutes `0`.
- Tests and CI use only the local emulator or mocked clients. Hosted entrypoint
  unit tests mock credentials and store construction; they never create a cloud client.
- The reset integration test uses the emulator's exact demo document, skips it if
  already present, and removes only the document it created.
- Never commit keys, passwords, tokens, preview-access URLs, or scheduler credentials.
