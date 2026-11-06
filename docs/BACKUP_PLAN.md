# Backup plan

This plan covers one case: the organizers give us the **Gemini Enterprise licence** but **no GCP credits or project**.

In that case the mandatory tool (Gemini Enterprise) is covered. The only real gap is **where our connector runs**: Cloud Run needs a billing-enabled GCP project. The database does not force the issue — **Cloud Firestore has a free tier (Firebase Spark plan) that needs no billing and no card**, so our existing storage layer can stay as it is. The backups below keep our code and only swap the host.

Key constraint: judges assess the Gemini app from **2026-11-11 to 11-14**, so whatever hosts the connector must stay up on its own through that window.

## Plan A — same architecture, off GCP (primary backup)

Keep the current design. Move it off GCP.

- Host the MCP connector on a **free, no-card platform** (for example a Render free web service or Hugging Face Spaces). Both give a public HTTPS URL, which the Gemini Enterprise 3P connector needs.
- **Keep Cloud Firestore as the data store on the free Spark tier** (no card, no credits). Our backend already uses Firestore, so the lending rules and transactions can stay. The store still needs explicit cloud configuration and credentials; see [Firebase setup](FIREBASE_SETUP.md).
  - Supabase free tier is the organizer-approved fallback, but it is **Postgres**: moving to it means rewriting our transactional storage layer. Use it only if the Firestore free tier is somehow unavailable.

**Upside:** reuses all our coded logic (reservations, overdue recovery, substitution) through the MCP connector **and** keeps the storage layer untouched. This is the work we already planned, just pointed at a free host instead of Cloud Run.

**Risk — cold starts, not capacity.** Free hosts sleep after about 15 minutes idle and take about a minute to wake. Because judges assess **unattended from 2026-11-11 to 11-14**, a sleeping connector could time out on a judge's first call. Keep it warm across that window: either ping it every ~10 minutes (one service fits inside Render's 750 free instance-hours/month) or pay about $7 for an always-on instance for those few days and cancel after. Warm it manually before the live demo too. Capacity itself (bandwidth, number of services) is far more than this demo needs.

## Plan B — pure no-code, zero infrastructure (safety net)

If a host misbehaves on demo day, fall back to a Gemini-only build with no server at all.

- Build the agent entirely on **1P connectors**: a **Google Sheet** holds assets and reservations, **Gmail** sends the staff recovery email, and the **maximizing workflow** (scheduled overdue check, then draft, approve, and send the email) lives in the Gemini no-code builder.

**Upside:** no server, no card, no GCP, nothing to keep awake. It meets every hard requirement: a Gemini-native agent, scored 1P connectors, and the maximizing pattern.

**Downside:** we do not reuse the coded repo at run time. The repo becomes the engineering and research story in the README and video, not the live backend. If we lean on this, the README and video should frame the work as "we built the system and modeled it in Gemini."

## Which to use

Prepare **Plan A** as the backup we build, because it is cheap and keeps our code in play. Keep **Plan B** fully designed and ready, because it needs no infrastructure and cannot be blocked by credits, cards, or cold starts. Lead with A; fall back to B if A's host fails.

The trade-off is code reuse (A) against zero-risk uptime (B).
