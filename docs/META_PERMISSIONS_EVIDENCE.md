# Meta / Instagram Permissions, Endpoints & Compliance Evidence Dossier

**Document Version:** 4.0  
**Verification Date:** 27 October 2026  
**Prepared By:** Agent Bravo (Agent 2 — Meta/Instagram Developer Platform & Integrations Specialist)  
**Target Account:** `@annreveals` (Instagram Professional Creator / Business Account)

---

## 1. Executive Summary

This dossier provides the technical and regulatory evidence for **Ann Reveals AI Manager (`ARAIM`)** interacting with Meta's **Instagram Platform**. Every Instagram feature in `ARAIM` operates strictly within Meta's official **Instagram API with Instagram Login** (`https://graph.instagram.com/v21.0`) or falls back to transparent, owner-in-the-loop manual tools.

### Core Compliance Commitments
1. **Least-Privileged OAuth Route:** Uses **Instagram API with Instagram Login** (`instagram_business_basic`, `instagram_business_manage_comments`) so `@annreveals` only needs an Instagram Professional (**Creator** or **Business**) account—no mandatory Facebook Page is required.
2. **Default Write Gate (`INSTAGRAM_WRITE_ENABLED=false`):** Even after OAuth connection, outgoing comment writes remain disabled in `DRAFT` mode until scopes are verified live and the owner explicitly activates writes after a 10-comment pilot test.
3. **Permanent Third-Party Automation Ban:** `comment_on_nonowned_post` and `get_following_posts` are permanently blocked in code (`UnsupportedCapabilityError`). Engaging with fellow creators uses **Owner-in-the-Loop Assisted Mode** (2–4 contextual draft replies + one-tap Copy & Open in Instagram).
4. **Independent Provenance vs. Commercial Disclosure:** Self-purchase receipts (`SELF_PURCHASED`, e.g., from `Empyrean` or other retailers) never suppress Meta's **Paid Partnership label** or UK ASA **`Ad`** disclosure when an affiliate link, discount code, or brand commission exists.

---

## 2. Official Scopes & Endpoint Matrix

### 2.1 Scopes (`Instagram API with Instagram Login`)

| Scope Name | Required in v4.0? | Purpose for `@annreveals` | Endpoints Unlocked | Fallback if Unapproved / Revoked |
| :--- | :--- | :--- | :--- | :--- |
| **`instagram_business_basic`** | **YES (Core)** | Read `@annreveals` professional profile metadata (`id`, `user_id`, `username`, `account_type`) and list owned Reels/Posts (`/{ig-user-id}/media`) to attach fragrance provenance records and ingest comment threads. | • `GET /v21.0/me`<br>• `GET /v21.0/{ig-user-id}/media`<br>• `GET /v21.0/{ig-media-id}` | Manual post URL registration in Content Studio & Verified Purchases Vault. |
| **`instagram_business_manage_comments`** | **YES (Core)** | Read comments and nested replies on `@annreveals` owned media, post brand-safe replies to viewer comments (`POST /{ig-comment-id}/replies`), and optionally post a non-repetitive first-party context/ownership comment on owned media (`POST /{ig-media-id}/comments`). | • `GET /v21.0/{ig-media-id}/comments`<br>• `GET /v21.0/{ig-comment-id}/replies`<br>• `POST /v21.0/{ig-comment-id}/replies`<br>• `POST /v21.0/{ig-media-id}/comments` | `DRAFT_ONLY` mode: AI drafts replies in dashboard; owner uses one-tap Copy & Open Permalink. |
| **`instagram_business_manage_messages`** | **OPTIONAL (Disabled by default)** | Read/manage Instagram Direct Messages if the owner enables DM inbox triage in a future release. Excluded from default v4.0 OAuth scope string to keep permissions minimal. | • `GET /v21.0/me/conversations?platform=instagram` | Native Instagram app inbox; zero automated bulk DMs permitted (FR-016). |
| **`instagram_business_content_publish`** | **OPTIONAL (Disabled by default)** | Publish Reels/single media containers directly from Content Studio (`POST /{ig-user-id}/media`, `POST /{ig-user-id}/media_publish`). | • `POST /v21.0/{ig-user-id}/media`<br>• `GET /v21.0/{ig-container-id}`<br>• `POST /v21.0/{ig-user-id}/media_publish` | One-tap "Copy Caption & Hashtags + Open Instagram" workflow in Dual-Platform Content Studio. |

### 2.2 Alternative Fallback Route (`Instagram API with Facebook Login`)
If `@annreveals` elects to connect via a linked Facebook Page instead of direct Instagram Login, the adapter maps the equivalent Graph API (`https://graph.facebook.com/v21.0`) scopes:
- `instagram_basic`
- `instagram_manage_comments`
- `pages_show_list`
- `pages_read_engagement`

---

## 3. Meta App Mode Behavior: Development Mode vs. Live Mode

| Capability | Development Mode (Owner Added as `Instagram Tester`) | Live Mode (Post Meta App Review) | Engineering Mitigation in `ARAIM` |
| :--- | :--- | :--- | :--- |
| **OAuth Login & Token Refresh** | Works immediately for `@annreveals` once accepted under *Apps and Websites -> Tester Invites*. | Works for any verified professional account. | Token inspector checks `expires_in` and refreshes 60-day long-lived tokens automatically. |
| **Reading Owned Posts & Comments (`GET`)** | Works immediately for `@annreveals`'s owned media. | Works in full production. | Cursor pagination (`after`) with rate-limit header tracking (`X-Business-Use-Case-Usage`). |
| **Replying to Owned Comments (`POST`)** | Works for `@annreveals` owned media when `instagram_business_manage_comments` is granted. | Works in full production. | Gated behind `INSTAGRAM_WRITE_ENABLED`, self-reply loop guard, and `RECONCILE_PENDING` timeout reconciliation. |
| **Real-Time Webhooks (`comments` field)** | Meta only guarantees live webhook delivery when the App is in **Live Mode** (though test payloads work in Dev Mode). | Full real-time delivery signed with `X-Hub-Signature-256`. | Hybrid ingestion: `ARAIM` combines `X-Hub-Signature-256` webhooks with a scheduled polling reconciler (`GET /{ig-media-id}/comments`) so Dev Mode misses zero comments. |

---

## 4. Meta Branded Content & UK ASA Compliance Rules

Per [Meta Branded Content Policies](https://www.facebook.com/help/instagram/616901995832907?locale=en_GB) and the UK CAP Code:
1. **When Paid Partnership Label is Mandatory:** Any Instagram Reel, Post, or Story featuring a fragrance where `@annreveals` has an affiliate link, commission code, paid sponsorship, gifted PR bottle, or commercial relationship with a brand or retailer **must** enable Instagram's native **Paid Partnership label** and include a clear upfront **`Ad`** disclosure.
2. **Self-Purchase Truthfulness (`FR-021`, `FR-022`, `FR-054`):**
   - If `@annreveals` bought a bottle with her own money (verified via receipt in the Verified Purchases Vault, e.g., raw merchant `Empyrean` or `Experian` pending owner confirmation) **and** has zero commercial/affiliate links on the post, she may state:
     > *"Purchased with my own money. These are my personal impressions."*
   - If she bought the bottle herself **but** includes an affiliate link or discount code, `ARAIM` **requires** both the **`Ad` / Paid Partnership** disclosure and allows truthful combined wording without **ever** appending *"not an ad"* or *"unsponsored"*.
