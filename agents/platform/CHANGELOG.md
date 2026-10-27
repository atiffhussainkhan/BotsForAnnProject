# Agent Echo (Agent 5) — Changelog

All notable platform, security, SRE, deployment, and QA changes for **Ann Reveals AI Manager (`ARAIM` v4.0)**.

## [4.0.0] — 2026-10-27

### Added
- **Platform Operations (`apps/backend/platform_ops/`)**:
  - `security.py`: Authenticated envelope encryption (`ARAIM-ENC-V1`) with PBKDF2-HMAC-SHA256 key derivation, keystream encryption, and constant-time HMAC-SHA256 authentication tag verification; OAuth 2.0 PKCE (`S256`) `code_verifier`/`code_challenge` and cryptographic `state` generator; CSRF token signing/validation; RBAC owner verification; log secret redaction filter.
  - `kill_switch.py`: Universal `EMERGENCY STOP` kill-switch and per-platform state machine (`OFF`, `OBSERVE`, `DRAFT`, `SAFE_AUTO`, `PAUSED_BY_SYSTEM`) with instant outbound queue draining to `DRAFT` and automatic downgrade on 401/403/rate-limit/policy anomalies.
  - `budget_guard.py`: Hard £30.00/month total budget ceiling with configurable £5.00/month AI token sub-cap and £7.00/month hosting allocation, per-1,000-reply cost estimator, and automatic fallback to deterministic templates / `DRAFT` mode.
  - `idempotency.py`: Durable event deduplication (`platform + account_id + comment_id + event_version`), self-reply loop prevention, per-thread concurrency lock, `RECONCILE_PENDING` timeout state, dead-letter queue (DLQ), and 10,000-event duplicate replay filter.
  - `gdpr.py`: UK GDPR PII redaction engine (payment card PANs, UK postcodes/addresses, email addresses, phone numbers, invoice tokens), configurable retention policy cleanup, immutable access audit log, full JSON/ZIP vendor-exit export, and cryptographic right-to-erasure wipe.
  - `backup_manager.py`: Encrypted point-in-time snapshot backup generator, SHA-256 manifest verification, and corruption-detecting restore engine.
  - `health.py`: Real-time service health monitor tracking 99.5% uptime target, p50/p95 webhook latency, duplicate outbound count (`0`), false self-purchase claim count (`0`), and deterministic chaos failure drill simulator (`429`, `401`, `5xx`, `db_degraded`).
- **Architecture & ADRs (`design/architecture/`)**:
  - `component-diagrams.md`: C4 & Mermaid component, sequence, and deployment diagrams.
  - `ADR-001-modular-monolith-cloud.md`, `ADR-002-encryption-and-oauth.md`, `ADR-003-idempotency-and-killswitch.md`.
- **Infrastructure, CI/CD & Operational Scripts**:
  - `docker-compose.yml`, `.env.example`, `infra/docker/Dockerfile`, `infra/deploy/render.yaml`, `infra/deploy/fly.toml`, `infra/monitoring/alerts.yml`, `.github/workflows/ci.yml`, `scripts/backup.py`, and `scripts/restore.py`.
- **Documentation & Reports**:
  - `docs/SECURITY_PRIVACY.md`, `docs/RUNBOOK.md`, and `docs/OWNER_GUIDE.md` (with 2-page plain-English Quick Start, Reconnect Guide, Emergency Stop Guide, Receipt Upload Guide, TikTok Refusal Fallback Guide, Billing/Retention Policy, and Vendor Exit Export Guide).
  - `reports/security-assessment.md`, `reports/reliability-drills.md`, `reports/cost-forecast.md`, and `reports/release-readiness.md`.
- **Verification & Stress Test Suite (`tests/platform/test_platform_sre.py`)**:
  - 10,000-event duplicate webhook replay stress test verifying 0 duplicate dispatches.
  - Universal Emergency Stop queue drain test.
  - Budget cap auto-downgrade to `DRAFT` verification.
  - OAuth token envelope encryption/decryption and byte-tamper rejection test.
  - Encrypted backup and point-in-time restore roundtrip verification.
  - Chaos failure drills (`429`, `401`, `5xx`, `db_degraded`).
