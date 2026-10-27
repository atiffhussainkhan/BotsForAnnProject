"""
Redacted Human-Reviewable Appeal Packet Builder.

Implements FR-032, FR-057, NFR-06, and Hard Rule G6:
- Assembles human-reviewable appeal packets with timeline, policy version citation,
  PII-redacted purchase proof, SHA-256 evidence checksums, commercial status declaration,
  factual statement, and owner sign-off block.
- Guarantees zero unredacted card numbers, billing addresses, emails, phone numbers, or raw order IDs.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from apps.backend.appeals.tracker import (
    AppealCase,
    AppealLifecycleStatus,
    AppealsTracker,
)
from apps.backend.provenance.matcher import ReceiptRecord
from apps.backend.provenance.redactor import ReceiptRedactor
from apps.backend.provenance.vault import ImmutableEvidenceSnapshot


@dataclass(frozen=True)
class RedactedAppealPacket:
    """
    Human-reviewable, PII-redacted appeal evidence bundle ready for manual submission (FR-032).
    """

    packet_id: str
    case_id: str
    platform: str
    platform_post_id: str
    violation_reference_code: str
    violation_category: str
    provenance_evidence_relevant: bool
    policy_version_citations: List[str]
    chronological_timeline: List[str]
    commercial_status_declaration: str
    redacted_purchase_proof_excerpt: str
    receipt_sha256: Optional[str]
    snapshot_checksum: Optional[str]
    merchant_summary: str
    factual_appeal_statement: str
    owner_sign_off_required: bool
    owner_sign_off_name: Optional[str]
    automated_submission_blocked: bool = True
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_markdown(self) -> str:
        """Render the redacted appeal packet as a clean human-reviewable Markdown document."""
        timeline_md = "\n".join(f"- {item}" for item in self.chronological_timeline)
        citations_md = ", ".join(self.policy_version_citations)
        sign_off = self.owner_sign_off_name or "[PENDING OWNER SIGNATURE — MANUAL SUBMISSION REQUIRED]"
        return (
            f"# Redacted Appeal Evidence Packet (`{self.packet_id}`)\n\n"
            f"- **Case ID:** `{self.case_id}`\n"
            f"- **Platform & Post ID:** `{self.platform}` / `{self.platform_post_id}`\n"
            f"- **Violation Reference Code:** `{self.violation_reference_code}`\n"
            f"- **Category:** `{self.violation_category}`\n"
            f"- **Provenance Proof Directly Relevant:** `{self.provenance_evidence_relevant}`\n"
            f"- **Policy Citations:** {citations_md}\n"
            f"- **Receipt SHA-256:** `{self.receipt_sha256 or 'N/A'}`\n"
            f"- **Upload Snapshot Checksum:** `{self.snapshot_checksum or 'N/A'}`\n"
            f"- **Merchant Summary:** {self.merchant_summary}\n\n"
            f"## 1. Commercial & Provenance Status Declaration\n"
            f"{self.commercial_status_declaration}\n\n"
            f"## 2. Factual Statement for Platform Reviewer\n"
            f"{self.factual_appeal_statement}\n\n"
            f"## 3. Redacted Purchase Proof Excerpt (UK GDPR Scrubbed)\n"
            f"```text\n{self.redacted_purchase_proof_excerpt}\n```\n\n"
            f"## 4. Event Timeline\n"
            f"{timeline_md}\n\n"
            f"## 5. Owner Sign-Off (Manual Submission Only — Zero Automated Flooding)\n"
            f"- **Signed Off By:** {sign_off}\n"
        )


class AppealPacketBuilder:
    """
    Constructs PII-redacted appeal packets from an `AppealCase`, optional `ImmutableEvidenceSnapshot`,
    and optional `ReceiptRecord`.
    """

    def __init__(self, redactor: Optional[ReceiptRedactor] = None) -> None:
        self.redactor = redactor or ReceiptRedactor()

    def build_packet(
        self,
        case: AppealCase,
        tracker: Optional[AppealsTracker] = None,
        snapshot: Optional[ImmutableEvidenceSnapshot] = None,
        receipt: Optional[ReceiptRecord] = None,
        owner_sign_off_name: Optional[str] = None,
    ) -> RedactedAppealPacket:
        """
        Assemble a human-reviewable `RedactedAppealPacket` and transition the case to `DRAFTED`.
        """
        raw_excerpt = ""
        receipt_sha256: Optional[str] = None
        merchant_summary = "No retail receipt linked."

        if receipt is not None:
            raw_excerpt = receipt.redacted_text
            receipt_sha256 = receipt.proof_sha256
            merchant_summary = (
                f"Canonical: {receipt.merchant.normalized_name} "
                f"(Raw label preserved: '{receipt.merchant.merchant_label_raw}', "
                f"Owner verified: {receipt.merchant.owner_verified})"
            )
        elif snapshot is not None and snapshot.redacted_receipt_excerpt:
            raw_excerpt = snapshot.redacted_receipt_excerpt
            receipt_sha256 = snapshot.receipt_sha256
            merchant_summary = (
                f"Canonical: {snapshot.merchant_normalized} "
                f"(Raw label preserved: '{snapshot.merchant_label_raw}')"
            )

        # Double-pass redaction guarantee so zero PII can ever leak into an appeal packet
        scrubbed_excerpt = (
            self.redactor.redact(raw_excerpt).redacted_text
            if raw_excerpt
            else "No receipt excerpt attached (see Root-Cause Analysis for non-provenance flags)."
        )

        # Scrub notification text in case it echoed any private identifier
        scrubbed_timeline = [
            self.redactor.redact(ev).redacted_text for ev in case.timeline_events
        ]

        if snapshot is not None:
            comm_list = ", ".join(snapshot.commercial_relationships) or "NONE"
            commercial_decl = (
                f"Provenance at publish: {snapshot.provenance_claim} "
                f"(Vault status: {snapshot.vault_status_at_publish}). "
                f"Commercial relationships: {comm_list}. "
                f"Native platform disclosure toggle enabled: {snapshot.native_toggle_enabled}."
            )
            citations = [
                snapshot.rule_version,
                "UK-ASA-INF-2026-10-23",
                "TT-COMM-2026-04" if case.notice.platform == "tiktok" else "META-BC-2026",
            ]
        else:
            commercial_decl = (
                "No immutable publish snapshot was linked; refer to attached Vault record."
            )
            citations = [
                "UK-ASA-INF-2026-10-23",
                "TT-COMM-2026-04" if case.notice.platform == "tiktok" else "META-BC-2026",
            ]

        if case.root_cause.is_provenance_evidence_relevant:
            if snapshot and snapshot.commercial_relationships == ["NONE"] and snapshot.provenance_claim == "SELF_PURCHASED":
                factual_statement = (
                    "This post is an independent editorial review of a perfume bottle purchased by the creator "
                    "with personal funds. There is no brand sponsorship, no gifted PR arrangement, no affiliate link, "
                    "and no discount code associated with this post. A UK GDPR-redacted retail purchase receipt "
                    f"(SHA-256: {receipt_sha256 or 'attached'}) is provided to confirm independent self-purchase."
                )
            else:
                factual_statement = (
                    "This post includes upfront UK ASA disclosure ('Ad |') and the platform's native commercial "
                    "disclosure setting aligned with the declared commercial/provenance status. Please review "
                    "the attached upload snapshot checksum and redacted evidence."
                )
        else:
            factual_statement = (
                f"Diagnostic Note: This enforcement notice falls under '{case.notice.category.value}', where "
                "retail purchase provenance is not the primary dispute. The creator requests human review "
                "based on original production assets and platform policy compliance."
            )

        packet = RedactedAppealPacket(
            packet_id=f"pkt-{uuid.uuid4().hex[:10]}",
            case_id=case.case_id,
            platform=case.notice.platform,
            platform_post_id=case.notice.platform_post_id,
            violation_reference_code=case.notice.reference_code,
            violation_category=case.notice.category.value,
            provenance_evidence_relevant=case.root_cause.is_provenance_evidence_relevant,
            policy_version_citations=citations,
            chronological_timeline=scrubbed_timeline,
            commercial_status_declaration=commercial_decl,
            redacted_purchase_proof_excerpt=scrubbed_excerpt,
            receipt_sha256=receipt_sha256,
            snapshot_checksum=snapshot.snapshot_checksum if snapshot else None,
            merchant_summary=merchant_summary,
            factual_appeal_statement=factual_statement,
            owner_sign_off_required=True,
            owner_sign_off_name=owner_sign_off_name,
            automated_submission_blocked=True,
        )

        case.packet_id = packet.packet_id
        if tracker is not None and case.status == AppealLifecycleStatus.CREATED:
            tracker.transition_status(
                case_id=case.case_id,
                new_status=AppealLifecycleStatus.DRAFTED,
                note=f"Redacted appeal packet {packet.packet_id} assembled for owner review.",
            )

        return packet
