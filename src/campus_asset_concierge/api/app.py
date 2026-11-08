from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.api_core.exceptions import NotFound
from pydantic import BaseModel, Field

from campus_asset_concierge.api.booking_view import booking_overview
from campus_asset_concierge.api.auth import (
    Actor, DEMO_PASSWORDS, DEV_ACCOUNTS, LOCAL_ACCOUNTS, LocalAccount, Role, SESSION_COOKIE, SESSION_MAX_AGE,
    authenticate, browser_account, dev_login_enabled, require_role,
    require_same_origin, secure_session_cookie, session_signer,
)
from campus_asset_concierge.domain.reservations import (
    ReservationError,
    ReservationRequest,
    local_clock,
    malaysia_times,
    requirements_text,
)
from campus_asset_concierge.domain.scenarios import TestScenario
from campus_asset_concierge.pickups import Pickups
from campus_asset_concierge.reassignment import Reassignment
from campus_asset_concierge.recovery import Recovery
from campus_asset_concierge.reservations import Reservations
from campus_asset_concierge.returns import Returns
from campus_asset_concierge.storage.local_state import LocalStateStore

PACKAGE_DIR = Path(__file__).resolve().parent.parent


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


def create_app(store: LocalStateStore | None = None, *, public_demo_accounts: bool = False) -> FastAPI:
    local_store = store if store is not None else LocalStateStore()
    reservations = Reservations(local_store)
    pickups = Pickups(local_store)
    returns = Returns(local_store)
    recovery = Recovery(local_store)
    reassignment = Reassignment(local_store)
    app = FastAPI(title="Campus Asset Concierge · Local Development")
    app.state.public_demo_accounts = public_demo_accounts
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")
    templates.env.globals["requirements_text"] = requirements_text
    templates.env.globals["demo_accounts"] = [
        {"username": username, "password": password, "role": LOCAL_ACCOUNTS[username][0].value}
        for username, password in DEMO_PASSWORDS.items()
    ] if public_demo_accounts else []

    @app.get("/", include_in_schema=False)
    def home():
        return RedirectResponse("/login", status_code=303)

    @app.get("/login", response_class=HTMLResponse, include_in_schema=False)
    def login_page(request: Request):
        if browser_account(request) is not None:
            return RedirectResponse("/locker", status_code=303)
        response = templates.TemplateResponse(request, "login.html", {
            "role": "borrower", "username": "", "error": None,
        })
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/login", response_class=HTMLResponse, include_in_schema=False)
    def login(
        request: Request,
        username: Annotated[str, Form(min_length=1, max_length=80)],
        password: Annotated[str, Form(min_length=1, max_length=256)],
        role: Annotated[Literal["borrower", "staff"], Form()],
    ):
        require_same_origin(request)
        username = username.strip()
        account = authenticate(username, password, public_demo_accounts=public_demo_accounts)
        if account is None or account.role != role:
            response = templates.TemplateResponse(request, "login.html", {
                "role": role, "username": username,
                "error": "Check your username, password, and account type.",
            }, status_code=401)
        else:
            signer = session_signer(account.username)
            assert signer is not None
            response = RedirectResponse("/locker", status_code=303)
            response.set_cookie(
                SESSION_COOKIE, f"{account.username}:{signer.dumps(account.username)}",
                max_age=SESSION_MAX_AGE, httponly=True, samesite="strict",
                secure=secure_session_cookie(request),
            )
            response.delete_cookie("dev_account")
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/dev-login", response_class=HTMLResponse)
    def dev_login_page(request: Request) -> HTMLResponse:
        if not dev_login_enabled(request):
            raise HTTPException(404, "Not found.")
        return templates.TemplateResponse(request, "dev_login.html", {"accounts": DEV_ACCOUNTS})

    @app.post("/dev-login/{account}")
    def dev_login(account: str, request: Request) -> RedirectResponse:
        if not dev_login_enabled(request):
            raise HTTPException(404, "Not found.")
        require_same_origin(request)
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

    @app.get("/logout", include_in_schema=False)
    def logout(request: Request) -> Response:
        require_same_origin(request)
        target = "/dev-login" if dev_login_enabled(request) else "/login"
        response = RedirectResponse(target, status_code=303)
        response.delete_cookie(
            SESSION_COOKIE, httponly=True, samesite="strict",
            secure=secure_session_cookie(request),
        )
        response.delete_cookie("dev_account")
        response.headers["Cache-Control"] = "no-store"
        return response

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
