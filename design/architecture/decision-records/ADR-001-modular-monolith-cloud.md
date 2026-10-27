# ADR-001: Cloud-Hosted Modular Monolith Architecture Under £30/Month Ceiling

- **Status:** Accepted
- **Date:** 27 October 2026
- **Author:** Agent Echo (Agent 5 — Principal Platform Architect)
- **Requirements Addressed:** `FR-039`, `FR-040`, `FR-042`, `FR-044`, `FR-050`, `NFR-01`, `NFR-07`

---

## 1. Context

Ann (`@annreveals`) needs a unified, always-available cloud system that manages TikTok and Instagram comments, tracks friend creator posts, verifies perfume purchase receipts (`Empyrean`/`Experian` and other retailers), generates dual-platform compliant content packages, and tracks enforcement appeals.

Crucially:
1. The system must not depend on an always-on home laptop, local terminal commands, or complex multi-cluster Kubernetes orchestration (`FR-042`).
2. Total monthly infrastructure + AI token + storage spend must remain strictly under **£30.00/month**, with target routine operating cost around **£12.00–£16.00/month** (`FR-039`, `FR-050`).
3. Availability target is **99.5%** (`NFR-01`).

## 2. Decision

We adopt a **Single-Container Cloud Modular Monolith with Embedded Background Worker** deployed to Render (`render.yaml`) or Fly.io (`fly.toml`), serving both the REST API / Webhook ingestion endpoints and the installable 9-screen Mobile-First Progressive Web App (PWA).

Key structural boundaries inside the modular monolith:
- `apps/backend/platform_ops/`: Security, Envelope Encryption, Kill-Switch, Budget Guard, Idempotency, GDPR, Encrypted Backups, Health & Chaos Drills (Agent Echo).
- `apps/backend/adapters/tiktok/` & `apps/backend/adapters/instagram/`: Official OAuth + Webhook + Capability adapters (Agents Alpha & Bravo).
- `apps/backend/ai/` & `apps/backend/creators/`: Brand voice, 14-category classifier, 1,000+ template seed library, and Friends Watchlist (Agent Charlie).
- `apps/backend/vault/` & `apps/backend/compliance/`: Verified Purchases Vault, UK ASA/CMA dual-axis disclosure engine, and Appeals tracker (Agent Delta).
- `apps/web/`: Zero-CLI mobile-responsive PWA frontend with 44px touch targets and truthful status badges.

## 3. Consequences

### Positive
- **Predictable Low Cost:** Runs comfortably on a single £5.50–£7.00/month cloud instance with persistent volume or managed database, leaving ample headroom beneath the £30.00/month hard cap.
- **Zero Distributed Transaction Complexity:** Outbound comment idempotency locks, kill-switch state transitions, and audit logs execute ACID transactions against the same local/managed database without cross-service network partitions.
- **Simple Disaster Recovery:** A single encrypted snapshot (`scripts/backup.py`) captures database tables, redacted receipt proofs, encrypted OAuth grants, and SHA-256 verification manifests (`FR-044`).

### Negative / Mitigations
- **Single-Instance Contention Risk:** A surge of webhook events could compete with UI requests.
  - *Mitigation:* Webhook receivers validate HMAC signatures, deduplicate via `IdempotencyStore` in `<2ms`, enqueue work, and return HTTP `200 OK` immediately.
