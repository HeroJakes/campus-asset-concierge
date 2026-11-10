"""Run the collection-layout review app against the local emulator only."""

import uvicorn

from campus_asset_concierge.api.app import create_app as create_web_app
from campus_asset_concierge.storage.collection_state import CollectionStateStore


def create_app():
    return create_web_app(CollectionStateStore(), public_demo_accounts=True)


def main() -> None:
    uvicorn.run(
        "campus_asset_concierge.emulator_collections:create_app",
        factory=True, host="127.0.0.1", port=8001, reload=True, env_file=".env",
    )
