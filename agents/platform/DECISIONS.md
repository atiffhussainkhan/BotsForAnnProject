# Agent Echo (Agent 5) — Architectural & Engineering Decisions

**Agent:** Agent Echo — Principal Platform Architect, Security Engineer, SRE, and Quality Assurance Specialist  
**Project:** Ann Reveals AI Manager (`ARAIM` v4.0)  
**Date:** 27 October 2026

---

## Decision Log

| ID | Date | Decision | Rationale | Status |
|---|---|---|---|---|
| **ECHO-DEC-001** | 2026-10-27 | **Modular Monolith + Background Worker under £30/mo Cloud Ceiling** | Splitting into microservices exceeds the hard £30.00/month budget ceiling and complicates deployment for a single creator (`@annreveals`). A single containerised Python web + worker runtime backed by SQLite WAL / Managed Postgres delivers 99.5%+ availability for ~£7.00/mo hosting + ≤£5.00/mo AI token budget. | Approved |
| **ECHO-DEC-002** | 2026-10-27 | **Authenticated Envelope Encryption at Rest (PBKDF2-HMAC-SHA256 + Stream Cipher + HMAC-SHA256 Auth Tag)** | OAuth access/refresh tokens and purchase receipts must never be stored in plaintext (`NFR-05`). Using pure-stdlib authenticated envelope encryption (`ARAIM-ENC-V1`) guarantees zero external compilation dependencies while enforcing cryptographic integrity and tamper detection. | Approved |
| **ECHO-DEC-003** | 2026-10-27 | **Universal `EMERGENCY STOP` Kill-Switch & Immediate Queue Drain to `DRAFT`** | To satisfy `FR-010`, `FR-035`, and `NFR-10`, activating the universal kill-switch or receiving a 401/403/policy warning immediately transitions platform mode to `PAUSED_BY_SYSTEM` or `OFF` and drains all pending outbound dispatch items into `DRAFT` status so zero unauthorized comments can leave the system. | Approved |
| **ECHO-DEC-004** | 2026-10-27 | **Composite Idempotency Key (`platform:account_id:comment_id:event_version`) + `RECONCILE_PENDING` State** | Webhook retries from Meta and TikTok frequently overlap. Composite idempotency keys combined with per-thread locks prevent duplicate replies and self-reply loops (`FR-003`, `NFR-03`, `NFR-04`). Network timeouts transition to `RECONCILE_PENDING` rather than blind retries. | Approved |
| **ECHO-DEC-005** | 2026-10-27 | **Hard Monthly Budget Guard (£30.00 Total / £5.00 AI Sub-Cap) with Deterministic Template Fallback** | Protects the owner from surprise LLM or cloud bills (`FR-050`, `NFR-07`). When total spend reaches £30.00 or AI spend reaches £5.00, LLM calls are blocked and the system automatically downgrades to deterministic template drafts (`DRAFT` mode). | Approved |
| **ECHO-DEC-006** | 2026-10-27 | **Zero-CLI Installable Mobile-First PWA with Truthful Status Badges** | The owner operates from an Android phone and laptop browser (`FR-040`, `FR-042`, `FR-043`). Every screen uses ≥44px touch targets, plain-English explanations, and truthful live connection badges (`Not connected`, `Connected: read only`, `Awaiting review`, `Live: can reply`, `Suspended`, `Needs reconnect`). | Approved |
| **ECHO-DEC-007** | 2026-10-27 | **UK GDPR Data Minimisation, Redaction Before Storage, and 1-Click Vendor Exit Export** | Receipt uploads redact payment cards, billing addresses, emails, and phone numbers prior to disk persistence or LLM inspection (`NFR-06`). Full JSON/ZIP export and right-to-erasure wipe prevent vendor lock-in (`FR-044`). | Approved |
