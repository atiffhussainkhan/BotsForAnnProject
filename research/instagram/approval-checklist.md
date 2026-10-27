# Instagram Integration & Approval Checklist for `@annreveals`

**Document Purpose:** Plain-English, step-by-step instructions for connecting `@annreveals` to **Ann Reveals AI Manager (`ARAIM`)** via the official **Instagram API with Instagram Login**, plus the Meta App Review checklist if moving from Development Mode (Tester) to Live Mode.  
**Last Verified Against Meta Docs:** 27 October 2026

---

## Why We Use "Instagram API with Instagram Login"

Meta offers two ways to connect a professional Instagram account:
1. **Instagram API with Instagram Login (Selected Primary Route):** Connects directly to your `@annreveals` Instagram Creator or Business account **without** needing to create or link a Facebook Page.
2. **Instagram API with Facebook Login (Optional Fallback):** Only used if you already manage `@annreveals` through a linked Facebook Page and Meta Business Suite.

---

## Part 1: 5-Minute Account Preparation for `@annreveals` (In the Instagram App)

Meta does not allow personal Instagram accounts to use any official automation or comment-management API. Your account must be set to a free **Creator** (recommended for `@annreveals`) or **Business** account.

1. Open the **Instagram app** on your Android phone signed in as **`@annreveals`**.
2. Tap your **Profile picture** (bottom right) -> tap the **Menu (`☰`)** (top right) -> **Settings and activity**.
3. Scroll down to **For professionals** -> tap **Account type and tools**.
4. Tap **Switch to professional account** -> choose **Creator** (best for fragrance reviewers and public figures) -> select category **Creator / Beauty, Cosmetic & Personal Care**.
5. When asked "Connect to a Facebook Page?", you can tap **Skip** (because ARAIM uses **Instagram API with Instagram Login**).

---

## Part 2: Connecting `@annreveals` in Development / Single-Owner Tester Mode

Because **Ann Reveals AI Manager** is your dedicated single-owner cloud manager, you can use it immediately with your own `@annreveals` account as an **Instagram Tester** in Development Mode while keeping the app private to you:

1. **Create / Open the Meta App (`developers.facebook.com/apps`):**
   - Click **Create App** -> Choose **Other** -> Select **Business** app type -> Name it `Ann Reveals AI Manager`.
2. **Add the Instagram Product:**
   - In the left sidebar, add the **Instagram** product.
   - Choose **API setup with Instagram login**.
3. **Add `@annreveals` as an Instagram Tester:**
   - Go to **App Roles -> Roles -> Add People -> Instagram Testers** and enter `annreveals`.
   - On your phone or browser (`instagram.com` -> **Settings -> Website Permissions -> Apps and websites -> Tester Invites**), click **Accept** on the invitation from `Ann Reveals AI Manager`.
4. **Configure OAuth Redirect URI & Webhook Callback:**
   - In **Instagram -> API setup with Instagram login -> Set up Instagram business login**:
     - Copy the **Instagram App ID** and **Instagram App Secret** into ARAIM's encrypted cloud environment (`INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET`).
     - Set the **OAuth Redirect URI** to: `https://<your-araim-domain>/api/oauth/instagram/callback`
   - In **Configure Webhooks**:
     - Callback URL: `https://<your-araim-domain>/webhooks/instagram`
     - Verify Token: `<your-INSTAGRAM_WEBHOOK_VERIFY_TOKEN>`
     - Subscribe to field: **`comments`**
5. **Click "Connect Instagram" Inside ARAIM:**
   - Open the ARAIM dashboard -> **Settings -> Social Accounts -> Connect Instagram**.
   - Approve the requested scopes:
     - `instagram_business_basic` (Read your `@annreveals` profile & posts so ARAIM can link posts to your perfume library)
     - `instagram_business_manage_comments` (Read comments on your posts and, when you turn it on, post replies or first-party context comments on your own posts)
6. **Verify Connection Badge:**
   - ARAIM inspects your live token and displays:
     - `Connected: read only (Draft mode)` while `INSTAGRAM_WRITE_ENABLED=false`.
     - After you review 10 drafted replies in the inbox and flip the write toggle, the badge updates to `Live: can reply`.

---

## Part 3: Meta App Review Checklist (For Live Mode & Real-Time Webhooks)

> [!IMPORTANT]
> In Meta's platform rules, webhook deliveries for Instagram objects often require the Meta App to be switched to **Live Mode** (or tested via the App Dashboard Webhook Test button + periodic polling in Development Mode). While in Development Mode, ARAIM automatically polls `GET /{ig-media-id}/comments` on a safe schedule so zero comments are missed even before App Review completes.

To switch the Meta App to **Live Mode**, complete these steps in the Meta App Dashboard:

- [ ] **Privacy Policy URL & Terms URL:** Published on the ARAIM cloud domain (`/privacy`, `/terms`).
- [ ] **Data Deletion Instructions URL:** Published at `/data-deletion` per UK GDPR & Meta Platform rules.
- [ ] **Business Verification (if prompted by Meta):** Upload supporting identity/sole-trader verification in Meta Business Settings.
- [ ] **Permission Justifications & Screencasts:**
  - [ ] **`instagram_business_basic`:** Show the owner clicking "Connect Instagram", ARAIM displaying `@annreveals` profile metadata (`username`, `account_type: CREATOR`) and listing `@annreveals`'s recent fragrance Reels so they can be linked to verified perfume receipts.
  - [ ] **`instagram_business_manage_comments`:** Show an incoming viewer comment on an `@annreveals` Reel appearing in the ARAIM Comment Inbox, classification + safety check running, the owner reviewing/approving the reply in `DRAFT` mode (or `SAFE_AUTO` mode for low-risk compliments), and the reply appearing under the comment on Instagram.
  - [ ] **`instagram_business_manage_messages` (Optional — only if DM triage is enabled later):** Currently omitted from default v4.0 OAuth scope request to minimize approval friction.

---

## Part 4: What ARAIM Will NEVER Ask You To Do

- **Never** enter your Instagram password or 2FA code into ARAIM (login happens exclusively on `instagram.com`).
- **Never** copy browser cookies (`sessionid`) or install browser extensions that scrape Instagram.
- **Never** auto-comment on other creators' posts (`THIRD_PARTY_AUTOCOMMENT=false`). For fellow creators on your shortlist, ARAIM drafts 2–4 thoughtful replies and gives you a **Copy & Open in Instagram** button so you always post personally.
