"""Emulator-only collection layout. Hosted storage stays on LocalStateStore."""

import os
import re

from google.api_core.exceptions import AlreadyExists
from google.cloud import firestore

from campus_asset_concierge.storage.local_state import LocalStateStore


# Domain keys stay stable; only the Firestore collection names change.
RECORD_COLLECTIONS = {
    "assets": "assets",
    "reservations": "reservations",
    "offers": "reservation_offers",
    "loans": "loans",
    "pickup_access": "pickup_access",
    "return_access": "return_access",
    "reminders": "recovery_reminders",
    "at_risk_reservations": "at_risk_reservations",
    "substitution_proposals": "recovery_proposals",
    "escalations": "recovery_escalations",
}
SPECIAL_GROUPS = {"location", "locker", "audit_events"}


def _records(state: dict) -> tuple[dict, dict[str, dict]]:
    """Split domain state into environment metadata and named records."""
    metadata = {key: value for key, value in state.items()
                if key not in RECORD_COLLECTIONS and key not in SPECIAL_GROUPS}
    metadata["schema_version"] = 1
    metadata["record_groups"] = [key for key in (*RECORD_COLLECTIONS, *sorted(SPECIAL_GROUPS)) if key in state]
    records = {}
    for key, collection in RECORD_COLLECTIONS.items():
        for record_id, value in state.get(key, {}).items():
            if not record_id or "/" in record_id:
                raise ValueError("Record IDs must be non-empty and cannot contain '/'.")
            records[f"{collection}/{record_id}"] = value
    if "location" in state:
        records[f"locations/{state['location']['id']}"] = state["location"]
    if "locker" in state:
        locker = state["locker"]
        records[f"lockers/{locker['id']}"] = {key: value for key, value in locker.items() if key != "compartments"}
        for compartment_id, status in locker["compartments"].items():
            records[f"locker_compartments/{compartment_id}"] = {"locker_id": locker["id"], "status": status}
    for index, event in enumerate(state.get("audit_events", [])):
        records[f"audit_events/event-{index:010d}"] = event
    if any(len(path.split("/")) != 2 or not all(path.split("/")) for path in records):
        raise ValueError("Record paths must contain one collection and one document ID.")
    return metadata, records


class CollectionStateStore(LocalStateStore):
    """Reuse lending transactions while storing each record in its own document."""

    def __init__(self, document_id: str = "development") -> None:
        if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
            raise RuntimeError("The collection layout is emulator-only. Set FIRESTORE_EMULATOR_HOST.")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", document_id):
            raise ValueError("Use a short lowercase environment ID with letters, numbers, '-' or '_'.")
        super().__init__(document_id)
        self.document = self.client.collection("environments").document(document_id)

    def _read_state(self, transaction: firestore.Transaction | None = None) -> dict | None:
        metadata = self.document.get(transaction=transaction).to_dict()
        if metadata is None:
            return None
        if metadata.pop("schema_version", None) != 1:
            raise RuntimeError("Unsupported collection layout version.")
        groups = metadata.pop("record_groups")
        metadata.pop("revision", None)

        def read(collection: str) -> dict:
            return {doc.id: doc.to_dict() for doc in self.document.collection(collection).stream(transaction=transaction)}

        for key, collection in RECORD_COLLECTIONS.items():
            if key in groups:
                metadata[key] = read(collection)
        if "location" in groups:
            locations = read("locations")
            if len(locations) != 1:
                raise RuntimeError("The demo requires exactly one location.")
            metadata["location"] = next(iter(locations.values()))
        if "locker" in groups:
            lockers = read("lockers")
            if len(lockers) != 1:
                raise RuntimeError("The demo requires exactly one locker.")
            metadata["locker"] = next(iter(lockers.values())) | {
                "compartments": {key: value["status"] for key, value in read("locker_compartments").items()},
            }
        if "audit_events" in groups:
            events = read("audit_events")
            metadata["audit_events"] = [events[key] for key in sorted(events)]
        return metadata

    def _write_state(self, transaction: firestore.Transaction, state: dict, previous: dict | None) -> None:
        metadata, records = _records(state)
        old_records = _records(previous)[1] if previous is not None else {}
        # shortcut: serialize changes per demo workspace; use narrower transactions before multi-site use.
        transaction.set(self.document, metadata | {"revision": firestore.Increment(1)})
        for path in old_records.keys() - records.keys():
            transaction.delete(self.client.document(f"{self.document.path}/{path}"))
        for path, value in records.items():
            if path not in old_records or value != old_records[path]:
                transaction.set(self.client.document(f"{self.document.path}/{path}"), value)

    def load(self) -> dict | None:
        # A transaction keeps the root and all child reads at one consistent snapshot.
        return firestore.transactional(self._read_state)(self.client.transaction())

    def _seed_state(self, state: dict, *, replace: bool) -> None:
        def seed(transaction: firestore.Transaction) -> None:
            previous = self._read_state(transaction)
            if previous is not None and not replace:
                raise AlreadyExists(f"Environment {self.document.id} already exists.")
            self._write_state(transaction, state, previous)

        self._transact(seed)

    def advance(self, minutes: int) -> None:
        def advance(state: dict | None) -> None:
            if state is None:
                raise RuntimeError("Seed the emulator environment before advancing its clock.")
            state["elapsed_minutes"] += minutes

        self.change(advance)
