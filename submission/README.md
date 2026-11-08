# Submission

Everything we hand in for the **APU Cloud Innovation Hackathon 2026**.
**Track 1 — Smart Campus & Student Experience** (equipment lending self-service + overdue recovery).

This file is the checklist so nothing is missed. It follows the official judging criteria.

> **Honesty rule (required):** label every feature as **live / simulated / mocked / planned**.
> Remove access keys and private user data from anything shared.

---

## Entry gates — must be met (pass/fail, no marks, but miss one and the round is lost)

- [ ] **Gemini used** — the borrower booking chat uses the Gemini API. Write one line on how it helped.
- [ ] **Antigravity used** — use Google Antigravity (the agentic IDE) for a real piece of the build, and write one line on how it helped. ⚠️ **Confirm this is actually done.**
- [ ] **Agentic workflow shown** — show the model choosing tools; name the fixed rules and the human-approval points.
- [ ] **Honest evidence** — live/simulated/mocked/planned labels present; no keys or private data in shared work.

---

## Required deliverables (preliminary round)

| # | Item | Rule | Where it goes |
| --- | --- | --- | --- |
| 1 | [ ] **Project details** | Title, track, summary (≥50 chars) | this README + the submission form |
| 2 | [ ] **Preliminary video** | Openable link, **max 10 min** | `submission/video-script.md` → recorded link |
| 3 | [ ] **Pitch deck** | **PDF, ≤10 MB** | `submission/deck.pdf` (+ source) |
| 4 | [ ] **Architecture diagram** | Inputs → model → tools → data → actions → outputs | `submission/architecture.png` |
| 5 | [ ] **Prompts + run log** | The prompts used, their context, and ONE log linking one input → tool actions → final result | `submission/run-log.md` |
| 6 | [ ] **Output checks** | 3 cases — normal, hard, missing-data/failure — each with *expected vs actual vs gap* | `submission/output-checks.md` |
| 7 | [ ] **Prototype + repo + setup** | Demo access, public HTTPS GitHub link, setup steps | live Vercel URL + this repo + [README](../README.md) |
| 8 | [ ] **Gemini + Antigravity statement** | One short paragraph on how each tool contributed | `submission/tools-statement.md` |

The three we most often forget are **4 (diagram), 5 (run log), 6 (output checks)** — they are required *and* they carry the agent-related marks. Build them.

---

## Pitch deck — what each slide must contain

Keep the deck light (~2 min of talking); the demo/video is the proof. Target ~8 slides.

1. [ ] **Title** — project name, tagline, Track 1, team members, live URL.
2. [ ] **Problem** — who feels the pain (students + equipment staff) + **one baseline number** (loans/week, hours spent chasing returns).
3. [ ] **Solution** — one screen of the product; 3 bullets (book by chat · confirm + pickup code · auto-recovery). Mark live vs simulated.
4. [ ] **Architecture** *(biggest-weighted area)* — the diagram, with the **human-approval stop lines** and **fixed rules** (codes never reach the model; Confirm is a button, not a tool) marked.
5. [ ] **Agent & prompting** *(biggest-weighted area)* — the tools the model can call, the system-prompt intent, and **how outputs are checked**.
6. [ ] **Output checks** — the normal / hard / missing-data table from deliverable 6.
7. [ ] **Business value + adoption** — who benefits + how much, running cost (free Flash tier), who maintains it; roadmap in 2 bullets.
8. [ ] **Gemini + Antigravity + closing** — the tools statement and a one-line wrap.

> The two biggest-weighted criteria are **agentic workflow** and **prompting & orchestration** — slides 4 and 5 plus the demo must serve them. Do not let UI polish (a small-weighted criterion) eat the time.

---

## Demo must show (live proof — this is where most marks are)

- [ ] The **model deciding** which tool to call (narrate it).
- [ ] A **happy-path booking** end to end, ending with the **Confirm button** (human approval).
- [ ] A **hard case** — nothing available → substitution proposed, staff approves.
- [ ] An **error recovery** — bad input (e.g. invalid time) → the assistant asks again.
- [ ] A **missing-data / failure case** — e.g. no API key → graceful fallback, app still works.
- [ ] For the in-person final: rehearse with a **changed input** (judges may change inputs within our stated scope).

---

## Where material already lives (reuse, do not rewrite)

- Problem & status: [`README.md`](../README.md)
- Architecture, lending rules & connector: [`docs/DEVELOPMENT.md`](../docs/DEVELOPMENT.md)
- Demo sequence: [`docs/DEMO_GUIDE.md`](../docs/DEMO_GUIDE.md)
- Live deployment, cron & release evidence: [`docs/OPERATIONS.md`](../docs/OPERATIONS.md)
- Stages & ownership: [`docs/BUILD_STAGES.md`](../docs/BUILD_STAGES.md)
- Interim Gemini chat decision: [`docs/adr/0001-interim-gemini-api-chat.md`](../docs/adr/0001-interim-gemini-api-chat.md)

## Status

The borrower booking assistant (Gemini API) is built and merged. Gemini Enterprise is an
**optional upgrade** (organiser-provided access, no personal paid upgrade required) — the
MCP connector already exposes the same tools, so the Enterprise agent is a drop-in later.
The prelim does not depend on it. Fill the deliverable files above, then record the deck and video.
