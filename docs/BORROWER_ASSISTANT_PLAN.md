# Borrower assistant plan

The borrower assistant is a Gemini-API chat that books equipment in plain language.
It is the interim stand-in for the Gemini Enterprise borrower agent; see
[ADR 0001](adr/0001-interim-gemini-api-chat.md) for why it exists, and
[GLOSSARY.md](../GLOSSARY.md) for *offer* vs *reservation* vs *loan*.

This document is the build spec. Nothing here is implemented yet.

## Settled decisions

- **Model:** free Gemini **Flash** tier (confirm the exact id in AI Studio when wiring).
- **Scope:** exactly four capabilities, matching the Enterprise borrower chat — no more.
- **Transaction safety:** the model proposes an offer; the **borrower clicks Confirm**,
  which calls the confirm endpoint directly. The model never commits a reservation.
- **Identity:** the signed-in session (`borrower_id = actor.username`), never a parameter.
- **Email:** not involved — the assistant only books. (Recovery email stays simulated elsewhere.)
- **State:** stateless server; the browser sends the message history each turn.
- **Key & failure:** `GEMINI_API_KEY` is a server-side env var; on API error or rate-limit
  the chat shows a graceful message pointing to `/docs` (the deterministic fallback).
- **Tools run in-process:** the backend calls the domain classes directly, as the MCP server does.
- **Placement:** its own page (`/assistant`), separate from the locker page; top-bar nav links the two.

## The four capabilities

| Name | Driven by | Maps to | Reads/Writes |
| --- | --- | --- | --- |
| `find_equipment` | LLM function call | `Reservations.offer(actor.username, req)` | Writes an offer |
| `confirm_booking` | **Confirm button** (not the LLM) | `Reservations.confirm(actor.username, offer_id)` | Writes a reservation |
| `check_pickup_status` | LLM function call | `Pickups.borrower_page(actor.username)` | Read only |
| `check_return_status` | LLM function call | `Returns.borrower_page(actor.username)` | Read only |

`confirm_booking` is a real capability of the agent, but in this prototype it is wired
to the Confirm button for safety (deterministic, human-in-the-loop). In Enterprise it
becomes an ordinary agent tool; the instruction "confirm only after the borrower agrees"
covers it there. Everything else is identical.

### `find_equipment` parameters (from the real `ReservationRequest`)

- `category` — **required**, one of `projector`, `raspberry_pi_kit`. No others.
- `pickup_at` — **required**, full date and time to the minute, e.g. `2026-11-07T14:00`
  (interpreted as Malaysia time).
- `due_at` **or** `duration_minutes` — **exactly one** (XOR). `due_at` same format as
  `pickup_at`; `duration_minutes` a positive integer.
- `require_hdmi`, `require_built_in_speakers` — optional booleans, **projectors only**
  (the backend rejects them for a Pi kit).

The offer returned has: `id`, `asset_id`, `category`, `pickup_location`, `pickup_at`,
`due_at`, `require_hdmi`, `require_built_in_speakers` (all times are Malaysia-time strings).

## System prompt (draft — adapt from `booking_instructions`)

```
You are the Campus Asset Concierge booking assistant for the signed-in borrower.
The current reference time is {current_time} (Malaysia time); use it for relative dates.

Help the borrower reserve exactly ONE item.
- Equipment categories are only: projector, raspberry_pi_kit.
- Ask for a missing pickup time, and a return time OR a loan duration — never both.
- Interpret all times in Malaysia time. Use full date and time to the minute.
  Resolve relative dates ("today", "2pm") against the reference time; if the date is
  unclear, ask for it.
- HDMI and built-in-speaker needs apply to projectors only. Capture them only when
  the borrower mentions them; never ask about them for a Raspberry Pi kit.
- Call find_equipment once you have a category, a pickup time, and either a return
  time or a duration.
- When an offer comes back, show the asset, location, pickup time, return time, and
  requirements (or "No extra requirements"), then ask the borrower to confirm using
  the Confirm button. Do not claim the booking is done yourself.
- For "where/when do I pick up?" or "is my return checked in?", use
  check_pickup_status / check_return_status.
- Codes, unlocking, pickup, and drop-off happen on the My Locker page, not in chat.
  Never invent or reveal a one-time code.
If a tool returns an error, explain it plainly and offer to try again.
```

## Request / response flow

1. Browser POSTs `{ messages: [...] }` to `POST /assistant/chat` (session-authed, borrower only).
2. Server prepends the system prompt (with the current test clock) and calls Gemini Flash
   with the four function declarations.
3. If Gemini calls `find_equipment` / `check_*`, the server runs the matching domain call
   **in-process**, feeds the result back, and gets Gemini's reply.
4. Server returns the assistant text plus, if an offer was produced, the offer object.
5. The page renders the offer as a card with a **Confirm booking** button.
6. Confirm button POSTs directly to `/reservation-offers/{id}/confirm`, then links to My Locker.

All within Vercel's 60s request cap — Flash calls are ~1–2s, so a call → tool → call round
trip fits comfortably.

## Files to add / change

**New**
- `src/campus_asset_concierge/assistant.py` — builds the four function declarations,
  runs the Gemini call + tool-dispatch loop, maps each tool to the domain classes.
- `templates/locker_assistant.html` — the chat page (borrower shell, reuses the top bar).
- `static/locker_assistant.css` — chat styling, matching the borrower design tokens.
- `static/locker_assistant.js` — holds message history client-side, posts to `/assistant/chat`,
  renders messages and the offer card + Confirm button.
- `tests/test_assistant.py` — tool dispatch, auth (borrower-only), error handling, with the
  Gemini client **mocked** (no real API in CI).

**Changed**
- `api/app.py` — add `GET /assistant` (render page, borrower only) and
  `POST /assistant/chat` (the orchestration endpoint); both behind `signed_in`.
- `templates/locker.html` — add a top-bar nav link between My Locker and Assistant.
- `pyproject.toml` — add the Gemini SDK (`google-genai`) dependency; refresh the lock.

`GEMINI_API_KEY` is read from the environment at request time (set it as a Vercel
sensitive env var for the demo; local dev reads it from `.env`). `GEMINI_MODEL`
overrides the model id (default `gemini-3.8-flash`, the current free full Flash — confirm
it is listed in AI Studio; switching is one line). **If the key is absent the chat degrades to a friendly fallback rather than
failing startup**, so a missing key never takes down the locker or the rest of the app.

**Untouched**: all booking/recovery/locker domain logic (reused, not duplicated),
the MCP connector, the staff UI, the Firestore layer.

## Testing

- Unit-test `assistant.py` tool dispatch by **mocking the Gemini client** to emit a scripted
  function call, then assert it calls `Reservations.offer` with the parsed args and returns
  the offer. Never call the real API in tests (CI has no key, and tests stay on the emulator).
- Test `POST /assistant/chat` rejects staff/operator and unauthenticated callers.
- Test the graceful path: missing key / simulated API error returns a clean fallback, not a 500.
- Keep the existing booking tests as the proof the underlying flow works end to end.

## Deliberately out of scope

- Real email (simulated elsewhere; Enterprise Gmail connector later).
- Any chat power beyond the four capabilities (pickup/unlock/recovery stay off the assistant).
- Persisting chat history server-side.
- A standalone booking form (`/docs` is the deterministic fallback).

## Port to Gemini Enterprise

The system prompt and the four tool definitions move almost unchanged into the Enterprise
borrower agent; the tools point at the MCP connector instead of in-process calls. This chat
then remains as the no-licence fallback. See the Gemini/Gmail assembly in
[DEMO_GUIDE.md](DEMO_GUIDE.md).
