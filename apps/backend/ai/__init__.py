"""
Ann Reveals AI Manager (v4.0) — Conversational Intelligence & Grounded Reply Package.

Exports:
- `FragranceRecord`, `FragranceKnowledgeBase`, `DEFAULT_FRAGRANCE_CATALOG`
- `PromptGuard`, `PromptGuardResult`, `redact_pii`
- `CommentClassifier`, `ClassificationResult`, `VALID_COMMENT_CATEGORIES`, `detect_language`
- `TemplateCatalog`, `ReplyTemplateVariation`, `compute_similarity`
- `ReplyEngine`, `ReplyEngineOutput`, `BudgetTracker`, `PROMPT_HASH`, `RULE_VERSION`
"""

from .classifier import (
     VALID_COMMENT_CATEGORIES,
    VALID_RISK_TIERS,
    ClassificationResult,
    CommentClassifier,
    detect_language,
)
from .fragrance_kb import (
    DEFAULT_FRAGRANCE_CATALOG,
    FragranceKnowledgeBase,
    FragranceRecord,
)
from .prompt_guard import PromptGuard, PromptGuardResult, redact_pii
from .reply_engine import (
    DETERMINISTIC_MODEL_VERSION,
    GEMINI_FLASH_MODEL_VERSION,
    PROMPT_HASH,
    RULE_VERSION,
    BudgetTracker,
    ReplyEngine,
    ReplyEngineOutput,
)
from .template_catalog import (
    ReplyTemplateVariation,
    TemplateCatalog,
    compute_similarity,
)

__all__ = [
    "BudgetTracker",
    "ClassificationResult",
    "CommentClassifier",
    "DEFAULT_FRAGRANCE_CATALOG",
    "DETERMINISTIC_MODEL_VERSION",
    "FragranceKnowledgeBase",
    "FragranceRecord",
    "GEMINI_FLASH_MODEL_VERSION",
    "PROMPT_HASH",
    "PromptGuard",
    "PromptGuardResult",
    "RULE_VERSION",
    "ReplyEngine",
    "ReplyEngineOutput",
    "ReplyTemplateVariation",
    "TemplateCatalog",
    "VALID_COMMENT_CATEGORIES",
    "VALID_RISK_TIERS",
    "compute_similarity",
    "detect_language",
    "redact_pii",
]
