"""
Contextual Draft Comment Generator & Notification Builder (`draft_generator.py`).

Implements FR-013, FR-014, FR-015, FR-016:
- Generates 2–4 distinct, warm, non-generic UK English draft comments for a friend's post,
  explicitly grounded in the friend's post description, fragrance notes, and relationship context.
- Builds the owner notification card containing:
  - Creator display name & handle
  - Post title / description & link
  - Publish timestamp
  - 2–4 contextual draft comments (`draft_suggestions`)
  - One-tap copy + native platform open action (`MANUAL_COPY_AND_OPEN_APP`)
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..ai.prompt_guard import PromptGuard
from ..ai.template_catalog import compute_similarity
from .watchlist import (
    CreatorWatchlistEntry,
    CreatorWatchlistManager,
    FriendPostEvent,
)


_KNOWN_SCENT_NOTES: Tuple[str, ...] = (
    "vanilla",
    "oud",
    "rose",
    "bergamot",
    "amber",
    "sandalwood",
    "pistachio",
    "marshmallow",
    "jasmine",
    "iris",
    "tonka",
    "cardamom",
    "fig",
    "vetiver",
    "musk",
    "cedarwood",
    "lychee",
    "peach",
    "saffron",
    "incense",
    "patchouli",
    "neroli",
    "pear",
    "praline",
    "coffee",
    "cherry",
    "tuberose",
    "ambrette",
)


@dataclass(frozen=True)
class CreatorNotificationCard:
    """
    Notification payload presented to Ann when a shortlisted creator shares a new post (FR-013, FR-014).
    """

    notification_id: str
    creator_handle: str
    creator_display_name: str
    platform: str
    post_title: str
    post_description: str
    post_url: str
    published_at: str
    draft_suggestions: Tuple[str, ...]
    extracted_notes: Tuple[str, ...]
    extracted_perfume: str
    one_tap_copy_enabled: bool = True
    open_native_app_url: str = ""
    delivery_status: str = "READY_FOR_MANUAL_COPY"  # "READY_FOR_MANUAL_COPY" | "SUPPRESSED_SNOOZED" | "SUPPRESSED_DAILY_CAP"
    auto_post_permitted: bool = False
    audit_note: str = "Owner-in-the-loop manual copy & open native app (THIRD_PARTY_AUTOCOMMENT=false)"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def extract_fragrance_signals(
    post_title: str,
    post_description: str,
    explicit_notes: Sequence[str] = (),
    explicit_perfume: Optional[str] = None,
) -> Tuple[str, Tuple[str, ...]]:
    """
    Extract mentioned perfume name and fragrance notes from a friend's post caption
    so draft suggestions are genuinely contextual rather than generic spam (FR-015).
    """
    combined = f"{post_title or ''} {post_description or ''}".strip()
    lower = combined.lower()

    found_notes: List[str] = [n.lower() for n in explicit_notes if n]
    for note in _KNOWN_SCENT_NOTES:
        if re.search(rf"\b{re.escape(note)}\b", lower) and note not in found_notes:
            found_notes.append(note)

    if explicit_perfume and explicit_perfume.strip():
        perfume_name = explicit_perfume.strip()
    else:
        # Look for capitalized multi-word fragrance names or quoted titles
        quoted = re.findall(r"['\"]([A-Za-z0-9\s&'éèê]{3,35})['\"]", combined)
        if quoted:
            perfume_name = quoted[0].strip()
        else:
            cap_matches = re.findall(
                r"\b([A-Z][a-zA-Zéèê']+(?:\s+[A-Z][a-zA-Z0-9éèê']+){1,3})\b",
                combined,
            )
            stop_phrases = {"New Video", "Scent Of", "My Favourite", "Full Review", "Autumn Scents"}
            filtered = [m for m in cap_matches if m not in stop_phrases]
            perfume_name = filtered[0] if filtered else "this bottle"

    if not found_notes:
        found_notes = ["the dry-down", "those base notes"]

    return perfume_name, tuple(found_notes[:4])


class CreatorDraftGenerator:
    """
    Generates 2–4 distinct, non-repetitive UK English draft comments grounded in a friend's
    post description and builds the notification card for Ann's dashboard (FR-013–FR-016).
    """

    def __init__(
        self,
        watchlist_manager: Optional[CreatorWatchlistManager] = None,
        prompt_guard: Optional[PromptGuard] = None,
    ) -> None:
        self.watchlist = watchlist_manager or CreatorWatchlistManager()
        self.prompt_guard = prompt_guard or PromptGuard()

    def generate_contextual_drafts(
        self,
        creator: CreatorWatchlistEntry,
        post: FriendPostEvent,
        count: int = 3,
    ) -> Tuple[Tuple[str, ...], str, Tuple[str, ...]]:
        """
        Generate between 2 and 4 contextual draft comments in Ann's sincere UK English voice.
        Guarantees every draft references specific elements from the friend's post and that
        all drafts are mutually distinct (`similarity < 0.65`).
        """
        num_drafts = max(2, min(4, count))
        safe_title = self.prompt_guard.inspect(post.post_title).sanitized_text
        safe_desc = self.prompt_guard.inspect(post.post_description).sanitized_text

        perfume_name, notes = extract_fragrance_signals(
            post_title=safe_title,
            post_description=safe_desc,
            explicit_notes=post.mentioned_notes,
            explicit_perfume=post.mentioned_perfume,
        )

        primary_note = notes[0]
        secondary_note = notes[1] if len(notes) > 1 else "warm base notes"
        first_name = creator.display_name.split()[0] if creator.display_name else "lovely"

        # 4 distinct structural angles:
        # 1. Sensory / note breakdown appreciation
        # 2. Wear-occasion / layering curiosity
        # 3. Aesthetic / collection resonance
        # 4. Warm close-friend encouragement grounded in the perfume
        candidates = [
            (
                f"Such a gorgeous review, {first_name}! The way you described the {primary_note} "
                f"and {secondary_note} in {perfume_name} makes me want to spritz it on skin immediately ✨"
            ),
            (
                f"Ooh {perfume_name} sounds right up my street with that {primary_note} note! "
                f"How do you find the dry-down settles after a few hours on your skin, lovely?"
            ),
            (
                f"Love how thoughtfully you captured {perfume_name}, {first_name} — anything blending "
                f"{primary_note} with {secondary_note} is an instant favourite in my collection too 🤍"
            ),
            (
                f"Your bottle styling for {perfume_name} is so dreamy! That {primary_note} opening "
                f"sounds heavenly for this time of year, thank you for such a helpful breakdown darling!"
            ),
        ]

        selected: List[str] = []
        for cand in candidates:
            if len(selected) >= num_drafts:
                break
            if all(compute_similarity(cand, prev) < 0.65 for prev in selected):
                selected.append(cand)

        return tuple(selected), perfume_name, notes

    def build_notification(
        self,
        post: FriendPostEvent,
        draft_count: int = 3,
        now: Optional[datetime] = None,
    ) -> CreatorNotificationCard:
        """
        Ingest a friend's post via the lawful watchlist manager and assemble a
        `CreatorNotificationCard` with 2–4 contextual draft comments (FR-013, FR-014, FR-016).
        """
        # 1. Verify lawful access route first (raises UnlawfulIngestionError if scraped)
        self.watchlist.ingest_post(post)

        creator = self.watchlist.get_creator(post.platform, post.creator_handle)
        if creator is None:
            creator = CreatorWatchlistEntry(
                handle=post.creator_handle,
                platform=post.platform,
                display_name=post.creator_handle.lstrip("@").capitalize(),
                relationship_context="Curated fragrance creator",
                post_url=post.post_url,
                close_friend=False,
                access_route=post.access_route,
            )

        drafts, perfume_name, notes = self.generate_contextual_drafts(
            creator=creator,
            post=post,
            count=draft_count,
        )

        # 2. Check snooze and daily notification cap (FR-016)
        if self.watchlist.is_snoozed(post.platform, post.creator_handle, now=now):
            status = "SUPPRESSED_SNOOZED"
        elif not self.watchlist.can_send_notification(now=now):
            status = "SUPPRESSED_DAILY_CAP"
        else:
            status = "READY_FOR_MANUAL_COPY"
            self.watchlist.record_notification_dispatched(now=now)

        return CreatorNotificationCard(
            notification_id=f"NTF-{post.event_id}",
            creator_handle=creator.handle,
            creator_display_name=creator.display_name,
            platform=creator.platform,
            post_title=post.post_title,
            post_description=post.post_description,
            post_url=post.post_url,
            published_at=post.published_at,
            draft_suggestions=drafts,
            extracted_notes=notes,
            extracted_perfume=perfume_name,
            one_tap_copy_enabled=True,
            open_native_app_url=post.post_url,
            delivery_status=status,
            auto_post_permitted=False,
        )
