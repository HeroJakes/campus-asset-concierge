from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

MALAYSIA_TIME = timezone(timedelta(hours=8), "MYT")
# A return code is usable from the moment it is issued until this long after.
RETURN_CODE_WINDOW = timedelta(minutes=30)


def equipment_requirements(record: dict) -> dict[str, bool]:
    return {
        "require_hdmi": record.get("require_hdmi", False),
        "require_built_in_speakers": record.get("require_built_in_speakers", False),
    }


def requirements_text(record: dict) -> str:
    needs = equipment_requirements(record)
    return ", ".join(
        label for key, label in (
            ("require_hdmi", "HDMI"),
            ("require_built_in_speakers", "Built-in speakers"),
        ) if needs[key]
    ) or "No extra requirements"


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
    require_hdmi: StrictBool = False
    require_built_in_speakers: StrictBool = False

    @model_validator(mode="after")
    def projector_requirements(self) -> Self:
        if self.category != EquipmentCategory.PROJECTOR and (
            self.require_hdmi or self.require_built_in_speakers
        ):
            raise ValueError("HDMI and built-in speaker requirements apply to projectors only.")
        return self

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


def reassignment_applicable(
    state: dict, reservation_id: str, original_asset_id: str, now: datetime,
) -> bool:
    reservation = state["reservations"].get(reservation_id)
    return bool(
        reservation
        and reservation["status"] == "confirmed"
        and reservation["asset_id"] == original_asset_id
        and reservation_id not in state.get("pickup_access", {})
        and reservation["pickup_at"] >= now
    )


def return_live(access: dict, now: datetime) -> bool:
    """A return holds its unit and compartment until checked: once unlocked or dropped, or while its code works."""
    if access["checked_at"] is not None:
        return False
    return (
        access["dropped_at"] is not None or access["used_at"] is not None
        or now <= access["issued_at"] + RETURN_CODE_WINDOW
    )


def find_free_compartment(state: dict, now: datetime) -> tuple[str, str | None]:
    """Pick an empty compartment, or one held by an expired, unused return (its asset ID is returned too)."""
    compartments = state["locker"]["compartments"]
    for compartment in sorted(compartments):
        if compartments[compartment] == "empty":
            return compartment, None
        stale = next((
            asset_id for asset_id, access in state.get("return_access", {}).items()
            if access["compartment"] == compartment and access["checked_at"] is None
            and not return_live(access, now)
        ), None)
        if stale is not None:
            return compartment, stale
    raise ReservationError(409, "Both compartments are full.")


def claim_free_compartment(state: dict, now: datetime) -> str:
    compartment, stale = find_free_compartment(state, now)
    if stale is not None:
        del state["return_access"][stale]
        state["locker"]["compartments"][compartment] = "empty"
    return compartment


def uncollected_pickups(state: dict, asset_id: str) -> list[dict]:
    """Pickup access for a unit that is loaded in a compartment and not yet collected."""
    return [
        access for access in state.get("pickup_access", {}).values()
        if access["asset_id"] == asset_id and access["collected_at"] is None
    ]


def eligible_unit(
    state: dict, asset_id: str, category: str, pickup: datetime, due: datetime, now: datetime,
    require_hdmi: bool = False, require_built_in_speakers: bool = False,
) -> bool:
    asset = state["assets"].get(asset_id)
    if not asset or asset["category"] != category or asset["condition"] != "good":
        return False
    if require_hdmi and asset.get("has_hdmi") is not True:
        return False
    if require_built_in_speakers and asset.get("has_built_in_speakers") is not True:
        return False

    for loan in state["loans"].values():
        if loan["asset_id"] != asset_id:
            continue
        # A dropped-but-unchecked return holds the unit until staff verify it.
        if loan["status"] in {"overdue", "awaiting_check"}:
            return False
        if loan["status"] == "active" and (loan["due_at"] < now or pickup < loan["due_at"]):
            return False

    # A loaded unit cannot serve any window that starts before its booking ends.
    if any(pickup < access["due_at"] for access in uncollected_pickups(state, asset_id)):
        return False

    # A return in progress (code issued, not yet verified) holds the unit entirely.
    access = state.get("return_access", {}).get(asset_id)
    if access is not None and return_live(access, now):
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
