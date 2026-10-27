# TikTok Accounts API v1.3 & Content Posting API — Official Application Evidence Packet (`TIKTOK_APPLICATION_EVIDENCE.md`)

**Prepared By:** Agent Alpha (`Agent 1 — Official TikTok Platform Access, Policy, and Integration Specialist`)  
**Date:** 27 October 2026  
**Applicant Account:** `@annreveals` (Ann Reveals — Luxury & Niche Fragrance Reviews, UK)  
**Application Type:**
1. **TikTok Business Accounts API v1.3 Access Application** (Mandatory effective **March 20, 2026** per `https://business-api.tiktok.com/portal/docs/accounts-api-overview/v1.3`)
2. **TikTok for Developers App Review** (`Login Kit`, `Display API`, `Content Posting API`)

---

## 1. Ready-to-Paste Application Answers (TikTok Business Developer Portal)

When filling out the **TikTok Accounts API v1.3 Access Application** at `https://business-api.tiktok.com/portal/apps`, copy and paste the truthful declarations below:

### Field 1: App Name & Website
- **App Name:** `Ann Reveals AI Manager`
- **Official Website / Domain:** `https://app.annreveals.co.uk` (or owner's configured cloud PWA URL)
- **Privacy Policy URL:** `https://app.annreveals.co.uk/legal/privacy`
- **Terms of Service URL:** `https://app.annreveals.co.uk/legal/terms`

### Field 2: Business Use Case Description (Copy-Paste Ready)
> **Use Case Summary:**
> `Ann Reveals AI Manager` is a first-party creator management and audience engagement web application built exclusively for the verified UK fragrance creator account `@annreveals` (TikTok Business Account).
>
> **How We Use TikTok Accounts API v1.3:**
> 1. **Owned-Video Comment Management (`comment.list`, `comment.list.manage`, Webhooks `comment.update`):** We ingest viewer comments on `@annreveals`'s own published fragrance review videos via official webhooks and `/open_api/v1.3/business/comment/list/`. We classify viewer questions (e.g., fragrance notes, longevity, projection, retailer availability) and draft helpful, accurate replies grounded in `@annreveals`'s verified product notes. Replies are either approved by the creator in Draft mode or sent via `/open_api/v1.3/business/comment/reply/` only on `@annreveals`'s own videos. High-risk or sensitive comments (e.g., skin allergies, complaints, spam) are routed to human moderation or hidden via `/open_api/v1.3/business/comment/status/update/`.
> 2. **Owned-Video Listing & Analytics (`video.list`, `user.info.basic`, `user.info.stats`):** We retrieve `@annreveals`'s own published video list (`/open_api/v1.3/business/video/list/`) to link each video to its corresponding fragrance product notes and UK ASA / TikTok Commercial Content compliance checklist.
>
> **Strict Compliance & Safety Guarantees:**
> - Single first-party creator tool: Used only by `@annreveals` on her own TikTok Business Account.
> - Zero third-party automation: The application NEVER scrapes other creators' profiles, NEVER accesses non-owned videos via API, and NEVER posts automated comments on third-party videos.
> - Prominent human control: Includes a per-platform `OFF / DRAFT / SAFE_AUTO` mode switch and an instant `EMERGENCY STOP` kill-switch that halts all outgoing API writes immediately.

### Field 3: Requested Scopes & Justification Table

| API Family | Scope Name | Exact Endpoint(s) Used | Justification for TikTok Reviewer |
| :--- | :--- | :--- | :--- |
| **Accounts API v1.3** | `user.info.basic` / `user.info.profile` / `user.info.stats` | `GET /open_api/v1.3/business/get/` | Display connection status badge, account handle (`@annreveals`), and profile health on the owner dashboard. |
| **Accounts API v1.3** | `video.list` | `GET /open_api/v1.3/business/video/list/` | Match `@annreveals`'s own videos with fragrance review notes and purchase provenance records so viewer questions are answered accurately. |
| **Accounts API v1.3** | `comment.list` | `GET /open_api/v1.3/business/comment/list/` & Webhook `comment.update` | Display incoming viewer comments on `@annreveals`'s own videos in the unified Comment Inbox and reconcile missed webhooks. |
| **Accounts API v1.3** | `comment.list.manage` | `POST /open_api/v1.3/business/comment/reply/`, `POST /open_api/v1.3/business/comment/create/`, `POST /open_api/v1.3/business/comment/status/update/` | Reply to viewer fragrance questions on `@annreveals`'s own videos, post optional first-party video notes, and hide abusive/spam comments. |
| **Content Posting API v2** | `video.upload` | `POST /v2/post/publish/inbox/video/init/` | Allow `@annreveals` to send pre-checked fragrance review videos and captions to her TikTok Inbox Drafts. |
| **Content Posting API v2** | `video.publish` | `POST /v2/post/publish/video/init/` | Allow `@annreveals` to publish videos with mandatory TikTok Commercial Content Disclosure toggles (`brand_content_toggle`, `brand_organic_toggle`). |

---

## 2. Demo Screen-Recording Script for TikTok App Review

TikTok requires a short screen recording (`MP4`, under 50 MB, 2–3 minutes) showing the end-to-end user flow. Record the following 5 scenes in the **Ann Reveals AI Manager** PWA:

1. **Scene 1 — Login & OAuth Consent (0:00–0:30):**
   - Show the owner clicking **"Connect TikTok Business Account"** in Onboarding Step 3.
   - Show the official TikTok OAuth 2.0 authorization screen displaying the requested scopes (`user.info.basic`, `video.list`, `comment.list`, `comment.list.manage`) and redirecting back to `Ann Reveals AI Manager`.
2. **Scene 2 — Truthful Status Badge & Mode Switch (0:30–1:00):**
   - Show the Dashboard with the connection status badge, the `OFF / DRAFT / SAFE_AUTO` selector (defaulting to `DRAFT`), and the red `EMERGENCY STOP` button.
3. **Scene 3 — Owned-Video Comment Inbox & Reply Approval (1:00–1:45):**
   - Open the **Comment Inbox** showing a viewer comment on `@annreveals`'s own fragrance video (e.g., *"How long does this vanilla extrait last on skin?"*).
   - Show the AI-generated draft reply grounded in verified fragrance notes, and click **"Approve & Send Reply"** (invoking `POST /open_api/v1.3/business/comment/reply/`).
4. **Scene 4 — Content Studio & Commercial Disclosure Toggle (1:45–2:15):**
   - Open the **Dual-Platform Content Studio**, show the TikTok Commercial Content Disclosure selector (`Your brand` / `Branded content`), privacy selector, and verified purchase badge.
5. **Scene 5 — Disconnect / Revoke Access (2:15–2:30):**
   - Show the **"Disconnect TikTok Account"** button in Settings that revokes token storage and transitions the app immediately to `Not connected`.

---

## 3. Data Privacy, Security & UK GDPR Declarations

- **Encryption at Rest:** All OAuth access tokens and refresh tokens are encrypted at rest using AES-GCM / Fernet (`NFR-05`).
- **Webhook Verification:** All incoming TikTok webhooks are verified using constant-time `HMAC-SHA256` signature validation and a 300-second timestamp freshness window (`apps/backend/integrations/tiktok/webhook.py`).
- **Data Minimisation & Retention:** Viewer comment metadata is retained only for thread deduplication and audit history on `@annreveals`'s own videos, and is purged immediately upon account disconnection or data erasure request (`NFR-06`).
