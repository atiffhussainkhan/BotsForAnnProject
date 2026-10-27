# Agent Echo (Agent 5) — Platform Architecture, Security, SRE & QA Workspace

Welcome to the **Agent Echo** workspace for **Ann Reveals AI Manager (`ARAIM` v4.0)**.

## Responsibilities & Delivered Modules

1. **Core Platform Operations (`apps/backend/platform_ops/`)**
   - [`security.py`](file:///Users/mac/Downloads/bots%20for%20ann/apps/backend/platform_ops/security.py): Authenticated envelope encryption at rest (`ARAIM-ENC-V1`), OAuth 2.0 PKCE (`S256`) & state management, CSRF protection, RBAC owner verification, and secret-scrubbing log sanitizer.
   - [`kill_switch.py`](file:///Users/mac/Downloads/bots%20for%20ann/apps/backend/platform_ops/kill_switch.py): Universal `EMERGENCY STOP` kill-switch + per-platform `OFF` / `OBSERVE` / `DRAFT` / `SAFE_AUTO` / `PAUSED_BY_SYSTEM` state machine with immediate queue drain to `DRAFT`.
   - [`budget_guard.py`](file:///Users/mac/Downloads/bots%20for%20ann/apps/backend/platform_ops/budget_guard.py): Hard £30.00/month total budget ceiling (£5.00/month AI sub-cap + £7.00/month hosting), per-1,000-reply cost estimator, and automatic `DRAFT`/template downgrade.
   - [`idempotency.py`](file:///Users/mac/Downloads/bots%20for%20ann/apps/backend/platform_ops/idempotency.py): Durable deduplication (`platform + account_id + comment_id + event_version`), per-thread concurrency lock, `RECONCILE_PENDING` state, dead-letter queue, and 10,000-event duplicate replay filter.
   - [`gdpr.py`](file:///Users/mac/Downloads/bots%20for%20ann/apps/backend/platform_ops/gdpr.py): UK GDPR PII redaction, retention cleanup, access audit log, full JSON/ZIP owner export, and right-to-erasure wipe.
   - [`backup_manager.py`](file:///Users/mac/Downloads/bots%20for%20ann/apps/backend/platform_ops/backup_manager.py): Encrypted point-in-time snapshot backup, SHA-256 manifest verification, and tested restore with tamper/corruption detection.
   - [`health.py`](file:///Users/mac/Downloads/bots%20for%20ann/apps/backend/platform_ops/health.py): Uptime, p50/p95 webhook latency, zero duplicate outbound counter, zero false self-purchase claim counter, and chaos failure drill simulator.

2. **Architecture & ADRs (`design/architecture/`)**
   - [`component-diagrams.md`](file:///Users/mac/Downloads/bots%20for%20ann/design/architecture/component-diagrams.md)
   - [`ADR-001-modular-monolith-cloud.md`](file:///Users/mac/Downloads/bots%20for%20ann/design/architecture/decision-records/ADR-001-modular-monolith-cloud.md)
   - [`ADR-002-encryption-and-oauth.md`](file:///Users/mac/Downloads/bots%20for%20ann/design/architecture/decision-records/ADR-002-encryption-and-oauth.md)
   - [`ADR-003-idempotency-and-killswitch.md`](file:///Users/mac/Downloads/bots%20for%20ann/design/architecture/decision-records/ADR-003-idempotency-and-killswitch.md)

3. **Security, SRE Runbook & Owner Manual (`docs/`)**
   - [`SECURITY_PRIVACY.md`](file:///Users/mac/Downloads/bots%20for%20ann/docs/SECURITY_PRIVACY.md)
   - [`RUNBOOK.md`](file:///Users/mac/Downloads/bots%20for%20ann/docs/RUNBOOK.md)
   - [`OWNER_GUIDE.md`](file:///Users/mac/Downloads/bots%20for%20ann/docs/OWNER_GUIDE.md)

4. **Cloud Deployment, Backup Scripts & CI/CD**
   - [`docker-compose.yml`](file:///Users/mac/Downloads/bots%20for%20ann/docker-compose.yml), [`.env.example`](file:///Users/mac/Downloads/bots%20for%20ann/.env.example), [`infra/docker/Dockerfile`](file:///Users/mac/Downloads/bots%20for%20ann/infra/docker/Dockerfile), [`infra/deploy/render.yaml`](file:///Users/mac/Downloads/bots%20for%20ann/infra/deploy/render.yaml), [`infra/deploy/fly.toml`](file:///Users/mac/Downloads/bots%20for%20ann/infra/deploy/fly.toml), [`infra/monitoring/alerts.yml`](file:///Users/mac/Downloads/bots%20for%20ann/infra/monitoring/alerts.yml), [`.github/workflows/ci.yml`](file:///Users/mac/Downloads/bots%20for%20ann/.github/workflows/ci.yml), [`scripts/backup.py`](file:///Users/mac/Downloads/bots%20for%20ann/scripts/backup.py), [`scripts/restore.py`](file:///Users/mac/Downloads/bots%20for%20ann/scripts/restore.py).

5. **Verification & Assurance Reports (`reports/` & `tests/platform/`)**
   - [`reports/security-assessment.md`](file:///Users/mac/Downloads/bots%20for%20ann/reports/security-assessment.md)
   - [`reports/reliability-drills.md`](file:///Users/mac/Downloads/bots%20for%20ann/reports/reliability-drills.md)
   - [`reports/cost-forecast.md`](file:///Users/mac/Downloads/bots%20for%20ann/reports/cost-forecast.md)
   - [`reports/release-readiness.md`](file:///Users/mac/Downloads/bots%20for%20ann/reports/release-readiness.md)
   - [`tests/platform/test_platform_sre.py`](file:///Users/mac/Downloads/bots%20for%20ann/tests/platform/test_platform_sre.py)

## Running Tests

```bash
python3 -m unittest discover -s tests/platform -p "test_*.py" -v
```
