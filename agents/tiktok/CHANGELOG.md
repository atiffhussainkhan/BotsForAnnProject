# Agent Alpha (TikTok) — Changelog (`CHANGELOG.md`)

**Agent:** Agent Alpha (`Agent 1 — Official TikTok Platform Access, Policy, and Integration Specialist`)  
**Project:** Ann Reveals AI Manager (`ARAIM` v4.0)  

---

## [4.0.0] — 2026-10-27

### Added
- **Primary-Source Research & Verification (`research/tiktok/`):**
  - Created `research/tiktok/source-register.md` with dated (27 Oct 2026) primary-source checks of TikTok Accounts API v1.3 (`https://business-api.tiktok.com/portal/docs/accounts-api-overview/v1.3`), Owned-Video Comments & Webhooks (`doc_id=1736271785207810`, `doc_id=1751617884206210`), Content Posting API (`https://developers.tiktok.com/products/content-posting-api/`), Developer Guidelines, Scopes Overview, and TikTok Commercial Disclosure Policy.
  - Created `research/tiktok/capability-matrix.csv` classifying all 12 provider capabilities across `VERIFIED_ACTIVE`, `AWAITING_APPROVAL`, `UNAVAILABLE`, and `UNKNOWN`.
  - Created `research/tiktok/approval-checklist.md` providing a plain-English, step-by-step owner guide for the mandatory **March 20, 2026 TikTok Accounts API Access Application**.
- **Architecture & Provider Contracts (`docs/` & `design/tiktok/`):**
  - Created `docs/api-matrix-tiktok.md` with comprehensive endpoint mappings, HTTP methods, scopes, rate limits, and fallback behaviors.
  - Created `docs/provider-contracts/tiktok.md` defining the provider-neutral interface contract, idempotency semantics (`RECONCILE_PENDING`), error taxonomy, and security invariants.
  - Created `docs/TIKTOK_APPLICATION_EVIDENCE.md` containing the ready-to-submit application justification packet, privacy/data-handling declarations, and screen-recording script for TikTok app review.
  - Created `design/tiktok/sequence-diagrams.md` with Mermaid sequence diagrams for OAuth PKCE + Scope Inspection, Signed Webhook Ingestion + Idempotent Owned-Comment Reply, and Fail-Closed Downgrade on `401`/`403`/`429`.
- **Production TikTok Integration Package (`apps/backend/integrations/tiktok/`):**
  - Implemented zero-external-dependency Python 3.9+ package (`__init__.py`, `models.py`, `webhook.py`, `adapter.py`, `tiktok-capabilities.json`).
  - Implemented all 12 provider-neutral methods (`get_owned_posts`, `list_owned_comments`, `reply_to_owned_comment`, `create_comment_on_owned_post`, `subscribe_to_webhooks`, `refresh_auth`, `get_post_publication_status`, `publish_post`, `get_owned_profile`, `get_inbox_messages`, `get_following_posts`, `comment_on_nonowned_post`).
  - Enforced `TIKTOK_WRITE_ENABLED=false` default, outbound host allowlist (`business-api.tiktok.com`, `open.tiktokapis.com`), constant-time HMAC-SHA256 webhook signature verification + timestamp replay defense, 429 `Retry-After` + jittered backoff (`30s/60s/120s`), 5xx circuit breaker, and 401/403 fail-closed transition to `DRAFT` / `READ_ONLY`.
  - Hard-blocked `comment_on_nonowned_post` and `get_following_posts` with `PermissionPolicyError`.
- **Verification & Live Access Truth Report (`reports/` & `tests/tiktok/`):**
  - Created `reports/tiktok-live-access-proof.md` documenting truthful current status (`AWAITING_APPROVAL` / `DRAFT_ONLY` for live credentials, `VERIFIED_ACTIVE` in deterministic sandbox mode).
  - Created `tests/tiktok/test_tiktok_adapter.py` covering webhook signature/replay verification, scope allowlist enforcement, `TIKTOK_WRITE_ENABLED=false` guard, forbidden third-party commenting block, rate-limit backoff & circuit breaker, 401/403 auto-downgrade to `DRAFT`, and sandbox comment read/reply flow.
