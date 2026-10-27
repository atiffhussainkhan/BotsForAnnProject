# OFFICIAL SOURCE REGISTER & GOVERNANCE SNAPSHOT

**Project:** Ann Reveals AI Manager (`ARAIM` v4.0)
**Verified Date:** 27 October 2026
**Governance Policy:** All platform adapters, disclosure engines, and appeal templates reference versioned entries in this register. Documentation existence is never conflated with granted account permissions.

---

## 1. TikTok Official Documentation Register

| Source ID | Title | Official URL | Checked Date | Effective Policy Version | Key Engineering Constraint Extracted |
|---|---|---|---|---|---|
| `SRC-TT-01` | TikTok Accounts API Overview v1.3 | `https://business-api.tiktok.com/portal/docs/accounts-api-overview/v1.3` | 27 Oct 2026 | v1.3 (Post-20 March 2026 Access Policy) | Owned-video comment management for Personal & Business accounts requires a dedicated **TikTok Accounts API Access Application** (effective 20 March 2026). |
| `SRC-TT-02` | TikTok API for Business Accounts — Owned-Video Comment Endpoints & Webhooks | `https://business-api.tiktok.com/portal/docs?id=1736271785207810` | 27 Oct 2026 | v1.3 | Defines `/open_api/v1.3/business/comment/list/`, `/comment/reply/create/`, `/comment/create/` and webhook signature header `TikTok-Signature`. |
| `SRC-TT-03` | TikTok Business Gateway Reference (Doc 1751617884206210) | `https://business-api.tiktok.com/gateway/docs/index?doc_id=1751617884206210` | 27 Oct 2026 | v1.3 | Confirms comment write operations apply **only** to videos owned by the authenticated token holder. Zero third-party video comment write endpoint exists. |
| `SRC-TT-04` | TikTok Developer Guidelines | `https://developers.tiktok.com/docs/en/our-guidelines-developer-guidelines` | 27 Oct 2026 | Updated 4 Aug 2026 | Strictly prohibits scraping, automated mass engagement on third-party accounts, credential harvesting, and bypassing rate limits. |
| `SRC-TT-05` | TikTok Developer Scopes Overview | `https://developers.tiktok.com/docs/en/scopes-overview` | 27 Oct 2026 | 2026 Current | Login Kit (`user.info.basic`) and Content Posting (`video.publish`) scopes do **not** include Accounts API comment moderation scopes. |
| `SRC-TT-06` | TikTok Content-Sharing Guidelines & Direct Post Prerequisites | `https://developers.tiktok.com/docs/en/content-sharing-guidelines` & `https://developers.tiktok.com/docs/en/content-posting-api-get-started` | 27 Oct 2026 | Updated 4 Aug 2026 | Unaudited Content Posting API clients are restricted to private (`SELF_ONLY`) posts; creators must explicitly select commercial content disclosures. |
| `SRC-TT-07` | TikTok Commercial Content Disclosure Policy | `https://support.tiktok.com/en/business-and-creator/creator-and-business-accounts/promoting-a-brand-product-or-service` & `https://ads.tiktok.com/resources/help/article/about-the-content-disclosure-setting-for-creators` | 27 Oct 2026 | Updated Apr 2026 | Creators must turn on the Commercial Content Disclosure toggle ("Your brand" -> *Promotional content* or "Branded content" -> *Paid partnership*) whenever promoting a brand/product with any commercial incentive (including affiliate links, TikTok Shop commissions, PR gifts, or sponsorship), even if the bottle was originally bought by the creator. |

---

## 2. Meta / Instagram Official Documentation Register

| Source ID | Title | Official URL | Checked Date | Effective Policy Version | Key Engineering Constraint Extracted |
|---|---|---|---|---|---|
| `SRC-IG-01` | Meta Instagram Platform Overview | `https://developers.facebook.com/docs/instagram-platform/` | 27 Oct 2026 | Graph API v21.0 (2026) | Supports Instagram Professional accounts (Creator & Business) via either *Instagram API with Instagram Login* (`graph.instagram.com`) or *Instagram Graph API with Facebook Login* (`graph.facebook.com`). |
| `SRC-IG-02` | Meta Instagram Comment Moderation API | `https://developers.facebook.com/docs/instagram-platform/comment-moderation/` | 27 Oct 2026 | Graph API v21.0 | Requires `instagram_business_manage_comments` (Instagram Login) or `instagram_manage_comments` (Facebook Login). Supports reading comments and replying to comments on **owned** media only. |
| `SRC-IG-03` | Official Meta Postman Collection — Instagram API with Instagram Login | `https://www.postman.com/meta/instagram/folder/6raa77c/instagram-api-with-instagram-login` & `https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api` | 27 Oct 2026 | 2026 Official Collection | Documents exact payload schemas for `/me`, `/{ig-user-id}/media`, `/{ig-media-id}/comments`, and `/{ig-comment-id}/replies`. |
| `SRC-IG-04` | Instagram Branded Content & Paid Partnership Rules | `https://www.facebook.com/help/instagram/616901995832907?locale=en_GB` | 27 Oct 2026 | UK / Global Current | Requires the native **Paid partnership label** whenever value (payment, gifted PR product, affiliate commission, discount code incentive) is exchanged or present. |

---

## 3. UK Advertising Standards Authority (ASA) / CAP & CMA Register

| Source ID | Title | Official URL | Checked Date | Effective Policy Version | Key Engineering Constraint Extracted |
|---|---|---|---|---|---|
| `SRC-UK-01` | UK ASA / CAP Influencers' Guide to Making Clear that Ads are Ads | `https://www.asa.org.uk/resource/influencers-guide.html` | 27 Oct 2026 | 23 Oct 2026 Edition | Any post featuring an affiliate link, discount code, TikTok Shop commission, PR gift, or brand payment is an **Ad** under UK CAP Code and must display a prominent upfront **`Ad`** label (not buried in hashtags or obscured as `#spon` or `#collab`), **even if the creator purchased the product with their own money**. |
| `SRC-UK-02` | UK ASA Recognising Ads on Social Media / Affiliate Marketing | `https://www.asa.org.uk/advice-online/recognising-ads-social-media.html` | 27 Oct 2026 | 2026 Current | Self-purchase is a factual provenance statement ("Purchased with my own money"), **not** a blanket exemption from UK advertising disclosure rules when affiliate links or commercial arrangements are attached to the post. |
