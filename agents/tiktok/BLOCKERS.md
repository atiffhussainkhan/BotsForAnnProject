# Agent Alpha (TikTok) — Active External Blockers & Mitigations (`BLOCKERS.md`)

**Agent:** Agent Alpha (`Agent 1 — Official TikTok Platform Access, Policy, and Integration Specialist`)  
**Project:** Ann Reveals AI Manager (`ARAIM` v4.0)  
**Last Updated:** 27 October 2026  

---

## Summary of Blockers

| Blocker ID | Severity | Component / Scope | Current Status | External Gatekeeper | Safe Fallback Active? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **BLK-TT-001** | **HIGH (External Policy Gate)** | TikTok Accounts API v1.3 Access Application (Effective March 20, 2026) | `AWAITING_APPROVAL` | TikTok Business API Review Team (`business-api.tiktok.com`) | **YES** (`DRAFT_ONLY` + One-Tap Copy & Open TikTok App) |
| **BLK-TT-002** | **MEDIUM (Owner Action)** | TikTok Developer App Review for Content Posting API (`video.publish`, `video.upload`) | `AWAITING_APPROVAL` | TikTok for Developers Portal (`developers.tiktok.com`) | **YES** (Export package + One-Tap Copy Caption & Open TikTok) |
| **BLK-TT-003** | **PERMANENT (Platform Boundary)** | Third-Party Video Commenting & Follow-List Feed Discovery | `UNAVAILABLE` (By Design) | TikTok Platform Policy & API Architecture | **YES** (Curated URL import + Manual Copy & Open Native App) |
| **BLK-TT-004** | **MEDIUM (Regional / Account Gate)** | TikTok Business Messaging / Direct Message Inbox API | `AWAITING_APPROVAL` / `UNAVAILABLE` | TikTok Business Messaging Allowlist | **YES** (Disabled in v1; comments handled via Accounts API) |

---

## Detailed Blocker Analysis

### BLK-TT-001: Mandatory March 20, 2026 TikTok Accounts API v1.3 Access Application
- **Primary Source:** `https://business-api.tiktok.com/portal/docs/accounts-api-overview/v1.3` (Verified 27 Oct 2026).
- **Description:**
  Effective **March 20, 2026**, TikTok requires all developers to submit a formal **TikTok Accounts API Access Application** in the TikTok For Business Developer Portal before making live calls to organic Business Account endpoints:
  - `GET /open_api/v1.3/business/video/list/` (Owned video metadata & engagement metrics)
  - `GET /open_api/v1.3/business/comment/list/` (Listing comments and replies on owned videos)
  - `POST /open_api/v1.3/business/comment/create/` (Posting a top-level ownership/pinned candidate comment on an owned video)
  - `POST /open_api/v1.3/business/comment/reply/` (Replying to viewer comments on an owned video)
  - `POST /open_api/v1.3/business/comment/status/update/` (Hiding/unhiding spam or abusive comments)
  - Webhook subscriptions (`comment.update`)
- **Impact on `@annreveals`:**
  Until the owner completes the Business Account linking and TikTok approves the Accounts API v1.3 application (`comment.list`, `comment.list.manage`, `video.list`), live automated comment ingestion and auto-reply on TikTok cannot execute against production servers.
- **Required Owner Action:**
  Follow the step-by-step instructions in [`research/tiktok/approval-checklist.md`](../../research/tiktok/approval-checklist.md) and attach the pre-prepared evidence packet in [`docs/TIKTOK_APPLICATION_EVIDENCE.md`](../../docs/TIKTOK_APPLICATION_EVIDENCE.md).
- **Engineering Mitigation:**
  - `TIKTOK_WRITE_ENABLED` defaults to `false`.
  - Adapter reports capability state `AWAITING_APPROVAL` and UI badge `Awaiting review` (`FR-043`).
  - Deterministic sandbox mode (`sandbox_mode=True`) validates the full contract offline without falsifying live status.

---

### BLK-TT-002: TikTok Content Posting API App Audit (`video.publish` / `video.upload`)
- **Primary Source:** `https://developers.tiktok.com/products/content-posting-api/` (Verified 27 Oct 2026).
- **Description:**
  Direct video publishing (`POST https://open.tiktokapis.com/v2/post/publish/video/init/`) requires passing TikTok's Content Posting API audit, including UX compliance checks for commercial content disclosure toggles (`brand_content_toggle`, `brand_organic_toggle`), privacy level selection, and explicit creator consent before posting. Unaudited apps are restricted to posting to private/sandbox accounts or draft inbox upload (`video.upload`).
- **Engineering Mitigation:**
  - Dual-Platform Content Studio (`FR-047`, `FR-048`) generates the complete TikTok caption, 5 hashtags, disclosure checklist, and first-comment candidate, allowing one-tap copy + native TikTok upload while `video.publish` is `AWAITING_APPROVAL`.

---

### BLK-TT-003: Absence of Lawful Third-Party Commenting or Follow-List Feed API
- **Primary Source:** `https://developers.tiktok.com/docs/en/scopes-overview` & `https://developers.tiktok.com/docs/en/our-guidelines-developer-guidelines` (Verified 27 Oct 2026).
- **Description:**
  TikTok provides **no official API endpoint** to list posts from accounts a user follows or to publish comments on third-party creators' videos. Attempting to bypass this via headless browsers, session cookies, or private mobile endpoints violates TikTok Developer Guidelines and risks permanent suspension of `@annreveals`.
- **Engineering Mitigation:**
  - `get_following_posts` and `comment_on_nonowned_post` are permanently classified `UNAVAILABLE` and raise `PermissionPolicyError` in `TikTokAdapter`.
  - Friends & Creator Engagement Assistant (`FR-011`–`FR-017`) uses owner-curated creator URLs and generates 2–4 contextual draft comments for **One-Tap Copy + Open in TikTok App**.
