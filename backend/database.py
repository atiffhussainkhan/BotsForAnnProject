"""
Persistent Database Layer for Ann Reveals AI Manager (v4.0).

Applies `migrations/001_initial_schema.sql` to SQLite (or Postgres via adapter)
and maintains durable state across all 19 core entities defined in Section O.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT_DIR / "data" / "ann_reveals_manager.db"
MIGRATION_FILE = ROOT_DIR / "migrations" / "001_initial_schema.sql"


class DatabaseManager:
    """Thread-safe SQLite persistence manager implementing the 19-table Section O schema."""

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self.db_path = Path(db_path or os.environ.get("ARAIM_DB_PATH", DEFAULT_DB_PATH))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_schema_and_seed()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema_and_seed(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                sql = MIGRATION_FILE.read_text(encoding="utf-8")
                conn.executescript(sql)
                now = datetime.now(timezone.utc).isoformat()

                # Seed Owner User
                conn.execute(
                    """
                    INSERT OR IGNORE INTO users (id, email, authentication_subject, locale, timezone, mfa_enabled, role, created_at)
                    VALUES (?, ?, ?, 'en-GB', 'Europe/London', 1, 'owner', ?)
                    """,
                    ("usr-ann-001", "ann@annreveals.co.uk", "auth0|annreveals", now),
                )

                # Seed Social Accounts (@annreveals on Instagram & TikTok)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO social_accounts (id, platform, provider_user_id, handle, account_type, connection_state, permission_reviewed_at)
                    VALUES
                        ('acc-ig-ann', 'instagram', '17841400000001', '@annreveals', 'CREATOR_PROFESSIONAL', 'Awaiting review', ?),
                        ('acc-tt-ann', 'tiktok', 'tt_biz_annreveals_01', '@annreveals', 'CREATOR_BUSINESS', 'Awaiting review', ?)
                    """,
                    (now, now),
                )

                # Seed Default System Settings
                conn.execute(
                    """
                    INSERT OR IGNORE INTO system_settings (
                        account_id, instagram_mode, tiktok_mode, emergency_stop,
                        max_daily_actions, quiet_hours, model_budget_gbp,
                        hard_monthly_ceiling_gbp, retention_days, brand_voice_notes, setup_wizard_step
                    ) VALUES (?, 'DRAFT', 'DRAFT', 0, 100, '23:00-07:00', 5.00, 30.00, 90, ?, 6)
                    """,
                    (
                        "usr-ann-001",
                        "Ann Reveals: Sincere UK English, warm feminine soft-luxury. Honest personal wear impressions, occasional delicate emoji (✨🤍), never pushy or salesy, never invent wear-time hours.",
                    ),
                )

                # Seed Policy Rules Register
                policy_rows = [
                    (
                        "pol-uk-asa-2026",
                        "both",
                        "UK",
                        "UK-ASA-INF-2026-10-23",
                        "https://www.asa.org.uk/resource/influencers-guide.html",
                        "2026-10-23",
                        now,
                        "apps.backend.compliance.disclosure_engine.DisclosureEngine",
                    ),
                    (
                        "pol-tt-comm-2026",
                        "tiktok",
                        "GLOBAL/UK",
                        "TT-COMM-2026-04",
                        "https://ads.tiktok.com/resources/help/article/about-the-content-disclosure-setting-for-creators",
                        "2026-04-01",
                        now,
                        "apps.backend.compliance.preflight.PreflightChecker",
                    ),
                    (
                        "pol-meta-bc-2026",
                        "instagram",
                        "GLOBAL/UK",
                        "META-BC-2026",
                        "https://www.facebook.com/help/instagram/616901995832907?locale=en_GB",
                        "2026-01-01",
                        now,
                        "apps.backend.compliance.preflight.PreflightChecker",
                    ),
                ]
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO policy_rules (id, platform, jurisdiction, rule_version, source_url, effective_date, reviewed_at, decision_logic_ref)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    policy_rows,
                )

                conn.commit()
            finally:
                conn.close()

    def log_audit_event(
        self,
        actor: str,
        action: str,
        target: str,
        result_summary: str,
        data_classification: str = "INTERNAL_REDACTED",
    ) -> str:
        event_id = f"aud-{uuid.uuid4().hex[:12]}"
        trace_id = f"trc-{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO audit_events (id, actor, action, target, trace_id, timestamp, data_classification, result_summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (event_id, actor, action, target, trace_id, now, data_classification, result_summary),
                )
                conn.commit()
            finally:
                conn.close()
        return event_id

    def save_comment(
        self,
        comment_id: str,
        platform: str,
        post_id: str,
        commenter_pseudonym: str,
        text_redacted: str,
        category: str,
        risk_tier: str,
        response_status: str,
        reply_candidate: Optional[str],
        audit_trail: List[str],
        parent_id: Optional[str] = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO comments (
                        id, platform, provider_comment_id, post_id, parent_id,
                        commenter_pseudonym, text_redacted, category, risk_tier,
                        response_status, reply_candidate, audit_trail_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"c-{platform}-{comment_id}",
                        platform,
                        comment_id,
                        post_id,
                        parent_id,
                        commenter_pseudonym,
                        text_redacted,
                        category,
                        risk_tier,
                        response_status,
                        reply_candidate,
                        json.dumps(audit_trail),
                        now,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def list_comments(self, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            try:
                if platform and platform.lower() != "all":
                    cur = conn.execute(
                        "SELECT * FROM comments WHERE platform = ? ORDER BY created_at DESC",
                        (platform.lower(),),
                    )
                else:
                    cur = conn.execute("SELECT * FROM comments ORDER BY created_at DESC")
                rows = []
                for r in cur.fetchall():
                    d = dict(r)
                    d["audit_trail"] = json.loads(d.get("audit_trail_json") or "[]")
                    rows.append(d)
                return rows
            finally:
                conn.close()

    def list_audit_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                )
                return [dict(r) for r in cur.fetchall()]
            finally:
                conn.close()

    def get_settings(self) -> Dict[str, Any]:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "SELECT * FROM system_settings WHERE account_id = 'usr-ann-001'"
                )
                row = cur.fetchone()
                return dict(row) if row else {}
            finally:
                conn.close()

    def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        allowed_cols = {
            "instagram_mode",
            "tiktok_mode",
            "emergency_stop",
            "max_daily_actions",
            "quiet_hours",
            "model_budget_gbp",
            "hard_monthly_ceiling_gbp",
            "retention_days",
            "brand_voice_notes",
            "setup_wizard_step",
        }
        filtered = {k: v for k, v in updates.items() if k in allowed_cols}
        if not filtered:
            return self.get_settings()
        set_clause = ", ".join(f"{k} = ?" for k in filtered.keys())
        values = list(filtered.values()) + ["usr-ann-001"]
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    f"UPDATE system_settings SET {set_clause} WHERE account_id = ?",
                    values,
                )
                conn.commit()
            finally:
                conn.close()
        return self.get_settings()

    def get_table_names(self) -> List[str]:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
                return [r["name"] for r in cur.fetchall()]
            finally:
                conn.close()
