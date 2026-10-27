# Agent Alpha (TikTok) — Architectural Decisions Log (`DECISIONS.md`)

**Agent:** Agent Alpha (`Agent 1 — Official TikTok Platform Access, Policy, and Integration Specialist`)  
**Project:** Ann Reveals AI Manager (`ARAIM` v4.0)  
**Target Account:** `@annreveals`  
**Last Updated:** 27 October 2026  

---

## ADR-TT-001: Dual-API Architecture (TikTok Display/Content Posting API vs. TikTok Accounts API v1.3)

- **Status:** Accepted
- **Date:** 27 October 2026
- **Context:**
  TikTok splits creator and business capabilities across two distinct developer portals and API families:
  1. **TikTok for Developers (`open.tiktokapis.com/v2/`)**: Provides Login Kit (`user.info.basic`, `user.info.profile`, `user.info.stats`), Display API (`video.list`, `video.List`), and Content Posting API (`video.upload`, `video.publish`). However, it does **not** expose endpoints to read, reply to, or moderate comments on owned videos.
  2. **TikTok Business API / Accounts API v1.3 (`business-api.tiktok.com/open_api/v1.3/`)**: Provides organic Business Account management, including owned-video comment listing (`/business/comment/list/`), comment creation (`POST /business/comment/create/`), comment replying (`POST /business/comment/reply/`), status hiding/moderation, and organic comment webhooks (`comment.update`).
- **Decision:**
  Implement a unified `TikTokAdapter` (`apps/backend/integrations/tiktok/adapter.py`) that routes:
  - Profile inspection, video listing fallback, and draft/direct video upload to `open.tiktokapis.com` (`v2`) or `business-api.tiktok.com` (`v1.3`) depending on approved scopes.
  - Owned-video comment ingestion, comment creation on owned posts, comment replies on owned posts, and webhook event handling strictly through **TikTok Accounts API v1.3** (`business-api.tiktok.com/open_api/v1.3/business/...`).
  - Strictly restrict outbound HTTP calls to an explicit host allowlist (`business-api.tiktok.com`, `open.tiktokapis.com`).

---

## ADR-TT-002: Compliance with March 20, 2026 TikTok Accounts API Access Gate

- **Status:** Accepted
- **Date:** 27 October 2026
- **Context:**
  Per official TikTok Business API documentation (`https://business-api.tiktok.com/portal/docs/accounts-api-overview/v1.3`), effective **March 20, 2026**, developers must submit an explicit **TikTok Accounts API access application** before accessing organic Business Account endpoints (`/business/video/list/`, `/business/comment/list/`, `/business/comment/create/`, `/business/comment/reply/`, `/business/webhook/`). Unapproved apps or apps awaiting review cannot invoke live comment read/write endpoints.
- **Decision:**
  - Classify all live TikTok Accounts API v1.3 endpoints as `AWAITING_APPROVAL` until live app credentials (`TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_BUSINESS_APP_ID`) and granted token scopes (`video.list`, `comment.list`, `comment.list.manage`, `biz.spark.auth`) are cryptographically verified via `refresh_auth` / scope inspection.
  - Default `TIKTOK_WRITE_ENABLED=false` across all environments (`NFR-09`).
  - Surface truthful UI badges (`Awaiting review` / `Draft only`) rather than claiming live write capability.

---

## ADR-TT-003: Permanent Hard Block on Third-Party Post Commenting & Follow-List Scraping

- **Status:** Accepted (Non-Negotiable Policy Gate)
- **Date:** 27 October 2026
- **Context:**
  FR-011 through FR-017 describe the Friends & Creator Engagement Assistant. Neither TikTok for Developers (`open.tiktokapis.com`) nor TikTok Accounts API v1.3 (`business-api.tiktok.com`) offers a lawful API to read arbitrary third-party creators' feeds via follow-list scraping or to post automated comments on videos not owned by `@annreveals`. Furthermore, TikTok Developer Guidelines explicitly prohibit automated mass commenting, unsolicited engagement, and unauthorized scraping.
- **Decision:**
  - `comment_on_nonowned_post` and `get_following_posts` are permanently marked `UNAVAILABLE` in `tiktok-capabilities.json` and `capability-matrix.csv`.
  - Calling `comment_on_nonowned_post()` or `get_following_posts()` in `TikTokAdapter` unconditionally raises `PermissionPolicyError` with error code `ERR_THIRD_PARTY_INTERACTION_PROHIBITED`, regardless of environment flags.
  - Creator engagement on TikTok operates strictly via owner-curated URLs/shortlists and **One-Tap Copy Draft + Open Native TikTok App** (`FR-014`, `FR-048`).

---

## ADR-TT-004: Zero-Dependency Python Standard Library Implementation & Fail-Closed Resiliency

- **Status:** Accepted
- **Date:** 27 October 2026
- **Context:**
  To guarantee zero dependency supply-chain breakage and deterministic execution across local sandboxes, CI containers, and cloud workers, the core TikTok integration layer must not rely on fragile third-party SDKs. Additionally, `NFR-02`, `NFR-03`, `NFR-05`, and `NFR-10` mandate HMAC webhook verification, replay protection, jittered rate-limit backoff, circuit breaking, and automatic fail-closed downgrade to `DRAFT`/`READ_ONLY` on `401`/`403`.
- **Decision:**
  - Build `apps/backend/integrations/tiktok/` exclusively using Python 3.9+ standard library (`hmac`, `hashlib`, `json`, `time`, `urllib.request`, `urllib.parse`, `urllib.error`, `dataclasses`, `typing`, `enum`, `random`).
  - Enforce constant-time `hmac.compare_digest` signature verification and configurable timestamp freshness tolerance (`default=300s`) + event ID replay cache in `webhook.py`.
  - Implement automatic fail-closed transition to `OperationalMode.DRAFT` and `ConnectionBadge.NEEDS_RECONNECT` whenever a `401 Unauthorized` or `403 Forbidden` (or scope revocation) occurs.
  - Implement `Retry-After` parsing + `30s / 60s / 120s` jittered exponential backoff on `429 Too Many Requests` (`NFR-02`) and a 5xx circuit breaker that trips after 3 consecutive upstream failures.

---

## ADR-TT-005: Separation of Self-Purchase Provenance and TikTok Commercial Content Disclosure

- **Status:** Accepted
- **Date:** 27 October 2026
- **Context:**
  TikTok's Commercial Content Disclosure policy requires creators to enable the native **Disclose video content** toggle (`Your brand` or `Branded content`) whenever promoting a brand, product, or service in exchange for value, affiliate commission, or TikTok Shop link—even if the creator originally bought the perfume bottle with their own money (`FR-021`, `FR-022`, `FR-053`, `FR-055`). Conversely, self-purchasing a product with zero commercial relationship must **not** trigger false paid partnership disclosures or repetitive spam comments.
- **Decision:**
  - When publishing or pre-checking via `Content Posting API` (`publish_post`), enforce independent provenance (`SELF_PURCHASED` vs `PR_GIFTED`) and commercial incentive flags (`brand_content_toggle`, `brand_organic_toggle`).
  - Provide optional first-party ownership comment creation (`create_comment_on_owned_post`) only when `TIKTOK_WRITE_ENABLED=true`, `comment.list.manage` is `VERIFIED_ACTIVE`, and anti-spam variation checks pass (`FR-025`, `FR-055`).
