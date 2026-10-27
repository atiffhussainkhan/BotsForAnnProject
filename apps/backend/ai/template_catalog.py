"""
Structured Combinatorial Reply Variation Taxonomy & Near-Duplicate Guard (`template_catalog.py`).

Implements FR-005, FR-007, FR-055:
- Generates 1,200+ distinct, natural Ann Reveals reply variations in sincere UK English
  (warm feminine soft-luxury, concise, helpful, never promotional by default).
- Combines category-specific openings, grounded middle clauses, and warm sign-offs.
- Computes hybrid token-Jaccard + character 3-gram similarity against recent replies
  to guarantee semantic diversity and prevent repetitive comment spam on TikTok/Instagram.
"""

from __future__ import annotations

import hashlib
import itertools
import re
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Sequence, Set, Tuple


@dataclass(frozen=True)
class ReplyTemplateVariation:
    """Single structured variation entry in the Ann Reveals seed taxonomy."""

    template_id: str
    intent_bucket: str
    tone_variant: str
    opening: str
    body_pattern: str
    closing: str

    def render(self, **context: str) -> str:
        """Render the variation with grounded fragrance context placeholders."""
        defaults = {
            "product_name": "this fragrance",
            "brand": "the house",
            "scent_family": "soft-luxury",
            "vibe_summary": "a really balanced, wearable composition",
            "notes_summary": "It has a lovely balance of top, heart, and base notes",
            "longevity_statement": "I'm still testing how many hours it lasts on my skin.",
            "price_statement": "It sits around the usual eau de parfum price point depending on bottle size.",
            "store_statement": "I picked mine up from an authorised UK stockist.",
        }
        merged = {**defaults, **{k: v for k, v in context.items() if v}}
        parts = [
            self.opening.format(**merged).strip(),
            self.body_pattern.format(**merged).strip(),
            self.closing.format(**merged).strip(),
        ]
        rendered = " ".join(p for p in parts if p)
        return re.sub(r"\s+", " ", rendered).strip()


# Combinatorial building blocks per intent bucket (designed to yield >1,500 distinct combinations)
_TAXONOMY_BUCKETS: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "compliment": {
        "tones": ("warm_appreciative", "poised_grateful", "soft_conversational"),
        "openings": (
            "Thank you so much, lovely!",
            "Aw, thank you darling, that truly means a lot!",
            "You are so kind, thank you so much!",
            "That is so sweet of you to say, thank you!",
            "Thank you ever so much for watching and leaving such a lovely note!",
            "So happy you enjoyed this review, thank you lovely!",
            "What a thoughtful comment to read today, thank you!",
            "Thank you so much — I always love chatting perfume with you all!",
            "Aw, you've genuinely made my day with this comment, thank you!",
            "Thank you darling, I really appreciate you being here!",
        ),
        "bodies": (
            "{product_name} has quickly become one of my favourite bottles to reach for because of its {scent_family} character.",
            "I really enjoyed filming this one — {product_name} has such {vibe_summary} on my skin.",
            "Exploring {scent_family} scents like {product_name} is honestly my favourite part of sharing my collection.",
            "It's such a pleasure sharing honest impressions on bottles like {product_name}, especially with that dry-down.",
            "{product_name} really surprised me in the best way with {vibe_summary}.",
            "I always try to capture how a scent truly wears in real life, and {product_name} is such a special one.",
        ),
        "closings": (
            "Hope you're having a wonderful week! ✨",
            "Have you tried anything from {brand} yet, or is it on your wishlist?",
            "Let me know what your scent of the day is today! 🤍",
            "Sending you lots of love from London!",
            "Always love hearing which notes are your favourites too!",
            "Hope this helps if you ever decide to sample it in store!",
        ),
    },
    "product_notes": {
        "tones": ("sensory_detailed", "editorial_soft_luxury", "helpful_concise"),
        "openings": (
            "It's such a beautifully blended scent!",
            "Great question, lovely — the note pyramid on this one is gorgeous.",
            "Happy to share how the notes unfold on my skin!",
            "If you enjoy {scent_family} profiles, you'll find the notes really interesting.",
            "The way {product_name} develops from the first spritz is lovely.",
            "Here is how the notes read on my skin from opening to dry-down:",
        ),
        "bodies": (
            "{notes_summary}, giving it {vibe_summary}.",
            "{notes_summary} — on my skin it feels like {vibe_summary}.",
            "In {product_name}, {notes_summary}, which creates a really refined {scent_family} aura.",
            "{notes_summary}; the transition into the base is my favourite part.",
            "With {product_name}, {notes_summary}, and the vapour trail stays wonderfully smooth.",
        ),
        "closings": (
            "Are you normally drawn to {scent_family} scents?",
            "Hope that helps give you a feel for how it wears!",
            "It's definitely worth smelling on a blotter and on skin if you pass a counter!",
            "Let me know if you also enjoy those base notes!",
            "The dry-down is honestly where it shines most for me.",
        ),
    },
    "longevity_measured": {
        "tones": ("grounded_empirical", "skin_chemistry_aware", "helpful_direct"),
        "openings": (
            "Great question on the performance!",
            "Happy to share how it performed during my wear test!",
            "I've tested {product_name} properly over a full day now.",
            "When it comes to lasting power on my skin:",
            "Here is what I found during my full wear test of {product_name}:",
            "Performance is always so important with {scent_family} scents!",
        ),
        "bodies": (
            "{longevity_statement}",
            "{longevity_statement} It lingers even longer on knitwear and scarves.",
            "{longevity_statement} The base notes stay noticeable well into the evening.",
            "{longevity_statement} As always, skin chemistry and moisturised skin make a big difference too.",
            "{longevity_statement} The opening settles after the first hour into a steady dry-down.",
        ),
        "closings": (
            "Hope that helps with your decision, lovely!",
            "Do scents in the {scent_family} family usually last well on your skin?",
            "Always recommend a skin test first as every skin type holds fragrance differently!",
            "Let me know how it performs on you if you try a sample!",
            "It's a very comfortable wear from morning to evening.",
        ),
    },
    "longevity_unmeasured": {
        "tones": ("transparent_honest", "careful_reviewer", "sincere_uk"),
        "openings": (
            "Thank you for asking about the wear time, lovely!",
            "I always want to be completely honest with my longevity numbers:",
            "Good question — I never like to guess at hours before a full test:",
            "Regarding lasting power on {product_name}:",
            "I'm still in the middle of testing this bottle properly:",
            "To be totally transparent with you on performance:",
        ),
        "bodies": (
            "{longevity_statement}",
            "{longevity_statement} I'll share an update once I've worn it for several full days.",
            "{longevity_statement} I always prefer doing a proper multi-day wear test before quoting hours.",
            "{longevity_statement} So far the opening and heart notes feel really promising on skin.",
        ),
        "closings": (
            "I'll definitely report back once my full wear test is done!",
            "Keep an eye on my upcoming updates once I've tracked a full day's wear!",
            "Hope that's helpful in the meantime, darling!",
            "Have you tested this one on your skin yet?",
        ),
    },
    "price": {
        "tones": ("informative_neutral", "value_conscious", "soft_luxury_helpful"),
        "openings": (
            "Happy to share the pricing details I have for {product_name}!",
            "Great question, lovely — here is the price context for this bottle:",
            "Regarding the price of {product_name}:",
            "Here's what to expect price-wise for {product_name}:",
            "If you're budgeting for {product_name}, here are the details:",
        ),
        "bodies": (
            "{price_statement}",
            "{price_statement} Retail prices can vary slightly depending on bottle size and seasonal promotions.",
            "{price_statement} I always suggest sampling or checking a discovery size first if you're blind-buying.",
            "{price_statement} Given the {scent_family} profile, a little goes a long way.",
        ),
        "closings": (
            "Hope that helps with your fragrance wishlist!",
            "I always recommend trying a decant or counter spritz before committing to a full bottle!",
            "Let me know if you'd like to know how the bottle size compares!",
            "Hope that's useful, lovely!",
        ),
    },
    "where_to_buy": {
        "tones": ("helpful_stockist", "uk_retail_grounded", "concise_guide"),
        "openings": (
            "Happy to point you in the right direction, lovely!",
            "Great question on where to find {product_name}:",
            "If you're looking to check out {product_name} in person or online:",
            "Regarding where I picked up {product_name}:",
            "Here is the stockist information I have for {product_name}:",
        ),
        "bodies": (
            "{store_statement}",
            "{store_statement} It's also worth checking {brand}'s official UK counter or boutique.",
            "{store_statement} Always make sure to shop through authorised stockists so you know your bottle is authentic.",
            "{store_statement} If you can visit a counter first to test it on your skin, that's always my favourite way!",
        ),
        "closings": (
            "Hope you manage to track down a sample to try!",
            "Let me know what you think of it if you give it a spritz!",
            "Hope that helps, darling!",
            "Happy fragrance hunting! ✨",
        ),
    },
    "provenance_self_purchased": {
        "tones": ("sincere_transparent", "proud_collector", "warm_direct"),
        "openings": (
            "Thank you for asking, lovely!",
            "Happy to clarify how I got this bottle!",
            "Always happy to be completely transparent about my collection:",
            "Great question — transparency is so important to me:",
            "To answer your question directly, darling:",
        ),
        "bodies": (
            "I bought {product_name} myself with my own money, and everything I've shared here is purely my personal impression on my skin.",
            "Purchased with my own money! I picked up {product_name} for my personal collection and these are my honest thoughts.",
            "I bought this bottle of {product_name} myself — these are entirely my own personal impressions.",
            "This bottle was purchased with my own money for my collection, and I'm just sharing how it wears for me.",
        ),
        "closings": (
            "Hope you found the review helpful! 🤍",
            "Always let you know clearly whenever anything is gifted or an ad!",
            "Let me know if you have any questions about how the notes wear!",
            "Thank you so much for watching and supporting my honest reviews!",
        ),
    },
    "provenance_self_purchased_affiliate": {
        "tones": ("uk_asa_compliant", "transparent_affiliate", "clear_honest"),
        "openings": (
            "Thank you for asking — happy to be 100% transparent!",
            "Great question, lovely, here is the full breakdown:",
            "Always happy to explain how this bottle was bought and linked:",
            "To be completely clear on both the bottle and the link:",
            "Here is the exact provenance for {product_name}:",
        ),
        "bodies": (
            "I purchased {product_name} myself with my own money and these are my personal impressions, though I do include an affiliate link on the post (Ad / Affiliate) which may earn a small commission if used.",
            "The bottle of {product_name} was bought with my own money, and I've also included an affiliate shopping link on this post (Ad — affiliate commission applies).",
            "Purchased with my own money for my collection! Please note that any product link attached to this post is an affiliate link (Ad), so I may earn a small commission at no extra cost to you.",
            "I bought {product_name} myself with my own money; however, because there is an affiliate link attached to the post, it is marked as Ad / Affiliate for full transparency.",
        ),
        "closings": (
            "Thank you for supporting my channel, lovely!",
            "Always want to make sure both my self-purchase and any affiliate links are crystal clear!",
            "Let me know if you'd like any more details on the scent notes!",
            "Hope that answers your question clearly, darling!",
        ),
    },
    "question_general": {
        "tones": ("conversational_advisor", "warm_expert", "soft_luxury_guide"),
        "openings": (
            "Such a good question, lovely!",
            "Ooh, I love talking about how to style and wear this one!",
            "Happy to share my thoughts on {product_name}!",
            "That's a really thoughtful question about {product_name}:",
            "From my experience wearing {product_name}:",
            "Here is how I personally find {product_name} wears:",
        ),
        "bodies": (
            "Because it's a {scent_family} scent with {vibe_summary}, I find it really versatile across seasons and occasions.",
            "{notes_summary}, which makes {product_name} feel wonderfully balanced whether worn solo or layered.",
            "On my skin, {product_name} has {vibe_summary}, so it works beautifully when you want something polished and memorable.",
            "It has a lovely {scent_family} character — {notes_summary}, so two or three spritzes feel just right.",
            "With {product_name}, the {scent_family} profile feels very wearable and unisex-friendly depending on what you normally gravitate towards.",
        ),
        "closings": (
            "What kind of scent families do you usually gravitate towards?",
            "Hope that helps you picture how it wears, darling!",
            "Let me know if you end up sampling it!",
            "Would love to hear how it settles on your skin if you try it!",
            "Hope that helps! ✨",
        ),
    },
    "multilingual_appreciation": {
        "tones": ("warm_international", "gracious_polyglot"),
        "openings": (
            "Merci beaucoup / Muchas gracias / Thank you so much, lovely!",
            "Thank you so much for your sweet message from afar, darling!",
            "Aw, thank you ever so much for watching and commenting!",
            "So grateful for your lovely comment, thank you!",
        ),
        "bodies": (
            "I'm so glad you enjoyed this look at {product_name} and its {scent_family} notes.",
            "{product_name} is truly a special bottle in my collection with {vibe_summary}.",
            "Sharing my love of fragrance with fellow perfume lovers everywhere is such a joy!",
        ),
        "closings": (
            "Sending you so much love from the UK! 🤍✨",
            "Hope you're wearing a gorgeous fragrance today!",
            "Thank you for being part of our fragrance community!",
        ),
    },
}


def _tokenize_words(text: str) -> Set[str]:
    """Extract normalized lowercase alphanumeric word tokens."""
    return set(re.findall(r"[a-z0-9']+", (text or "").lower()))


def _char_ngrams(text: str, n: int = 3) -> Set[str]:
    """Extract character n-grams for robust near-duplicate detection."""
    cleaned = re.sub(r"\s+", " ", (text or "").lower()).strip()
    if len(cleaned) < n:
        return {cleaned} if cleaned else set()
    return {cleaned[i : i + n] for i in range(len(cleaned) - n + 1)}


def compute_similarity(text_a: str, text_b: str) -> float:
    """
    Compute hybrid semantic/lexical similarity in [0.0, 1.0] combining
    word-level Jaccard similarity (60%) and character 3-gram Jaccard (40%).
    """
    if not text_a or not text_b:
        return 0.0
    if text_a.strip().lower() == text_b.strip().lower():
        return 1.0

    words_a = _tokenize_words(text_a)
    words_b = _tokenize_words(text_b)
    word_union = words_a | words_b
    word_jaccard = (len(words_a & words_b) / float(len(word_union))) if word_union else 0.0

    ngrams_a = _char_ngrams(text_a, 3)
    ngrams_b = _char_ngrams(text_b, 3)
    ngram_union = ngrams_a | ngrams_b
    ngram_jaccard = (len(ngrams_a & ngrams_b) / float(len(ngram_union))) if ngram_union else 0.0

    return round(0.60 * word_jaccard + 0.40 * ngram_jaccard, 4)


class TemplateCatalog:
    """
    Generates 1,200+ structured Ann Reveals reply variations and selects
    semantically diverse candidates using a sliding window of recent replies.
    """

    def __init__(
        self,
        max_recent_memory: int = 60,
        similarity_threshold: float = 0.72,
    ) -> None:
        self.max_recent_memory = max_recent_memory
        self.similarity_threshold = similarity_threshold
        self._recent_replies: Deque[str] = deque(maxlen=max_recent_memory)
        self._variations_by_bucket: Dict[str, List[ReplyTemplateVariation]] = {}
        self._build_catalog()

    def _build_catalog(self) -> None:
        """Build the deterministic combinatorial catalog (>1,500 variations)."""
        for bucket, spec in _TAXONOMY_BUCKETS.items():
            tones = spec["tones"]
            openings = spec["openings"]
            bodies = spec["bodies"]
            closings = spec["closings"]

            bucket_list: List[ReplyTemplateVariation] = []
            idx = 0
            for tone, opening, body, closing in itertools.product(
                tones, openings, bodies, closings
            ):
                idx += 1
                tid = f"TPL-{bucket[:6].upper()}-{idx:04d}"
                bucket_list.append(
                    ReplyTemplateVariation(
                        template_id=tid,
                        intent_bucket=bucket,
                        tone_variant=tone,
                        opening=opening,
                        body_pattern=body,
                        closing=closing,
                    )
                )
            self._variations_by_bucket[bucket] = bucket_list

    def total_variation_count(self) -> int:
        """Return total number of distinct reply template variations in the catalog."""
        return sum(len(v) for v in self._variations_by_bucket.values())

    def enumerate_all_variations(self) -> List[ReplyTemplateVariation]:
        """Return all template variation objects across all intent buckets."""
        all_items: List[ReplyTemplateVariation] = []
        for items in self._variations_by_bucket.values():
            all_items.extend(items)
        return all_items

    def record_used_reply(self, reply_text: str) -> None:
        """Add a sent or drafted reply to the recent memory window."""
        if reply_text and reply_text.strip():
            self._recent_replies.append(reply_text.strip())

    def max_similarity_against_recent(
        self,
        candidate_text: str,
        extra_recent: Optional[Sequence[str]] = None,
    ) -> float:
        """Return the maximum similarity score between candidate_text and recent replies."""
        pool: List[str] = list(self._recent_replies)
        if extra_recent:
            pool.extend(r for r in extra_recent if r)
        if not pool:
            return 0.0
        return max(compute_similarity(candidate_text, prev) for prev in pool)

    def select_diverse_reply(
        self,
        intent_bucket: str,
        seed_key: str = "",
        recent_replies: Optional[Sequence[str]] = None,
        **context: str,
    ) -> Tuple[str, float, str]:
        """
        Select and render a variation for `intent_bucket` that minimizes near-duplicate
        similarity against `recent_replies` and internal memory.
        Returns (rendered_reply, duplicate_similarity_score, template_id).
        """
        variations = self._variations_by_bucket.get(
            intent_bucket, self._variations_by_bucket["question_general"]
        )
        total = len(variations)
        if total == 0:
            raise RuntimeError(f"No variations registered for bucket: {intent_bucket}")

        # Deterministic starting offset derived from seed_key + current memory length
        digest = hashlib.sha256(
            f"{intent_bucket}:{seed_key}:{len(self._recent_replies)}".encode("utf-8")
        ).hexdigest()
        start_idx = int(digest[:8], 16) % total

        best_text = ""
        best_sim = 1.0
        best_tid = variations[start_idx].template_id

        # Probe up to 36 evenly spaced candidates across opening/body/closing combinations
        step = max(1, total // 36)
        for probe in range(min(36, total)):
            idx = (start_idx + probe * step) % total
            var = variations[idx]
            rendered = var.render(**context)
            sim = self.max_similarity_against_recent(rendered, extra_recent=recent_replies)
            if sim < best_sim:
                best_sim = sim
                best_text = rendered
                best_tid = var.template_id
            if sim < 0.35:
                # Sufficiently novel — stop early
                break

        self.record_used_reply(best_text)
        return best_text, round(best_sim, 4), best_tid
