"""Private, authenticated storage for the purchase vault's redacted records."""

from __future__ import annotations

import os
from contextlib import closing
from pathlib import Path
import secrets
import sqlite3
import stat
from tempfile import NamedTemporaryFile

from apps.backend.platform_ops.security import EnvelopeEncryptor


def _local_key(db_path: Path, existing_vault: bool) -> str:
    key_path = db_path.with_name(db_path.name + ".vault-key")
    if not key_path.exists() and not existing_vault:
        # Publish a complete file with exclusive creation. Parallel starts can
        # use the same winning key without reading partial contents.
        with NamedTemporaryFile(mode="w", encoding="ascii", dir=db_path.parent, delete=False) as out:
            temporary = Path(out.name)
            out.write(secrets.token_urlsafe(32))
        try:
            os.link(temporary, key_path)
        except FileExistsError:
            pass
        finally:
            temporary.unlink()
    if not key_path.is_file() or key_path.is_symlink():
        raise ValueError("The local vault key is missing or invalid.")
    if os.name == "posix" and stat.S_IMODE(key_path.stat().st_mode) & 0o077:
        raise ValueError("The local vault key must be private to the server owner.")
    return key_path.read_text(encoding="ascii").strip()


class VaultStorage:
    """Store one authenticated state snapshot in the owner's application database."""

    _CONTEXT = "araim:verified-purchases-vault:v1"

    def __init__(
        self, db_path: str | Path, encryptor: EnvelopeEncryptor | None = None
    ) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS purchase_vault_state (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    envelope TEXT NOT NULL
                )
            """)
            existing_vault = db.execute("SELECT 1 FROM purchase_vault_state").fetchone() is not None
        if encryptor is None:
            key = _local_key(self.path, existing_vault)
            if len(key) < 32:
                raise ValueError("The local vault key is invalid.")
            encryptor = EnvelopeEncryptor(master_key=key)
        self.encryptor = encryptor

    def load(self) -> dict | None:
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute("SELECT envelope FROM purchase_vault_state WHERE id=1").fetchone()
        return self.encryptor.decrypt_json(row[0], self._CONTEXT) if row else None

    def save(self, state: dict) -> None:
        envelope = self.encryptor.encrypt_json(state, self._CONTEXT)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("""
                INSERT INTO purchase_vault_state (id, envelope) VALUES (1, ?)
                ON CONFLICT (id) DO UPDATE SET envelope=excluded.envelope
            """, (envelope,))
