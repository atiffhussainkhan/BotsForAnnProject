# Dual-Platform Compliance Scenarios & 30 Receipt Edge Cases Verification Report

**Project:** Ann Reveals AI Manager (`ARAIM` v4.0)
**Agent:** Agent Delta (Agent 4 — Purchase Evidence, UK Advertising Compliance, Dual-Platform Preflight, and Appeals Specialist)
**Date:** 27 October 2026
**Test Suite:** [`tests/compliance/test_provenance_and_compliance.py`](../tests/compliance/test_provenance_and_compliance.py)

---

## 1. Executive Summary

- **Total Mandatory Compliance Scenarios Tested:** **10 / 10 PASS**
- **Total Fictional Receipt Edge Cases Tested:** **30 / 30 PASS**
- **PII Redaction & Zero-Leakage Checks:** **PASS** (PANs, Luhn cards, last-4 digits, IBANs, UK sort codes, bank accounts, billing/street addresses, UK postcodes, emails, phone numbers, barcodes/QR payloads, and raw order IDs stripped before storage, LLM prompts, or appeal packet export).
- **`Experian` vs `Empyrean` Disambiguation Guard:** **PASS** (`merchant_label_raw` preserved; `"Experian"` is never mapped to `experian.com` and requires explicit `owner_verified=True` before resolving to `"Empyrean Parfums"`).
- **Retroactive Receipt Contradiction Guard (`FR-058`):** **PASS** (Published `ImmutableEvidenceSnapshot` records are never silently mutated when a subsequent refund or conflicting receipt arrives; a high-priority `RetroactiveContradictionAlert` is raised).
- **Enforcement Intake, Automation Freeze & Redacted Appeal Packet (`Rule G6`):** **PASS** (All 9 violation taxonomy categories supported; `freeze_post_automation` immediately locks flagged posts; human sign-off required).

---

## 2. Ten Mandatory Dual-Platform Compliance Scenarios

| # | Scenario Name | Platform | Provenance Axis | Commercial Axis | Upfront `Ad \|` Required? | Native Toggle | Expected Preflight Grade | Key Rule Verified |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **S-01** | Verified Self-Purchase (Sample Case A) | Instagram | `SELF_PURCHASED` (`VERIFIED_SELF_PURCHASE`) | `NONE` | `False` | `OFF` | `GREEN` | FR-022, FR-054: Truthful self-purchase wording; Paid Partnership OFF |
| **S-02** | Verified Self-Purchase (Sample Case B) | TikTok | `SELF_PURCHASED` (`VERIFIED_SELF_PURCHASE`) | `NONE` | `False` | `OFF` | `GREEN` | Rule G5: Never tell TikTok an independent self-purchase is paid content |
| **S-03** | Self-Purchased + Affiliate Link (`"not an ad"` blocked) | TikTok & Instagram | `SELF_PURCHASED` (`VERIFIED_SELF_PURCHASE`) | `AFFILIATE_LINK` | `True` (`Ad \|`) | `ON` | `GREEN` (Valid) / `RED` (if `"not an ad"` used) | Rule G1 & G2: Self-purchase never erases affiliate disclosure; `"not an ad"` hard-blocked |
| **S-04** | Self-Purchased + TikTok Shop Anchor + Pop Music Check | TikTok | `SELF_PURCHASED` (`VERIFIED_SELF_PURCHASE`) | `TIKTOK_SHOP` | `True` (`Ad \|`) | `ON` | `RED` (with pop music) / `GREEN` (with CML/Original) | Rule G1, FR-056: TikTok Shop requires `Ad \|`, toggle ON, and CML/Original audio |
| **S-05** | Self-Purchased + Viewer Discount Code (`ANN10`) | Instagram | `SELF_PURCHASED` (`VERIFIED_SELF_PURCHASE`) | `PROMO_CODE` | `True` (`Ad \|`) | `ON` | `GREEN` | Rule G1, UK ASA CAP 2.1: Creator promo code triggers upfront `Ad \|` + toggle |
| **S-06** | Gifted PR Bottle (`#gifted` alone vs upfront `Ad \|`) | Instagram | `PR_GIFTED` | `GIFTED_INCENTIVE` | `True` (`Ad \|`) | `ON` | `RED` (`#gifted` only) / `GREEN` (`Ad \|`) | Rule G3: Standalone `#gifted` or `#pr` without upfront `Ad` is rejected |
| **S-07** | Paid Brand Partnership with Missing Native Toggle | TikTok | `PR_GIFTED` | `PAID_PARTNERSHIP` | `True` (`Ad \|`) | `ON` (Tested with `OFF` -> `RED`) | `RED` (when toggle OFF) | FR-026: Missing native platform commercial toggle blocks preflight |
| **S-08** | Unverified Self-Purchase (`"Experian"` Unconfirmed) | Instagram | `SELF_PURCHASED` (`UNVERIFIED`) | `NONE` | `False` | `OFF` | `AMBER` | FR-019, FR-051: Holds Verified Purchase badge until `"Experian"` confirmed |
| **S-09** | Conflicted Vault Receipt (Refunded / £0 PR Slip) | TikTok | `SELF_PURCHASED` (`CONFLICTED`) | `NONE` | `False` | `OFF` | `RED` | FR-020: Blocks `"Purchased with my own money"` when receipt is refunded/£0 PR |
| **S-10** | Account-Wide `"Never Accept Gifts"` Claim & Comment Spam Guard | Dual | `SELF_PURCHASED` (`VERIFIED_SELF_PURCHASE`) | `NONE` | `False` | `OFF` | `RED` (on account-wide claim) | Rule G4 & G5, FR-055: Blocks account-wide absolutes; rotates optional comments |

---

## 3. Thirty Fictional Receipt Edge Cases Matrix

| Case ID | Category | Raw Merchant Label | Product & Size on Receipt | Target Item Size | Price / Notes | Expected Vault Status | Key Discrepancy / Warning Verified |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RC-01** | Correct | `Empyrean Parfums` | Celestial Iris Extrait 100ml | 100ml | £195.00 paid | `VERIFIED_SELF_PURCHASE` | Full match + SHA-256 hash |
| **RC-02** | Correct | `Selfridges & Co` | Parfums de Marly Delina EDP 75ml | 75ml | £255.00 paid (Visa PAN redacted) | `VERIFIED_SELF_PURCHASE` | Full match + PAN & postcode redacted |
| **RC-03** | Correct | `Harrods Knightsbridge` | Baccarat Rouge 540 EDP 70ml | 70ml | £245.00 paid (Last-4 redacted) | `VERIFIED_SELF_PURCHASE` | Full match + Card Last-4 redacted |
| **RC-04** | Correct | `Liberty London` | Byredo Mojave Ghost EDP 100ml | 100ml | £210.00 paid (IBAN/Sort redacted) | `VERIFIED_SELF_PURCHASE` | Full match + IBAN & sort code redacted |
| **RC-05** | Correct | `Les Senteurs` | Diptyque Orpheon EDP 75ml | 75ml | £160.00 paid (QR/Barcode redacted) | `VERIFIED_SELF_PURCHASE` | Full match + Barcode & phone redacted |
| **RC-06** | Correct (Verified Alias) | `Experian` (`owner_verified=True`) | Celestial Iris Extrait 100ml | 100ml | £195.00 paid | `VERIFIED_SELF_PURCHASE` | `merchant_label_raw="Experian"` preserved; resolved to `Empyrean Parfums` |
| **RC-07** | Wrong Size | `Empyrean Parfums` | Celestial Iris Extrait **50ml** | 100ml | £135.00 paid | `UNVERIFIED` | `SIZE_MISMATCH` (50ml vs 100ml) |
| **RC-08** | Wrong Size | `Selfridges` | Parfums de Marly Delina EDP **10ml** | 75ml | £42.00 paid | `UNVERIFIED` | `SIZE_MISMATCH` (10ml travel spray vs 75ml) |
| **RC-09** | Wrong Size | `Jo Malone London` | Wood Sage & Sea Salt EDC **30ml** | 100ml | £56.00 paid | `UNVERIFIED` | `SIZE_MISMATCH` (30ml vs 100ml) |
| **RC-10** | Refunded | `Empyrean Parfums` | Celestial Iris Extrait 100ml | 100ml | £195.00 `FULL REFUND` | `CONFLICTED` | `REFUNDED_OR_CANCELLED_ORDER` |
| **RC-11** | Refunded / Cancelled | `Selfridges` | Parfums de Marly Delina EDP 75ml | 75ml | `ORDER CANCELLED` | `CONFLICTED` | `REFUNDED_OR_CANCELLED_ORDER` |
| **RC-12** | Refunded / Chargeback | `Harrods` | Baccarat Rouge 540 EDP 70ml | 70ml | `PAYMENT REVERSED / CHARGEBACK` | `CONFLICTED` | `REFUNDED_OR_CANCELLED_ORDER` |
| **RC-13** | PR Free | `Empyrean Parfums` | Celestial Iris Extrait 100ml | 100ml | £0.00 `PR SAMPLE - NOT FOR RESALE` | `CONFLICTED` | `FREE_OR_PR_RECEIPT_CONFLICT` |
| **RC-14** | PR Free | `Byredo` | Mojave Ghost EDP 100ml | 100ml | £0.00 `INFLUENCER SEEDING PRESS GIFT` | `CONFLICTED` | `FREE_OR_PR_RECEIPT_CONFLICT` |
| **RC-15** | PR Free (2ml Vial) | `Empyrean Parfums` | Celestial Iris Extrait **2ml GWP Sample** | 100ml | £0.00 `COMPLIMENTARY 2ML` | `CONFLICTED` | `SAMPLE_VIAL_MISMATCH` |
| **RC-16** | Discounted | `Empyrean Parfums` | Celestial Iris Extrait 100ml | 100ml | £195 - £19.50 (`VIP10`) = £175.50 | `VERIFIED_SELF_PURCHASE` | `DISCOUNT_APPLIED_ON_RECEIPT` warning recorded |
| **RC-17** | Discounted | `Selfridges` | Parfums de Marly Delina EDP 75ml | 75ml | £255 - £51.00 (`BF20`) = £204.00 | `VERIFIED_SELF_PURCHASE` | `DISCOUNT_APPLIED_ON_RECEIPT` warning recorded |
| **RC-18** | Discounted (100% Voucher) | `Empyrean Parfums` | Celestial Iris Extrait 100ml | 100ml | £195 - £195 (`PRESS100`) = £0.00 | `UNVERIFIED` | `ZERO_NET_PAID_WITH_VOUCHER` (net paid £0) |
| **RC-19** | Affiliate Metadata | `Empyrean Parfums` | Celestial Iris Extrait 100ml | 100ml | £195.00 + `LTK tracking` | `VERIFIED_SELF_PURCHASE` | `AFFILIATE_METADATA_ON_RECEIPT` warning |
| **RC-20** | Affiliate Metadata | `Les Senteurs` | Diptyque Orpheon EDP 75ml | 75ml | £160.00 + `ShopMy commission` | `VERIFIED_SELF_PURCHASE` | `AFFILIATE_METADATA_ON_RECEIPT` warning |
| **RC-21** | Affiliate Metadata | `Liberty London` | Byredo Mojave Ghost EDP 100ml | 100ml | £210.00 + `TikTok Shop affiliate` | `VERIFIED_SELF_PURCHASE` | `AFFILIATE_METADATA_ON_RECEIPT` warning |
| **RC-22** | No Proof | N/A (`receipt=None`) | No receipt uploaded | 100ml | N/A | `UNVERIFIED` | `NO_PROOF_UPLOADED` (`confidence=0.0`) |
| **RC-23** | No Proof (Blank OCR) | `""` (Missing merchant) | Blank / unreadable OCR text | 100ml | £0.00 | `UNVERIFIED` | `MISSING_MERCHANT_LABEL` + `PRODUCT_MISMATCH` |
| **RC-24** | Duplicated Order | `Empyrean Parfums` | Celestial Iris Extrait 100ml | 100ml | Reused `ORD-EMP-99001` | `CONFLICTED` | `DUPLICATE_ORDER_REF` (`is_duplicate_order=True`) |
| **RC-25** | Duplicated Order | `Selfridges` | Parfums de Marly Delina EDP 75ml | 75ml | Reused `INV-SLF-77412` | `CONFLICTED` | `DUPLICATE_ORDER_REF` (`is_duplicate_order=True`) |
| **RC-26** | Mismatched Email | `Empyrean Parfums` | Celestial Iris Extrait 100ml | 100ml | Buyer: `stranger99@yahoo.co.uk` | `CONFLICTED` | `MISMATCHED_PURCHASER_EMAIL` |
| **RC-27** | Mismatched Email | `Harrods` | Baccarat Rouge 540 EDP 70ml | 70ml | Buyer: `seeding@pr-agency.co.uk` | `CONFLICTED` | `MISMATCHED_PURCHASER_EMAIL` |
| **RC-28** | Unknown / `Experian` | `Experian` (`owner_verified=False`) | Celestial Iris Extrait 100ml | 100ml | £195.00 paid | `UNVERIFIED` | `AMBIGUOUS_MERCHANT_EXPERIAN_EMPYREAN` (`domain=None`) |
| **RC-29** | Unknown / `Experian UK` | `Experian UK` (`owner_verified=False`) | Celestial Iris Extrait 100ml | 100ml | £195.00 paid | `UNVERIFIED` | `AMBIGUOUS_MERCHANT_EXPERIAN_EMPYREAN` (`domain=None`) |
| **RC-30** | Unknown Merchant | `Mystery Bazaar Perfumes Ltd` | Celestial Iris Extrait 100ml | 100ml | £195.00 paid (`owner_verified=False`) | `UNVERIFIED` | `UNRECOGNIZED_MERCHANT` |
