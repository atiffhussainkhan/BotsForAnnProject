"""Owned TikTok comment ingestion and durable reply dispatch."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import hashlib
import os
import sqlite3
import threading
import time
from typing import Any, Callable
from zoneinfo import ZoneInfo

from apps.backend.ai import compute_similarity
from apps.backend.integrations.tiktok import TikTokAdapter
from apps.backend.integrations.tiktok.models import DispatchState, OperationalMode, TikTokIntegrationError
from apps.backend.platform_ops import PlatformMode
from backend.comment_drafts import grounded_draft




class TikTokWorker:
    """Use the approved provider account as the sole source of live comments."""

    def __init__(
        self, app: Any, adapter: TikTokAdapter | None = None, *, writes_enabled: bool | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.app = app
        self.clock = clock
        token = os.environ.get("TIKTOK_BUSINESS_ACCESS_TOKEN", "").strip()
        account = os.environ.get("TIKTOK_BUSINESS_OPEN_ID", "").strip()
        self.app_id = os.environ.get("TIKTOK_BUSINESS_APP_ID", "").strip()
        self.configured = bool(adapter is not None or (token and account and self.app_id))
        self.writes_enabled = (
            os.environ.get("TIKTOK_WRITE_ENABLED", "").lower() in {"1", "true", "yes"}
            if writes_enabled is None else writes_enabled
        )
        self.adapter = adapter or TikTokAdapter(
            business_id=account, access_token=token, accounts_api_approved=self.configured,
            write_enabled=False,
        )
        self.account = self.adapter.business_id
        self.lock = threading.Lock()
        self.wakeup = threading.Event()
        self.connected = False
        self.write_scope = False
        self.checked_at: float | None = None
        self.last_sync_at: float | None = None
        self.error: str | None = None
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tiktok_owned_inbox (
                    account TEXT NOT NULL,
                    video_id TEXT NOT NULL,
                    comment_id TEXT NOT NULL,
                    author TEXT NOT NULL,
                    body TEXT NOT NULL,
                    published_at INTEGER NOT NULL,
                    candidate TEXT,
                    category TEXT NOT NULL,
                    risk_tier TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempted_at REAL,
                    last_reconciled_at REAL,
                    reply_id TEXT,
                    pilot INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (account, comment_id)
                );
                CREATE INDEX IF NOT EXISTS idx_tiktok_inbox_state
                    ON tiktok_owned_inbox (account, state, published_at);
                CREATE TABLE IF NOT EXISTS tiktok_worker_settings (
                    account TEXT PRIMARY KEY,
                    auto_since REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tiktok_read_cursors (
                    account TEXT NOT NULL,
                    stream TEXT NOT NULL,
                    cursor INTEGER NOT NULL,
                    PRIMARY KEY(account, stream)
                );
            """)
            columns = {row[1] for row in db.execute("PRAGMA table_info(tiktok_owned_inbox)")}
            if "last_reconciled_at" not in columns:
                db.execute("ALTER TABLE tiktok_owned_inbox ADD COLUMN last_reconciled_at REAL")

    @contextmanager
    def _db(self):
        db = sqlite3.connect(str(self.app.db.db_path), timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def _pilot_verified(self) -> bool:
        with self._db() as db:
            return db.execute(
                "SELECT 1 FROM tiktok_owned_inbox WHERE account=? AND pilot=1 AND state='SENT' LIMIT 1",
                (self.account,),
            ).fetchone() is not None

    def _publish_connection_state(self) -> None:
        verified = self.connected and self.write_scope and self._pilot_verified()
        self.app.kill_switch.configure_connection_state(
            "tiktok", oauth_connected=self.connected, write_scope_verified=verified,
            review_pending=not self.connected and self.error is None,
            needs_reconnect=self.error in {"AUTH_REQUIRED", "PROVIDER_ACCESS_DENIED"},
            write_flag_enabled=self.writes_enabled and verified,
        )
        if self.app.kill_switch.get_platform_snapshot("tiktok").mode == PlatformMode.SAFE_AUTO and not verified:
            self.app.kill_switch.set_platform_mode("tiktok", PlatformMode.DRAFT)
            self.app.db.update_settings({"tiktok_mode": "DRAFT"})

    def overview(self) -> dict:
        with self._db() as db:
            count = db.execute(
                "SELECT COUNT(*) FROM tiktok_owned_inbox WHERE account=? AND state='SENT'",
                (self.account,),
            ).fetchone()[0]
            candidates = db.execute(
                """SELECT video_id, comment_id, body AS comment_text, candidate AS reply_candidate FROM tiktok_owned_inbox
                   WHERE account=? AND state='DRAFT_READY' ORDER BY published_at DESC LIMIT 15""",
                (self.account,),
            ).fetchall() if self.connected and self.write_scope and self.writes_enabled else []
        return {
            "configured": self.configured,
            "connected": self.connected,
            "can_request_pilot": self.connected and self.write_scope and self.writes_enabled,
            "pilot_verified": self.connected and self.write_scope and self._pilot_verified(),
            "pilot_candidates": [dict(row) for row in candidates],
            "auto_pilot_enabled": self.app.kill_switch.get_platform_snapshot("tiktok").mode == PlatformMode.SAFE_AUTO,
            "auto_replies_sent": count,
            "last_sync_at": datetime.fromtimestamp(self.last_sync_at).astimezone().isoformat() if self.last_sync_at else None,
            "last_error": self.error,
        }

    def inbox(self) -> list[dict]:
        with self._db() as db:
            rows = db.execute(
                """SELECT comment_id AS provider_comment_id, video_id AS post_id,
                          author AS commenter_pseudonym, body AS text_redacted,
                          category, risk_tier, state AS response_status, candidate AS reply_candidate,
                          reply_id
                   FROM tiktok_owned_inbox WHERE account=? ORDER BY published_at DESC LIMIT 300""",
                (self.account,),
            ).fetchall()
        return [dict(row, platform="tiktok", audit_trail=[]) for row in rows]

    def set_mode(self, mode: PlatformMode):
        before = self.app.kill_switch.get_platform_snapshot("tiktok").mode
        result = self.app.kill_switch.set_platform_mode("tiktok", mode)
        if result.mode == PlatformMode.SAFE_AUTO and before != PlatformMode.SAFE_AUTO:
            with self._db() as db:
                db.execute(
                    "INSERT OR REPLACE INTO tiktok_worker_settings(account, auto_since) VALUES (?, ?)",
                    (self.account, self.clock()),
                )
        return result

    def _provider_error(self, code: str) -> None:
        if any(part in code for part in ("401", "403", "AUTH", "SCOPE", "PERMISSION", "APPROVAL")):
            self.connected = self.write_scope = False
            self.error = "PROVIDER_ACCESS_DENIED"
            if self.app.db.get_settings().get("tiktok_mode") == "SAFE_AUTO":
                self.app.db.update_settings({"tiktok_mode": "DRAFT"})
            self._publish_connection_state()
        else:
            self.error = code

    @staticmethod
    def _result(response):
        if not response.ok or response.data is None:
            raise TikTokIntegrationError("TikTok declined verification", response.error_code or "PROVIDER_ACCESS_DENIED")
        return response.data

    def _verify(self) -> None:
        self.checked_at = self.clock()
        if not self.configured:
            self.error = "AWAITING_CREDENTIALS"
            return
        # Permission information comes from TikTok. A submitted form cannot grant access.
        scopes = self.adapter.inspect_access_token(self.app_id)
        self.write_scope = "comment.list.manage" in scopes
        posts = self._result(self.adapter.get_owned_posts(max_count=1))
        if posts:
            self._result(self.adapter.list_owned_comments(posts[0].video_id, max_count=1))
        self.connected = True
        self.error = None
        self._publish_connection_state()
        if (self.writes_enabled and self.write_scope and self._pilot_verified()
                and not self.app.kill_switch.emergency_stop_active
                and self.app.db.get_settings().get("tiktok_mode") == "SAFE_AUTO"):
            self.app.kill_switch.set_platform_mode("tiktok", PlatformMode.SAFE_AUTO)

    def verify(self) -> dict:
        if not self.lock.acquire(blocking=False):
            return dict(self.overview(), status="busy")
        try:
            try:
                self._verify()
            except (OSError, TikTokIntegrationError) as exc:
                self.connected = self.write_scope = False
                self._provider_error(getattr(exc, "code", "PROVIDER_UNREACHABLE"))
                self._publish_connection_state()
            return self.overview()
        finally:
            self.lock.release()

    def _page(self, reader, *args, page_limit=4, resume=False, **kwargs):
        cursor = 0
        stream = ":".join((reader.__name__, *map(str, args)))
        if resume:
            with self._db() as db:
                previous = db.execute(
                    "SELECT cursor FROM tiktok_read_cursors WHERE account=? AND stream=?",
                    (self.account, stream),
                ).fetchone()
            cursor = previous[0] if previous else 0
        for _ in range(page_limit):
            response = reader(*args, cursor=cursor, **kwargs)
            yield from self._result(response)
            next_cursor = response.metadata.get("cursor")
            more = response.metadata.get("has_more")
            if more and (next_cursor is None or next_cursor == cursor):
                raise TikTokIntegrationError("TikTok returned an invalid page cursor", "INVALID_PROVIDER_CURSOR")
            if resume:
                with self._db() as db:
                    db.execute(
                        "INSERT OR REPLACE INTO tiktok_read_cursors VALUES (?, ?, ?)",
                        (self.account, stream, int(next_cursor) if more else 0),
                    )
            if not more:
                return
            cursor = next_cursor

    def _ingest(self, post, comment) -> bool:
        if (not post.is_owned or post.business_id != self.account
                or comment.business_id != self.account or comment.video_id != post.video_id
                or comment.is_self_author or comment.status != "PUBLIC"
                or comment.is_reply or not comment.user_id or not comment.comment_id):
            return False
        with self._db() as db:
            known = db.execute(
                "SELECT 1 FROM tiktok_owned_inbox WHERE account=? AND comment_id=?",
                (self.account, comment.comment_id),
            ).fetchone()
        if known:
            return False
        redacted = self.app.redactor.redact(comment.text).redacted_text
        # Do not attach the demo fragrance to a real post. Generic compliments
        # can be automated, while fact-based answers await a verified post link.
        author = "TikTok viewer " + hashlib.sha256(
            f"{self.account}:{comment.user_id}".encode()
        ).hexdigest()[:10]
        classification = self.app.classifier.classify(redacted, author_handle=author)
        facts = self.app.comment_drafts.facts_for("tiktok", post.video_id)
        candidate = grounded_draft(classification, facts, comment.comment_id)
        if classification.risk_tier == "BLOCK":
            state = "BLOCKED_SAFETY_GUARD"
        elif candidate:
            state = "DRAFT_READY"
        else:
            state = "NEEDS_HUMAN_REVIEW"
        with self._db() as db:
            return bool(db.execute(
                """INSERT OR IGNORE INTO tiktok_owned_inbox
                   (account, video_id, comment_id, author, body, published_at,
            candidate, category, risk_tier, state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (self.account, post.video_id, comment.comment_id, author, redacted,
                 comment.create_time,
                 candidate, classification.category, classification.risk_tier, state),
            ).rowcount)

    def _write_allowed(self, *, pilot: bool, video_id: str | None = None) -> bool:
        if (not self.connected or not self.write_scope or not self.writes_enabled
                or self.checked_at is None or self.clock() - self.checked_at >= 600):
            return False
        if self.app.kill_switch.emergency_stop_active:
            return False
        if video_id is not None and (
            self.app.appeals_tracker.is_post_automation_frozen("tiktok", video_id)
            or self.app.db.is_post_frozen("tiktok", video_id)
        ):
            return False
        settings = self.app.db.get_settings()
        if settings.get("emergency_stop") or settings.get("tiktok_mode") == "OFF":
            return False
        if pilot:
            return True
        snap = self.app.kill_switch.get_platform_snapshot("tiktok")
        if snap.mode != PlatformMode.SAFE_AUTO or settings.get("tiktok_mode") != "SAFE_AUTO":
            return False
        now = datetime.fromtimestamp(self.clock(), ZoneInfo("Europe/London")).strftime("%H:%M")
        quiet = str(settings.get("quiet_hours") or "")
        if len(quiet) == 11 and quiet[5] == "-":
            start, end = quiet.split("-")
            if (start <= now < end if start <= end else now >= start or now < end):
                return False
        return True

    def _finish(self, comment_id: str, state: str, reply_id: str | None = None) -> None:
        with self._db() as db:
            db.execute(
                "UPDATE tiktok_owned_inbox SET state=?, reply_id=? WHERE account=? AND comment_id=?",
                (state, reply_id, self.account, comment_id),
            )

    def _dispatch(self, row, *, pilot=False) -> str:
        video_id, comment_id = row["video_id"], row["comment_id"]
        if not self._write_allowed(pilot=pilot, video_id=video_id):
            return "DRAFT_READY"
        current = self._result(self.adapter.list_owned_comments(video_id, comment_ids=[comment_id]))
        if not any(
            item.comment_id == comment_id and item.video_id == video_id
            and item.business_id == self.account and not item.is_self_author
            and not item.is_reply and item.status == "PUBLIC"
            and self.app.redactor.redact(item.text).redacted_text == row["body"]
            for item in current
        ):
            self._finish(comment_id, "NEEDS_HUMAN_REVIEW")
            return "NEEDS_HUMAN_REVIEW"
        classification = self.app.classifier.classify(row["body"], author_handle=row["author"])
        current_candidate = grounded_draft(
            classification, self.app.comment_drafts.facts_for("tiktok", video_id), comment_id,
        )
        if not current_candidate or current_candidate != row["candidate"]:
            self._finish(comment_id, "NEEDS_HUMAN_REVIEW")
            return "NEEDS_HUMAN_REVIEW"
        # Fetch existing provider replies first to avoid answering an already
        # handled thread. Incomplete reply history stays in the review queue.
        response = self.adapter.list_comment_replies(video_id, comment_id, max_count=50)
        if any(reply.is_self_author for reply in self._result(response)):
            self._finish(comment_id, "ALREADY_REPLIED")
            return "ALREADY_REPLIED"
        if response.metadata.get("has_more"):
            return "DRAFT_READY"
        if not self._write_allowed(pilot=pilot, video_id=video_id):
            return "DRAFT_READY"
        now = self.clock()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            limit = max(0, min(100, int(self.app.db.get_settings().get("max_daily_actions", 100))))
            attempted = db.execute(
                "SELECT COUNT(*) FROM tiktok_owned_inbox WHERE account=? AND attempted_at>?",
                (self.account, now - 86400),
            ).fetchone()[0]
            if attempted >= limit:
                return "DRAFT_READY"
            recent = db.execute(
                """SELECT candidate FROM tiktok_owned_inbox WHERE account=? AND video_id=?
                   AND state IN ('SENDING','SENT','RECONCILE_PENDING')
                   AND attempted_at>? ORDER BY attempted_at DESC LIMIT 100""",
                (self.account, video_id, now - 86400),
            ).fetchall()
            if any(
                compute_similarity(row["candidate"], previous["candidate"])
                >= self.app.template_catalog.similarity_threshold
                for previous in recent
            ):
                db.execute(
                    "UPDATE tiktok_owned_inbox SET state='NEEDS_HUMAN_REVIEW' WHERE account=? AND comment_id=? AND state='DRAFT_READY'",
                    (self.account, comment_id),
                )
                return "NEEDS_HUMAN_REVIEW"
            updated = db.execute(
                """UPDATE tiktok_owned_inbox SET state='SENDING', attempted_at=?, pilot=?
                   WHERE account=? AND comment_id=? AND state='DRAFT_READY'""",
                (now, int(pilot), self.account, comment_id),
            ).rowcount
        if not updated:
            return "ALREADY_ATTEMPTED"
        if not self._write_allowed(pilot=pilot, video_id=video_id):
            self._finish(comment_id, "DRAFT_READY")
            return "DRAFT_READY"
        key = hashlib.sha256(f"tiktok:{self.account}:{video_id}:{comment_id}".encode()).hexdigest()
        self.adapter.write_enabled = True
        self.adapter.operational_mode = OperationalMode.SAFE_AUTO
        try:
            result = self.adapter.reply_to_owned_comment(
                video_id=video_id, comment_id=comment_id, text=row["candidate"], idempotency_key=key,
            )
            data = result.data
            if result.ok and data and data.dispatch_state == DispatchState.SENT and data.comment_id:
                self._finish(comment_id, "SENT", data.comment_id)
                return "SENT"
            if result.error_code:
                self._provider_error(result.error_code)
            state = (
                "RECONCILE_PENDING" if not data or data.dispatch_state in {DispatchState.SENT, DispatchState.RECONCILE_PENDING}
                else "FAILED"
            )
        except (OSError, TikTokIntegrationError) as exc:
            self._provider_error(getattr(exc, "code", "REPLY_OUTCOME_UNKNOWN"))
            state = "RECONCILE_PENDING"
        finally:
            self.adapter.write_enabled = False
            self.adapter.operational_mode = OperationalMode.DRAFT
        self._finish(comment_id, state)
        return state

    def _reconcile(self) -> None:
        with self._db() as db:
            pending = db.execute(
                """SELECT * FROM tiktok_owned_inbox WHERE account=?
                   AND state IN ('SENDING', 'RECONCILE_PENDING')
                   ORDER BY COALESCE(last_reconciled_at, 0), attempted_at LIMIT 10""", (self.account,),
            ).fetchall()
        for row in pending:
            with self._db() as db:
                db.execute(
                    "UPDATE tiktok_owned_inbox SET last_reconciled_at=? WHERE account=? AND comment_id=?",
                    (self.clock(), self.account, row["comment_id"]),
                )
            for reply in self._page(self.adapter.list_comment_replies, row["video_id"], row["comment_id"]):
                if (reply.is_self_author and reply.text == row["candidate"] and reply.comment_id
                        and reply.create_time >= int(row["attempted_at"])):
                    self._finish(row["comment_id"], "SENT", reply.comment_id)
                    break

    def sync(self) -> dict:
        if not self.lock.acquire(blocking=False):
            return {"status": "busy", "processed_count": 0}
        try:
            if not self.configured:
                return {"status": "awaiting_credentials", "processed_count": 0}
            if self.app.kill_switch.emergency_stop_active or self.app.kill_switch.get_platform_snapshot("tiktok").mode == PlatformMode.OFF:
                return {"status": "paused", "processed_count": 0}
            processed = sent = 0
            try:
                if not self.connected or self.clock() - (self.checked_at or 0) >= 600:
                    self._verify()
                for post in self._page(
                    self.adapter.get_owned_posts, page_limit=2, max_count=10, resume=True,
                ):
                    if not post.is_owned or post.business_id != self.account:
                        continue
                    for comment in self._page(
                        self.adapter.list_owned_comments, post.video_id,
                        include_replies=False, page_limit=4, resume=True,
                    ):
                        if self.app.kill_switch.emergency_stop_active:
                            return {"status": "paused", "processed_count": processed}
                        processed += self._ingest(post, comment)
                self._reconcile()
                if self._write_allowed(pilot=False):
                    with self._db() as db:
                        ready = db.execute(
                            """SELECT i.* FROM tiktok_owned_inbox i
                               JOIN tiktok_worker_settings s ON i.account=s.account
                               WHERE i.account=? AND i.state='DRAFT_READY'
                                 AND i.published_at>=s.auto_since
                               ORDER BY i.published_at LIMIT 20""", (self.account,),
                        ).fetchall()
                    for row in ready:
                        sent += self._dispatch(row) == "SENT"
            except (OSError, TikTokIntegrationError) as exc:
                self._provider_error(getattr(exc, "code", "PROVIDER_UNREACHABLE"))
                return {"status": "provider_error", "error": self.error, "processed_count": processed, "sent": sent}
            self.last_sync_at = self.clock()
            self.error = None
            self._publish_connection_state()
            return {"status": "ok", "processed_count": processed, "sent": sent}
        finally:
            self.lock.release()

    def pilot(self, video_id: str, comment_id: str) -> dict:
        if not self.lock.acquire(blocking=False):
            return {"status": "busy"}
        try:
            if self.configured and (not self.connected or self.clock() - (self.checked_at or 0) >= 600):
                try:
                    self._verify()
                except (OSError, TikTokIntegrationError) as exc:
                    self._provider_error(getattr(exc, "code", "PROVIDER_UNREACHABLE"))
                    return {"status": "provider_error"}
            if not self._write_allowed(pilot=True):
                return {"status": "pilot_unavailable"}
            with self._db() as db:
                row = db.execute(
                    """SELECT * FROM tiktok_owned_inbox WHERE account=? AND video_id=?
                       AND comment_id=? AND state='DRAFT_READY'""",
                    (self.account, video_id, comment_id),
                ).fetchone()
            if row is None:
                return {"status": "draft_unavailable"}
            try:
                state = self._dispatch(row, pilot=True)
            except (OSError, TikTokIntegrationError) as exc:
                self._provider_error(getattr(exc, "code", "PROVIDER_UNREACHABLE"))
                return {"status": "provider_error"}
            self._publish_connection_state()
            return {"status": state}
        finally:
            self.lock.release()
