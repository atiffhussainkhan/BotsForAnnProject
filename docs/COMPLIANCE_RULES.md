# Ann Reveals AI Manager (v4.0) — Compliance Engineering Rules (G1–G6 & FR Matrix)

**Document ID:** `ARAIM-COMP-RULES-v4.0`
**Owner:** Agent Delta (`content-integrity`)
**Regulatory Baseline:** UK ASA/CAP Influencer Guide (23 Oct 2026), CMA / DMCC Act 2024, TikTok Commercial Content Policy (Apr 2026), Meta Branded Content Policy.

---

## 1. Mandatory Hard Rules (`G1`–`G6`)

### Rule G1 — Orthogonal Provenance & Commercial Relationship Evaluation
- Acquisition provenance (`SELF_PURCHASED`, `PR_GIFTED`, `LOANED`, `FREE_SAMPLE`, `UNKNOWN`) and commercial relationship (`NONE`, `AFFILIATE_LINK`, `PROMO_CODE`, `PAID_PARTNERSHIP`, `TIKTOK_SHOP`, `GIFTED_INCENTIVE`, `OWN_BRAND`) must be stored, evaluated, and audited as independent dimensions.
- `SELF_PURCHASED` status—even when backed by a SHA-256 verified receipt—**never** overrides or suppresses disclosure obligations triggered by `AFFILIATE_LINK`, `PROMO_CODE`, `PAID_PARTNERSHIP`, `TIKTOK_SHOP`, `GIFTED_INCENTIVE`, or `OWN_BRAND`.

### Rule G2 — Prohibition on False Non-Commercial Claims (`"Not an Ad"`)
- The system must **never** generate, suggest, or approve `"not an ad"`, `"not sponsored"`, `"unsponsored"`, or `"no commercial link"` when any commercial relationship (`!= NONE`) or gifted/PR incentive exists.
- Even on pure self-purchases (`SELF_PURCHASED` + `NONE`), default approved copy uses positive factual provenance (`"Purchased with my own money. These are my personal impressions."`) rather than defensive `"not an ad"` phrasing that can trigger keyword moderation filters.

### Rule G3 — UK ASA Upfront `Ad` Prominence Standard
- Whenever a commercial relationship or PR/gifted incentive applies, the generated caption must begin with `Ad |` (or `Ad —`) at the very start of the text (prior to any truncation fold) **in addition to** instructing the user to enable the platform's native disclosure toggle.
- Standalone labels such as `#gifted`, `#pr`, `#aff`, `#collab`, or `Spon` without an upfront `Ad` label are rejected by `PreflightChecker` with risk grade `RED`.

### Rule G4 — Per-Item Scope Only (No Account-Wide Absolutes)
- All provenance statements must be scoped strictly to the featured item(s) in the post (`"I bought this perfume myself"`).
- The system blocks account-wide absolutes such as `"I never accept PR"`, `"Everything on my page is bought by me"`, or `"This account is 100% ad-free"`.

### Rule G5 — Anti-Spam Ownership Comment Guard & Toggle Honesty
- First-party ownership comments (`FR-025`, `FR-055`) are optional, disabled by default, rotated across distinct phrasing templates so two consecutive posts never share identical wording, and suppressed whenever `CommercialRelationship != NONE` or write permissions are disabled.
- Never instruct the creator to enable TikTok's `Disclose video content` toggle or Instagram's `Paid partnership` label when a post is genuinely `SELF_PURCHASED` with `CommercialRelationship == NONE`.

### Rule G6 — Immediate Automation Freeze & Human-Signed Redacted Appeals
- Upon intake of any platform enforcement/violation notice (`FR-029`–`FR-033`), the system immediately freezes automated comment replies and outbound mutations for the affected `platform_post_id` (`freeze_post_automation`).
- Appeal packets must strip all PII/card/address data (`ReceiptRedactor`), distinguish provenance evidence from non-provenance flags (e.g., copyright music or unoriginal video), and require explicit human sign-off (`SUBMITTED_BY_USER`) with zero automated ticket flooding.

---

## 2. Requirements Traceability Matrix (`FR-018`–`FR-033`, `FR-047`, `FR-051`–`FR-058`)

| Requirement | Module Implementation | Verification Test |
| :--- | :--- | :--- |
| **FR-018** Perfume item library | `apps/backend/provenance/matcher.py` (`PerfumeItem`), `vault.py` | `test_01_vault_and_item_library` |
| **FR-019** `Empyrean`/`Experian` raw preservation & PII redaction | `apps/backend/provenance/redactor.py`, `merchant_normalizer.py` | `test_02_pii_redactor`, `test_03_experian_empyrean_guard` |
| **FR-020** Multi-item post linking & fuzzy confidence score | `apps/backend/provenance/matcher.py` (`ReceiptMatcher`), `vault.py` | `test_04_thirty_receipt_edge_cases` |
| **FR-021** Two-axis provenance vs commercial model | `apps/backend/compliance/disclosure_engine.py` | `test_05_ten_mandatory_compliance_scenarios` |
| **FR-022** Truthful public copy & `"not an ad"` prohibition | `apps/backend/compliance/disclosure_engine.py`, `content_studio.py` | `test_05_ten_mandatory_compliance_scenarios` |
| **FR-023** Pre-publication content checklist | `apps/backend/compliance/preflight.py` (`PreflightChecker`) | `test_06_preflight_checklist_and_grading` |
| **FR-024** Compliant captions (5 hashtags default), overlays, covers | `apps/backend/compliance/content_studio.py` (`DualPlatformContentStudio`) | `test_07_dual_platform_content_studio_and_samples` |
| **FR-025 / FR-055** Non-repetitive optional ownership comment guard | `apps/backend/compliance/content_studio.py` | `test_08_anti_spam_ownership_comment_rotation` |
| **FR-026** Native platform toggle + UK ASA `Ad` prompt | `apps/backend/compliance/disclosure_engine.py`, `preflight.py` | `test_05_ten_mandatory_compliance_scenarios` |
| **FR-027** Advisory `GREEN` / `AMBER` / `RED` preflight risk assessment | `apps/backend/compliance/preflight.py` | `test_06_preflight_checklist_and_grading` |
| **FR-028 / FR-057** Immutable upload snapshot & SHA-256 hash | `apps/backend/provenance/vault.py` (`ImmutableEvidenceSnapshot`) | `test_09_retroactive_receipt_contradiction_guard` |
| **FR-029–FR-033** Violation intake, 9 categories, root-cause, appeals | `apps/backend/appeals/tracker.py`, `packet_builder.py` | `test_10_appeals_intake_freeze_and_redacted_packet` |
| **FR-047** Single-upload Dual-Platform Content Studio | `apps/backend/compliance/content_studio.py` | `test_07_dual_platform_content_studio_and_samples` |
| **FR-051–FR-056** Cross-platform vault, rule citations, platform checks | `apps/backend/provenance/`, `apps/backend/compliance/` | All test suites |
| **FR-058** Retroactive receipt contradiction guard | `apps/backend/provenance/vault.py` (`RetroactiveContradictionAlert`) | `test_09_retroactive_receipt_contradiction_guard` |
