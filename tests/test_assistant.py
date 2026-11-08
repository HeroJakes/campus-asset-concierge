"""Tests for the borrower booking assistant.

The Gemini client is always mocked: CI has no API key and must never call the real
service. Pure loop/dispatch tests run without the emulator; endpoint tests use it.
"""

import pytest
from types import SimpleNamespace
from unittest.mock import Mock

from conftest import BORROWER_A, OPERATOR, STAFF
from campus_asset_concierge import assistant
from test_pickups import book, load
from test_returns import return_request


def scripted(script):
    """A fake `generate(transcript)` that returns each scripted reply in turn."""
    replies = iter(script)

    def generate(_transcript):
        return next(replies)

    return generate


def fake_gemini(script):
    """Stand in for assistant.gemini_generate, ignoring key/model/time."""
    def factory(_api_key, _model, _current_time):
        return scripted(script)

    return factory


FIND_PI = {
    "name": "find_equipment",
    "args": {"category": "raspberry_pi_kit", "pickup_at": "2026-11-07T10:30", "duration_minutes": 60},
}


# --- pure control-flow (no store, no app) ---

def test_run_assistant_dispatches_tool_then_captures_offer():
    seen = []

    def dispatch(name, args):
        seen.append((name, args))
        return {"id": "offer-1", "asset_id": "raspberry-pi-kit"} if name == "find_equipment" else {}

    result = assistant.run_assistant(
        scripted([
            {"text": None, "calls": [FIND_PI]},
            {"text": "Here is your Raspberry Pi kit. Confirm to book.", "calls": []},
        ]),
        [{"role": "user", "text": "pi kit at 10:30 for an hour"}],
        dispatch,
    )
    assert result["offer"] == {"id": "offer-1", "asset_id": "raspberry-pi-kit"}
    assert "Confirm" in result["reply"]
    assert seen[0][0] == "find_equipment"


def test_run_assistant_does_not_capture_offer_on_tool_error():
    result = assistant.run_assistant(
        scripted([
            {"text": None, "calls": [FIND_PI]},
            {"text": "That didn't work, want to try again?", "calls": []},
        ]),
        [{"role": "user", "text": "book it"}],
        lambda name, args: {"error": "No eligible unit is available for that window."},
    )
    assert result["offer"] is None
    assert "again" in result["reply"].lower()


def test_run_assistant_stops_at_max_hops():
    result = assistant.run_assistant(
        scripted([{"text": None, "calls": [FIND_PI]}] * 10),
        [{"role": "user", "text": "x"}],
        lambda name, args: {"error": "nope"},
        max_hops=3,
    )
    assert "try again" in result["reply"].lower()
    assert result["offer"] is None


def test_dispatch_rejects_unknown_tool():
    dispatch = assistant.make_dispatch(None, None, None, "borrower-a")
    assert "error" in dispatch("mystery_tool", {})


def test_clean_find_args_coerces_floats_and_drops_nulls():
    cleaned = assistant._clean_find_args({"duration_minutes": 60.0, "due_at": None, "category": "projector"})
    assert cleaned["duration_minutes"] == 60
    assert "due_at" not in cleaned


def test_sdk_round_trip_preserves_model_parts_and_groups_parallel_tool_results(monkeypatch):
    from google import genai
    from google.genai import types

    content = types.Content(role="model", parts=[
        types.Part(function_call=types.FunctionCall(name="check_pickup_status", args={}, id="pickup"),
                   thought_signature=b"test-signature"),
        types.Part(function_call=types.FunctionCall(name="check_return_status", args={}, id="return")),
    ])
    generate = Mock(side_effect=[
        types.GenerateContentResponse(candidates=[types.Candidate(content=content)]),
        types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
            role="model", parts=[types.Part(text="Your status is ready.")],
        ))]),
    ])
    client = Mock(return_value=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    monkeypatch.setattr(genai, "Client", client)
    monkeypatch.setattr(assistant, "monotonic", Mock(side_effect=[100, 101, 111]))
    result = assistant.run_assistant(
        assistant.gemini_generate("test-key", "test-model", "2026-11-07T11:01:00+08:00"),
        [{"role": "user", "text": "Check both statuses"}],
        lambda name, args: {"status": "ready"},
    )
    assert result["reply"] == "Your status is ready."
    sent = generate.call_args_list[1].kwargs["contents"]
    assert [item.role for item in sent] == ["user", "model", "user"]
    assert sent[1] is content
    assert sent[1].parts[0].thought_signature == b"test-signature"
    assert [part.function_response.id for part in sent[2].parts] == ["pickup", "return"]
    assert client.call_args.kwargs["http_options"].timeout == 45000
    assert client.call_args.kwargs["http_options"].retry_options.attempts == 1
    assert [call.kwargs["config"].http_options.timeout for call in generate.call_args_list] == [44000, 34000]
    assert generate.call_args.kwargs["config"].thinking_config.thinking_level == types.ThinkingLevel.LOW


# --- endpoint tests (mock Gemini, real dispatch against the emulator) ---

def chat(client, messages, auth=BORROWER_A):
    return client.post("/assistant/chat", auth=auth, json={"messages": messages})


def test_chat_books_through_find_equipment_and_returns_an_offer(booking_app, monkeypatch):
    client, _ = booking_app
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(assistant, "gemini_generate", fake_gemini([
        {"text": None, "calls": [FIND_PI]},
        {"text": "Here is your Raspberry Pi kit offer. Confirm to book.", "calls": []},
    ]))
    response = chat(client, [{"role": "user", "text": "a pi kit at 10:30 for an hour"}])
    assert response.status_code == 200, response.text
    body = response.json()
    assert "Confirm to book" in body["reply"]
    assert body["offer"]["category"] == "raspberry_pi_kit"
    assert body["offer"]["id"]
    # The offer is confirmable through the existing endpoint (human-driven, not the model).
    confirmed = client.post(f"/reservation-offers/{body['offer']['id']}/confirm", auth=BORROWER_A)
    assert confirmed.status_code == 200, confirmed.text


def test_chat_surfaces_a_tool_error_without_an_offer(booking_app, monkeypatch):
    client, _ = booking_app
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    # HDMI on a Pi kit is rejected by the domain validator -> dispatch returns an error.
    bad = {"name": "find_equipment", "args": {"category": "raspberry_pi_kit", "pickup_at": "2026-11-07T10:30",
                                              "duration_minutes": 60, "require_hdmi": True}}
    monkeypatch.setattr(assistant, "gemini_generate", fake_gemini([
        {"text": None, "calls": [bad]},
        {"text": "HDMI applies to projectors only. Want a projector instead?", "calls": []},
    ]))
    body = chat(client, [{"role": "user", "text": "pi kit with hdmi"}]).json()
    assert body["offer"] is None
    assert "projector" in body["reply"].lower()


def test_chat_status_query_returns_reply_without_offer(booking_app, monkeypatch):
    client, _ = booking_app
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(assistant, "gemini_generate", fake_gemini([
        {"text": None, "calls": [{"name": "check_pickup_status", "args": {}}]},
        {"text": "You have nothing to collect yet.", "calls": []},
    ]))
    body = chat(client, [{"role": "user", "text": "where do I pick up?"}]).json()
    assert body["offer"] is None
    assert "collect" in body["reply"].lower()


@pytest.mark.parametrize("kind", ["pickup", "return"])
def test_status_codes_stay_in_borrower_api_and_out_of_model_transcript(booking_app, monkeypatch, kind):
    client, _ = booking_app
    if kind == "pickup":
        reservation = book(client, category="raspberry_pi_kit")
        assert load(client, reservation).status_code == 200
    else:
        assert return_request(client).status_code == 200
    # Email is not connected: the authenticated borrower API remains the demo stand-in.
    before = client.get(f"/{kind}s", auth=BORROWER_A).json()
    assert before and all("code" in record for record in before)
    model_results = []

    def factory(_api_key, _model, _current_time):
        def generate(transcript):
            if transcript[-1]["role"] == "user":
                return {"calls": [{"name": f"check_{kind}_status", "args": {}}]}
            response = transcript[-1]["response"]
            model_results.append(response)
            records = response[f"{kind}s"]
            assert records
            assert all("code" not in record for record in records)
            assert [(r["asset_id"], r["step"]) for r in records] == [
                (r["asset_id"], r["step"]) for r in before
            ]
            return {"text": "Here is your current status.", "calls": []}
        return generate

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(assistant, "gemini_generate", factory)
    result = chat(client, [{"role": "user", "text": "Check my status"}])
    assert result.status_code == 200
    assert result.json() == {"reply": "Here is your current status.", "offer": None}
    assert len(model_results) == 1
    assert client.get(f"/{kind}s", auth=BORROWER_A).json() == before


def test_chat_falls_back_gracefully_when_key_is_missing(booking_app, monkeypatch):
    client, _ = booking_app
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = chat(client, [{"role": "user", "text": "hi"}])
    assert response.status_code == 200
    assert response.json() == {"reply": assistant.FALLBACK_REPLY, "offer": None}


def test_chat_falls_back_when_the_model_call_raises(booking_app, monkeypatch):
    client, _ = booking_app
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def boom(_api_key, _model, _current_time):
        def generate(_transcript):
            raise RuntimeError("gemini down")
        return generate

    monkeypatch.setattr(assistant, "gemini_generate", boom)
    assert chat(client, [{"role": "user", "text": "hi"}]).json()["reply"] == assistant.FALLBACK_REPLY


@pytest.mark.parametrize("auth,status", [(STAFF, 403), (OPERATOR, 403), (None, 401)])
def test_chat_is_borrower_only(booking_app, auth, status):
    client, _ = booking_app
    kwargs = {"json": {"messages": [{"role": "user", "text": "hi"}]}}
    if auth:
        kwargs["auth"] = auth
    assert client.post("/assistant/chat", **kwargs).status_code == status


def test_assistant_page_renders_for_borrower_only(booking_app):
    client, _ = booking_app
    page = client.get("/assistant", auth=BORROWER_A)
    assert page.status_code == 200
    assert "Assistant" in page.text
    assert "/static/locker_assistant.js" in page.text
    assert 'href="/locker"' in page.text  # nav back to My Locker
    for text in ('AI Assistant', 'Quick actions', 'Check my pickups', 'Check my returns',
                 'Tips for a quick booking', 'aria-label="Send message"'):
        assert text in page.text
    assert 'Change or Cancel' not in page.text
    assert 'sent to your university email' not in page.text
    assert client.get("/assistant", auth=STAFF).status_code == 403
    assert client.get("/static/locker_assistant.css").status_code == 200


def test_chat_rejects_empty_and_oversized_histories(booking_app):
    client, _ = booking_app
    assert client.post("/assistant/chat", auth=BORROWER_A, json={"messages": []}).status_code == 422
    big = [{"role": "user", "text": "x"}] * 41
    assert client.post("/assistant/chat", auth=BORROWER_A, json={"messages": big}).status_code == 422
