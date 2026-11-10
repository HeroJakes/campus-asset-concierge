"""Optional Gmail delivery for fictional pickup and return codes."""

import base64
from email.message import EmailMessage
import json
import os
import re
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from campus_asset_concierge.domain.reservations import (
    MALAYSIA_TIME, RETURN_CODE_WINDOW, ReservationError, local_clock,
)
from campus_asset_concierge.pickups import CODE_WINDOW, MAX_WRONG_TRIES


def _address(value: str) -> str:
    # Only one plain address is accepted; never accept recipient headers from a request.
    if not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", value):
        raise ValueError("Configure one plain email address per demo account.")
    return value


class DeliveryError(Exception):
    def __init__(self, status: str):
        self.status = status


def send_gmail(message: EmailMessage) -> str:
    """Use send-only OAuth credentials. Never retry an uncertain send automatically."""
    try:
        credentials = json.loads(os.environ["GMAIL_OAUTH_JSON"])
        body = urlencode({key: credentials[key] for key in (
            "client_id", "client_secret", "refresh_token",
        )} | {"grant_type": "refresh_token"}).encode()
        with urlopen(Request("https://oauth2.googleapis.com/token", data=body), timeout=10) as response:
            token = json.load(response)["access_token"]
    except Exception:
        raise DeliveryError("failed") from None

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    request = Request(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        data=json.dumps({"raw": raw}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            return json.load(response)["id"]
    except HTTPError as error:
        raise DeliveryError("failed" if 400 <= error.code < 500 and error.code != 408 else "unknown") from None
    except Exception:
        raise DeliveryError("unknown") from None


class CodeEmail:
    def __init__(self, store):
        self.store = store

    @property
    def enabled(self) -> bool:
        return bool(os.environ.get("GMAIL_SENDER"))

    def statuses(self) -> dict:
        state = self.store.load() or {}
        return {
            kind: {key: value.get("email_delivery", {}).get("status", "not_sent")
                   for key, value in state.get(f"{kind}_access", {}).items()}
            for kind in ("pickup", "return")
        }

    def deliver(self, kind: str, key: str, borrower_id: str | None = None) -> dict:
        if not self.enabled:
            return {"status": "disabled"}
        attempt_id = uuid4().hex

        def claim(state):
            access = state.get(f"{kind}_access", {}).get(key) if state else None
            if access is None:
                raise ReservationError(404, "Code not found.")
            booking = state["reservations"][key] if kind == "pickup" else access
            owner = booking["borrower_id"]
            if borrower_id is not None and borrower_id != owner:
                raise ReservationError(404, "Code not found.")
            opens = booking["pickup_at"] if kind == "pickup" else access["issued_at"]
            closes = opens + (CODE_WINDOW if kind == "pickup" else RETURN_CODE_WINDOW)
            if (access["used_at"] is not None or access["failed_tries"] >= MAX_WRONG_TRIES
                    or local_clock(state) > closes):
                raise ReservationError(409, "This code is no longer usable.")
            delivery = access.get("email_delivery", {})
            if delivery.get("status") in {"sent", "sending", "unknown"}:
                return {"status": delivery["status"]}
            access["email_delivery"] = {"status": "sending", "attempt_id": attempt_id}
            return {"status": "claimed", "code": access["code"], "owner": owner,
                    "asset": access["asset_id"] if kind == "pickup" else key,
                    "compartment": access["compartment"], "opens": opens, "closes": closes,
                    "location": state["location"]["name"]}

        claimed = self.store.change(claim)
        if claimed["status"] != "claimed":
            return claimed
        status, message_id = "failed", None
        try:
            sender = _address(os.environ["GMAIL_SENDER"])
            recipient = _address(os.environ[f"LOCAL_{claimed['owner'].upper().replace('-', '_')}_EMAIL"])
            message = EmailMessage()
            message["From"], message["To"] = sender, recipient
            message["Subject"] = f"Your {kind} code for {claimed['asset'].replace('-', ' ')}"
            message.set_content(
                f"Campus Asset Concierge — fictional demo\n\n"
                f"Your one-time {kind} code: {claimed['code']}\n"
                f"Item: {claimed['asset']}\nLocation: {claimed['location']}\n"
                f"Compartment: {claimed['compartment'].upper()}\n"
                f"Valid from: {claimed['opens'].astimezone(MALAYSIA_TIME).isoformat()}\n"
                f"Expires: {claimed['closes'].astimezone(MALAYSIA_TIME).isoformat()}\n\n"
                "Times follow the simulated demo clock, not the real clock.\n"
                "Enter this code on My Locker, then confirm pickup or drop-off.\n"
            )
            message_id = send_gmail(message)
            status = "sent"
        except DeliveryError as error:
            status = error.status
        except (KeyError, ValueError):
            pass

        def finish(state):
            access = state.get(f"{kind}_access", {}).get(key) if state else None
            if access and access.get("email_delivery", {}).get("attempt_id") == attempt_id:
                access["email_delivery"] = {"status": status, "attempt_id": attempt_id,
                                            "message_id": message_id}

        self.store.change(finish)
        return {"status": status}
