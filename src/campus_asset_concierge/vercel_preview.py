"""Protected Vercel experiment against an isolated fictional Firestore document."""

from contextlib import asynccontextmanager
import json
import os
import re
from secrets import compare_digest

from fastapi.responses import JSONResponse
from google.oauth2.service_account import Credentials

from campus_asset_concierge.api.app import create_app
from campus_asset_concierge.mcp_server import create_mcp_server
from campus_asset_concierge.storage.local_state import LocalStateStore


def create_preview_app():
    document_id = os.environ.get("VERCEL_TEST_DOCUMENT_ID", "")
    if not re.fullmatch(r"vercel-test-[a-z0-9-]+", document_id):
        raise RuntimeError("Set VERCEL_TEST_DOCUMENT_ID to an isolated vercel-test- document.")
    token = os.environ.get("PREVIEW_ACCESS_TOKEN", "")
    if len(token) < 32:
        raise RuntimeError("Set PREVIEW_ACCESS_TOKEN to at least 32 random characters.")
    if "FIRESTORE_EMULATOR_HOST" in os.environ or os.environ.get("DEV_LOGIN") == "1":
        raise RuntimeError("The preview requires cloud Firestore and password-based accounts.")
    credentials = Credentials.from_service_account_info(json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"]))
    store = LocalStateStore(document_id, credentials=credentials)
    app = create_app(store)
    mcp = create_mcp_server(store, transport="streamable-http")
    mcp.settings.json_response = True
    hostname = os.environ.get("VERCEL_URL")
    if hostname:
        mcp.settings.transport_security.allowed_hosts = [hostname]
        mcp.settings.transport_security.allowed_origins = [f"https://{hostname}"]
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app):
        async with mcp_app.router.lifespan_context(mcp_app):
            yield

    app.router.lifespan_context = lifespan

    @app.middleware("http")
    async def protect_preview(request, call_next):
        supplied = request.headers.get("x-preview-token", "")
        if not compare_digest(supplied.encode(), token.encode()):
            return JSONResponse({"detail": "Preview access token required."}, status_code=401)
        return await call_next(request)

    @app.get("/")
    def preview_status():
        return {"status": "preview", "document": store.document.path}

    app.mount("/", mcp_app)
    return app
