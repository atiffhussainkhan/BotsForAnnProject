# MASTER ARCHITECTURAL & GOVERNANCE DECISIONS LOG

**Project:** Ann Reveals AI Manager (`ARAIM` v4.0)
**Lead Integrator:** Autonomous Software Architect

| Decision ID | Date | Decision Summary | Rationale & Official Source Basis |
|---|---|---|---|
| `DEC-001` | 2026-10-27 | **Modular Monolith Cloud Deployment (`< £30/mo`)** | A single containerised Python web + worker service with SQLite/Postgres persistence keeps monthly hosting at ~£5.50–£7.00/mo (well below the £30/mo ceiling) and avoids distributed microservices complexity for a single-owner application. |
| `DEC-002` | 2026-10-27 | **Zero-Dependency Core Domain Modules (Python 3.9+ Stdlib + Optional FastAPI/Gemini Adapters)** | Building all 5 specialist engines (TikTok adapter, Instagram adapter, AI classifier/reply engine, Provenance/UK Compliance engine, SRE/Security/Kill-Switch/Backup ops) with clean standard-library Python + SQLite persistence guarantees 100% deterministic offline/CI execution and zero dependency bitrot, while exposing a full HTTP REST API and pluggable Gemini Flash integration. |
| `DEC-003` | 2026-10-27 | **Instagram API with Instagram Login as Primary Meta Route** | Allows `@annreveals` (Creator/Business account) to grant `instagram_business_basic` and `instagram_business_manage_comments` without needing to create and link a Facebook Page first. |
| `DEC-004` | 2026-10-27 | **Truthful TikTok Accounts API Gate (`AWAITING_APPROVAL` Default)** | Per TikTok's 20 March 2026 policy (`SRC-TT-01`), comment management requires a dedicated TikTok Accounts API Access Application. `TIKTOK_WRITE_ENABLED` defaults to `false` (`Awaiting review — Draft only`) until granted and live-tested. |
| `DEC-005` | 2026-10-27 | **Two-Axis Provenance vs Commercial Disclosure Engine** | Per UK ASA Influencer Guide (23 Oct 2026, `SRC-UK-01`), buying a perfume with personal funds (`SELF_PURCHASED`) does not exempt a post from `Ad` disclosure if an affiliate link, promo code, or TikTok Shop tag is used. Both axes are evaluated independently per platform. |
| `DEC-006` | 2026-10-27 | **Strict `Experian` vs `Empyrean` Merchant Isolation** | Raw retailer labels (`merchant_label_raw`) are preserved verbatim. `Experian` is never mapped to `experian.com` (credit bureau) and only normalizes to `Empyrean Parfums` after explicit `owner_verified=True` confirmation. |
