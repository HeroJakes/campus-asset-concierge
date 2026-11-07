# Stable hackathon deployment

Stage 1.5. Vercel is the chosen host for the locker, REST API, and MCP endpoint.
Judging runs November 11–14, 2026. This plan replaces the older Render runbook.

## Status

The entrypoint is implemented on `feat/run-recovery-endpoint` for teammate review.
No stable deployment, hosted seed, sensitive environment settings, or scheduler
has been created in this change. PR #20 is merged; PR #21 must be reviewed and
merged before release. The teammate must review the entrypoint changes too.

| Target | Setting |
| --- | --- |
| Planned Vercel project | `campus-asset-concierge-demo`, in Ivan Lee's projects, Hobby |
| Runtime | Python 3.12, FastAPI, Singapore (`sin1`), 60-second request cap |
| Firebase | `campus-asset-concierge`, `(default)`, Singapore (`asia-southeast1`), Spark |
| Live document after release | `demo/hackathon-20261111` only |
| Locker | `/locker`, HTTP Basic |
| MCP | `/mcp`, Streamable HTTP, no authentication for this fictional demo |
| Health | `/health`, public, no database read or write |
| Live URL | Pending review and deployment; do not use an experimental preview link |

`vercel_demo.py` requires the exact project and document. Startup never seeds or
resets data. `vercel_preview.py` keeps its experimental token and document guards;
the two wrappers share only MCP mounting and lifespan setup in `vercel_app.py`.

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

Set these on the dedicated project's Production environment. Use a separate project
from `campus-asset-concierge-vercel-test`. Verify the team and project before changing
settings. Do not copy the local `.env`, where dev login may be enabled.

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

## Daily scheduler, after HTTPS verification

Create exactly one cron-job.org job:

| Field | Value |
| --- | --- |
| URL | `<stable HTTPS origin>/recovery/run` |
| Method | `POST` |
| Time zone | `Asia/Kuala_Lumpur` |
| Schedule | Daily at 09:00 (`0 9 * * *`; 01:00 UTC) |
| HTTP Basic username | `equipment-staff` |
| HTTP Basic password | Same sensitive staff password as Vercel, entered privately |
| Expected result | HTTP 200; repeat calls do not duplicate recovery records |

Run one manual scheduler test and check its execution history before relying on it.
No keep-awake job is planned or needed. `/health` is available for manual checks.
Vercel Cron is not configured; it sends GET, while this endpoint requires POST.
Scheduler account access is needed to create and verify the external job.

## Data and test guardrails

- Fictional data only. Never seed, reset, or write hosted `demo/current`.
- Baseline read on November 7: `demo/current` update timestamp is
  `2026-11-06T09:19:18.605177Z`; scenario `spare_available`, elapsed minutes `0`.
- Tests and CI use only the local emulator or mocked clients. Hosted entrypoint
  unit tests mock credentials and store construction; they never create a cloud client.
- The reset integration test uses the emulator's exact demo document, skips it if
  already present, and removes only the document it created.
- Never commit keys, passwords, tokens, preview-access URLs, or scheduler credentials.
