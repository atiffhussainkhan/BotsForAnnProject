# Agent Charlie (Agent 3) — Blockers & External Dependencies

## Current Internal Blockers
- **None.** All AI classification, prompt-injection defense, grounded fragrance knowledge base, 1,200+ template catalog, reply generation engine, and Creator Watchlist modules are fully implemented and verified with Python 3.9+ standard library tests.

## External Policy & Live API Gates (Tracked Truthfully per PRD Section 1)
| Gate ID | External Dependency | Impact on Agent Charlie | Enforced Fallback Behaviour |
|---|---|---|---|
| **GATE-EXT-01** | `GEMINI_API_KEY` (Optional Cloud LLM API Key) | Live Gemini Flash phrasing refinement requires an active API key and available monthly GBP budget (`FR-050`, `NFR-07`). | Automatically uses the deterministic grounded synthesis & 1,200+ variation catalog with zero downtime or error. |
| **GATE-EXT-02** | TikTok & Meta Official Comment Publish Scopes | Auto-sending `SAFE_AUTO` replies requires verified platform write tokens (`Agent Alpha` / `Agent Bravo`). | `reply_engine.py` outputs `eligible_for_auto` metadata, while the platform router defaults to `DRAFT` mode until live write scopes are verified. |
| **GATE-EXT-03** | Third-Party Creator Comment Publishing API | Neither TikTok nor Instagram provides a general API scope for automated commenting on other creators' videos. | `creator_assistant` permanently sets `THIRD_PARTY_AUTOCOMMENT=False` and provides 2–4 contextual drafts with one-tap copy + native app deep-link (`FR-014`, `FR-017`). |
