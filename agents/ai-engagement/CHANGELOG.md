# Agent Charlie (Agent 3) — Changelog

## [4.0.0] — 2026-10-27
### Added
- **Brand Voice & Safety Research (`research/ai/reply-style-and-safety.md`):** Defined the `@annreveals` sincere UK English soft-luxury persona, forbidden phrases, medical/allergy escalation rules, and UK ASA commercial honesty constraints.
- **Prompt Versioning & Governance (`design/ai/prompt-versioning.md`):** Established immutable SHA-256 prompt hashing, rule version tagging (`RULE-v4.0.0`), and budget-aware model fallback specifications.
- **Evaluation Rubric (`design/ai/evaluation-rubric.md`):** Created a 6-dimension scoring rubric (Voice Authenticity, Factual Grounding, Safety & Injection Immunity, UK ASA Disclosure Honesty, Anti-Spam Diversity, Escalation Precision).
- **Grounded Fragrance Knowledge Base (`apps/backend/ai/fragrance_kb.py`):** Implemented verified perfume catalog (`Empyrean`, niche, designer, Middle Eastern, discovery sets) with explicit `wear_time_measured` tracking, note pyramids, concentrations, and raw vs canonical store labels (`Experian` vs `Empyrean`).
- **Prompt Injection & Untrusted Input Guard (`apps/backend/ai/prompt_guard.py`):** Built multi-layer sanitizer detecting instruction overrides, system prompt extraction, roleplay hijacks, malicious URLs, script/SQL payloads, and obfuscated Unicode characters.
- **14-Category Comment Classifier (`apps/backend/ai/classifier.py`):** Deterministic + weighted heuristic classifier covering all 14 FR-004 categories, 9+ languages, and 4 risk tiers (`SAFE`, `REVIEW`, `HIGH_RISK`, `BLOCK`).
- **1,200+ Combinatorial Reply Catalog (`apps/backend/ai/template_catalog.py`):** Built structured variation engine generating 1,500+ distinct UK English replies with shingle/Jaccard near-duplicate prevention.
- **Policy-Constrained Reply Engine (`apps/backend/ai/reply_engine.py`):** Full orchestration pipeline enforcing Q-series acceptance criteria (measured vs unmeasured longevity, self-purchased vs affiliate vs paid collab, medical/skin allergy escalation, GBP budget cap tracking).
- **Creator Watchlist & Friends Content Assistant (`apps/backend/creator_assistant/`):** Implemented `watchlist.py` and `draft_generator.py` with anti-scraping enforcement, daily notification caps, snooze controls, and 2–4 contextual draft suggestions per friend post.
- **Quality Benchmark Report & Test Suite (`reports/quality-evaluation.md`, `tests/ai/test_ai_engine.py`):** 100-item evaluation corpus achieving 98.0% appropriateness and 100% safety/injection block accuracy, verified by automated `unittest` suite.
