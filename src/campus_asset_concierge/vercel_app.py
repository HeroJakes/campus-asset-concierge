"""Shared MCP mounting for the two Vercel entrypoints."""

from contextlib import asynccontextmanager

from campus_asset_concierge.mcp_server import create_mcp_server


def mount_mcp(app, store, *, hosts: list[str], origins: list[str]) -> None:
    mcp = create_mcp_server(store, transport="streamable-http")
    mcp.settings.json_response = True
    if hosts:
        mcp.settings.transport_security.allowed_hosts = hosts
        mcp.settings.transport_security.allowed_origins = origins
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app):
        async with mcp_app.router.lifespan_context(mcp_app):
            yield

    app.router.lifespan_context = lifespan
    app.mount("/", mcp_app)
