# Monthly Cloud & AI Cost Forecast Report (`ARAIM` v4.0)

**Financial & Capacity Architect:** Agent Echo (Agent 5)  
**Date:** 27 October 2026  
**Hard Monthly Ceiling:** **£30.00 / month** (`FR-039`, `FR-050`, `NFR-07`)

---

## 1. Itemised Monthly Spend Model

| Cost Component | Provider / Tier | Routine Monthly Spend (£) | Hard Cap Allocation (£) | Notes |
|---|---|---|---|---|
| **Cloud App + Background Worker** | Render Starter / Fly.io `shared-cpu-1x` (512MB RAM, London/Frankfurt) | £7.00 | £7.00 | Fixed monthly container cost |
| **Encrypted Persistent Volume & Backups** | 2 GB Managed NVMe Volume + Encrypted Snapshot Storage | £0.50 | £1.50 | Stores SQLite WAL DB, encrypted tokens, and redacted receipts |
| **AI Comment Classification & Reply Drafting** | Lightweight Frontier Tier (~340 tokens/reply @ £0.41 per 1,000 replies) | £1.25 – £3.50 | **£5.00 (Hard AI Sub-Cap)** | Covers ~3,000 to 12,000 replies/month before deterministic template fallback |
| **Contingency / Bandwidth Headroom** | Outbound webhook & PWA traffic | £0.00 | £16.50 | Reserved buffer beneath £30.00 ceiling |
| **TOTAL MONTHLY SPEND** | **All-In Managed Cloud Product** | **£8.75 – £11.00 / mo** | **≤ £30.00 / mo (Hard Cap)** | **63%–70% below the £30.00 ceiling** |

---

## 2. Per-1,000-Reply Cost Estimator (`BudgetGuard.estimate_cost_per_1000_replies`)

- **Average Input Prompt (System + Brand Voice + Product Grounding + Comment):** `250 tokens`
- **Average Output Reply (Concise UK-English Draft):** `90 tokens`
- **Total per Reply:** `340 tokens`
- **Estimated Cost per 1,000 Replies:** **£0.4080 (~41 pence per 1,000 replies)**
- **Replies Supported Under £5.00/Month AI Sub-Cap:** **~12,250 AI replies/month**
- **Cost Beyond 12,250 Replies/Month:** **£0.00** (automatically switches to the built-in 1,000+ deterministic UK-English seed template library in `DRAFT` mode).

---

## 3. Hard Cap Enforcement Verification (`NFR-07`)

`BudgetGuard` in [`apps/backend/platform_ops/budget_guard.py`](file:///Users/mac/Downloads/bots%20for%20ann/apps/backend/platform_ops/budget_guard.py) enforces two independent circuit breakers before every LLM call:
1. **AI Monthly Sub-Cap (£5.00):** Blocks paid LLM calls as soon as cumulative AI token spend reaches £5.00.
2. **Total Monthly Ceiling (£30.00):** Blocks paid calls if `hosting + storage + other + AI` reaches £30.00.
3. **Automatic Safe Downgrade:** Immediately transitions any `SAFE_AUTO` platform to `DRAFT` mode and serves deterministic brand-aligned templates at £0 marginal cost.
