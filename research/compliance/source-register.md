# Regulatory & Platform Compliance Source Register

**Project:** Ann Reveals AI Manager (`ARAIM` v4.0)
**Owner:** Agent Delta (`content-integrity`)
**Jurisdiction:** United Kingdom (ASA, CAP, CMA, ICO) + Dual-Platform (Meta Instagram & TikTok)
**Baseline Date:** 27 October 2026

---

## 1. UK Statutory & Self-Regulatory Advertising Authorities

### 1.1 UK ASA / CAP / CMA — *Influencers’ Guide to Making Clear that Ads are Ads*
- **Rule Version Code:** `UK-ASA-INF-2026-10-23`
- **Publication / Update Date:** Updated 23 October 2026 (Joint ASA, CAP, and CMA guidance)
- **Primary Sections Cited:**
  - **CAP Code Section 2 (Recognition of Marketing Communications):** Rule `2.1` (Marketing communications must be obviously identifiable as such) and Rule `2.4` (Marketers and publishers must make clear that advertorials and commercial creator content are marketing communications).
  - **Affiliate Marketing & Discount Codes:** When a creator shares an affiliate link, unique tracking URL, or viewer discount/promo code from which the creator can earn commission, credits, or any financial/non-financial benefit, the post—or the relevant portion containing the link/code—is an advertisement **even if the creator purchased the featured product themselves at full retail price**.
  - **Gifted / PR Products:** Unsolicited or solicited free products, PR packages, press samples, or長期 loans accompanied by any expectation, encouragement, or commercial relationship require upfront disclosure. Even where a creator believes there was "no editorial control," CMA consumer law obligations require transparency whenever a material incentive exists.
  - **Upfront Prominence Standard:** Disclosures must be **immediate, prominent, and unambiguous** before the consumer engages with or clicks on the content:
    - **Acceptable primary labels:** `Ad`, `#Ad`, `Advert`, `Advertising`, `Advertisement` placed at the **very beginning** of the caption/overlay without requiring the user to click `"…more"`.
    - **Unacceptable / Insufficient standalone labels:** `Spon`, `Sponsored`, `Collab`, `Affiliate`, `Aff`, `PR`, `Gifted`, `Thanks to [Brand]`, `#ad` buried inside a block of hashtags at the end of a caption, or relying solely on a platform toggle if the toggle is subtle or omitted on cross-posted surfaces.

### 1.2 Competition and Markets Authority (CMA) & DMCC Act 2024
- **Rule Version Code:** `UK-CMA-DMCC-2026`
- **Statutory Basis:** Digital Markets, Competition and Consumers Act 2024 (DMCC Act) — Unfair Commercial Practices provisions (replacing CPRs 2008) & CMA *Hidden Advertising: Compliance Principles for Social Media Platforms and Creators*.
- **Key Obligations:**
  - Prohibits hidden advertising, falsely representing oneself as an unincentivised consumer when acting for a commercial purpose, and omitting material information about commercial incentives.
  - **Strict Prohibition on False Non-Commercial Claims:** A creator must **never** state `"not an ad"`, `"unsponsored"`, or `"100% non-commercial"` on any post that includes an affiliate link, TikTok Shop commission tag, discount code, brand gift, or paid boost—even if the creator bought the physical bottle with their own money.
  - **Account-Wide Claims Prohibition:** Never claim `"I never accept gifts or sponsorships"` at an account level unless 100% historically and prospectively verified; all provenance claims must be scoped strictly to the specific bottle/post (`"I bought this bottle myself"`).

### 1.3 UK GDPR & Data Protection Act 2018 (ICO Guidance)
- **Rule Version Code:** `UK-GDPR-MIN-2026`
- **Key Obligations:**
  - **Data Minimisation (Article 5(1)(c)):** Order receipts uploaded for purchase verification contain special/sensitive financial and personal identifiers (PANs, billing addresses, emails, phone numbers, order barcodes).
  - All such identifiers must be redacted prior to persistent storage, LLM context injection, or external appeal packet generation.

---

## 2. TikTok Platform Policies

### 2.1 TikTok Commercial Content Disclosure Policy (Updated April 2026)
- **Rule Version Code:** `TT-COMM-2026-04`
- **Effective / Updated Date:** April 2026
- **Key Requirements:**
  - Creators must turn **ON** the native **Content Disclosure Setting (`Disclose video content`)** whenever posting content that promotes a brand, product, or service in exchange for anything of value (payment, free gifts/PR, affiliate commission, discount code revenue, or promoting the creator's own business/brand).
  - **Sub-Selection Logic:**
    - `Your brand` -> Generates the `"Promotional content"` label (used when promoting the creator's own products/services/shop).
    - `Branded content` -> Generates the `"Paid partnership"` label (used for third-party brand sponsorships, gifted PR, affiliate promotions, or paid collaborations).
  - **Crucial Distinction for Pure Self-Purchase (`Provenance=SELF_PURCHASED` + `Commercial=NONE`):**
    - If a creator bought a perfume with their own money AND has **no** affiliate link, **no** TikTok Shop link, **no** promo code, **no** gift, and **no** brand relationship, they must **NOT** turn on the TikTok Commercial Content toggle (as doing so falsely marks an editorial review as paid advertising).
    - Instead, they should store the redacted receipt in the Verified Purchases Vault (`FR-051`) so that if TikTok's automated moderation mistakenly flags the video for undisclosed branded content, an immediate factual appeal packet (`FR-032`) can be submitted.

### 2.2 TikTok Shop Creator & Affiliate Rules + Music Terms
- **Rule Version Code:** `TT-SHOP-MUSIC-2026`
- **Key Requirements:**
  - Any video attaching a **TikTok Shop product anchor link** or earning creator affiliate commission is commercial content and must carry both the native TikTok Shop/Commercial disclosure and an upfront `Ad` indicator for UK audiences.
  - **Commercial Music Library Restriction:** Videos with commercial content (`Ad`, affiliate, gifted, paid partnership, own brand) cannot use standard non-commercial licensed pop music; they must use **Original Voiceover/Audio** or tracks cleared in TikTok’s **Commercial Music Library (CML)**.

---

## 3. Meta (Instagram) Platform Policies

### 3.1 Meta Branded Content Policies & Paid Partnership Tool
- **Rule Version Code:** `META-BC-2026`
- **Key Requirements:**
  - Creators must use the native **Paid Partnership label** (`Add paid partnership label` -> tag business partner where applicable) for Reels, Feed posts, Stories, and Carousels featuring content where the creator received—or will receive—anything of value (monetary payment, gifted PR/free products, affiliate commission, or discount code kickbacks).
  - **Dual Requirement in the UK:** The UK ASA has repeatedly ruled that Meta’s native `"Paid partnership with [Brand]"` sub-header alone may not always suffice if viewers can miss it or if an affiliate link is placed in the caption/bio; therefore, ARAIM enforces **both** the native Instagram Paid Partnership toggle **and** an upfront `Ad` prefix at the start of the caption whenever `CommercialRelationship != NONE`.
  - **Pure Self-Purchase on Instagram:** When `Provenance == SELF_PURCHASED` and `CommercialRelationship == NONE`, the Paid Partnership toggle remains **OFF**, and the creator may optionally use truthful personal purchase wording (`"Purchased with my own money. These are my personal impressions."`).
