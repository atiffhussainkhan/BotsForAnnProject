"""TikTok Integration Models, Enums, and Exceptions for Ann Reveals AI Manager (v4.0).

Built using ONLY the Python 3.9+ standard library (`dataclasses`, `enum`, `typing`).
Enforces truthful capability classification (`VERIFIED_ACTIVE`, `AWAITING_APPROVAL`,
`UNAVAILABLE`, `UNKNOWN`) and strict separation between provenance and commercial disclosure.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

T = TypeVar("T")


class CapabilityStatus(str, Enum):
    """Truthful capability states required by Agent Alpha & PRD Section 1."""

    VERIFIED_ACTIVE = "VERIFIED_ACTIVE"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class OperationalMode(str, Enum):
    """Per-platform operational mode (FR-006, FR-035)."""

    OFF = "OFF"
    DRAFT = "DRAFT"
    SAFE_AUTO = "SAFE_AUTO"
    READ_ONLY = "READ_ONLY"


class ConnectionBadge(str, Enum):
    """Truthful UI connection status badges (FR-043)."""

    NOT_CONNECTED = "Not connected"
    CONNECTED_READ_ONLY = "Connected: read only"
    AWAITING_REVIEW = "Awaiting review"
    LIVE_CAN_REPLY = "Live: can reply"
    SUSPENDED = "Suspended"
    NEEDS_RECONNECT = "Needs reconnect"


class DispatchState(str, Enum):
    """Outward write dispatch states including NFR-03 timeout reconciliation."""

    DRAFT_ONLY = "DRAFT_ONLY"
    SENT = "SENT"
    RECONCILE_PENDING = "RECONCILE_PENDING"
    BLOCKED_BY_POLICY = "BLOCKED_BY_POLICY"
    FAILED = "FAILED"


class TikTokIntegrationError(Exception):
    """Base exception for TikTok integration errors."""

    def __init__(self, message: str, code: str = "ERR_TIKTOK_GENERIC") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class PermissionPolicyError(TikTokIntegrationError):
    """Raised when an operation is permanently prohibited by platform policy or safety rules.

    Specifically enforces the permanent hard block on `comment_on_nonowned_post`
    and `get_following_posts`.
    """

    def __init__(self, message: str, code: str = "ERR_THIRD_PARTY_INTERACTION_PROHIBITED") -> None:
        super().__init__(message, code=code)


class ScopeNotApprovedError(TikTokIntegrationError):
    """Raised when an operation requires a scope that is still AWAITING_APPROVAL."""

    def __init__(self, capability: str, missing_scopes: List[str]) -> None:
        msg = (
            f"Capability '{capability}' is AWAITING_APPROVAL (March 20, 2026 TikTok Accounts API gate). "
            f"Missing approved scopes: {', '.join(missing_scopes)}"
        )
        super().__init__(msg, code="ERR_SCOPE_AWAITING_APPROVAL")
        self.capability = capability
        self.missing_scopes = missing_scopes


class WriteDisabledError(TikTokIntegrationError):
    """Raised when a strict write check fails because TIKTOK_WRITE_ENABLED=false."""

    def __init__(self, message: str = "Outbound TikTok write blocked: TIKTOK_WRITE_ENABLED=false") -> None:
        super().__init__(message, code="ERR_TIKTOK_WRITE_DISABLED")


class SecurityConfigurationError(TikTokIntegrationError):
    """Raised on outbound host allowlist violations or invalid webhook signatures."""

    def __init__(self, message: str, code: str = "ERR_SECURITY_VIOLATION") -> None:
        super().__init__(message, code=code)


class RateLimitExceededError(TikTokIntegrationError):
    """Raised on HTTP 429 with computed Retry-After + jittered backoff."""

    def __init__(self, message: str, retry_after_seconds: float) -> None:
        super().__init__(message, code="ERR_RATE_LIMIT_429")
        self.retry_after_seconds = retry_after_seconds


class CircuitBreakerOpenError(TikTokIntegrationError):
    """Raised when consecutive 5xx errors trip the upstream circuit breaker."""

    def __init__(self, message: str, open_until_epoch: float) -> None:
        super().__init__(message, code="ERR_CIRCUIT_BREAKER_OPEN")
        self.open_until_epoch = open_until_epoch


@dataclass(frozen=True)
class TikTokProfile:
    """Normalized representation of the owned @annreveals TikTok Business Account."""

    business_id: str
    handle: str
    display_name: str
    is_business_account: bool
    follower_count: int = 0
    likes_count: int = 0
    video_count: int = 0
    avatar_url: str = ""
    bio_description: str = ""


@dataclass(frozen=True)
class TikTokPost:
    """Normalized representation of an owned TikTok video post."""

    video_id: str
    business_id: str
    caption: str
    share_url: str
    create_time: int
    comment_count: int = 0
    like_count: int = 0
    view_count: int = 0
    duration_seconds: int = 0
    is_owned: bool = True


@dataclass(frozen=True)
class TikTokComment:
    """Normalized representation of a comment or reply on an owned TikTok video."""

    comment_id: str
    video_id: str
    business_id: str
    text: str
    create_time: int
    user_id: str
    username: str
    parent_comment_id: Optional[str] = None
    is_reply: bool = False
    is_self_author: bool = False
    status: str = "PUBLIC"
    like_count: int = 0


@dataclass(frozen=True)
class CommentWriteResult:
    """Outcome of creating or replying to a comment on an owned TikTok video."""

    video_id: str
    text: str
    idempotency_key: str
    dispatch_state: DispatchState
    capability_status: CapabilityStatus
    comment_id: Optional[str] = None
    parent_comment_id: Optional[str] = None
    fallback_copy_text: str = ""
    audit_note: str = ""


@dataclass(frozen=True)
class PublishPostRequest:
    """Request payload for TikTok Content Posting API v2 (FR-021, FR-026, FR-053, FR-055)."""

    video_url: str
    caption: str
    privacy_level: str = "PUBLIC_TO_EVERYONE"
    publish_to_draft_inbox: bool = True
    self_purchased: bool = False
    has_commercial_incentive: bool = False
    brand_content_toggle: bool = False
    brand_organic_toggle: bool = False
    disable_comment: bool = False


@dataclass(frozen=True)
class PublishPostResult:
    """Result of initializing or checking a TikTok video publication."""

    publish_id: str
    status: str
    dispatch_state: DispatchState
    capability_status: CapabilityStatus
    share_url: Optional[str] = None
    fallback_caption: str = ""
    commercial_disclosure_applied: bool = False
    audit_note: str = ""


@dataclass(frozen=True)
class TokenGrant:
    """OAuth 2.0 token grant and live scope inspection summary."""

    access_token: str
    refresh_token: str
    open_id: str
    expires_in: int
    granted_scopes: List[str]
    badge: ConnectionBadge
    write_scope_verified: bool
    read_scope_verified: bool


@dataclass
class ProviderResponse(Generic[T]):
    """Standardized provider-neutral response wrapper."""

    ok: bool
    capability: str
    capability_status: CapabilityStatus
    operational_mode: OperationalMode
    connection_badge: ConnectionBadge
    data: Optional[T] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    fallback_action: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
