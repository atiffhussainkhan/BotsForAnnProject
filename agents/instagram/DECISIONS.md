# Agent Bravo (Instagram) — Architecture & API Decisions Log

**Agent:** Agent Bravo (Agent 2 — Meta/Instagram Developer Platform & Integrations Specialist)  
**Project:** Ann Reveals AI Manager (`ARAIM` v4.0)  
**Target Account:** `@annreveals` (Instagram Professional Creator / Business Account)  
**Last Updated:** 27 October 2026

---

## ADR-IG-001: Selection of "Instagram API with Instagram Login" over "Facebook Login for Business"

### Status
**Accepted** (27 October 2026)

### Context
Meta provides two distinct official authentication and Graph API routes for Instagram Professional accounts:
1. **Instagram API with Instagram Login** (`graph.instagram.com` / `api.instagram.com`): Authenticates the Instagram Professional (Creator or Business) account directly via Instagram credentials without requiring a linked Facebook Page or Meta Business Portfolio for single-owner creator operations.
2. **Instagram API with Facebook Login** (`graph.facebook.com`): Requires the Instagram Professional account to be linked to a Facebook Page and managed via Facebook Login permissions (`instagram_basic`, `instagram_manage_comments`, `pages_show_list`, `pages_read_engagement`).

### Decision
We select **Instagram API with Instagram Login** (`graph.instagram.com`, Graph API v21.0+) as the primary, least-privileged integration route for `@annreveals`, while retaining configuration support for the Facebook Login route strictly as an optional fallback.

### Rationale
- **No Mandatory Facebook Page Overhead:** `@annreveals` is an independent UK fragrance creator. Requiring a linked Facebook Page and `pages_show_list` / `pages_read_engagement` scopes increases onboarding friction and expands permission surface unnecessarily.
- **Least-Privileged Scopes:** Uses granular business/creator scopes (`instagram_business_basic`, `instagram_business_manage_comments`, and optional `instagram_business_manage_messages` / `instagram_business_content_publish`).
- **Single-Account Isolation:** For a single-owner workspace where `@annreveals` can be added as an Instagram Tester in the Meta App Dashboard, Development Mode supports full end-to-end testing of owned-account webhooks and comment replies by role-assigned testers before public App Review is required.

---

## ADR-IG-002: Permanent Block on Non-Owned Post Commenting & Follow-List Scraping

### Status
**Accepted** (27 October 2026)

### Context
Capability Area C2 ("Friends & Creator Engagement Assistant") assists `@annreveals` in engaging with a curated shortlist of fellow fragrance creators.

### Decision
The Instagram adapter permanently disables and raises `PermissionError` / `UnsupportedCapabilityError` on `comment_on_nonowned_post()` and `get_following_posts()`.
- `THIRD_PARTY_AUTOCOMMENT` is hardcoded to `false` for Instagram.
- All third-party creator engagement is routed through **Owner-in-the-Loop Assisted Mode** (`DRAFT_ONLY` + one-tap copy & deep-link to native Instagram app).

### Rationale
- Meta's Instagram Platform API does **not** expose any public endpoint to list an account's following feed or post comments on arbitrary third-party media not owned by the authenticated user (outside narrow Business Discovery read metadata).
- Attempting to bypass this via private mobile APIs, session cookies, or headless browser automation violates Meta Platform Terms and risks immediate account suspension for `@annreveals`.

---

## ADR-IG-003: Fail-Closed Write Gate (`INSTAGRAM_WRITE_ENABLED=false`) & Timeout Reconciliation (`RECONCILE_PENDING`)

### Status
**Accepted** (27 October 2026)

### Context
Network timeouts during `POST /{ig-comment-id}/replies` or `POST /{ig-media-id}/comments` can leave the system uncertain whether Meta committed the comment write. Simply retrying on a 5xx or socket timeout risks posting duplicate replies under a viewer's comment, which looks robotic and violates Meta's spam policy.

### Decision
1. **Default Write Gate:** `INSTAGRAM_WRITE_ENABLED` defaults to `false`. Even if an access token possesses `instagram_business_manage_comments`, outward writes are blocked until `INSTAGRAM_WRITE_ENABLED=true`, connection status is `LIVE_VERIFIED`, and platform mode is `SAFE_AUTO` (or explicit owner-approved single dispatch).
2. **Ambiguous Timeout Reconciliation (`RECONCILE_PENDING`):** Whenever a write request times out or returns an ambiguous transport error:
   - The attempt state transitions immediately to `RECONCILE_PENDING`.
   - Before any retry is allowed, the adapter queries `GET /{ig-comment-id}/replies` (or `GET /{ig-media-id}/comments` for top-level ownership comments) and inspects recent comments from `@annreveals` matching the normalized text or idempotency fingerprint.
   - If found on Instagram, the local record is marked `SENT_RECONCILED` and no second `POST` is dispatched.
3. **Self-Reply Loop Guard:** Every incoming webhook and polled comment is checked against the authenticated owner's `ig_user_id` and username (`@annreveals`). Any comment authored by the owner is tagged `is_self=True` and strictly excluded from auto-reply generation or dispatch.

---

## ADR-IG-004: UK ASA & Meta Branded Content / Paid Partnership Separation from Self-Purchase Proof

### Status
**Accepted** (27 October 2026)

### Decision
- Having a verified retail receipt (`SELF_PURCHASED`, e.g., from `Empyrean` or another fragrance retailer) only proves **acquisition provenance**.
- If a post includes an affiliate link, discount code, brand commission, or gifted/sponsored arrangement, the Instagram package **must** require Meta's native **Paid Partnership label** (`is_paid_partnership`) and a prominent upfront **`Ad`** disclosure per UK ASA / CAP Code rules, and **must never** claim "not an ad".
