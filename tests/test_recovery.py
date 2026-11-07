import pytest

from conftest import BORROWER_B, OPERATOR, STAFF


def test_recovery_escalates_when_spare_lacks_required_speakers(booking_app):
    client, store = booking_app

    def need_speakers(state):
        state["reservations"]["next-projector"]["require_built_in_speakers"] = True

    store.change(need_speakers)
    advance(client)
    body = client.get("/recovery", auth=STAFF).json()
    assert body["substitution_proposals"] == []
    assert body["escalations"][0]["require_built_in_speakers"] is True
    assert body["escalations"][0]["owner"] == "equipment-staff"


@pytest.mark.parametrize("speakers_required", [True, False])
def test_new_booking_requirements_follow_the_full_recovery_rehearsal(booking_app, speakers_required):
    client, _ = booking_app
    offer = client.post("/reservation-offers", auth=BORROWER_B, json={
        "category": "projector", "pickup_at": "2026-11-07T13:00", "duration_minutes": 60,
        "require_hdmi": True, "require_built_in_speakers": speakers_required,
    }).json()
    booking = client.post(f"/reservation-offers/{offer['id']}/confirm", auth=BORROWER_B).json()
    assert booking["asset_id"] == "projector-a"
    advance(client)
    seeded = client.get("/recovery", auth=STAFF).json()["substitution_proposals"][0]
    assert client.post("/recovery/substitution-proposals/next-projector/approve", auth=STAFF,
                       json={"proposal_id": seeded["id"]}).status_code == 200
    advance(client, 1)
    recovery = client.get("/recovery", auth=STAFF).json()
    if speakers_required:
        escalation = next(e for e in recovery["escalations"] if e["reservation_id"] == booking["id"])
        assert escalation["require_built_in_speakers"] is True
        assert escalation["owner"] == "equipment-staff"
    else:
        path = f"/recovery/substitution-proposals/{booking['id']}"
        checked = client.post(f"{path}/recheck", auth=STAFF).json()["proposal"]
        assert checked["substitute_asset_id"] == "projector-b"
        applied = client.post(f"{path}/approve", auth=STAFF, json={"proposal_id": checked["id"]}).json()
        assert applied["reservation"]["require_hdmi"] is True
        assert applied["reservation"]["require_built_in_speakers"] is False
        assert applied["reservation"]["asset_id"] == "projector-b"
    assert client.get("/recovery", auth=STAFF).json()["overdue_loans"][0]["id"] == "active-projector"


def advance(client, minutes=61):
    response = client.post(
        "/local-test/clock/advance", auth=OPERATOR, json={"minutes": minutes}
    )
    assert response.status_code == 204


def test_overdue_recovery_records_a_verified_spare_proposal(booking_app):
    client, store = booking_app

    advance(client)

    saved = store.load()
    assert saved["loans"]["active-projector"]["status"] == "overdue"
    assert saved["reservations"]["next-projector"]["status"] == "confirmed"
    assert len(saved["reminders"]) == 1
    assert len(saved["at_risk_reservations"]) == 1
    assert saved["substitution_proposals"]["next-projector"] == {
        "id": "proposal-next-projector",
        "reservation_id": "next-projector",
        "loan_id": "active-projector",
        "original_asset_id": "projector-a",
        "substitute_asset_id": "projector-b",
        "status": "pending_staff_approval",
        "verified": True,
        "verified_at": saved["substitution_proposals"]["next-projector"]["verified_at"],
    }
    assert saved["escalations"] == {}
    # Recovery events keep the shared audit shape (asset_id on every event).
    assert all(event["asset_id"] == "projector-a" for event in saved["audit_events"])

    recovery = client.get("/recovery", auth=STAFF)
    assert recovery.status_code == 200
    body = recovery.json()
    assert body["substitution_proposals"][0]["substitute_asset_id"] == "projector-b"
    assert body["substitution_proposals"][0]["verified"] is True
    assert body["reminders"][0]["simulated"] is True
    assert body["at_risk_reservations"][0]["status"] == "confirmed"

    page = client.get("/locker", auth=STAFF)
    assert page.status_code == 200
    assert "Verified substitute proposal" in page.text
    assert "Awaiting staff approval" in page.text
    assert "Simulated reminder queued" in page.text


def test_overdue_recovery_creates_a_staff_owned_escalation_when_spare_is_booked(local_app):
    client, store = local_app
    reset = client.post(
        "/local-test/reset", auth=OPERATOR, json={"scenario": "spare_unavailable"}
    )
    assert reset.status_code == 204

    advance(client)

    saved = store.load()
    assert saved["loans"]["active-projector"]["status"] == "overdue"
    assert saved["substitution_proposals"] == {}
    assert saved["escalations"]["next-projector"]["owner"] == "equipment-staff"
    assert saved["escalations"]["next-projector"]["status"] == "open"
    assert saved["reservations"]["next-projector"]["asset_id"] == "projector-a"
    assert saved["reservations"]["next-projector"]["status"] == "confirmed"

    body = client.get("/recovery", auth=STAFF).json()
    assert body["escalations"][0]["owner_role"] == "staff"
    assert body["substitution_proposals"] == []
    assert "Staff-owned escalation" in client.get("/locker", auth=STAFF).text



def test_run_recovery_endpoint_detects_overdue_and_is_staff_only(booking_app):
    client, store = booking_app

    # Advance the clock directly, bypassing the route that also runs recovery,
    # so the loan is due but recovery has not processed it yet.
    store.advance(61)
    assert store.load()["loans"]["active-projector"]["status"] == "active"

    ran = client.post("/recovery/run", auth=STAFF)
    assert ran.status_code == 200
    assert ran.json()["substitution_proposals"][0]["substitute_asset_id"] == "projector-b"
    assert store.load()["loans"]["active-projector"]["status"] == "overdue"

    # Safe for a daily scheduler to call repeatedly.
    assert client.post("/recovery/run", auth=STAFF).status_code == 200
    assert client.post("/recovery/run", auth=BORROWER_B).status_code == 403
    assert client.post("/recovery/run", auth=OPERATOR).status_code == 403
    assert client.post("/recovery/run").status_code == 401


def test_recovery_is_idempotent_and_staff_only(booking_app):
    client, store = booking_app
    advance(client)
    first = store.load()
    first_audit = list(first["audit_events"])

    advance(client, 1)
    second = store.load()
    assert len(second["reminders"]) == 1
    assert len(second["at_risk_reservations"]) == 1
    assert len(second["substitution_proposals"]) == 1
    assert len(second["audit_events"]) == len(first_audit)
    assert [event["action"] for event in second["audit_events"]] == [
        "overdue_marked",
        "reminder_queued",
        "booking_at_risk",
        "substitute_proposed",
    ]

    assert client.get("/recovery", auth=BORROWER_B).status_code == 403
    assert client.get("/recovery", auth=OPERATOR).status_code == 403
