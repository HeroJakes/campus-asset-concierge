import logging
import os
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.api_core.exceptions import NotFound
from pydantic import BaseModel, Field

from campus_asset_concierge import assistant
from campus_asset_concierge.code_email import CodeEmail
from campus_asset_concierge.api.booking_view import booking_overview
from campus_asset_concierge.api.auth import (
    Actor, DEMO_PASSWORDS, LOCAL_ACCOUNTS, LocalAccount, Role, SESSION_COOKIE, SESSION_MAX_AGE,
    authenticate, browser_account, require_role,
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
from campus_asset_concierge.usage import equipment_usage

PACKAGE_DIR = Path(__file__).resolve().parent.parent
logger = logging.getLogger(__name__)

# The borrower assistant model id; override with GEMINI_MODEL. Current free full Flash.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")


class ResetRequest(BaseModel):
    scenario: TestScenario


class AssistantMessage(BaseModel):
    role: Literal["user", "model"]
    text: Annotated[str, Field(min_length=1, max_length=2000)]


class AssistantChat(BaseModel):
    messages: Annotated[list[AssistantMessage], Field(min_length=1, max_length=40)]


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
    code_email = CodeEmail(local_store)
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
        signer = session_signer(account.username) if account is not None else None
        if account is None or account.role != role or signer is None:
            response = templates.TemplateResponse(request, "login.html", {
                "role": role, "username": username,
                "error": "Check your username, password, and account type.",
            }, status_code=401)
        else:
            response = RedirectResponse("/locker", status_code=303)
            response.set_cookie(
                SESSION_COOKIE, f"{account.username}:{signer.dumps(account.username)}",
                max_age=SESSION_MAX_AGE, httponly=True, samesite="strict",
                secure=secure_session_cookie(request),
            )
        response.headers["Cache-Control"] = "no-store"
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

    @app.get("/assistant", response_class=HTMLResponse)
    def assistant_page(request: Request, actor: Actor) -> HTMLResponse:
        require_role(actor, Role.BORROWER)
        response = templates.TemplateResponse(request, "locker_assistant.html", {
            "username": actor.username,
            "current_time": pickups.current_time(),
        })
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/assistant/chat")
    def assistant_chat(payload: AssistantChat, actor: Actor) -> dict:
        require_role(actor, Role.BORROWER)
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {"reply": assistant.FALLBACK_REPLY, "offer": None}
        try:
            return assistant.respond(
                [{"role": m.role, "text": m.text} for m in payload.messages],
                borrower_id=actor.username, reservations=reservations,
                pickups=pickups, returns=returns, current_time=pickups.current_time(),
                api_key=api_key, model=GEMINI_MODEL,
            )
        except Exception:  # noqa: BLE001 - external dependency; degrade to a friendly reply.
            logger.exception("Assistant chat failed")
            return {"reply": assistant.FALLBACK_REPLY, "offer": None}

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
        result = pickups.load(actor.username, reservation_id)
        if result["step"] in {"code_not_open", "enter_code"}:
            code_email.deliver("pickup", reservation_id)
        return result

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
        result = returns.request(actor.username, asset_id)
        if result["step"] == "enter_code":
            code_email.deliver("return", asset_id, actor.username)
        return result

    @app.post("/code-email/{kind}/{record_id}")
    def email_code(kind: Literal["pickup", "return"], record_id: str, actor: Actor) -> dict:
        require_role(actor, Role.BORROWER)
        return code_email.deliver(kind, record_id, actor.username)

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
        }
        if actor.role == Role.STAFF:
            context |= pickups.staff_page()
            context["returns"] = returns.staff_returns()
            context["recovery"] = recovery.staff_page()
            if bookings_page:
                context |= booking_overview(context["reservations"], q, status)
            else:
                context["usage"] = equipment_usage(load_state())
        else:
            context["pickups"] = pickups.borrower_page(actor.username)
            context["returns"] = returns.borrower_page(actor.username)
            context["pickup_location"] = load_state()["location"]["name"]
            context["code_email_enabled"] = code_email.enabled
            context["code_email_statuses"] = code_email.statuses() if code_email.enabled else {}
        return templates.TemplateResponse(request, "locker.html", context)

    @app.get("/logout", include_in_schema=False)
    def logout(request: Request) -> Response:
        require_same_origin(request)
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(
            SESSION_COOKIE, httponly=True, samesite="strict",
            secure=secure_session_cookie(request),
        )
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
