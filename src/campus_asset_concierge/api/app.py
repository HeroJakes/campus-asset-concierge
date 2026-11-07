import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from secrets import compare_digest
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.api_core.exceptions import NotFound
from pydantic import BaseModel, Field

from campus_asset_concierge.api.booking_view import booking_overview
from campus_asset_concierge.domain.reservations import (
    ReservationError,
    ReservationRequest,
    local_clock,
    malaysia_times,
    requirements_text,
)
from campus_asset_concierge.domain.scenarios import BORROWER_A, BORROWER_B, TestScenario
from campus_asset_concierge.pickups import Pickups
from campus_asset_concierge.reassignment import Reassignment
from campus_asset_concierge.recovery import Recovery
from campus_asset_concierge.reservations import Reservations
from campus_asset_concierge.returns import Returns
from campus_asset_concierge.storage.local_state import LocalStateStore

PACKAGE_DIR = Path(__file__).resolve().parent.parent


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
basic = HTTPBasic(auto_error=False)


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
    dev_mode = dev_login_enabled(request)
    if dev_mode:
        username = DEV_ACCOUNTS.get(request.cookies.get("dev_account", ""))
        if username is not None:
            return LocalAccount(username, LOCAL_ACCOUNTS[username][0])
        if credentials is None and request.url.path.startswith("/locker"):
            raise HTTPException(303, headers={"Location": "/dev-login"})
    account = LOCAL_ACCOUNTS.get(credentials.username) if credentials else None
    if account is not None and credentials is not None:
        role, password_variable = account
        password = os.environ.get(password_variable)
        if password and compare_digest(password.encode(), credentials.password.encode()):
            return LocalAccount(credentials.username, role)
    raise HTTPException(
        401, "Choose a dev account." if dev_mode else "Invalid local credentials.",
        headers={} if dev_mode else {"WWW-Authenticate": "Basic"},
    )


Actor = Annotated[LocalAccount, Depends(signed_in)]


def require_role(account: LocalAccount, role: Role) -> None:
    if account.role != role:
        raise HTTPException(403, "This account cannot perform that action.")


class ResetRequest(BaseModel):
    scenario: TestScenario


class AdvanceRequest(BaseModel):
    minutes: Annotated[int, Field(strict=True, gt=0, le=1440)]


class UnlockRequest(BaseModel):
    code: Annotated[str, Field(min_length=1, max_length=12)]


class VerifyRequest(BaseModel):
    result: Literal["pass", "fail"]


class ApproveRequest(BaseModel):
    proposal_id: Annotated[str, Field(strict=True, min_length=1)]


def create_app(store: LocalStateStore | None = None) -> FastAPI:
    local_store = store if store is not None else LocalStateStore()
    reservations = Reservations(local_store)
    pickups = Pickups(local_store)
    returns = Returns(local_store)
    recovery = Recovery(local_store)
    reassignment = Reassignment(local_store)
    app = FastAPI(title="Campus Asset Concierge · Local Development")
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")
    templates.env.globals["requirements_text"] = requirements_text

    @app.get("/dev-login", response_class=HTMLResponse)
    def dev_login_page(request: Request) -> HTMLResponse:
        if not dev_login_enabled(request):
            raise HTTPException(404, "Not found.")
        return templates.TemplateResponse(request, "dev_login.html", {"accounts": DEV_ACCOUNTS})

    @app.post("/dev-login/{account}")
    def dev_login(account: str, request: Request) -> RedirectResponse:
        if not dev_login_enabled(request):
            raise HTTPException(404, "Not found.")
        if request.headers.get("origin", str(request.base_url).rstrip("/")) != str(request.base_url).rstrip("/"):
            raise HTTPException(403, "Open dev login from this app.")
        if account not in DEV_ACCOUNTS:
            raise HTTPException(404, "Unknown dev account.")
        response = RedirectResponse("/locker", status_code=303)
        # Deliberately selectable identities for loopback-only demos, never public authentication.
        response.set_cookie("dev_account", account, httponly=True, samesite="strict")
        return response

    @app.exception_handler(ReservationError)
    async def reservation_error(_: Request, error: ReservationError) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=error.status)

    def load_state() -> dict:
        state = local_store.load()
        if state is None:
            raise HTTPException(409, "Load a local test scenario first.")
        return state

    @app.get("/me")
    def who_am_i(actor: Actor) -> LocalAccount:
        return actor

    @app.get("/reservations")
    def my_reservations(actor: Actor) -> list[dict]:
        require_role(actor, Role.BORROWER)
        return [
            {"id": reservation_id, **malaysia_times(reservation)}
            for reservation_id, reservation in load_state()["reservations"].items()
            if reservation["borrower_id"] == actor.username
        ]

    @app.post("/reservation-offers", status_code=201)
    def offer_reservation(request: ReservationRequest, actor: Actor) -> dict:
        return reservations.offer(actor.username, request)

    @app.post("/reservation-offers/{offer_id}/confirm")
    def confirm_reservation(offer_id: str, actor: Actor) -> dict:
        return reservations.confirm(actor.username, offer_id)

    # Hosted entrypoints must check the origin of browser mutations with cached Basic auth.
    @app.post("/reservations/{reservation_id}/load")
    def load_reservation(reservation_id: str, actor: Actor) -> dict:
        require_role(actor, Role.STAFF)
        return pickups.load(actor.username, reservation_id)

    @app.get("/pickups")
    def my_pickups(actor: Actor) -> list[dict]:
        require_role(actor, Role.BORROWER)
        return pickups.borrower_page(actor.username)

    @app.get("/recovery")
    def recovery_status(actor: Actor) -> dict:
        require_role(actor, Role.STAFF)
        return recovery.staff_page()

    # Idempotent trigger for a daily scheduler (cron-job.org) once hosted; staff-authenticated.
    @app.post("/recovery/run")
    def run_recovery(actor: Actor) -> dict:
        require_role(actor, Role.STAFF)
        return recovery.process()

    @app.post("/recovery/substitution-proposals/{reservation_id}/approve")
    def approve_substitution(reservation_id: str, request: ApproveRequest, actor: Actor) -> dict:
        require_role(actor, Role.STAFF)
        return reassignment.approve(actor.username, reservation_id, request.proposal_id)

    @app.post("/recovery/substitution-proposals/{reservation_id}/recheck")
    def recheck_substitution(reservation_id: str, actor: Actor) -> dict:
        require_role(actor, Role.STAFF)
        return recovery.recheck(actor.username, reservation_id)

    @app.post("/reservations/{reservation_id}/unlock")
    def unlock_compartment(reservation_id: str, request: UnlockRequest, actor: Actor) -> dict:
        require_role(actor, Role.BORROWER)
        return pickups.unlock(actor.username, reservation_id, request.code)

    @app.post("/reservations/{reservation_id}/confirm-pickup")
    def confirm_pickup(reservation_id: str, actor: Actor) -> dict:
        require_role(actor, Role.BORROWER)
        return pickups.confirm(actor.username, reservation_id)

    @app.post("/assets/{asset_id}/return-request")
    def request_return(asset_id: str, actor: Actor) -> dict:
        require_role(actor, Role.BORROWER)
        return returns.request(actor.username, asset_id)

    @app.post("/assets/{asset_id}/return-unlock")
    def unlock_return(asset_id: str, request: UnlockRequest, actor: Actor) -> dict:
        require_role(actor, Role.BORROWER)
        return returns.unlock(actor.username, asset_id, request.code)

    @app.post("/assets/{asset_id}/return-drop")
    def drop_return(asset_id: str, actor: Actor) -> dict:
        require_role(actor, Role.BORROWER)
        return returns.drop(actor.username, asset_id)

    @app.post("/assets/{asset_id}/verify-return")
    def verify_return(asset_id: str, request: VerifyRequest, actor: Actor) -> dict:
        require_role(actor, Role.STAFF)
        return returns.verify(actor.username, asset_id, request.result)

    @app.get("/returns")
    def my_returns(actor: Actor) -> list[dict]:
        require_role(actor, Role.BORROWER)
        return returns.borrower_page(actor.username)

    @app.get("/locker/bookings", response_class=HTMLResponse)
    @app.get("/locker", response_class=HTMLResponse)
    def locker_page(
        request: Request, actor: Actor, q: str = "",
        status: Literal["all", "to_load", "active", "completed"] = "all",
    ) -> HTMLResponse:
        bookings_page = request.url.path == "/locker/bookings"
        if bookings_page:
            require_role(actor, Role.STAFF)
        if actor.role == Role.OPERATOR:
            raise HTTPException(403, "Sign in as staff or a borrower to use the locker page.")
        context = {
            "username": actor.username,
            "current_time": pickups.current_time(),
            "is_staff": actor.role == Role.STAFF,
            "returns": [],
            "bookings_page": bookings_page,
            "dev_login": dev_login_enabled(request),
        }
        if actor.role == Role.STAFF:
            context |= pickups.staff_page()
            context["returns"] = returns.staff_returns()
            context["recovery"] = recovery.staff_page()
            if bookings_page:
                context |= booking_overview(context["reservations"], q, status)
        else:
            context["pickups"] = pickups.borrower_page(actor.username)
            context["returns"] = returns.borrower_page(actor.username)
        return templates.TemplateResponse(request, "locker.html", context)

    @app.get("/logout", response_class=HTMLResponse)
    def logout(request: Request) -> Response:
        if dev_login_enabled(request):
            response = RedirectResponse("/dev-login", status_code=303)
            response.delete_cookie("dev_account")
            return response
        # HTTP Basic has no real logout; a 401 makes the browser re-prompt so the
        # demo can switch between the staff and borrower accounts.
        body = (
            "<!doctype html><meta charset=utf-8><title>Signed out</title>"
            "<p style=\"font-family:system-ui;margin:2rem\">Signed out. "
            "<a href=\"/locker\">Sign in to the locker</a> with another account.</p>"
        )
        return HTMLResponse(
            body, status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Campus Asset Concierge"'},
        )

    @app.post("/local-test/reset", status_code=204)
    def reset(request: ResetRequest, actor: Actor) -> Response:
        require_role(actor, Role.OPERATOR)
        local_store.reset(request.scenario)
        return Response(status_code=204)

    @app.get("/local-test/clock")
    def clock(actor: Actor) -> dict:
        require_role(actor, Role.OPERATOR)
        state = load_state()
        return {"scenario": state["scenario"], "current_time": local_clock(state)}

    @app.post("/local-test/clock/advance", status_code=204)
    def advance(request: AdvanceRequest, actor: Actor) -> Response:
        require_role(actor, Role.OPERATOR)
        try:
            local_store.advance(request.minutes)
            recovery.process()
        except NotFound as error:
            raise HTTPException(409, "Load a local test scenario first.") from error
        return Response(status_code=204)

    return app
