# MCP connector — Cloud Run readiness plan

**Status:** Proposed. Awaiting user review before implementation.

## Goal and stop line

Prepare the existing MCP connector for a private Cloud Run service backed by a dedicated Firestore demo database. Reuse all five tools, lending rules, transactions, and fictional scenarios, including Stage 2.2 requirements.

This work does not need a Gemini Enterprise licence to build and test locally. Real cloud validation needs an approved Google Cloud project, billing, permissions, and resources. Gemini registration and borrower identity mapping still depend on event access.

The first milestone is a tested container, service configuration, seed command, and deployment instructions. Stop there for review. Do not create resources, grant access, write hosted data, or deploy until the user approves the target project and cloud work.

## Current gaps

- `mcp_server.py` starts with stdio transport. Cloud Run requires HTTP.
- `LocalStateStore` requires a loopback emulator address and uses anonymous credentials with a fixed emulator project ID.
- No Dockerfile, Cloud Run manifest, or explicit hosted seed command exists.
- MCP tools trust the supplied `borrower_id`; the recovery tool has no staff-role check. Cloud service authentication alone does not establish a borrower identity.
- The demo clock is stored test time. Hosting it does not make overdue recovery follow wall-clock time.

## Proposed scope

### 1. HTTP entry point

Keep stdio as the default for existing local callers. Add an explicit `MCP_TRANSPORT=streamable-http` mode for the container. Reject unsupported transport values at startup.

Use the installed FastMCP SDK, listening on `0.0.0.0` and the Cloud Run `PORT` value, defaulting to 8080 for local HTTP runs. Serve MCP at `/mcp`. Use stateless HTTP so requests do not depend on one instance keeping an MCP session in memory. Keep application state in Firestore.

Validate the port and configure the SDK's allowed HTTP host/origin settings for the intended service URL and local tests. Retain host checks rather than disabling transport protections to make deployment work. Document any service URL value that must be filled in before deployment.

Expose only MCP in this container. Do not mount the local FastAPI app, operator reset/clock routes, or locker page. The hosted locker remains a separate integration task. Keep the existing tool contracts and error behavior.

### 2. Explicit Firestore modes

Extend the existing store rather than introducing a second persistence implementation. Preserve its class name and transaction interface to avoid changing every domain caller.

| Setting | Emulator mode | Hosted mode |
| --- | --- | --- |
| `FIRESTORE_MODE` | Default `emulator` | Explicit `cloud` |
| Project | Existing `demo-campus-asset-concierge` | Required `GOOGLE_CLOUD_PROJECT`; no fallback |
| Database | Existing default database | Dedicated project's `(default)` database |
| Credentials | Anonymous, loopback emulator only | Application Default Credentials from the runtime service account |
| `FIRESTORE_EMULATOR_HOST` | Required and validated | Must be absent; reject conflicting configuration |
| Demo document | Existing `demo/current` or test fixture ID | Required `DEMO_DOCUMENT_ID` within the `demo` collection |

Validate the hosted project and document settings before constructing the client. Reject the emulator-only `demo-` project prefix in cloud mode, empty IDs, and document IDs containing path separators. Missing credentials must fail; never silently fall back to anonymous access or the emulator.

Keep explicit `document_id` arguments for isolated local tests. Ensure every caller uses the same mode selection: API, ADK, MCP, and seeding. Extend the test fixture to force emulator mode so normal tests cannot write to hosted Firestore because of ambient shell settings.

Reuse Firestore transactions for all changes. The Python lock covers one process only; hosted correctness must come from transactions. Keep the single-document state model for this small demo. Do not add a migration, repository abstraction, or production-scale schema.

### 3. Explicit fictional-data seeding

Add `python -m campus_asset_concierge.seed_demo` with a required scenario argument: `spare_available` or `spare_unavailable`. Use the same store configuration and `starting_state()` fixtures as the app.

Create an absent demo document atomically. If it already exists, refuse to overwrite it unless `--replace` is supplied. Use the existing transaction path for an explicit replacement. Display the project, database, document, and selected scenario before the write; do not print credentials or locker codes.

Never seed or reset on container startup. A restart or new revision must preserve reservations, audit events, and the demo clock. The seed command is an operator operation, not an MCP tool or public HTTP route.

Retain the fixed test clock and label it clearly. To prepare an overdue hosted demo without exposing a clock endpoint, permit `--advance-minutes` with the existing local operator range, 1–1440, defaulting to no advance. Build that clock offset into the seeded state; do not process recovery during seeding. The first `run_overdue_recovery` call then demonstrates detection. Replacing a seeded document destroys that document's previous demo activity, so require the explicit replacement flag every time.

### 4. Container packaging

Add a Python 3.12 Dockerfile and `.dockerignore`. Install runtime dependencies from `uv.lock` with locked dependency resolution; exclude development dependencies. Use a separate build stage if needed to keep uv/build tools out of the runtime image.

Run the existing module as a non-root user. Include package templates/static files needed for package completeness, but do not serve the locker. Exclude `.git`, `.venv`, `.env` files, credential files, tests, emulator data, and debug logs from the build context. No service-account key or local credentials belong in the image.

The container defaults to HTTP transport, while running the Python module outside the image still defaults to stdio. Do not bake a real project ID, service URL, or service-account name into the image. The image must start without writing demo data.

### 5. Cloud Run service configuration and access

Add `deploy/cloud-run.yaml` as the canonical service configuration template. Use placeholders for the image, project, service account, demo document, and allowed service host. Proposed initial settings: one CPU, 512 MiB memory, zero minimum instances, one maximum instance, concurrency one, port 8080, and a 300-second request timeout. These are demo defaults, not a reliability guarantee or hard spending cap.

Keep IAM invocation checks enabled. Do not grant `allUsers` or `allAuthenticatedUsers` access. Restrict invocation to explicitly approved test operators. Use a dedicated runtime service account with Firestore data access, not project Owner/Editor. Keep deployment permissions separate from runtime permissions. A dedicated demo project limits the scope of the data-access role.

This private service is an operator-tested backend. An approved invoker can still supply either fictional borrower ID and run recovery. That is acceptable only for this controlled fictional demo. Do not grant general borrower or Gemini access until trusted identity and role binding is designed and tested. Do not assume Cloud Run IAM tokens match Gemini Enterprise's connector authentication requirements.

Prepare instructions to fill the manifest and apply it with one deployment command after provisioning and image publishing. A YAML service manifest uses `gcloud run services replace`; explain that this serves the intended one-command deployment outcome. Keep configuration in the manifest instead of duplicating it in a long deploy command.

Do not claim the manifest alone establishes IAM policy: document and verify the service's invoker policy separately, including existing bindings when updating a service. Prefer a new dedicated service for the initial cloud validation.

## Files and callers affected

| Area | Planned work |
| --- | --- |
| `mcp_server.py` | Transport, bind address, port, stateless HTTP, allowed hosts |
| `storage/local_state.py` | Explicit emulator/cloud client selection and validated target |
| `seed_demo.py` (new) | Explicit create/replace seeding using existing fictional fixtures |
| `Dockerfile`, `.dockerignore` (new) | Locked runtime container and clean build context |
| `deploy/cloud-run.yaml` (new) | Private-service template and runtime settings |
| Existing store callers | Keep constructors compatible; verify API, tools, and domain services share configuration |
| `tests/conftest.py` | Force isolated emulator mode and test document IDs |
| Tests | Extend MCP tests; add focused configuration and seeding tests |
| README and connector/architecture docs | Local commands, hosted prerequisites, security boundary, planned versus verified status |
| Build stages | Track readiness as preparation under Stage 1.5; do not mark Gemini access complete |

No new runtime dependency is expected. Do not add an OAuth server, scheduler, real notifications, hosted locker, real-time clock, or CI auto-deployment in this change.

## Implementation and validation order

1. Add configuration tests and explicit Firestore modes. Prove defaults remain local and conflicting/missing hosted settings fail. Test cloud client construction with a stub so normal CI makes no cloud calls.
2. Add create-only seeding and explicit replacement tests against the emulator. Cover both scenarios, invalid offsets, repeated create attempts, and preserving existing state when replacement is absent.
3. Add HTTP startup and MCP client tests. Initialize, list exactly five tools, find and confirm an offer, read status without codes, and process both recovery outcomes. Preserve stdio compatibility and strict Stage 2.2 inputs.
4. Build the container locally. Use a Docker-networked emulator with the application still seeing an allowed loopback emulator address, or another documented setup that preserves the store's loopback-only check. Do not broaden emulator host validation just for Docker networking.
5. Test through the container's HTTP endpoint with the MCP client. Use the configured hostname; check invalid hosts and malformed input. Verify configuration errors fail startup and repeated recovery/confirmation stay safe.
6. Restart the container and confirm persisted data survives. Start two app processes against the emulator with competing last-unit confirmations to exercise transactions beyond the per-process lock.
7. Run the full pytest suite, Python compilation, manifest/configuration checks, and documentation link checks. Review the Docker build context for secrets and local files. Do not mark container validation passed if Docker is unavailable or tests were skipped.
8. Update docs with exact tested commands and evidence. Review the change before approving any cloud operations.

No type checker is currently configured. Continue the existing checks rather than adding unrelated tooling.

## Later cloud validation — separate approval

Before cloud work, agree on the project ID, region, billing owner, Firestore location, image repository, runtime service account, and permitted invokers. The existing emulator project ID is not a deployable real project. Check that the chosen account can create/use the required resources and that billing is available.

After approval: enable required APIs, create or verify the dedicated database and image repository, assign scoped roles, build/publish the tested image, seed one fictional document, and deploy the filled manifest. Inspect IAM before invoking. Test that an anonymous request is denied and an approved operator can initialize MCP and use the tools. Verify hosted persistence across a new revision and the Firestore transaction behavior under competing confirmations.

Test missing data and missing Firestore permissions as explicit failures. Reseeding is never a recovery action for a permission error. Record cleanup steps and how to remove service access and demo resources after the event.

## Acceptance and remaining limits

Local readiness is complete when the container and protocol tests pass, existing tests remain green, seeding is explicit and repeat-safe, defaults cannot write to cloud by accident, and deployment instructions list all remaining target values and prerequisites.

Hosted readiness is verified only after the separately approved real Firestore and private Cloud Run checks pass. Gemini integration remains unverified until the licence arrives and its authentication, identity mapping, and tool round-trip work. Deploying MCP alone does not provide the hosted locker or an end-to-end demo UI.

## Reference documentation

Consulted on 2026-11-06; validate exact commands against the chosen project during implementation.

- [Host MCP servers on Cloud Run](https://docs.cloud.google.com/run/docs/host-mcp-servers) — HTTP transport and client authentication.
- [Cloud Run container contract](https://docs.cloud.google.com/run/docs/container-contract) — bind address and port requirements.
- [Cloud Run service identity](https://docs.cloud.google.com/run/docs/securing/service-identity) — runtime credentials and permissions.
- [Firestore server-client security](https://docs.cloud.google.com/firestore/native/docs/security/iam) — server access uses IAM.
