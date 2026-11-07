# Run the local MCP container

This runs the HTTP connector and Firestore emulator locally. It does not use cloud credentials, billing, or Gemini. The connector trusts fictional borrower IDs and permits recovery calls without a staff role, so keep its published port on loopback. Host/origin checks prevent DNS rebinding; they do not authenticate a caller.

## Prerequisites

Use Docker with Linux containers, uv, and the Firebase Firestore emulator JAR. These PowerShell commands were tested with `cloud-firestore-emulator-v1.22.0.jar` in the Firebase CLI cache. If needed, download the emulator with `firebase setup:emulators:firestore`; confirm the downloaded filename before setting the path below. Do not put the JAR or credentials in this repository.

The commands create two named containers. Use unused names or remove your own previous demo containers first. They do not affect other Docker services.

## Build and start

```powershell
docker build -t campus-asset-concierge:mcp-local .
$emulatorJar = (Resolve-Path "$env:USERPROFILE/.cache/firebase/emulators/cloud-firestore-emulator-v1.22.0.jar").Path
docker run -d --name campus-mcp-emulator -p 127.0.0.1:18080:8080 -p 127.0.0.1:18081:8081 --mount "type=bind,source=$emulatorJar,target=/emulator.jar,readonly" eclipse-temurin:21-jre java -jar /emulator.jar --host 0.0.0.0 --port 8080 --project_id demo-campus-asset-concierge
docker logs campus-mcp-emulator
```

Wait for the emulator's API endpoint message, then start MCP:

```powershell
docker run -d --name campus-mcp --network container:campus-mcp-emulator -e PORT=8081 -e FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 campus-asset-concierge:mcp-local
docker logs campus-mcp
```

Wait for Uvicorn's startup-complete message. MCP is at `http://127.0.0.1:18081/mcp`. Its container shares the emulator container's network namespace, so Firestore is still on allowed loopback `127.0.0.1:8080`. MCP uses port 8081 to avoid a conflict. Both host port mappings belong to the emulator container; do not add `-p` to the MCP container.

Startup does not seed data. Only MCP is served; `/locker` and the local operator routes are absent.

## Seed and check

```powershell
docker exec campus-mcp python -m campus_asset_concierge.seed_demo spare_available --advance-minutes 61
uv run --locked python tests/mcp_http_smoke.py http://127.0.0.1:18081/mcp spare_available
```

The seed command prints its target and creates `demo/current` only if absent. An existing document causes exit code 1 without changing it. `--advance-minutes` accepts 1–1440; omission leaves the test clock at reset time. Seeding does not run recovery. The smoke check runs recovery, confirms a new HDMI booking, checks status/code privacy, and repeats calls to verify safe behavior. It changes this fictional demo state.

For the other outcome, explicitly replace the previous activity:

```powershell
docker exec campus-mcp python -m campus_asset_concierge.seed_demo spare_unavailable --replace --advance-minutes 61
uv run --locked python tests/mcp_http_smoke.py http://127.0.0.1:18081/mcp spare_unavailable
```

The second case creates a staff-owned escalation. `--replace` atomically overwrites the whole demo document, discarding prior bookings and audit activity. Use it only when intentionally resetting the demo. The smoke check creates a booking, so reseed explicitly before repeating it.

Restart only MCP to verify persistence:

```powershell
docker restart campus-mcp
```

The emulator holds the data outside the MCP container. Restarting or deleting the emulator discards its in-memory data. Under cross-process contention, emulator transactions can return conflicts to both callers; retry after contention clears. Conflicts cannot confirm two overlapping reservations for one unit.

## Run without Docker

With a local emulator running at port 8080:

```powershell
$env:FIRESTORE_EMULATOR_HOST = '127.0.0.1:8080'
uv run --locked python -m campus_asset_concierge.seed_demo spare_available
$env:MCP_TRANSPORT = 'streamable-http'
$env:PORT = '8081'
uv run --locked python -m campus_asset_concierge.mcp_server
```

This uses the existing `demo/current` document in that emulator. If it already exists, review its activity before intentionally adding `--replace` to the seed command.

For the original stdio entry point, omit `MCP_TRANSPORT` or set it to `stdio`. The image defaults to HTTP, while the Python module defaults to stdio. Unsupported transports fail startup. In HTTP mode, `PORT` must be an integer from 1 to 65535; its default is 8080.

`MCP_ALLOWED_HOSTS` and `MCP_ALLOWED_ORIGINS` accept comma-separated explicit hosts and HTTP origins. Defaults allow only localhost and 127.0.0.1, with any port. For a different approved host, set both explicitly, for example `MCP_ALLOWED_HOSTS=mcp.example:443` and `MCP_ALLOWED_ORIGINS=https://mcp.example`. Host values must match the actual HTTP Host header, including its port when present. An absent Origin header is permitted for non-browser MCP clients. Paths and global/domain wildcards are rejected; `:*` is allowed only for a port. Changing these settings does not add authentication or authorize public hosting.

## Cleanup

```powershell
docker rm -f campus-mcp
docker rm -f campus-mcp-emulator
```

These commands remove only the named demo containers and their in-memory demo data. Keep the image for another local rehearsal.

## Validation

Verified end to end on 2026-11-06:

- Docker build and shared-emulator networking.
- Safe seeding and overwrite refusal.
- Both recovery scenarios through HTTP.
- Booking, confirmation, status, and repeated (idempotent) actions.
- Persistence after an MCP container restart.
- Host/origin rejection and invalid-port startup failure.

Cloud persistence (Firestore Spark) and deployment (Vercel) are now live; see the [deployment plan](DEPLOYMENT_PLAN.md). Trusted caller identity for the MCP endpoint is still pending.
