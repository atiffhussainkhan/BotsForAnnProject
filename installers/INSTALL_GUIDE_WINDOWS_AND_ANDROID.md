# Ann Reveals AI Manager v4.0 — Single Application Installation Guide (Windows Laptop & Android Mobile)

This repository delivers a **single unified application** (`AnnRevealsApplication`) that installs and runs on both your **Windows 10/11 Laptop** and your **Android Mobile Phone**, allowing you to sign in / configure your **Instagram (`@annreveals`)** and **TikTok (`@annreveals`)** accounts directly inside the app and start automatic comment management (`SAFE_AUTO`).

---

## 💻 1. How to Install & Run on Your Windows Laptop

You have **three zero-friction ways** to install and launch the application on Windows:

### Method A — One-Click Windows Desktop Installer (Creates Desktop & Start Menu Icon)
1. Open the `installers/windows/` folder.
2. Right-click **`Install-AnnReveals-Windows.ps1`** and select **Run with PowerShell** (or double-click **`Start-AnnReveals-Windows.bat`**).
3. It automatically creates the **"Ann Reveals AI Manager"** icon on your Windows Desktop and Start Menu, starts the local `AnnRevealsApplication` backend (`backend/main.py`), and opens the frameless native desktop app window.

### Method B — Install as a Native Windows App via Edge / Chrome PWA
1. Once the app window is open, click the **`📲 Install App (Windows & Android)`** button in the top bar.
2. Click **Install** — Windows pins **Ann Reveals AI Manager** directly to your Windows Taskbar and Start Menu as a standalone application.

### Method C — Zero-Dependency Portable File
- Double-click **`dist/AnnRevealsAIManager-Portable.html`** on any Windows laptop. It includes an embedded offline/local engine (`ARAIM_PORTABLE_STATE_V4`) so every screen, account login, and auto-pilot simulation works even without Python installed.

---

## 📱 2. How to Install & Run on Your Android Mobile Phone

### Method A — Install Native Android App Icon via Chrome (WebAPK / PWA)
1. Open your hosted **Ann Reveals AI Manager** URL (or local Wi-Fi URL `http://<laptop-ip>:8080`) in **Google Chrome on Android**.
2. Tap the **`📲 Install App (Windows & Android)`** button in the top header (or tap Chrome's menu `⋮` → **Install app / Add to Home screen**).
3. Android compiles and installs **Ann Reveals AI Manager** (`uk.co.annreveals.aimanager`) onto your Android app drawer and home screen with full-screen standalone launch.

### Method B — Portable Offline Android App (`AnnRevealsAIManager-Portable.html`)
1. Send **`dist/AnnRevealsAIManager-Portable.html`** to your Android phone (via WhatsApp, Google Drive, USB, or email).
2. Tap the file to open it in Chrome on Android — all 9 screens, in-app Instagram & TikTok account sign-in, and the Auto-Pilot loop run directly on your phone.

### Method C — Native Android APK Build (Trusted Web Activity / Capacitor)
- Pre-configured manifests are included in `installers/android/twa-manifest.json` and `installers/android/capacitor.config.json` (`packageId: uk.co.annreveals.aimanager`) for packaging a signed `.apk` / `.aab` bundle with `@bubblewrap/cli` or `@capacitor/android`.

---

## 🔐 3. How In-App Instagram & TikTok Login + Automatic Bot (`SAFE_AUTO`) Works

1. Open **Ann Reveals AI Manager** on your Windows Laptop or Android Mobile.
2. On **Screen 1 (Home & Controls)**, locate the **Instagram (`@annreveals`)** and **TikTok (`@annreveals`)** In-App Account Setup cards (or click the green **`🚀 1-Click Sign In Both Accounts & Start Automatic Bot`** button at the top).
3. Enter or confirm:
   - Your **Instagram Handle** (`@annreveals`), **Meta App / Business ID**, and **OAuth Access Token**.
   - Your **TikTok Handle** (`@annreveals`), **TikTok Client Key / Business ID**, and **OAuth Access Token**.
4. Click **`🔐 Sign In & Start Instagram Auto-Bot (SAFE_AUTO)`** and **`🔐 Sign In & Start TikTok Auto-Bot (SAFE_AUTO)`**.
5. **Automatic Operation Starts Immediately:**
   - `AnnRevealsApplication.configure_and_connect_account()` verifies your scopes, switches the platform state to **`SAFE_AUTO`**, and starts the background Auto-Pilot loop (`/api/v1/autopilot/tick`).
   - Incoming comments on your posts are automatically ingested, checked against `PromptGuard`, matched against your **Verified Purchases Vault** (`Empyrean Parfums`), and answered automatically in your authentic UK voice (`Auto-Replies Sent` counter updates live).
   - High-risk comments (medical/allergy/rash claims, hostility, prompt injection) are **never** auto-replied; they are automatically blocked and escalated for your review.
   - At any moment, tapping **`🛑 EMERGENCY STOP (ALL WRITES)`** on your phone or laptop halts all outgoing replies in under 1 second.
