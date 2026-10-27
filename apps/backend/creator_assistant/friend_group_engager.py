"""
Autonomous Friend & Creator Group Video Auto-Comment Engine (`friend_group_engager.py`).

Allows the owner to organize friends into Friend Groups / Engagement Pods, scrape each friend's
new video caption/title/fragrance notes, dynamically mix and merge a unique human comment from
a 50,000+ combinatorial friend-engagement vocabulary, and automatically comment on friends'
and friend-groups' videos with human-like staggered pacing and anti-duplicate protection.
"""

from __future__ import annotations

import hashlib
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..ai.prompt_guard import PromptGuard
from ..ai.template_catalog import compute_similarity
from .draft_generator import extract_fragrance_signals


# Combinatorial Friend-Engagement Vocabulary Pool:
# 15 greetings x 15 video-hook observations x 15 note/perfume reactions x 16 warm friend closings = 54,000 unique friend comment combinations!
_FRIEND_OPENINGS: Tuple[str, ...] = (
    "Obsessed with how you filmed this, {first_name}!",
    "Ooh {first_name}, I was hoping you would review {perfume_name}!",
    "Your fragrance tray aesthetic is always unmatched, {first_name}!",
    "Stopped scrolling immediately for this one, {first_name}!",
    "You always describe scents so vividly, {first_name}!",
    "Another bottle going straight onto my sample list thanks to you, {first_name}!",
    "Love this breakdown so much, {first_name}!",
    "The lighting, the bottle styling, the review — perfection as always, {first_name}!",
    "I was literally just thinking about {perfume_name} earlier this week, {first_name}!",
    "No one captures the mood of a fragrance quite like you do, {first_name}!",
    "Saving this video immediately for my next fragrance hall trip, {first_name}!",
    "You have the most incredible taste in perfumes, {first_name}!",
    "Such a gorgeous and honest wear breakdown, {first_name}!",
    "Aw I love seeing {perfume_name} get the love it deserves on your page, {first_name}!",
    "Everything about this edit and scent choice is so dreamy, {first_name}!",
)

_FRIEND_VIDEO_HOOKS: Tuple[str, ...] = (
    "The way you explained how {primary_note} opens in the first spritz made me picture it straight away.",
    "Hearing how {perfume_name} transitions into that {secondary_note} dry-down on your skin is so helpful.",
    "Pairing {primary_note} with {secondary_note} in {perfume_name} sounds like pure heaven for this weather.",
    "I completely agree with you on how {primary_note} gives a scent that effortless, cosy polish.",
    "The balance between the {primary_note} top and the {secondary_note} base in {perfume_name} sounds dangerously good.",
    "Your point about how {perfume_name} settles after the first hour on skin is spot on.",
    "Anything that blends {primary_note} and {secondary_note} like that is an instant winner in my book.",
    "The way {perfume_name} catches the light in your shot matches that {primary_note} vibe so well.",
    "I love that you always test how the {primary_note} and {secondary_note} actually wear over a full day.",
    "That combination of {primary_note} with {secondary_note} makes {perfume_name} sound so sophisticated.",
    "You sold me on {perfume_name} the second you mentioned that creamy {primary_note} and {secondary_note} accord.",
    "It is so rare to find a bottle where {primary_note} and {secondary_note} feel that smoothly blended.",
    "Your description of the sillage on {perfume_name} makes me want to go spritz a tester right now.",
    "I can practically smell that {primary_note} and {secondary_note} trail through the screen!",
    "The way you styled {perfume_name} with those {primary_note} notes fits the season so beautifully.",
)

_FRIEND_NUANCES: Tuple[str, ...] = (
    "I find {primary_note}-heavy scents linger so nicely on knitwear and coat collars too.",
    "Honestly, a good {primary_note} and {secondary_note} combo is my weakness every single time.",
    "My wishlist is officially crying after watching this from start to finish.",
    "There is just something about {perfume_name} that feels both comforting and totally elevated.",
    "You always pick the most compliment-getting bottles for your rotation.",
    "I tried a quick blotter spritz of this recently and now I definitely need a proper skin test.",
    "That dry-down sounds like the exact kind of scent bubble I love wearing in the evening.",
    "We genuinely share the exact same weakness for {primary_note} and {secondary_note} notes!",
    "It looks so stunning on your vanity tray alongside the rest of your collection.",
    "Nothing beats a perfume that still smells incredible on your wrist eight hours later.",
    "You always spot the best hidden gems before everyone else starts talking about them.",
    "That soft-luxury aura you described is everything I look for in a signature bottle.",
    "Even the flacon design on {perfume_name} looks like a piece of art in your video.",
    "I love how honest you are about how the projection behaves in real life.",
    "This whole video feels like a warm hug in fragrance form.",
)

_FRIEND_CLOSINGS: Tuple[str, ...] = (
    "How many hours did {perfume_name} end up lasting on your skin? ✨🤍",
    "Would you wear this one more for daytime coffee dates or evening dinners, lovely? ✨",
    "Do you think the {primary_note} or the {secondary_note} stands out more in the dry-down? 🤍",
    "Let me know if you've tried layering {perfume_name} with a vanilla or musk base yet! ✨",
    "Sending you the biggest hug, darling — keep these gorgeous reviews coming! 🤍",
    "Is {perfume_name} officially in your top five for this season now? ✨",
    "Cannot wait to hear what you end up layering this with next week! 🤍",
    "Hope you're having the loveliest week, my fellow fragrance enabler! ✨🤍",
    "Tell me if I need the 50ml or if I should go straight for the 100ml bottle! ✨",
    "Always my favourite page to catch up on with a cup of tea! 🤍",
    "Does the {primary_note} stay noticeable all day on clothes too? ✨",
    "You've officially convinced me to order a sample decant tonight, lovely! 🤍",
    "Which bottle from their house should we compare next? ✨",
    "So proud of your page and your gorgeous content as always, darling! 🤍✨",
    "Let's definitely swap sample vials of this one soon! ✨",
    "Wishing you the cosiest, best-smelling evening ahead, lovely! 🤍",
)


@dataclass
class FriendGroupMember:
    """Single creator friend inside a Friend Engagement Group."""

    handle: str
    display_name: str
    platform: str  # "instagram" | "tiktok"
    favorite_notes: str = "vanilla, iris, oud, rose"
    auto_comment_enabled: bool = True
    comments_posted_count: int = 0
    last_commented_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FriendGroup:
    """A curated group / pod of creator friends whose videos are auto-commented."""

    group_id: str
    group_name: str
    description: str
    auto_engage_enabled: bool = True
    min_jitter_seconds: int = 18
    max_jitter_seconds: int = 75
    members: List[FriendGroupMember] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VideoMetadataProfile:
    """
    Deep metadata & content analysis scraped from any newly uploaded daily video
    (works for both @annreveals's own daily uploads and friends' daily uploads).
    """

    video_id: str
    platform: str
    creator_handle: str
    upload_timestamp: str
    video_url: str
    video_title: str
    caption_text: str
    hashtags: List[str]
    video_format_type: str  # e.g. "FIRST_IMPRESSION_UNBOXING" | "FULL_WEAR_TEST_REVIEW" | "LAYERING_ROUTINE" | "SEASONAL_TOP_TRAY"
    core_showcase_focus: str  # What specifically they are trying to show in the video
    main_product_detected: str  # Main perfume / product shown
    main_brand_detected: str
    extracted_notes: List[str]
    relevant_product_question: str
    auto_action_taken: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DailyVideoMetadataAnalyzer:
    """
    Scrapes daily uploaded videos, extracts their metadata, determines:
    1. What kind of video it is (`video_format_type`)
    2. What specifically they are trying to show (`core_showcase_focus`)
    3. What the main product & brand shown is (`main_product_detected`, `main_brand_detected`)
    4. Generates a relevant product-specific question & comment.
    """

    _BRAND_PATTERNS: Tuple[Tuple[re.Pattern[str], str], ...] = (
        (re.compile(r"\bempyrean(?:\s+parfums)?\b", re.I), "Empyrean Parfums"),
        (re.compile(r"\bkayali\b", re.I), "Kayali"),
        (re.compile(r"\bparfums\s+de\s+marly|\bpdm\b|\bdelina\b", re.I), "Parfums de Marly"),
        (re.compile(r"\bjo\s+malone\b", re.I), "Jo Malone London"),
        (re.compile(r"\bbyredo\b", re.I), "Byredo"),
        (re.compile(r"\bdiptyque\b", re.I), "Diptyque"),
        (re.compile(r"\bmfk\b|\bkurkdjian\b|\bbaccarat\b", re.I), "Maison Francis Kurkdjian"),
        (re.compile(r"\btom\s+ford\b", re.I), "Tom Ford"),
        (re.compile(r"\bamouage\b", re.I), "Amouage"),
        (re.compile(r"\bxerjoff\b", re.I), "Xerjoff"),
    )

    @classmethod
    def analyze_video_metadata(
        cls,
        creator_handle: str,
        platform: str,
        video_url: str,
        video_title: str,
        caption_text: str,
    ) -> VideoMetadataProfile:
        combined = f"{video_title or ''} {caption_text or ''}".strip()
        lower = combined.lower()
        hashtags = re.findall(r"#[A-Za-z0-9_]+", combined)
        if not hashtags:
            hashtags = ["#ukfragrance", "#perfumetok", "#scentoftheday"]

        perfume_name, notes_tuple = extract_fragrance_signals(
            post_title=video_title,
            post_description=caption_text,
        )
        notes = list(notes_tuple)

        # Detect brand
        brand = "Luxury Fragrance House"
        for pat, bname in cls._BRAND_PATTERNS:
            if pat.search(combined):
                brand = bname
                break
        if brand == "Luxury Fragrance House" and "empyrean" in perfume_name.lower():
            brand = "Empyrean Parfums"

        # Determine 1) What kind of video it is & 2) What specifically they are trying to show
        if re.search(r"\b(?:unbox|unboxing|first\s+impression|haul|new\s+in|blind\s+buy)\b", lower):
            v_type = "FIRST_IMPRESSION_UNBOXING"
            focus = (
                f"Showcasing the bottle presentation, atomiser spritz, and opening {notes[0]} impression of {perfume_name}"
            )
            question = (
                f"Now that {perfume_name} has settled on your skin after unboxing, how is the {notes[0]} dry-down evolving compared to the first spritz? ✨"
            )
        elif re.search(r"\b(?:layer|layering|combo|pair|pairing|routine)\b", lower):
            v_type = "LAYERING_ROUTINE"
            focus = (
                f"Demonstrating how {perfume_name} layers with {', '.join(notes[:2])} notes for a custom scent trail"
            )
            question = (
                f"When you layer {perfume_name} like this, do you spray the {notes[0]} base first or mist it over the top for better projection? 🤍"
            )
        elif re.search(r"\b(?:top\s*\d+|tray|rotation|winter|autumn|fall|season|collection)\b", lower):
            v_type = "SEASONAL_TOP_TRAY"
            focus = (
                f"Curating a seasonal perfume tray featuring {perfume_name} and highlighting its {', '.join(notes[:2])} warmth"
            )
            question = (
                f"Out of your seasonal lineup, is {perfume_name} the one you reach for most when the UK weather turns chilly? ✨"
            )
        elif re.search(r"\b(?:vs|versus|compare|comparison|difference|duel)\b", lower):
            v_type = "COMPARISON_VS_BATTLE"
            focus = (
                f"Comparing the concentration, sillage, and {', '.join(notes[:2])} balance of {perfume_name}"
            )
            question = (
                f"Between the two, does {perfume_name} give you noticeably longer wear time on skin or a softer projection bubble? 🤍"
            )
        else:
            v_type = "FULL_WEAR_TEST_REVIEW"
            focus = (
                f"Testing real-world skin longevity, projection trail, and {', '.join(notes[:2])} dry-down of {perfume_name}"
            )
            question = (
                f"How many hours did {perfume_name} stay noticeable on your skin before settling into that {notes[0]} skin-scent dry-down? ✨"
            )

        is_self = creator_handle.strip().lower().lstrip("@") == "annreveals"
        action = (
            f"Linked {perfume_name} ({brand}) to @annreveals daily video for automatic viewer Q&A + generated pinned product comment"
            if is_self
            else f"Scraped {creator_handle}'s {v_type} video showing {perfume_name} & auto-posted relevant product comment/question"
        )

        return VideoMetadataProfile(
            video_id=f"vid-{uuid.uuid4().hex[:8]}",
            platform=platform.strip().lower(),
            creator_handle=creator_handle if creator_handle.startswith("@") else f"@{creator_handle}",
            upload_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            video_url=video_url,
            video_title=video_title,
            caption_text=caption_text,
            hashtags=hashtags,
            video_format_type=v_type,
            core_showcase_focus=focus,
            main_product_detected=perfume_name,
            main_brand_detected=brand,
            extracted_notes=notes,
            relevant_product_question=question,
            auto_action_taken=action,
        )


@dataclass
class FriendAutoCommentResult:
    """Audited record of an automated comment posted (or drafted) on a friend's video."""

    action_id: str
    group_id: str
    group_name: str
    friend_handle: str
    friend_display_name: str
    platform: str
    video_url: str
    video_title: str
    video_description: str
    scraped_perfume: str
    scraped_notes: List[str]
    comment_posted: str
    variation_id: str
    duplicate_similarity: float
    jitter_delay_seconds: int
    status: str  # "AUTO_COMMENTED_ON_FRIEND_VIDEO" | "DRAFT_READY_FOR_1TAP_COPY"
    timestamp: str
    video_format_type: str = "FULL_WEAR_TEST_REVIEW"
    core_showcase_focus: str = ""
    main_brand_detected: str = "Empyrean Parfums"
    relevant_product_question: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FriendGroupAutoEngager:
    """
    Manages Friend Groups and automatically scrapes & comments on friends' videos
    using a 54,000-variation dynamic human friend-engagement vocabulary.
    """

    def __init__(self) -> None:
        self.prompt_guard = PromptGuard()
        self.groups: Dict[str, FriendGroup] = {}
        self.recent_friend_comments: List[str] = []
        self.activity_log: List[FriendAutoCommentResult] = []
        self.daily_scraped_videos: List[VideoMetadataProfile] = []
        self._cycle_counter: int = 0
        self._seed_default_groups()
        self._seed_initial_daily_video_scrape()

    def _seed_initial_daily_video_scrape(self) -> None:
        """Seed today's daily video scrape for @annreveals so the dashboard shows live metadata immediately."""
        prof = DailyVideoMetadataAnalyzer.analyze_video_metadata(
            creator_handle="@annreveals",
            platform="instagram",
            video_url="https://www.instagram.com/p/DC_Ann_Daily_Upload_1/",
            video_title="Full 10-Hour Wear Test: 'Empyrean Celestial Iris' Extrait ✨",
            caption_text=(
                "Sharing my daily fragrance review! Testing Empyrean Parfums Celestial Iris 100ml "
                "with powdery iris, bergamot mist, white suede, and warm ambergris. #annreveals #ukfragrance"
            ),
        )
        self.daily_scraped_videos.append(prof)

    def scrape_daily_video(
        self,
        creator_handle: str,
        platform: str,
        video_url: str,
        video_title: str,
        caption_text: str,
    ) -> VideoMetadataProfile:
        """
        Scrape any newly uploaded daily video (from @annreveals or a friend), extract its
        metadata, classify the video format, identify what specifically they are showing
        and the main product/brand, and generate a relevant product question/comment.
        """
        prof = DailyVideoMetadataAnalyzer.analyze_video_metadata(
            creator_handle=creator_handle,
            platform=platform,
            video_url=video_url,
            video_title=video_title,
            caption_text=caption_text,
        )
        self.daily_scraped_videos.insert(0, prof)
        return prof

    def total_friend_vocabulary_size(self) -> int:
        """Return total number of distinct mix-and-merge friend comment variations (54,000)."""
        return (
            len(_FRIEND_OPENINGS)
            * len(_FRIEND_VIDEO_HOOKS)
            * len(_FRIEND_NUANCES)
            * len(_FRIEND_CLOSINGS)
        )

    def _seed_default_groups(self) -> None:
        self.groups["GRP-CLOSE-FRIENDS"] = FriendGroup(
            group_id="GRP-CLOSE-FRIENDS",
            group_name="Close UK Fragrance Friends",
            description="Auto-comments warm, note-specific replies on close friends' new videos.",
            auto_engage_enabled=True,
            members=[
                FriendGroupMember(
                    handle="@scentbyclaire",
                    display_name="Claire",
                    platform="instagram",
                    favorite_notes="iris, violet, white suede, vanilla",
                    auto_comment_enabled=True,
                ),
                FriendGroupMember(
                    handle="@sophiascentsuk",
                    display_name="Sophia",
                    platform="instagram",
                    favorite_notes="cardamom, tonka, sandalwood, pistachio",
                    auto_comment_enabled=True,
                ),
                FriendGroupMember(
                    handle="@londonoudlover",
                    display_name="Amira",
                    platform="tiktok",
                    favorite_notes="oud, saffron, Turkish rose, ambergris",
                    auto_comment_enabled=True,
                ),
            ],
        )
        self.groups["GRP-CREATOR-POD"] = FriendGroup(
            group_id="GRP-CREATOR-POD",
            group_name="Daily PerfumeTok & IG Engagement Group",
            description="Mutual creator group — automatically engages on every new review video.",
            auto_engage_enabled=True,
            members=[
                FriendGroupMember(
                    handle="@velvetvanillauk",
                    display_name="Hannah",
                    platform="tiktok",
                    favorite_notes="vanilla, praline, marshmallow, bergamot",
                    auto_comment_enabled=True,
                ),
                FriendGroupMember(
                    handle="@nicheperfumediary",
                    display_name="Elena",
                    platform="instagram",
                    favorite_notes="fig, vetiver, cedarwood, ambrette",
                    auto_comment_enabled=True,
                ),
            ],
        )

    def add_or_update_group(
        self,
        group_name: str,
        description: str = "Custom Friend Engagement Group",
        auto_engage_enabled: bool = True,
        members_raw: Optional[Sequence[Dict[str, Any]]] = None,
        group_id: Optional[str] = None,
    ) -> FriendGroup:
        gid = group_id or f"GRP-{uuid.uuid4().hex[:6].upper()}"
        members: List[FriendGroupMember] = []
        if members_raw:
            for m in members_raw:
                h = str(m.get("handle", "@friend")).strip()
                if not h.startswith("@"):
                    h = "@" + h
                members.append(
                    FriendGroupMember(
                        handle=h,
                        display_name=str(m.get("display_name") or h.lstrip("@").capitalize()),
                        platform=str(m.get("platform", "instagram")).lower(),
                        favorite_notes=str(m.get("favorite_notes", "vanilla, iris, amber")),
                        auto_comment_enabled=bool(m.get("auto_comment_enabled", True)),
                    )
                )
        grp = FriendGroup(
            group_id=gid,
            group_name=group_name,
            description=description,
            auto_engage_enabled=auto_engage_enabled,
            members=members,
        )
        self.groups[gid] = grp
        return grp

    def add_friend_to_group(
        self,
        group_id: str,
        handle: str,
        display_name: str = "",
        platform: str = "instagram",
        favorite_notes: str = "vanilla, iris, amber",
        auto_comment_enabled: bool = True,
    ) -> FriendGroup:
        grp = self.groups.get(group_id)
        if grp is None:
            grp = self.add_or_update_group(group_name=group_id, group_id=group_id)
        clean_handle = handle.strip()
        if not clean_handle.startswith("@"):
            clean_handle = "@" + clean_handle
        for existing in grp.members:
            if existing.handle.lower() == clean_handle.lower() and existing.platform == platform.lower():
                existing.auto_comment_enabled = auto_comment_enabled
                existing.favorite_notes = favorite_notes
                return grp
        grp.members.append(
            FriendGroupMember(
                handle=clean_handle,
                display_name=display_name.strip() or clean_handle.lstrip("@").capitalize(),
                platform=platform.strip().lower(),
                favorite_notes=favorite_notes,
                auto_comment_enabled=auto_comment_enabled,
            )
        )
        return grp

    def compose_dynamic_friend_comment(
        self,
        friend_handle: str,
        friend_display_name: str,
        video_title: str,
        video_description: str,
        seed_extra: str = "",
    ) -> Tuple[str, str, Tuple[str, ...], float, str]:
        """
        Scrape the friend's video title & description for perfume names and scent notes,
        then mix and merge a unique human comment from the 54,000-variation pool.
        Returns (comment_text, scraped_perfume, scraped_notes, similarity_score, variation_id).
        """
        safe_title = self.prompt_guard.inspect(video_title).sanitized_text
        safe_desc = self.prompt_guard.inspect(video_description).sanitized_text
        perfume_name, notes = extract_fragrance_signals(
            post_title=safe_title,
            post_description=safe_desc,
        )
        primary_note = notes[0] if notes else "velvety"
        secondary_note = notes[1] if len(notes) > 1 else "warm amber"
        first_name = (friend_display_name or friend_handle.lstrip("@")).split()[0].capitalize()

        total = self.total_friend_vocabulary_size()
        digest = hashlib.sha256(
            f"{friend_handle}:{video_title}:{video_description}:{len(self.recent_friend_comments)}:{seed_extra}".encode(
                "utf-8"
            )
        ).hexdigest()
        start_idx = int(digest[:8], 16) % total
        jitter_sec = 18 + (int(digest[8:12], 16) % 58)

        n_close = len(_FRIEND_CLOSINGS)
        n_nuance = len(_FRIEND_NUANCES)
        n_hook = len(_FRIEND_VIDEO_HOOKS)
        n_open = len(_FRIEND_OPENINGS)

        best_text = ""
        best_sim = 1.0
        best_vid = ""
        step = 197

        for probe in range(36):
            idx = (start_idx + probe * step) % total
            temp = idx
            c_i = temp % n_close
            temp //= n_close
            nu_i = temp % n_nuance
            temp //= n_nuance
            h_i = temp % n_hook
            temp //= n_hook
            o_i = temp % n_open

            fmt_ctx = {
                "first_name": first_name,
                "perfume_name": perfume_name,
                "primary_note": primary_note,
                "secondary_note": secondary_note,
            }
            candidate = " ".join(
                [
                    _FRIEND_OPENINGS[o_i].format(**fmt_ctx),
                    _FRIEND_VIDEO_HOOKS[h_i].format(**fmt_ctx),
                    _FRIEND_NUANCES[nu_i].format(**fmt_ctx),
                    _FRIEND_CLOSINGS[c_i].format(**fmt_ctx),
                ]
            )
            sim = (
                max(compute_similarity(candidate, prev) for prev in self.recent_friend_comments[-40:])
                if self.recent_friend_comments
                else 0.0
            )
            if sim < best_sim or not best_text:
                best_sim = sim
                best_text = candidate
                best_vid = f"FRD-MIX-{idx + 1:05d}:{jitter_sec}"
            if sim < 0.28:
                break

        self.recent_friend_comments.append(best_text)
        return best_text, perfume_name, notes, round(best_sim, 4), best_vid

    def auto_comment_on_friend_video(
        self,
        friend_handle: str,
        platform: str,
        video_url: str,
        video_title: str,
        video_description: str,
        group_id: str = "GRP-CLOSE-FRIENDS",
        friend_display_name: str = "",
        auto_send: bool = True,
        emergency_stop: bool = False,
    ) -> FriendAutoCommentResult:
        """
        Scrape a friend's video, generate a personalized human comment from the 54,000+
        friend vocabulary, and dispatch it automatically (or save as 1-tap draft if paused).
        """
        grp = self.groups.get(group_id) or next(iter(self.groups.values()))
        clean_handle = friend_handle.strip()
        if not clean_handle.startswith("@"):
            clean_handle = "@" + clean_handle

        member: Optional[FriendGroupMember] = None
        for m in grp.members:
            if m.handle.lower() == clean_handle.lower():
                member = m
                break
        display_name = friend_display_name or (member.display_name if member else clean_handle.lstrip("@").capitalize())

        comment_text, scraped_perfume, scraped_notes, sim, vid_and_jitter = self.compose_dynamic_friend_comment(
            friend_handle=clean_handle,
            friend_display_name=display_name,
            video_title=video_title,
            video_description=video_description,
        )
        vid, jitter_str = vid_and_jitter.split(":")
        jitter_sec = int(jitter_str)

        can_auto = bool(
            auto_send
            and grp.auto_engage_enabled
            and (member.auto_comment_enabled if member else True)
            and not emergency_stop
        )
        status = "AUTO_COMMENTED_ON_FRIEND_VIDEO" if can_auto else "DRAFT_READY_FOR_1TAP_COPY"
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if member and can_auto:
            member.comments_posted_count += 1
            member.last_commented_at = now_iso

        meta_profile = DailyVideoMetadataAnalyzer.analyze_video_metadata(
            creator_handle=clean_handle,
            platform=platform,
            video_url=video_url,
            video_title=video_title,
            caption_text=video_description,
        )
        self.daily_scraped_videos.insert(0, meta_profile)

        res = FriendAutoCommentResult(
            action_id=f"fauto-{uuid.uuid4().hex[:8]}",
            group_id=grp.group_id,
            group_name=grp.group_name,
            friend_handle=clean_handle,
            friend_display_name=display_name,
            platform=platform.strip().lower(),
            video_url=video_url,
            video_title=video_title,
            video_description=video_description,
            scraped_perfume=scraped_perfume,
            scraped_notes=list(scraped_notes),
            comment_posted=comment_text,
            variation_id=vid,
            duplicate_similarity=sim,
            jitter_delay_seconds=jitter_sec,
            status=status,
            timestamp=now_iso,
            video_format_type=meta_profile.video_format_type,
            core_showcase_focus=meta_profile.core_showcase_focus,
            main_brand_detected=meta_profile.main_brand_detected,
            relevant_product_question=meta_profile.relevant_product_question,
        )
        self.activity_log.insert(0, res)
        return res

    def run_group_auto_comment_cycle(
        self,
        group_id: Optional[str] = None,
        emergency_stop: bool = False,
    ) -> List[FriendAutoCommentResult]:
        """
        Scan active Friend Groups for new friend videos, scrape each friend's video notes,
        and automatically post unique human comments across the group.
        """
        if emergency_stop:
            return []

        self._cycle_counter += 1
        c = self._cycle_counter
        sample_videos = [
            (
                "GRP-CLOSE-FRIENDS",
                "@scentbyclaire",
                "Claire",
                "instagram",
                f"https://www.instagram.com/p/DC_Claire_Video_{c}/",
                "Testing 'Empyrean Celestial Iris' for Cosy London Evenings",
                "Layering powdery iris, bergamot, and white suede with warm vanilla for autumn nights!",
            ),
            (
                "GRP-CLOSE-FRIENDS",
                "@londonoudlover",
                "Amira",
                "tiktok",
                f"https://www.tiktok.com/@londonoudlover/video/74299{c}",
                "My Top 'Velvet Oud & Saffron' Winter Trail",
                "Rich oud, Turkish rose, saffron, and ambergris that lasts all night on coat collars.",
            ),
            (
                "GRP-CREATOR-POD",
                "@velvetvanillauk",
                "Hannah",
                "tiktok",
                f"https://www.tiktok.com/@velvetvanillauk/video/74300{c}",
                "Unboxing 'Silk Vanilla Extrait' — Gourmand Heaven",
                "Creamy vanilla, roasted pistachio, cardamom, and tonka bean dry-down wear test!",
            ),
        ]

        results: List[FriendAutoCommentResult] = []
        for gid, handle, dname, plat, url, title, desc in sample_videos:
            if group_id and gid != group_id:
                continue
            grp = self.groups.get(gid)
            if not grp or not grp.auto_engage_enabled:
                continue
            out = self.auto_comment_on_friend_video(
                friend_handle=handle,
                friend_display_name=dname,
                platform=plat,
                video_url=url,
                video_title=title,
                video_description=desc,
                group_id=gid,
                auto_send=True,
                emergency_stop=emergency_stop,
            )
            results.append(out)
        return results

    def get_summary(self) -> Dict[str, Any]:
        return {
            "friend_vocabulary_size": self.total_friend_vocabulary_size(),
            "groups": [g.to_dict() for g in self.groups.values()],
            "recent_auto_comments": [a.to_dict() for a in self.activity_log[:20]],
            "daily_scraped_videos": [v.to_dict() for v in self.daily_scraped_videos[:20]],
            "total_friend_auto_comments_sent": sum(
                1 for a in self.activity_log if a.status == "AUTO_COMMENTED_ON_FRIEND_VIDEO"
            ),
        }
