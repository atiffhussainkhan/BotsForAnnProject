"""
Two-Axis Provenance vs Commercial Relationship Engine (UK ASA/CAP, CMA, Meta, TikTok).

Implements Hard Rules G1–G5 and FR-021, FR-022, FR-026, FR-053, FR-054:
- Maintains strictly independent axes for `ProvenanceStatus` and `CommercialRelationship`.
- Rule G1: `SELF_PURCHASED` never erases `AFFILIATE_LINK`, `PROMO_CODE`, `TIKTOK_SHOP`,
  `PAID_PARTNERSHIP`, `GIFTED_INCENTIVE`, or `OWN_BRAND` disclosure obligations.
- Rule G2: Never claim "not an ad" or "unsponsored" when any commercial incentive exists.
- Rule G3: Require upfront `Ad |` prefix at caption index 0 whenever commercial/PR incentives exist;
  never rely on `#gifted`, `#pr`, or `#aff` alone.
- Rule G4: Scope all purchase claims strictly to the specific bottle/post; block account-wide
  "I never accept gifts" claims.
- Rule G5: Never instruct the creator to enable platform paid/commercial toggles on a genuinely
  non-commercial self-purchased review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Sequence

from apps.backend.provenance.matcher import VaultConfidenceStatus


class ProvenanceStatus(str, Enum):
    """Axis 1: How the creator acquired the featured product."""

    SELF_PURCHASED = "SELF_PURCHASED"
    PR_GIFTED = "PR_GIFTED"
    LOANED = "LOANED"
    FREE_SAMPLE = "FREE_SAMPLE"
    UNKNOWN = "UNKNOWN"


class CommercialRelationship(str, Enum):
    """Axis 2: Any commercial or financial incentive linked to the post or brand."""

    NONE = "NONE"
    AFFILIATE_LINK = "AFFILIATE_LINK"
    PROMO_CODE = "PROMO_CODE"
    PAID_PARTNERSHIP = "PAID_PARTNERSHIP"
    TIKTOK_SHOP = "TIKTOK_SHOP"
    GIFTED_INCENTIVE = "GIFTED_INCENTIVE"
    OWN_BRAND = "OWN_BRAND"


class PlatformType(str, Enum):
    """Target social platform for policy evaluation."""

    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"


@dataclass(frozen=True)
class DisclosureDecision:
    """Complete regulatory and platform disclosure decision for a single platform post."""

    platform: PlatformType
    provenance_status: ProvenanceStatus
    vault_confidence: VaultConfidenceStatus
    commercial_relationships: List[CommercialRelationship]
    has_commercial_incentive: bool
    requires_upfront_uk_asa_ad_label: bool
    required_caption_prefix: str
    native_platform_toggle_required: bool
    native_toggle_setting: str
    native_toggle_instructions: str
    approved_provenance_copy: str
    verified_purchase_badge_allowed: bool
    requires_commercial_music_library: bool
    forbidden_claims: List[str] = field(default_factory=list)
    rule_citations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class DisclosureEngine:
    """
    Evaluates the two-axis `(ProvenanceStatus, CommercialRelationship)` model
    independently for Instagram and TikTok under UK ASA/CAP and CMA rules.
    """

    _NOT_AN_AD_PATTERN = re.compile(
        r"\b(?:not\s+an?\s+ad(?:vert(?:isement)?)?|#notanad|unsponsored|not\s+sponsored|100%\s+non[-\s]?commercial|zero\s+commercial\s+links?)\b",
        re.IGNORECASE,
    )

    _ACCOUNT_WIDE_CLAIM_PATTERN = re.compile(
        r"\b(?:i\s+never\s+accept\s+(?:pr|gifts|sponsorships)|everything\s+on\s+(?:my|this)\s+(?:page|account|channel)\s+is\s+bought\s+by\s+me|this\s+(?:account|page)\s+never\s+does\s+ads)\b",
        re.IGNORECASE,
    )

    _INSUFFICIENT_STANDALONE_TAG_PATTERN = re.compile(
        r"(?:^|\s)#?(?:gifted|pr|prgift|prsample|aff|affiliate|spon|collab)\b",
        re.IGNORECASE,
    )

    _UPFRONT_AD_PREFIX_PATTERN = re.compile(
        r"^\s*(?:#?ad|advert|advertising|advertisement)\b(?:\s*[\|—:-])?",
        re.IGNORECASE,
    )

    def evaluate(
        self,
        platform: PlatformType,
        provenance_status: ProvenanceStatus,
        vault_confidence: VaultConfidenceStatus = VaultConfidenceStatus.UNVERIFIED,
        commercial_relationships: Optional[Sequence[CommercialRelationship]] = None,
    ) -> DisclosureDecision:
        """
        Compute the mandatory disclosure decision for a given platform, provenance,
        vault verification status, and commercial relationship list.
        """
        rels = [
            r
            for r in (commercial_relationships or [CommercialRelationship.NONE])
            if r != CommercialRelationship.NONE
        ]
        if not rels:
            rels = [CommercialRelationship.NONE]

        active_commercial = [r for r in rels if r != CommercialRelationship.NONE]

        # Under UK ASA/CAP & CMA rules, PR_GIFTED and LOANED also constitute material incentives
        is_gifted_or_loaned = provenance_status in (
            ProvenanceStatus.PR_GIFTED,
            ProvenanceStatus.LOANED,
        )
        has_commercial_incentive = bool(active_commercial) or is_gifted_or_loaned

        # Conflict in Vault blocks any verified self-purchase claim
        is_conflicted = vault_confidence == VaultConfidenceStatus.CONFLICTED
        is_verified_self_purchase = (
            provenance_status == ProvenanceStatus.SELF_PURCHASED
            and vault_confidence == VaultConfidenceStatus.VERIFIED_SELF_PURCHASE
        )

        warnings: List[str] = []
        citations: List[str] = ["UK-ASA-INF-2026-10-23 (CAP Code 2.1, 2.4)", "UK-CMA-DMCC-2026"]
        forbidden: List[str] = [
            "I never accept gifts or sponsorships on this account (Rule G4: account-wide absolutes forbidden)",
            "Everything on my page is bought by me (Rule G4)",
        ]

        if is_conflicted:
            warnings.append(
                "VAULT_CONFLICT_DETECTED: Receipt is refunded, £0 PR sample, duplicate, or mismatched purchaser. "
                "Self-purchase claims are blocked until resolved."
            )
            forbidden.append("Purchased with my own money (Blocked due to Vault CONFLICTED status)")

        if provenance_status == ProvenanceStatus.SELF_PURCHASED and not is_verified_self_purchase and not is_conflicted:
            warnings.append(
                "UNVERIFIED_SELF_PURCHASE: Receipt is missing, low-confidence, or merchant ('Experian' vs 'Empyrean') "
                "awaits owner confirmation. Withhold 'Verified Purchase' badge."
            )

        # Determine UK ASA upfront Ad label obligation
        requires_ad_label = has_commercial_incentive
        caption_prefix = "Ad | " if requires_ad_label else ""

        if has_commercial_incentive:
            forbidden.extend(
                [
                    "Not an ad / #notanad (Rule G1/G2: strictly forbidden when affiliate, shop, promo, gift, or paid incentive exists)",
                    "Unsponsored / Not sponsored (Rule G2)",
                    "Standalone #gifted / #pr / #aff without upfront 'Ad' label (Rule G3)",
                ]
            )

        # Determine platform-specific native toggle instructions
        if platform == PlatformType.INSTAGRAM:
            citations.append("META-BC-2026 (Instagram Paid Partnership & Branded Content Policy)")
            if has_commercial_incentive:
                native_toggle_required = True
                native_toggle_setting = "Instagram Paid Partnership Label: ON"
                native_toggle_instructions = (
                    "1. In Instagram post settings, tap 'Add paid partnership label'. "
                    "2. Toggle ON 'Add paid partnership label' (and tag brand partner if applicable). "
                    "3. Keep 'Ad | ' at the very start of the caption for UK ASA upfront prominence."
                )
            else:
                native_toggle_required = False
                native_toggle_setting = "Instagram Paid Partnership Label: OFF"
                native_toggle_instructions = (
                    "Leave Instagram 'Paid partnership label' OFF. Do not mark an independent, "
                    "non-commercial review as a paid partnership."
                )
        else:
            citations.append("TT-COMM-2026-04 (TikTok Commercial Content Disclosure Policy)")
            if CommercialRelationship.TIKTOK_SHOP in active_commercial:
                citations.append("TT-SHOP-MUSIC-2026 (TikTok Shop Creator Affiliate Rules)")
            if has_commercial_incentive:
                native_toggle_required = True
                if CommercialRelationship.OWN_BRAND in active_commercial and len(active_commercial) == 1 and not is_gifted_or_loaned:
                    native_toggle_setting = "TikTok Disclose video content: ON -> 'Your brand' (Promotional content)"
                    native_toggle_instructions = (
                        "1. In TikTok post settings, tap 'Content disclosure and ads'. "
                        "2. Toggle ON 'Disclose video content' and select 'Your brand' (displays 'Promotional content'). "
                        "3. Keep 'Ad | ' at the very beginning of the caption and use Commercial Music Library or Original Audio."
                    )
                else:
                    native_toggle_setting = "TikTok Disclose video content: ON -> 'Branded content' (Paid partnership)"
                    native_toggle_instructions = (
                        "1. In TikTok post settings, tap 'Content disclosure and ads'. "
                        "2. Toggle ON 'Disclose video content' and select 'Branded content' (displays 'Paid partnership'). "
                        "3. Keep 'Ad | ' at the very beginning of the caption and use Commercial Music Library or Original Audio."
                    )
            else:
                native_toggle_required = False
                native_toggle_setting = "TikTok Disclose video content: OFF"
                native_toggle_instructions = (
                    "Leave TikTok 'Disclose video content' toggle OFF (Rule G5: never tell TikTok an "
                    "independent self-purchased review with zero commercial links is paid content). "
                    "Keep redacted receipt in Vault for immediate appeal if mistakenly flagged."
                )

        # Build truthful, non-contradictory public copy (FR-022, FR-054)
        approved_copy = self._build_approved_provenance_copy(
            provenance_status=provenance_status,
            is_verified_self_purchase=is_verified_self_purchase,
            is_conflicted=is_conflicted,
            active_commercial=active_commercial,
        )

        return DisclosureDecision(
            platform=platform,
            provenance_status=provenance_status,
            vault_confidence=vault_confidence,
            commercial_relationships=list(rels),
            has_commercial_incentive=has_commercial_incentive,
            requires_upfront_uk_asa_ad_label=requires_ad_label,
            required_caption_prefix=caption_prefix,
            native_platform_toggle_required=native_toggle_required,
            native_toggle_setting=native_toggle_setting,
            native_toggle_instructions=native_toggle_instructions,
            approved_provenance_copy=approved_copy,
            verified_purchase_badge_allowed=is_verified_self_purchase and not is_conflicted,
            requires_commercial_music_library=has_commercial_incentive,
            forbidden_claims=forbidden,
            rule_citations=citations,
            warnings=warnings,
        )

    @staticmethod
    def _build_approved_provenance_copy(
        provenance_status: ProvenanceStatus,
        is_verified_self_purchase: bool,
        is_conflicted: bool,
        active_commercial: List[CommercialRelationship],
    ) -> str:
        """Construct truthful public provenance wording that never conflicts with commercial status."""
        if is_conflicted:
            return "Personal fragrance impressions."

        if provenance_status == ProvenanceStatus.SELF_PURCHASED:
            base_purchase = (
                "Purchased with my own money. These are my personal impressions."
                if is_verified_self_purchase
                else "I bought this perfume myself and these are my personal impressions."
            )
            if not active_commercial:
                return base_purchase
            # Self-purchased + commercial incentive (Rule G1 & FR-054)
            incentive_labels: List[str] = []
            if CommercialRelationship.AFFILIATE_LINK in active_commercial:
                incentive_labels.append("affiliate link included")
            if CommercialRelationship.PROMO_CODE in active_commercial:
                incentive_labels.append("discount code included")
            if CommercialRelationship.TIKTOK_SHOP in active_commercial:
                incentive_labels.append("linked on TikTok Shop — commission earned")
            if CommercialRelationship.PAID_PARTNERSHIP in active_commercial:
                incentive_labels.append("paid brand partnership")
            if CommercialRelationship.OWN_BRAND in active_commercial:
                incentive_labels.append("own brand promotion")
            if CommercialRelationship.GIFTED_INCENTIVE in active_commercial:
                incentive_labels.append("brand incentive applies")
            joined = ", ".join(incentive_labels)
            return f"Ad | I bought this bottle myself ({joined}). These are my personal impressions."

        if provenance_status == ProvenanceStatus.PR_GIFTED:
            return "Ad | Gifted PR product. These are my honest personal impressions."

        if provenance_status == ProvenanceStatus.LOANED:
            return "Ad | Bottle loaned for review. These are my personal impressions."

        if provenance_status == ProvenanceStatus.FREE_SAMPLE:
            if active_commercial:
                return "Ad | Complimentary sample vial (commercial link/incentive included)."
            return "Complimentary sample vial received with a retail order. These are my personal impressions."

        # UNKNOWN provenance
        if active_commercial:
            return "Ad | Commercial link or brand partnership applies."
        return "Personal fragrance impressions."

    def inspect_caption_violations(
        self,
        caption_text: str,
        decision: DisclosureDecision,
    ) -> List[str]:
        """
        Inspect a draft caption against Hard Rules G1–G4 and return any policy violations.
        """
        violations: List[str] = []
        text = caption_text or ""

        # Rule G2: Never claim "not an ad" when commercial incentive exists
        if decision.has_commercial_incentive and self._NOT_AN_AD_PATTERN.search(text):
            violations.append(
                "RULE_G2_VIOLATION: Caption claims 'not an ad' / 'unsponsored' while a commercial "
                "or gifted incentive exists."
            )

        # Rule G3: Upfront 'Ad' label must appear at the very start when required
        if decision.requires_upfront_uk_asa_ad_label:
            if not self._UPFRONT_AD_PREFIX_PATTERN.search(text):
                violations.append(
                    "RULE_G3_VIOLATION: UK ASA requires an upfront 'Ad' label at the very beginning "
                    "of the caption before any truncation fold."
                )
                if self._INSUFFICIENT_STANDALONE_TAG_PATTERN.search(text):
                    violations.append(
                        "RULE_G3_AMBIGUOUS_LABEL: Caption uses #gifted/#pr/#aff/#spon without an upfront 'Ad' prefix."
                    )

        # Rule G4: Account-wide absolute claims are forbidden
        if self._ACCOUNT_WIDE_CLAIM_PATTERN.search(text):
            violations.append(
                "RULE_G4_VIOLATION: Account-wide absolute claim ('I never accept gifts/ads') is prohibited; "
                "scope provenance strictly to this bottle."
            )

        # Vault conflict check: block self-purchase wording if receipt is conflicted
        if decision.vault_confidence == VaultConfidenceStatus.CONFLICTED:
            if re.search(r"\b(?:bought\s+this\s+(?:perfume\s+|bottle\s+)?myself|purchased\s+with\s+my\s+own\s+money)\b", text, re.IGNORECASE):
                violations.append(
                    "VAULT_CONFLICT_VIOLATION: Caption claims self-purchase while Vault receipt is CONFLICTED (refunded/PR/mismatched)."
                )

        return violations
