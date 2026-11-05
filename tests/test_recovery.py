from conftest import BORROWER_B, OPERATOR, STAFF


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
