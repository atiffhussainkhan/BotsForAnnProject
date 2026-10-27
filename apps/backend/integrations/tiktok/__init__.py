"""Official TikTok Integration Package for Ann Reveals AI Manager (v4.0).

Exports the standard-library-only `TikTokAdapter`, `TikTokWebhookVerifier`,
and all models, capability enums, and policy exceptions.
"""

from .adapter import ALLOWED_OUTBOUND_HOSTS, BACKOFF_SCHEDULE_SECONDS, TikTokAdapter
from .models import (
    CapabilityStatus,
    CircuitBreakerOpenError,
    CommentWriteResult,
    ConnectionBadge,
    DispatchState,
    OperationalMode,
    PermissionPolicyError,
    ProviderResponse,
    PublishPostRequest,
    PublishPostResult,
    RateLimitExceededError,
    ScopeNotApprovedError,
    SecurityConfigurationError,
    TikTokComment,
    TikTokIntegrationError,
    TikTokPost,
    TikTokProfile,
    TokenGrant,
    WriteDisabledError,
)
from .webhook import TikTokWebhookVerifier, VerifiedWebhookEvent

__all__ = [
    "ALLOWED_OUTBOUND_HOSTS",
    "BACKOFF_SCHEDULE_SECONDS",
    "CapabilityStatus",
    "CircuitBreakerOpenError",
    "CommentWriteResult",
    "ConnectionBadge",
    "DispatchState",
    "OperationalMode",
    "PermissionPolicyError",
    "ProviderResponse",
    "PublishPostRequest",
    "PublishPostResult",
    "RateLimitExceededError",
    "ScopeNotApprovedError",
    "SecurityConfigurationError",
    "TikTokAdapter",
    "TikTokComment",
    "TikTokIntegrationError",
    "TikTokPost",
    "TikTokProfile",
    "TikTokWebhookVerifier",
    "TokenGrant",
    "VerifiedWebhookEvent",
    "WriteDisabledError",
]
