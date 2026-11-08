# Demo fallback plan

The active backend is already hosted on Vercel and uses Firestore. Use the
[deployment runbook](DEPLOYMENT_PLAN.md) for the live URL, credentials, reset, and
scheduled recovery. The obsolete Vercel test project has been removed.

## If Gemini Enterprise access arrives

Follow the [build sheet](GEMINI_BUILD_SHEET.md) to connect the existing MCP endpoint,
build the borrower agent and recovery workflow, and configure Gmail. Reuse the
current host and isolated fictional demo document.

## If the licence does not arrive

Ask the organisers whether a Gemini API and Google ADK demonstration is eligible.
The repo contains an ADK booking agent, but that fallback still needs configuration
against an isolated demo document and an end-to-end rehearsal. Do not treat it as
a completed substitute for the required Gemini Enterprise app.

The locker and lending backend can still demonstrate booking, pickup, return,
substitution approval, and escalation. Label the missing Gemini integration and
simulated email delivery clearly. A pure no-code Gemini Enterprise build also
requires the licence, so it does not solve missing access.

## If the live connection fails during judging

Check `/health`, the configured MCP URL, and the existing Vercel deployment first.
Keep a recorded demonstration ready. A new host or database migration is outside
the current demo plan and needs its own approval and rehearsal. No keep-awake job
is configured for the Vercel deployment.
