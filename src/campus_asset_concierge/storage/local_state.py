import os
from collections.abc import Callable

from google.auth.credentials import AnonymousCredentials
from google.cloud import firestore

from campus_asset_concierge.domain.scenarios import TestScenario, starting_state


class LocalStateStore:
    """Store the local test state as one document so a reset replaces all fixture data."""

    def __init__(self, document_id: str = "current") -> None:
        emulator = os.environ.get("FIRESTORE_EMULATOR_HOST", "")
        host, separator, port = emulator.partition(":")
        if host not in {"127.0.0.1", "localhost"} or not separator or not port.isdecimal():
            raise RuntimeError("Set FIRESTORE_EMULATOR_HOST to a local emulator address.")
        self.client = firestore.Client(
            project="demo-campus-asset-concierge",
            credentials=AnonymousCredentials(),
        )
        self.document = self.client.collection("demo").document(document_id)

    def reset(self, scenario: TestScenario) -> None:
        self.document.set(starting_state(scenario))

    def load(self) -> dict | None:
        return self.document.get().to_dict()

    def advance(self, minutes: int) -> None:
        self.document.update({"elapsed_minutes": firestore.Increment(minutes)})

    def change[T](self, apply: Callable[[dict | None], T]) -> T:
        @firestore.transactional
        def update(transaction: firestore.Transaction) -> T:
            state = self.document.get(transaction=transaction).to_dict()
            result = apply(state)
            if state is not None:
                transaction.set(self.document, state)
            return result

        return update(self.client.transaction())
