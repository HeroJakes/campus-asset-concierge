# Backup plan

This plan covers one case: the organizers give us the **Gemini Enterprise licence** but **no GCP credits or project**.

In that case the mandatory tool (Gemini Enterprise) is covered. The only thing at risk is where our connector and its data live, because Cloud Run and Firestore both need a billing-enabled GCP project. So both backups below remove the GCP dependency.

Key constraint: judges assess the Gemini app from **2026-11-11 to 11-14**, so whatever hosts the connector must stay up on its own through that window.

## Plan A — same architecture, off GCP (primary backup)

Keep the current design. Move it off GCP.

- Host the MCP connector on a **free, no-card platform** (for example Hugging Face Spaces or a Render free web service). Both give a public HTTPS URL, which the Gemini Enterprise 3P connector needs.
- Move the data store to **Supabase free tier**. The organizers approved Supabase, it is free, and it needs no card.

**Upside:** reuses all our coded logic (reservations, overdue recovery, substitution) through the MCP connector. This is the work we already planned, just pointed at a free host instead of Cloud Run.

**Risk:** free hosts sleep and cold-start (about 30 seconds). Keep the service warm during the live demo and rehearse it.

## Plan B — pure no-code, zero infrastructure (safety net)

If a host misbehaves on demo day, fall back to a Gemini-only build with no server at all.

- Build the agent entirely on **1P connectors**: a **Google Sheet** holds assets and reservations, **Gmail** sends the staff recovery email, and the **maximizing workflow** (scheduled overdue check, then draft, approve, and send the email) lives in the Gemini no-code builder.

**Upside:** no server, no card, no GCP, nothing to keep awake. It meets every hard requirement: a Gemini-native agent, scored 1P connectors, and the maximizing pattern.

**Downside:** we do not reuse the coded repo at run time. The repo becomes the engineering and research story in the README and video, not the live backend. If we lean on this, the README and video should frame the work as "we built the system and modeled it in Gemini."

## Which to use

Prepare **Plan A** as the backup we build, because it is cheap and keeps our code in play. Keep **Plan B** fully designed and ready, because it needs no infrastructure and cannot be blocked by credits, cards, or cold starts. Lead with A; fall back to B if A's host fails.

The trade-off is code reuse (A) against zero-risk uptime (B).
