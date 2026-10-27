# TRANSPARENT COST MODEL & MONTHLY BUDGET CEILING (FR-050 / NFR-07)

**Project:** Ann Reveals AI Manager (`ARAIM` v4.0)
**Hard Monthly Ceiling:** **£30.00 / month** (enforced in code by `BudgetGuard`)
**Spend Incurred to Date:** **£0.00** (Zero paid services provisioned without explicit owner consent)

---

## 1. Recommended Cloud Hosting Options (FR-039)

To ensure `@annreveals` never has to leave her Lenovo laptop or Android phone switched on, **Ann Reveals AI Manager** is packaged as a single containerised modular monolith (`docker-compose.yml`, `infra/deploy/render.yaml`, `infra/deploy/fly.toml`) that runs 24/7 in the cloud with automatic crash recovery and HTTPS.

| Option | Provider & Architecture | Monthly Cost (GBP est.) | Pros for a Non-Technical Owner | Tradeoffs |
|---|---|---|---|---|
| **Option A (Recommended Primary)** | **Render.com Managed Web Service + Managed Disk / Neon Serverless Postgres** | **£5.50 – £7.00 / month** ($7/mo starter web service + $0 free-tier Neon Postgres or persistent SQLite volume) | Zero server maintenance, automatic HTTPS certificate, 1-click GitHub connection, automatic restart on crash | Cold start on free tier (eliminated on £5.50/mo Starter plan) |
| **Option B (Alternative PaaS)** | **Fly.io Shared-CPU-1x VM (London `lhr` region) + 3GB Encrypted Volume** | **£4.20 – £6.50 / month** | Hosted in London (`lhr`) for UK GDPR proximity, fast webhook response, built-in daily volume snapshots | Slightly more detailed initial web dashboard than Render |
| **Option C (Alternative Managed VPS)** | **Hetzner Cloud CX22 / DigitalOcean Basic Droplet (London)** | **£4.00 – £5.00 / month** | Fixed monthly price with generous 40GB SSD storage for receipt PDFs | Requires automated unattended OS security updates (configured in our `infra/` scripts) |

---

## 2. Itemised Monthly Operating Budget (Low-to-Moderate Volume)

Assuming **3,000 inbound comments/month**, **30 new videos checked/month**, **40 receipt OCR/extractions/month**, and **150 creator watchlist drafts/month**:

| Cost Category | Service / Component | Unit Pricing Basis | Estimated Monthly Usage | Estimated Monthly Cost (GBP) | Hard Cap Setting (GBP) |
|---|---|---|---|---|---|
| **1. Cloud Hosting & Compute** | Managed Web Service + Worker (Render Starter or Fly.io `lhr`) | Fixed monthly instance | 24/7 continuous (730 hrs) | **£5.60** | £10.00 |
| **2. Database & Encrypted Receipt Storage** | Managed Postgres (Neon Free Tier) + 5GB Encrypted Object/Volume Storage | £0.12 / GB-month | < 2 GB receipts & audit logs | **£0.50** | £3.00 |
| **3. AI Generation (Gemini 2.5 Flash)** | Google Gemini Flash API via pluggable adapter | ~£0.08 per 1,000 comment replies (input + output tokens) | 3,000 replies + 60 content checklists (~1.8M tokens) | **£0.45** | **£5.00** (Auto-downgrades to template/draft mode at £5.00) |
| **4. Owner Alert Notifications** | Dashboard Web Push (Free) + Resend/Postmark Transactional Email (Free tier: 3,000 emails/mo) | £0.00 up to 3,000 emails/month | ~40 daily digests & urgent alerts/month | **£0.00** | £2.00 |
| **5. Automated Encrypted Backups** | Daily compressed & encrypted snapshot retention (30 days) | Included in storage volume / GitHub private release artifact | 30 daily snapshots | **£0.30** | £2.00 |
| **TOTAL ESTIMATED MONTHLY COST** | **All-in Managed Cloud Operation** | — | — | **£6.85 / month** | **Hard Ceiling: £30.00 / month** |

---

## 3. Automated Cost Protection Controls (`BudgetGuard`)

1. **Per-1,000-Reply Cost Estimator:** Every AI operation records exact input/output token counts and calculates real-time GBP cost (`~£0.08 per 1,000 replies`).
2. **Soft Warning Threshold (80% of Cap):** Sends a single plain-English owner notification when monthly AI or total spend reaches 80% of the configured cap.
3. **Hard Stop / Automatic Fallback (100% of Cap):** If the monthly AI budget cap (default `£5.00` AI sub-cap or `£30.00` total ceiling) is reached, `BudgetGuard` immediately disables paid LLM API calls and switches the reply engine to **Zero-Cost Deterministic Template / Draft Mode** (using the 1,200+ vetted Ann Reveals reply variations).
4. **No Silent Escalation:** The system can never autonomously upgrade to a paid tier or switch to an expensive frontier model without explicit owner confirmation in Settings.
