import pytest

from campus_asset_concierge.storage.local_state import LocalStateStore


def test_store_requires_emulator_or_project(monkeypatch):
    # With no emulator and no project, the store fails fast instead of guessing.
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    with pytest.raises(RuntimeError, match="GOOGLE_CLOUD_PROJECT"):
        LocalStateStore()


def test_store_rejects_a_non_loopback_emulator(monkeypatch):
    # A non-local emulator address is refused so dev never points at a remote host.
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "evil.example:8080")
    with pytest.raises(RuntimeError, match="local address"):
        LocalStateStore()
