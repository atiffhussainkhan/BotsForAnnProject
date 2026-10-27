# Meta / Instagram Official Documentation Source Register

**Verification Date:** 27 October 2026  
**Auditor:** Agent Bravo (Agent 2 — Meta/Instagram Developer Platform & Integrations Specialist)  
**Target Account:** `@annreveals` (Instagram Professional Creator / Business Account)

---

## 1. Primary Official Meta Documentation Sources

| Source ID | Document Title | Official URL | Last Verified | Key Findings & Architectural Impact |
| :--- | :--- | :--- | :--- | :--- |
| **META-DOC-01** | **Instagram Platform Overview** | `https://developers.facebook.com/docs/instagram-platform/` | 2026-10-27 | Confirms two official authentication pathways: **Instagram API with Instagram Login** (`graph.instagram.com`, no Facebook Page required, supports Creator and Business accounts) and **Instagram API with Facebook Login** (`graph.facebook.com`, requires a linked Facebook Page). Confirms personal Instagram accounts have no API access. |
| **META-DOC-02** | **Comment Moderation — Instagram Platform** | `https://developers.facebook.com/docs/instagram-platform/comment-moderation/` | 2026-10-27 | Defines exact Graph API operations for reading comments on owned media (`GET /{ig-media-id}/comments`), reading nested replies (`GET /{ig-comment-id}/replies`), replying to a comment on owned media (`POST /{ig-comment-id}/replies?message=...`), creating a top-level comment on owned media (`POST /{ig-media-id}/comments?message=...`), hiding/unhiding (`POST /{ig-comment-id}?hide=true`), and deleting (`DELETE /{ig-comment-id}`). Requires `instagram_business_manage_comments` (Instagram Login) or `instagram_manage_comments` (Facebook Login). |
| **META-DOC-03** | **Official Meta Postman Collection — Instagram API with Instagram Login** | `https://www.postman.com/meta/instagram/folder/6raa77c/instagram-api-with-instagram-login` | 2026-10-27 | Provides canonical request structures against `https://graph.instagram.com/v21.0`:<br>• `GET /me?fields=id,user_id,username,name,account_type,profile_picture_url,followers_count,follows_count,media_count`<br>• `GET /{ig-user-id}/media?fields=id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count`<br>• `GET /{ig-media-id}/comments?fields=id,text,timestamp,username,from,parent_id,hidden,like_count`<br>• `POST /{ig-comment-id}/replies`<br>• `POST /{ig-media-id}/comments` |
| **META-DOC-04** | **Instagram API with Instagram Login — Business Login for Instagram** | `https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/` | 2026-10-27 | Details OAuth 2.0 authorization endpoint (`https://www.instagram.com/oauth/authorize`), short-lived token exchange (`POST https://api.instagram.com/oauth/access_token`), long-lived token exchange (`GET https://graph.instagram.com/access_token?grant_type=ig_exchange_token`), and 60-day token refresh (`GET https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token`). |
| **META-DOC-05** | **Webhooks for Instagram** | `https://developers.facebook.com/docs/instagram-platform/webhooks/` | 2026-10-27 | Documents webhook subscription handshake (`GET` with `hub.mode=subscribe`, `hub.verify_token`, echoing `hub.challenge`), payload verification using `X-Hub-Signature-256` (`sha256=` + HMAC-SHA256 of raw request body keyed by App Secret), and `comments` field event payloads (`object: "instagram"`, `entry[].changes[].field == "comments"`). |
| **META-DOC-06** | **Meta Branded Content Policies & Paid Partnership Label (UK/Global)** | `https://www.facebook.com/help/instagram/616901995832907?locale=en_GB` | 2026-10-27 | Creators must use the **Paid Partnership label** whenever posting content where they have received anything of value from a brand or business partner, or where commercial links, affiliate commissions, discount codes, or gifted products are involved. Self-purchasing a product does **not** exempt a creator from the Paid Partnership tool if an affiliate link or brand commission is attached to the post. |
| **META-DOC-07** | **Graph API Rate Limiting (Instagram Business Use Case)** | `https://developers.facebook.com/docs/graph-api/overview/rate-limiting/` | 2026-10-27 | Instagram Platform calls are subject to Business Use Case (BUC) and application rate limits (`X-Business-Use-Case-Usage` and `X-App-Usage` response headers). Exceeding limits returns HTTP `429` or Graph error codes `4`, `17`, `32`, or `613`. Adapters must inspect usage headers and back off with jitter. |

---

## 2. Explicit Verification of Architectural Boundaries (27 Oct 2026)

1. **Can `@annreveals` read and reply to comments on her own Reels/Posts via official API?**
   - **YES.** Fully supported via `GET /{ig-media-id}/comments`, `GET /{ig-comment-id}/replies`, and `POST /{ig-comment-id}/replies` using `instagram_business_basic` + `instagram_business_manage_comments`.
2. **Can `@annreveals` post a first-party ownership or context comment on her own post?**
   - **YES.** Supported via `POST /{ig-media-id}/comments` on owned media when `instagram_business_manage_comments` is granted and `INSTAGRAM_WRITE_ENABLED=true`.
3. **Can `@annreveals` automatically fetch a feed of everyone she follows or post comments on other creators' posts via API?**
   - **NO.** Meta does not provide any endpoint to list a user's following feed or publish comments on non-owned third-party media. `get_following_posts` and `comment_on_nonowned_post` are permanently disabled in `ARAIM` and handled via the **Owner-in-the-Loop Creator Engagement Assistant** (notification + 2–4 draft comments + one-tap copy & open Instagram).
4. **Does `@annreveals` need a Facebook Page?**
   - **NO** when using **Instagram API with Instagram Login** (`graph.instagram.com`), provided `@annreveals` is an Instagram Professional (Creator or Business) account.
