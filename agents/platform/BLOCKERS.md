# Agent Echo (Agent 5) — External Blockers & Risk Register

**Agent:** Agent Echo — Principal Platform Architect, Security Engineer, SRE, and Quality Assurance Specialist  
**Status:** Zero internal engineering blockers. External platform approval gates are tracked below with safe fallbacks active by default.

---

## External Platform Approval Gates (Non-Blocking to v4.0 Delivery)

| Gate ID | Platform / Dependency | Current State | Impact | Enforced Safe Fallback in v4.0 |
|---|---|---|---|---|
| **EXT-BLK-01** | **TikTok Official Comment Reply Write Scope** | `Awaiting review` (`TIKTOK_WRITE_ENABLED=false`) | Direct automated comment replies on TikTok cannot be dispatched until TikTok Developer Portal approves write scope. | System defaults to `Connected: read only` / `Awaiting review` badge and `DRAFT` mode with 1-tap **"Copy Reply & Open TikTok"** fallback (`FR-043`, `FR-048`). |
| **EXT-BLK-02** | **Meta Instagram Graph API Live Mode Review (`instagram_manage_comments`)** | `Awaiting review` (`INSTAGRAM_WRITE_ENABLED=false`) | Automated comment publishing outside app tester accounts requires Meta App Review completion. | System defaults to `DRAFT` mode with live scope inspection; only enables `SAFE_AUTO` when `instagram_manage_comments` is verified active (`FR-006`). |
| **EXT-BLK-03** | **Third-Party Creator Post Auto-Commenting API** | Unavailable / Restricted (`THIRD_PARTY_AUTOCOMMENT=false`) | Neither TikTok nor Instagram provides a general API for automated commenting on arbitrary third-party creator videos without explicit business/ad permissions. | Friends & Creator Watchlist operates in strict **Owner-in-the-Loop** mode: generates 2–4 contextual draft comments and provides a 1-tap **"Copy & Open App"** workflow (`FR-014`, `FR-017`). |

---

## Resolved Engineering Risks

- **Zero Non-Stdlib Runtime Fragility:** All `apps/backend/platform_ops/` modules use pure Python 3.9+ standard library primitives (`hashlib`, `hmac`, `secrets`, `threading`, `json`, `zipfile`, `sqlite3`) so CI, Docker, and local verification run with 100% determinism.
- **Zero Unbounded Spend:** `BudgetGuard` enforces a hard £30.00/month ceiling (£5.00/month AI sub-cap) before any LLM invocation.
