"""
Unified Cross-Platform Verified Purchases Vault & Retroactive Contradiction Guard.

Implements FR-018, FR-019, FR-020, FR-028, FR-051, FR-052, FR-057, FR-058:
- Manages `PerfumeItem` catalog, redacted `ReceiptRecord` evidence, and `PostProvenanceRecord`.
- Creates write-once `ImmutableEvidenceSnapshot` bundles at post publication/upload time.
- Enforces FR-058 Retroactive Receipt Contradiction Guard: newly imported or updated receipts
  that conflict with an already-published post NEVER silently alter the published claim;
  instead, the vault raises a `RetroactiveContradictionAlert` requiring explicit owner review.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from apps.backend.provenance.matcher import (
    MatchResult,
    PerfumeItem,
    ReceiptMatcher,
    ReceiptRecord,
    VaultConfidenceStatus,
)
from apps.backend.provenance.merchant_normalizer import MerchantNormalizer
from apps.backend.provenance.redactor import ReceiptRedactor


@dataclass
class PostProvenanceRecord:
    """
    Per-post, per-perfume provenance record (FR-052).
    """

    record_id: str
    platform: str  # "instagram" or "tiktok"
    platform_post_id: str
    sku: str
    receipt_found: bool
    product_matched: bool
    owner_confirmed: bool
    confidence: float
    vault_status: VaultConfidenceStatus
    last_checked: str
    source: str
    provenance_claim: str  # e.g., "SELF_PURCHASED", "PR_GIFTED", "LOANED", "UNKNOWN"
    ad_relationship: str  # e.g., "NONE", "PAID_PARTNERSHIP", "GIFTED_INCENTIVE", "OWN_BRAND"
    affiliate_relationship: str  # e.g., "NONE", "AFFILIATE_LINK", "PROMO_CODE", "TIKTOK_SHOP"
    public_copy_status: str  # e.g., "VERIFIED_SELF_PURCHASE_COPY", "AD_DISCLOSED_COPY", "UNVERIFIED_HOLD"
    receipt_id: Optional[str] = None
    proof_sha256: Optional[str] = None


@dataclass(frozen=True)
class ImmutableEvidenceSnapshot:
    """
    Write-once immutable evidence archive snapshot created at upload/publication time (FR-028, FR-057).
    """

    snapshot_id: str
    platform: str
    platform_post_id: str
    sku: str
    caption_text: str
    selected_disclosures: List[str]
    native_toggle_enabled: bool
    product_link_present: bool
    provenance_claim: str
    commercial_relationships: List[str]
    vault_status_at_publish: str
    receipt_sha256: Optional[str]
    redacted_receipt_excerpt: Optional[str]
    merchant_label_raw: Optional[str]
    merchant_normalized: Optional[str]
    rule_version: str
    created_at: str
    snapshot_checksum: str


@dataclass
class RetroactiveContradictionAlert:
    """
    Alert generated when a newly imported or updated receipt contradicts an
    already-published post's provenance claim (FR-058).
    """

    alert_id: str
    platform: str
    platform_post_id: str
    snapshot_id: str
    sku: str
    published_provenance_claim: str
    published_vault_status: str
    new_receipt_id: str
    new_vault_status: str
    contradiction_reasons: List[str]
    created_at: str
    owner_acknowledged: bool = False
    resolution_note: Optional[str] = None


class VerifiedPurchasesVault:
    """
    Cross-platform Verified Purchases Vault managing perfume items, redacted receipts,
    post provenance records, immutable upload snapshots, and FR-058 contradiction alerts.
    """

    def __init__(
        self,
        owner_emails: Optional[List[str]] = None,
    ) -> None:
        self.owner_emails: List[str] = owner_emails or ["ann@annreveals.co.uk", "ann.reveals@gmail.com"]
        self.redactor = ReceiptRedactor()
        self.merchant_normalizer = MerchantNormalizer()
        self.matcher = ReceiptMatcher(
            redactor=self.redactor,
            merchant_normalizer=self.merchant_normalizer,
        )
        self.items: Dict[str, PerfumeItem] = {}
        self.receipts: Dict[str, ReceiptRecord] = {}
        self.match_results_by_sku: Dict[str, MatchResult] = {}
        self.seen_order_ref_hashes: Set[str] = set()
        self.post_records: Dict[str, PostProvenanceRecord] = {}
        self.immutable_snapshots: Dict[str, ImmutableEvidenceSnapshot] = {}
        self.contradiction_alerts: List[RetroactiveContradictionAlert] = []

    def register_item(self, item: PerfumeItem) -> PerfumeItem:
        """Add or update a `PerfumeItem` in the catalog (FR-018)."""
        self.items[item.sku] = item
        return item

    def ingest_receipt_for_item(
        self,
        sku: str,
        raw_text: str,
        merchant_label_raw: str,
        extracted_brand: str,
        extracted_product_name: str,
        extracted_variant: str = "",
        extracted_concentration: str = "EDP",
        extracted_size_ml: Optional[int] = None,
        subtotal_price: float = 0.0,
        discount_amount: float = 0.0,
        net_paid: Optional[float] = None,
        currency: str = "GBP",
        purchase_date: Optional[str] = None,
        owner_verified_merchant: bool = False,
        source_type: str = "RECEIPT_OCR",
        raw_order_ref: Optional[str] = None,
        claimed_self_purchased: bool = True,
    ) -> MatchResult:
        """
        Parse, redact, normalize, and match a receipt against a registered `PerfumeItem`.
        If the item is already linked to any published `ImmutableEvidenceSnapshot` and the new
        receipt introduces a contradiction, trigger FR-058 `RetroactiveContradictionAlert`
        without mutating the existing published snapshot.
        """
        if sku not in self.items:
            raise KeyError(f"PerfumeItem SKU '{sku}' not found in Vault.")

        item = self.items[sku]
        receipt = self.matcher.parse_receipt(
            raw_text=raw_text,
            merchant_label_raw=merchant_label_raw,
            extracted_brand=extracted_brand,
            extracted_product_name=extracted_product_name,
            extracted_variant=extracted_variant,
            extracted_concentration=extracted_concentration,
            extracted_size_ml=extracted_size_ml,
            subtotal_price=subtotal_price,
            discount_amount=discount_amount,
            net_paid=net_paid,
            currency=currency,
            purchase_date=purchase_date,
            owner_verified_merchant=owner_verified_merchant,
            owner_emails=self.owner_emails,
            source_type=source_type,
            raw_order_ref=raw_order_ref,
        )

        self.receipts[receipt.receipt_id] = receipt

        match_result = self.matcher.match(
            item=item,
            receipt=receipt,
            seen_order_ref_hashes=self.seen_order_ref_hashes,
            claimed_self_purchased=claimed_self_purchased,
        )

        if receipt.order_ref_hash and not match_result.is_duplicate_order:
            self.seen_order_ref_hashes.add(receipt.order_ref_hash)

        # Check FR-058: Does this new receipt contradict any already-published snapshot for this SKU?
        self._check_retroactive_contradictions(
            sku=sku,
            new_receipt=receipt,
            new_match=match_result,
        )

        # Update current catalog item status (for future drafts), never mutating past snapshots
        item.confidence = match_result.confidence_score
        item.status = match_result.status
        item.proof_file_ref = receipt.receipt_id
        item.private_order_ref_hash = receipt.order_ref_hash
        self.match_results_by_sku[sku] = match_result

        return match_result

    def evaluate_item_without_receipt(self, sku: str) -> MatchResult:
        """Evaluate an item that has no uploaded receipt proof."""
        if sku not in self.items:
            raise KeyError(f"PerfumeItem SKU '{sku}' not found in Vault.")
        item = self.items[sku]
        match_result = self.matcher.match(item=item, receipt=None)
        item.confidence = match_result.confidence_score
        item.status = match_result.status
        self.match_results_by_sku[sku] = match_result
        return match_result

    def confirm_merchant_for_receipt(
        self,
        sku: str,
        receipt_id: str,
        confirmed_canonical_key: str = "empyrean parfums",
    ) -> MatchResult:
        """
        Explicit owner action (FR-019 / FR-051) confirming an ambiguous merchant label
        (such as 'Experian' -> 'Empyrean Parfums') while preserving `merchant_label_raw`.
        """
        if sku not in self.items:
            raise KeyError(f"PerfumeItem SKU '{sku}' not found in Vault.")
        if receipt_id not in self.receipts:
            raise KeyError(f"Receipt '{receipt_id}' not found in Vault.")

        item = self.items[sku]
        old_receipt = self.receipts[receipt_id]
        updated_merchant = self.merchant_normalizer.normalize(
            merchant_label_raw=old_receipt.merchant.merchant_label_raw,
            owner_verified=True,
            confirmed_canonical_key=confirmed_canonical_key,
        )
        old_receipt.merchant = updated_merchant

        # Temporarily exclude this receipt's own order_ref_hash from duplicate check during re-evaluation
        other_hashes = set(self.seen_order_ref_hashes)
        if old_receipt.order_ref_hash in other_hashes:
            other_hashes.remove(old_receipt.order_ref_hash)

        match_result = self.matcher.match(
            item=item,
            receipt=old_receipt,
            seen_order_ref_hashes=other_hashes,
        )
        item.confidence = match_result.confidence_score
        item.status = match_result.status
        self.match_results_by_sku[sku] = match_result
        return match_result

    def create_post_provenance_record(
        self,
        platform: str,
        platform_post_id: str,
        sku: str,
        owner_confirmed: bool,
        provenance_claim: str,
        ad_relationship: str,
        affiliate_relationship: str,
        public_copy_status: str,
    ) -> PostProvenanceRecord:
        """Create a per-post, per-perfume provenance record (FR-052)."""
        if sku not in self.items:
            raise KeyError(f"PerfumeItem SKU '{sku}' not found in Vault.")
        item = self.items[sku]
        match_result = self.match_results_by_sku.get(sku) or self.evaluate_item_without_receipt(sku)
        receipt = self.receipts.get(match_result.receipt_id) if match_result.receipt_id else None

        record = PostProvenanceRecord(
            record_id=f"ppr-{uuid.uuid4().hex[:12]}",
            platform=platform.lower(),
            platform_post_id=platform_post_id,
            sku=sku,
            receipt_found=receipt is not None,
            product_matched=(match_result.status == VaultConfidenceStatus.VERIFIED_SELF_PURCHASE),
            owner_confirmed=owner_confirmed,
            confidence=match_result.confidence_score,
            vault_status=match_result.status,
            last_checked=datetime.now(timezone.utc).isoformat(),
            source=receipt.source_type if receipt else "NONE",
            provenance_claim=provenance_claim,
            ad_relationship=ad_relationship,
            affiliate_relationship=affiliate_relationship,
            public_copy_status=public_copy_status,
            receipt_id=receipt.receipt_id if receipt else None,
            proof_sha256=receipt.proof_sha256 if receipt else None,
        )
        key = f"{platform.lower()}:{platform_post_id}:{sku}"
        self.post_records[key] = record
        return record

    def create_immutable_snapshot(
        self,
        platform: str,
        platform_post_id: str,
        sku: str,
        caption_text: str,
        selected_disclosures: List[str],
        native_toggle_enabled: bool,
        product_link_present: bool,
        provenance_claim: str,
        commercial_relationships: List[str],
        rule_version: str = "UK-ASA-INF-2026-10-23+TT-COMM-2026-04+META-BC-2026",
    ) -> ImmutableEvidenceSnapshot:
        """
        Capture an immutable upload-time evidence snapshot (FR-028, FR-057).
        """
        if sku not in self.items:
            raise KeyError(f"PerfumeItem SKU '{sku}' not found in Vault.")
        match_result = self.match_results_by_sku.get(sku) or self.evaluate_item_without_receipt(sku)
        receipt = self.receipts.get(match_result.receipt_id) if match_result.receipt_id else None

        created_at = datetime.now(timezone.utc).isoformat()
        payload_for_hash = {
            "platform": platform.lower(),
            "platform_post_id": platform_post_id,
            "sku": sku,
            "caption_text": caption_text,
            "selected_disclosures": selected_disclosures,
            "native_toggle_enabled": native_toggle_enabled,
            "product_link_present": product_link_present,
            "provenance_claim": provenance_claim,
            "commercial_relationships": commercial_relationships,
            "vault_status_at_publish": match_result.status.value,
            "receipt_sha256": receipt.proof_sha256 if receipt else None,
            "rule_version": rule_version,
            "created_at": created_at,
        }
        checksum = hashlib.sha256(
            json.dumps(payload_for_hash, sort_keys=True).encode("utf-8")
        ).hexdigest()

        snapshot = ImmutableEvidenceSnapshot(
            snapshot_id=f"snap-{uuid.uuid4().hex[:12]}",
            platform=platform.lower(),
            platform_post_id=platform_post_id,
            sku=sku,
            caption_text=caption_text,
            selected_disclosures=list(selected_disclosures),
            native_toggle_enabled=native_toggle_enabled,
            product_link_present=product_link_present,
            provenance_claim=provenance_claim,
            commercial_relationships=list(commercial_relationships),
            vault_status_at_publish=match_result.status.value,
            receipt_sha256=receipt.proof_sha256 if receipt else None,
            redacted_receipt_excerpt=receipt.redacted_text[:400] if receipt else None,
            merchant_label_raw=receipt.merchant.merchant_label_raw if receipt else None,
            merchant_normalized=receipt.merchant.normalized_name if receipt else None,
            rule_version=rule_version,
            created_at=created_at,
            snapshot_checksum=checksum,
        )
        key = f"{platform.lower()}:{platform_post_id}"
        self.immutable_snapshots[key] = snapshot
        return snapshot

    def get_snapshot(self, platform: str, platform_post_id: str) -> Optional[ImmutableEvidenceSnapshot]:
        return self.immutable_snapshots.get(f"{platform.lower()}:{platform_post_id}")

    def _check_retroactive_contradictions(
        self,
        sku: str,
        new_receipt: ReceiptRecord,
        new_match: MatchResult,
    ) -> None:
        """
        Enforce FR-058: If an already-published post snapshot exists for `sku` and the newly
        imported receipt contradicts the published claim (e.g., item refunded, PR free, or
        downgraded from VERIFIED_SELF_PURCHASE to CONFLICTED/UNVERIFIED), emit a
        `RetroactiveContradictionAlert` and NEVER silently alter the published snapshot.
        """
        for snap in self.immutable_snapshots.values():
            if snap.sku != sku:
                continue
            if (
                snap.provenance_claim == "SELF_PURCHASED"
                and new_match.status != VaultConfidenceStatus.VERIFIED_SELF_PURCHASE
            ):
                reasons = list(new_match.discrepancies) or [
                    f"New receipt '{new_receipt.receipt_id}' changed status from "
                    f"'{snap.vault_status_at_publish}' to '{new_match.status.value}'."
                ]
                alert = RetroactiveContradictionAlert(
                    alert_id=f"contra-{uuid.uuid4().hex[:10]}",
                    platform=snap.platform,
                    platform_post_id=snap.platform_post_id,
                    snapshot_id=snap.snapshot_id,
                    sku=sku,
                    published_provenance_claim=snap.provenance_claim,
                    published_vault_status=snap.vault_status_at_publish,
                    new_receipt_id=new_receipt.receipt_id,
                    new_vault_status=new_match.status.value,
                    contradiction_reasons=reasons,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                self.contradiction_alerts.append(alert)

    def export_redacted_vault_summary(self) -> Dict[str, object]:
        """Export a UK GDPR compliant, PII-redacted summary of the Vault."""
        return {
            "items": {sku: asdict(item) for sku, item in self.items.items()},
            "snapshots": {k: asdict(snap) for k, snap in self.immutable_snapshots.items()},
            "contradiction_alerts": [asdict(a) for a in self.contradiction_alerts],
        }
