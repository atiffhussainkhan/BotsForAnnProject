"""
Single-Upload Dual-Platform Content Studio (Instagram & TikTok).

Implements FR-022, FR-024, FR-025, FR-026, FR-047, FR-048, FR-054, FR-055:
- Generates independent Instagram and TikTok content packages from one upload.
- Produces compliant captions (default 5 hashtags), on-screen overlay text, cover title,
  alt-text, optional non-repetitive ownership comment (with FR-055 anti-spam guard),
  native platform toggle instructions, and preflight risk reports.
- Provides ready-to-verify Sample Case A (Instagram Empyrean self-purchased perfume review)
  and Sample Case B (TikTok independent evaluation of the same perfume, plus affiliate variant).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from apps.backend.compliance.disclosure_engine import (
    CommercialRelationship,
    DisclosureDecision,
    DisclosureEngine,
    PlatformType,
    ProvenanceStatus,
)
from apps.backend.compliance.preflight import (
    PreflightChecker,
    PreflightInput,
    PreflightReport,
)
from apps.backend.provenance.matcher import VaultConfidenceStatus


DEFAULT_FIVE_HASHTAGS: List[str] = [
    "#perfumetok",
    "#fragrancereview",
    "#nicheperfume",
    "#scentoftheday",
    "#ukfragcomm",
]


@dataclass
class ContentStudioRequest:
    """Single-upload input for generating both Instagram and TikTok content packages."""

    sku: str
    brand: str
    product_name: str
    variant: str
    concentration: str
    size_ml: int
    fragrance_notes_summary: str
    wear_impression_summary: str
    provenance_status: ProvenanceStatus
    vault_confidence: VaultConfidenceStatus
    instagram_commercial_relationships: Sequence[CommercialRelationship] = field(
        default_factory=lambda: [CommercialRelationship.NONE]
    )
    tiktok_commercial_relationships: Sequence[CommercialRelationship] = field(
        default_factory=lambda: [CommercialRelationship.NONE]
    )
    custom_hashtags: Optional[Sequence[str]] = None
    include_optional_ownership_comment: bool = False
    instagram_write_enabled: bool = False
    tiktok_write_enabled: bool = False
    uses_non_commercial_licensed_music: bool = False
    merchant_requires_confirmation: bool = False


@dataclass(frozen=True)
class PlatformContentPackage:
    """Generated compliant content package for a single platform (Instagram or TikTok)."""

    platform: PlatformType
    caption: str
    hashtags: List[str]
    on_screen_overlay_text: str
    cover_title: str
    alt_text: str
    optional_ownership_comment: Optional[str]
    ownership_comment_delivery_mode: str  # "SUPPRESSED", "DRAFT_COPY_PASTE", "LIVE_READY"
    native_toggle_setting: str
    native_toggle_instructions: str
    one_tap_copy_fallback_instructions: str
    preflight_report: PreflightReport


@dataclass(frozen=True)
class DualPlatformPackage:
    """Combined single-upload output containing independent Instagram and TikTok packages (FR-047)."""

    sku: str
    instagram_package: PlatformContentPackage
    tiktok_package: PlatformContentPackage


class DualPlatformContentStudio:
    """
    Generates brand-aligned (Ann Reveals warm feminine soft-luxury UK English)
    Instagram and TikTok packages while strictly enforcing Hard Rules G1–G5.
    """

    # Diverse, natural UK-English ownership comment templates rotated to prevent repetition (FR-055)
    _OWNERSHIP_COMMENT_TEMPLATES: List[str] = [
        "For anyone wondering, I bought this {size_ml}ml bottle of {product_name} with my own money — sharing my personal wear notes.",
        "Picked up this bottle of {brand} {product_name} myself; all thoughts on the scent and projection are my own.",
        "Purchased this {product_name} ({concentration}) myself for my personal collection — hope these notes help if you're sampling it!",
        "Bought with my own money for my wardrobe; just sharing how {product_name} wears on my skin.",
    ]

    def __init__(
        self,
        disclosure_engine: Optional[DisclosureEngine] = None,
        preflight_checker: Optional[PreflightChecker] = None,
    ) -> None:
        self.engine = disclosure_engine or DisclosureEngine()
        self.preflight = preflight_checker or PreflightChecker(disclosure_engine=self.engine)
        self._last_template_index_by_platform: Dict[PlatformType, int] = {}
        self._recent_comments_by_platform: Dict[PlatformType, List[str]] = {
            PlatformType.INSTAGRAM: [],
            PlatformType.TIKTOK: [],
        }

    def generate_dual_package(self, request: ContentStudioRequest) -> DualPlatformPackage:
        """
        Generate independent Instagram and TikTok content packages from a single upload request.
        """
        ig_pkg = self._generate_for_platform(
            platform=PlatformType.INSTAGRAM,
            request=request,
            commercial_relationships=request.instagram_commercial_relationships,
            write_enabled=request.instagram_write_enabled,
        )
        tt_pkg = self._generate_for_platform(
            platform=PlatformType.TIKTOK,
            request=request,
            commercial_relationships=request.tiktok_commercial_relationships,
            write_enabled=request.tiktok_write_enabled,
        )
        return DualPlatformPackage(
            sku=request.sku,
            instagram_package=ig_pkg,
            tiktok_package=tt_pkg,
        )

    def _generate_for_platform(
        self,
        platform: PlatformType,
        request: ContentStudioRequest,
        commercial_relationships: Sequence[CommercialRelationship],
        write_enabled: bool,
    ) -> PlatformContentPackage:
        decision: DisclosureDecision = self.engine.evaluate(
            platform=platform,
            provenance_status=request.provenance_status,
            vault_confidence=request.vault_confidence,
            commercial_relationships=commercial_relationships,
        )

        # Select 5 hashtags by default (FR-024)
        hashtags = list(request.custom_hashtags or DEFAULT_FIVE_HASHTAGS)[:5]
        hashtag_block = " ".join(hashtags)

        # Build caption body in Ann Reveals warm UK-English voice
        full_title = f"{request.brand} {request.product_name}".strip()
        if request.variant:
            full_title = f"{full_title} ({request.variant})"

        editorial_body = (
            f"{full_title} — {request.concentration}, {request.size_ml}ml.\n\n"
            f"Notes & opening: {request.fragrance_notes_summary}\n"
            f"Wear & longevity: {request.wear_impression_summary}\n\n"
            f"{decision.approved_provenance_copy}"
        )

        # Ensure 'Ad | ' is placed at index 0 when required (Rule G3)
        if decision.requires_upfront_uk_asa_ad_label:
            if editorial_body.startswith("Ad | "):
                caption_core = editorial_body
            else:
                caption_core = f"{decision.required_caption_prefix}{editorial_body}"
        else:
            caption_core = editorial_body

        caption = f"{caption_core}\n\n{hashtag_block}".strip()

        # On-screen overlay text & cover title
        overlay_prefix = "Ad | " if decision.requires_upfront_uk_asa_ad_label else ""
        on_screen_overlay = (
            f"{overlay_prefix}{request.brand} {request.product_name} ({request.concentration}) — Honest Review"
        )
        cover_title = f"{overlay_prefix}{request.product_name}: First Impressions"
        alt_text = (
            f"Bottle of {request.brand} {request.product_name} {request.concentration} "
            f"({request.size_ml}ml) reviewed by Ann Reveals."
        )

        # Optional non-repetitive first-party ownership comment (FR-025, FR-055, Rule G5)
        ownership_comment, delivery_mode = self._build_optional_ownership_comment(
            platform=platform,
            request=request,
            decision=decision,
            write_enabled=write_enabled,
        )

        # Run preflight check on the generated package
        preflight_input = PreflightInput(
            platform=platform,
            provenance_status=request.provenance_status,
            vault_confidence=request.vault_confidence,
            commercial_relationships=commercial_relationships,
            caption_text=caption,
            on_screen_overlay_text=on_screen_overlay,
            hashtags=hashtags,
            native_toggle_enabled=decision.native_platform_toggle_required,
            uses_non_commercial_licensed_music=request.uses_non_commercial_licensed_music,
            has_tiktok_shop_anchor=(
                CommercialRelationship.TIKTOK_SHOP in commercial_relationships
            ),
            has_affiliate_or_bio_link_callout=any(
                r in commercial_relationships
                for r in (CommercialRelationship.AFFILIATE_LINK, CommercialRelationship.PROMO_CODE)
            ),
            merchant_requires_confirmation=request.merchant_requires_confirmation,
        )
        report = self.preflight.run_preflight(preflight_input)

        fallback_instructions = (
            f"One-Tap Fallback (FR-048): Tap 'Copy Caption', open {platform.value.title()}, "
            f"paste caption, verify toggle ({decision.native_toggle_setting}), and publish."
        )

        return PlatformContentPackage(
            platform=platform,
            caption=caption,
            hashtags=hashtags,
            on_screen_overlay_text=on_screen_overlay,
            cover_title=cover_title,
            alt_text=alt_text,
            optional_ownership_comment=ownership_comment,
            ownership_comment_delivery_mode=delivery_mode,
            native_toggle_setting=decision.native_toggle_setting,
            native_toggle_instructions=decision.native_toggle_instructions,
            one_tap_copy_fallback_instructions=fallback_instructions,
            preflight_report=report,
        )

    def _build_optional_ownership_comment(
        self,
        platform: PlatformType,
        request: ContentStudioRequest,
        decision: DisclosureDecision,
        write_enabled: bool,
    ) -> tuple[Optional[str], str]:
        """
        Enforce FR-025 & FR-055 Anti-Spam Ownership Comment Guard:
        - Disabled unless explicitly requested (`include_optional_ownership_comment=True`).
        - Suppressed if commercial incentives exist (disclosure already belongs in the upfront caption)
          or if the purchase is not `VERIFIED_SELF_PURCHASE`.
        - Rotates across templates so consecutive posts never use identical wording.
        - Reports `DRAFT_COPY_PASTE` when write scopes are disabled (`TIKTOK_WRITE_ENABLED=false` /
          `INSTAGRAM_WRITE_ENABLED=false`).
        """
        if not request.include_optional_ownership_comment:
            return None, "SUPPRESSED"
        if decision.has_commercial_incentive:
            return None, "SUPPRESSED"
        if (
            request.provenance_status != ProvenanceStatus.SELF_PURCHASED
            or request.vault_confidence != VaultConfidenceStatus.VERIFIED_SELF_PURCHASE
        ):
            return None, "SUPPRESSED"

        last_idx = self._last_template_index_by_platform.get(platform, -1)
        next_idx = (last_idx + 1) % len(self._OWNERSHIP_COMMENT_TEMPLATES)
        self._last_template_index_by_platform[platform] = next_idx

        template = self._OWNERSHIP_COMMENT_TEMPLATES[next_idx]
        rendered = template.format(
            size_ml=request.size_ml,
            product_name=request.product_name,
            brand=request.brand,
            concentration=request.concentration,
        )

        # Ensure non-repetition against most recent comment on same platform
        recent = self._recent_comments_by_platform[platform]
        if recent and recent[-1] == rendered:
            next_idx = (next_idx + 1) % len(self._OWNERSHIP_COMMENT_TEMPLATES)
            self._last_template_index_by_platform[platform] = next_idx
            rendered = self._OWNERSHIP_COMMENT_TEMPLATES[next_idx].format(
                size_ml=request.size_ml,
                product_name=request.product_name,
                brand=request.brand,
                concentration=request.concentration,
            )

        recent.append(rendered)
        delivery_mode = "LIVE_READY" if write_enabled else "DRAFT_COPY_PASTE"
        return rendered, delivery_mode

    def build_sample_case_a_instagram(self) -> PlatformContentPackage:
        """
        Sample Case A: Instagram self-purchased Empyrean Parfums review (zero commercial links).
        """
        req = ContentStudioRequest(
            sku="EMP-VELVET-OUD-100",
            brand="Empyrean Parfums",
            product_name="Celestial Iris",
            variant="Extrait",
            concentration="Extrait de Parfum",
            size_ml=100,
            fragrance_notes_summary="Orris butter, bergamot mist, white suede, and warm ambergris.",
            wear_impression_summary="Measured 8 hours of soft-luxury skin projection with a velvety dry-down.",
            provenance_status=ProvenanceStatus.SELF_PURCHASED,
            vault_confidence=VaultConfidenceStatus.VERIFIED_SELF_PURCHASE,
            instagram_commercial_relationships=[CommercialRelationship.NONE],
            tiktok_commercial_relationships=[CommercialRelationship.NONE],
            include_optional_ownership_comment=True,
            instagram_write_enabled=False,
        )
        return self.generate_dual_package(req).instagram_package

    def build_sample_case_b_tiktok(
        self,
        with_affiliate_link: bool = False,
    ) -> PlatformContentPackage:
        """
        Sample Case B: TikTok evaluation of the same Empyrean Parfums bottle.
        Supports both the pure independent self-purchase mode (`with_affiliate_link=False`)
        and the self-purchased + affiliate link variant (`with_affiliate_link=True`).
        """
        tt_rels = (
            [CommercialRelationship.AFFILIATE_LINK]
            if with_affiliate_link
            else [CommercialRelationship.NONE]
        )
        req = ContentStudioRequest(
            sku="EMP-VELVET-OUD-100",
            brand="Empyrean Parfums",
            product_name="Celestial Iris",
            variant="Extrait",
            concentration="Extrait de Parfum",
            size_ml=100,
            fragrance_notes_summary="Orris butter, bergamot mist, white suede, and warm ambergris.",
            wear_impression_summary="Measured 8 hours of soft-luxury skin projection with a velvety dry-down.",
            provenance_status=ProvenanceStatus.SELF_PURCHASED,
            vault_confidence=VaultConfidenceStatus.VERIFIED_SELF_PURCHASE,
            instagram_commercial_relationships=[CommercialRelationship.NONE],
            tiktok_commercial_relationships=tt_rels,
            include_optional_ownership_comment=not with_affiliate_link,
            tiktok_write_enabled=False,
        )
        return self.generate_dual_package(req).tiktok_package
