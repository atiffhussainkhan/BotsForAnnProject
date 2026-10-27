#!/usr/bin/env python3
"""
Ann Reveals AI Manager (`ARAIM` v4.0) — Verified Point-in-Time Restore CLI (`scripts/restore.py`).

Usage:
  python3 scripts/restore.py --backup-file ./backups/latest.araim.bak --target-dir ./data_restored
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.platform_ops.backup_manager import BackupCorruptionError, BackupManager
from apps.backend.platform_ops.security import EnvelopeEncryptor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify HMAC + SHA-256 manifest and restore an encrypted ARAIM backup."
    )
    parser.add_argument(
        "--backup-file",
        required=True,
        help="Path to the encrypted .araim.bak file.",
    )
    parser.add_argument(
        "--target-dir",
        required=True,
        help="Destination directory to restore verified files into.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Verify cryptographic integrity and manifest hashes without writing files.",
    )
    parser.add_argument(
        "--master-key",
        default=None,
        help="Optional override master key (defaults to ARAIM_MASTER_KEY env var).",
    )
    args = parser.parse_args(argv)

    encryptor = EnvelopeEncryptor(master_key=args.master_key) if args.master_key else EnvelopeEncryptor()
    manager = BackupManager(encryptor=encryptor)

    try:
        result = manager.verify_and_restore(
            backup_file=args.backup_file,
            restore_target_dir=args.target_dir,
            dry_run=args.dry_run,
        )
    except (BackupCorruptionError, FileNotFoundError) as exc:
        print(json.dumps({"status": "RESTORE_FAILED", "error": str(exc)}), file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "status": "RESTORE_VERIFIED_AND_COMPLETED",
                **result,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
