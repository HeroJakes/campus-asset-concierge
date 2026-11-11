import pytest

from conftest import BORROWER_A, BORROWER_B, STAFF
from test_pickups import advance, book, code_for, load, pick_up, unlock, wrong_code_for
from test_returns import code_for as return_code_for
from test_returns import return_drop, return_request, return_unlock, verify


def page(client, account=BORROWER_A):
    response = client.get('/locker', auth=account)
    assert response.status_code == 200
    return response.text


def test_borrower_pickup_cards_follow_the_real_workflow(booking_app):
    client, _ = booking_app
    reservation = book(client, category='raspberry_pi_kit')
    html = page(client)
    assert 'My Locker' in html and 'My pickups <span>(1)</span>' in html
    assert 'Waiting for loading' in html and 'Compartment not assigned yet' in html
    assert 'Campus Loan Desk' in html
    assert 'disabled>Collect' in html
    assert load(client, reservation).status_code == 200
    assert 'Code not active yet' in page(client)
    assert 'Opens at 10:30' in page(client)
    advance(client, 30)
    code = code_for(client, reservation)
    html = page(client)
    assert 'Enter your pickup code' in html
    assert 'pattern="[0-9]{6}"' in html and 'autocomplete="one-time-code"' in html
    assert 'Pickup code for Raspberry Pi Kit (six digits)' in html
    assert code not in html
    assert reservation not in page(client, BORROWER_B)
    assert unlock(client, reservation, code).status_code == 200
    assert 'Compartment A1 is open' in page(client)
    assert 'Confirm pickup' in page(client)
    assert pick_up(client, reservation).status_code == 200
    assert 'Collected' in page(client) and 'On loan' in page(client)
    assert return_request(client, 'raspberry-pi-kit').status_code == 200
    assert return_unlock(client, 'raspberry-pi-kit', return_code_for(client, 'raspberry-pi-kit')).status_code == 200
    assert return_drop(client, 'raspberry-pi-kit').status_code == 200
    assert verify(client, 'raspberry-pi-kit').status_code == 200
    html = page(client)
    assert 'Returned</span>' in html and 'On loan' not in html


def test_borrower_return_cards_follow_the_real_workflow(booking_app):
    client, _ = booking_app
    assert 'Ready to return' in page(client)
    assert return_request(client).status_code == 200
    code = return_code_for(client)
    html = page(client)
    assert 'Enter your return code' in html
    assert 'Return code for Projector A (six digits)' in html
    assert code not in html
    assert '/assets/projector-a/return-unlock' in html
    assert return_unlock(client, 'projector-a', code).status_code == 200
    assert 'Compartment A1 is open' in page(client)
    assert 'Confirm drop-off' in page(client)
    assert return_drop(client).status_code == 200
    assert 'Waiting for staff check' in page(client)
    assert verify(client).status_code == 200
    assert 'Nothing to return right now' in page(client)


@pytest.mark.parametrize('blocked', [False, True])
def test_unusable_codes_show_recovery_instructions(booking_app, blocked):
    client, _ = booking_app
    reservation = book(client)
    load(client, reservation)
    advance(client, 30)
    code = code_for(client, reservation)
    if blocked:
        for _ in range(5):
            assert unlock(client, reservation, wrong_code_for(code)).status_code == 403
    else:
        advance(client, 31)
    html = page(client)
    assert ('Pickup code blocked' if blocked else 'Pickup code expired') in html
    assert 'Contact staff' in html
    assert f'data-unlock="/reservations/{reservation}/unlock"' not in html


def test_borrower_styles_and_empty_states_do_not_change_staff(booking_app):
    client, _ = booking_app
    html = page(client)
    assert 'no bookings to collect' in html
    assert '/static/locker_borrower.css' in html
    staff = page(client, STAFF)
    assert '/static/locker_borrower.css' not in staff
    assert 'Staff navigation' in staff
    assert client.get('/static/locker_borrower.css').status_code == 200
    assert client.get('/static/locker_borrower.js').status_code == 200


@pytest.mark.parametrize('blocked', [False, True])
def test_unusable_return_codes_offer_the_right_next_action(booking_app, blocked):
    client, _ = booking_app
    return_request(client)
    if blocked:
        for _ in range(5):
            assert return_unlock(client, 'projector-a', 'not-a-code').status_code == 403
    else:
        advance(client, 31)
    html = page(client)
    if blocked:
        assert 'Return code blocked' in html and 'Contact staff' in html
    else:
        assert 'Return code expired' in html and 'Request a new code' in html
        assert 'Compartment not assigned yet' in html
    assert 'data-unlock="/assets/projector-a/return-unlock"' not in html
