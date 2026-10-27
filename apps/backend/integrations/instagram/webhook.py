"""Meta / Instagram Webhook Security, Challenge Handshake, and Comment Event Parser.

Implements:
- GET subscription challenge verification (`hub.mode=subscribe`, `hub.verify_token`, `hub.challenge`).
- POST `X-Hub-Signature-256` HMAC-SHA256 verification using `hmac.compare_digest`.
- Event deduplication (`instagram:{account_id}:{comment_id}`).
- Self-reply loop guard (`is_self=True` when comment author is `@annreveals`).
"""

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import InstagramComment, InstagramError


class WebhookVerificationError(InstagramError):
    """Raised when webhook challenge or X-Hub-Signature-256 verification fails."""


@dataclass
class WebhookProcessingResult:
    """Result of parsing and filtering an incoming Instagram webhook batch."""

    actionable_comments: List[InstagramComment]
    skipped_self_comments: List[InstagramComment]
    skipped_duplicates: List[str]


class InstagramWebhookVerifier:
    """Verifies Meta `X-Hub-Signature-256` headers, hub challenges, and comment events."""

    SIGNATURE_PREFIX = "sha256="

    def __init__(
        self,
        app_secret: str,
        verify_token: str,
        owner_ig_user_id: str = "17841400008460056",
        owner_username: str = "annreveals",
    ) -> None:
        if not app_secret:
            raise ValueError("app_secret must be non-empty for HMAC-SHA256 webhook verification")
        if not verify_token:
            raise ValueError("verify_token must be non-empty for hub challenge verification")
        self.app_secret = app_secret
        self.verify_token = verify_token
        self.owner_ig_user_id = str(owner_ig_user_id).strip()
        self.owner_username = owner_username.strip().lstrip("@").lower()
        self._seen_event_keys: Set[str] = set()

    def verify_subscription_challenge(
        self,
        hub_mode: Optional[str],
        hub_verify_token: Optional[str],
        hub_challenge: Optional[str],
    ) -> Tuple[int, str]:
        """Validate Meta GET webhook subscription handshake.

        Returns `(200, hub_challenge)` on success, or raises `WebhookVerificationError` (403).
        """
        if hub_mode != "subscribe" or not hub_verify_token or hub_challenge is None:
            raise WebhookVerificationError(
                "Invalid webhook subscription parameters: hub.mode must be 'subscribe'",
                status_code=403,
            )

        token_matches = hmac.compare_digest(
            hub_verify_token.encode("utf-8"),
            self.verify_token.encode("utf-8"),
        )
        if not token_matches:
            raise WebhookVerificationError(
                "Webhook verify_token mismatch",
                status_code=403,
            )

        return 200, str(hub_challenge)

    @staticmethod
    def compute_signature(app_secret: str, raw_body: bytes) -> str:
        """Compute canonical `sha256=<hex>` header value for raw payload bytes."""
        digest = hmac.new(
            app_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={digest}"

    def verify_signature(self, raw_body: bytes, signature_header: Optional[str]) -> bool:
        """Verify Meta `X-Hub-Signature-256` header in constant time (`NFR-05`)."""
        if not signature_header or not signature_header.startswith(self.SIGNATURE_PREFIX):
            raise WebhookVerificationError(
                "Missing or malformed X-Hub-Signature-256 header",
                status_code=401,
            )

        expected = self.compute_signature(self.app_secret, raw_body)
        if not hmac.compare_digest(signature_header.strip(), expected):
            raise WebhookVerificationError(
                "X-Hub-Signature-256 HMAC verification failed",
                status_code=401,
            )
        return True

    def is_self_authored(self, author_id: str, author_username: str) -> bool:
        """Return True if the comment author is the owner (`@annreveals`)."""
        normalized_user = author_username.strip().lstrip("@").lower()
        if self.owner_ig_user_id and str(author_id).strip() == self.owner_ig_user_id:
            return True
        if self.owner_username and normalized_user == self.owner_username:
            return True
        return False

    def process_webhook_payload(
        self,
        raw_body: bytes,
        signature_header: Optional[str],
    ) -> WebhookProcessingResult:
        """Verify signature, parse `instagram` comment events, deduplicate, and block self-reply loops."""
        self.verify_signature(raw_body, signature_header)

        try:
            payload: Dict[str, Any] = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WebhookVerificationError(
                f"Malformed JSON webhook payload: {exc}",
                status_code=400,
            ) from exc

        if payload.get("object") != "instagram":
            return WebhookProcessingResult(
                actionable_comments=[],
                skipped_self_comments=[],
                skipped_duplicates=[],
            )

        actionable: List[InstagramComment] = []
        skipped_self: List[InstagramComment] = []
        skipped_dupes: List[str] = []

        for entry in payload.get("entry", []):
            account_id = str(entry.get("id") or self.owner_ig_user_id)
            entry_time = str(entry.get("time") or "")
            for change in entry.get("changes", []):
                if change.get("field") != "comments":
                    continue
                val: Dict[str, Any] = change.get("value") or {}
                comment_id = str(val.get("id") or "").strip()
                if not comment_id:
                    continue

                dedupe_key = f"instagram:{account_id}:{comment_id}"
                if dedupe_key in self._seen_event_keys:
                    skipped_dupes.append(dedupe_key)
                    continue
                self._seen_event_keys.add(dedupe_key)

                from_obj: Dict[str, Any] = val.get("from") or {}
                author_id = str(from_obj.get("id") or "")
                author_username = str(from_obj.get("username") or val.get("username") or "")
                media_obj: Dict[str, Any] = val.get("media") or {}
                post_id = str(media_obj.get("id") or val.get("media_id") or "")
                parent_id = val.get("parent_id")
                is_self = self.is_self_authored(author_id, author_username)

                comment = InstagramComment(
                    comment_id=comment_id,
                    post_id=post_id,
                    text=str(val.get("text") or ""),
                    author_id=author_id,
                    author_username=author_username,
                    timestamp=str(val.get("timestamp") or entry_time),
                    parent_id=str(parent_id) if parent_id else None,
                    hidden=bool(val.get("hidden", False)),
                    like_count=int(val.get("like_count", 0) or 0),
                    is_self=is_self,
                    raw=val,
                )

                if is_self:
                    skipped_self.append(comment)
                else:
                    actionable.append(comment)

        return WebhookProcessingResult(
            actionable_comments=actionable,
            skipped_self_comments=skipped_self,
            skipped_duplicates=skipped_dupes,
        )
