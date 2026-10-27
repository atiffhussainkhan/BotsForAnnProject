# MASTER DEVELOPMENT PLAN & FIVE-AGENT EXECUTION BOARD

**Project:** Ann Reveals AI Manager (`ARAIM` v4.0)
**Repository:** `https://github.com/atiffhussainkhan/BotsForAnnProject`
**Execution Mode:** Five Concurrent Native Specialist Agents + Lead Architect/Integrator

---

## 1. Native Five-Agent Capability Confirmation

In accordance with Section A0 & Final Launch Command #2 of the v4.0 Contract:
- **Environment Confirmation:** This Gemini Antigravity environment **supports concurrent native subagents** (`define_subagent` / `invoke_subagent`).
- **Active Native Subagent Sessions Launched:**
  1. **Agent Alpha (`agent-alpha-tiktok`)** — Conversation ID: `abc43102-5781-4bc6-a72b-8889d610810f`
  2. **Agent Bravo (`agent-bravo-instagram`)** — Conversation ID: `68dae923-b02e-45b9-9948-51b108bc0e1d`
  3. **Agent Charlie (`agent-charlie-ai`)** — Conversation ID: `d98c67ee-179b-4496-a6cb-05d2aea8e944`
  4. **Agent Delta (`agent-delta-compliance`)** — Conversation ID: `0dc72435-7c1e-44d6-972e-cd927a1b6a08`
  5. **Agent Echo (`agent-echo-platform`)** — Conversation ID: `cee55f23-9787-4266-b46f-61fc3d80f125`

---

## 2. Five-Agent Ownership & Boundary Matrix

| Agent | Role Title | Owned Directories | Primary Deliverables | Adversarial Review Assignment |
|---|---|---|---|---|
| **Agent Alpha (Agent 1)** | Official TikTok Platform Access, Policy & Integration Specialist | `agents/tiktok/`, `research/tiktok/`, `design/tiktok/`, `apps/backend/integrations/tiktok/`, `tests/tiktok/` | TikTok Accounts API v1.3 matrix, March 20, 2026 access application pack, signed webhook verifier, rate-limit/backoff adapter, contract tests | Reviews Agent Delta for TikTok commercial disclosure & Shop rules |
| **Agent Bravo (Agent 2)** | Meta / Instagram Developer Platform & Integrations Specialist | `agents/instagram/`, `research/instagram/`, `design/instagram/`, `apps/backend/integrations/instagram/`, `tests/instagram/` | Instagram Login vs Facebook Login audit, `instagram_business_manage_comments` adapter, `X-Hub-Signature-256` verifier, timeout reconciliation, contract tests | Reviews Agent Charlie for Instagram reply loop & DM safety |
| **Agent Charlie (Agent 3)** | Autonomous Conversational Intelligence, Creator-Network & Content Studio Specialist | `agents/ai-engagement/`, `research/ai/`, `design/ai/`, `apps/backend/ai/`, `apps/backend/creator_assistant/`, `tests/ai/` | Ann Reveals soft-luxury UK voice engine, 14-class classifier, 1,200+ reply variation catalog, grounded fragrance KB, prompt-injection shield, Creator Watchlist assistant | Reviews UI copy & user-friendliness across all screens |
| **Agent Delta (Agent 4)** | Purchase Evidence, UK Advertising Compliance, Dual-Platform Preflight & Appeals Specialist | `agents/content-integrity/`, `research/compliance/`, `design/evidence/`, `apps/backend/provenance/`, `apps/backend/compliance/`, `apps/backend/appeals/`, `tests/compliance/` | Encrypted Evidence Vault, PII redactor, `Experian`/`Empyrean` normalizer, 2-axis provenance vs commercial disclosure engine (UK ASA/CAP + Meta + TikTok), 10 mandatory scenarios, 30 receipt tests, Appeals packet builder | Reviews all public disclosure & self-purchase wording |
| **Agent Echo (Agent 5)** | Principal Platform Architect, Security Engineer, SRE & QA Specialist | `agents/platform/`, `design/architecture/`, `apps/backend/platform_ops/`, `infra/`, `scripts/`, `tests/platform/` | Envelope encryption, universal Emergency Stop kill-switch, £30/mo budget guard, 10,000-event idempotency engine, UK GDPR export/wipe, encrypted backup/restore, Docker/PaaS IaC, CI/CD | Reviews system architecture, privacy, resilience & release gates |
| **Lead Integrator** | Autonomous Software Architect & Release Controller | `docs/`, `backend/`, `apps/web/`, `tests/e2e/` | Unified FastAPI + SQLite/Postgres persistence layer, REST API gateway, responsive soft-luxury Ann Reveals PWA (all 9 screens), cross-agent integration, E2E verification, GitHub commits | Signs off all 8 Cross-Agent Quality Gates |

---

## 3. Phased Execution & Quality Gates (G0 – G7)

1. **Gate 0 (Research & Capability Audit — Complete):** Primary-source audit of TikTok Accounts API (March 20, 2026 rule), Meta Instagram Login API, UK ASA/CAP Influencer Guide (23 Oct 2026), cost forecast (`<= £30/mo`), and full FR/NFR traceability matrix.
2. **Gate 1 (Offline Integrated System & 10,000-Event Stress Test):** Unified backend, database schema, all 5 specialist modules integrated, 10,000 duplicate webhook injection test (`0` duplicates), 30 fictional receipts test, 10 compliance scenarios, and interactive PWA dashboard.
3. **Gate 2 (Live Instagram Pilot Gate — Ready for Owner Consent):** Guided Setup Wizard OAuth connector + 1 controlled test reply on `@annreveals` owned post once owner connects Instagram Tester account.
4. **Gate 3 (Live TikTok Pilot Gate — Ready for Owner Application):** Guided application pack for TikTok's March 20, 2026 Accounts API gate; remains safely in `Awaiting review — Draft only` until TikTok grants `comment.list.manage`.
5. **Gate 4 (Dual-Platform Evidence & UK Compliance Verification):** Sample Case A (Instagram Empyrean self-purchased review) and Sample Case B (TikTok independent + affiliate review) verified end-to-end with full PII redaction.
6. **Gate 5 (Novice Mobile/Laptop UX & 9-Screen PWA Verification):** All 9 screens operational (`Home`, `9-Step Setup Wizard`, `Unified Comments`, `Content Studio`, `Purchases Vault`, `Friends Watchlist`, `Warnings & Appeals`, `Settings & Budget Guard`, `Health/Logs & Owner Guide`).
7. **Gate 6 (Chaos, Failure Drills & Backup/Restore Verification):** Simulated 429/401/5xx, worker crash, token expiry, budget exhaustion, emergency kill-switch, and encrypted backup/restore roundtrip verified by automated tests.
8. **Gate 7 (GitHub Repository Commit, CI Pipeline & Cloud Deployment Handover):** Full codebase, tests, documentation, Docker/Render/Fly.io cloud configs committed and pushed to `https://github.com/atiffhussainkhan/BotsForAnnProject`.
