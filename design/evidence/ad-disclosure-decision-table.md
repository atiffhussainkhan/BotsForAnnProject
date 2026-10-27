# Dual-Platform Ad & Provenance Disclosure Decision Table

**Project:** Ann Reveals AI Manager (`ARAIM` v4.0)
**Owner:** Agent Delta (`content-integrity`)
**Covers:** Hard Rules `G1`–`G6`, `FR-021`–`FR-027`, `FR-053`–`FR-056`

---

## 1. Fundamental Two-Axis Principle (Rule G1 & G2)

$$\text{Disclosure Obligation} = f(\text{ProvenanceStatus}, \text{CommercialRelationship}, \text{Platform})$$

- **Axis 1 — Acquisition Provenance (`ProvenanceStatus`):** How did `@annreveals` acquire the physical bottle?
  - `SELF_PURCHASED` (Verified in Vault or Unverified claim)
  - `PR_GIFTED` (Free product / press pack / unsolicited gift)
  - `LOANED` (Temporary bottle loan from brand/PR)
  - `FREE_SAMPLE` (Complimentary discovery vial / GWP)
  - `UNKNOWN` (No provenance declared or receipt missing)
- **Axis 2 — Commercial Relationship (`CommercialRelationship`):** Does `@annreveals` have any financial or commercial incentive tied to this post or brand?
  - `NONE`
  - `AFFILIATE_LINK` (Amazon Associates, LTK, ShopMy, Skimlinks, retailer affiliate URL in bio/caption/stories)
  - `PROMO_CODE` (Viewer discount code, e.g. `ANN10`, that tracks sales or benefits the creator)
  - `TIKTOK_SHOP` (TikTok Shop product anchor link or creator commission)
  - `PAID_PARTNERSHIP` (Sponsored post, paid brief, paid usage/whitelisting rights)
  - `GIFTED_INCENTIVE` (Gifted item with posting expectation or ongoing brand ambassador relationship)
  - `OWN_BRAND` (Promoting creator's own products, decants, or merchandise)

---

## 2. Master Decision Matrix

| Scenario ID | Provenance Status | Vault Confidence | Commercial Relationship(s) | UK ASA Upfront `Ad` Required? | Instagram Native Paid Partnership Toggle | TikTok Commercial Content Toggle | Allowed Self-Purchase Wording | Forbidden Claims (Hard Block) | Preflight Risk Grade (If Properly Configured) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M-01** | `SELF_PURCHASED` | `VERIFIED_SELF_PURCHASE` | `NONE` | **NO** | **OFF** | **OFF** | `"Purchased with my own money. These are my personal impressions."` | Account-wide `"I never accept gifts"` (Rule G4) | `GREEN` |
| **M-02** | `SELF_PURCHASED` | `UNVERIFIED` (No receipt / low OCR / unconfirmed `Experian`) | `NONE` | **NO** | **OFF** | **OFF** | Personal editorial review allowed, but **"Verified Purchase"** badge/claim is withheld until receipt verified | Claiming `"Verified receipt on file"` when unverified | `AMBER` (Advisory: upload/verify receipt in Vault) |
| **M-03** | `SELF_PURCHASED` | `VERIFIED_SELF_PURCHASE` | `AFFILIATE_LINK` or `PROMO_CODE` | **YES (`Ad` at very start)** | **ON** (Paid Partnership / Affiliate disclosure) | **ON** (`Branded content` -> Paid partnership) | `"Ad \| Purchased with my own money (contains affiliate link/code)."` | **`"Not an ad"`**, `"Unsponsored"`, hiding `#ad` at end of caption (Rule G1/G2) | `GREEN` (if `Ad` + toggle ON); `RED` if `Ad` omitted or `"not an ad"` present |
| **M-04** | `SELF_PURCHASED` | `VERIFIED_SELF_PURCHASE` | `TIKTOK_SHOP` | **YES (`Ad` at very start)** | **ON** (if cross-posted with shop/affiliate link) | **ON** (TikTok Shop Commission + Commercial Toggle) | `"Ad \| I bought this bottle myself; linked on TikTok Shop (commission earned)."` | **`"Not an ad"`**, omitting `Ad` prefix | `GREEN` (with `Ad` + toggle + CML audio); `RED` if missing |
| **M-05** | `PR_GIFTED` or `LOANED` | N/A | `NONE` or `GIFTED_INCENTIVE` | **YES (`Ad` at very start)** | **ON** (`Paid partnership`) | **ON** (`Branded content`) | **NONE** (Must state gifted/PR status clearly after `Ad`) | Claiming `"Bought with my own money"` or using `#gifted` without `Ad` | `GREEN` (with upfront `Ad` + toggle); `RED` if only `#gifted` used |
| **M-06** | `SELF_PURCHASED` or `PR_GIFTED` | Any | `PAID_PARTNERSHIP` | **YES (`Ad` at very start)** | **ON** (`Paid partnership with @brand`) | **ON** (`Branded content`) | If self-purchased prior to sponsorship, must still lead with `Ad \| Paid partnership` | **`"Not an ad"`**, omitting native toggle | `GREEN` (when `Ad` + toggle ON); `RED` otherwise |
| **M-07** | `FREE_SAMPLE` (Complimentary GWP with paid order) | `VERIFIED_SELF_PURCHASE` (on main item only) | `NONE` | **AMBER / Conditional** | **OFF** (if purely unsolicited sample with paid retail order & zero brand contact) | **OFF** | `"Complimentary sample received with my retail order. Personal impressions."` | Claiming full bottle was purchased if reviewing a free 2ml vial | `AMBER` (Disclose sample origin transparently) |
| **M-08** | Any | `CONFLICTED` (Refunded / £0 PR invoice) | Any | Depends on commercial axis | Depends on commercial axis | Depends on commercial axis | **BLOCKED** — Cannot claim self-purchase on a refunded or £0 order | Any self-purchase claim | `RED` (Resolve Vault conflict before publishing) |
| **M-09** | Any | Any | `OWN_BRAND` | **YES (`Ad` at start)** | **ON** | **ON** (`Your brand` -> Promotional content) | N/A (Must disclose own brand/business) | Pretending to be an independent third-party consumer | `GREEN` (with `Ad` + `Your brand` toggle) |

---

## 3. Platform-Specific Audio, Hashtag & Comment Rules

1. **Caption Hashtag Standard (`FR-024`):**
   - Default to **5 highly relevant, non-spammy hashtags** placed at the end of the caption (e.g., `#perfumetok #fragrancereview #nicheperfume #scentoftheday #ukfragcomm`).
   - Never bury the `Ad` disclosure inside the hashtag block; `Ad |` must appear at character index `0` of the caption when required.
2. **Audio & Music Rights Check (`FR-056`):**
   - On TikTok and Instagram, whenever `CommercialRelationship != NONE` or the Commercial/Paid Partnership toggle is **ON**, standard licensed pop music is restricted. Preflight flags `RED` if non-commercial trending music is selected on a commercial post, instructing the owner to use **Original Voiceover** or **Commercial Music Library (CML)** audio.
3. **Optional First-Party Ownership Comment Guard (`FR-025`, `FR-055`, Rule G5):**
   - Disabled by default (`include_ownership_comment=False`).
   - Only eligible when `ProvenanceStatus == SELF_PURCHASED`, Vault confidence is `VERIFIED_SELF_PURCHASE`, and `CommercialRelationship == NONE`.
   - Rotates through natural, non-repetitive UK-English phrases and blocks posting identical wording on consecutive videos.
