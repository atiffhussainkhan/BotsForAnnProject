"""Data models, enums, and exception types for the Instagram Platform integration.

Uses only the Python 3.9+ standard library (`dataclasses`, `enum`, `typing`).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ConnectionStatus(str, Enum):
    """Truthful connection status badges required by FR-043."""

    NOT_CONNECTED = "Not connected"
    CONNECTED_READ_ONLY = "Connected: read only"
    AWAITING_REVIEW = "Awaiting review"
    LIVE_CAN_REPLY = "Live: can reply"
    SUSPENDED = "Suspended"
    NEEDS_RECONNECT = "Needs reconnect"


class AutomationMode(str, Enum):
    """Per-platform operating mode required by FR-006 and FR-035."""

    OFF = "OFF"
    DRAFT = "DRAFT"
    SAFE_AUTO = "SAFE_AUTO"


class DispatchState(str, Enum):
    """Outward write state machine for effectively-once comment dispatch (NFR-03)."""

    DRAFT_ONLY = "DRAFT_ONLY"
    IN_FLIGHT = "IN_FLIGHT"
    RECONCILE_PENDING = "RECONCILE_PENDING"
    SENT = "SENT"
    SENT_RECONCILED = "SENT_RECONCILED"
    FAILED = "FAILED"


class AuthRoute(str, Enum):
    """Official Meta authentication pathways."""

    INSTAGRAM_LOGIN = "instagram_login"
    FACEBOOK_LOGIN = "facebook_login"


class InstagramError(Exception):
    """Base exception for Instagram adapter errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[int] = None,
        error_subcode: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.error_subcode = error_subcode


class UnsupportedCapabilityError(InstagramError):
    """Raised when calling capabilities permanently unsupported by Meta APIs (e.g. non-owned post commenting)."""


class WriteGateDisabledError(InstagramError):
    """Raised when a write operation is attempted while INSTAGRAM_WRITE_ENABLED=false or mode != SAFE_AUTO."""


class SelfReplyForbiddenError(InstagramError):
    """Raised when attempting to reply to a comment authored by @annreveals (loop prevention FR-003)."""


class InstagramAuthError(InstagramError):
    """Raised on 401/403 or Meta OAuth error codes 190/10/200; triggers NEEDS_RECONNECT + DRAFT fail-safe."""


class InstagramRateLimitError(InstagramError):
    """Raised on HTTP 429 or Meta rate-limit codes (4, 17, 32, 613)."""

    def __init__(
        self,
        message: str,
        retry_after_seconds: int = 30,
        status_code: Optional[int] = 429,
        error_code: Optional[int] = None,
    ) -> None:
        super().__init__(message, status_code=status_code, error_code=error_code)
        self.retry_after_seconds = retry_after_seconds


class InstagramAmbiguousTimeoutError(InstagramError):
    """Raised when a POST comment/reply times out and transitions to RECONCILE_PENDING."""


@dataclass
class InstagramProfile:
    """Normalized Instagram Professional (Creator/Business) account metadata."""

    ig_user_id: str
    username: str
    name: str
    account_type: str
    followers_count: int = 0
    follows_count: int = 0
    media_count: int = 0
    profile_picture_url: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_professional(self) -> bool:
        return self.account_type.upper() in {"CREATOR", "MEDIA_CREATOR", "BUSINESS"}


@dataclass
class InstagramPost:
    """Normalized owned Instagram Media object (Reel, Carousel, or Image)."""

    post_id: str
    caption: str
    media_type: str
    permalink: str
    timestamp: str
    media_product_type: str = "REELS"
    media_url: Optional[str] = None
    like_count: int = 0
    comments_count: int = 0
    owner_id: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InstagramComment:
    """Normalized comment or nested reply on an owned Instagram post."""

    comment_id: str
    post_id: str
    text: str
    author_id: str
    author_username: str
    timestamp: str
    parent_id: Optional[str] = None
    hidden: bool = False
    like_count: int = 0
    is_self: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_reply(self) -> bool:
        return bool(self.parent_id)


@dataclass
class PaginatedResult:
    """Cursor-paginated collection wrapper."""

    items: List[Any]
    next_cursor: Optional[str] = None
    has_more: bool = False


@dataclass
class CommentDispatchRecord:
    """Tracks idempotency and RECONCILE_PENDING state for outward comment writes."""

    idempotency_key: str
    target_id: str
    target_type: str  # "comment_reply" or "post_comment"
    message: str
    state: DispatchState
    external_comment_id: Optional[str] = None
    attempts: int = 0
    reconciled_from_existing: bool = False
    last_error: Optional[str] = None
    updated_at: float = 0.0
