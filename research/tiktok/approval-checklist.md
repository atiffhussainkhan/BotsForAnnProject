# Owner Step-by-Step Guide: March 20, 2026 TikTok Accounts API Approval Checklist (`approval-checklist.md`)

**For:** Ann (`@annreveals`)  
**Prepared By:** Agent Alpha (`Agent 1 — Official TikTok Platform Access, Policy, and Integration Specialist`)  
**Last Updated:** 27 October 2026  
**Estimated Time to Complete:** 20–25 minutes  

> [!IMPORTANT]
> **Why is this checklist required?**  
> Starting **March 20, 2026**, TikTok requires an official **TikTok Accounts API Access Application** before any app can read or reply to comments on your TikTok videos (`https://business-api.tiktok.com/portal/docs/accounts-api-overview/v1.3`).  
> **Good news:** Your **Ann Reveals AI Manager** works right now in **Draft & One-Tap Copy Mode** even while you wait for TikTok's approval! You never have to worry about your account being put at risk.

---

## Step 1: Switch `@annreveals` to a TikTok Business Account (On Your Phone)

TikTok only allows comment management APIs for **Business Accounts** (switching is 100% free).

1. Open the **TikTok app** on your Android phone and log in to `@annreveals`.
2. Tap **Profile** (bottom right) -> tap the **Menu (☰)** icon (top right) -> tap **Settings and privacy**.
3. Tap **Account** -> tap **Switch to Business Account**.
4. Select the category **Beauty / Personal Care** (or **Shopping & Retail**) and tap **Next**.
5. **Important Music Note:** As a Business Account, always use original voiceovers or tracks from TikTok's **Commercial Music Library (CML)** so your videos are never muted for music copyright (`FR-023`, `FR-056`).

---

## Step 2: Register Your Developer Account on TikTok For Business

1. On your laptop browser, open: `https://business-api.tiktok.com/portal`
2. Click **Log In / Sign Up** and sign in using your business email for `@annreveals`.
3. Complete the basic Developer Registration form:
   - **Organization Name:** `Ann Reveals`
   - **Region:** `United Kingdom`
   - **Primary Role:** `Direct Advertiser / Creator Business (In-House Tool)`

---

## Step 3: Create the `Ann Reveals AI Manager` App

1. In the TikTok Business Developer Portal, go to **My Apps** -> click **Create App**.
2. Fill in the details from [`docs/TIKTOK_APPLICATION_EVIDENCE.md`](../../docs/TIKTOK_APPLICATION_EVIDENCE.md):
   - **App Name:** `Ann Reveals AI Manager`
   - **App Description:** *"First-party creator management, comment inbox assistant, and purchase provenance tracker for @annreveals."*
   - **Redirect URI (Callback URL):** Enter your cloud manager OAuth callback URL (e.g., `https://app.annreveals.co.uk/api/v1/oauth/tiktok/callback`).
   - **Webhook Callback URL:** Enter `https://app.annreveals.co.uk/api/v1/webhooks/tiktok`.

---

## Step 4: Submit the March 20, 2026 TikTok Accounts API v1.3 Application

1. Inside your app dashboard in the TikTok Business Portal, locate **Products / Scope Management** and select **TikTok Accounts API (v1.3)**.
2. Click **Apply for Access** (required under the **March 20, 2026** rule).
3. Tick the following scopes:
   - [x] `user.info.basic` & `user.info.profile` & `user.info.stats` *(Why needed? Lets your dashboard verify your `@annreveals` profile connection).*
   - [x] `video.list` *(Why needed? Lets the app match your own videos with the perfume you reviewed).*
   - [x] `comment.list` *(Why needed? Lets the app receive incoming viewer questions on your own videos).*
   - [x] `comment.list.manage` *(Why needed? Lets the app post approved replies to viewer questions on your own videos).*
4. **Paste the Use-Case Justification:** Copy the exact text from **Section 1, Field 2** of [`docs/TIKTOK_APPLICATION_EVIDENCE.md`](../../docs/TIKTOK_APPLICATION_EVIDENCE.md).
5. **Attach the Screen Recording:** Upload the 2-minute demo walkthrough described in **Section 2** of [`docs/TIKTOK_APPLICATION_EVIDENCE.md`](../../docs/TIKTOK_APPLICATION_EVIDENCE.md).
6. Click **Submit for Review**. (TikTok typically reviews applications within 3–7 business days).

---

## Step 5: What Happens While You Wait vs. After Approval?

| Stage | Dashboard Badge Shown | How Owned-Video Comments Work | How Friends' Posts Work |
| :--- | :--- | :--- | :--- |
| **Before / During Review (`AWAITING_APPROVAL`)** | `Awaiting review` (`Draft only`) | You can paste or preview comments in sandbox/draft mode and tap **Copy Reply & Open TikTok**. | **One-Tap Copy Draft + Open TikTok App** (Always manual & safe). |
| **After TikTok Approves Your App (`VERIFIED_ACTIVE`)** | `Connected: read only` (until you enable write) or `Live: can reply` | Incoming comments arrive automatically via Webhook; safe ordinary questions can be answered in `DRAFT` or `SAFE_AUTO` mode. | **One-Tap Copy Draft + Open TikTok App** (Third-party auto-commenting is permanently prohibited by TikTok). |
| **If TikTok Refuses or Delays Approval** | `Draft only (Manual Copy Active)` | Full **Dual-Platform Content Studio**, **Verified Purchases Vault**, **Appeal Packet Builder**, and **One-Tap Copy Reply** continue working seamlessly with zero interruption (`FR-048`, `FR-049`). | **One-Tap Copy Draft + Open TikTok App**. |
