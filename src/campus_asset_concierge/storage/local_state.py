import os
from collections.abc import Callable
from threading import Lock

from google.auth.credentials import AnonymousCredentials
from google.api_core.exceptions import Aborted
from google.cloud import firestore

from campus_asset_concierge.domain.scenarios import TestScenario, starting_state
from campus_asset_concierge.domain.reservations import ReservationError


# shortcut: this lock covers one process, revisit emulator contention for multi-process runs.
_local_write_lock = Lock()


class LocalStateStore:
    """Store the local test state as one document so a reset replaces all fixture data."""

    def __init__(self, document_id: str = "current") -> None:
        emulator = os.environ.get("FIRESTORE_EMULATOR_HOST", "")
        if emulator:
            host, separator, port = emulator.partition(":")
            if host not in {"127.0.0.1", "localhost"} or not separator or not port.isdecimal():
                raise RuntimeError(
                    "FIRESTORE_EMULATOR_HOST must be a local address like 127.0.0.1:8080."
                )
            # Local emulator (dev, tests, CI): anonymous credentials, fixed demo project.
            self.client = firestore.Client(
                project="demo-campus-asset-concierge",
                credentials=AnonymousCredentials(),
            )
        else:
            # Hosted Firestore: project from GOOGLE_CLOUD_PROJECT, credentials from
            # Application Default Credentials (GOOGLE_APPLICATION_CREDENTIALS key file).
            project = os.environ.get("GOOGLE_CLOUD_PROJECT")
            if not project:
                raise RuntimeError(
                    "Set FIRESTORE_EMULATOR_HOST for local development, or GOOGLE_CLOUD_PROJECT "
                    "(with GOOGLE_APPLICATION_CREDENTIALS pointing at a service-account key) "
                    "to use hosted Firestore."
                )
            self.client = firestore.Client(project=project)
        self.document = self.client.collection("demo").document(document_id)

    def reset(self, scenario: TestScenario) -> None:
        self.seed(scenario, replace=True)

    def seed(self, scenario: TestScenario, *, replace: bool = False, advance_minutes: int = 0) -> None:
        """Create fictional state, replacing it only when explicitly requested."""
        if not 0 <= advance_minutes <= 1440:
            raise ValueError("Advance minutes must be between 0 and 1440.")
        state = starting_state(scenario)
        state["elapsed_minutes"] = advance_minutes
        with _local_write_lock:
            if replace:
                self.document.set(state)
            else:
                self.document.create(state)

    def load(self) -> dict | None:
        return self.document.get().to_dict()

    def advance(self, minutes: int) -> None:
        with _local_write_lock:
            self.document.update({"elapsed_minutes": firestore.Increment(minutes)})

    def change[T](self, apply: Callable[[dict | None], T]) -> T:
        @firestore.transactional
        def update(transaction: firestore.Transaction) -> T:
            state = self.document.get(transaction=transaction).to_dict()
            result = apply(state)
            if state is not None:
                transaction.set(self.document, state)
            return result

        with _local_write_lock:
            try:
                return update(self.client.transaction())
            except (Aborted, ValueError) as error:
                if isinstance(error, Aborted) or isinstance(error.__cause__, Aborted):
                    raise ReservationError(409, "State changed during this action. Please try again.") from error
                raise
