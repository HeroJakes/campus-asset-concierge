from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

MALAYSIA_TIME = timezone(timedelta(hours=8), "MYT")


class EquipmentCategory(StrEnum):
    PROJECTOR = "projector"
    RASPBERRY_PI_KIT = "raspberry_pi_kit"


class ReservationError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


def parse_booking_time(value: str) -> datetime:
    try:
        if len(value) < 16 or value[10] not in {"T", " "}:
            raise ValueError
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=MALAYSIA_TIME)
        return parsed.astimezone(MALAYSIA_TIME)
    except (ValueError, OverflowError) as error:
        raise ReservationError(422, "Use a full date and time, such as 2026-11-07T14:00.") from error


class ReservationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: EquipmentCategory
    pickup_at: str
    due_at: str | None = None
    duration_minutes: Annotated[int, Field(strict=True, gt=0)] | None = None

    def window(self) -> tuple[datetime, datetime]:
        pickup = parse_booking_time(self.pickup_at)
        if self.due_at is not None and self.duration_minutes is None:
            due = parse_booking_time(self.due_at)
        elif self.due_at is None and self.duration_minutes is not None:
            try:
                due = pickup + timedelta(minutes=self.duration_minutes)
            except OverflowError as error:
                raise ReservationError(422, "Choose a shorter loan duration.") from error
        else:
            raise ReservationError(422, "Provide either a return time or a loan duration.")
        if due <= pickup:
            raise ReservationError(422, "Return time must be after pickup time.")
        return pickup, due


def local_clock(state: dict) -> datetime:
    return state["starts_at"] + timedelta(minutes=state["elapsed_minutes"])


def eligible_unit(
    state: dict, asset_id: str, category: str, pickup: datetime, due: datetime, now: datetime
) -> bool:
    asset = state["assets"].get(asset_id)
    if not asset or asset["category"] != category or asset["condition"] != "good":
        return False

    for loan in state["loans"].values():
        if loan["asset_id"] != asset_id:
            continue
        if loan["status"] == "overdue":
            return False
        if loan["status"] == "active" and (loan["due_at"] < now or pickup < loan["due_at"]):
            return False

    return not any(
        booking["asset_id"] == asset_id
        and booking["status"] in {"confirmed", "ready_for_pickup"}
        and pickup < booking["due_at"]
        and booking["pickup_at"] < due
        for booking in state["reservations"].values()
    )


def malaysia_times(record: dict) -> dict:
    return {
        **record,
        "pickup_at": record["pickup_at"].astimezone(MALAYSIA_TIME).isoformat(),
        "due_at": record["due_at"].astimezone(MALAYSIA_TIME).isoformat(),
    }
