from conftest import BORROWER_B, OPERATOR, STAFF

RES = "next-projector"  # the seeded next booking that goes at risk when projector-a is overdue


def advance(client, minutes=61):
    response = client.post("/local-test/clock/advance", auth=OPERATOR, json={"minutes": minutes})
    assert response.status_code == 204


def approve(client, reservation_id=RES, auth=STAFF):
    return client.post(f"/recovery/substitution-proposals/{reservation_id}/approve", auth=auth)


def actions(store):
    return [event["action"] for event in store.load().get("audit_events", [])]


def test_staff_approve_applies_the_substitute(booking_app):
    client, store = booking_app
    advance(client)

    saved = store.load()
    assert saved["substitution_proposals"][RES]["status"] == "pending_staff_approval"
    assert saved["reservations"][RES]["asset_id"] == "projector-a"

    response = approve(client)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reservation"]["asset_id"] == "projector-b"
    assert body["proposal"]["status"] == "applied"
    assert body["proposal"]["approved_by"] == "equipment-staff"
    assert body["audit_event"]["action"] == "substitution_applied"

    saved = store.load()
    assert saved["reservations"][RES]["asset_id"] == "projector-b"
    assert saved["reservations"][RES]["status"] == "confirmed"
    # The original loan stays overdue for staff follow-up.
    assert saved["loans"]["active-projector"]["status"] == "overdue"
    assert actions(store).count("substitution_applied") == 1
    # The resolved booking is no longer flagged at risk.
    assert RES not in saved["at_risk_reservations"]


def test_approval_is_idempotent(booking_app):
    client, store = booking_app
    advance(client)
    approve(client)

    second = approve(client)
    assert second.status_code == 200
    assert second.json()["reservation"]["asset_id"] == "projector-b"
    assert actions(store).count("substitution_applied") == 1
    assert store.load()["reservations"][RES]["asset_id"] == "projector-b"


def test_only_staff_can_approve(booking_app):
    client, _ = booking_app
    advance(client)
    assert approve(client, auth=BORROWER_B).status_code == 403
    assert approve(client, auth=OPERATOR).status_code == 403


def test_approve_unknown_proposal_is_404(booking_app):
    client, _ = booking_app
    # No clock advance, so no proposal exists yet.
    assert approve(client).status_code == 404


def test_approve_rejected_when_substitute_no_longer_eligible(booking_app):
    client, store = booking_app
    advance(client)  # proposes projector-b for next-projector

    def hold_spare(state):
        state["assets"]["projector-b"]["condition"] = "hold"

    store.change(hold_spare)

    assert approve(client).status_code == 409
    saved = store.load()
    assert saved["substitution_proposals"][RES]["status"] == "pending_staff_approval"
    assert saved["reservations"][RES]["asset_id"] == "projector-a"
