"""Hosted hackathon demo. All writes are pinned to one fictional document."""

import json
import os
from urllib.parse import urlsplit

from fastapi.responses import JSONResponse
from google.oauth2.service_account import Credentials

from campus_asset_concierge.api.app import create_app
from campus_asset_concierge.api.auth import same_origin
from campus_asset_concierge.domain.scenarios import TestScenario
from campus_asset_concierge.recovery import Recovery
from campus_asset_concierge.storage.local_state import LocalStateStore
from campus_asset_concierge.vercel_app import mount_mcp

DEMO_DOCUMENT_ID = "hackathon-20261111"
DEMO_ADVANCE_MINUTES = 61


class DemoStateStore(LocalStateStore):
    def __init__(self, *, credentials):
        super().__init__(DEMO_DOCUMENT_ID, credentials=credentials)

    def reset(self, scenario: TestScenario) -> None:
        # Check again at the destructive operation, not just at startup.
        if self.document.path != f"demo/{DEMO_DOCUMENT_ID}":
            raise RuntimeError("Reset is restricted to the hackathon demo document.")
        self.seed(scenario, replace=True, advance_minutes=DEMO_ADVANCE_MINUTES)
        Recovery(self).process()


def _demo_store() -> DemoStateStore:
    if os.environ.get("FIRESTORE_DOCUMENT_ID") != DEMO_DOCUMENT_ID:
        raise RuntimeError(f"Set FIRESTORE_DOCUMENT_ID to {DEMO_DOCUMENT_ID}.")
    if os.environ.get("GOOGLE_CLOUD_PROJECT") != "campus-asset-concierge":
        raise RuntimeError("The demo requires the campus-asset-concierge project.")
    if "FIRESTORE_EMULATOR_HOST" in os.environ or os.environ.get("DEV_LOGIN") == "1":
        raise RuntimeError("The hosted demo requires cloud Firestore and password-based accounts.")
    credentials = Credentials.from_service_account_info(json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"]))
    return DemoStateStore(credentials=credentials)


def seed_demo() -> None:
    """Explicit, create-only first seed. Never run during app startup."""
    store = _demo_store()
    store.seed(TestScenario.SPARE_AVAILABLE, advance_minutes=DEMO_ADVANCE_MINUTES)
    Recovery(store).process()


def create_demo_app():
    origin = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    url = urlsplit(origin)
    if (url.scheme != "https" or not url.hostname or url.netloc != url.hostname
            or url.path or url.query or url.fragment):
        raise RuntimeError("Set PUBLIC_BASE_URL to the stable HTTPS origin, without a path.")
    for account in ("BORROWER_A", "BORROWER_B", "STAFF", "OPERATOR"):
        if len(os.environ.get(f"LOCAL_{account}_PASSWORD", "")) < 32:
            raise RuntimeError(f"Set LOCAL_{account}_PASSWORD to a strong generated password.")
    store = _demo_store()
    app = create_app(store)
    app.title = "Campus Asset Concierge · Hackathon Demo"
    app.router.routes[:] = [
        route for route in app.router.routes
        if not route.path.startswith(("/local-test/clock", "/dev-login"))
    ]

    @app.middleware("http")
    async def protect_browser_mutations(request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if not same_origin(request, origin):
                return JSONResponse({"detail": "Open this action from the demo app."}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health")
    def health():
        return {"status": "ok"}

    # shortcut: unauthenticated MCP is approved for this fictional demo only; add OAuth
    # and caller roles when the real Gemini Enterprise connector can be tested.
    mount_mcp(app, store, hosts=[url.hostname], origins=[origin])
    return app
