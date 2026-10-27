# ACCESS READINESS & PERMISSION FEASIBILITY GATE (PHASE 0 — G0)

**Project:** Ann Reveals AI Manager (`ARAIM` v4.0)
**Target Handle:** `@annreveals`
**Audit Date:** 27 October 2026
**Status:** Phase 0 Capability & Spending Gate Complete — Ready for Owner OAuth & App Review Actions

---

## 1. Executive Summary & Honest Capability Declaration

This document records the verified official API prerequisites for `@annreveals` on Instagram and TikTok as of **27 October 2026**.

> [!IMPORTANT]
> **Truthful Access Principle:** Software implementation does **not** grant platform permissions. Until the owner (`@annreveals`) completes official OAuth consent and the respective developer app passes platform review where required, outbound comment publishing remains locked in **`DRAFT_ONLY` / `Awaiting approval`** mode (`INSTAGRAM_WRITE_ENABLED=false`, `TIKTOK_WRITE_ENABLED=false`, `THIRD_PARTY_AUTOCOMMENT=false`). Under no circumstances does Ann Reveals AI Manager use browser automation, scraped cookies, private mobile APIs, or stealth proxies.

| Capability Area | Current Status (27 Oct 2026) | Default Runtime Mode | Required Gate to Unlock `SAFE_AUTO` |
|---|---|---|---|
| **Core Cloud Dashboard, AI Reply Engine, Receipt Vault & UK Compliance Studio** | **VERIFIED_ACTIVE (Local & Cloud Ready)** | `ACTIVE` | None — operates independently of social API write approvals |
| **Instagram Owned-Post Comment Read & Reply** | **`AWAITING_APPROVAL` (Owner OAuth + App Scope)** | `DRAFT` (`INSTAGRAM_WRITE_ENABLED=false`) | Gate G2: Professional Account (Creator/Business) + Meta App `instagram_business_manage_comments` grant + 1 live test reply |
| **TikTok Owned-Video Comment Read & Reply** | **`AWAITING_APPROVAL` (March 2026 Accounts API Gate)** | `DRAFT` (`TIKTOK_WRITE_ENABLED=false`) | Gate G3: TikTok Accounts API Application (post-20 March 2026 policy) + Owned Account OAuth + 1 live test reply |
| **Instagram / TikTok Inbound DMs** | **`AWAITING_APPROVAL` (Optional Separate Scope)** | `OFF` | Separate messaging permission grant + explicit owner opt-in |
| **Friends / Creator Watchlist New-Post Alerts & Drafts** | **VERIFIED_ACTIVE (Draft & Notification Mode)** | `DRAFT` (Owner-in-the-loop) | Uses lawful RSS/shared URLs/consented feeds; owner posts manually via 1-tap Copy & Open App |
| **Automated Mass Commenting on Third-Party Videos** | **`UNAVAILABLE` (Prohibited by Platform Terms)** | `DISABLED` (`THIRD_PARTY_AUTOCOMMENT=false`) | Permanently disabled in v1; no official blanket third-party auto-commenting API exists |

---

## 2. Instagram (`@annreveals`) Access Readiness & Selected Route

### 2.1 Selected Least-Privileged Pathway: Instagram API with Instagram Login
Meta provides two official pathways for Instagram Professional accounts:
1. **Instagram API with Instagram Login (Selected Primary Route):**
   - **Why selected:** Allows `@annreveals` (Instagram Creator or Business account) to authenticate directly via `api.instagram.com` / `graph.instagram.com` **without** requiring a linked Facebook Page.
   - **Official Reference:** [Meta Instagram API with Instagram Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login) & [Comment Moderation Guide](https://developers.facebook.com/docs/instagram-platform/comment-moderation/) (verified 27 Oct 2026).
   - **Required Scopes:**
     - `instagram_business_basic` (profile & owned media discovery)
     - `instagram_business_manage_comments` (read comments on owned media, reply to comments on owned media, create first-party comments on owned media, hide/unhide/delete comments)
     - `instagram_business_manage_messages` *(optional, disabled by default unless DM assistance is opted into)*
2. **Instagram Graph API with Facebook Login (Supported Fallback):**
   - Requires `@annreveals` to be linked to a Facebook Page and uses `pages_read_engagement` + `instagram_basic` + `instagram_manage_comments` on `graph.facebook.com`.

### 2.2 Development Mode vs Live Mode on Meta
- **Development Mode Pilot (Immediate once owner links account):** If `@annreveals` is added as an **Instagram Tester** on the owner's Meta Developer App, `instagram_business_basic` and `instagram_business_manage_comments` can be tested live on `@annreveals`'s own posts immediately without waiting for public App Review.
- **Live Mode:** Required for production webhook delivery in some Meta configurations; requires submitting a screen recording of the dashboard's comment moderation flow for Meta App Review.

---

## 3. TikTok (`@annreveals`) Access Readiness & March 20, 2026 Policy Gate

### 3.1 Critical Distinction: TikTok Accounts API vs Content Posting API
- **TikTok Business Accounts API (v1.3):**
  - **Official Reference:** [TikTok Accounts API Overview v1.3](https://business-api.tiktok.com/portal/docs/accounts-api-overview/v1.3) and [Owned-Video Comment Endpoints](https://business-api.tiktok.com/portal/docs?id=1736271785207810) / [Gateway Doc 1751617884206210](https://business-api.tiktok.com/gateway/docs/index?doc_id=1751617884206210) (verified 27 Oct 2026).
  - **Supported Operations (when approved):**
    - List comments on an owned video (`/open_api/v1.3/business/comment/list/`)
    - Reply to an existing comment on an owned video (`/open_api/v1.3/business/comment/reply/create/`)
    - Create a new first-party comment on an owned video (`/open_api/v1.3/business/comment/create/`)
    - Receive signed comment webhooks for owned videos
  - **Mandatory March 20, 2026 Access Policy:** Effective **20 March 2026**, TikTok requires an explicit **Accounts API Access Application** in the TikTok Business Developer Portal before comment management scopes (`comment.list`, `comment.list.manage` / business comment scopes) are granted to new apps. Standard Login Kit (`user.info.basic`) or Content Posting API (`video.publish`, `video.upload`) approvals **do not** grant Accounts API comment moderation access.
- **Fallback When TikTok Approval is Pending or Denied:**
  - Ann Reveals AI Manager keeps TikTok in **`Awaiting review — Draft only`** mode.
  - All TikTok pre-publication compliance checks, purchase-proof matching, UK ASA + TikTok commercial disclosure guidance, 5-hashtag caption generation, manual comment drafting, creator watchlist alerts, and violation appeal packet generation remain **100% operational**.

---

## 4. Exact Owner Actions Required (Plain-English Checklist)

 Gemini will **never** ask for your Instagram or TikTok password, session cookies, or raw tokens in chat. When you are ready to connect live accounts in Phase 2/3, you only need to perform these official steps:

1. **Confirm Account Types (Free, 2 minutes in phone apps):**
   - In Instagram: Ensure `@annreveals` is set to a **Creator** or **Business** (Professional) account (*Settings -> Account type and tools -> Switch to professional account*).
   - In TikTok: Check whether `@annreveals` is a Creator/Personal or Business account so the matching TikTok Developer portal flow is used.
2. **Meta Developer App Setup (Free, ~10 minutes):**
   - Sign in at [https://developers.facebook.com/apps/](https://developers.facebook.com/apps/) and create an app selecting **Instagram API with Instagram Login**.
   - Add `@annreveals` under *App Roles -> Instagram Testers* and accept the tester invite inside the Instagram app (*Settings -> Website permissions -> Apps and websites -> Tester Invites*).
   - Click **Connect Instagram** inside the Ann Reveals AI Manager Setup Wizard to complete official OAuth login.
3. **TikTok Developer / Business Portal Application (Free, ~15 minutes + TikTok review time):**
   - Sign in at [https://business-api.tiktok.com/portal/](https://business-api.tiktok.com/portal/) (or [https://developers.tiktok.com/](https://developers.tiktok.com/)).
   - Submit the **TikTok Accounts API Access Application** (required under the 20 March 2026 policy) using the pre-written justification text generated for you in `docs/TIKTOK_APPLICATION_EVIDENCE.md`.

---

## 5. Spending & Risk Gate Summary

- **Spend Incurred So Far:** **£0.00**
- **Monthly Budget Ceiling:** Hard cap at **£30.00/month** (estimated steady-state operating cost: **£5.50 – £11.80/month**).
- **Paid Upgrades / External Charges:** **£0.00 authorised.** No paid cloud hosting, domain, or paid API tier will be provisioned without explicit owner sign-off.
