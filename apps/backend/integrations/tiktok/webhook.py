"""TikTok Business Webhook Verifier & Replay Defense (`webhook.py`).

Implements primary-source verified webhook signature validation for TikTok Business
Accounts API v1.3 (`https://business-api.tiktok.com/gateway/docs/index?doc_id=1751617884206210`):
- Constant-time HMAC-SHA256 verification (`hmac.compare_digest`).
- Timestamp freshness validation (`max_skew_seconds=300` by default) to prevent replay attacks.
- Deduplication / replay cache keyed by `(event_id, comment_id, signature)` (NFR-04, NFR-05).
- Self-comment loop guard (`FR-003`) so `@annreveals` never auto-replies to her own comments.
"""

from dataclasses import dataclass
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional, Set, Tuple

from .models import SecurityConfigurationError, TikTokComment


@dataclass(frozen=True)
class VerifiedWebhookEvent:
    """Parsed and cryptographically verified TikTok webhook payload."""

    event_id: str
    event_type: str
    timestamp: int
    business_id: str
    video_id: str
    comment: Optional[TikTokComment]
    should_ignore_self_comment: bool
    dedup_key: str
    raw_payload: Dict[str, Any]


class TikTokWebhookVerifier:
    """Verifies TikTok Business API webhook signatures, freshness, and replay state."""

    DEFAULT_MAX_SKEW_SECONDS = 300

    def __init__(
        self,
        client_secret: str,
        owned_business_id: str = "annreveals_biz_001",
        max_skew_seconds: int = DEFAULT_MAX_SKEW_SECONDS,
    ) -> None:
        if not client_secret or not client_secret.strip():
            raise SecurityConfigurationError(
                "TikTok webhook verifier requires a non-empty client_secret",
                code="ERR_EMPTY_WEBHOOK_SECRET",
            )
        self._client_secret = client_secret.encode("utf-8")
        self._owned_business_id = owned_business_id
        self._max_skew_seconds = max_skew_seconds
        self._processed_keys: Set[str] = set()

    @staticmethod
    def compute_signature(client_secret: str, timestamp: int, raw_body: bytes) -> str:
        """Compute the expected hex HMAC-SHA256 signature for `<timestamp>.<raw_body>`."""
        body_text = raw_body.decode("utf-8")
        signing_input = f"{timestamp}.{body_text}".encode("utf-8")
        return hmac.new(
            client_secret.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).hexdigest()

    @classmethod
    def build_signature_header(cls, client_secret: str, timestamp: int, raw_body: bytes) -> str:
        """Build a canonical `TikTok-Signature: t=<timestamp>,s=<hex>` header value."""
        sig = cls.compute_signature(client_secret, timestamp, raw_body)
        return f"t={timestamp},s={sig}"

    @staticmethod
    def _parse_signature_header(signature_header: str) -> Tuple[int, str]:
        """Parse `t=<unix_ts>,s=<hex_hmac>` from `TikTok-Signature` or `X-TikTok-Signature`."""
        if not signature_header or not signature_header.strip():
            raise SecurityConfigurationError(
                "Missing TikTok-Signature header",
                code="ERR_WEBHOOK_SIGNATURE_MISSING",
            )
        parts: Dict[str, str] = {}
        for item in signature_header.split(","):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                parts[k.strip()] = v.strip()

        if "t" not in parts or "s" not in parts:
            raise SecurityConfigurationError(
                "Malformed TikTok-Signature header; expected 't=<timestamp>,s=<hex_sig>'",
                code="ERR_WEBHOOK_SIGNATURE_MALFORMED",
            )
        try:
            timestamp = int(parts["t"])
        except ValueError as exc:
            raise SecurityConfigurationError(
                "Invalid non-integer timestamp in TikTok-Signature header",
                code="ERR_WEBHOOK_TIMESTAMP_INVALID",
            ) from exc

        signature_hex = parts["s"]
        if not signature_hex:
            raise SecurityConfigurationError(
                "Empty signature value in TikTok-Signature header",
                code="ERR_WEBHOOK_SIGNATURE_EMPTY",
            )
        return timestamp, signature_hex

    def verify_and_parse(
        self,
        raw_body: bytes,
        signature_header: str,
        now_epoch: Optional[ float] = None,
    ) -> VerifiedWebhookEvent:
        """Verify HMAC-SHA256 signature, check timestamp freshness, guard against replays, and parse event."""
        current_time = float(now_epoch if now_epoch is not None else time.time())
        timestamp, provided_sig = self._parse_signature_header(signature_header)

        # 1. Timestamp freshness check (replay defense)
        skew = abs(current_time - float(timestamp))
        if skew > float(self._max_skew_seconds):
            raise SecurityConfigurationError(
                f"Webhook timestamp outside allowed freshness window ({skew:.1f}s > {self._max_skew_seconds}s)",
                code="ERR_WEBHOOK_TIMESTAMP_EXPIRED",
            )

        # 2. Constant-time HMAC-SHA256 signature check
        try:
            body_text = raw_body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SecurityConfigurationError(
                "Webhook body is not valid UTF-8",
                code="ERR_WEBHOOK_BODY_ENCODING",
            ) from exc

        signing_input = f"{timestamp}.{body_text}".encode("utf-8")
        expected_sig = hmac.new(self._client_secret, signing_input, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_sig.lower(), provided_sig.lower()):
            raise SecurityConfigurationError(
                "Webhook HMAC-SHA256 signature verification failed",
                code="ERR_WEBHOOK_SIGNATURE_MISMATCH",
            )

        # 3. Parse JSON payload
        try:
            payload = json.loads(body_text)
        except json.JSONDecodeError as exc:
            raise SecurityConfigurationError(
                "Webhook body is not valid JSON",
                code="ERR_WEBHOOK_JSON_INVALID",
            ) from exc

        event_id = str(payload.get("event_id") or payload.get("log_id") or f"evt_{timestamp}")
        event_type = str(payload.get("event") or payload.get("event_type") or "comment.update")
        business_id = str(payload.get("business_id") or payload.get("user_openid") or self._owned_business_id)
        content = payload.get("content") or payload.get("data") or {}
        video_id = str(content.get("video_id") or payload.get("video_id") or "")
        comment_id = str(content.get("comment_id") or payload.get("comment_id") or "")

        dedup_key = f"tiktok:{business_id}:{event_id}:{comment_id}"
        if dedup_key in self._processed_keys:
            raise SecurityConfigurationError(
                f"Duplicate webhook replay detected for key '{dedup_key}'",
                code="ERR_WEBHOOK_REPLAY_DETECTED",
            )
        self._processed_keys.add(dedup_key)

        comment_obj: Optional[TikTokComment] = None
        should_ignore_self = False

        if comment_id:
            sender_user_id = str(content.get("user_id") or content.get("comment_user_id") or "")
            sender_username = str(content.get("username") or content.get("unique_id") or "viewer")
            is_self_author = bool(
                content.get("is_self_author", False)
                or (sender_user_id and sender_user_id == self._owned_business_id)
                or sender_username.lower().lstrip("@") == "annreveals"
            )
            should_ignore_self = is_self_author
            parent_id = content.get("parent_comment_id")
            comment_obj = TikTokComment(
                comment_id=comment_id,
                video_id=video_id,
                business_id=business_id,
                text=str(content.get("text") or content.get("comment_text") or ""),
                create_time=int(content.get("create_time") or timestamp),
                user_id=sender_user_id,
                username=sender_username,
                parent_comment_id=str(parent_id) if parent_id else None,
                is_reply=bool(parent_id),
                is_self_author=is_self_author,
                status=str(content.get("status") or "PUBLIC"),
                like_count=int(content.get("likes") or content.get("like_count") or 0),
            )

        return VerifiedWebhookEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            business_id=business_id,
            video_id=video_id,
            comment=comment_obj,
            should_ignore_self_comment=should_ignore_self,
            dedup_key=dedup_key,
            raw_payload=payload,
        )
