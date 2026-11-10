"""Start the local web app with automatic reload."""

import uvicorn


def main() -> None:
    uvicorn.run(
        "campus_asset_concierge.api.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        reload=True,
        env_file=".env",
    )
