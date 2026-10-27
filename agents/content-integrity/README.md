# Agent Delta (`content-integrity`) — Module Overview & Developer Guide

**Agent:** Agent Delta (Agent 4 — Purchase Evidence, UK Advertising Compliance, Dual-Platform Preflight, and Appeals Specialist)
**Scope:** Requirements C3 (`FR-018`–`FR-028`), C4 (`FR-029`–`FR-033`), C6 (`FR-046`–`FR-048`), C7 (`FR-051`–`FR-058`), and Hard Rules `G1`–`G6`.

---

## 1. Mission Summary

Agent Delta safeguards `@annreveals` against two distinct compliance failure modes on Instagram and TikTok:
1. **False Commercial / Hidden Ad Violations:** Failing to disclose affiliate links, discount codes, TikTok Shop commissions, gifted PR, or paid collaborations with an upfront `Ad` label and native platform toggle, or falsely claiming a self-purchased bottle is `"not an ad"` when an affiliate link or commercial incentive is attached.
2. **Mistaken Moderation & Privacy Leaks:** Having an honest, 100% self-funded perfume review mistakenly flagged as undisclosed branded content without redacted proof ready for appeal—or accidentally leaking payment card numbers, home addresses, or raw order invoices into public comments, LLM prompts, or appeal attachments.

---

## 2. Directory & File Inventory

### Documentation & Design Artifacts
- [`research/compliance/source-register.md`](../../research/compliance/source-register.md) — Authoritative regulatory citations (UK ASA/CAP Influencer’s Guide 23 Oct 2026, CMA guidance, DMCC Act 2024, TikTok April 2026 Commercial Content rules, Meta Paid Partnership policies).
- [`design/evidence/provenance-rules.md`](../../design/evidence/provenance-rules.md) — Data model and verification state machine for the Verified Purchases Vault, PII redaction, and `Experian` vs `Empyrean` disambiguation.
- [`design/evidence/ad-disclosure-decision-table.md`](../../design/evidence/ad-disclosure-decision-table.md) — Complete truth table mapping Provenance × Commercial Relationship × Platform.
- [`docs/DISCLOSURE_POLICY.md`](../../docs/DISCLOSURE_POLICY.md) — Owner-facing plain-English policy handbook.
- [`docs/COMPLIANCE_RULES.md`](../../docs/COMPLIANCE_RULES.md) — Formal specification of Hard Rules G1–G6 and FR compliance matrix.
- [`reports/dual-platform-disclosure-tests.md`](../../reports/dual-platform-disclosure-tests.md) — Test report detailing 10 mandatory compliance scenarios and 30 receipt edge cases.

### Backend Packages (`apps/backend/`)
- **`apps/backend/provenance/`**
  - `redactor.py` (`ReceiptRedactor`, `RedactionResult`): Strips PANs, Luhn card sequences, last-4 card digits, IBANs, UK sort codes, street addresses, UK postcodes, emails, phone numbers, and barcodes/QR payloads.
  - `merchant_normalizer.py` (`MerchantNormalizer`, `NormalizedMerchant`): Preserves `merchant_label_raw` and prevents auto-conflating `"Experian"` with `experian.com` or `"Empyrean Parfums"` without `owner_verified=True`.
  - `matcher.py` (`ReceiptMatcher`, `ReceiptRecord`, `PerfumeItem`, `MatchResult`): Parses receipts and computes multi-factor confidence scores across brand, fragrance name, concentration, size (`ml`), price/refund status, PR sample flags, and purchaser identity.
  - `vault.py` (`VerifiedPurchasesVault`, `PostProvenanceRecord`, `ImmutableEvidenceSnapshot`, `RetroactiveContradictionAlert`): Cross-platform vault managing items, receipts, post links, immutable upload-time snapshots, and FR-058 retroactive contradiction alerts.
- **`apps/backend/compliance/`**
  - `disclosure_engine.py` (`DisclosureEngine`, `ProvenanceStatus`, `CommercialRelationship`, `DisclosureDecision`): Enforces Hard Rules G1–G6 and generates truthful UK ASA + platform-specific disclosure obligations.
  - `preflight.py` (`PreflightChecker`, `PreflightInput`, `PreflightReport`): Runs independent Instagram and TikTok pre-publication compliance checks with advisory `GREEN` / `AMBER` / `RED` grading.
  - `content_studio.py` (`DualPlatformContentStudio`, `ContentStudioRequest`, `DualPlatformPackage`): Produces ready-to-use Instagram and TikTok packages (captions with 5-hashtag default, overlays, cover titles, alt-text, anti-spam ownership comment rotation, and Sample Cases A & B).
- **`apps/backend/appeals/`**
  - `tracker.py` (`AppealsTracker`, `ViolationNotice`, `ViolationCategory`, `AppealCase`, `AppealLifecycleStatus`): Handles violation intake across 9 categories, immediately freezes post automation (`freeze_post_automation`), and tracks manual appeal states.
  - `packet_builder.py` (`AppealPacketBuilder`, `RedactedAppealPacket`): Assembles human-reviewable, PII-redacted appeal evidence bundles.

---

## 3. Running Verification Tests

```bash
python3 -m unittest discover -s tests/compliance -p "test_*.py" -v
```
