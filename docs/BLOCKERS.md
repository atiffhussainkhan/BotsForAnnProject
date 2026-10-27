# EXTERNAL APPROVAL BLOCKERS & FALLBACK REGISTER

**Project:** Ann Reveals AI Manager (`ARAIM` v4.0)
**Date:** 27 October 2026

> [!NOTE]
> None of the blockers below prevent **Ann Reveals AI Manager** from running in the cloud today for comment drafting, receipt verification, UK ASA / platform compliance checking, dual-platform caption generation, creator watchlist alerts, or appeal packet drafting. They only gate **automated outbound comment publishing** until the owner completes the official provider steps.

| Blocker ID | Platform / Scope | External Requirement | Current Safe Fallback State | Exact Owner Action to Resolve |
|---|---|---|---|---|
| `BLK-001` | **TikTok Owned-Video Auto-Reply (`comment.list.manage`)** | Requires TikTok's post-20 March 2026 **Accounts API Access Application** approval + `@annreveals` OAuth consent. | `Awaiting review — Draft only` (`TIKTOK_WRITE_ENABLED=false`). All TikTok compliance checks, captions, and reply drafts work with 1-tap Copy & Open App. | Submit the pre-prepared application in `docs/TIKTOK_APPLICATION_EVIDENCE.md` at `https://business-api.tiktok.com/portal/`. |
| `BLK-002` | **Instagram Owned-Post Auto-Reply (`instagram_business_manage_comments`)** | Requires `@annreveals` to be a Professional (Creator/Business) account + owner OAuth sign-in via Meta app. | `Not connected — Draft only` (`INSTAGRAM_WRITE_ENABLED=false`). Full inbox simulation, AI drafting, and Instagram Branded Content preflight active. | Use Step 3 of the in-app **Guided Setup Wizard** to connect `@annreveals` via official Instagram OAuth and run 1 live test reply. |
| `BLK-003` | **Third-Party Friends Auto-Commenting** | Neither TikTok nor Meta provides an official API for unrestricted automated commenting on other creators' posts. | `UNAVAILABLE (Hard Blocked)` (`THIRD_PARTY_AUTOCOMMENT=false`). **Creator Watchlist Assistant** generates 2–4 tailored draft comments per new friend post for 1-tap manual posting. | No action needed — manual 1-tap owner posting protects `@annreveals` from spam enforcement. |
