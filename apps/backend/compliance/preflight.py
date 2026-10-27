"""
Dual-Platform Pre-Publication Compliance Preflight Checker (Instagram & TikTok).

Implements FR-023, FR-026, FR-027, FR-053, FR-056:
- Evaluates visuals, overlays, voiceover, hashtags, metadata, pricing, purchase status,
  affiliate links, TikTok Shop tags, PR/gifts, music rights, originality, and brand claims.
- Outputs advisory-only `GREEN` / `AMBER` / `RED` preflight risk grades.
- Never claims "guaranteed compliance" or immunity from platform moderation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Sequence

from apps.backend.compliance.disclosure_engine import (
    CommercialRelationship,
    DisclosureDecision,
    DisclosureEngine,
    PlatformType,
    ProvenanceStatus,
)
from apps.backend.provenance.matcher import VaultConfidenceStatus
from apps.backend.provenance.redactor import ReceiptRedactor


class RiskGrade(str, Enum):
    """Advisory pre-publication compliance risk grade (FR-027)."""

    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"


@dataclass(frozen=True)
class ChecklistItemResult:
    """Single pre-publication checklist evaluation item (FR-023, FR-056)."""

    item_code: str
    title: str
    passed: bool
    grade: RiskGrade
    detail: str
    remediation: Optional[str] = None


@dataclass
class PreflightInput:
    """Input parameters for pre-publication compliance preflight evaluation."""

    platform: PlatformType
    provenance_status: ProvenanceStatus
    vault_confidence: VaultConfidenceStatus
    commercial_relationships: Sequence[CommercialRelationship]
    caption_text: str
    on_screen_overlay_text: str = ""
    hashtags: Sequence[str] = field(default_factory=list)
    native_toggle_enabled: bool = False
    uses_non_commercial_licensed_music: bool = False
    has_tiktok_shop_anchor: bool = False
    has_affiliate_or_bio_link_callout: bool = False
    has_prior_account_warning: bool = False
    is_original_visual_and_voiceover: bool = True
    makes_unverified_medical_or_longevity_claim: bool = False
    merchant_requires_confirmation: bool = False


@dataclass(frozen=True)
class PreflightReport:
    """
    Complete pre-publication compliance preflight report for a single platform (FR-027).
    """

    platform: PlatformType
    overall_grade: RiskGrade
    advisory_disclaimer: str
    decision: DisclosureDecision
    checklist_results: List[ChecklistItemResult]
    blocking_issues: List[str]
    amber_warnings: List[str]


class PreflightChecker:
    """
    Runs independent Instagram and TikTok pre-publication compliance checks.
    """

    ADVISORY_DISCLAIMER = (
        "ADVISORY RISK ASSESSMENT ONLY: This preflight check evaluates alignment with UK ASA/CAP "
        "(23 Oct 2026), CMA, Meta Branded Content, and TikTok Commercial Content (Apr 2026) rules. "
        "It does not guarantee platform reach or immunity from automated platform moderation."
    )

    def __init__(
        self,
        disclosure_engine: Optional[DisclosureEngine] = None,
        redactor: Optional[ReceiptRedactor] = None,
    ) -> None:
        self.engine = disclosure_engine or DisclosureEngine()
        self.redactor = redactor or ReceiptRedactor()

    def run_preflight(self, preflight_input: PreflightInput) -> PreflightReport:
        """
        Execute all pre-publication compliance checks for the target platform.
        """
        effective_rels = list(preflight_input.commercial_relationships)
        if preflight_input.has_tiktok_shop_anchor and CommercialRelationship.TIKTOK_SHOP not in effective_rels:
            effective_rels.append(CommercialRelationship.TIKTOK_SHOP)
        if preflight_input.has_affiliate_or_bio_link_callout and not any(
            r in effective_rels
            for r in (
                CommercialRelationship.AFFILIATE_LINK,
                CommercialRelationship.PROMO_CODE,
                CommercialRelationship.TIKTOK_SHOP,
            )
        ):
            effective_rels.append(CommercialRelationship.AFFILIATE_LINK)

        decision = self.engine.evaluate(
            platform=preflight_input.platform,
            provenance_status=preflight_input.provenance_status,
            vault_confidence=preflight_input.vault_confidence,
            commercial_relationships=effective_rels,
        )

        checklist: List[ChecklistItemResult] = []
        blocking: List[str] = []
        amber: List[str] = []

        # Check 1: Caption UK ASA & Hard Rule G1–G4 compliance
        caption_violations = self.engine.inspect_caption_violations(
            caption_text=preflight_input.caption_text,
            decision=decision,
        )
        overlay_violations = self.engine.inspect_caption_violations(
            caption_text=preflight_input.on_screen_overlay_text,
            decision=decision,
        )
        # Filter overlay violations to G2/G4 ("not an ad" or account-wide claims on overlay)
        overlay_g2_g4 = [
            v for v in overlay_violations if "RULE_G2" in v or "RULE_G4" in v or "VAULT_CONFLICT" in v
        ]
        all_copy_violations = caption_violations + overlay_g2_g4

        if all_copy_violations:
            msg = "; ".join(all_copy_violations)
            blocking.extend(all_copy_violations)
            checklist.append(
                ChecklistItemResult(
                    item_code="PF-01-DISCLOSURE-COPY",
                    title="UK ASA Upfront Disclosure & Truthful Copy (Rules G1–G4)",
                    passed=False,
                    grade=RiskGrade.RED,
                    detail=msg,
                    remediation=(
                        f"Start caption with '{decision.required_caption_prefix}' and remove any "
                        "'not an ad' or account-wide claims."
                    ),
                )
            )
        else:
            checklist.append(
                ChecklistItemResult(
                    item_code="PF-01-DISCLOSURE-COPY",
                    title="UK ASA Upfront Disclosure & Truthful Copy (Rules G1–G4)",
                    passed=True,
                    grade=RiskGrade.GREEN,
                    detail="Caption and overlay text comply with UK ASA upfront disclosure and provenance rules.",
                )
            )

        # Check 2: Platform Native Disclosure Toggle Consistency (FR-026 & Rule G5)
        if decision.native_platform_toggle_required and not preflight_input.native_toggle_enabled:
            issue = (
                f"NATIVE_TOGGLE_MISSING: {decision.native_toggle_setting} is required for this post "
                "because a commercial or gifted relationship exists."
            )
            blocking.append(issue)
            checklist.append(
                ChecklistItemResult(
                    item_code="PF-02-NATIVE-TOGGLE",
                    title="Native Platform Commercial / Paid Partnership Toggle",
                    passed=False,
                    grade=RiskGrade.RED,
                    detail=issue,
                    remediation=decision.native_toggle_instructions,
                )
            )
        elif not decision.native_platform_toggle_required and preflight_input.native_toggle_enabled:
            warn = (
                "UNNECESSARY_COMMERCIAL_TOGGLE (Rule G5): Native commercial toggle is ON even though "
                "this post is an independent self-purchase with zero commercial incentives."
            )
            amber.append(warn)
            checklist.append(
                ChecklistItemResult(
                    item_code="PF-02-NATIVE-TOGGLE",
                    title="Native Platform Commercial / Paid Partnership Toggle",
                    passed=False,
                    grade=RiskGrade.AMBER,
                    detail=warn,
                    remediation="Turn OFF the platform commercial toggle for pure non-commercial self-purchases.",
                )
            )
        else:
            checklist.append(
                ChecklistItemResult(
                    item_code="PF-02-NATIVE-TOGGLE",
                    title="Native Platform Commercial / Paid Partnership Toggle",
                    passed=True,
                    grade=RiskGrade.GREEN,
                    detail=f"Toggle state matches policy ({decision.native_toggle_setting}).",
                )
            )

        # Check 3: Vault Receipt & Provenance Integrity (FR-019, FR-020, FR-051)
        if preflight_input.vault_confidence == VaultConfidenceStatus.CONFLICTED:
            issue = (
                "VAULT_EVIDENCE_CONFLICT: Linked receipt is refunded, £0 PR sample, duplicate, "
                "or mismatched purchaser."
            )
            blocking.append(issue)
            checklist.append(
                ChecklistItemResult(
                    item_code="PF-03-VAULT-PROVENANCE",
                    title="Verified Purchases Vault Evidence Check",
                    passed=False,
                    grade=RiskGrade.RED,
                    detail=issue,
                    remediation="Resolve the receipt conflict in the Vault or update the post's provenance status.",
                )
            )
        elif (
            preflight_input.provenance_status == ProvenanceStatus.SELF_PURCHASED
            and preflight_input.vault_confidence == VaultConfidenceStatus.UNVERIFIED
        ) or preflight_input.merchant_requires_confirmation:
            warn = (
                "UNVERIFIED_PURCHASE_PROOF: Self-purchased bottle does not yet have a fully verified "
                "Vault receipt (or merchant label 'Experian' awaits owner confirmation)."
            )
            amber.append(warn)
            checklist.append(
                ChecklistItemResult(
                    item_code="PF-03-VAULT-PROVENANCE",
                    title="Verified Purchases Vault Evidence Check",
                    passed=True,
                    grade=RiskGrade.AMBER,
                    detail=warn,
                    remediation="Upload/verify the receipt in the Vault so appeal proof is ready before publishing.",
                )
            )
        else:
            checklist.append(
                ChecklistItemResult(
                    item_code="PF-03-VAULT-PROVENANCE",
                    title="Verified Purchases Vault Evidence Check",
                    passed=True,
                    grade=RiskGrade.GREEN,
                    detail=f"Provenance status ({preflight_input.provenance_status.value}) aligns with Vault record.",
                )
            )

        # Check 4: Commercial Music Rights Check (FR-056)
        if decision.requires_commercial_music_library and preflight_input.uses_non_commercial_licensed_music:
            issue = (
                "COMMERCIAL_MUSIC_VIOLATION: Commercial/Ad/Affiliate/Gifted posts cannot use standard "
                "non-commercial licensed pop music on TikTok or Instagram."
            )
            blocking.append(issue)
            checklist.append(
                ChecklistItemResult(
                    item_code="PF-04-MUSIC-RIGHTS",
                    title="Audio & Commercial Music Library Rights",
                    passed=False,
                    grade=RiskGrade.RED,
                    detail=issue,
                    remediation="Switch to Original Voiceover/Audio or a track from the Commercial Music Library (CML).",
                )
            )
        else:
            checklist.append(
                ChecklistItemResult(
                    item_code="PF-04-MUSIC-RIGHTS",
                    title="Audio & Commercial Music Library Rights",
                    passed=True,
                    grade=RiskGrade.GREEN,
                    detail="Audio selection is compatible with post commercial status.",
                )
            )

        # Check 5: Hashtag Hygiene (5-hashtag preference, FR-024)
        num_tags = len(preflight_input.hashtags)
        if num_tags > 8:
            warn = f"EXCESS_HASHTAGS: {num_tags} hashtags supplied; 5 focused hashtags are recommended."
            amber.append(warn)
            checklist.append(
                ChecklistItemResult(
                    item_code="PF-05-HASHTAGS",
                    title="Hashtag Count & Placement Hygiene (5-Hashtag Standard)",
                    passed=True,
                    grade=RiskGrade.AMBER,
                    detail=warn,
                    remediation="Trim to 5 relevant niche fragrance hashtags at the end of the caption.",
                )
            )
        else:
            checklist.append(
                ChecklistItemResult(
                    item_code="PF-05-HASHTAGS",
                    title="Hashtag Count & Placement Hygiene (5-Hashtag Standard)",
                    passed=True,
                    grade=RiskGrade.GREEN,
                    detail=f"Hashtag count ({num_tags}) follows clean platform best practice.",
                )
            )

        # Check 6: Originality, Medical/Longevity Grounding & PII Leak Guard (FR-008, FR-019, FR-023)
        has_pii_in_caption = self.redactor.contains_unredacted_pii(preflight_input.caption_text)
        if has_pii_in_caption:
            issue = "PUBLIC_PII_LEAK_DETECTED: Caption contains unredacted order ref, email, postcode, or card data."
            blocking.append(issue)
            checklist.append(
                ChecklistItemResult(
                    item_code="PF-06-PRIVACY-AND-CLAIMS",
                    title="Privacy, Originality & Grounded Fragrance Claims",
                    passed=False,
                    grade=RiskGrade.RED,
                    detail=issue,
                    remediation="Remove all private receipt/order details from public caption text.",
                )
            )
        elif not preflight_input.is_original_visual_and_voiceover or preflight_input.makes_unverified_medical_or_longevity_claim:
            warn = (
                "ORIGINALITY_OR_CLAIM_WARNING: Reused visuals or unmeasured wear-time/skin claims "
                "increase moderation and recommendation ineligibility risk."
            )
            amber.append(warn)
            checklist.append(
                ChecklistItemResult(
                    item_code="PF-06-PRIVACY-AND-CLAIMS",
                    title="Privacy, Originality & Grounded Fragrance Claims",
                    passed=False,
                    grade=RiskGrade.AMBER,
                    detail=warn,
                    remediation="Use 100% original footage/voiceover and state explicitly if longevity has not been measured yet.",
                )
            )
        else:
            checklist.append(
                ChecklistItemResult(
                    item_code="PF-06-PRIVACY-AND-CLAIMS",
                    title="Privacy, Originality & Grounded Fragrance Claims",
                    passed=True,
                    grade=RiskGrade.GREEN,
                    detail="No PII leaks, unoriginal assets, or ungrounded medical/wear-time claims detected.",
                )
            )

        # Check 7: Prior Account Warning Sensitivity (FR-056)
        if preflight_input.has_prior_account_warning:
            warn = (
                "PRIOR_WARNING_ELEVATED_CARE: Account has a recent moderation flag; verify Vault "
                "snapshot before publishing."
            )
            amber.append(warn)
            checklist.append(
                ChecklistItemResult(
                    item_code="PF-07-ACCOUNT-HEALTH",
                    title="Account Enforcement History Check",
                    passed=True,
                    grade=RiskGrade.AMBER,
                    detail=warn,
                    remediation="Ensure ImmutableEvidenceSnapshot is archived before posting.",
                )
            )

        if blocking:
            overall = RiskGrade.RED
        elif amber:
            overall = RiskGrade.AMBER
        else:
            overall = RiskGrade.GREEN

        return PreflightReport(
            platform=preflight_input.platform,
            overall_grade=overall,
            advisory_disclaimer=self.ADVISORY_DISCLAIMER,
            decision=decision,
            checklist_results=checklist,
            blocking_issues=blocking,
            amber_warnings=amber,
        )
