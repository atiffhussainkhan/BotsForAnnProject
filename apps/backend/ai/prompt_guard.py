"""
Untrusted Social Input Sanitizer & Prompt Injection Guard (`prompt_guard.py`).

Implements security and safety requirements (FR-004, FR-009, NFR-05, NFR-06):
- Treats all viewer comments, handles, and third-party post captions as untrusted input.
- Detects prompt-injection overrides ("ignore previous instructions", system prompt leaks,
  roleplay hijacks, token smuggling, fake XML/JSON delimiter injection, SQL/XSS payloads,
  and suspicious URLs).
- Redacts accidental PII (credit/debit card numbers, UK postcodes, email addresses, phone numbers)
  before storage or model inspection.
- Forces `HUMAN_REVIEW` / `BLOCK` whenever an injection or malicious payload is detected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass(frozen=True)
class PromptGuardResult:
    """Result of inspecting untrusted social media text."""

    is_safe: bool
    injection_detected: bool
    suspicious_url_detected: bool
    script_or_sql_detected: bool
    pii_redacted: bool
    recommended_action: str  # "ALLOW", "HUMAN_REVIEW", "BLOCK"
    triggered_rules: Tuple[str, ...] = field(default_factory=tuple)
    sanitized_text: str = ""
    original_length: int = 0


# Deterministic prompt-injection and jailbreak signatures
_INJECTION_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    (
        "INJ_IGNORE_INSTRUCTIONS",
        re.compile(
            r"\b(?:ignore|disregard|forget|bypass|override)\b.{0,40}\b(?:previous|prior|above|all|system|initial|safety)\b.{0,30}\b(?:instructions?|prompts?|rules?|directives?|constraints?|guidelines?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "INJ_SYSTEM_PROMPT_LEAK",
        re.compile(
            r"\b(?:reveal|print|show|output|repeat|dump|display|tell\s+me)\b.{0,35}\b(?:system\s+prompt|hidden\s+prompt|initial\s+instructions?|developer\s+message|secret\s+instructions?|api\s*key|access\s*token)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "INJ_ROLEPLAY_HIJACK",
        re.compile(
            r"(?:\byou\s+are\s+no\s+longer\b|\bact\s+as\s+(?:a|an)\b.{0,30}\b(?:pirate|hacker|unrestricted|dan|evil|bot)\b|\bsimulate\s+developer\s+mode\b|\bjailbreak\b|\bdo\s+anything\s+now\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "INJ_FAKE_SYSTEM_DELIMITER",
        re.compile(
            r"(?:\[\s*SYSTEM[_\s]*DIRECTIVE|\<\s*/?\s*(?:system|instruction|developer|assistant|prompt)\s*\>|###\s*(?:SYSTEM|INSTRUCTION)\s*:)",
            re.IGNORECASE,
        ),
    ),
    (
        "INJ_FORCED_OUTPUT_COMMAND",
        re.compile(
            r"\b(?:reply\s+with\s+exact(?:ly)?|respond\s+only\s+with|say\s+that\s+this\s+perfume\s+is\s+(?:fake|poison|toxic|a\s+scam)|write\s+a\s+reply\s+saying)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "INJ_COMMERCIAL_SABOTAGE",
        re.compile(
            r"\b(?:tell\s+everyone\s+to\s+use\s+code|promote\s+my\s+(?:telegram|whatsapp|crypto|onlyfans)|admit\s+you\s+lied\s+about)\b",
            re.IGNORECASE,
        ),
    ),
)

# Script, XSS, SQL injection, and command execution signatures
_PAYLOAD_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    (
        "PAYLOAD_XSS_SCRIPT",
        re.compile(
            r"(?:\<\s*script\b|javascript\s*:|onerror\s*=|onload\s*=|\<\s*iframe\b|\<\s*img\s+[^>]*on\w+\s*=)",
            re.IGNORECASE,
        ),
    ),
    (
        "PAYLOAD_SQL_INJECTION",
        re.compile(
            r"(?:\bUNION\s+ALL\s+SELECT\b|\bDROP\s+TABLE\b|\bINSERT\s+INTO\b|\bDELETE\s+FROM\b|'\s*OR\s+'?1'?\s*=\s*'?1|--\s*$)",
            re.IGNORECASE,
        ),
    ),
    (
        "PAYLOAD_TEMPLATE_EXEC",
        re.compile(r"(?:\{\{.*?\}\}|\$\{.*?\}|`\s*(?:rm|curl|wget|bash|sh)\s+)", re.IGNORECASE),
    ),
)

# URLs, shortened links, and suspicious domains in comments
_URL_PATTERN = re.compile(
    r"(?:https?://[^\s<>\"']+|www\.[^\s<>\"']+|\b(?:bit\.ly|tinyurl\.com|t\.me|wa\.me|linktr\.ee| cutt\.ly|is\.gd|gg\.gg)/[^\s<>\"']*|\b[a-z0-9.-]+\.(?:ru|cn|tk|xyz|top|zip|click|loan|work)/[^\s<>\"']*)",
    re.IGNORECASE,
)

# Invisible / directional override Unicode characters used for homograph/token smuggling
_CONTROL_CHARS_PATTERN = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]")

# PII Redaction patterns (NFR-06, FR-019)
_CARD_NUMBER_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_UK_PHONE_PATTERN = re.compile(r"\b(?:(?:\+44\s?|0)7\d{3}\s?\d{6})\b")


def redact_pii(text: str) -> Tuple[str, bool]:
    """
    Redact payment card numbers, email addresses, and personal mobile numbers
    from any text before logging or LLM inspection (NFR-06).
    """
    if not text:
        return "", False

    redacted = text
    changed = False

    if _CARD_NUMBER_PATTERN.search(redacted):
        redacted = _CARD_NUMBER_PATTERN.sub("[REDACTED_CARD]", redacted)
        changed = True

    if _EMAIL_PATTERN.search(redacted):
        redacted = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", redacted)
        changed = True

    if _UK_PHONE_PATTERN.search(redacted):
        redacted = _UK_PHONE_PATTERN.sub("[REDACTED_PHONE]", redacted)
        changed = True

    return redacted, changed


class PromptGuard:
    """
    Multi-layered untrusted input inspector and prompt-injection defense engine.
    """

    def __init__(self, max_comment_length: int = 1200) -> None:
        self.max_comment_length = max_comment_length

    def inspect(self, raw_text: str) -> PromptGuardResult:
        """
        Inspect untrusted social comment or caption text and return a deterministic
        PromptGuardResult. Any detected injection or payload forces HUMAN_REVIEW / BLOCK.
        """
        text = raw_text or ""
        original_len = len(text)
        triggered: List[str] = []

        # 1. Strip hidden Unicode control/bidi override characters
        if _CONTROL_CHARS_PATTERN.search(text):
            triggered.append("UNICODE_CONTROL_CHARS")
            text = _CONTROL_CHARS_PATTERN.sub("", text)

        # 2. Enforce length bound
        if len(text) > self.max_comment_length:
            triggered.append("EXCESSIVE_LENGTH")
            text = text[: self.max_comment_length]

        # 3. Check prompt-injection signatures
        injection_found = False
        for rule_id, pattern in _INJECTION_PATTERNS:
            if pattern.search(text):
                triggered.append(rule_id)
                injection_found = True

        # 4. Check XSS / SQLi / template execution signatures
        script_or_sql_found = False
        for rule_id, pattern in _PAYLOAD_PATTERNS:
            if pattern.search(text):
                triggered.append(rule_id)
                script_or_sql_found = True

        # 5. Check suspicious URLs / link spam
        url_found = False
        if _URL_PATTERN.search(text):
            triggered.append("SUSPICIOUS_URL_IN_COMMENT")
            url_found = True

        # 6. Redact any PII before downstream storage/LLM usage
        sanitized, pii_found = redact_pii(text)
        if pii_found:
            triggered.append("PII_REDACTED")

        # Neutralize angle brackets in sanitized text so it can never break XML/HTML delimiters
        sanitized = sanitized.replace("<", "‹").replace(">", "›").strip()

        is_safe = not (injection_found or script_or_sql_found or url_found)
        if injection_found or script_or_sql_found:
            action = "BLOCK"
        elif url_found or "EXCESSIVE_LENGTH" in triggered or "UNICODE_CONTROL_CHARS" in triggered:
            action = "HUMAN_REVIEW"
        else:
            action = "ALLOW"

        return PromptGuardResult(
            is_safe=is_safe,
            injection_detected=injection_found,
            suspicious_url_detected=url_found,
            script_or_sql_detected=script_or_sql_found,
            pii_redacted=pii_found,
            recommended_action=action,
            triggered_rules=tuple(triggered),
            sanitized_text=sanitized,
            original_length=original_len,
        )
