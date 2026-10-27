"""
PII, Payment Card, Address, and Barcode Redactor for Purchase Receipts.

Implements FR-019, FR-046, NFR-05, NFR-06:
Automatically strips and masks payment card numbers (PAN/Luhn/last-4),
bank account/IBAN/sort codes, home/billing street addresses, UK postcodes,
phone numbers, email addresses, invoice/order barcodes, and QR payloads
before storage, LLM inspection, or appeal packet export.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class RedactionResult:
    """Result of running deterministic PII and payment redaction on receipt text."""

    redacted_text: str
    redaction_counts: Dict[str, int] = field(default_factory=dict)
    extracted_emails_hashes: List[str] = field(default_factory=list)
    purchaser_email_matched_owner: Optional[bool] = None
    raw_sha256: str = ""

    @property
    def total_redactions(self) -> int:
        return sum(self.redaction_counts.values())


class ReceiptRedactor:
    """Deterministic zero-trust PII scrubber for receipts, invoices, and screenshots."""

    # Explicit card last-4 patterns (e.g., "Visa ending in 4421", "Card **** 8892", "Amex •••• 1005")
    _CARD_LAST4_PATTERN = re.compile(
        r"\b(?:"
        r"(?:visa|mastercard|amex|american\s+express|maestro|debit|credit|card|apple\s+pay|google\s+pay|klarnas?)"
        r"[\s:,-]*(?:ending\s+in|ending|last\s+4(?:\s+digits)?|[*•xX#]{2,12})[\s:,-]*\d{3,4}"
        r"|"
        r"(?:[*•]{4}[\s-]*){1,3}\d{4}"
        r")\b",
        re.IGNORECASE,
    )

    # Candidate 13-19 digit PAN sequences (including spaces or hyphens)
    _PAN_CANDIDATE_PATTERN = re.compile(
        r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"
    )

    # IBAN (e.g., GB29 NWBK 6016 1331 9268 19)
    _IBAN_PATTERN = re.compile(
        r"\b[A-Z]{2}\d{2}(?:[\s-]?[A-Z0-9]{4}){3,7}(?:[\s-]?[A-Z0-9]{1,4})?\b"
    )

    # UK Sort Code (e.g., 12-34-56 or Sort Code: 12 34 56)
    _SORT_CODE_PATTERN = re.compile(
        r"\b(?:sort\s*code[\s:,-]*)?\d{2}-\d{2}-\d{2}\b|\bsort\s*code[\s:,-]*\d{2}\s\d{2}\s\d{2}\b",
        re.IGNORECASE,
    )

    # Labeled Bank Account Number (8 digits in UK)
    _BANK_ACCT_PATTERN = re.compile(
        r"\b(?:account\s*(?:no|number|#)?[\s:,-]*)\d{8}\b",
        re.IGNORECASE,
    )

    # Email addresses
    _EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    )

    # UK & International Phone Numbers
    _PHONE_PATTERN = re.compile(
        r"(?:(?:\+44\s?\(0\)\s?|\+44\s?|0044\s?)(?:7\d{3}|\d{2,4})[\s-]?\d{3}[\s-]?\d{3,4})"
        r"|(?:\b0(?:7\d{3}|1\d{2,3}|2\d|3\d{2})[\s-]?\d{3}[\s-]?\d{3,4}\b)"
        r"|(?:(?:\b(?:tel|telephone|phone|mobile|contact)[\s:,-]+)\+?\d[\d\s()-]{7,16}\d)"
    , re.IGNORECASE)

    # UK Postcodes (standard formats like SW1X 7XL, EC1A 1BB, M1 1AE, W1A 0AX)
    _UK_POSTCODE_PATTERN = re.compile(
        r"\b(?:GIR\s?0AA|(?:(?:[A-PR-UWYZ][0-9][0-9]?|[A-PR-UWYZ][A-HK-Y][0-9][0-9]?|[A-PR-UWYZ][0-9][A-HJKSTUW]|[A-PR-UWYZ][A-HK-Y][0-9][ABEHMNPRV-Y])\s?[0-9][ABD-HJLNP-UW-Z]{2}))\b",
        re.IGNORECASE,
    )

    # Labeled Address lines or street address lines
    _LABELED_ADDRESS_PATTERN = re.compile(
        r"(?:(?:billing|shipping|delivery|home|customer|recipient|ship\s+to|deliver\s+to|bill\s+to)\s*address[\s:,-]+[^\n\r]+)"
        r"|(?:(?:ship\s+to|deliver\s+to|bill\s+to)[\s:,-]+\d+[^\n\r]+)",
        re.IGNORECASE,
    )

    _STREET_ADDRESS_PATTERN = re.compile(
        r"\b(?:(?:Flat|Apt|Apartment|Unit|Suite)\s+[0-9A-Za-z]+[,\s]+)?\d{1,4}[A-Za-z]?\s+[A-Z][A-Za-z0-9\s.'-]{2,35}\s+"
        r"(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Drive|Dr|Close|Court|Ct|Way|Place|Pl|Gardens|Gdns|Square|Sq|Terrace|Crescent|Mews|Grove|Boulevard|Blvd)\b",
        re.IGNORECASE,
    )

    # Barcodes / QR Payloads / Explicit Invoice Serials
    _QR_BARCODE_PATTERN = re.compile(
        r"(?:(?:QR(?:_CODE|_PAYLOAD|\s+Code)?|BARCODE|EAN13|UPC|TRACKING_BARCODE)[\s:=-]*[A-Za-z0-9+/=:_.-]{6,})"
        r"|(?:\|\|[\|\s]{4,}\|\|)"
        r"|(?:https?://[^\s]*(?:qr|invoice-token|verify-receipt|track)[^\s]*)",
        re.IGNORECASE,
    )

    _INVOICE_REF_PATTERN = re.compile(
        r"\b(?:invoice\s*(?:id|no|number|#)|order\s*(?:id|no|number|ref|#)|transaction\s*(?:id|ref|#)|receipt\s*(?:id|no|#))[\s:=-]*([A-Z0-9-]{5,30})\b",
        re.IGNORECASE,
    )

    @staticmethod
    def is_luhn_valid(digits: str) -> bool:
        """Check whether a numeric string satisfies the Luhn checksum algorithm."""
        if not digits.isdigit() or not (13 <= len(digits) <= 19):
            return False
        total = 0
        reverse_digits = digits[::-1]
        for idx, ch in enumerate(reverse_digits):
            n = int(ch)
            if idx % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        return total % 10 == 0

    @staticmethod
    def hash_identifier(value: str) -> str:
        """Return a deterministic SHA-256 hex digest of a normalized identifier."""
        cleaned = value.strip().lower()
        return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()

    def redact(
        self,
        raw_text: str,
        owner_emails: Optional[List[str]] = None,
    ) -> RedactionResult:
        """
        Scrub all PII, card numbers, addresses, emails, phones, and barcodes from receipt text.
        """
        if not raw_text:
            return RedactionResult(
                redacted_text="",
                redaction_counts={},
                extracted_emails_hashes=[],
                purchaser_email_matched_owner=None,
                raw_sha256=hashlib.sha256(b"").hexdigest(),
            )

        raw_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        counts: Dict[str, int] = {
            "card_pan": 0,
            "card_last4": 0,
            "iban": 0,
            "sort_code": 0,
            "bank_account": 0,
            "email": 0,
            "phone": 0,
            "address": 0,
            "postcode": 0,
            "barcode_qr": 0,
            "order_invoice_ref": 0,
        }

        text = raw_text

        # 1. Extract and check emails before redacting them
        found_emails = self._EMAIL_PATTERN.findall(text)
        email_hashes = [self.hash_identifier(e) for e in found_emails]
        purchaser_matched: Optional[bool] = None
        if found_emails and owner_emails:
            normalized_owners = {e.strip().lower() for e in owner_emails if e}
            # Ignore known merchant customer service emails
            customer_emails = [
                e.strip().lower()
                for e in found_emails
                if not any(
                    prefix in e.lower()
                    for prefix in ("support@", "orders@", "info@", "help@", "concierge@", "noreply@", "no-reply@", "sales@")
                )
            ]
            if customer_emails:
                purchaser_matched = any(ce in normalized_owners for ce in customer_emails)

        def _replace_email(_match: re.Match) -> str:
            counts["email"] += 1
            return "[REDACTED_EMAIL]"

        text = self._EMAIL_PATTERN.sub(_replace_email, text)

        # 2. QR codes and barcodes (before PAN so numeric barcodes are caught cleanly)
        def _replace_barcode(_match: re.Match) -> str:
            counts["barcode_qr"] += 1
            return "[REDACTED_BARCODE]"

        text = self._QR_BARCODE_PATTERN.sub(_replace_barcode, text)

        # 3. IBANs
        def _replace_iban(_match: re.Match) -> str:
            counts["iban"] += 1
            return "[REDACTED_IBAN]"

        text = self._IBAN_PATTERN.sub(_replace_iban, text)

        # 4. UK Sort Codes & Bank Accounts
        def _replace_sort_code(_match: re.Match) -> str:
            counts["sort_code"] += 1
            return "[REDACTED_SORT_CODE]"

        text = self._SORT_CODE_PATTERN.sub(_replace_sort_code, text)

        def _replace_bank_acct(_match: re.Match) -> str:
            counts["bank_account"] += 1
            return "[REDACTED_BANK_ACCOUNT]"

        text = self._BANK_ACCT_PATTERN.sub(_replace_bank_acct, text)

        # 5. Full Payment Card Numbers (PANs - Luhn valid or 13-19 digit card sequences)
        def _replace_pan(match: re.Match) -> str:
            raw_seq = match.group(0)
            digits_only = re.sub(r"\D", "", raw_seq)
            if 13 <= len(digits_only) <= 19 and (
                self.is_luhn_valid(digits_only)
                or len(digits_only) in (15, 16)
            ):
                counts["card_pan"] += 1
                return "[REDACTED_CARD_PAN]"
            return raw_seq

        text = self._PAN_CANDIDATE_PATTERN.sub(_replace_pan, text)

        # 6. Card Last-4 notations
        def _replace_last4(_match: re.Match) -> str:
            counts["card_last4"] += 1
            return "[REDACTED_CARD_LAST4]"

        text = self._CARD_LAST4_PATTERN.sub(_replace_last4, text)

        # 7. Phone numbers
        def _replace_phone(_match: re.Match) -> str:
            counts["phone"] += 1
            return "[REDACTED_PHONE]"

        text = self._PHONE_PATTERN.sub(_replace_phone, text)

        # 8. Labeled & street addresses
        def _replace_address(_match: re.Match) -> str:
            counts["address"] += 1
            return "[REDACTED_ADDRESS]"

        text = self._LABELED_ADDRESS_PATTERN.sub(_replace_address, text)
        text = self._STREET_ADDRESS_PATTERN.sub(_replace_address, text)

        # 9. UK Postcodes
        def _replace_postcode(_match: re.Match) -> str:
            counts["postcode"] += 1
            return "[REDACTED_POSTCODE]"

        text = self._UK_POSTCODE_PATTERN.sub(_replace_postcode, text)

        # 10. Invoice / Order references
        def _replace_invoice_ref(_match: re.Match) -> str:
            counts["order_invoice_ref"] += 1
            return "Order Ref: [REDACTED_ORDER_REF]"

        text = self._INVOICE_REF_PATTERN.sub(_replace_invoice_ref, text)

        # Filter out zero counts for cleanliness
        non_zero_counts = {k: v for k, v in counts.items() if v > 0}

        return RedactionResult(
            redacted_text=text,
            redaction_counts=non_zero_counts,
            extracted_emails_hashes=email_hashes,
            purchaser_email_matched_owner=purchaser_matched,
            raw_sha256=raw_sha256,
        )

    def contains_unredacted_pii(self, text: str) -> bool:
        """Verify that a string contains no residual raw PII, card data, or postcodes."""
        probe = self.redact(text)
        return probe.total_redactions > 0
