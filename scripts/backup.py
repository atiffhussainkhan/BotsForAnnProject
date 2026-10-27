#!/usr/bin/env python3
"""
Ann Reveals AI Manager (`ARAIM` v4.0) — Automated Encrypted Backup CLI (`scripts/backup.py`).

Usage:
  python3 scripts/backup.py --source-dir ./data --output-file ./backups/latest.araim.bak
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.platform_ops.backup_manager import BackupManager
from apps.backend.platform_ops.security import EnvelopeEncryptor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create an authenticated encrypted point-in-time backup with SHA-256 manifest."
    )
    parser.add_argument(
        "--source-dir",
        required=True,
        help="Path to the data directory to back up.",
    )
    parser.add_argument(
        "--output-file",
        default=None,
        help="Output .araim.bak file path (optional if --output-dir is supplied).",
    )
    parser.add_argument(
        "--output-dir",
        default="./backups",
        help="Directory to write backup file if --output-file is omitted.",
    )
    parser.add_argument(
        "--master-key",
        default=None,
        help="Optional override master key (defaults to ARAIM_MASTER_KEY env var).",
    )
    args = parser.parse_args(argv)

    encryptor = EnvelopeEncryptor(master_key=args.master_key) if args.master_key else EnvelopeEncryptor()
    manager = BackupManager(encryptor=encryptor)

    out_file = args.output_file
    if not out_file:
        out_file = str(Path(args.output_dir) / "latest.araim.bak")

    metadata = manager.create_backup(source_dir=args.source_dir, output_backup_file=out_file)
    print(
        json.dumps(
            {
                "status": "BACKUP_CREATED",
                "backup_id": metadata.backup_id,
                "backup_file_path": metadata.backup_file_path,
                "file_count": metadata.file_count,
                "total_plaintext_bytes": metadata.total_plaintext_bytes,
                "manifest_sha256": metadata.manifest_sha256,
                "key_id": metadata.key_id,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
