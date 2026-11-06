# Target architecture

This is the plan we are building toward for the hackathon. It explains what each part does and who builds it. The local coded prototype in this repo is the **engine**; the submission is a **Gemini Enterprise** agent that uses that engine.

## Why this shape

The hackathon requires the solution to be built in **Gemini Enterprise** (a no-code agent platform). Gemini Enterprise gives us the **chat interface and the agent** for free — we do not build the chat screen. What we build is the data and logic behind it, plus the staff locker page.

We keep our **FastAPI + Firestore** backend (Stages 1.1–1.3) and connect it to the agent as an **MCP connector**. We chose this over putting the data in a Google Sheet because a Sheet has no transactions, and our booking rules need them (for example, only one borrower can win the last unit). Firestore gives us that; a Sheet does not.

## Diagram

```text
┌──────────────── GEMINI ENTERPRISE (no-code, mandatory) ────────────────┐
│                                                                        │
│  Chat interface ─► Borrower chat agent     Maximizing workflow (daily) │
│  (provided by GE)  "I need a projector"     overdue check → at-risk    │
│                                             booking → draft staff mail │
│          │                  │                        │                 │
│          └──────────────────┴──── MCP connector ─────┘                 │
└───────────────────────────────────│────────────────────────────────────┘
                                     │  tools: find/book, pickup, return, list-overdue
                    ┌────────────────▼─────────────────┐
                    │  Backend — FastAPI + MCP server   │  ◄── we build/own (Cloud Run)
                    │  reservations / pickups / returns │
                    └────────────────┬─────────────────┘
                                     │
                    ┌────────────────▼─────────────────┐
                    │  Cloud Firestore (source of truth)│  ◄── real database
                    └────────────────┬─────────────────┘
                                     │
                    ┌────────────────▼─────────────────┐
                    │  Staff locker page (/locker)      │  ◄── we build (already have it)
                    │  loading · codes · pickup · return│
                    └──────────────────────────────────┘
```

## Who builds what

| Piece | Built where | Status |
| --- | --- | --- |
| Chat interface + borrower agent | Gemini Enterprise (no-code) | To build — needs the licence |
| Maximizing overdue workflow | Gemini Enterprise (no-code) | To build — local recovery logic is ready; needs the licence |
| MCP connector (thin wrapper over the backend) | Our FastAPI, Python MCP SDK | Built locally with stdio, HTTP, seeding, and a container; hosted integration pending |
| Backend logic and data | FastAPI + Firestore | Built locally through Stage 1.4 and Stage 2.1 (PR #10) |
| Staff locker page | Our web UI (`/locker`) | Built |
| Hosting | Cloud Run + Cloud Firestore | Google credits expected to cover it |
| Staff email (optional) | Gmail 1P connector | Easy to add later |

## One source of truth

The Gemini chat and the locker page read and write the **same Firestore**. A booking made in chat shows up on the staff locker page, and a staff action shows up for the borrower. This matches the build plan's rule that the chat and locker display must match the persisted records.

## What is left to build

- **Hosted identity and access** — bind MCP callers to trusted identities and roles. The local connector currently trusts borrower IDs supplied by callers.
- **Deploy** the backend to Cloud Run and wire the MCP connector into Gemini Enterprise (the fiddly part is the connector auth: client ID, secret, redirect URL).
- **Gemini Enterprise build** — the chat agent and the workflow. Blocked until the licence is distributed.

## Connector terms (quick reference)

- **Connector** — the pipe from the Gemini agent to our data or tools.
- **1P (first party)** — Google's own services: Sheets, Drive, Gmail, Calendar. Easy, no code.
- **3P (third party)** — everything else, including our own backend via **MCP**. No "2P" exists.
- **MCP** — the way our custom backend plugs in as a 3P connector.

See [BUILD_STAGES.md](BUILD_STAGES.md) for the stage roadmap and [adr/0001-return-uses-locker-drop-off.md](adr/0001-return-uses-locker-drop-off.md) for an earlier design decision.
