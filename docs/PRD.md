# ANN REVEALS — AUTONOMOUS ENGAGEMENT & CONTENT INTEGRITY SYSTEM (v4.0)
## Master Product Requirements Document (PRD), Technical Architecture, API Approval Gates and Five-Agent Contract

**Version:** 4.0 FINAL — Cloud Manager + Dual-Platform Purchase Verification + Five-Agent Development Contract
**Date:** 27 October 2026
**Project:** Ann Reveals AI Manager (ARAIM)
**Primary social handle:** `@annreveals`
**Repository:** `https://github.com/atiffhussainkhan/BotsForAnnProject`
**Status:** Engineering specification and live implementation contract. NOT an assertion that external TikTok or Meta permissions have already been granted.

---

## 1. Mission & Critical Delivery Contract

- **Product Name:** **Ann Reveals AI Manager** (`ARAIM`).
- **Delivery Model:** One unified, beginner-friendly, cloud-hosted Progressive Web Application (PWA) accessible from the owner's Android phone and laptop browser without requiring an always-on home laptop, local Python/Docker commands, or routine terminal access.
- **Five Specialist Engineering Agents:** Five concurrent engineering subagents (`Agent Alpha — TikTok`, `Agent Bravo — Instagram`, `Agent Charlie — AI & Creator Network`, `Agent Delta — Purchase Proof & UK Compliance`, `Agent Echo — Platform, Security, SRE & UI`) build one unified application.
- **Strict Account-Safety & Honesty Rules:**
  - Never replace denied or pending official API permissions with scraping, browser automation, session/cookie extraction, CAPTCHA bypass, or private mobile APIs.
  - Default feature flags: `TIKTOK_WRITE_ENABLED=false`, `INSTAGRAM_WRITE_ENABLED=false`, `THIRD_PARTY_AUTOCOMMENT=false`.
  - Features requiring ungranted permissions must visibly report `Awaiting approval` or `Draft only`, never `Active`.
  - Acquisition provenance (`SELF_PURCHASED`, `PR_GIFTED`, `LOANED`, `UNKNOWN`) and commercial relationship (`NONE`, `AFFILIATE`, `PAID_COLLAB`, `TIKTOK_SHOP`, `GIFTED_INCENTIVE`) are independent axes. Self-purchase never automatically makes a post non-commercial ("not an ad").
  - Preserve raw merchant names (`Experian` vs `Empyrean`) without assuming `experian.com` is a perfume retailer; normalize only after explicit owner confirmation.
  - Redact all payment card numbers, billing addresses, invoice IDs, and personal PII before storage or LLM inspection; never expose receipts publicly.

---

## 2. Requirements Summary (FR-001 to FR-058 & NFR-01 to NFR-10)

### C1. Own-Video/Post Comment Inbox & Safe Auto-Reply
- **FR-001:** Ingest all legally accessible comments/replies on owned posts via official webhooks + periodic reconciliation.
- **FR-002:** Distinguish top-level comments, replies, owner's own comments, blocked/hidden comments, spam, advertising, repeat commenters, and specialist escalations.
- **FR-003:** Prevent reply loops (never answer self, dedupe by platform + comment ID + event version, enforce per-thread reply policy).
- **FR-004:** Classify into 14 categories: `compliment`, `question`, `product_notes`, `longevity`, `price`, `where_to_buy`, `sensitive_health_skin`, `complaint`, `troll`, `threat`, `explicit_content`, `suspicious_link`, `partnership_request`, `uncertain_other`.
- **FR-005:** Generate Ann Reveals brand-aligned replies (sincere UK English, warm feminine soft-luxury, concise, grounded in verified product notes).
- **FR-006:** Route safe ordinary replies to auto-send ONLY when platform adapter is verified and mode is `SAFE_AUTO`; default to `DRAFT`. Support `OFF` / `DRAFT` / `SAFE_AUTO` per platform.
- **FR-007:** Seed catalog of 1,000+ structured variation templates/taxonomy with semantic diversity and near-duplicate detection.
- **FR-008:** Grounded accuracy for wear-time/longevity, fragrance notes, clone comparisons, and pricing; explicitly state if wear-time has not been measured.
- **FR-009:** Escalate medical/skin reactions, legal issues, harassment, age-restricted claims, defamatory claims, giveaway disputes, financial details, and sponsorship offers.
- **FR-010:** Durable queue, status verification, rate-limit pause, circuit breaker, manual pause switch, and bulk draft-only mode.

### C2. Friends & Creator Engagement Assistant
- **FR-011:** Owner-curated creator shortlist (`handle`, `platform`, `display_name`, `relationship_context`, `post_url`, `close_friend`, `access_route`, `permitted_method`).
- **FR-012:** Detect new content only via lawful authorised feeds, user-submitted/shared URLs, or owner-curated imports (no follow-list scraping).
- **FR-013:** Send notification with creator name, post title/description, link, publish timestamp, and 2–4 contextual draft comments.
- **FR-014:** Owner-in-the-loop manual posting via one-tap copy + open native app where third-party comment publishing API is unavailable.
- **FR-015:** Contextual, non-repetitive draft comments grounded in actual post caption/notes.
- **FR-016:** Optional creator reminders, daily notification caps, snooze controls; zero bulk DMs or automated mass liking/commenting.
- **FR-017:** Gate any future third-party interaction API behind explicit scope verification and owner release gate (disabled in v1).

### C3. Personal Purchases & Content Authenticity
- **FR-018:** Perfume item library (`sku`, `product_name`, `brand`, `variant`, `size_ml`, `concentration`, `store`, `purchase_date`, `private_price`, `currency`, `private_order_ref`, `proof_file_ref`, `confidence`, `status`).
- **FR-019:** Store evidence from `Empyrean`/`Experian` (raw label preserved until verified) and other retailers via PDF/screenshot/receipt upload or consented email import; redact PII/card data.
- **FR-020:** Link videos/posts to one or multiple perfumes with fuzzy match confidence score; low confidence forces human verification.
- **FR-021:** Separate axes for provenance (`SELF_PURCHASED`, `PR_GIFTED`, `PAID_COLLAB`, `AFFILIATE`, `TIKTOK_SHOP`, `LOANED`, `UNKNOWN`) and commercial incentives.
- **FR-022:** Truthful public copy ("I bought this perfume myself and these are my personal impressions" or "Purchased with my own money. These are my personal impressions."); never append "not an ad" when affiliate/commercial links exist.
- **FR-023:** Pre-publication content checklist (visuals, overlays, voiceover, hashtags, metadata, pricing, purchase status, affiliate links, TikTok Shop tags, PR/gifts, music rights, originality, brand claims).
- **FR-024:** Platform-specific compliant caption (with 5 hashtags preference), on-screen copy, cover title, and optional first/pinned comment candidate.
- **FR-025:** Optional non-repetitive first-party ownership comment only when verified and write scope is live.
- **FR-026:** Prompt native platform commercial disclosure toggles + prominent UK ASA `Ad` label when incentives apply.
- **FR-027:** Advisory-only `GREEN` / `AMBER` / `RED` pre-publication risk assessment (never claims guaranteed compliance or reach).
- **FR-028:** Immutable evidence archive snapshot at upload time (checksum, caption, selected disclosures, product link, receipt SHA-256, rule version, timestamp).

### C4. Enforcement & Appeal Support
- **FR-029:** Intake violation screenshots, reference codes, notification text, content IDs, and exported account notices.
- **FR-030:** Violation taxonomy (`commercial_disclosure`, `paid_partnership`, `affiliate_tiktok_shop`, `unoriginal_content`, `copyright_music`, `community_guideline`, `spam_automation`, `recommendation_ineligibility`, `other`).
- **FR-031:** Root-cause analysis without false certainty; distinguish provenance proof from non-provenance policy flags.
- **FR-032:** Assemble human-reviewable appeal packets with timeline, policy version citation, redacted purchase proof, commercial status, factual statement, and owner sign-off.
- **FR-033:** Appeals case lifecycle tracker (`CREATED`, `DRAFTED`, `SUBMITTED_BY_USER`, `PENDING`, `OUTCOME_RECORDED`, `FOLLOW_UP_DUE`) with zero automated ticket flooding.

### C5. Dashboard & User Experience
- **FR-034:** Mobile-friendly owner dashboard showing permissions, API status, lag, replies drafted/sent/failed, comment queue, high-risk escalations, creator alerts, purchases, content checks, violations, and spend.
- **FR-035:** Prominent `OFF` / `DRAFT` / `SAFE_AUTO` switch per platform + universal `EMERGENCY STOP` kill-switch that halts all outgoing writes and queued jobs immediately.
- **FR-036:** Plain-language audit trail (`Comment Received -> Classification -> AI Draft -> Safety/Policy Checks -> API Dispatch/Result -> Permalink`).
- **FR-037:** Editable brand voice & fragrance experience profile (default: Ann Reveals sincere UK English, warm feminine soft luxury).
- **FR-038:** Independent settings and OAuth grants for Instagram and TikTok.

### C6. Managed Cloud Product & Frictionless Onboarding
- **FR-039:** Single branded cloud application (`Ann Reveals AI Manager`) with container/PaaS deployment under £30/month target ceiling.
- **FR-040:** Installable mobile-responsive PWA (`manifest.json`, service worker, mobile navigation, 44px touch targets) for Android Home Screen & laptop browser.
- **FR-041:** Guided 9-step onboarding wizard with plain-English "Why needed?" explanations and printable/viewable 1-page owner checklist.
- **FR-042:** Zero-CLI routine operation from a single home screen.
- **FR-043:** Truthful connection status badges (`Not connected`, `Connected: read only`, `Awaiting review`, `Live: can reply`, `Suspended`, `Needs reconnect`) backed by live token/scope inspection.
- **FR-044:** Managed operations: migrations, background worker, health checks, automated encrypted backups, verified restore script, secret rotation, and full JSON/CSV vendor exit export.
- **FR-045:** Configurable alert notifications (urgent policy/auth alerts vs daily/weekly digest).
- **FR-046:** Simple "Add Perfume & Receipt" flow with automated OCR/text extraction, PII redaction, and fuzzy matcher correction.
- **FR-047:** Single-upload Dual-Platform Content Studio generating independent Instagram and TikTok packages, disclosures, and checklists.
- **FR-048:** One-tap "Copy Caption / Open Platform" fallback wherever direct publishing or auto-commenting is unsupported or unapproved.
- **FR-049:** Built-in interactive Owner Manual & Runbook (Quick Start, Reconnect Guide, Pause/Kill-Switch, Receipt Upload, TikTok Refusal Fallback, Billing/Retention, Full Data Export).
- **FR-050:** Monthly budget monitor with itemised hosting/AI/storage spend, per-1,000-reply cost estimator, and hard monthly spend cap that automatically downgrades to `DRAFT`/template fallback.

### C7. Cross-Platform Evidence & Self-Purchase Assurance
- **FR-051:** Unified cross-platform Verified Purchases Vault supporting `Empyrean`/`Experian` raw vs canonical merchant verification, PDFs, screenshots, receipts, and manual entries.
- **FR-052:** Per-post, per-perfume provenance record (`receipt_found`, `product_matched`, `owner_confirmed`, `confidence`, `last_checked`, `source`, `ad_relationship`, `affiliate_relationship`, `public_copy_status`, `platform_post_id`).
- **FR-053:** Independent Instagram (Meta Branded Content + UK ASA) and TikTok (TikTok Commercial Content Toggle + TikTok Shop + UK ASA) policy evaluations with versioned rule citations.
- **FR-054:** Verified independent purchase wording ("Purchased with my own money. These are my personal impressions.") combined truthfully with any required `Ad` / affiliate disclosure; never generate false "not an ad" claims.
- **FR-055:** Anti-spam ownership comment guard (never post identical repetitive declarations on every video; never tell TikTok a video is paid content solely because the bottle was self-purchased).
- **FR-056:** Platform-specific preflight checks (TikTok music rights, Shop tags, originality, warning history; Instagram Paid Partnership label, affiliate disclosure, recommendation rules).
- **FR-057:** Immutable completed content package archival with SHA-256 receipt hash and redacted appeal packet export.
- **FR-058:** Retroactive receipt contradiction guard (newly imported receipts never silently alter already-published claims; alert owner and require confirmation).

### D. Non-Functional Requirements
- **NFR-01:** 99.5% own-service availability target with uptime/error metrics endpoint.
- **NFR-02:** Webhook processing with 30/60/120s jittered backoff and `Retry-After` compliance.
- **NFR-03:** Effectively-once outward dispatch via idempotency keys and `RECONCILE_PENDING` state on timeout.
- **NFR-04:** Deduplication on `platform + account_id + comment_id` + per-thread concurrency lock + dead-letter queue.
- **NFR-05:** Security baseline: OAuth PKCE/state, Fernet/AES-GCM encryption at rest for tokens/evidence, HMAC webhook verification, CSRF/CORS protection, RBAC, audit logging, zero secrets in logs.
- **NFR-06:** UK GDPR & data minimisation: PII redaction before storage/LLM, configurable retention cleanup, full owner data export and account erasure.
- **NFR-07:** Hard monthly token/GBP budget meter with automatic fallback to deterministic templates/drafts.
- **NFR-08:** GitHub CI workflow, secret scanning, SBOM/dependency check, and tested encrypted backup/restore scripts.
- **NFR-09:** Instant feature flags (`TIKTOK_WRITE_ENABLED`, `INSTAGRAM_WRITE_ENABLED`, `THIRD_PARTY_AUTOCOMMENT`) defaulting to `false`.
- **NFR-10:** Automatic downgrade to `READ_ONLY` / `DRAFT` on 401/403, token revocation, rate-limit anomaly, or policy warning.
