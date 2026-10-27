# Agent Delta (`content-integrity`) — Active Blockers & External Dependencies

**Agent:** Agent Delta (Agent 4 — Purchase Evidence, UK Advertising Compliance, Dual-Platform Preflight, and Appeals Specialist)
**Last Updated:** 27 October 2026

---

## 1. Internal Engineering Blockers
- **None.** All Python modules in `apps/backend/provenance/`, `apps/backend/compliance/`, and `apps/backend/appeals/` are implemented using the Python 3.9+ standard library with zero external runtime blockers and 100% passing unit tests.

---

## 2. External Owner & Platform Dependencies (Non-Blocking for Code Delivery, Required for Live Operation)

| ID | Dependency / Gate | Affected Requirement | Safe Fallback Implemented |
| :--- | :--- | :--- | :--- |
| **BLK-D01** | **Owner Confirmation of `"Experian"` vs `"Empyrean"` Receipts** | FR-019, FR-051 | Raw label `merchant_label_raw="Experian"` is preserved. Normalizer holds merchant in `AMBIGUOUS_MERCHANT_EXPERIAN_EMPYREAN` state and blocks `"Verified Self-Purchase from Empyrean Parfums"` public copy until the owner clicks confirm (`owner_verified=True`) in the Vault UI. |
| **BLK-D02** | **Platform Native Commercial Content Toggle APIs** | FR-024, FR-026, FR-048 | Neither Meta nor TikTok allows third-party tools to bypass creator acceptance of Branded Content / Commercial Content terms in-app. Content Studio generates step-by-step native toggle instructions and one-tap `"Copy Caption & Open App"` workflow. |
| **BLK-D03** | **First-Party Comment Publishing Scopes (`video.comment` / `instagram_manage_comments`)** | FR-025, FR-055 | Until write scopes are approved and `TIKTOK_WRITE_ENABLED` / `INSTAGRAM_WRITE_ENABLED` are set to `true`, optional first-party ownership comments remain in `DRAFT_ONLY` copy-paste mode. |
| **BLK-D04** | **Platform Appeal Submission Portals** | FR-032, FR-033, Rule G6 | Neither TikTok nor Meta provides a public API for submitting policy appeals. `AppealsPacketBuilder` exports a complete, PII-redacted markdown/JSON evidence packet for the owner to submit manually inside the native app (`SUBMITTED_BY_USER`). |
