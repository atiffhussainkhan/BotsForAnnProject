"""
Ann Reveals AI Manager (v4.0) — Friends & Creator Engagement Assistant Package.

Implements FR-011 through FR-017:
- `CreatorWatchlistEntry`, `CreatorWatchlistManager`, `FriendPostEvent`
- `UnlawfulIngestionError`, `BulkAutoCommentForbiddenError`
- `CreatorDraftGenerator`, `CreatorNotificationCard`, `extract_fragrance_signals`
"""

from .draft_generator import (
    CreatorDraftGenerator,
    CreatorNotificationCard,
    extract_fragrance_signals,
)
from .watchlist import (
    BulkAutoCommentForbiddenError,
    CreatorWatchlistEntry,
    CreatorWatchlistManager,
    FORBIDDEN_ACCESS_ROUTES,
    FriendPostEvent,
    PERMITTED_ACCESS_ROUTES,
    PERMITTED_INTERACTION_METHODS,
    UnlawfulIngestionError,
)

__all__ = [
    "BulkAutoCommentForbiddenError",
    "CreatorDraftGenerator",
    "CreatorNotificationCard",
    "CreatorWatchlistEntry",
    "CreatorWatchlistManager",
    "FORBIDDEN_ACCESS_ROUTES",
    "FriendPostEvent",
    "PERMITTED_ACCESS_ROUTES",
    "PERMITTED_INTERACTION_METHODS",
    "UnlawfulIngestionError",
    "extract_fragrance_signals",
]
