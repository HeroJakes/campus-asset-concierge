from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from campus_asset_concierge import dev
from campus_asset_concierge.api.app import create_app


@pytest.mark.parametrize("username,password,role", [
    ("borrower-a", "BorrowerA2026!", "borrower"),
    ("borrower-b", "BorrowerB2026!", "borrower"),
    ("equipment-staff", "Staff2026!", "staff"),
])
def test_dev_login_shows_accounts_and_accepts_them(monkeypatch, username, password, role):
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setenv("DEV_LOGIN", "0")
    for label in ("BORROWER_A", "BORROWER_B", "STAFF", "OPERATOR"):
        monkeypatch.setenv(f"LOCAL_{label}_PASSWORD", f"private-{label}")
    # Login checks do not need a database.
    with patch.object(dev, "create_app", side_effect=lambda **kwargs: create_app(store=object(), **kwargs)):
        app = dev.create_dev_app()
    with TestClient(app) as client:
        page = client.get("/login")
        assert "Try an account" in page.text
        assert username in page.text
        assert password in page.text
        assert "private-" not in page.text
        response = client.post("/login", data={
            "username": username, "password": password, "role": role,
        }, follow_redirects=False)
        assert response.status_code == 303
        assert client.get("/me").json() == {"username": username, "role": role}
        client.cookies.clear()
        assert client.get("/me", auth=("local-operator", password)).status_code == 401


def test_dev_command_uses_local_entrypoint():
    with patch.object(dev.uvicorn, "run") as run:
        dev.main()
    run.assert_called_once_with(
        "campus_asset_concierge.dev:create_dev_app", factory=True,
        host="127.0.0.1", port=8000, reload=True, env_file=".env",
    )
