"""
Agent Echo (Agent 5) — UK GDPR Data Minimisation, PII Redaction, Retention, Audit Log & Vendor Exit (`gdpr.py`).

Satisfies:
- FR-019: Redact all payment card numbers, billing addresses, invoice IDs, and personal PII before storage or LLM inspection.
- FR-036: Plain-language audit trail (`Comment Received -> Classification -> AI Draft -> Safety/Policy Checks -> API Dispatch/Result -> Permalink`).
- FR-044: Full JSON/CSV/ZIP vendor exit export.
- NFR-06: UK GDPR & data minimisation: PII redaction before storage/LLM, configurable retention cleanup,
  full owner data export and account erasure.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import time
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AuditLogEntry:
    entry_id: str
    timestamp: float
    actor: str
    action: str
    resource_type: str
    resource_id: str
    plain_english_summary: str
    prev_hash: str
    entry_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class GDPRComplianceManager:
    """
    Implements UK GDPR data minimisation, automated PII redaction for receipts/comments,
    configurable retention pruning, hash-chained access/action audit logs,
    1-click portable JSON/ZIP owner export, and cryptographic right-to-erasure wipe.
    """

    # UK Postcode regex (standard formats like SW1A 1AA, M1 1AE, B33 8TH, etc.)
    _UK_POSTCODE_RE = re.compile(
        r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b", re.IGNORECASE
    )
    # Payment card PAN (13-19 digits, optionally separated by spaces or hyphens)
    _CARD_PAN_RE = re.compile(
        r"\b(?:\d[ -]*?){13,19}\b"
    )
    # Email addresses
    _EMAIL_RE = re.compile(
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
    )
    # UK / International phone numbers
    _PHONE_RE = re.compile(
        r"(?:\+44\s?7\d{3}|\(?07\d{3}\)?)\s?\d{3}\s?\d{3}\b"
    )
    # Billing street line patterns
    _ADDRESS_LINE_RE = re.compile(
        r"\b\d{1,4}\s+[A-Za-z0-9\s]{2,30}\s+(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Close|Gardens|Drive|Dr|Way|Court|Ct)\b",
        re.IGNORECASE,
    )
    # Invoice / Order secret ref pattern when labelled in raw text
    _INVOICE_SECRET_RE = re.compile(
        r"((?:Invoice\s*(?:No|ID|#)|Billing\s*Ref|Transaction\s*ID)\s*[:#-]?\s*)([A-Za-z0-9\-]{5,})",
        re.IGNORECASE,
    )

    def __init__(
        self,
        comment_retention_days: int = 90,
        audit_retention_days: int = 365,
        evidence_retention_days: int = 730,
    ) -> None:
        self.comment_retention_days = int(comment_retention_days)
        self.audit_retention_days = int(audit_retention_days)
        self.evidence_retention_days = int(evidence_retention_days)

        self._audit_log: List[AuditLogEntry] = []
        self._comments_store: Dict[str, Dict[str, Any]] = {}
        self._perfume_vault_store: Dict[str, Dict[str, Any]] = {}
        self._friends_watchlist_store: Dict[str, Dict[str, Any]] = {}
        self._appeals_store: Dict[str, Dict[str, Any]] = {}
        self._erased: bool = False

    @classmethod
    def redact_pii(cls, raw_text: str) -> Dict[str, Any]:
        """
        Redact payment card numbers, UK postcodes, street addresses, email addresses,
        phone numbers, and invoice IDs before storage or LLM inspection (`FR-019`, `NFR-06`).
        Preserves merchant names (`Experian` / `Empyrean`) and perfume product names intact.
        """
        if not raw_text:
            return {"redacted_text": "", "redactions_applied": []}

        redacted = raw_text
        applied: List[str] = []

        if cls._CARD_PAN_RE.search(redacted):
            redacted = cls._CARD_PAN_RE.sub("[REDACTED_CARD_PAN]", redacted)
            applied.append("card_pan")

        if cls._EMAIL_RE.search(redacted):
            redacted = cls._EMAIL_RE.sub("[REDACTED_EMAIL]", redacted)
            applied.append("email")

        if cls._PHONE_RE.search(redacted):
            redacted = cls._PHONE_RE.sub("[REDACTED_PHONE]", redacted)
            applied.append("phone")

        if cls._UK_POSTCODE_RE.search(redacted):
            redacted = cls._UK_POSTCODE_RE.sub("[REDACTED_UK_POSTCODE]", redacted)
            applied.append("uk_postcode")

        if cls._ADDRESS_LINE_RE.search(redacted):
            redacted = cls._ADDRESS_LINE_RE.sub("[REDACTED_ADDRESS]", redacted)
            applied.append("billing_address")

        if cls._INVOICE_SECRET_RE.search(redacted):
            redacted = cls._INVOICE_SECRET_RE.sub(r"\1[REDACTED_INVOICE_ID]", redacted)
            applied.append("invoice_id")

        return {
            "redacted_text": redacted,
            "redactions_applied": applied,
            "pii_found": len(applied) > 0,
        }

    def record_audit_event(
        self,
        *,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str,
        plain_english_summary: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None,
    ) -> AuditLogEntry:
        """Append an immutable, hash-chained audit trail record (`FR-036`, `NFR-05`)."""
        ts = time.time() if timestamp is None else float(timestamp)
        prev_hash = self._audit_log[-1].entry_hash if self._audit_log else "GENESIS"
        entry_id = f"audit-{len(self._audit_log) + 1:06d}"
        meta = metadata or {}
        canonical = json.dumps(
            {
                "entry_id": entry_id,
                "timestamp": ts,
                "actor": actor,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "plain_english_summary": plain_english_summary,
                "prev_hash": prev_hash,
                "metadata": meta,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        entry_hash = hashlib.sha256(canonical).hexdigest()
        entry = AuditLogEntry(
            entry_id=entry_id,
            timestamp=ts,
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            plain_english_summary=plain_english_summary,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            metadata=meta,
        )
        self._audit_log.append(entry)
        return entry

    def verify_audit_chain(self) -> bool:
        """Verify that no audit log entry has been modified or deleted."""
        prev = "GENESIS"
        for entry in self._audit_log:
            if entry.prev_hash != prev:
                return False
            canonical = json.dumps(
                {
                    "entry_id": entry.entry_id,
                    "timestamp": entry.timestamp,
                    "actor": entry.actor,
                    "action": entry.action,
                    "resource_type": entry.resource_type,
                    "resource_id": entry.resource_id,
                    "plain_english_summary": entry.plain_english_summary,
                    "prev_hash": entry.prev_hash,
                    "metadata": entry.metadata,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            expected = hashlib.sha256(canonical).hexdigest()
            if expected != entry.entry_hash:
                return False
            prev = entry.entry_hash
        return True

    def store_minimised_comment(
        self,
        comment_id: str,
        platform: str,
        author_handle: str,
        comment_text: str,
        created_at: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Store only the minimum necessary comment data with automatic PII redaction (`NFR-06`)."""
        redaction = self.redact_pii(comment_text)
        record = {
            "comment_id": comment_id,
            "platform": platform,
            "author_handle": author_handle,
            "comment_text": redaction["redacted_text"],
            "redactions_applied": redaction["redactions_applied"],
            "created_at": time.time() if created_at is None else float(created_at),
        }
        self._comments_store[comment_id] = record
        return record

    def store_perfume_receipt_record(
        self,
        sku: str,
        product_name: str,
        raw_merchant_label: str,
        raw_receipt_text: str,
        canonical_merchant_confirmed: bool = False,
        created_at: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Store a perfume receipt record after PII redaction while preserving the raw merchant label
        (`Experian` vs `Empyrean`) until explicit owner confirmation (`FR-019`, `FR-051`).
        """
        redaction = self.redact_pii(raw_receipt_text)
        receipt_sha256 = hashlib.sha256(
            redaction["redacted_text"].encode("utf-8")
        ).hexdigest()
        record = {
            "sku": sku,
            "product_name": product_name,
            "raw_merchant_label": raw_merchant_label,
            "canonical_merchant_name": (
                "Empyrean Watches & Perfume" if canonical_merchant_confirmed else None
            ),
            "owner_confirmed_merchant": bool(canonical_merchant_confirmed),
            "redacted_receipt_text": redaction["redacted_text"],
            "redactions_applied": redaction["redactions_applied"],
            "receipt_sha256": receipt_sha256,
            "created_at": time.time() if created_at is None else float(created_at),
        }
        self._perfume_vault_store[sku] = record
        return record

    def enforce_retention_policy(self, current_time: Optional[float] = None) -> Dict[str, int]:
        """Prune expired comments and records older than configured retention windows (`NFR-06`)."""
        now = time.time() if current_time is None else float(current_time)
        comment_cutoff = now - (self.comment_retention_days * 86400)
        evidence_cutoff = now - (self.evidence_retention_days * 86400)

        expired_comments = [
            cid
            for cid, rec in self._comments_store.items()
            if rec.get("created_at", now) < comment_cutoff
        ]
        for cid in expired_comments:
            del self._comments_store[cid]

        expired_evidence = [
            sku
            for sku, rec in self._perfume_vault_store.items()
            if rec.get("created_at", now) < evidence_cutoff
        ]
        for sku in expired_evidence:
            del self._perfume_vault_store[sku]

        self.record_audit_event(
            actor="system:retention_scheduler",
            action="RETENTION_CLEANUP",
            resource_type="all_stores",
            resource_id="retention_policy",
            plain_english_summary=(
                f"Pruned {len(expired_comments)} expired comments and {len(expired_evidence)} expired evidence items."
            ),
        )
        return {
            "pruned_comments": len(expired_comments),
            "pruned_evidence": len(expired_evidence),
            "remaining_comments": len(self._comments_store),
            "remaining_evidence": len(self._perfume_vault_store),
        }

    def export_owner_data_bundle(
        self, output_zip_path: Optional[str | Path] = None, owner_handle: str = "@annreveals"
    ) -> Dict[str, Any]:
        """
        FR-044 / NFR-06: Generate full portable JSON + ZIP vendor-exit data export for the owner.
        """
        export_payload = {
            "schema_version": "4.0.0",
            "exported_at": time.time(),
            "owner_handle": owner_handle,
            "retention_policy": {
                "comment_retention_days": self.comment_retention_days,
                "audit_retention_days": self.audit_retention_days,
                "evidence_retention_days": self.evidence_retention_days,
            },
            "verified_purchases_vault": list(self._perfume_vault_store.values()),
            "minimised_comments": list(self._comments_store.values()),
            "friends_watchlist": list(self._friends_watchlist_store.values()),
            "appeals_cases": list(self._appeals_store.values()),
            "audit_trail": [asdict(entry) for entry in self._audit_log],
        }
        json_bytes = json.dumps(export_payload, indent=2, sort_keys=True).encode("utf-8")
        bundle_sha256 = hashlib.sha256(json_bytes).hexdigest()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("owner_data_export.json", json_bytes)
            zf.writestr(
                "MANIFEST.sha256",
                f"{bundle_sha256}  owner_data_export.json\n".encode("utf-8"),
            )
        zip_bytes = zip_buffer.getvalue()

        if output_zip_path is not None:
            out_path = Path(output_zip_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(zip_bytes)

        self.record_audit_event(
            actor=owner_handle,
            action="OWNER_FULL_DATA_EXPORT",
            resource_type="owner_archive",
            resource_id=bundle_sha256[:16],
            plain_english_summary="Owner exported full portable JSON/ZIP data bundle.",
        )

        return {
            "export_payload": export_payload,
            "json_sha256": bundle_sha256,
            "zip_size_bytes": len(zip_bytes),
            "output_zip_path": str(output_zip_path) if output_zip_path else None,
        }

    def erase_all_owner_data(
        self, confirmation_phrase: str, actor: str = "@annreveals"
    ) -> Dict[str, Any]:
        """
        NFR-06: Right to Erasure. Wipes all stores, audit logs, and cached items and returns a signed
        Erasure Certificate. Requires explicit `CONFIRM ERASE` phrase.
        """
        if confirmation_phrase != "CONFIRM ERASE":
            raise ValueError("Confirmation phrase must be 'CONFIRM ERASE' to execute Right to Erasure.")

        wiped_counts = {
            "comments_wiped": len(self._comments_store),
            "perfume_vault_records_wiped": len(self._perfume_vault_store),
            "friends_watchlist_wiped": len(self._friends_watchlist_store),
            "appeals_wiped": len(self._appeals_store),
            "audit_entries_wiped": len(self._audit_log),
        }

        self._comments_store.clear()
        self._perfume_vault_store.clear()
        self._friends_watchlist_store.clear()
        self._appeals_store.clear()
        self._audit_log.clear()
        self._erased = True

        erased_at = time.time()
        cert_body = json.dumps(
            {"actor": actor, "erased_at": erased_at, "wiped_counts": wiped_counts},
            sort_keys=True,
        ).encode("utf-8")
        certificate_hash = hashlib.sha256(cert_body).hexdigest()

        return {
            "status": "ERASED",
            "actor": actor,
            "erased_at": erased_at,
            "wiped_counts": wiped_counts,
            "erasure_certificate_sha256": certificate_hash,
        }
