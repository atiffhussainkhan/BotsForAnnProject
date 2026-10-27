"""
Owner-Curated Creator Watchlist & Lawful Content Ingestion (`watchlist.py`).

Implements FR-011, FR-012, FR-014, FR-016, FR-017, NFR-09:
- Manages Ann's curated shortlist of fellow fragrance creators and close friends.
- Strictly enforces lawful ingestion routes (`USER_SHARED_URL`, `AUTHORISED_FEED`, `MANUAL_ENTRY`)
  and raises a hard `UnlawfulIngestionError` if `FOLLOW_LIST_SCRAPE`, `BROWSER_AUTOMATION`,
  `COOKIE_EXTRACTION`, or `PRIVATE_API` is attempted.
- Enforces daily notification caps, per-creator snooze controls, and a permanent gate against
  automated third-party mass commenting (`THIRD_PARTY_AUTOCOMMENT = False`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple


PERMITTED_ACCESS_ROUTES = frozenset({
    "USER_SHARED_URL",
    "AUTHORISED_FEED",
    "MANUAL_ENTRY",
})

FORBIDDEN_ACCESS_ROUTES = frozenset({
    "FOLLOW_LIST_SCRAPE",
    "BROWSER_AUTOMATION",
    "COOKIE_EXTRACTION",
    "PRIVATE_API",
    "HEADLESS_SCRAPER",
})

PERMITTED_INTERACTION_METHODS = frozenset({
    "MANUAL_COPY_AND_OPEN_APP",
    "DRAFT_NOTIFICATION_ONLY",
})


class UnlawfulIngestionError(PermissionError):
    """Raised when an unapproved scraping or automation access route is requested (FR-012)."""


class BulkAutoCommentForbiddenError(PermissionError):
    """Raised when automated third-party commenting or bulk DMing is attempted (FR-016, FR-017)."""


@dataclass
class CreatorWatchlistEntry:
    """
    Owner-curated creator shortlist record (FR-011).
    """

    handle: str
    platform: str  # "instagram" | "tiktok"
    display_name: str
    relationship_context: str  # e.g. "Close UK fragrance friend, loves warm vanillas & niche"
    post_url: str = ""
    close_friend: bool = True
    access_route: str = "USER_SHARED_URL"
    permitted_method: str = "MANUAL_COPY_AND_OPEN_APP"
    snoozed_until: Optional[str] = None
    reminder_interval_days: int = 3

    def __post_init__(self) -> None:
        norm_platform = self.platform.strip().lower()
        if norm_platform not in {"instagram", "tiktok"}:
            raise ValueError(f"Unsupported platform '{self.platform}'. Expected 'instagram' or 'tiktok'.")
        object.__setattr__(self, "platform", norm_platform)

        route = self.access_route.strip().upper()
        if route in FORBIDDEN_ACCESS_ROUTES or route not in PERMITTED_ACCESS_ROUTES:
            raise UnlawfulIngestionError(
                f"Access route '{self.access_route}' is strictly prohibited by FR-012. "
                f"Only lawful routes {sorted(PERMITTED_ACCESS_ROUTES)} are allowed."
            )
        object.__setattr__(self, "access_route", route)

        method = self.permitted_method.strip().upper()
        if method not in PERMITTED_INTERACTION_METHODS:
            raise BulkAutoCommentForbiddenError(
                f"Interaction method '{self.permitted_method}' is prohibited by FR-014/FR-017. "
                f"Third-party engagement must remain owner-in-the-loop ({sorted(PERMITTED_INTERACTION_METHODS)})."
            )
        object.__setattr__(self, "permitted_method", method)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FriendPostEvent:
    """
    A newly detected or user-shared post from a shortlisted creator (FR-012, FR-013).
    """

    event_id: str
    creator_handle: str
    platform: str
    post_url: str
    post_title: str
    post_description: str
    published_at: str
    access_route: str = "USER_SHARED_URL"
    mentioned_notes: Tuple[str, ...] = field(default_factory=tuple)
    mentioned_perfume: Optional[str] = None


class CreatorWatchlistManager:
    """
    Manages the creator shortlist, lawful post ingestion, snooze state,
    and daily notification cap (FR-011 through FR-017).
    """

    def __init__(
        self,
        daily_notification_cap: int = 10,
        third_party_autocomment_flag: bool = False,
    ) -> None:
        if third_party_autocomment_flag:
            raise BulkAutoCommentForbiddenError(
                "THIRD_PARTY_AUTOCOMMENT must remain False in v4.0 (FR-017, NFR-09)."
            )
        self.daily_notification_cap = max(1, daily_notification_cap)
        self.third_party_autocomment_flag = False
        self._creators: Dict[str, CreatorWatchlistEntry] = {}
        self._notifications_sent_today: int = 0
        self._current_day_key: str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._ingested_posts: List[FriendPostEvent] = []

    @staticmethod
    def _key(platform: str, handle: str) -> str:
        clean_handle = handle.strip().lower().lstrip("@")
        return f"{platform.strip().lower()}:{clean_handle}"

    def add_creator(self, entry: CreatorWatchlistEntry) -> CreatorWatchlistEntry:
        """Add or update a creator in Ann's watchlist after validating lawful access route."""
        key = self._key(entry.platform, entry.handle)
        self._creators[key] = entry
        return entry

    def get_creator(self, platform: str, handle: str) -> Optional[CreatorWatchlistEntry]:
        return self._creators.get(self._key(platform, handle))

    def list_creators(self) -> List[CreatorWatchlistEntry]:
        return list(self._creators.values())

    def snooze_creator(
        self,
        platform: str,
        handle: str,
        hours: int = 24,
        now: Optional[datetime] = None,
    ) -> bool:
        """Snooze notifications for a specific creator for `hours` (FR-016)."""
        entry = self.get_creator(platform, handle)
        if entry is None:
            return False
        ref_now = now or datetime.now(timezone.utc)
        until_dt = ref_now + timedelta(hours=max(1, hours))
        entry.snoozed_until = until_dt.isoformat()
        return True

    def is_snoozed(
        self,
        platform: str,
        handle: str,
        now: Optional[datetime] = None,
    ) -> bool:
        """Return True if the creator is currently snoozed."""
        entry = self.get_creator(platform, handle)
        if entry is None or not entry.snoozed_until:
            return False
        ref_now = now or datetime.now(timezone.utc)
        try:
            until_dt = datetime.fromisoformat(entry.snoozed_until)
            if until_dt.tzinfo is None:
                until_dt = until_dt.replace(tzinfo=timezone.utc)
            return ref_now < until_dt
        except ValueError:
            return False

    def can_send_notification(self, now: Optional[datetime] = None) -> bool:
        """Check if today's notification count is below `daily_notification_cap` (FR-016)."""
        ref_now = now or datetime.now(timezone.utc)
        day_key = ref_now.strftime("%Y-%m-%d")
        if day_key != self._current_day_key:
            self._current_day_key = day_key
            self._notifications_sent_today = 0
        return self._notifications_sent_today < self.daily_notification_cap

    def record_notification_dispatched(self, now: Optional[datetime] = None) -> None:
        ref_now = now or datetime.now(timezone.utc)
        day_key = ref_now.strftime("%Y-%m-%d")
        if day_key != self._current_day_key:
            self._current_day_key = day_key
            self._notifications_sent_today = 0
        self._notifications_sent_today += 1

    def ingest_post(self, event: FriendPostEvent) -> FriendPostEvent:
        """
        Ingest a friend's post ONLY if `access_route` is in `PERMITTED_ACCESS_ROUTES`.
        Raises `UnlawfulIngestionError` on follow-list scraping or browser automation (FR-012).
        """
        route = (event.access_route or "").strip().upper()
        if route in FORBIDDEN_ACCESS_ROUTES or route not in PERMITTED_ACCESS_ROUTES:
            raise UnlawfulIngestionError(
                f"Cannot ingest post via '{event.access_route}'. "
                f"Follow-list scraping and browser automation are strictly forbidden (FR-012)."
            )
        self._ingested_posts.append(event)
        return event

    def attempt_bulk_autocomment(self, *args: Any, **kwargs: Any) -> None:
        """
        Architectural hard block against bulk DMs or automated third-party commenting (FR-016, FR-017).
        """
        raise BulkAutoCommentForbiddenError(
            "Automated third-party commenting and bulk DMs are disabled in Ann Reveals AI Manager "
            "(THIRD_PARTY_AUTOCOMMENT=false, FR-016, FR-017). Use manual one-tap copy + open app."
        )
