import re

from conftest import BORROWER_A, OPERATOR, STAFF
from test_pickups import code_for, load, pick_up, unlock
from test_returns import code_for as return_code_for
from test_returns import return_drop, return_request, return_unlock, verify


def start_presentation(client):
    # Same state the hosted reset gives: the presentation seed at 11:01 with recovery run.
    assert client.post("/local-test/reset", auth=OPERATOR, json={"scenario": "presentation"}).status_code == 204
    assert client.post("/local-test/clock/advance", auth=OPERATOR, json={"minutes": 61}).status_code == 204


def test_presentation_seed_fills_every_staff_panel(booking_app):
    client, _ = booking_app
    start_presentation(client)

    html = client.get("/locker", auth=STAFF).text
    assert re.search(r"2 in use · 4 free", html)
    assert 'data-open-dialog="return-projector-c"' in html  # a return waiting for its check
    assert "Verified substitute proposal" in html
    usage = {unit: status for unit, status in re.findall(
        r'<td class="identity">([^<]+)</td>\s*<td>([^<]+)</td>', html)}
    assert usage["Projector A"] == "Overdue"
    assert usage["Projector C"] == "Awaiting return check"
    assert usage["Raspberry Pi Kit C"] == "Loaded in locker"
    assert usage["Projector B"] == "Available"
    bookings = client.get("/locker/bookings", auth=STAFF).text
    assert "Completed<strong>2</strong>" in bookings
    assert client.get("/locker", auth=BORROWER_A).status_code == 200


def test_presentation_sequence_runs_on_the_seed(booking_app):
    client, _ = booking_app
    start_presentation(client)
    offer = client.post("/reservation-offers", auth=BORROWER_A, json={
        "category": "raspberry_pi_kit", "pickup_at": "2026-11-07T11:01", "duration_minutes": 60,
    }).json()
    assert offer["asset_id"] == "raspberry-pi-kit"
    kit = client.post(f"/reservation-offers/{offer['id']}/confirm", auth=BORROWER_A).json()["id"]
    assert load(client, kit).json()["compartment"] == "a3"
    assert unlock(client, kit, code_for(client, kit)).status_code == 200
    assert pick_up(client, kit).status_code == 200

    proposal = client.get("/recovery", auth=STAFF).json()["substitution_proposals"][0]
    assert proposal["substitute_asset_id"] == "projector-b"
    approved = client.post("/recovery/substitution-proposals/next-projector/approve", auth=STAFF,
                           json={"proposal_id": proposal["id"]})
    assert approved.json()["reservation"]["asset_id"] == "projector-b"

    assert return_request(client, "raspberry-pi-kit").status_code == 200
    assert return_unlock(client, "raspberry-pi-kit", return_code_for(client, "raspberry-pi-kit")).status_code == 200
    assert return_drop(client, "raspberry-pi-kit").status_code == 200
    assert verify(client, "raspberry-pi-kit").status_code == 200
    assert verify(client, "projector-c").status_code == 200  # the seeded return can be checked too
