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

from campus_asset_concierge.domain.scenarios import BORROWER_A, BORROWER_B, TestScenario
from campus_asset_concierge.storage.local_state import LocalStateStore


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


def create_app(store: LocalStateStore | None = None) -> FastAPI:
    local_store = store if store is not None else LocalStateStore()
    app = FastAPI(title="Campus Asset Concierge · Local Development")

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
            {"id": reservation_id, **reservation}
            for reservation_id, reservation in load_state()["reservations"].items()
            if reservation["borrower_id"] == actor.username
        ]

    @app.post("/local-test/reset", status_code=204)
    def reset(request: ResetRequest, actor: Actor) -> Response:
        require_role(actor, Role.OPERATOR)
        local_store.reset(request.scenario)
        return Response(status_code=204)

    @app.get("/local-test/clock")
    def clock(actor: Actor) -> dict:
        require_role(actor, Role.OPERATOR)
        state = load_state()
        current_time = state["starts_at"] + timedelta(minutes=state["elapsed_minutes"])
        return {"scenario": state["scenario"], "current_time": current_time}

    @app.post("/local-test/clock/advance", status_code=204)
    def advance(request: AdvanceRequest, actor: Actor) -> Response:
        require_role(actor, Role.OPERATOR)
        try:
            local_store.advance(request.minutes)
        except NotFound as error:
            raise HTTPException(409, "Load a local test scenario first.") from error
        return Response(status_code=204)

    return app
