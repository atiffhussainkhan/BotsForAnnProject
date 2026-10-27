# Agent Delta (`content-integrity`) — Changelog

All notable changes implemented by **Agent Delta (Agent 4 — Purchase Evidence, UK Advertising Compliance, Dual-Platform Preflight, and Appeals Specialist)** are documented in this file.

## [4.0.0] — 2026-10-27

### Added
- **Compliance Research & Policy Documentation:**
  - `research/compliance/source-register.md`: Annotated regulatory register covering the UK ASA/CAP Influencer’s Guide (updated 23 October 2026), CMA *Hidden Advertising / Greenwashing & Endorsements* guidance, DMCC Act 2024 unfair commercial practices provisions, TikTok Commercial Content Disclosure Policy (updated April 2026) & TikTok Shop Creator Rules, and Meta Instagram Branded Content / Paid Partnership policies.
  - `design/evidence/provenance-rules.md`: Architecture specification for the Cross-Platform Verified Purchases Vault, PII redaction patterns, `Experian` vs `Empyrean` disambiguation state machine, SKU fuzzy matcher, and FR-058 retroactive contradiction guard.
  - `design/evidence/ad-disclosure-decision-table.md`: Complete two-axis decision matrix mapping `ProvenanceStatus` × `CommercialRelationship` × `Platform` to required UK ASA labels, platform toggles, allowed purchase wording, and preflight risk grades.
  - `docs/DISCLOSURE_POLICY.md`: Plain-English owner disclosure handbook for `@annreveals`.
  - `docs/COMPLIANCE_RULES.md`: Formal engineering specification of Hard Rules G1–G6 and FR-018 through FR-033, FR-047, and FR-051 through FR-058.
- **Provenance & Verified Purchases Vault (`apps/backend/provenance/`):**
  - `redactor.py`: Deterministic PII and financial data scrubber masking PAN/Luhn card numbers, explicit last-4 card markers, UK sort codes, IBANs, billing/street addresses, UK postcodes, email addresses, phone numbers, invoice/order barcodes, and QR payloads prior to storage or LLM inspection.
  - `merchant_normalizer.py`: Preserves `merchant_label_raw` alongside canonical merchant fields and implements the explicit `Experian` vs `Empyrean Parfums` safety gate (never conflating `Experian` with `experian.com`).
  - `matcher.py`: Perfume receipt parser and fuzzy matcher scoring brand, product name, concentration (`EDP`, `EDT`, `Extrait`, `Parfum`), size (`ml`), price/refund anomalies, PR samples, and purchaser email mismatches.
  - `vault.py`: Unified cross-platform `VerifiedPurchasesVault` with SHA-256 evidence hashing, duplicate order detection, immutable post snapshots (FR-028/FR-057), and retroactive contradiction protection (FR-058).
- **Dual-Platform Compliance & Content Studio (`apps/backend/compliance/`):**
  - `disclosure_engine.py`: Two-axis evaluation engine enforcing Hard Rules G1–G6 across Instagram and TikTok.
  - `preflight.py`: Independent Instagram and TikTok pre-publication compliance checklists with `GREEN` / `AMBER` / `RED` advisory grading (FR-023, FR-027, FR-056).
  - `content_studio.py`: Single-upload Dual-Platform Content Studio generating compliant captions (default 5 hashtags), on-screen text, cover titles, alt-text, anti-spam ownership comment rotation (FR-055), native toggle instructions, and pre-built Sample Case A (Instagram) and Sample Case B (TikTok).
- **Enforcement Intake & Redacted Appeal Packet Builder (`apps/backend/appeals/`):**
  - `tracker.py`: Violation intake across all 9 taxonomy categories (FR-030), root-cause analysis without false certainty (FR-031), automatic per-post automation freeze (`freeze_post_automation`, Rule G6), and lifecycle state machine (`CREATED` -> `DRAFTED` -> `SUBMITTED_BY_USER` -> `PENDING` -> `OUTCOME_RECORDED` -> `FOLLOW_UP_DUE`).
  - `packet_builder.py`: Generates human-reviewable, PII-redacted appeal packets linking immutable vault snapshots, SHA-256 hashes, UK ASA / platform policy citations, and owner sign-off blocks.
- **Verification & Test Suite:**
  - `reports/dual-platform-disclosure-tests.md`: Full verification report covering all 10 mandatory compliance scenarios and 30 receipt edge cases.
  - `tests/compliance/test_provenance_and_compliance.py`: Comprehensive `unittest` suite exercising all 10 compliance scenarios, 30 receipt edge cases, PII redaction, `Experian` vs `Empyrean` guard, retroactive contradiction guard, and appeal packet generation.
