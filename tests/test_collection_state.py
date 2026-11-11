import os
from unittest.mock import patch
from uuid import uuid4

import pytest
from google.api_core.exceptions import AlreadyExists

from campus_asset_concierge.domain.scenarios import TestScenario as Scenario, starting_state
from campus_asset_concierge.storage.collection_state import CollectionStateStore
from campus_asset_concierge.storage.local_state import LocalStateStore


@pytest.fixture
def collection_store():
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        pytest.skip("Start the Firestore emulator for collection-layout checks.")
    store = CollectionStateStore(f"test-{uuid4().hex}")
    try:
        yield store
    finally:
        store.client.recursive_delete(store.document)


def test_collection_layout_cannot_fall_back_to_cloud(monkeypatch):
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "campus-asset-concierge")
    with patch("campus_asset_concierge.storage.local_state.firestore.Client") as client:
        with pytest.raises(RuntimeError, match="emulator-only"):
            CollectionStateStore()
        client.assert_not_called()


@pytest.mark.parametrize("environment", ["demo/current", "../current", "", "Mixed Case"])
def test_environment_ids_cannot_escape_their_workspace(monkeypatch, environment):
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")
    with pytest.raises(ValueError, match="environment ID"):
        CollectionStateStore(environment)


def test_collection_layout_rejects_a_remote_emulator(monkeypatch):
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "remote.example:8080")
    with pytest.raises(RuntimeError, match="local address"):
        CollectionStateStore()


def test_seed_creates_named_records_and_preserves_the_domain_state(collection_store):
    store = collection_store
    assert store.load() is None
    store.seed(Scenario.SPARE_AVAILABLE)
    assert store.client.project == "demo-campus-asset-concierge"
    assert store.document.path.startswith("environments/test-")
    assert store.load() == starting_state(Scenario.SPARE_AVAILABLE)
    metadata = store.document.get().to_dict()
    assert metadata["schema_version"] == 1
    assert "assets" not in metadata and "loans" not in metadata
    assert store.document.collection("assets").document("projector-a").get().exists
    assert store.document.collection("loans").document("active-projector").get().exists
    compartment = store.document.collection("locker_compartments").document("a1").get().to_dict()
    assert compartment == {"locker_id": "locker-a", "status": "empty"}
    before = store.document.get()
    with pytest.raises(AlreadyExists):
        store.seed(Scenario.SPARE_UNAVAILABLE)
    assert store.document.get().update_time == before.update_time


def test_reset_removes_old_records_and_preserves_audit_order(collection_store):
    store = collection_store
    store.seed(Scenario.SPARE_AVAILABLE)

    def add_records(state):
        state["reservation_offers"] = {"old-offer": {"borrower_id": "borrower-a"}}
        state["audit_events"] = [{"action": "first"}, {"action": "second"}]

    store.change(add_records)
    assert store.load()["audit_events"] == [{"action": "first"}, {"action": "second"}]
    assert store.document.collection("reservation_offers").document("old-offer").get().exists
    store.advance(61)
    assert store.load()["elapsed_minutes"] == 61
    store.reset(Scenario.SPARE_UNAVAILABLE)
    assert store.load() == starting_state(Scenario.SPARE_UNAVAILABLE)
    assert list(store.document.collection("reservation_offers").stream()) == []
    assert list(store.document.collection("audit_events").stream()) == []


def test_diff_writes_leave_unchanged_assets_alone(collection_store):
    store = collection_store
    store.seed(Scenario.SPARE_AVAILABLE)
    asset = store.document.collection("assets").document("projector-a")
    before = asset.get().update_time
    store.advance(10)
    assert asset.get().update_time == before
    assert store.load()["elapsed_minutes"] == 10


def test_invalid_nested_record_path_rolls_back_the_whole_change(collection_store):
    store = collection_store
    store.seed(Scenario.SPARE_AVAILABLE)
    before = store.document.get()

    def invalid(state):
        state["location"]["id"] = "invalid/nested/id"

    with pytest.raises(ValueError, match="Record paths"):
        store.change(invalid)
    assert store.document.get().update_time == before.update_time
    assert store.load() == starting_state(Scenario.SPARE_AVAILABLE)


def test_collection_environment_cannot_modify_a_legacy_document(collection_store):
    store = collection_store
    legacy = LocalStateStore(store.document.id)
    try:
        legacy.seed(Scenario.SPARE_UNAVAILABLE)
        before = legacy.document.get()
        store.seed(Scenario.SPARE_AVAILABLE)
        store.advance(61)
        store.reset(Scenario.SPARE_AVAILABLE)
        after = legacy.document.get()
        assert after.to_dict() == before.to_dict()
        assert after.update_time == before.update_time
    finally:
        legacy.document.delete()
