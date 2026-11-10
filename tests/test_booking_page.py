import pytest

from conftest import BORROWER_A, BORROWER_B, OPERATOR, STAFF
from test_pickups import advance, book, code_for, load, pick_up, unlock
from test_returns import code_for as return_code_for
from test_returns import return_drop, return_request, return_unlock, verify


def page(client, **params):
    response = client.get("/locker/bookings", auth=STAFF, params=params)
    assert response.status_code == 200
    return response.text


def row(reservation_id):
    return f'data-booking-id="{reservation_id}"'


def test_bookings_page_is_staff_only(booking_app):
    client, _ = booking_app
    assert client.get("/locker/bookings", follow_redirects=False).headers["location"] == "/login"
    for account in (BORROWER_A, BORROWER_B, OPERATOR):
        assert client.get("/locker/bookings", auth=account).status_code == 403
    assert 'href="/locker/bookings"' in client.get("/locker", auth=STAFF).text
    assert client.get("/static/locker_bookings.css").status_code == 200


def test_search_filters_and_counts_follow_saved_bookings(booking_app):
    client, _ = booking_app
    reservation_id = book(client)
    assert row(reservation_id) in page(client, status="to_load")
    assert row(reservation_id) not in page(client, status="active")
    assert load(client, reservation_id).status_code == 200
    html = page(client, status="active", q="PROJECTOR B")
    assert row(reservation_id) in html
    assert row("next-projector") not in html
    assert "Loaded &amp; locked" in html
    assert "All bookings<strong>3</strong>" in html
    assert "To load<strong>1</strong>" in html
    assert "Active<strong>2</strong>" in html
    assert "Completed<strong>0</strong>" in html
    assert row(reservation_id) in page(client, q=reservation_id)
    assert row(reservation_id) in page(client, q="borrower a")
    assert "No bookings match your search" in page(client, q="no such item")
    assert client.get("/locker/bookings?status=unknown", auth=STAFF).status_code == 422
    html = page(client, q='<script>alert("x")</script>')
    assert '<script>alert("x")</script>' not in html


@pytest.mark.parametrize("result", ["pass", "fail"])
def test_completed_requires_return_check_not_just_collection(booking_app, result):
    client, _ = booking_app
    reservation_id = book(client)
    assert load(client, reservation_id).status_code == 200
    advance(client, 30)
    code = code_for(client, reservation_id)
    assert unlock(client, reservation_id, code).status_code == 200
    assert pick_up(client, reservation_id).status_code == 200
    assert row(reservation_id) in page(client, status="active")
    assert row(reservation_id) not in page(client, status="completed")
    assert code not in page(client)
    asset_id = "projector-b"
    assert return_request(client, asset_id).status_code == 200
    return_code = return_code_for(client, asset_id)
    assert return_unlock(client, asset_id, return_code).status_code == 200
    assert return_drop(client, asset_id).status_code == 200
    assert row(reservation_id) not in page(client, status="completed")
    active = page(client, status="active")  # bookings page offers the staff return check directly
    assert f'data-open-dialog="return-{asset_id}"' in active
    assert f'/assets/{asset_id}/verify-return' in active
    assert verify(client, asset_id, result=result).status_code == 200
    html = page(client, status="completed")
    assert row(reservation_id) in html
    assert "Returned &amp; checked" in html
    assert row(reservation_id) not in page(client, status="active")


def test_recovery_review_uses_existing_guarded_approval(booking_app):
    client, _ = booking_app
    advance(client, 61)
    proposal = client.get("/recovery", auth=STAFF).json()["substitution_proposals"][0]
    html = page(client)
    assert f'data-open-dialog="proposal-{proposal["id"]}"' in html
    assert f'/recovery/substitution-proposals/{proposal["reservation_id"]}/approve' in html
    assert proposal["id"] in html
    assert "Approve and apply" in html
    assert "Review proposal" in html


def test_loan_without_reservation_stays_active_until_staff_checks_return(booking_app):
    client, _ = booking_app
    assert row("active-projector") in page(client, status="active")
    assert "Collected" in page(client, status="active")
    advance(client, 61)
    assert "Overdue" in page(client, status="active")
    assert return_request(client, "projector-a").status_code == 200
    staff = client.get("/locker", auth=STAFF).text
    assert "Reserved for return — awaiting code" in staff
    assert "Returned, awaiting check" not in staff
    assert return_drop(client, "projector-a").status_code == 409
    assert verify(client, "projector-a").status_code == 409
    assert row("active-projector") in page(client, status="active")
    assert return_unlock(client, "projector-a", return_code_for(client, "projector-a")).status_code == 200
    assert return_drop(client, "projector-a").status_code == 200
    assert "Awaiting return check" in page(client, status="active")
    assert verify(client, "projector-a").status_code == 200
    assert row("active-projector") not in page(client, status="active")
    assert row("active-projector") in page(client, status="completed")
