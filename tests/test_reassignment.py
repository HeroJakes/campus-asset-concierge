from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from conftest import BORROWER_B, OPERATOR, STAFF

RES = "next-projector"  # the seeded next booking that goes at risk when projector-a is overdue


def advance(client, minutes=61):
    response = client.post("/local-test/clock/advance", auth=OPERATOR, json={"minutes": minutes})
    assert response.status_code == 204


def approve(client, reservation_id=RES, auth=STAFF, proposal_id=None):
    if proposal_id is None:
        proposals = client.get("/recovery", auth=STAFF).json()["substitution_proposals"]
        proposal_id = next((p["id"] for p in proposals if p["reservation_id"] == reservation_id), "missing")
    return client.post(
        f"/recovery/substitution-proposals/{reservation_id}/approve", auth=auth,
        json={"proposal_id": proposal_id},
    )


def test_recheck_replaces_pending_proposal_and_rejects_old_approval(booking_app):
    client, store = booking_app
    advance(client)
    first = client.get("/recovery", auth=STAFF).json()["substitution_proposals"][0]

    def change_stock(state):
        state["assets"]["projector-b"]["condition"] = "hold"
        state["assets"]["projector-c"] = {
            "category": "projector", "condition": "good", "has_hdmi": True,
        }

    store.change(change_stock)
    response = client.post(f"/recovery/substitution-proposals/{RES}/recheck", auth=STAFF)
    assert response.status_code == 200
    new = response.json()["proposal"]
    assert new["substitute_asset_id"] == "projector-c"
    assert new["id"] != first["id"]
    assert response.json()["reservation"]["asset_id"] == "projector-a"
    assert approve(client, proposal_id=first["id"]).status_code == 409
    assert approve(client, proposal_id=new["id"]).status_code == 200
    assert approve(client, proposal_id=new["id"]).status_code == 200
    assert actions(store).count("substitution_applied") == 1


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


def test_approval_rechecks_and_preserves_saved_requirements(booking_app):
    client, store = booking_app

    def require_hdmi(state):
        state["reservations"][RES]["require_hdmi"] = True

    store.change(require_hdmi)
    advance(client)

    def change_hdmi(state):
        state["assets"]["projector-b"]["has_hdmi"] = False

    store.change(change_hdmi)
    assert approve(client).status_code == 409

    def restore_hdmi(state):
        state["assets"]["projector-b"]["has_hdmi"] = True

    store.change(restore_hdmi)
    result = approve(client).json()
    assert result["reservation"]["require_hdmi"] is True
    assert result["proposal"]["require_hdmi"] is True


def test_recheck_with_same_stock_is_a_noop_and_staff_only(booking_app):
    client, store = booking_app
    advance(client)
    path = f"/recovery/substitution-proposals/{RES}/recheck"
    before = client.get("/recovery", auth=STAFF).json()
    assert client.post(path).status_code == 401
    for account in (BORROWER_B, OPERATOR):
        assert client.post(path, auth=account).status_code == 403
    for _ in range(2):
        response = client.post(path, auth=STAFF)
        assert response.status_code == 200
        assert response.json()["proposal"] == before["substitution_proposals"][0]
    assert client.get("/recovery", auth=STAFF).json() == before
    page = client.get("/locker", auth=STAFF).text
    assert "Check substitutes again" in page
    assert before["substitution_proposals"][0]["id"] in page
    assert "proposal_id" in page
    assert approve(client).status_code == 200
    assert client.post(path, auth=STAFF).status_code == 409
    assert "Check substitutes again" not in client.get("/locker", auth=STAFF).text


def test_recheck_without_suitable_stock_creates_an_owned_escalation(booking_app):
    client, store = booking_app
    advance(client)

    def hold_spare(state):
        state["assets"]["projector-b"]["condition"] = "hold"

    store.change(hold_spare)
    path = f"/recovery/substitution-proposals/{RES}/recheck"
    response = client.post(path, auth=STAFF)
    assert response.status_code == 200
    assert response.json()["proposal"] is None
    assert response.json()["escalation"]["owner"] == "equipment-staff"
    assert response.json()["reservation"]["asset_id"] == "projector-a"
    assert client.post(path, auth=STAFF).status_code == 404
    body = client.get("/recovery", auth=STAFF).json()
    assert len(body["at_risk_reservations"]) == 1
    event = next(e for e in body["audit_events"] if e["action"] == "substitute_rechecked")
    assert event["actor"] == "equipment-staff"
    assert event["previous_substitute_asset_id"] == "projector-b"
    assert event["proposal_id"] is None
    advance(client, 1)
    assert len(client.get("/recovery", auth=STAFF).json()["escalations"]) == 1


@pytest.mark.parametrize("change", ["missing_reservation", "loaded", "pickup_access", "past_pickup", "returned_loan", "different_asset"])
def test_recheck_rejects_stale_booking_without_writes(booking_app, change):
    client, store = booking_app
    advance(client)

    def stale(state):
        if change == "missing_reservation":
            del state["reservations"][RES]
        elif change == "loaded":
            state["reservations"][RES]["status"] = "ready_for_pickup"
        elif change == "pickup_access":
            state.setdefault("pickup_access", {})[RES] = {}
        elif change == "past_pickup":
            state["elapsed_minutes"] = 121
        elif change == "returned_loan":
            state["loans"]["active-projector"]["status"] = "closed"
        else:
            state["reservations"][RES]["asset_id"] = "projector-b"

    store.change(stale)
    before = store.load()
    assert client.post(f"/recovery/substitution-proposals/{RES}/recheck", auth=STAFF).status_code == 409
    assert store.load() == before


@pytest.mark.parametrize("body", [None, {}, {"proposal_id": ""}, {"proposal_id": 1}])
def test_approval_requires_a_valid_proposal_id(booking_app, body):
    client, _ = booking_app
    advance(client)
    assert client.post(f"/recovery/substitution-proposals/{RES}/approve", auth=STAFF, json=body).status_code == 422


def test_concurrent_recheck_cannot_replace_an_applied_proposal(booking_app):
    client, store = booking_app
    advance(client)
    start = Barrier(2)

    def recheck():
        start.wait(timeout=5)
        return client.post(f"/recovery/substitution-proposals/{RES}/recheck", auth=STAFF)

    def apply():
        start.wait(timeout=5)
        return approve(client, proposal_id="proposal-next-projector")

    with ThreadPoolExecutor(max_workers=2) as pool:
        check = pool.submit(recheck)
        application = pool.submit(apply)
        assert check.result(timeout=20).status_code in (200, 409)
        assert application.result(timeout=20).status_code == 200
    body = client.get("/recovery", auth=STAFF).json()
    assert body["substitution_proposals"][0]["status"] == "applied"
    assert body["at_risk_reservations"] == []
    assert actions(store).count("substitution_applied") == 1
