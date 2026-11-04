import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from campus_asset_concierge.api.app import create_app
from campus_asset_concierge.storage.local_state import LocalStateStore


@pytest.fixture
def local_app(monkeypatch):
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        pytest.skip("Start the Firestore emulator to run the Firestore integration tests.")
    for account in ("BORROWER_A", "BORROWER_B", "STAFF", "OPERATOR"):
        monkeypatch.setenv(f"LOCAL_{account}_PASSWORD", f"test-{account.lower()}")
    store = LocalStateStore(document_id=f"test-{uuid4().hex}")
    try:
        with TestClient(create_app(store)) as client:
            yield client, store
    finally:
        store.document.delete()

BORROWER_A = ("borrower-a", "test-borrower_a")
BORROWER_B = ("borrower-b", "test-borrower_b")
OPERATOR = ("local-operator", "test-operator")


@pytest.fixture
def booking_app(local_app):
    client, store = local_app
    response = client.post("/local-test/reset", auth=OPERATOR, json={"scenario": "spare_available"})
    assert response.status_code == 204
    return client, store
