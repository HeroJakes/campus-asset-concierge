import os
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from google.api_core.exceptions import NotFound
from pydantic import BaseModel, Field

from campus_asset_concierge.domain.demo import BORROWER_A, BORROWER_B, DemoScenario
from campus_asset_concierge.storage.demo import DemoStore


class Role(StrEnum):
    BORROWER = "borrower"
    STAFF = "staff"
    DEMO_OPERATOR = "demo_operator"


@dataclass(frozen=True)
class DemoAccount:
    username: str
    role: Role


DEMO_ACCOUNTS = {
    BORROWER_A: (Role.BORROWER, "DEMO_BORROWER_A_PASSWORD"),
    BORROWER_B: (Role.BORROWER, "DEMO_BORROWER_B_PASSWORD"),
    "staff-demo": (Role.STAFF, "DEMO_STAFF_PASSWORD"),
    "demo-operator": (Role.DEMO_OPERATOR, "DEMO_OPERATOR_PASSWORD"),
}

basic = HTTPBasic()


def signed_in(credentials: Annotated[HTTPBasicCredentials, Depends(basic)]) -> DemoAccount:
    account = DEMO_ACCOUNTS.get(credentials.username)
    if account is not None:
        role, password_variable = account
        password = os.environ.get(password_variable)
        if password and compare_digest(password.encode(), credentials.password.encode()):
            return DemoAccount(credentials.username, role)
    raise HTTPException(401, "Invalid demo credentials.", headers={"WWW-Authenticate": "Basic"})


Actor = Annotated[DemoAccount, Depends(signed_in)]


def require_role(account: DemoAccount, role: Role) -> None:
    if account.role != role:
        raise HTTPException(403, "This demo account cannot perform that action.")


class ResetRequest(BaseModel):
    scenario: DemoScenario


class AdvanceRequest(BaseModel):
    minutes: Annotated[int, Field(strict=True, gt=0, le=1440)]


def create_app(store: DemoStore | None = None) -> FastAPI:
    demo_store = store if store is not None else DemoStore()
    app = FastAPI(title="Campus Asset Concierge · Local Demo")

    def load_state() -> dict:
        state = demo_store.load()
        if state is None:
            raise HTTPException(409, "Reset the demo before using it.")
        return state

    @app.get("/demo/me")
    def who_am_i(actor: Actor) -> DemoAccount:
        return actor

    @app.get("/demo/reservations")
    def my_reservations(actor: Actor) -> list[dict]:
        require_role(actor, Role.BORROWER)
        return [
            {"id": reservation_id, **reservation}
            for reservation_id, reservation in load_state()["reservations"].items()
            if reservation["borrower_id"] == actor.username
        ]

    @app.post("/demo/reset", status_code=204)
    def reset(request: ResetRequest, actor: Actor) -> Response:
        require_role(actor, Role.DEMO_OPERATOR)
        demo_store.reset(request.scenario)
        return Response(status_code=204)

    @app.get("/demo/clock")
    def clock(actor: Actor) -> dict:
        require_role(actor, Role.DEMO_OPERATOR)
        state = load_state()
        current_time = state["starts_at"] + timedelta(minutes=state["elapsed_minutes"])
        return {"scenario": state["scenario"], "current_time": current_time}

    @app.post("/demo/clock/advance", status_code=204)
    def advance(request: AdvanceRequest, actor: Actor) -> Response:
        require_role(actor, Role.DEMO_OPERATOR)
        try:
            demo_store.advance(request.minutes)
        except NotFound as error:
            raise HTTPException(409, "Reset the demo before using it.") from error
        return Response(status_code=204)

    return app
