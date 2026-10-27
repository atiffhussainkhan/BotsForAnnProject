# Agent Charlie (Agent 3) — Autonomous Conversational Intelligence, Creator-Network, and Content Studio Specialist

**Owner Handle:** `@annreveals`  
**Subsystem Scope:** `apps/backend/ai/`, `apps/backend/creator_assistant/`, `research/ai/`, `design/ai/`, `reports/quality-evaluation.md`, `tests/ai/`  
**Requirements Covered:** FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, FR-017, FR-022, FR-037, FR-050, FR-054, NFR-06, NFR-07.

---

## 1. Mission Overview

Agent Charlie powers the conversational intelligence, safety classification, grounded fragrance knowledge base, 1,200+ combinatorial reply variation taxonomy, and the Owner-in-the-Loop Creator Watchlist & Friends Content Assistant for the **Ann Reveals AI Manager (v4.0)**.

### Core Architectural Guarantees
1. **Sincere UK English Soft-Luxury Voice (`@annreveals`):** Warm, helpful, concise, feminine soft-luxury tone using authentic UK spelling (`favourite`, `vapour`, `colour`, `organise`, `centre`, `lovely`) and natural phrasing (`on my skin`, `dry-down`, `wear test`). Never robotic, never pushy or promotional by default.
2. **Strict Grounding & Zero Fabrication (`fragrance_kb.py` + `reply_engine.py`):**
   - Never invents fragrance notes, concentrations, prices, retailers, or longevity hours.
   - If a perfume's wear-time has **not** been formally wear-tested by Ann (`wear_time_hours=None`), the engine explicitly states that Ann has not finished a full wear-time test yet and shares only verified notes/impressions.
   - Separates **acquisition provenance** (`SELF_PURCHASED`, `PR_GIFTED`, `LOANED`, `UNKNOWN`) from **commercial relationship** (`NONE`, `AFFILIATE`, `PAID_COLLAB`, `TIKTOK_SHOP`, `GIFTED_INCENTIVE`). Never outputs `"not an ad"` when an affiliate link or commercial incentive is active.
3. **Untrusted Social Input & Prompt-Injection Defense (`prompt_guard.py`):**
   - Every social media comment, bio, or post caption is treated as untrusted external data.
   - Detects instruction overrides (`ignore previous instructions`), system prompt extraction, roleplay hijacks, raw URL/phishing injection, XSS/SQLi payloads, and hidden Unicode control characters.
   - Immediately escalates any flagged input to `HIGH_RISK` / `BLOCK` with `needs_human=True` and `eligible_for_auto=False`.
4. **14-Category Deterministic + Heuristic Classifier (`classifier.py`):**
   - Covers all 14 required FR-004 intents: `compliment`, `question`, `product_notes`, `longevity`, `price`, `where_to_buy`, `sensitive_health_skin`, `complaint`, `troll`, `threat`, `explicit_content`, `suspicious_link`, `partnership_request`, and `uncertain_other`.
   - Includes multilingual language detection (`en`, `fr`, `es`, `ar`, `de`, `it`, `pt`, `ur`, `hi`) and deterministic risk tiering (`SAFE`, `REVIEW`, `HIGH_RISK`, `BLOCK`).
5. **1,200+ Structured Reply Variation Catalog & Near-Duplicate Guard (`template_catalog.py`):**
   - Generates >1,200 distinct, natural reply variations across categories, tone profiles, openings, grounded body clauses, and closings.
   - Enforces token Jaccard + character 3-gram cosine similarity checking (`duplicate_similarity < 0.72`) against recent replies to prevent repetitive bot-like behaviour on TikTok and Instagram.
6. **Lawful Creator Watchlist & Friends Content Assistant (`apps/backend/creator_assistant/`):**
   - Strictly forbids follow-list scraping, private mobile APIs, or automated bulk third-party commenting (`THIRD_PARTY_AUTOCOMMENT=false`).
   - Ingests friend posts only via owner-submitted URLs, authorised RSS/webhook feeds, or manual curation.
   - Generates 2–4 distinct, non-generic draft comments grounded in the friend's actual post caption and fragrance notes, paired with one-tap copy + native platform deep links and daily notification caps.
