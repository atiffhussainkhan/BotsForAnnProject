# Agent Alpha — Official TikTok Platform Access, Policy & Integration Specialist (`README.md`)

**Agent ID:** `Agent Alpha (Agent 1)`  
**System:** Ann Reveals AI Manager (`ARAIM` v4.0)  
**Account Protected:** `@annreveals`  
**Status:** Sandbox Contract Verified (`100%` Unit Test Pass) | Live Production API: `AWAITING_APPROVAL` (`TIKTOK_WRITE_ENABLED=false`)

---

## 1. Mission Overview

Agent Alpha owns the official TikTok platform integration, primary-source policy verification, webhook ingestion security, and fail-closed adapter implementation for **Ann Reveals AI Manager (v4.0)**.

### Core Principles Enforced
1. **Zero Unofficial Automation:** Never scrape, automate browsers, extract cookies, bypass CAPTCHAs, or call undocumented mobile APIs.
2. **Truthful Capability Reporting:** Every capability is classified strictly as `VERIFIED_ACTIVE`, `AWAITING_APPROVAL`, `UNAVAILABLE`, or `UNKNOWN`. Because the **March 20, 2026 TikTok Accounts API v1.3 access application** requires external approval from TikTok (`BLK-TT-001`), live comment read/write capabilities report `AWAITING_APPROVAL` (`Draft only`) until live tokens with approved scopes are present.
3. **Permanent Third-Party Commenting Prohibition:** Automated commenting on friends' or third-party creators' posts (`comment_on_nonowned_post`) and follow-list scraping (`get_following_posts`) are permanently `UNAVAILABLE` and raise `PermissionPolicyError`.
4. **Fail-Closed Resiliency:** `TIKTOK_WRITE_ENABLED=false` by default. Any `401 Unauthorized` or `403 Forbidden` immediately downgrades the adapter to `DRAFT` mode and sets the connection badge to `Needs reconnect` (`NFR-10`).

---

## 2. Deliverable Inventory

| Category | File Path | Description |
| :--- | :--- | :--- |
| **Agent Governance** | [`agents/tiktok/DECISIONS.md`](DECISIONS.md) | Architectural Decision Records (`ADR-TT-001` to `ADR-TT-005`) |
| **Agent Governance** | [`agents/tiktok/BLOCKERS.md`](BLOCKERS.md) | March 20, 2026 TikTok Accounts API gate & mitigations (`BLK-TT-001` to `BLK-TT-004`) |
| **Agent Governance** | [`agents/tiktok/CHANGELOG.md`](CHANGELOG.md) | Audit trail of all Agent Alpha deliverables |
| **Primary Research** | [`research/tiktok/source-register.md`](../../research/tiktok/source-register.md) | Dated (27 Oct 2026) verification of 7 official TikTok documentation sources |
| **Primary Research** | [`research/tiktok/capability-matrix.csv`](../../research/tiktok/capability-matrix.csv) | Machine-readable matrix of all 12 TikTok capabilities, scopes, and statuses |
| **Primary Research** | [`research/tiktok/approval-checklist.md`](../../research/tiktok/approval-checklist.md) | Plain-English step-by-step owner guide for the March 20, 2026 Accounts API application |
| **Documentation** | [`docs/api-matrix-tiktok.md`](../../docs/api-matrix-tiktok.md) | Complete human-readable TikTok API matrix & endpoint reference |
| **Documentation** | [`docs/provider-contracts/tiktok.md`](../../docs/provider-contracts/tiktok.md) | Provider-neutral interface specification, error handling & security contract |
| **Documentation** | [`docs/TIKTOK_APPLICATION_EVIDENCE.md`](../../docs/TIKTOK_APPLICATION_EVIDENCE.md) | Ready-to-paste application answers & review evidence packet for TikTok portal |
| **System Design** | [`design/tiktok/sequence-diagrams.md`](../../design/tiktok/sequence-diagrams.md) | Mermaid sequence diagrams for OAuth, Webhooks/Idempotency, and Fail-Closed Downgrade |
| **Backend Code** | [`apps/backend/integrations/tiktok/__init__.py`](../../apps/backend/integrations/tiktok/__init__.py) | Package exports for TikTok integration |
| **Backend Code** | [`apps/backend/integrations/tiktok/models.py`](../../apps/backend/integrations/tiktok/models.py) | Standard-library dataclasses, enums, exceptions, and capability statuses |
| **Backend Code** | [`apps/backend/integrations/tiktok/webhook.py`](../../apps/backend/integrations/tiktok/webhook.py) | HMAC-SHA256 webhook signature verifier, timestamp freshness & replay guard |
| **Backend Code** | [`apps/backend/integrations/tiktok/adapter.py`](../../apps/backend/integrations/tiktok/adapter.py) | Production `TikTokAdapter` with allowlist, backoff, circuit breaker, and sandbox fixtures |
| **Backend Code** | [`apps/backend/integrations/tiktok/tiktok-capabilities.json`](../../apps/backend/integrations/tiktok/tiktok-capabilities.json) | Runtime capability & scope configuration manifest |
| **Verification** | [`reports/tiktok-live-access-proof.md`](../../reports/tiktok-live-access-proof.md) | Truthful live access vs. sandbox verification report |
| **Test Suite** | [`tests/tiktok/test_tiktok_adapter.py`](../../tests/tiktok/test_tiktok_adapter.py) | Standard-library `unittest` suite covering all safety, policy, and resiliency invariants |

---

## 3. Running Verification Tests

The entire TikTok integration and test suite uses only the Python 3.9+ standard library (`unittest`, `hmac`, `hashlib`, `json`, `urllib`, `dataclasses`) with zero external dependencies required:

```bash
python3 -m unittest discover -s tests/tiktok -v
```
