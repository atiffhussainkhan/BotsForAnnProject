# Agent Bravo — Meta / Instagram Developer Platform & Integrations

Welcome to the **Agent Bravo** workspace for the **Ann Reveals AI Manager (`ARAIM` v4.0)**.

Agent Bravo owns the official Meta / Instagram Platform integration for `@annreveals`, including OAuth 2.0 token lifecycle (`Instagram API with Instagram Login`), `X-Hub-Signature-256` webhook verification, owned-post & comment ingestion, safe auto-reply dispatch with `RECONCILE_PENDING` timeout reconciliation, first-party ownership comments, and Meta Branded Content / Paid Partnership policy rules.

---

## Directory & Artifact Map

| Path | Purpose |
| :--- | :--- |
| [`agents/instagram/DECISIONS.md`](file:///Users/mac/Downloads/bots%20for%20ann/agents/instagram/DECISIONS.md) | Architectural Decision Records (ADR-IG-001 to ADR-IG-004) |
| [`agents/instagram/BLOCKERS.md`](file:///Users/mac/Downloads/bots%20for%20ann/agents/instagram/BLOCKERS.md) | External dependency register & fail-closed fallbacks |
| [`agents/instagram/CHANGELOG.md`](file:///Users/mac/Downloads/bots%20for%20ann/agents/instagram/CHANGELOG.md) | Chronological log of Agent Bravo deliverables |
| [`research/instagram/source-register.md`](file:///Users/mac/Downloads/bots%20for%20ann/research/instagram/source-register.md) | Dated (27 Oct 2026) audit of official Meta Developer & Branded Content documentation |
| [`research/instagram/capability-matrix.csv`](file:///Users/mac/Downloads/bots%20for%20ann/research/instagram/capability-matrix.csv) | Machine-readable matrix of endpoints, scopes, app modes, and fallbacks |
| [`research/instagram/approval-checklist.md`](file:///Users/mac/Downloads/bots%20for%20ann/research/instagram/approval-checklist.md) | Step-by-step plain-English onboarding & Meta App Review guide for `@annreveals` |
| [`docs/META_PERMISSIONS_EVIDENCE.md`](file:///Users/mac/Downloads/bots%20for%20ann/docs/META_PERMISSIONS_EVIDENCE.md) | Complete Meta permissions evidence dossier, scope justification, and compliance mapping |
| [`docs/provider-contracts/instagram.md`](file:///Users/mac/Downloads/bots%20for%20ann/docs/provider-contracts/instagram.md) | Exact HTTP contract specification for Graph API v21.0+ endpoints, webhooks, and error codes |
| [`design/instagram/sequence-diagrams.md`](file:///Users/mac/Downloads/bots%20for%20ann/design/instagram/sequence-diagrams.md) | Mermaid sequence diagrams for OAuth, Webhook HMAC verification, and `RECONCILE_PENDING` recovery |
| [`apps/backend/integrations/instagram/`](file:///Users/mac/Downloads/bots%20for%20ann/apps/backend/integrations/instagram/__init__.py) | Production Python 3.9+ standard-library Instagram adapter, webhook verifier, models, and capabilities JSON |
| [`reports/instagram-live-access-proof.md`](file:///Users/mac/Downloads/bots%20for%20ann/reports/instagram-live-access-proof.md) | Truthful live-access readiness report (`Awaiting owner OAuth connection` / `DRAFT_ONLY`) |
| [`tests/instagram/test_instagram_adapter.py`](file:///Users/mac/Downloads/bots%20for%20ann/tests/instagram/test_instagram_adapter.py) | Contract & safety unit tests runnable via `python3 -m unittest discover -s tests/instagram` |

---

## Running Contract & Safety Tests

All Instagram integration code uses pure Python 3.9+ standard library modules (`hmac`, `hashlib`, `json`, `time`, `urllib.request`, `dataclasses`, `typing`, `enum`) and requires zero third-party packages to test:

```bash
python3 -m unittest discover -s tests/instagram -v
```

---

## Core Safety Guarantees

1. **Zero Unauthorized Automation:** Never uses scraping, browser automation, session cookies, or private mobile APIs.
2. **Write Gate Disabled by Default:** `INSTAGRAM_WRITE_ENABLED=false` by default until live scope inspection confirms `instagram_business_manage_comments` and the owner enables writes.
3. **Permanent Third-Party Block:** `comment_on_nonowned_post` and `get_following_posts` are permanently blocked (`UnsupportedCapabilityError`).
4. **Loop Prevention:** Comments authored by `@annreveals` (matching `owner_ig_user_id` or `owner_username`) are never replied to.
5. **Ambiguous Timeout Reconciliation:** Any network timeout during `POST /{ig-comment-id}/replies` or `POST /{ig-media-id}/comments` marks the attempt `RECONCILE_PENDING` and queries existing replies before retrying, eliminating duplicate comments.
6. **Fail-Closed on Auth Errors:** HTTP `401` / `403` or OAuth error code `190` / `10` / `200` immediately transitions the connection status to `NEEDS_RECONNECT` and downgrades automation mode to `DRAFT`.
