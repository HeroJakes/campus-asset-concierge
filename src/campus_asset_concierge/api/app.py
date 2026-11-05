import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from secrets import compare_digest
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.api_core.exceptions import NotFound
from pydantic import BaseModel, Field

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

basic = HTTPBasic()


def signed_in(credentials: Annotated[HTTPBasicCredentials, Depends(basic)]) -> LocalAccount:
    account = LOCAL_ACCOUNTS.get(credentials.username)
    if account is not None:
        role, password_variable = account
        password = os.environ.get(password_variable)
        if password and compare_digest(password.encode(), credentials.password.encode()):
            return LocalAccount(credentials.username, role)
    raise HTTPException(401, "Invalid local credentials.", headers={"WWW-Authenticate": "Basic"})


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

    # shortcut: browser-cached Basic sign-in has no CSRF protection, add it before hosting.
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

    @app.get("/locker", response_class=HTMLResponse)
    def locker_page(request: Request, actor: Actor) -> HTMLResponse:
        if actor.role == Role.OPERATOR:
            raise HTTPException(403, "Sign in as staff or a borrower to use the locker page.")
        context = {
            "username": actor.username,
            "current_time": pickups.current_time(),
            "is_staff": actor.role == Role.STAFF,
            "returns": [],
        }
        if actor.role == Role.STAFF:
            context |= pickups.staff_page()
            context["returns"] = returns.staff_returns()
            context["recovery"] = recovery.staff_page()
        else:
            context["pickups"] = pickups.borrower_page(actor.username)
            context["returns"] = returns.borrower_page(actor.username)
        return templates.TemplateResponse(request, "locker.html", context)

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
