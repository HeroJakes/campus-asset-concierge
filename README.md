# Campus Asset Concierge

Campus Asset Concierge helps borrowers reserve shared campus equipment and helps staff recover future bookings when equipment is overdue. The hackathon prototype uses synthetic data and a virtual locker. This repository starts with the project scaffold. Product implementation follows a separate build plan.

## Local setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run these commands from the repository root. uv can install the pinned Python version if needed.

```sh
uv sync --locked
uv run python -c "import campus_asset_concierge; print('Package import OK')"
```

The scaffold can be set up without a Google Cloud or Gemini Enterprise account. The Firestore emulator is available for local development once persistence work starts. With the [Firebase CLI and emulator prerequisites](https://firebase.google.com/docs/emulator-suite/install_and_configure) installed, start it with a demo project ID.

```sh
firebase emulators:start --only firestore --project demo-campus-asset-concierge
```

In the terminal that runs the future application, set `FIRESTORE_EMULATOR_HOST` to `127.0.0.1:8080` and use `demo-campus-asset-concierge` as the Firestore project ID.

## Project layout

```text
src/campus_asset_concierge/
  agent/      ADK agent and typed tool adapters
  api/        FastAPI entry points and request handling
  domain/     Lending rules and workflows
  storage/    Firestore persistence
  templates/  Server-rendered locker views
  static/     Locker styles and browser scripts
tests/        pytest test suite location
```

## Hosting later

Local development is the current target. The intended hosted setup is Cloud Run for FastAPI, Cloud Firestore for shared persistence, and Agent Runtime for the ADK agent registered in Gemini Enterprise. The hosted integration depends on the event account's permissions and quota.
