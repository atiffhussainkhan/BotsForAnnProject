"""
14-Category Deterministic + Heuristic Comment Classifier (`classifier.py`).

Implements FR-002, FR-003, FR-004, FR-009:
- Classifies incoming social comments into the exact 14 required PRD categories:
  1. `compliment`
  2. `question`
  3. `product_notes`
  4. `longevity`
  5. `price`
  6. `where_to_buy`
  7. `sensitive_health_skin`
  8. `complaint`
  9. `troll`
  10. `threat`
  11. `explicit_content`
  12. `suspicious_link`
  13. `partnership_request`
  14. `uncertain_other`
- Detects language (`en`, `fr`, `es`, `ar`, `de`, `it`, `pt`, `ur`, `hi`).
- Assigns deterministic risk tiers (`SAFE`, `REVIEW`, `HIGH_RISK`, `BLOCK`).
- Flags provenance/sponsorship questions ("Was this gifted?", "Did you buy this yourself?")
  so the reply engine can apply orthogonal acquisition + commercial disclosure logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Tuple

from .prompt_guard import PromptGuard, PromptGuardResult


VALID_COMMENT_CATEGORIES: Tuple[str, ...] = (
    "compliment",
    "question",
    "product_notes",
    "longevity",
    "price",
    "where_to_buy",
    "sensitive_health_skin",
    "complaint",
    "troll",
    "threat",
    "explicit_content",
    "suspicious_link",
    "partnership_request",
    "uncertain_other",
)

VALID_RISK_TIERS: Tuple[str, ...] = (
    "SAFE",
    "REVIEW",
    "HIGH_RISK",
    "BLOCK",
)


@dataclass(frozen=True)
class ClassificationResult:
    """Structured output of the 14-category comment classifier."""

    category: str
    language: str
    risk_tier: str
    confidence: float
    needs_human: bool
    eligible_for_auto: bool
    asks_provenance_or_gifted: bool = False
    is_self_comment: bool = False
    prompt_guard: Optional[PromptGuardResult] = None
    matched_signals: Tuple[str, ...] = field(default_factory=tuple)


# Language detection patterns
_ARABIC_SCRIPT_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F]")
_DEVANAGARI_SCRIPT_RE = re.compile(r"[\u0900-\u097F]")
_FRENCH_MARKERS_RE = re.compile(
    r"\b(?:j'adore|merci|beaucoup|parfum|combien|magnifique|bonjour|coucou|odeur|tenue|acheter|c'est)\b",
    re.IGNORECASE,
)
_SPANISH_MARKERS_RE = re.compile(
    r"\b(?:encanta|gracias|hermosa|perfume|cuánto|cuanto|dónde|donde|comprar|huele|duración|hola|preciosa)\b",
    re.IGNORECASE,
)
_GERMAN_MARKERS_RE = re.compile(
    r"\b(?:danke|wunderschön|parfüm|wieviel|gekauft|haltbarkeit|duft|liebe\s+grüße|toll)\b",
    re.IGNORECASE,
)
_ITALIAN_MARKERS_RE = re.compile(
    r"\b(?:grazie|bellissima|profumo|quanto\s+costa|dove\s+comprare|stupendo|ciao)\b",
    re.IGNORECASE,
)
_PORTUGUESE_MARKERS_RE = re.compile(
    r"\b(?:obrigada|obrigado|linda|maravilhosa|onde\s+comprar|quanto\s+custa|cheiro)\b",
    re.IGNORECASE,
)

# Priority-ordered safety & intent patterns
_THREAT_RE = re.compile(
    r"\b(?:i\s+will\s+(?:kill|hurt|find|stalk|dox|destroy|attack|beat)\s+you|watch\s+your\s+back|know\s+where\s+you\s+live|hope\s+you\s+die|kill\s+yourself|kys|swat\s+you|burn\s+your\s+house|bomb\s+threat)\b",
    re.IGNORECASE,
)

_EXPLICIT_RE = re.compile(
    r"\b(?:onlyfans|nudes|sex\s+tape|porn|xxx|nsfw|explicit\s+pics|sugar\s+daddy\s+pays|camgirl|blowjob|f\*ck\s+me|send\s+nudes|18\+\s+link)\b",
    re.IGNORECASE,
)

_SENSITIVE_HEALTH_SKIN_RE = re.compile(
    r"\b(?:rash|allergic|allergy|allergies|hives|eczema|dermatitis|psoriasis|asthma|migraine|headache|pregnant|pregnancy|breastfeeding|toddler|baby|infant|child|children|kids\s+skin|chemical\s+burn|blister|swelling|itching|itchy|burning\s+sensation|red\s+patches|anaphylaxis|sensitive\s+skin\s+reaction|safe\s+for\s+babies)\b",
    re.IGNORECASE,
)

_TROLL_RE = re.compile(
    r"\b(?:you\s+have\s+terrible\s+taste|paid\s+shill|fake\s+reviewer|clown|pathetic|ugly|shut\s+up|nobody\s+cares|trash\s+channel|worst\s+creator|stop\s+posting|delusional|sellout|liar|fraud|cringe\s+af|stupid\s+b\*tch|idiot)\b",
    re.IGNORECASE,
)

_COMPLAINT_RE = re.compile(
    r"\b(?:arrived\s+broken|leaking\s+bottle|fake\s+bottle|counterfeit|watered\s+down|never\s+received|customer\s+service|refund|scammed\s+by|ruined\s+my\s+clothes|stained\s+my\s+silk|giveaway\s+was\s+rigged|disappointed\s+with\s+your\s+recommendation|waste\s+of\s+money)\b",
    re.IGNORECASE,
)

_PARTNERSHIP_RE = re.compile(
    r"\b(?:collab|collaboration|partnership|sponsored\s+post\s+opportunity|pr\s+package|pr\s+list|send\s+you\s+a\s+bottle|gifting\s+campaign|media\s+kit|ambassador|brand\s+deal|check\s+your\s+dms\s+for\s+business|email\s+us\s+for\s+collab|work\s+with\s+you|marketing\s+team|paid\s+promotion)\b",
    re.IGNORECASE,
)

_PROVENANCE_GIFTED_QUESTION_RE = re.compile(
    r"\b(?:was\s+this\s+gifted|is\s+this\s+gifted|did\s+you\s+buy\s+this|did\s+they\s+send\s+you\s+this|bought\s+with\s+your\s+own\s+money|is\s+this\s+an\s+ad|is\s+this\s+sponsored|pr\s+or\s+purchased|did\s+you\s+pay\s+for\s+this)\b",
    re.IGNORECASE,
)

_LONGEVITY_RE = re.compile(
    r"\b(?:how\s+long\s+does\s+.{1,50}?\s+last|longevity|wear\s*time|lasting\s+power|sillage|projection|does\s+.{1,40}?\s+last\s+all\s+day|hours\s+on\s+skin|fade\s+quickly|beast\s+mode|how\s+many\s+hours|tenue|duración)\b",
    re.IGNORECASE,
)

_PRICE_RE = re.compile(
    r"\b(?:how\s+much\s+(?:is|was|does)\b|what\s+is\s+the\s+price|price|cost|expensive|affordable|how\s+many\s+pounds|£\d+|\$\d+|worth\s+the\s+money|combien|cuánto\s+cuesta|quanto\s+costa)\b",
    re.IGNORECASE,
)

_WHERE_TO_BUY_RE = re.compile(
    r"\b(?:where\s+(?:can\s+i|did\s+you|to)\s+(?:buy|get|find|order|purchase)|which\s+(?:store|shop|website|retailer)|stockist|available\s+in\s+the\s+uk|deliver\s+to\s+uk|link\s+to\s+buy|where\s+is\s+this\s+from|où\s+acheter|dónde\s+comprar)\b",
    re.IGNORECASE,
)

_PRODUCT_NOTES_RE = re.compile(
    r"\b(?:what\s+are\s+the\s+notes|fragrance\s+notes|scent\s+notes|what\s+does\s+.{1,50}?\s+smell\s+like|is\s+it\s+(?:sweet|woody|floral|oudy|powdery|fresh|spicy|vanilla|musky|boozy|gourmand)|top\s+notes|dry\s*down|base\s+notes|smell\s+more\s+like\s+rose\s+or\s+oud)\b",
    re.IGNORECASE,
)

_QUESTION_RE = re.compile(
    r"(?:\?|\b(?:which\s+one|what\s+perfume\s+is\s+this|would\s+you\s+recommend|better\s+for\s+(?:winter|summer|date\s+night|office|bridal|everyday)|can\s+men\s+wear|is\s+it\s+unisex|layer\s+this\s+with|dupe\s+for|similar\s+to)\b)",
    re.IGNORECASE,
)

_COMPLIMENT_RE = re.compile(
    r"\b(?:love\s+(?:your|this)|so\s+(?:elegant|classy|helpful|lovely|beautiful|pretty|gorgeous|aesthetic|calming|soothing)|my\s+favourite\s+creator|best\s+perfume\s+reviews|always\s+trust\s+your|stunning\s+video|amazing\s+collection|queen|angel|thank\s+you\s+for\s+sharing|obsessed\s+with\s+your\s+content|j'adore|me\s+encanta|bellissima|wunderschön)\b",
    re.IGNORECASE,
)


def detect_language(text: str) -> str:
    """Detect primary ISO 639-1 language code of a social comment."""
    if not text or not text.strip():
        return "en"
    if _ARABIC_SCRIPT_RE.search(text):
        return "ar"
    if _DEVANAGARI_SCRIPT_RE.search(text):
        return "hi"
    if _FRENCH_MARKERS_RE.search(text):
        return "fr"
    if _SPANISH_MARKERS_RE.search(text):
        return "es"
    if _GERMAN_MARKERS_RE.search(text):
        return "de"
    if _ITALIAN_MARKERS_RE.search(text):
        return "it"
    if _PORTUGUESE_MARKERS_RE.search(text):
        return "pt"
    return "en"


class CommentClassifier:
    """
    Deterministic + weighted heuristic 14-category classifier for @annreveals comments.
    """

    def __init__(
        self,
        owner_handles: Tuple[str, ...] = ("@annreveals", "annreveals"),
        prompt_guard: Optional[PromptGuard] = None,
    ) -> None:
        self.owner_handles = tuple(h.lower().lstrip("@") for h in owner_handles)
        self.prompt_guard = prompt_guard or PromptGuard()

    def classify(
        self,
        comment_text: str,
        author_handle: str = "",
    ) -> ClassificationResult:
        """
        Classify a comment into one of the 14 required categories, detect language,
        evaluate prompt-injection safety, and determine auto-reply eligibility.
        """
        clean_author = (author_handle or "").strip().lower().lstrip("@")
        is_self = bool(clean_author and clean_author in self.owner_handles)

        guard_res = self.prompt_guard.inspect(comment_text or "")
        lang = detect_language(comment_text or "")
        signals = list(guard_res.triggered_rules)

        # Loop prevention: never reply to self (FR-003)
        if is_self:
            signals.append("SELF_COMMENT_LOOP_GUARD")
            return ClassificationResult(
                category="uncertain_other",
                language=lang,
                risk_tier="BLOCK",
                confidence=1.0,
                needs_human=False,
                eligible_for_auto=False,
                asks_provenance_or_gifted=False,
                is_self_comment=True,
                prompt_guard=guard_res,
                matched_signals=tuple(signals),
            )

        # Prompt injection / XSS / SQLi -> immediate BLOCK + human review
        if guard_res.injection_detected or guard_res.script_or_sql_detected:
            return ClassificationResult(
                category="suspicious_link" if guard_res.suspicious_url_detected else "troll",
                language=lang,
                risk_tier="BLOCK",
                confidence=0.99,
                needs_human=True,
                eligible_for_auto=False,
                asks_provenance_or_gifted=False,
                is_self_comment=False,
                prompt_guard=guard_res,
                matched_signals=tuple(signals),
            )

        text = guard_res.sanitized_text
        asks_gifted = bool(_PROVENANCE_GIFTED_QUESTION_RE.search(text))
        if asks_gifted:
            signals.append("ASKS_PROVENANCE_OR_GIFTED")

        # 1. Threat (highest severity)
        if _THREAT_RE.search(text):
            signals.append("MATCH_THREAT")
            return ClassificationResult(
                category="threat",
                language=lang,
                risk_tier="BLOCK",
                confidence=0.98,
                needs_human=True,
                eligible_for_auto=False,
                asks_provenance_or_gifted=asks_gifted,
                prompt_guard=guard_res,
                matched_signals=tuple(signals),
            )

        # 2. Explicit content
        if _EXPLICIT_RE.search(text):
            signals.append("MATCH_EXPLICIT")
            return ClassificationResult(
                category="explicit_content",
                language=lang,
                risk_tier="BLOCK",
                confidence=0.97,
                needs_human=True,
                eligible_for_auto=False,
                asks_provenance_or_gifted=asks_gifted,
                prompt_guard=guard_res,
                matched_signals=tuple(signals),
            )

        # 3. Suspicious link
        if guard_res.suspicious_url_detected:
            signals.append("MATCH_SUSPICIOUS_LINK")
            return ClassificationResult(
                category="suspicious_link",
                language=lang,
                risk_tier="BLOCK",
                confidence=0.96,
                needs_human=True,
                eligible_for_auto=False,
                asks_provenance_or_gifted=asks_gifted,
                prompt_guard=guard_res,
                matched_signals=tuple(signals),
            )

        # 4. Sensitive health / skin / pregnancy / child safety (FR-009)
        if _SENSITIVE_HEALTH_SKIN_RE.search(text):
            signals.append("MATCH_SENSITIVE_HEALTH_SKIN")
            return ClassificationResult(
                category="sensitive_health_skin",
                language=lang,
                risk_tier="HIGH_RISK",
                confidence=0.96,
                needs_human=True,
                eligible_for_auto=False,
                asks_provenance_or_gifted=asks_gifted,
                prompt_guard=guard_res,
                matched_signals=tuple(signals),
            )

        # 5. Troll / harassment / abuse
        if _TROLL_RE.search(text):
            signals.append("MATCH_TROLL")
            return ClassificationResult(
                category="troll",
                language=lang,
                risk_tier="HIGH_RISK",
                confidence=0.93,
                needs_human=True,
                eligible_for_auto=False,
                asks_provenance_or_gifted=asks_gifted,
                prompt_guard=guard_res,
                matched_signals=tuple(signals),
            )

        # 6. Complaint / dispute / counterfeit accusation
        if _COMPLAINT_RE.search(text):
            signals.append("MATCH_COMPLAINT")
            return ClassificationResult(
                category="complaint",
                language=lang,
                risk_tier="HIGH_RISK",
                confidence=0.92,
                needs_human=True,
                eligible_for_auto=False,
                asks_provenance_or_gifted=asks_gifted,
                prompt_guard=guard_res,
                matched_signals=tuple(signals),
            )

        # 7. Partnership / PR / sponsorship request
        if _PARTNERSHIP_RE.search(text):
            signals.append("MATCH_PARTNERSHIP_REQUEST")
            return ClassificationResult(
                category="partnership_request",
                language=lang,
                risk_tier="REVIEW",
                confidence=0.94,
                needs_human=True,
                eligible_for_auto=False,
                asks_provenance_or_gifted=asks_gifted,
                prompt_guard=guard_res,
                matched_signals=tuple(signals),
            )

        # 8. Provenance / "Was this gifted?" question -> classify as `question` with provenance signal
        if asks_gifted:
            return ClassificationResult(
                category="question",
                language=lang,
                risk_tier="SAFE",
                confidence=0.95,
                needs_human=False,
                eligible_for_auto=True,
                asks_provenance_or_gifted=True,
                prompt_guard=guard_res,
                matched_signals=tuple(signals),
            )

        # 9. Longevity / wear-time / projection
        if _LONGEVITY_RE.search(text):
            signals.append("MATCH_LONGEVITY")
            return ClassificationResult(
                category="longevity",
                language=lang,
                risk_tier="SAFE",
                confidence=0.94,
                needs_human=False,
                eligible_for_auto=True,
                asks_provenance_or_gifted=False,
                prompt_guard=guard_res,
                matched_signals=tuple(signals),
            )

        # 10. Price / cost
        if _PRICE_RE.search(text):
            signals.append("MATCH_PRICE")
            return ClassificationResult(
                category="price",
                language=lang,
                risk_tier="SAFE",
                confidence=0.93,
                needs_human=False,
                eligible_for_auto=True,
                asks_provenance_or_gifted=False,
                prompt_guard=guard_res,
                matched_signals=tuple(signals),
            )

        # 11. Where to buy / stockist
        if _WHERE_TO_BUY_RE.search(text):
            signals.append("MATCH_WHERE_TO_BUY")
            return ClassificationResult(
                category="where_to_buy",
                language=lang,
                risk_tier="SAFE",
                confidence=0.93,
                needs_human=False,
                eligible_for_auto=True,
                asks_provenance_or_gifted=False,
                prompt_guard=guard_res,
                matched_signals=tuple(signals),
            )

        # 12. Product notes / scent profile
        if _PRODUCT_NOTES_RE.search(text):
            signals.append("MATCH_PRODUCT_NOTES")
            return ClassificationResult(
                category="product_notes",
                language=lang,
                risk_tier="SAFE",
                confidence=0.94,
                needs_human=False,
                eligible_for_auto=True,
                asks_provenance_or_gifted=False,
                prompt_guard=guard_res,
                matched_signals=tuple(signals),
            )

        # 13. General fragrance question
        if _QUESTION_RE.search(text):
            signals.append("MATCH_QUESTION")
            return ClassificationResult(
                category="question",
                language=lang,
                risk_tier="SAFE",
                confidence=0.89,
                needs_human=False,
                eligible_for_auto=True,
                asks_provenance_or_gifted=False,
                prompt_guard=guard_res,
                matched_signals=tuple(signals),
            )

        # 14. Compliment / positive appreciation
        if _COMPLIMENT_RE.search(text) or any(
            emoji in text for emoji in ("❤️", "😍", "🥰", "✨", "🤍", "🌸", "💖", "👏")
        ):
            signals.append("MATCH_COMPLIMENT")
            return ClassificationResult(
                category="compliment",
                language=lang,
                risk_tier="SAFE",
                confidence=0.92,
                needs_human=False,
                eligible_for_auto=True,
                asks_provenance_or_gifted=False,
                prompt_guard=guard_res,
                matched_signals=tuple(signals),
            )

        # 15. Fallback: uncertain_other -> requires human review
        signals.append("FALLBACK_UNCERTAIN_OTHER")
        return ClassificationResult(
            category="uncertain_other",
            language=lang,
            risk_tier="REVIEW",
            confidence=0.45,
            needs_human=True,
            eligible_for_auto=False,
            asks_provenance_or_gifted=False,
            prompt_guard=guard_res,
            matched_signals=tuple(signals),
        )
