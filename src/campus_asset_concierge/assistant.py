"""Borrower booking assistant backed by the Gemini API.

An interim stand-in for the Gemini Enterprise borrower agent. It exposes the same
booking + status capabilities over the same in-process domain logic the MCP
connector uses. See docs/BORROWER_ASSISTANT_PLAN.md and docs/adr/0001-interim-gemini-api-chat.md.

The Gemini SDK is imported lazily inside ``gemini_generate`` so the rest of the app
(and the tests) never require the package, and a missing key or package degrades to a
friendly fallback instead of breaking the page.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol
from time import monotonic

from pydantic import ValidationError

from campus_asset_concierge.domain.reservations import ReservationError, ReservationRequest

# What the LLM may call. confirm_booking is intentionally NOT here: confirming is a
# deterministic human action (the Confirm button hits the endpoint directly), never the model.
TOOL_DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "find_equipment",
        "description": (
            "Find and hold one available unit matching the borrower's request. "
            "Returns an offer the borrower then confirms with the Confirm button."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["projector", "raspberry_pi_kit"],
                    "description": "The kind of equipment to book.",
                },
                "pickup_at": {
                    "type": "string",
                    "description": "Full date and time to the minute in Malaysia time, e.g. 2026-11-07T14:00.",
                },
                "due_at": {
                    "type": "string",
                    "description": "Return time, same format. Provide this OR duration_minutes, never both.",
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Loan length in minutes. Provide this OR due_at, never both.",
                },
                "require_hdmi": {
                    "type": "boolean",
                    "description": "Projectors only. Omit entirely for a Raspberry Pi kit.",
                },
                "require_built_in_speakers": {
                    "type": "boolean",
                    "description": "Projectors only. Omit entirely for a Raspberry Pi kit.",
                },
            },
            "required": ["category", "pickup_at"],
        },
    },
    {
        "name": "check_pickup_status",
        "description": "List the borrower's current pickups and their states.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "check_return_status",
        "description": "List the borrower's current loans/returns and their states.",
        "parameters": {"type": "object", "properties": {}},
    },
]

SYSTEM_PROMPT = """You are the Campus Asset Concierge booking assistant for the signed-in borrower.
The current reference time is {current_time} (Malaysia time); use it for relative dates.

Help the borrower reserve exactly ONE item.
- Equipment categories are only: projector, raspberry_pi_kit.
- Ask for a missing pickup time, and a return time OR a loan duration - never both.
- Interpret all times in Malaysia time, to the minute (e.g. 2026-11-07T14:00). Resolve
  relative dates against the reference time; if the date is unclear, ask for it.
- HDMI and built-in-speaker needs apply to projectors only. Capture them only when the
  borrower mentions them; never ask about them for a Raspberry Pi kit.
- Call find_equipment once you have a category, a pickup time, and either a return time
  or a duration.
- When an offer comes back, show the asset, location, pickup time, return time, and
  requirements (or "No extra requirements"), then ask the borrower to confirm with the
  Confirm button. Do not claim the booking is done yourself.
- For "where/when do I pick up?" or "is my return checked in?", use check_pickup_status
  or check_return_status.
- Codes, unlocking, pickup, and drop-off happen on the My Locker page, not in chat.
  Never invent or reveal a one-time code.
If a tool returns an error, explain it plainly and offer to try again."""

FALLBACK_REPLY = (
    "The booking assistant is unavailable right now. You can still book through the "
    "API docs at /docs, or try again in a moment."
)

MAX_HOPS = 5


class _Domain(Protocol):
    def offer(self, borrower_id: str, request: ReservationRequest) -> dict: ...


def make_dispatch(reservations, pickups, returns, borrower_id: str) -> Callable[[str, dict], dict]:
    """Return a tool dispatcher bound to one borrower. Pure, fully testable."""

    def dispatch(name: str, args: dict) -> dict:
        try:
            if name == "find_equipment":
                return reservations.offer(borrower_id, ReservationRequest(**_clean_find_args(args)))
            if name == "check_pickup_status":
                return {"pickups": pickups.status(borrower_id)}
            if name == "check_return_status":
                return {"returns": returns.status(borrower_id)}
            return {"error": f"Unknown tool: {name}"}
        except ReservationError as error:
            return {"error": str(error)}
        except (ValidationError, ValueError, TypeError) as error:
            return {"error": str(error)}

    return dispatch


def _clean_find_args(args: dict) -> dict:
    """Coerce LLM-supplied args to what ReservationRequest expects (untrusted input)."""
    cleaned = {k: v for k, v in args.items() if v is not None}
    minutes = cleaned.get("duration_minutes")
    if isinstance(minutes, float) and minutes.is_integer():
        cleaned["duration_minutes"] = int(minutes)
    return cleaned


def run_assistant(
    generate: Callable[[list[dict]], dict],
    transcript: list[dict],
    dispatch: Callable[[str, dict], dict],
    max_hops: int = MAX_HOPS,
) -> dict:
    """Drive the tool-call loop. ``generate(transcript)`` returns {"text", "calls"}.

    Pure control flow: the Gemini SDK lives entirely inside the injected ``generate``.
    """
    offer: dict | None = None
    for _ in range(max_hops):
        reply = generate(transcript)
        calls = reply.get("calls") or []
        if not calls:
            return {"reply": reply.get("text") or "", "offer": offer}
        transcript.append({"role": "model", "calls": calls, "content": reply.get("content")})
        for call in calls:
            result = dispatch(call["name"], call.get("args") or {})
            if call["name"] == "find_equipment" and "error" not in result:
                offer = result
            transcript.append({"role": "tool", "name": call["name"], "id": call.get("id"), "response": result})
    return {"reply": "Sorry, I couldn't finish that - please try again.", "offer": offer}


def respond(
    messages: list[dict],
    *,
    borrower_id: str,
    reservations,
    pickups,
    returns,
    current_time: str,
    api_key: str,
    model: str,
    generate: Callable[[list[dict]], dict] | None = None,
) -> dict:
    """Entry point used by the API route. ``generate`` is injectable for tests."""
    transcript = [{"role": m["role"], "text": m["text"]} for m in messages]
    if generate is None:
        generate = gemini_generate(api_key, model, current_time)
    dispatch = make_dispatch(reservations, pickups, returns, borrower_id)
    return run_assistant(generate, transcript, dispatch)


def gemini_generate(api_key: str, model: str, current_time: str) -> Callable[[list[dict]], dict]:
    """Build the real Gemini call. Imports the SDK lazily so it's optional until used."""
    from google import genai
    from google.genai import types

    # One shared budget leaves time for Firestore and the response within Vercel's cap.
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(
        timeout=45000, retry_options=types.HttpRetryOptions(attempts=1),
    ))
    tools = [types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name=d["name"], description=d["description"], parameters=_schema(types, d["parameters"]),
        )
        for d in TOOL_DECLARATIONS
    ])]
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT.format(current_time=current_time),
        tools=tools,
        thinking_config=types.ThinkingConfig(thinking_level="low"),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    deadline = monotonic() + 45

    def generate(transcript: list[dict]) -> dict:
        remaining = int((deadline - monotonic()) * 1000)
        if remaining <= 0:
            raise TimeoutError("Assistant request timed out.")
        response = client.models.generate_content(
            model=model, contents=_to_contents(types, transcript), config=config.model_copy(update={
                "http_options": types.HttpOptions(
                    timeout=remaining, retry_options=types.HttpRetryOptions(attempts=1),
                ),
            }),
        )
        calls = [
            {"name": fc.name, "args": dict(fc.args or {}), "id": fc.id}
            for fc in (response.function_calls or [])
        ]
        return {"text": response.text if not calls else None, "calls": calls,
                "content": response.candidates[0].content if response.candidates else None}

    return generate


def _schema(types, spec: dict):
    """Convert a plain JSON-schema dict to a google-genai Schema."""
    kwargs: dict[str, Any] = {"type": spec["type"].upper()}
    if "description" in spec:
        kwargs["description"] = spec["description"]
    if "enum" in spec:
        kwargs["enum"] = spec["enum"]
    if spec["type"] == "object":
        kwargs["properties"] = {k: _schema(types, v) for k, v in spec.get("properties", {}).items()}
        if spec.get("required"):
            kwargs["required"] = spec["required"]
    return types.Schema(**kwargs)


def _to_contents(types, transcript: list[dict]) -> list:
    """Convert our internal transcript to google-genai Content objects."""
    contents = []
    for item in transcript:
        role = item["role"]
        if role == "user":
            contents.append(types.Content(role="user", parts=[types.Part(text=item["text"])]))
        elif role == "model" and item.get("calls"):
            if item.get("content") is not None:
                # Preserve the original parts, including Gemini's thought signatures.
                contents.append(item["content"])
                continue
            parts = [
                types.Part(function_call=types.FunctionCall(name=c["name"], args=c.get("args") or {}))
                for c in item["calls"]
            ]
            contents.append(types.Content(role="model", parts=parts))
        elif role == "model":
            contents.append(types.Content(role="model", parts=[types.Part(text=item.get("text") or "")]))
        elif role == "tool":
            part = types.Part(function_response=types.FunctionResponse(
                name=item["name"], response=item["response"], id=item.get("id"),
            ))
            if contents and contents[-1].role == "user" and contents[-1].parts[0].function_response:
                contents[-1].parts.append(part)
            else:
                contents.append(types.Content(role="user", parts=[part]))
    return contents
