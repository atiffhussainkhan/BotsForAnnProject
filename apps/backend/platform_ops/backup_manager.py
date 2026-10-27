"""
Agent Echo (Agent 5) — Encrypted Snapshot Backup & Point-in-Time Restore Manager (`backup_manager.py`).

Satisfies:
- FR-044: Automated encrypted backups, verified restore script, secret rotation.
- NFR-08: Tested encrypted backup/restore scripts with SHA-256 manifest verification and corruption detection.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .security import EnvelopeEncryptor, TamperDetectedError


class BackupCorruptionError(Exception):
    """Raised when a backup snapshot fails HMAC authentication or SHA-256 file manifest verification."""


@dataclass
class BackupMetadata:
    backup_id: str
    created_at: float
    source_dir: str
    backup_file_path: str
    file_count: int
    total_plaintext_bytes: int
    manifest_sha256: str
    key_id: str


class BackupManager:
    """
    Creates authenticated encrypted point-in-time backups of a directory or state dictionary,
    verifies per-file SHA-256 manifests, and performs atomic restores with tamper detection.
    """

    ASSOCIATED_DATA_PREFIX = "araim-backup-snapshot-v4"

    def __init__(self, encryptor: Optional[EnvelopeEncryptor] = None) -> None:
        self.encryptor = encryptor or EnvelopeEncryptor()

    def create_backup(
        self,
        source_dir: str | Path,
        output_backup_file: str | Path,
        backup_id: Optional[str] = None,
    ) -> BackupMetadata:
        """
        Walk `source_dir`, compute SHA-256 checksums for every file, assemble a manifest,
        and encrypt the entire archive using `EnvelopeEncryptor` (`ARAIM-ENC-V1`).
        """
        src = Path(source_dir).resolve()
        if not src.exists() or not src.is_dir():
            raise FileNotFoundError(f"Backup source directory does not exist: {src}")

        files_payload: Dict[str, str] = {}
        manifest_hashes: Dict[str, str] = {}
        total_bytes = 0

        for file_path in sorted(src.rglob("*")):
            if file_path.is_file():
                rel_path = file_path.relative_to(src).as_posix()
                raw_bytes = file_path.read_bytes()
                total_bytes += len(raw_bytes)
                file_sha256 = hashlib.sha256(raw_bytes).hexdigest()
                files_payload[rel_path] = base64.b64encode(raw_bytes).decode("ascii")
                manifest_hashes[rel_path] = file_sha256

        created_at = time.time()
        b_id = backup_id or f"araim-snap-{int(created_at)}"

        canonical_manifest = json.dumps(
            manifest_hashes, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        manifest_sha256 = hashlib.sha256(canonical_manifest).hexdigest()

        snapshot_bundle = {
            "schema_version": "4.0.0",
            "backup_id": b_id,
            "created_at": created_at,
            "file_count": len(files_payload),
            "total_plaintext_bytes": total_bytes,
            "manifest_sha256": manifest_sha256,
            "manifest": manifest_hashes,
            "files": files_payload,
        }

        aad = f"{self.ASSOCIATED_DATA_PREFIX}:{b_id}"
        encrypted_token = self.encryptor.encrypt_json(snapshot_bundle, associated_data=aad)

        wrapper = {
            "format": "ARAIM-BACKUP-V4",
            "backup_id": b_id,
            "created_at": created_at,
            "key_id": self.encryptor.active_key_id,
            "manifest_sha256": manifest_sha256,
            "file_count": len(files_payload),
            "envelope": encrypted_token,
        }

        out_path = Path(output_backup_file).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(wrapper, indent=2, sort_keys=True), encoding="utf-8"
        )

        return BackupMetadata(
            backup_id=b_id,
            created_at=created_at,
            source_dir=str(src),
            backup_file_path=str(out_path),
            file_count=len(files_payload),
            total_plaintext_bytes=total_bytes,
            manifest_sha256=manifest_sha256,
            key_id=self.encryptor.active_key_id,
        )

    def verify_and_restore(
        self,
        backup_file: str | Path,
        restore_target_dir: str | Path,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Verify outer HMAC authentication tag, decrypt snapshot, validate every file's SHA-256
        hash against the signed manifest, and write restored files to `restore_target_dir`.
        Raises `BackupCorruptionError` on any tampering or bit rot.
        """
        bak_path = Path(backup_file).resolve()
        if not bak_path.exists():
            raise FileNotFoundError(f"Backup file not found: {bak_path}")

        try:
            wrapper = json.loads(bak_path.read_text(encoding="utf-8"))
            if wrapper.get("format") != "ARAIM-BACKUP-V4":
                raise BackupCorruptionError("Invalid backup file format header.")
            b_id = str(wrapper["backup_id"])
            expected_manifest_sha = str(wrapper["manifest_sha256"])
            envelope_token = str(wrapper["envelope"])
        except BackupCorruptionError:
            raise
        except Exception as exc:
            raise BackupCorruptionError("Malformed backup wrapper JSON.") from exc

        aad = f"{self.ASSOCIATED_DATA_PREFIX}:{b_id}"
        try:
            bundle = self.encryptor.decrypt_json(envelope_token, expected_associated_data=aad)
        except TamperDetectedError as exc:
            raise BackupCorruptionError(f"Cryptographic tamper detected in backup: {exc}") from exc

        manifest_hashes: Dict[str, str] = bundle.get("manifest", {})
        files_payload: Dict[str, str] = bundle.get("files", {})

        canonical_manifest = json.dumps(
            manifest_hashes, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        computed_manifest_sha = hashlib.sha256(canonical_manifest).hexdigest()

        if (
            computed_manifest_sha != expected_manifest_sha
            or computed_manifest_sha != bundle.get("manifest_sha256")
        ):
            raise BackupCorruptionError("Backup manifest SHA-256 verification failed.")

        verified_files: Dict[str, bytes] = {}
        for rel_path, expected_file_sha in manifest_hashes.items():
            if rel_path not in files_payload:
                raise BackupCorruptionError(f"Missing file payload in backup: {rel_path}")
            raw_bytes = base64.b64decode(files_payload[rel_path].encode("ascii"))
            actual_sha = hashlib.sha256(raw_bytes).hexdigest()
            if actual_sha != expected_file_sha:
                raise BackupCorruptionError(
                    f"SHA-256 mismatch for file '{rel_path}': expected {expected_file_sha}, got {actual_sha}"
                )
            verified_files[rel_path] = raw_bytes

        target = Path(restore_target_dir).resolve()
        restored_paths: List[str] = []
        if not dry_run:
            target.mkdir(parents=True, exist_ok=True)
            for rel_path, raw_bytes in verified_files.items():
                dest = (target / rel_path).resolve()
                # Prevent path traversal attacks
                if not str(dest).startswith(str(target)):
                    raise BackupCorruptionError(f"Unsafe relative path in backup: {rel_path}")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(raw_bytes)
                restored_paths.append(rel_path)

        return {
            "verified": True,
            "backup_id": b_id,
            "file_count": len(verified_files),
            "manifest_sha256": computed_manifest_sha,
            "restored_files": sorted(verified_files.keys()),
            "restore_target_dir": str(target),
            "dry_run": dry_run,
        }
