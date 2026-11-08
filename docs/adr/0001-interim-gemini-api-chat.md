# Interim Gemini-API assistant alongside the Gemini Enterprise agent

The hackathon encourages a Gemini Enterprise no-code agent, but the trial licence
is delayed and the 13 November prototype does not require it. Booking previously
had no UI at all — the plan was for the Enterprise chat agent to be the booking
interface — so without it a borrower cannot reserve anything in the demo.

We decided to build an **interim borrower assistant** that calls the **Gemini API**
(free Flash tier) directly from our FastAPI backend, as a faithful stand-in for the
Enterprise borrower chat: the **same four capabilities** (`find_equipment`,
`confirm_booking`, `check_pickup_status`, `check_return_status`), the same
instructions, and the **same in-process domain logic** the MCP connector uses. It
is a separate front-end over one backend, not a second backend.

This is recorded because a future reader will see two agent front-ends — this API
chat and the Enterprise agent — and wonder why. The reasons: (1) it unblocks the
prototype's booking flow with no Google-Enterprise dependency; (2) the system
prompt and tool schema port almost directly to the Enterprise agent, so the work is
a head start, not throwaway; (3) it is deliberately capped at Enterprise parity — no
extra chat powers — so the prototype and the eventual final product stay aligned.

When the Enterprise licence arrives, the Enterprise agent is added alongside this
chat (both call the MCP connector). This interim chat stays as the no-licence
fallback and is not removed just because Enterprise works.
