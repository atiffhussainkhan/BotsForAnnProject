"""Meta / Instagram Developer Platform Integration Package (`ARAIM` v4.0 — Agent Bravo)."""

from .adapter import InstagramAdapter
from .models import (
    AuthRoute,
    AutomationMode,
    CommentDispatchRecord,
    ConnectionStatus,
    DispatchState,
    InstagramAmbiguousTimeoutError,
    InstagramAuthError,
    InstagramComment,
    InstagramError,
    InstagramPost,
    InstagramProfile,
    InstagramRateLimitError,
    PaginatedResult,
    SelfReplyForbiddenError,
    UnsupportedCapabilityError,
    WriteGateDisabledError,
)
from .webhook import InstagramWebhookVerifier, WebhookProcessingResult, WebhookVerificationError

__all__ = [
    "AuthRoute",
    "AutomationMode",
    "CommentDispatchRecord",
    "ConnectionStatus",
    "DispatchState",
    "InstagramAdapter",
    "InstagramAmbiguousTimeoutError",
    "InstagramAuthError",
    "InstagramComment",
    "InstagramError",
    "InstagramPost",
    "InstagramProfile",
    "InstagramRateLimitError",
    "InstagramWebhookVerifier",
    "PaginatedResult",
    "SelfReplyForbiddenError",
    "UnsupportedCapabilityError",
    "WebhookProcessingResult",
    "WebhookVerificationError",
    "WriteGateDisabledError",
]
