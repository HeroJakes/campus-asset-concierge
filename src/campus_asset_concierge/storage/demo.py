import os

from google.auth.credentials import AnonymousCredentials
from google.cloud import firestore

from campus_asset_concierge.domain.demo import DemoScenario, starting_state


class DemoStore:
    """Store the local demo as one document so a reset replaces all fixture data."""

    def __init__(self, document_id: str = "current") -> None:
        emulator = os.environ.get("FIRESTORE_EMULATOR_HOST", "")
        host, separator, port = emulator.partition(":")
        if host not in {"127.0.0.1", "localhost"} or not separator or not port.isdecimal():
            raise RuntimeError("Set FIRESTORE_EMULATOR_HOST to a local emulator address.")
        client = firestore.Client(
            project="demo-campus-asset-concierge",
            credentials=AnonymousCredentials(),
        )
        self.document = client.collection("demo").document(document_id)

    def reset(self, scenario: DemoScenario) -> None:
        self.document.set(starting_state(scenario))

    def load(self) -> dict | None:
        return self.document.get().to_dict()

    def advance(self, minutes: int) -> None:
        self.document.update({"elapsed_minutes": firestore.Increment(minutes)})
