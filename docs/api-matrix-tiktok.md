# TikTok Official API Capability & Policy Matrix (`api-matrix-tiktok.md`)

**Owner Agent:** Agent Alpha (`Agent 1 — Official TikTok Platform Access, Policy, and Integration Specialist`)  
**Last Verified:** 27 October 2026  
**Target Account:** `@annreveals`  
**Default Write Flag:** `TIKTOK_WRITE_ENABLED=false`  

---

## 1. Executive Summary

TikTok divides creator and business capabilities across two official developer ecosystems:
1. **TikTok Accounts API v1.3 (`https://business-api.tiktok.com/open_api/v1.3/`)**: Required for reading, creating, replying to, and moderating comments on **owned** Business Account videos, as well as receiving `comment.update` webhooks.
   - **CRITICAL POLICY GATE (Effective March 20, 2026):** Developers must submit an explicit **TikTok Accounts API Access Application** (`https://business-api.tiktok.com/portal/docs/accounts-api-overview/v1.3`) to gain production access to organic Business Account endpoints. Until TikTok approves this application for `@annreveals`, all live Accounts API capabilities are classified as **`AWAITING_APPROVAL`** and operate in **`DRAFT` / `One-Tap Copy`** fallback mode.
2. **TikTok for Developers API v2 (`https://open.tiktokapis.com/v2/`)**: Provides Login Kit (`user.info.basic`, `user.info.profile`), Display API (`video.list`), and Content Posting API (`video.upload`, `video.publish`).
3. **Permanent Prohibitions (`UNAVAILABLE`)**: Neither API provides endpoints for reading a user's following feed (`get_following_posts`) or posting comments on third-party videos (`comment_on_nonowned_post`). Both methods are permanently blocked in code via `PermissionPolicyError`.

---

## 2. Complete Capability Matrix

| ID | Provider Method | Official Endpoint | HTTP | Required Scope(s) | Mar 20, 2026 Gate? | Live Status | Sandbox Status | Safe Fallback When Unapproved |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TT-CAP-01** | `get_owned_profile` | `https://business-api.tiktok.com/open_api/v1.3/business/get/` | `GET` | `user.info.basic`, `user.info.profile`, `user.info.stats` | Yes | `AWAITING_APPROVAL` | `VERIFIED_ACTIVE` | Owner profile settings in dashboard |
| **TT-CAP-02** | `get_owned_posts` | `https://business-api.tiktok.com/open_api/v1.3/business/video/list/` | `GET` | `video.list` | Yes | `AWAITING_APPROVAL` | `VERIFIED_ACTIVE` | Manual video URL link in Content Studio |
| **TT-CAP-03** | `list_owned_comments` | `https://business-api.tiktok.com/open_api/v1.3/business/comment/list/` | `GET` | `comment.list` | **Yes** | `AWAITING_APPROVAL` | `VERIFIED_ACTIVE` | Manual comment paste / sandbox queue |
| **TT-CAP-04** | `reply_to_owned_comment` | `https://business-api.tiktok.com/open_api/v1.3/business/comment/reply/` | `POST` | `comment.list.manage` | **Yes** | `AWAITING_APPROVAL` | `VERIFIED_ACTIVE` | `DRAFT` mode + One-Tap Copy & Open TikTok |
| **TT-CAP-05** | `create_comment_on_owned_post` | `https://business-api.tiktok.com/open_api/v1.3/business/comment/create/` | `POST` | `comment.list.manage` | **Yes** | `AWAITING_APPROVAL` | `VERIFIED_ACTIVE` | `DRAFT` first-comment candidate + Copy |
| **TT-CAP-06** | `subscribe_to_webhooks` | `https://business-api.tiktok.com/open_api/v1.3/business/webhook/update/` | `POST` | `comment.list` | **Yes** | `AWAITING_APPROVAL` | `VERIFIED_ACTIVE` | Scheduled polling reconciliation |
| **TT-CAP-07** | `refresh_auth` | `https://open.tiktokapis.com/v2/oauth/token/` | `POST` | `oauth.token.refresh` | No | `AWAITING_APPROVAL` | `VERIFIED_ACTIVE` | Prompt owner in Reconnect Wizard |
| **TT-CAP-08** | `publish_post` | `https://open.tiktokapis.com/v2/post/publish/video/init/` | `POST` | `video.publish`, `video.upload` | No (App Audit) | `AWAITING_APPROVAL` | `VERIFIED_ACTIVE` | Dual-Platform Studio One-Tap Copy + App |
| **TT-CAP-09** | `get_post_publication_status` | `https://open.tiktokapis.com/v2/post/publish/status/fetch/` | `POST` | `video.publish`, `video.upload` | No (App Audit) | `AWAITING_APPROVAL` | `VERIFIED_ACTIVE` | Manual check in TikTok app |
| **TT-CAP-10** | `get_inbox_messages` | `https://business-api.tiktok.com/open_api/v1.3/business/message/list/` | `GET` | `business.message.read` | Yes | `UNAVAILABLE` | `UNAVAILABLE` | Native TikTok Direct Messages inbox |
| **TT-CAP-11** | `get_following_posts` | *None — No Official API* | N/A | N/A | N/A | **`UNAVAILABLE`** | **`UNAVAILABLE`** | Curated Creator Shortlist + Shared URLs |
| **TT-CAP-12** | `comment_on_nonowned_post` | *None — No Official API* | N/A | N/A | N/A | **`UNAVAILABLE`** | **`UNAVAILABLE`** | **One-Tap Copy Draft + Open TikTok App** |

---

## 3. Rate Limits, Backoff, and Fail-Closed Rules

| Condition | HTTP Status / TikTok Code | Adapter Action (`apps/backend/integrations/tiktok/adapter.py`) | Dashboard Badge Impact (`FR-043`) |
| :--- | :--- | :--- | :--- |
| **Write Flag Disabled** | Local Policy Gate (`TIKTOK_WRITE_ENABLED=false`) | Refuses network write; returns deterministic `DRAFT_ONLY` result with draft text preserved. | `Connected: read only` or `Awaiting review` |
| **Unapproved Scope** | Missing `comment.list.manage` or `video.publish` | Blocks call prior to HTTP dispatch; raises `ScopeNotApprovedError`. | `Awaiting review` |
| **Authentication Expired / Revoked** | HTTP `401` or `403` (or TikTok payload `code: 40100` / `40001`) | Immediately transitions adapter to `OperationalMode.DRAFT` (`write_enabled=False`) and trips auth lock (`NFR-10`). | `Needs reconnect` |
| **Rate Limit Exceeded** | HTTP `429` (or TikTok payload `code: 40104`) | Parses `Retry-After` header if present; otherwise applies `30s / 60s / 120s` base backoff with random jitter (`±20%`) (`NFR-02`). | Shows rate-limit cooldown timer |
| **Upstream Server Failure** | HTTP `500` / `502` / `503` / `504` | Increments consecutive failure counter; opens circuit breaker after `3` consecutive 5xx responses for `300s`. | `Degraded (TikTok API outage)` |
| **Network Timeout on Write** | `TimeoutError` / `URLError` during comment create/reply | Marks dispatch state as `RECONCILE_PENDING` (`NFR-03`) so worker reconciles via `list_owned_comments` before retrying, preventing duplicate replies. | `Reconciling comment status` |
| **Third-Party Comment / Scrape** | Call to `comment_on_nonowned_post` or `get_following_posts` | Immediately raises `PermissionPolicyError("ERR_THIRD_PARTY_INTERACTION_PROHIBITED")`. | Permanently disabled (`Manual copy mode`) |
