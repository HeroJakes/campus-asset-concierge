import base64
from concurrent.futures import ThreadPoolExecutor
from email import message_from_bytes
from io import BytesIO
import json
from threading import Barrier
from urllib.error import HTTPError

import pytest

from campus_asset_concierge import code_email
from conftest import BORROWER_A, BORROWER_B, OPERATOR, STAFF
from test_pickups import advance, book, code_for, load, unlock, wrong_code_for
from test_returns import return_request


@pytest.fixture
def mail(monkeypatch):
    monkeypatch.setenv("GMAIL_SENDER", "sender@example.com")
    monkeypatch.setenv("LOCAL_BORROWER_A_EMAIL", "a@example.com")
    monkeypatch.setenv("LOCAL_BORROWER_B_EMAIL", "b@example.com")
    messages = []

    def send(message):
        messages.append(message)
        return "gmail-message-1"

    monkeypatch.setattr(code_email, "send_gmail", send)
    return messages


@pytest.mark.parametrize("kind", ["pickup", "return"])
def test_email_after_saved_action_is_private_and_sent_once(booking_app, mail, monkeypatch, kind):
    client, store = booking_app
    if kind == "pickup":
        key = book(client, category="raspberry_pi_kit")
        action = lambda: load(client, key)
    else:
        key = "projector-a"
        action = lambda: return_request(client)

    original = code_email.send_gmail

    def check_saved(message):
        saved = store.load()[f"{kind}_access"][key]
        assert saved["email_delivery"]["status"] == "sending"
        assert saved["code"] in message.get_content()
        return original(message)

    monkeypatch.setattr(code_email, "send_gmail", check_saved)
    assert action().status_code == 200
    assert action().status_code == 200
    assert len(mail) == 1
    assert mail[0]["To"] == "a@example.com"
    assert mail[0]["From"] == "sender@example.com"
    assert "Compartment: A1" in mail[0].get_content()
    assert "simulated demo clock" in mail[0].get_content()
    saved = store.load()[f"{kind}_access"][key]
    assert saved["email_delivery"]["status"] == "sent"
    assert saved["code"] not in client.get("/locker", auth=BORROWER_A).text
    assert "accepted by Gmail" in client.get("/locker", auth=BORROWER_A).text
    for account, status in ((BORROWER_B, 404), (STAFF, 403), (OPERATOR, 403)):
        assert client.post(f"/code-email/{kind}/{key}", auth=account).status_code == status
    assert client.post(f"/code-email/{kind}/{key}").status_code == 401
    assert client.post(f"/code-email/{kind}/{key}", auth=BORROWER_A).json() == {"status": "sent"}
    assert len(mail) == 1


def test_failed_email_keeps_code_and_borrower_can_retry(booking_app, mail, monkeypatch):
    client, store = booking_app
    original = code_email.send_gmail

    def fail(message):
        raise code_email.DeliveryError("failed")

    monkeypatch.setattr(code_email, "send_gmail", fail)
    assert return_request(client).status_code == 200
    saved_code = store.load()["return_access"]["projector-a"]["code"]
    assert "Code email failed" in client.get("/locker", auth=BORROWER_A).text
    monkeypatch.setattr(code_email, "send_gmail", original)
    assert client.post("/code-email/return/projector-a", auth=BORROWER_A).json() == {"status": "sent"}
    assert saved_code in mail[0].get_content()


def test_uncertain_email_does_not_resend_and_invalid_config_does_not_send(booking_app, mail, monkeypatch):
    client, store = booking_app

    def uncertain(message):
        raise code_email.DeliveryError("unknown")

    monkeypatch.setattr(code_email, "send_gmail", uncertain)
    assert return_request(client).status_code == 200
    assert client.post("/code-email/return/projector-a", auth=BORROWER_A).json() == {"status": "unknown"}
    assert "could not be confirmed" in client.get("/locker", auth=BORROWER_A).text
    monkeypatch.setenv("LOCAL_BORROWER_A_EMAIL", "a@example.com\nBcc: other@example.com")
    key = book(client, category="raspberry_pi_kit")
    assert load(client, key).status_code == 200
    assert store.load()["pickup_access"][key]["email_delivery"]["status"] == "failed"
    assert mail == []


def test_used_and_expired_codes_cannot_be_emailed(booking_app, mail):
    client, _ = booking_app
    key = book(client, category="raspberry_pi_kit")
    assert load(client, key).status_code == 200
    advance(client, 30)
    assert unlock(client, key, code_for(client, key)).status_code == 200
    assert client.post(f"/code-email/pickup/{key}", auth=BORROWER_A).status_code == 409
    assert return_request(client).status_code == 200
    advance(client, 31)
    assert client.post("/code-email/return/projector-a", auth=BORROWER_A).status_code == 409
    assert len(mail) == 2


def test_borrower_b_mapping_and_blocked_code(booking_app, mail):
    client, _ = booking_app
    key = book(client, auth=BORROWER_B, category="raspberry_pi_kit")
    assert load(client, key).status_code == 200
    assert mail[0]["To"] == "b@example.com"
    advance(client, 30)
    code = code_for(client, key, BORROWER_B)
    for _ in range(5):
        assert unlock(client, key, wrong_code_for(code), BORROWER_B).status_code == 403
    assert client.post(f"/code-email/pickup/{key}", auth=BORROWER_B).status_code == 409
    assert len(mail) == 1


def test_competing_email_requests_send_only_once(booking_app, mail, monkeypatch):
    client, store = booking_app
    monkeypatch.delenv("GMAIL_SENDER")
    assert return_request(client).status_code == 200
    monkeypatch.setenv("GMAIL_SENDER", "sender@example.com")
    start = Barrier(2)

    def deliver():
        start.wait(timeout=5)
        return code_email.CodeEmail(store).deliver("return", "projector-a", "borrower-a")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(deliver) for _ in range(2)]
        assert all(result.result(timeout=20)["status"] in {"sent", "sending"} for result in results)
    assert len(mail) == 1


def test_gmail_transport_sends_mime_and_never_retries(monkeypatch):
    monkeypatch.setenv("GMAIL_OAUTH_JSON", json.dumps({
        "client_id": "client", "client_secret": "secret", "refresh_token": "refresh",
    }))
    calls = []

    def open_request(request, timeout):
        calls.append(request)
        assert timeout == 10
        if len(calls) == 1:
            return BytesIO(b'{"access_token":"access"}')
        raw = json.loads(request.data)["raw"]
        message = message_from_bytes(base64.urlsafe_b64decode(raw))
        assert message["To"] == "a@example.com"
        return BytesIO(b'{"id":"sent-1"}')

    monkeypatch.setattr(code_email, "urlopen", open_request)
    message = code_email.EmailMessage()
    message["To"] = "a@example.com"
    message.set_content("Code: 001234")
    assert code_email.send_gmail(message) == "sent-1"
    assert len(calls) == 2

    def fail_send(request, timeout):
        if request.full_url.endswith("/token"):
            return BytesIO(b'{"access_token":"access"}')
        raise HTTPError(request.full_url, 503, "Unavailable", {}, None)

    monkeypatch.setattr(code_email, "urlopen", fail_send)
    with pytest.raises(code_email.DeliveryError) as error:
        code_email.send_gmail(message)
    assert error.value.status == "unknown"
