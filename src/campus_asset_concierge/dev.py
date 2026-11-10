"""Start the local web app with automatic reload."""

import uvicorn

from campus_asset_concierge.api.app import create_app


def create_dev_app():
    return create_app(public_demo_accounts=True)


def main() -> None:
    uvicorn.run(
        "campus_asset_concierge.dev:create_dev_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        reload=True,
        env_file=".env",
    )
