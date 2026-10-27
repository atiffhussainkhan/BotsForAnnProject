# TikTok Official Documentation Primary-Source Register (`source-register.md`)

**Verified By:** Agent Alpha (`Agent 1 — Official TikTok Platform Access, Policy, and Integration Specialist`)  
**Verification Date:** 27 October 2026  
**Project:** Ann Reveals AI Manager (`ARAIM` v4.0)  
**Account:** `@annreveals`  

---

## 1. Summary of Primary Sources Checked (27 Oct 2026)

| Source ID | Official Document Title | Primary URL | Verification Date | API Family / Version | Key Policy / Technical Finding |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SRC-TT-01** | TikTok Accounts API v1.3 Overview | `https://business-api.tiktok.com/portal/docs/accounts-api-overview/v1.3` | 27 Oct 2026 | TikTok Business Accounts API `v1.3` | **CRITICAL GATE:** Effective **March 20, 2026**, developers must submit an explicit **TikTok Accounts API access application** and receive approval before accessing organic Business Account endpoints (videos, comments, webhooks, insights). |
| **SRC-TT-02** | TikTok Accounts API — Owned-Video Comments Management | `https://business-api.tiktok.com/portal/docs?id=1736271785207810` | 27 Oct 2026 | TikTok Business Accounts API `v1.3` | Provides `/open_api/v1.3/business/comment/list/`, `/business/comment/create/`, `/business/comment/reply/`, and `/business/comment/status/update/`. Strictly scoped to **owned Business Account videos** authorized via OAuth (`comment.list`, `comment.list.manage`). Zero support for commenting on third-party videos. |
| **SRC-TT-03** | TikTok Business API — Webhook Subscriptions & Event Payloads | `https://business-api.tiktok.com/gateway/docs/index?doc_id=1751617884206210` | 27 Oct 2026 | TikTok Business Webhook Gateway `v1.3` | Delivers real-time `comment.update` notifications for owned videos. Includes signature header (`TikTok-Signature` / `X-TikTok-Signature`) with timestamp `t=` and HMAC-SHA256 `s=` signed with client secret. Requires HTTPS callback responding `200 OK` within 3 seconds. |
| **SRC-TT-04** | TikTok Content Posting API | `https://developers.tiktok.com/products/content-posting-api/` | 27 Oct 2026 | TikTok for Developers API `v2` | Supports `video.upload` (inbox draft upload) and `video.publish` (direct post to profile via `https://open.tiktokapis.com/v2/post/publish/video/init/`). Direct post requires app audit and querying creator info (`/v2/post/publish/creator_info/query/`) plus commercial disclosure parameters (`brand_content_toggle`, `brand_organic_toggle`). |
| **SRC-TT-05** | TikTok Developer Guidelines | `https://developers.tiktok.com/docs/en/our-guidelines-developer-guidelines` | 27 Oct 2026 | Platform-Wide Legal & Policy | Strictly prohibits scraping, automated mass engagement (liking/commenting/following), bypassing authentication/rate limits, storing unconsented personal data, or misrepresenting app capabilities. |
| **SRC-TT-06** | TikTok Login Kit & Scopes Overview | `https://developers.tiktok.com/docs/en/scopes-overview` | 27 Oct 2026 | TikTok OAuth 2.0 (`v2` & Business `v1.3`) | Lists `user.info.basic`, `user.info.profile`, `user.info.stats`, `video.list`, `video.upload`, `video.publish` on `open.tiktokapis.com`. Confirms no scope exists for reading third-party following feeds or writing comments on third-party videos. |
| **SRC-TT-07** | Promoting a Brand, Product, or Service (Commercial Content Disclosure) | `https://support.tiktok.com/en/business-and-creator/creator-and-business-accounts/promoting-a-brand-product-or-service` | 27 Oct 2026 | TikTok Creator & Business Help Center | Requires enabling the **Disclose video content** setting (`Your brand` -> "Promotional content" or `Branded content` -> "Paid partnership") whenever a video promotes a brand, product, or service with commercial ties, affiliate links, or TikTok Shop links—regardless of whether the item was self-purchased. |

---

## 2. Detailed Primary-Source Verification Notes

### SRC-TT-01: TikTok Accounts API v1.3 Overview
- **URL:** `https://business-api.tiktok.com/portal/docs/accounts-api-overview/v1.3`
- **Checked On:** 27 October 2026
- **Base Host:** `https://business-api.tiktok.com`
- **Findings:**
  - The TikTok Accounts API v1.3 (formerly Organic Business Account API) enables TikTok Business Accounts to retrieve account metrics, list organic posts (`/open_api/v1.3/business/video/list/`), and manage comments on owned organic posts.
  - **March 20, 2026 Policy Gate:** TikTok introduced a mandatory **Accounts API Access Application** effective March 20, 2026. Any developer app created or operating after this date must submit a formal access request explaining the business use case, data retention, and moderation controls before the `comment.list`, `comment.list.manage`, and `video.list` scopes can be granted for production use.
  - **Account Prerequisite:** The creator account (`@annreveals`) must be switched to a **TikTok Business Account** (free in the TikTok mobile app under *Settings and privacy -> Account -> Switch to Business Account*). Note: Switching to a Business Account restricts usage of the General Music Library to the **Commercial Music Library (CML)** (`FR-023`, `FR-056`).

### SRC-TT-02: Owned-Video Comments Management (`doc_id=1736271785207810`)
- **URL:** `https://business-api.tiktok.com/portal/docs?id=1736271785207810`
- **Checked On:** 27 October 2026
- **Verified Endpoints:**
  1. **List Comments on Owned Video:**
     - Method & Path: `GET https://business-api.tiktok.com/open_api/v1.3/business/comment/list/`
     - Required Header: `Access-Token: <business_access_token>`
     - Query Parameters: `business_id` (string, required), `video_id` (string, required), `comment_ids` (optional array), `include_replies` (boolean, default `false`), `status` (`PUBLIC` | `ALL`), `sort_field` (`create_time` | `likes`), `sort_order` (`asc` | `desc`), `cursor` (integer), `max_results` (integer, 1–30, default 20).
     - Required Scope: `comment.list`
  2. **Create Top-Level Comment on Owned Video:**
     - Method & Path: `POST https://business-api.tiktok.com/open_api/v1.3/business/comment/create/`
     - JSON Body: `{"business_id": "...", "video_id": "...", "text": "..."}` (max 150 UTF-8 characters recommended by TikTok comment limit).
     - Required Scope: `comment.list.manage`
     - Use Case in ARAIM: Optional first-party ownership/provenance note on `@annreveals`'s own video (`FR-025`), subject to anti-spam variation guard (`FR-055`).
  3. **Reply to an Existing Comment on Owned Video:**
     - Method & Path: `POST https://business-api.tiktok.com/open_api/v1.3/business/comment/reply/`
     - JSON Body: `{"business_id": "...", "video_id": "...", "comment_id": "...", "text": "..."}` (max 150 UTF-8 characters).
     - Required Scope: `comment.list.manage`
  4. **Hide / Unhide Comment on Owned Video:**
     - Method & Path: `POST https://business-api.tiktok.com/open_api/v1.3/business/comment/status/update/`
     - JSON Body: `{"business_id": "...", "video_id": "...", "comment_ids": ["..."], "action": "HIDE" | "UNHIDE"}`
     - Required Scope: `comment.list.manage`

### SRC-TT-03: Webhook Subscriptions & Event Payloads (`doc_id=1751617884206210`)
- **URL:** `https://business-api.tiktok.com/gateway/docs/index?doc_id=1751617884206210`
- **Checked On:** 27 October 2026
- **Findings:**
  - Webhook subscription management via `/open_api/v1.3/business/webhook/update/` and `/open_api/v1.3/business/webhook/list/`.
  - Event type `comment.update` notifies the callback URL when a comment or reply is created, updated, hidden, or deleted on an owned Business Account video.
  - Signature verification: Header `TikTok-Signature` (or `X-TikTok-Signature`) formatted as `t=<unix_timestamp>,s=<hex_hmac_sha256>`. The signed payload string is `<timestamp>.<raw_request_body>` hashed with HMAC-SHA256 using the app's `client_secret`.
  - Replay defense: Reject webhook payloads where `abs(current_time - t) > 300` seconds or where the `(event_id, comment_id, timestamp)` tuple has already been processed (`NFR-04`, `NFR-05`).

### SRC-TT-04: Content Posting API (`https://developers.tiktok.com/products/content-posting-api/`)
- **URL:** `https://developers.tiktok.com/products/content-posting-api/`
- **Checked On:** 27 October 2026
- **Verified Endpoints:**
  - Query Creator Info: `POST https://open.tiktokapis.com/v2/post/publish/creator_info/query/`
  - Upload to Inbox (Draft): `POST https://open.tiktokapis.com/v2/post/publish/inbox/video/init/` (`video.upload` scope)
  - Direct Publish: `POST https://open.tiktokapis.com/v2/post/publish/video/init/` (`video.publish` scope)
  - Check Publish Status: `POST https://open.tiktokapis.com/v2/post/publish/status/fetch/` (`publish_id`)
  - Commercial Content Disclosure fields in `post_info`:
    - `brand_content_toggle` (boolean): `true` when promoting a third-party brand (`Paid partnership` label).
    - `brand_organic_toggle` (boolean): `true` when promoting the creator's own brand/business (`Promotional content` label).

### SRC-TT-05 & SRC-TT-06: Developer Guidelines & Scopes Overview
- **URLs:** `https://developers.tiktok.com/docs/en/our-guidelines-developer-guidelines` & `https://developers.tiktok.com/docs/en/scopes-overview`
- **Checked On:** 27 October 2026
- **Findings:**
  - No scope exists in either TikTok Login Kit (`v2`) or TikTok Business Accounts API (`v1.3`) to read a user's following feed or post comments on another user's video.
  - Automated comment posting on non-owned content is a direct violation of the TikTok Developer Agreement and Community Guidelines on artificial engagement.
  - In `ARAIM`, `get_following_posts` and `comment_on_nonowned_post` are permanently `UNAVAILABLE` and raise `PermissionPolicyError`.

### SRC-TT-07: Commercial Disclosure Policy
- **URL:** `https://support.tiktok.com/en/business-and-creator/creator-and-business-accounts/promoting-a-brand-product-or-service`
- **Checked On:** 27 October 2026
- **Findings:**
  - If `@annreveals` bought a perfume with her own money (`SELF_PURCHASED`) and has **zero** commercial relationship (`NONE` — no affiliate link, no TikTok Shop commission, no brand sponsorship, no gifted incentive), she should **not** turn on the TikTok commercial content disclosure toggle (`FR-055`), because enabling it falsely labels the video as `Promotional content` or `Paid partnership`.
  - However, if `@annreveals` bought a perfume with her own money (`SELF_PURCHASED`) **and** includes an affiliate code, TikTok Shop link, or paid sponsorship (`AFFILIATE`, `TIKTOK_SHOP`, `PAID_COLLAB`), she **must** enable the TikTok Commercial Content Disclosure toggle AND include prominent UK ASA `Ad` disclosure (`FR-021`, `FR-022`, `FR-026`, `FR-053`), while never appending "not an ad".
