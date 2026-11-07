# Vercel and Firestore preview experiment

Stage 1.5 experiment, 2026-11-07. This branch tests hosting compatibility. It does not complete Gemini Enterprise integration or approve a production release.

## Target and isolation

- Vercel project: `campus-asset-concierge-vercel-test` in Ivan Lee's projects (Hobby).
- Runtime: Python 3.12, FastAPI, one function in Singapore (`sin1`), 60-second maximum request duration.
- Firestore: existing `campus-asset-concierge` project and `(default)` database.
- Test document: `demo/vercel-test-20261107-cccda3a6`, separate from `demo/current`.
- No Git auto-deployment or production promotion is configured. Deployments use the local branch checkout through the CLI.

The first deployment of the empty test project was automatically labeled production despite the preview flag. It had no production credential configuration and was removed. Subsequent deployments are protected previews.

## Small changes

The tested experiment used `main.py` to export an app assembled in `vercel_preview.py`. The stable demo change switches `main.py` to `vercel_demo.py`; `create_preview_app()` retains its isolated document and token guards. Do not redeploy the experimental project with the new root entrypoint and its old environment. It reuses the API, MCP tools, lending services, and transactions. The store accepts an optional Google credential object; normal local startup still uses its existing credentials.

The wrapper requires a separate `vercel-test-` document ID and a random access token. It rejects emulator configuration and passwordless dev mode. It mounts MCP at `/mcp`, manages the MCP lifespan, and uses JSON responses so tool calls finish promptly. The regular locker/API routes and static assets remain available behind the preview token and their existing account permissions.

## Preview-only settings

Set these as Vercel preview environment variables, keeping secrets sensitive:

| Setting | Purpose |
| --- | --- |
| `GOOGLE_CLOUD_PROJECT` | `campus-asset-concierge` |
| `GOOGLE_CREDENTIALS_JSON` | Service-account JSON supplied as a secret, never committed |
| `VERCEL_TEST_DOCUMENT_ID` | The isolated test document ID, without `demo/` |
| `PREVIEW_ACCESS_TOKEN` | Random token of at least 32 characters |
| `LOCAL_BORROWER_A_PASSWORD`, `LOCAL_BORROWER_B_PASSWORD` | Test borrower passwords |
| `LOCAL_STAFF_PASSWORD`, `LOCAL_OPERATOR_PASSWORD` | Test staff and reset/clock passwords |
| `DEV_LOGIN` | `0` |

`VERCEL_URL` supplies the exact allowed MCP hostname. Do not set `FIRESTORE_EMULATOR_HOST`. Every HTTP request needs `x-preview-token`; API routes also retain HTTP Basic account checks. Operator reset is enabled only for the isolated experiment document.

Local `.env.vercel-test*` files contain test passwords, temporary preview access, and verification metadata. They are Git-ignored and excluded from the deployment upload. The Firebase key is sent through Vercel's sensitive environment settings, not source files. `.vercelignore` uploads only application source and build manifests.

## Checks

The live smoke script checks the isolated target before any write:

```powershell
uv run --locked --env-file .env.vercel-test python tests/vercel_preview_smoke.py <preview-url> --share-url-file .env.vercel-test-access
```

The share URL file is created using Vercel's temporary preview-access tool and must match the preview hostname. Do not publish that link or the access token. Vercel account protection stays enabled.

Verified live:

- Python build and protected HTTPS startup.
- Unauthorized requests rejected; dev login unavailable.
- Staff locker HTML and CSS available.
- Booking confirmation and repeat confirmation.
- Staff loading, borrower code unlock, pickup, return drop-off, and staff verification.
- Role checks prevent staff from using operator reset.
- Two competing confirmations for the only speaker-equipped unit: one succeeds, one conflicts.
- MCP initialization, exactly five tools, both overdue recovery outcomes, repeat-safe recovery and booking, and code-free chat status responses.
- A separate direct Firestore read confirms the MCP writes persisted.
- `demo/current` retains its original update timestamp.

## First-after-idle live checks (2026-11-07)

Tested the existing protected preview `campus-asset-concierge-vercel-test-26ghg6vh3.vercel.app`. Each idle-sensitive request used its own idle window, a new HTTP client, and no client retries. Staff `/recovery` was used for the Firestore read because `/pickups` requires a borrower role.

| Request | Idle before request | HTTP result | Client round-trip |
| --- | --- | --- | --- |
| Staff `GET /recovery` | 308.5 seconds | 200 | 0.203 seconds |
| Borrower booking confirmation | 314.4 seconds | 200 | 0.438 seconds |
| MCP `run_overdue_recovery` | 316.8 seconds | 200 | 0.285 seconds |
| MCP `tools/list` (warm comparison) | After recovery | 200, five tools | 0.085 seconds |
| Without `x-preview-token` | Access cookie present | 401 | 0.156 seconds |
| Fresh revision's first Firestore read | Unvisited for 5+ minutes after READY | 200 | 0.734 seconds |
| MCP offer write on the fresh revision | After its first read | 200 | 0.686 seconds |

The new booking and the fresh revision's new offer were verified directly through Firebase MCP in `demo/vercel-test-20261107-cccda3a6`, not through the application's read path. No seed or reset was used for these checks. The slowest measured request above was 0.734 seconds, below the configured 60-second cap. The HTTPS 401 response body was checked to confirm it came from the app's token gate, not Vercel sign-in protection.

Before testing, `demo/current` had update time `2026-11-06T09:19:18.605177Z`. Its canonical Firestore fields had SHA-256 `9DF5B70DFFC20CC5D314D63E90A38740E9BE1DB059846CB490D2FA73388A37C1`. Direct Firebase MCP checks compare both the full field content and update time.

Final Firebase MCP verification after all writes confirmed that both the update time and full content remained unchanged. Vercel reported no error or fatal logs for either tested preview during the test windows.

Five minutes idle does not prove Vercel recycled the process. Vercel returned no trace for the timed read, so these measurements alone establish first-after-idle success, not independently verified cold-instance startup.

To exercise initial connection setup separately, a forced, uncached build created preview `campus-asset-concierge-vercel-test-djigurwe1.vercel.app` (`dpl_ATKXPkp85QXYbK8FZJGs74V7BUdo`). It reached READY at 07:22:49 UTC. Its first app request was the staff Firestore read after 07:27:50 UTC, sent directly with authenticated CLI access, without opening a share URL or warming the app first. This verifies the new revision's first Firestore use; Vercel did not expose an explicit process cold-start flag.

## Limits and next steps

This confirms Vercel-to-Firestore compatibility for the tested workflows. It does not verify Gemini Enterprise, real email, unattended scheduling, load capacity, or long-running MCP streams. The API's demo clock remains manually controlled.

The preview token is an operator test gate, not Gemini OAuth or borrower identity mapping. Do not turn off protection and call this production-ready. Passwordless local login remains local-only. A real Gemini connection needs its supported authentication and identity requirements tested after access arrives.

Review the PR before merging. Merging the code alone does not publish a production deployment. To remove the experiment later, delete the exact test deployment/project and only the `demo/vercel-test-20261107-cccda3a6` document; preserve `demo/current` and the Firebase project. Remove preview credentials from Vercel when the test project is no longer needed.
