# Instagram Live Access & Contract Verification Proof Report

**Report Date:** 27 October 2026  
**Prepared By:** Agent Bravo (Agent 2 — Meta/Instagram Developer Platform & Integrations Specialist)  
**Target Account:** `@annreveals`  
**Current Truthful Live Status:** `Not connected` (`Awaiting owner OAuth connection` / `DRAFT_ONLY`)  
**Default Feature Flags:** `INSTAGRAM_WRITE_ENABLED=false`, `THIRD_PARTY_AUTOCOMMENT=false`

---

## 1. Truthful Live Connection Status Declaration (`FR-043`)

In strict compliance with `PRD.md` Section 1 ("Strict Account-Safety & Honesty Rules") and `FR-043`:
- **Live Meta OAuth Connection:** `Not connected` (`Awaiting owner OAuth connection`). No live `@annreveals` access token or Meta App Secret is stored in the repository.
- **Current Operating Mode:** `DRAFT` (`INSTAGRAM_WRITE_ENABLED=false`).
- **Third-Party Auto-Comment Mode:** Permanently `DISABLED` (`THIRD_PARTY_AUTOCOMMENT=false`).

| Capability | Code Readiness | Live Status for `@annreveals` | Active Fallback Until Connected / Approved |
| :--- | :--- | :--- | :--- |
| **Profile & Owned Posts Read (`instagram_business_basic`)** | 100% Implemented & Contract-Tested | `Awaiting owner OAuth connection` | Manual post URL & metadata entry in Dual-Platform Content Studio |
| **Owned Post Comment Ingestion (`instagram_business_manage_comments`)** | 100% Implemented (`X-Hub-Signature-256` Webhook + Polling Reconciler) | `Awaiting owner OAuth connection` | Sandbox simulation & manual comment review |
| **Owned Comment Auto-Reply (`POST /{ig-comment-id}/replies`)** | 100% Implemented (with Self-Reply Guard + `RECONCILE_PENDING`) | `DRAFT_ONLY` (`INSTAGRAM_WRITE_ENABLED=false`) | AI generates reply drafts in Inbox; One-Tap Copy & Open Permalink |
| **First-Party Ownership Comment (`POST /{ig-media-id}/comments`)** | 100% Implemented (with Anti-Spam Uniqueness Guard `FR-055`) | `DRAFT_ONLY` (`INSTAGRAM_WRITE_ENABLED=false`) | First-comment candidate generated in Content Studio with One-Tap Copy |
| **Creator Network Engagement (`comment_on_nonowned_post`)** | Permanently Blocked (`UnsupportedCapabilityError`) | Permanently Disabled (Unsupported by Meta API) | Owner-in-the-loop notification + 2–4 draft comments + One-Tap Copy & Open Instagram |

---

## 2. Automated Contract & Safety Verification Evidence

All safety and protocol invariants are verified deterministically via `python3 -m unittest discover -s tests/instagram`:

1. **`test_webhook_hmac_sha256_verification`:** Verifies valid `X-Hub-Signature-256` headers pass and tampered payloads or wrong secrets raise `WebhookVerificationError` (HTTP `401`).
2. **`test_webhook_subscription_challenge`:** Verifies `hub.mode=subscribe` + matching `hub.verify_token` returns `(200, hub.challenge)` and invalid tokens return `403`.
3. **`test_self_reply_loop_prevention`:** Verifies that comments authored by `@annreveals` (matching `owner_ig_user_id` or `username="annreveals"`) are filtered out during webhook ingestion (`is_self=True`) and raise `SelfReplyForbiddenError` if passed to `reply_to_owned_comment()`.
4. **`test_timeout_reconciliation_prevents_duplicate_replies`:** Simulates a network timeout on `POST /{ig-comment-id}/replies` (`RECONCILE_PENDING`), followed by a retry where `GET /{ig-comment-id}/replies` shows the comment actually landed on Instagram—proving the adapter transitions to `SENT_RECONCILED` without issuing a second `POST`.
5. **`test_forbidden_nonowned_post_commenting_and_following_feed`:** Confirms `comment_on_nonowned_post()` and `get_following_posts()` unconditionally raise `UnsupportedCapabilityError`.
6. **`test_401_403_token_revocation_fail_safe`:** Simulates HTTP `401` / `403` (Meta OAuth error code `190` / `10`) and proves the adapter immediately transitions `connection_status` to `Needs reconnect` (`NEEDS_RECONNECT`), downgrades `automation_mode` to `DRAFT`, and sets `write_enabled=False`.
7. **`test_sandbox_comment_read_and_reply_flow`:** Verifies end-to-end profile read, owned post listing, comment listing, write-gate enforcement (`INSTAGRAM_WRITE_ENABLED=false` blocks writes), and sandbox reply creation once write gate is enabled.
