"""Shared account checks for browser sessions and HTTP Basic clients."""

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import os
from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from itsdangerous import BadData, URLSafeTimedSerializer

from campus_asset_concierge.domain.scenarios import BORROWER_A, BORROWER_B


class Role(StrEnum):
    BORROWER = "borrower"
    STAFF = "staff"
    OPERATOR = "operator"


@dataclass(frozen=True)
class LocalAccount:
    username: str
    role: Role


LOCAL_ACCOUNTS = {
    BORROWER_A: (Role.BORROWER, "LOCAL_BORROWER_A_PASSWORD"),
    BORROWER_B: (Role.BORROWER, "LOCAL_BORROWER_B_PASSWORD"),
    "equipment-staff": (Role.STAFF, "LOCAL_STAFF_PASSWORD"),
    "local-operator": (Role.OPERATOR, "LOCAL_OPERATOR_PASSWORD"),
}
DEV_ACCOUNTS = {"borrower_a": BORROWER_A, "borrower_b": BORROWER_B, "staff": "equipment-staff"}
# Public test credentials for the hackathon and loopback development entrypoints.
DEMO_PASSWORDS = {
    BORROWER_A: "BorrowerA2026!",
    BORROWER_B: "BorrowerB2026!",
    "equipment-staff": "Staff2026!",
}
SESSION_COOKIE = "campus_session"
SESSION_MAX_AGE = 8 * 60 * 60
basic = HTTPBasic(auto_error=False)


def authenticate(username: str, password: str, *, public_demo_accounts: bool = False) -> LocalAccount | None:
    account = LOCAL_ACCOUNTS.get(username)
    if account is not None:
        role, variable = account
        expected = os.environ.get(variable)
        if expected and compare_digest(expected.encode(), password.encode()):
            return LocalAccount(username, role)
        public_password = DEMO_PASSWORDS.get(username) if public_demo_accounts else None
        if public_password and compare_digest(public_password.encode(), password.encode()):
            return LocalAccount(username, role)
    return None


def session_signer(username: str) -> URLSafeTimedSerializer | None:
    account = LOCAL_ACCOUNTS.get(username)
    if account is None or account[0] == Role.OPERATOR:
        return None
    password = os.environ.get(account[1])
    # A purpose-specific salt separates cookie signatures from password authentication.
    # The existing strong account secret also revokes that account's cookies on rotation.
    return URLSafeTimedSerializer(
        password, salt="campus-browser-session-v1", signer_kwargs={"digest_method": sha256},
    ) if password else None


def browser_account(request: Request) -> LocalAccount | None:
    cookie = request.cookies.get(SESSION_COOKIE, "")
    if len(cookie) > 2048:
        return None
    username, separator, token = cookie.partition(":")
    signer = session_signer(username) if separator else None
    if signer is not None:
        try:
            if signer.loads(token, max_age=SESSION_MAX_AGE) == username:
                return LocalAccount(username, LOCAL_ACCOUNTS[username][0])
        except BadData:
            pass
    return None


def same_origin(request: Request, expected: str | None = None) -> bool:
    origin = expected or os.environ.get("PUBLIC_BASE_URL") or str(request.base_url).rstrip("/")
    supplied = request.headers.get("origin")
    return ((supplied is None or supplied == origin.rstrip("/"))
            and request.headers.get("sec-fetch-site") != "cross-site")


def require_same_origin(request: Request) -> None:
    if not same_origin(request):
        raise HTTPException(403, "Open this action from the app.")


def secure_session_cookie(request: Request) -> bool:
    # A TLS-terminating host may forward an internal HTTP request to the app.
    return (request.url.scheme == "https"
            or os.environ.get("PUBLIC_BASE_URL", "").startswith("https://"))


def dev_login_enabled(request: Request) -> bool:
    return (
        os.environ.get("DEV_LOGIN") == "1"
        and request.client is not None
        and request.client.host in {"127.0.0.1", "::1"}
        and request.url.hostname in {"127.0.0.1", "localhost", "::1"}
    )


def signed_in(
    request: Request, credentials: Annotated[HTTPBasicCredentials | None, Depends(basic)],
) -> LocalAccount:
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        require_same_origin(request)
    dev_mode = dev_login_enabled(request)
    if dev_mode:
        username = DEV_ACCOUNTS.get(request.cookies.get("dev_account", ""))
        if username is not None:
            return LocalAccount(username, LOCAL_ACCOUNTS[username][0])
    account = browser_account(request)
    if account is not None:
        return account
    if credentials is not None:
        account = authenticate(
            credentials.username, credentials.password,
            public_demo_accounts=request.app.state.public_demo_accounts,
        )
        if account is not None:
            return account
    if credentials is None and request.url.path.startswith("/locker"):
        raise HTTPException(303, headers={"Location": "/dev-login" if dev_mode else "/login"})
    raise HTTPException(
        401, "Choose a dev account." if dev_mode else "Invalid credentials.",
        headers={} if dev_mode else {"WWW-Authenticate": "Basic"},
    )


Actor = Annotated[LocalAccount, Depends(signed_in)]


def require_role(account: LocalAccount, role: Role) -> None:
    if account.role != role:
        raise HTTPException(403, "This account cannot perform that action.")
