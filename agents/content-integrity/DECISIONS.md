# Agent Delta (`content-integrity`) — Architectural & Compliance Decisions

**Agent:** Agent Delta (Agent 4 — Purchase Evidence, UK Advertising Compliance, Dual-Platform Preflight, and Appeals Specialist)
**Version:** 4.0.0
**Date:** 27 October 2026
**Project:** Ann Reveals AI Manager (`ARAIM`)

---

## ADR-D01: Two-Axis Separation of Acquisition Provenance vs. Commercial Relationship (Rule G1 & FR-021)
- **Context:** Creators frequently assume that buying a perfume with their own money (`SELF_PURCHASED`) automatically makes any post about that bottle "not an ad." Under UK ASA/CAP and CMA guidance, as well as TikTok and Meta branded content policies, a self-purchased product promoted alongside an affiliate link, discount/promo code, TikTok Shop commission tag, paid brand amplification, or own-brand promotion is still commercial advertising.
- **Decision:** Model acquisition provenance (`ProvenanceStatus`: `SELF_PURCHASED`, `PR_GIFTED`, `LOANED`, `FREE_SAMPLE`, `UNKNOWN`) and commercial relationship (`CommercialRelationship`: `NONE`, `AFFILIATE_LINK`, `PROMO_CODE`, `PAID_PARTNERSHIP`, `TIKTOK_SHOP`, `GIFTED_INCENTIVE`, `OWN_BRAND`) as strictly orthogonal axes.
- **Consequence:** Even when `ProvenanceStatus == SELF_PURCHASED` is backed by a verified SHA-256 receipt in the Vault, any non-`NONE` commercial relationship triggers mandatory upfront UK ASA disclosure (`Ad`) and platform-native commercial disclosure toggles. The system is hard-coded (Rule G2) never to output `"not an ad"` or `"no commercial relationship"` when any commercial incentive exists.

## ADR-D02: Raw vs. Canonical Merchant Normalization — The `Experian` vs. `Empyrean` Guard (FR-019 & FR-051)
- **Context:** The owner (`@annreveals`) mentioned purchasing perfumes from `"Experian"` or `"Empyrean"` (likely referring to *Empyrean Parfums* or an automated speech-to-text/OCR transcription of *Empyrean* as *Experian*). However, `experian.com` is a major consumer credit reporting agency, not a fragrance retailer.
- **Decision:** Every receipt and vault entry preserves `merchant_label_raw` exactly as OCR'd or typed by the owner alongside `normalized_name`, `normalized_domain`, `category`, and `owner_verified`.
- **Consequence:**
  - When `merchant_label_raw` is `"Experian"` and `owner_verified=False`, the normalizer flags `AMBIGUOUS_MERCHANT_EXPERIAN_EMPYREAN`, refuses to assign `experian.com` as a perfume store domain, and holds canonical normalization at `UNVERIFIED_MERCHANT` until the owner explicitly confirms whether the receipt is from Empyrean Parfums (`owner_verified=True`).
  - Only after explicit owner confirmation is `normalized_name` mapped to `"Empyrean Parfums"` while permanently retaining `merchant_label_raw="Experian"` in the audit trail.

## ADR-D03: Zero-Trust Pre-Storage & Pre-LLM PII Redaction Pipeline (FR-019, NFR-05, NFR-06)
- **Context:** Order confirmations, PDF invoices, and receipt screenshots contain sensitive personal data under UK GDPR: Primary Account Numbers (PANs), last-4 card digits, UK sort codes, IBANs, billing/delivery street addresses, UK postcodes, email addresses, phone numbers, and raw invoice/tracking barcodes or QR codes.
- **Decision:** All receipt text passes through `ReceiptRedactor` synchronously **before** database persistence, LLM prompt construction, or Appeal Packet export.
- **Consequence:** Public captions, comments, and appeal packets never expose raw order IDs, payment card data, home addresses, or unredacted receipts. Only a cryptographic SHA-256 hash of the raw artifact (`proof_sha256`) and a redacted summary are stored in completed content packages.

## ADR-D04: Retroactive Receipt Contradiction Guard (FR-058)
- **Context:** A receipt might be uploaded or updated days after a video has already been published (e.g., an email refund notice arrives, or a corrected invoice reveals the item was a free PR sample rather than self-purchased).
- **Decision:** Published post provenance snapshots (`ImmutableEvidenceSnapshot`) are write-once. If a newly ingested or updated receipt in `VerifiedPurchasesVault` contradicts an already-published post's provenance or SKU claims, the vault raises a `RetroactiveContradictionAlert` rather than silently mutating historical post records.
- **Consequence:** Preserves audit integrity and alerts the owner to manually review or update the live post caption/toggle if required.

## ADR-D05: Advisory-Only Preflight Risk Grading (`GREEN` / `AMBER` / `RED`) & Anti-Spam Ownership Comment Guard (FR-025, FR-027, FR-055)
- **Context:** Social platforms (TikTok and Instagram) enforce proprietary, evolving moderation classifiers. Furthermore, posting identical robot-like comments ("I bought this with my own money, not an ad!") on every single video triggers platform spam heuristics and looks defensive.
- **Decision:**
  1. Preflight checks output `GREEN`, `AMBER`, or `RED` advisory risk assessments with specific rule citations, explicitly disclaiming any guarantee of platform reach or immunity from moderation.
  2. First-party ownership comments are disabled by default (`include_ownership_comment=False`), rotated across diverse natural UK-English phrasing templates when enabled, blocked from repeating across consecutive posts, and suppressed whenever a commercial disclosure is already in the caption.

## ADR-D06: Immediate Automation Freeze on Enforcement Notice Intake (Rule G6 & FR-029–FR-033)
- **Context:** If TikTok or Instagram flags a video for branded content, unoriginality, or spam, continuing to auto-reply to comments on that post risks compounding account penalties.
- **Decision:** Ingesting any violation notice in `AppealsTracker` immediately invokes `freeze_post_automation(platform, platform_post_id)` to lock that post to `MANUAL_REVIEW_ONLY` (`OFF`), halts queued comment replies for that post, and builds a human-reviewable, PII-redacted appeal packet requiring explicit owner sign-off (`SUBMITTED_BY_USER`). Zero automated appeal ticket submission is permitted.
