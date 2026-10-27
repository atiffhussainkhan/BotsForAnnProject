# Ann Reveals AI Manager (`ARAIM` v4.0)

**Autonomous Engagement, Verified Purchase Provenance & UK Advertising Compliance Cloud Application for `@annreveals`**

> **Delivery Model:** One unified, beginner-friendly, cloud-hosted Progressive Web Application (PWA) accessible from an Android phone and laptop browser without requiring an always-on home laptop, local Python/Docker commands, or routine terminal usage during everyday operation.

---

## 1. Architecture & Five Specialist Agent Workstreams

This repository was researched, architected, implemented, and tested by **five concurrent specialist engineering agents** coordinated by the Lead Autonomous Software Architect:

1. **Agent Alpha (`agents/tiktok/`, `apps/backend/integrations/tiktok/`):** Official TikTok Accounts API v1.3 specialist, March 20, 2026 Accounts API access application pack, `TikTok-Signature` HMAC-SHA256 webhook verifier, rate-limit backoff & circuit breaker, and contract tests.
2. **Agent Bravo (`agents/instagram/`, `apps/backend/integrations/instagram/`):** Official Meta *Instagram API with Instagram Login* specialist (`instagram_business_manage_comments`), `X-Hub-Signature-256` webhook verifier, self-reply loop prevention, `RECONCILE_PENDING` timeout reconciliation, and contract tests.
3. **Agent Charlie (`agents/ai-engagement/`, `apps/backend/ai/`, `apps/backend/creator_assistant/`):** Ann Reveals sincere UK English soft-luxury voice engine, 14-category comment classifier, 1,584-variation reply catalog with near-duplicate suppression, grounded fragrance knowledge base (explicitly distinguishing measured vs unmeasured wear-time), prompt-injection guard, and Creator Watchlist assistant.
4. **Agent Delta (`agents/content-integrity/`, `apps/backend/provenance/`, `apps/backend/compliance/`, `apps/backend/appeals/`):** Cross-platform Verified Purchases Vault, deterministic PII/payment card/address redactor, `Experian` vs `Empyrean Parfums` merchant disambiguation guard, two-axis Provenance vs Commercial Relationship engine (UK ASA 23 Oct 2026 + Meta Branded Content + TikTok Commercial Content Disclosure), Single-Upload Dual-Platform Content Studio, FR-058 retroactive contradiction guard, and Rule G6 Violation Freeze & Redacted Appeal Packet Builder.
5. **Agent Echo (`agents/platform/`, `apps/backend/platform_ops/`, `infra/`, `scripts/`):** `ARAIM-ENC-V1` authenticated envelope encryption, Universal `EMERGENCY STOP` kill-switch, hard £30.00/month `BudgetGuard` (£5.00/mo AI sub-cap with automatic zero-cost template fallback), 10,000-event idempotency deduplication store, UK GDPR export/erasure manager, encrypted snapshot backup & point-in-time restore verifier, and SRE chaos drill runner.

---

## 2. Truthful Live Permission & Feature Flag State

| Feature Flag / Capability | Default Value | Current Status | Requirement to Enable Live Auto-Publishing |
|---|---|---|---|
| `INSTAGRAM_WRITE_ENABLED` | `false` | `Awaiting review` (`DRAFT` mode) | Connect `@annreveals` Professional Account via Step 3 of the Setup Wizard (`instagram_business_manage_comments`) & pass 1 controlled live reply test |
| `TIKTOK_WRITE_ENABLED` | `false` | `Awaiting review` (`DRAFT` mode) | Approval of TikTok's post-20 March 2026 **Accounts API Access Application** (`docs/TIKTOK_APPLICATION_EVIDENCE.md`) + OAuth consent & 1 live reply test |
| `THIRD_PARTY_AUTOCOMMENT` | `false` | `UNAVAILABLE` (Hard Blocked) | Permanently disabled per platform terms; Friends & Creator Watchlist uses notification + 2–4 contextual drafts + 1-tap Copy & Open Native App |
| **Cloud Dashboard, AI Engine, Receipt Vault, Dual-Platform Studio & Appeals** | `ACTIVE` | **100% Operational & Verified** | Runs immediately in local or cloud deployment with zero external API blockers |

---

## 3. Reproducible Commands (Startup, Testing, Backup, Restore & Emergency Stop)

### Start the Unified Cloud Web Application Locally or in Container
```bash
python3 backend/main.py
# Opens at http://127.0.0.1:8080 (or $PORT in cloud PaaS)
```

### Run the Complete Automated Verification Suite (52 Tests Across All 5 Agents + E2E)
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

### Trigger Universal Emergency Stop via API (or Click the Red Header Button in UI)
```bash
curl -X POST http://127.0.0.1:8080/api/v1/kill-switch/emergency-stop \
  -H "Content-Type: application/json" \
  -d '{"activate": true, "reason": "Manual operator emergency halt"}'
```

### Create Encrypted Backup & Verify Point-in-Time Restore
```bash
python3 scripts/backup.py --source-dir ./data --output ./data/backups/latest.enc.json
python3 scripts/restore.py --backup-file ./data/backups/latest.enc.json --target-dir ./data/restore_verify --dry-run
```

---

## 4. Key Documentation Index

- [`docs/PRD.md`](docs/PRD.md) — Master v4.0 Product Requirements Document
- [`docs/TRACEABILITY_MATRIX.md`](docs/TRACEABILITY_MATRIX.md) — Complete `FR-001..FR-058` & `NFR-01..NFR-10` mapping table
- [`docs/ACCESS_READINESS.md`](docs/ACCESS_READINESS.md) — Phase 0 Access Readiness & Owner OAuth Checklist
- [`docs/API_CAPABILITY_MATRIX.md`](docs/API_CAPABILITY_MATRIX.md) — Living Official Endpoint & Scope Register
- [`docs/TIKTOK_APPLICATION_EVIDENCE.md`](docs/TIKTOK_APPLICATION_EVIDENCE.md) — Ready-to-submit March 20, 2026 TikTok Accounts API Application Pack
- [`docs/META_PERMISSIONS_EVIDENCE.md`](docs/META_PERMISSIONS_EVIDENCE.md) — Meta Instagram Login Setup & Permission Guide
- [`docs/DISCLOSURE_POLICY.md`](docs/DISCLOSURE_POLICY.md) & [`docs/COMPLIANCE_RULES.md`](docs/COMPLIANCE_RULES.md) — UK ASA (23 Oct 2026), Meta & TikTok Disclosure Rules
- [`docs/SECURITY_PRIVACY.md`](docs/SECURITY_PRIVACY.md) — Threat Model, Encryption & UK GDPR Controls
- [`docs/OWNER_GUIDE.md`](docs/OWNER_GUIDE.md) — Plain-English Illustrated Owner Manual & Quick Start
- [`docs/RUNBOOK.md`](docs/RUNBOOK.md) — SRE Operations, Rollback & Disaster Recovery Runbook
- [`docs/COST_ESTIMATE.md`](docs/COST_ESTIMATE.md) — Transparent Monthly Budget Model (`£6.85/mo` estimated vs `£30.00/mo` hard ceiling)
- [`docs/FIVE_AGENT_COMPLETION_MATRIX.md`](docs/FIVE_AGENT_COMPLETION_MATRIX.md) — Signed Five-Agent Completion & Adversarial Review Ledger
