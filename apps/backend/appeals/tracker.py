"""
Enforcement Notice Intake, Automation Freeze, Root-Cause Analyzer, and Appeal Lifecycle Tracker.

Implements FR-029 to FR-033 and Hard Rule G6:
- Ingests violation screenshots, reference codes, notification text, content IDs, and exported notices.
- Classifies into the 9 mandatory taxonomy categories (FR-030).
- Immediately freezes automated comment replies and mutations for the affected post (`freeze_post_automation`).
- Performs root-cause analysis without false certainty, distinguishing provenance-relevant flags
  from non-provenance flags (e.g., copyright music or unoriginality).
- Tracks appeal lifecycle (`CREATED` -> `DRAFTED` -> `SUBMITTED_BY_USER` -> `PENDING` ->
  `OUTCOME_RECORDED` -> `FOLLOW_UP_DUE`) with zero automated ticket submission.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set

from apps.backend.provenance.vault import ImmutableEvidenceSnapshot


class ViolationCategory(str, Enum):
    """Mandatory 9-category violation taxonomy (FR-030)."""

    COMMERCIAL_DISCLOSURE = "commercial_disclosure"
    PAID_PARTNERSHIP = "paid_partnership"
    AFFILIATE_TIKTOK_SHOP = "affiliate_tiktok_shop"
    UNORIGINAL_CONTENT = "unoriginal_content"
    COPYRIGHT_MUSIC = "copyright_music"
    COMMUNITY_GUIDELINE = "community_guideline"
    SPAM_AUTOMATION = "spam_automation"
    RECOMMENDATION_INELIGIBILITY = "recommendation_ineligibility"
    OTHER = "other"


class AppealLifecycleStatus(str, Enum):
    """Appeal case lifecycle states (FR-033). Zero automated ticket submission allowed."""

    CREATED = "CREATED"
    DRAFTED = "DRAFTED"
    SUBMITTED_BY_USER = "SUBMITTED_BY_USER"
    PENDING = "PENDING"
    OUTCOME_RECORDED = "OUTCOME_RECORDED"
    FOLLOW_UP_DUE = "FOLLOW_UP_DUE"


@dataclass(frozen=True)
class RootCauseAnalysis:
    """
    Diagnostic root-cause analysis without false certainty (FR-031).
    Explicitly states whether purchase provenance proof is relevant to the flag.
    """

    inferred_category: ViolationCategory
    is_provenance_evidence_relevant: bool
    diagnostic_summary: str
    possible_contributing_factors: List[str]
    recommended_owner_actions: List[str]
    uncertainty_disclaimer: str


@dataclass
class ViolationNotice:
    """Ingested platform enforcement or moderation notice (FR-029)."""

    notice_id: str
    platform: str  # "instagram" or "tiktok"
    platform_post_id: str
    reference_code: str
    notification_text: str
    screenshot_ref: Optional[str]
    category: ViolationCategory
    received_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class AppealCase:
    """Lifecycle record for an enforcement & appeal case (FR-033)."""

    case_id: str
    notice: ViolationNotice
    status: AppealLifecycleStatus
    post_automation_frozen: bool
    root_cause: RootCauseAnalysis
    timeline_events: List[str] = field(default_factory=list)
    owner_signed_off_by: Optional[str] = None
    owner_submitted_at: Optional[str] = None
    outcome_summary: Optional[str] = None
    packet_id: Optional[str] = None


class AppealsTracker:
    """
    Manages violation intake, automatic per-post automation freezes (Rule G6),
    root-cause analysis, and manual appeal lifecycle transitions.
    """

    _PROVENANCE_RELEVANT_CATEGORIES: Set[ViolationCategory] = {
        ViolationCategory.COMMERCIAL_DISCLOSURE,
        ViolationCategory.PAID_PARTNERSHIP,
        ViolationCategory.AFFILIATE_TIKTOK_SHOP,
    }

    def __init__(self) -> None:
        self.cases: Dict[str, AppealCase] = {}
        self.frozen_posts: Set[str] = set()  # format: "{platform}:{platform_post_id}"

    def freeze_post_automation(self, platform: str, platform_post_id: str) -> str:
        """
        Immediately freeze all automated comment replies and mutations for a flagged post (Rule G6).
        """
        key = f"{platform.strip().lower()}:{platform_post_id.strip()}"
        self.frozen_posts.add(key)
        return key

    def is_post_automation_frozen(self, platform: str, platform_post_id: str) -> bool:
        """Return True if automation on the specified post has been frozen due to an enforcement flag."""
        key = f"{platform.strip().lower()}:{platform_post_id.strip()}"
        return key in self.frozen_posts

    @staticmethod
    def classify_notice_text(
        notification_text: str,
        explicit_category: Optional[ViolationCategory] = None,
    ) -> ViolationCategory:
        """Classify a platform violation notice into one of the 9 mandatory taxonomy categories."""
        if explicit_category is not None:
            return explicit_category

        text = (notification_text or "").lower()
        if any(k in text for k in ("tiktok shop", "affiliate link", "product anchor", "shop commission")):
            return ViolationCategory.AFFILIATE_TIKTOK_SHOP
        if any(k in text for k in ("paid partnership", "branded content tag", "brand partner")):
            return ViolationCategory.PAID_PARTNERSHIP
        if any(k in text for k in ("undisclosed commercial", "promotional content", "commercial content disclosure", "hidden ad")):
            return ViolationCategory.COMMERCIAL_DISCLOSURE
        if any(k in text for k in ("unoriginal", "reproduced", "watermarked", "reposted", "low-effort")):
            return ViolationCategory.UNORIGINAL_CONTENT
        if any(k in text for k in ("copyright", "music rights", "muted audio", "commercial music library", "uml", "dmca")):
            return ViolationCategory.COPYRIGHT_MUSIC
        if any(k in text for k in ("spam", "inauthentic engagement", "automated behaviour", "repetitive comments")):
            return ViolationCategory.SPAM_AUTOMATION
        if any(k in text for k in ("not eligible for the for you feed", "ineligible for recommendation", "for you feed")):
            return ViolationCategory.RECOMMENDATION_INELIGIBILITY
        if any(k in text for k in ("community guidelines", "harassment", "dangerous", "regulated goods")):
            return ViolationCategory.COMMUNITY_GUIDELINE
        return ViolationCategory.OTHER

    def analyze_root_cause(
        self,
        category: ViolationCategory,
        notification_text: str,
        snapshot: Optional[ImmutableEvidenceSnapshot] = None,
    ) -> RootCauseAnalysis:
        """
        Produce a balanced, non-dogmatic root-cause analysis (FR-031) that clearly separates
        provenance proof from non-provenance policy flags.
        """
        is_prov_relevant = category in self._PROVENANCE_RELEVANT_CATEGORIES
        uncertainty = (
            "NO FALSE CERTAINTY: Platform moderation notices are generated by opaque classifiers. "
            "The factors below are diagnostic hypotheses based on post metadata and Vault records."
        )

        if is_prov_relevant:
            factors = [
                "Automated platform classifier detected brand/perfume bottle close-up, price mention, or retailer reference and inferred undisclosed commercial content.",
            ]
            if snapshot and snapshot.commercial_relationships and snapshot.commercial_relationships != ["NONE"]:
                factors.append(
                    f"Post had active commercial relationships ({', '.join(snapshot.commercial_relationships)}); "
                    f"verify whether native toggle ({snapshot.native_toggle_enabled}) and upfront 'Ad |' label were both active."
                )
            elif snapshot and snapshot.provenance_claim == "SELF_PURCHASED":
                factors.append(
                    "Post was recorded as an independent self-purchase with zero commercial links; "
                    "this appears to be a false-positive branded content flag where redacted purchase proof is directly relevant."
                )
            actions = [
                "Attach the PII-redacted Vault receipt excerpt and SHA-256 evidence hash in the manual appeal.",
                "If any affiliate link or discount code WAS present, enable the native Paid Partnership / Commercial Content toggle rather than disputing commercial status.",
            ]
            summary = (
                f"Flag classified under '{category.value}'. Purchase provenance and commercial relationship "
                "records from the Verified Purchases Vault ARE directly relevant to this appeal."
            )
        elif category == ViolationCategory.COPYRIGHT_MUSIC:
            factors = [
                "Audio track may not be cleared in the platform's Commercial Music Library (CML) or triggered a rights-holder match.",
                "Note: Attaching a perfume purchase receipt will NOT resolve a music copyright flag.",
            ]
            actions = [
                "Replace audio with Original Voiceover or an approved Commercial Music Library track.",
                "Do not rely on retail purchase receipts to appeal music licensing flags.",
            ]
            summary = (
                "Flag classified under 'copyright_music'. Purchase provenance proof is NOT the primary "
                "remedy; audio licensing/CML status must be addressed."
            )
        elif category == ViolationCategory.UNORIGINAL_CONTENT:
            factors = [
                "Classifier flagged video for potential B-roll reuse, external watermark, or cross-platform export metadata.",
                "Note: Purchase receipts prove bottle ownership but do not prove video footage originality.",
            ]
            actions = [
                "Provide original camera-roll recording timestamps/project timeline in the manual appeal.",
                "Ensure no third-party watermarks or stock clips were included.",
            ]
            summary = (
                "Flag classified under 'unoriginal_content'. Original camera-roll production proof is required "
                "(purchase receipts alone do not address video originality)."
            )
        else:
            factors = [
                f"Platform notice references '{category.value}': {notification_text[:120]}",
                "Automated reply activity on this post has been frozen immediately (Rule G6) to prevent compounding flags.",
            ]
            actions = [
                "Review the specific community/recommendation guideline cited in the native app before submitting a manual appeal.",
            ]
            summary = (
                f"Flag classified under '{category.value}'. Provenance proof is secondary; review the specific "
                "platform policy notice carefully."
            )

        return RootCauseAnalysis(
            inferred_category=category,
            is_provenance_evidence_relevant=is_prov_relevant,
            diagnostic_summary=summary,
            possible_contributing_factors=factors,
            recommended_owner_actions=actions,
            uncertainty_disclaimer=uncertainty,
        )

    def intake_violation(
        self,
        platform: str,
        platform_post_id: str,
        reference_code: str,
        notification_text: str,
        screenshot_ref: Optional[str] = None,
        explicit_category: Optional[ViolationCategory] = None,
        snapshot: Optional[ImmutableEvidenceSnapshot] = None,
    ) -> AppealCase:
        """
        Ingest a violation notice (FR-029), immediately freeze automation on the post (Rule G6),
        run root-cause analysis (FR-031), and create an `AppealCase` in `CREATED` state (FR-033).
        """
        category = self.classify_notice_text(
            notification_text=notification_text,
            explicit_category=explicit_category,
        )
        notice = ViolationNotice(
            notice_id=f"vio-{uuid.uuid4().hex[:10]}",
            platform=platform.strip().lower(),
            platform_post_id=platform_post_id.strip(),
            reference_code=reference_code.strip(),
            notification_text=notification_text.strip(),
            screenshot_ref=screenshot_ref,
            category=category,
        )

        # Rule G6: Immediately freeze automated replies/actions on the affected post
        self.freeze_post_automation(notice.platform, notice.platform_post_id)

        root_cause = self.analyze_root_cause(
            category=category,
            notification_text=notification_text,
            snapshot=snapshot,
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        case = AppealCase(
            case_id=f"case-{uuid.uuid4().hex[:10]}",
            notice=notice,
            status=AppealLifecycleStatus.CREATED,
            post_automation_frozen=True,
            root_cause=root_cause,
            timeline_events=[
                f"{now_iso}: Violation notice '{notice.reference_code}' ingested ({category.value}).",
                f"{now_iso}: Rule G6 enforced — automated comment replies frozen for {notice.platform}:{notice.platform_post_id}.",
            ],
        )
        self.cases[case.case_id] = case
        return case

    def transition_status(
        self,
        case_id: str,
        new_status: AppealLifecycleStatus,
        note: str = "",
        owner_signed_off_by: Optional[str] = None,
    ) -> AppealCase:
        """
        Advance the appeal case lifecycle (FR-033).
        Requires `owner_signed_off_by` when transitioning to `SUBMITTED_BY_USER`.
        """
        if case_id not in self.cases:
            raise KeyError(f"AppealCase '{case_id}' not found.")
        case = self.cases[case_id]

        if new_status == AppealLifecycleStatus.SUBMITTED_BY_USER and not owner_signed_off_by:
            raise ValueError(
                "Rule G6 / FR-032: Transitioning to SUBMITTED_BY_USER requires explicit owner_signed_off_by."
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        case.status = new_status
        if owner_signed_off_by:
            case.owner_signed_off_by = owner_signed_off_by
        if new_status == AppealLifecycleStatus.SUBMITTED_BY_USER:
            case.owner_submitted_at = now_iso
        if new_status == AppealLifecycleStatus.OUTCOME_RECORDED and note:
            case.outcome_summary = note

        event_line = f"{now_iso}: Status -> {new_status.value}"
        if note:
            event_line += f" ({note})"
        case.timeline_events.append(event_line)
        return case
