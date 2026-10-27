"""
Receipt Parser and Perfume SKU / Variant / Size Fuzzy Matcher.

Implements FR-018, FR-019, FR-020, FR-046, FR-051, FR-052:
- Parses PDF/screenshot/OCR receipt text into structured redacted ReceiptRecords.
- Computes SHA-256 evidence hashes.
- Matches receipts against `PerfumeItem` catalog entries across brand, product name,
  variant, concentration (`EDP`, `EDT`, `Parfum`, `Extrait`, `Cologne`), and size (`size_ml`).
- Detects refunds/cancellations, free PR samples (£0.00 / complimentary), discount/affiliate
  codes on receipts, duplicated order references, mismatched purchaser emails, and
  unverified/Experian merchants.
- Outputs `VaultConfidenceStatus` (`VERIFIED_SELF_PURCHASE`, `UNVERIFIED`, `CONFLICTED`).
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set

from apps.backend.provenance.merchant_normalizer import MerchantNormalizer, NormalizedMerchant
from apps.backend.provenance.redactor import ReceiptRedactor, RedactionResult


class VaultConfidenceStatus(str, Enum):
    """Tri-state purchase verification outcome stored in the Vault."""

    VERIFIED_SELF_PURCHASE = "VERIFIED_SELF_PURCHASE"
    UNVERIFIED = "UNVERIFIED"
    CONFLICTED = "CONFLICTED"


@dataclass
class PerfumeItem:
    """
    Perfume item catalog entry (FR-018).
    """

    sku: str
    product_name: str
    brand: str
    variant: str
    size_ml: int
    concentration: str  # e.g., "EDP", "EDT", "Extrait de Parfum", "Parfum", "Cologne"
    store: str
    purchase_date: str
    private_price: float
    currency: str = "GBP"
    private_order_ref_hash: Optional[str] = None
    proof_file_ref: Optional[str] = None
    confidence: float = 0.0
    status: VaultConfidenceStatus = VaultConfidenceStatus.UNVERIFIED


@dataclass
class ReceiptRecord:
    """
    Redacted, normalized receipt evidence record (FR-019, FR-051).
    Never stores raw unredacted PII, card numbers, or billing addresses.
    """

    receipt_id: str
    proof_sha256: str
    redacted_text: str
    redaction_summary: Dict[str, int]
    merchant: NormalizedMerchant
    extracted_brand: str
    extracted_product_name: str
    extracted_variant: str
    extracted_concentration: str
    extracted_size_ml: Optional[int]
    subtotal_price: float
    discount_amount: float
    net_paid: float
    currency: str
    order_ref_hash: Optional[str]
    purchase_date: Optional[str]
    is_refunded: bool = False
    is_pr_or_free_sample: bool = False
    is_gwp_sample_only: bool = False
    has_discount_code: bool = False
    discount_code_label: Optional[str] = None
    has_affiliate_tracking: bool = False
    purchaser_email_matched_owner: Optional[bool] = None
    source_type: str = "RECEIPT_OCR"  # "PDF_INVOICE", "SCREENSHOT_OCR", "EMAIL_IMPORT", "MANUAL_ENTRY"
    ingested_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class MatchResult:
    """Detailed result of matching a `ReceiptRecord` (or missing proof) to a `PerfumeItem`."""

    sku: str
    receipt_id: Optional[str]
    proof_sha256: Optional[str]
    confidence_score: float
    status: VaultConfidenceStatus
    matched_fields: List[str] = field(default_factory=list)
    discrepancies: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    is_duplicate_order: bool = False
    eligible_for_verified_self_purchase_copy: bool = False


class ReceiptMatcher:
    """
    Parses raw receipt texts (running PII redaction + merchant normalization first)
    and scores matches against target `PerfumeItem` records.
    """

    _CONCENTRATION_ALIASES: Dict[str, str] = {
        "edp": "EDP",
        "eau de parfum": "EDP",
        "extrait": "EXTRAIT",
        "extrait de parfum": "EXTRAIT",
        "parfum": "PARFUM",
        "pure parfum": "PARFUM",
        "edt": "EDT",
        "eau de toilette": "EDT",
        "edc": "EDC",
        "eau de cologne": "EDC",
        "cologne": "EDC",
        "elixir": "ELIXIR",
    }

    _SIZE_PATTERN = re.compile(r"\b(\d{1,3})\s*ml\b", re.IGNORECASE)
    _ORDER_REF_EXTRACT = re.compile(
        r"\b(?:invoice\s*(?:id|no|number|#)|order\s*(?:id|no|number|ref|#)|transaction\s*(?:id|ref|#)|receipt\s*(?:id|no|#))[\s:=-]*([A-Z0-9-]{4,30})\b",
        re.IGNORECASE,
    )
    _REFUND_PATTERN = re.compile(
        r"\b(?:refunded|full\s+refund|credit\s+note|order\s+cancelled|cancelled\s+order|chargeback|payment\s+reversed|returned\s+item)\b",
        re.IGNORECASE,
    )
    _PR_FREE_PATTERN = re.compile(
        r"\b(?:pr\s+sample|press\s+sample|press\s+gift|pr\s+gift|gifted\s+by\s+brand|complimentary\s+pr|not\s+for\s+resale|free\s+pr\s+package|influencer\s+seeding)\b",
        re.IGNORECASE,
    )
    _GWP_SAMPLE_PATTERN = re.compile(
        r"\b(?:free\s+sample\s+vial|discovery\s+vial|complimentary\s+2ml|gwp\s+sample|gift\s+with\s+purchase\s+sample)\b",
        re.IGNORECASE,
    )
    _AFFILIATE_PATTERN = re.compile(
        r"\b(?:affiliate\s+commission|affiliate\s+order|creator\s+commission|ltk\s+tracking|shopmy\s+commission|tiktok\s+shop\s+affiliate|partner\s+referral\s+credit)\b",
        re.IGNORECASE,
    )
    _DISCOUNT_CODE_PATTERN = re.compile(
        r"\b(?:promo\s*code|discount\s*code|voucher\s*code|coupon|vip\s*discount|staff\s*discount)[\s:=-]*([A-Z0-9_-]{3,20})?\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        redactor: Optional[ReceiptRedactor] = None,
        merchant_normalizer: Optional[MerchantNormalizer] = None,
    ) -> None:
        self.redactor = redactor or ReceiptRedactor()
        self.merchant_normalizer = merchant_normalizer or MerchantNormalizer()

    @classmethod
    def normalize_concentration(cls, raw_conc: str) -> str:
        cleaned = (raw_conc or "").strip().lower()
        for phrase, canon in sorted(
            cls._CONCENTRATION_ALIASES.items(), key=lambda x: -len(x[0])
        ):
            if phrase in cleaned:
                return canon
        return cleaned.upper()

    def parse_receipt(
        self,
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
        owner_emails: Optional[List[str]] = None,
        source_type: str = "RECEIPT_OCR",
        raw_order_ref: Optional[str] = None,
    ) -> ReceiptRecord:
        """
        Parse raw receipt evidence into a PII-redacted `ReceiptRecord`.
        """
        # Extract order reference hash BEFORE redaction removes the raw order number
        order_ref_candidate = raw_order_ref
        if not order_ref_candidate and raw_text:
            m_ref = self._ORDER_REF_EXTRACT.search(raw_text)
            if m_ref:
                order_ref_candidate = m_ref.group(1)

        order_ref_hash = (
            ReceiptRedactor.hash_identifier(order_ref_candidate)
            if order_ref_candidate
            else None
        )

        # Infer size_ml from raw_text if not explicitly provided
        if extracted_size_ml is None and raw_text:
            m_size = self._SIZE_PATTERN.search(raw_text)
            if m_size:
                extracted_size_ml = int(m_size.group(1))

        # Detect refund, PR/free status, GWP sample, affiliate, and discount codes from text
        is_refunded = bool(raw_text and self._REFUND_PATTERN.search(raw_text))
        is_pr_or_free = bool(raw_text and self._PR_FREE_PATTERN.search(raw_text))
        is_gwp_sample = bool(raw_text and self._GWP_SAMPLE_PATTERN.search(raw_text))
        has_affiliate = bool(raw_text and self._AFFILIATE_PATTERN.search(raw_text))

        discount_match = self._DISCOUNT_CODE_PATTERN.search(raw_text) if raw_text else None
        has_discount = bool(discount_match or discount_amount > 0.0)
        discount_label = (
            discount_match.group(1)
            if (discount_match and discount_match.group(1))
            else ("DISCOUNT_APPLIED" if has_discount else None)
        )

        computed_net = (
            net_paid
            if net_paid is not None
            else max(0.0, round(subtotal_price - discount_amount, 2))
        )
        if computed_net == 0.0 and subtotal_price == 0.0 and is_pr_or_free:
            is_pr_or_free = True

        # Run deterministic PII redaction BEFORE creating the stored record
        redaction: RedactionResult = self.redactor.redact(
            raw_text=raw_text,
            owner_emails=owner_emails,
        )

        # Normalize merchant while preserving raw label and enforcing Experian/Empyrean rule
        merchant: NormalizedMerchant = self.merchant_normalizer.normalize(
            merchant_label_raw=merchant_label_raw,
            owner_verified=owner_verified_merchant,
        )

        return ReceiptRecord(
            receipt_id=f"rcpt-{uuid.uuid4().hex[:12]}",
            proof_sha256=redaction.raw_sha256,
            redacted_text=redaction.redacted_text,
            redaction_summary=redaction.redaction_counts,
            merchant=merchant,
            extracted_brand=extracted_brand.strip(),
            extracted_product_name=extracted_product_name.strip(),
            extracted_variant=extracted_variant.strip(),
            extracted_concentration=self.normalize_concentration(extracted_concentration),
            extracted_size_ml=extracted_size_ml,
            subtotal_price=subtotal_price,
            discount_amount=discount_amount,
            net_paid=computed_net,
            currency=currency,
            order_ref_hash=order_ref_hash,
            purchase_date=purchase_date,
            is_refunded=is_refunded,
            is_pr_or_free_sample=is_pr_or_free,
            is_gwp_sample_only=is_gwp_sample,
            has_discount_code=has_discount,
            discount_code_label=discount_label,
            has_affiliate_tracking=has_affiliate,
            purchaser_email_matched_owner=redaction.purchaser_email_matched_owner,
            source_type=source_type,
        )

    @staticmethod
    def _token_similarity(a: str, b: str) -> float:
        """Compute token overlap similarity in [0.0, 1.0]."""
        tokens_a = {t for t in re.split(r"\W+", a.lower()) if t}
        tokens_b = {t for t in re.split(r"\W+", b.lower()) if t}
        if not tokens_a or not tokens_b:
            return 0.0
        if tokens_a == tokens_b or a.strip().lower() in b.strip().lower() or b.strip().lower() in a.strip().lower():
            return 1.0
        intersection = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        return intersection / union if union else 0.0

    def match(
        self,
        item: PerfumeItem,
        receipt: Optional[ReceiptRecord],
        seen_order_ref_hashes: Optional[Set[str]] = None,
        claimed_self_purchased: bool = True,
    ) -> MatchResult:
        """
        Evaluate a `ReceiptRecord` (or `None` when proof is missing) against a `PerfumeItem`.
        """
        if receipt is None:
            return MatchResult(
                sku=item.sku,
                receipt_id=None,
                proof_sha256=None,
                confidence_score=0.0,
                status=VaultConfidenceStatus.UNVERIFIED,
                matched_fields=[],
                discrepancies=["NO_PROOF_UPLOADED: No receipt or invoice attached to this item."],
                warnings=["Hold 'Verified Self-Purchase' public badge until a receipt is uploaded."],
                is_duplicate_order=False,
                eligible_for_verified_self_purchase_copy=False,
            )

        matched_fields: List[str] = []
        discrepancies: List[str] = []
        warnings: List[str] = list(receipt.merchant.warnings)
        score = 0.0
        has_conflict = False
        is_duplicate = False

        # 1. Duplicate order reference check
        if receipt.order_ref_hash and seen_order_ref_hashes is not None:
            if receipt.order_ref_hash in seen_order_ref_hashes:
                is_duplicate = True
                has_conflict = True
                discrepancies.append(
                    "DUPLICATE_ORDER_REF: This order reference hash is already bound to another vault claim."
                )

        # 2. Refund / cancellation / chargeback check
        if receipt.is_refunded or receipt.net_paid < 0:
            has_conflict = True
            discrepancies.append(
                "REFUNDED_OR_CANCELLED_ORDER: Receipt shows refund, cancellation, or reversal."
            )

        # 3. PR / Free / £0 check when claiming self-purchased
        if not receipt.redacted_text.strip() and not receipt.extracted_product_name:
            discrepancies.append(
                "EMPTY_OR_UNREADABLE_OCR: Receipt text and product fields are blank or unreadable."
            )
        elif receipt.is_pr_or_free_sample or (
            receipt.net_paid == 0.0
            and not receipt.has_discount_code
            and bool(re.search(r"£\s*0\.00|\b0\.00\b|\bfree\b|\bcomplimentary\b", receipt.redacted_text, re.IGNORECASE))
        ):
            if claimed_self_purchased:
                has_conflict = True
                discrepancies.append(
                    "FREE_OR_PR_RECEIPT_CONFLICT: Receipt shows £0.00 / complimentary PR item, "
                    "which contradicts a SELF_PURCHASED claim."
                )
            else:
                warnings.append("PR_OR_COMPLIMENTARY_ITEM: Zero-cost PR/complimentary receipt recorded.")

        # 4. Free 2ml GWP sample vial vs full bottle claim
        if receipt.is_gwp_sample_only and item.size_ml >= 10:
            has_conflict = True
            discrepancies.append(
                f"SAMPLE_VIAL_MISMATCH: Receipt is for a complimentary sample vial, not the {item.size_ml}ml bottle."
            )

        # 5. Purchaser email mismatch check
        if receipt.purchaser_email_matched_owner is False:
            has_conflict = True
            discrepancies.append(
                "MISMATCHED_PURCHASER_EMAIL: Receipt purchaser email does not match any verified owner email address."
            )

        # 6. Brand similarity (+0.25)
        brand_sim = self._token_similarity(item.brand, receipt.extracted_brand)
        if brand_sim >= 0.8:
            score += 0.25
            matched_fields.append("brand")
        elif brand_sim >= 0.4:
            score += 0.12
            warnings.append(
                f"PARTIAL_BRAND_MATCH: Item brand '{item.brand}' vs receipt '{receipt.extracted_brand}'."
            )
        else:
            discrepancies.append(
                f"BRAND_MISMATCH: Item brand '{item.brand}' does not match receipt '{receipt.extracted_brand}'."
            )

        # 7. Product & Variant similarity (+0.35)
        item_full_name = f"{item.product_name} {item.variant}".strip()
        rcpt_full_name = f"{receipt.extracted_product_name} {receipt.extracted_variant}".strip()
        prod_sim = self._token_similarity(item_full_name, rcpt_full_name)
        if prod_sim >= 0.75:
            score += 0.35
            matched_fields.append("product_name")
        elif prod_sim >= 0.4:
            score += 0.18
            warnings.append(
                f"PARTIAL_PRODUCT_MATCH: '{item_full_name}' vs receipt '{rcpt_full_name}'."
            )
        else:
            discrepancies.append(
                f"PRODUCT_MISMATCH: Item '{item_full_name}' does not match receipt '{rcpt_full_name}'."
            )

        # 8. Concentration check (+0.15)
        item_conc = self.normalize_concentration(item.concentration)
        rcpt_conc = self.normalize_concentration(receipt.extracted_concentration)
        if item_conc and rcpt_conc and item_conc == rcpt_conc:
            score += 0.15
            matched_fields.append("concentration")
        else:
            discrepancies.append(
                f"CONCENTRATION_MISMATCH: Expected '{item_conc}', receipt shows '{rcpt_conc}'."
            )

        # 9. Bottle Size ml check (+0.15 or -0.25 penalty on mismatch)
        if receipt.extracted_size_ml is not None:
            if receipt.extracted_size_ml == item.size_ml:
                score += 0.15
                matched_fields.append("size_ml")
            else:
                score = max(0.0, score - 0.20)
                discrepancies.append(
                    f"SIZE_MISMATCH: Item is {item.size_ml}ml, but receipt is for {receipt.extracted_size_ml}ml."
                )
        else:
            warnings.append("MISSING_SIZE_ML: Bottle volume (ml) was not legible on the receipt.")

        # 10. Positive net price paid (+0.10)
        if receipt.net_paid > 0.0 and not receipt.is_refunded and not receipt.is_pr_or_free_sample:
            score += 0.10
            matched_fields.append("positive_net_paid")
        elif receipt.net_paid == 0.0 and receipt.has_discount_code and receipt.subtotal_price > 0:
            # 100% voucher / gift card / promo code
            warnings.append(
                "ZERO_NET_PAID_WITH_VOUCHER: Net paid is £0.00 after discount/voucher; verify whether voucher was a brand gift."
            )

        # 11. Discount & affiliate flags on receipt
        if receipt.has_discount_code:
            warnings.append(
                f"DISCOUNT_APPLIED_ON_RECEIPT: Discount/promo ({receipt.discount_code_label}) recorded. "
                "If this is a creator-specific code or brand-supplied press discount, commercial disclosure may apply."
            )
        if receipt.has_affiliate_tracking:
            warnings.append(
                "AFFILIATE_METADATA_ON_RECEIPT: Receipt contains affiliate/referral tracking metadata. "
                "Ensure commercial relationship axis includes AFFILIATE_LINK if shared with viewers."
            )

        # 12. Merchant verification check (Experian vs Empyrean & unknown retailers)
        if receipt.merchant.requires_owner_confirmation:
            score = min(score, 0.75)  # Cap below 0.85 threshold until owner confirms merchant
            discrepancies.append(
                f"UNCONFIRMED_MERCHANT: Raw merchant '{receipt.merchant.merchant_label_raw}' "
                "requires explicit owner confirmation before Verified Self-Purchase status is granted."
            )

        score = round(min(1.0, max(0.0, score)), 2)

        if has_conflict:
            status = VaultConfidenceStatus.CONFLICTED
        elif (
            score >= 0.85
            and not discrepancies
            and receipt.net_paid > 0.0
            and not receipt.merchant.requires_owner_confirmation
        ):
            status = VaultConfidenceStatus.VERIFIED_SELF_PURCHASE
        else:
            status = VaultConfidenceStatus.UNVERIFIED

        return MatchResult(
            sku=item.sku,
            receipt_id=receipt.receipt_id,
            proof_sha256=receipt.proof_sha256,
            confidence_score=score,
            status=status,
            matched_fields=matched_fields,
            discrepancies=discrepancies,
            warnings=warnings,
            is_duplicate_order=is_duplicate,
            eligible_for_verified_self_purchase_copy=(
                status == VaultConfidenceStatus.VERIFIED_SELF_PURCHASE
            ),
        )
