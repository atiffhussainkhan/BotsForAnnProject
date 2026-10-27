# Agent Bravo (Instagram) — Changelog

All notable changes produced by **Agent Bravo (Meta/Instagram Developer Platform & Integrations Specialist)** for the Ann Reveals AI Manager (`ARAIM` v4.0) are recorded here.

---

## [4.0.0] — 2026-10-27

### Added
- **Architecture & Governance (`agents/instagram/`):**
  - Created `DECISIONS.md` covering ADR-IG-001 through ADR-IG-004 (Instagram Login selection, non-owned post hard block, `RECONCILE_PENDING` timeout reconciliation, and Meta Branded Content / UK ASA independence).
  - Created `BLOCKERS.md` tracking live external dependencies (`@annreveals` OAuth grant, Meta App ID/Secret provisioning, App Review for Live Mode if non-tester accounts are used).
  - Created `README.md` documenting Agent Bravo module layout, interfaces, and test commands.
- **Official Meta API Research & Evidence (`research/instagram/`, `docs/`):**
  - Created `research/instagram/source-register.md` with dated (27 Oct 2026) verification of Meta Instagram Platform Overview, Comment Moderation, Official Postman Collection, Webhooks, Rate Limits, and Branded Content policies.
  - Created `research/instagram/capability-matrix.csv` mapping every requested capability to official Meta Graph API endpoints, scopes, app modes, and fallback strategies.
  - Created `research/instagram/approval-checklist.md` and `docs/META_PERMISSIONS_EVIDENCE.md` with plain-English setup steps for `@annreveals`, permission justification scripts, and screencast checklists.
  - Created `docs/provider-contracts/instagram.md` defining exact HTTP request/response schemas, error handling codes (`190`, `10`, `200`, `4`, `613`, `368`), pagination cursors, and webhook envelopes.
- **System Design (`design/instagram/sequence-diagrams.md`):**
  - Authored Mermaid sequence diagrams for OAuth + Scope Verification, `X-Hub-Signature-256` Webhook Verification + Comment Threading, and Safe Auto-Reply with Ambiguous Timeout Reconciliation (`RECONCILE_PENDING`).
- **Production Instagram Adapter (`apps/backend/integrations/instagram/`):**
  - Implemented zero-external-dependency Python 3.9+ package (`__init__.py`, `models.py`, `webhook.py`, `adapter.py`, `instagram-capabilities.json`).
  - Implemented HMAC-SHA256 `X-Hub-Signature-256` verification using constant-time `hmac.compare_digest` and `hub.challenge` verification.
  - Implemented full provider-neutral contract (`get_owned_profile`, `get_owned_posts`, `list_owned_comments`, `reply_to_owned_comment`, `create_comment_on_owned_post`, `subscribe_to_webhooks`, `refresh_auth`, `get_post_publication_status`, `publish_post`, `get_inbox_messages`, `get_following_posts`, `comment_on_nonowned_post`).
  - Enforced `INSTAGRAM_WRITE_ENABLED=false` default, self-reply loop prevention, comment event deduplication, timeout reconciliation (`RECONCILE_PENDING`), rate-limit Retry-After backoff, and 401/403 automatic downgrade to `NEEDS_RECONNECT` + `DRAFT`.
- **Verification & Live Access Truthfulness (`reports/instagram-live-access-proof.md`, `tests/instagram/test_instagram_adapter.py`):**
  - Added comprehensive contract unit test suite covering webhook signature verification, hub challenge, self-reply loop guard, timeout reconciliation preventing duplicate replies, forbidden third-party commenting, 401/403 revocation fail-safe, and sandbox read/reply flow.
