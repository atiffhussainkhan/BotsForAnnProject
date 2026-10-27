"""
Agent Echo (Agent 5) — Universal `EMERGENCY STOP` Kill-Switch & Per-Platform Mode State Machine.

Satisfies:
- FR-006: Route safe ordinary replies to auto-send ONLY when platform adapter is verified and mode is `SAFE_AUTO`; default to `DRAFT`.
- FR-010: Manual pause switch, circuit breaker, and bulk draft-only mode.
- FR-035: Prominent `OFF` / `DRAFT` / `SAFE_AUTO` switch per platform + universal `EMERGENCY STOP` kill-switch that halts all outgoing writes and queued jobs immediately.
- FR-043: Truthful connection status badges (`Not connected`, `Connected: read only`, `Awaiting review`, `Live: can reply`, `Suspended`, `Needs reconnect`).
- NFR-09: Instant feature flags (`TIKTOK_WRITE_ENABLED`, `INSTAGRAM_WRITE_ENABLED`, `THIRD_PARTY_AUTOCOMMENT`) defaulting to `false`.
- NFR-10: Automatic downgrade to `READ_ONLY` / `DRAFT` on 401/403, token revocation, rate-limit anomaly, or policy warning.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PlatformMode(str, Enum):
    OFF = "OFF"
    OBSERVE = "OBSERVE"
    DRAFT = "DRAFT"
    SAFE_AUTO = "SAFE_AUTO"
    PAUSED_BY_SYSTEM = "PAUSED_BY_SYSTEM"


class ConnectionBadge(str, Enum):
    NOT_CONNECTED = "Not connected"
    CONNECTED_READ_ONLY = "Connected: read only"
    AWAITING_REVIEW = "Awaiting review"
    LIVE_CAN_REPLY = "Live: can reply"
    SUSPENDED = "Suspended"
    NEEDS_RECONNECT = "Needs reconnect"


@dataclass
class QueuedOutboundJob:
    job_id: str
    platform: str
    comment_id: str
    reply_text: str
    status: str = "QUEUED"  # QUEUED, DRAFT, SENT, CANCELLED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    reason: str = ""


@dataclass
class PlatformStateSnapshot:
    platform: str
    mode: PlatformMode
    write_flag_enabled: bool
    oauth_connected: bool
    write_scope_verified: bool
    review_pending: bool
    needs_reconnect: bool
    suspended: bool
    badge: ConnectionBadge
    last_transition_reason: str
    updated_at: float


class KillSwitchController:
    """
    Central authority governing the Universal `EMERGENCY STOP` kill-switch,
    per-platform modes, truthful connection badges, and the outbound dispatch queue.
    """

    SUPPORTED_PLATFORMS = ("tiktok", "instagram")

    def __init__(
        self,
        tiktok_write_enabled: Optional[bool] = None,
        instagram_write_enabled: Optional[bool] = None,
        third_party_autocomment: Optional[bool] = None,
    ) -> None:
        self._lock = threading.RLock()
        self.emergency_stop_active: bool = False
        self.emergency_stop_reason: str = ""
        self.emergency_stop_timestamp: Optional[float] = None

        # NFR-09: Default feature flags must be False unless explicitly enabled
        self.feature_flags: Dict[str, bool] = {
            "TIKTOK_WRITE_ENABLED": self._parse_bool(
                tiktok_write_enabled, os.environ.get("TIKTOK_WRITE_ENABLED", "false")
            ),
            "INSTAGRAM_WRITE_ENABLED": self._parse_bool(
                instagram_write_enabled, os.environ.get("INSTAGRAM_WRITE_ENABLED", "false")
            ),
            "THIRD_PARTY_AUTOCOMMENT": self._parse_bool(
                third_party_autocomment, os.environ.get("THIRD_PARTY_AUTOCOMMENT", "false")
            ),
        }

        self._modes: Dict[str, PlatformMode] = {
            "tiktok": PlatformMode.DRAFT,
            "instagram": PlatformMode.DRAFT,
        }
        self._connection_meta: Dict[str, Dict[str, Any]] = {
            "tiktok": {
                "oauth_connected": True,
                "write_scope_verified": False,
                "review_pending": True,
                "needs_reconnect": False,
                "suspended": False,
                "last_reason": "Default initial safe state (TikTok write scope awaiting review)",
                "updated_at": time.time(),
            },
            "instagram": {
                "oauth_connected": True,
                "write_scope_verified": False,
                "review_pending": True,
                "needs_reconnect": False,
                "suspended": False,
                "last_reason": "Default initial safe state (Instagram in DRAFT mode)",
                "updated_at": time.time(),
            },
        }
        self._outbound_queue: Dict[str, QueuedOutboundJob] = {}
        self._transition_history: List[Dict[str, Any]] = []

    @staticmethod
    def _parse_bool(explicit: Optional[bool], env_val: str) -> bool:
        if explicit is not None:
            return bool(explicit)
        return str(env_val).strip().lower() in ("true", "1", "yes")

    def enqueue_job(
        self, job_id: str, platform: str, comment_id: str, reply_text: str
    ) -> QueuedOutboundJob:
        """
        Add an outbound reply candidate to the queue.
        If Emergency Stop is active or platform cannot auto-dispatch, it is immediately stored as `DRAFT`.
        """
        platform_key = platform.lower()
        with self._lock:
            can_send, block_reason = self.can_dispatch_outbound(platform_key)
            initial_status = "QUEUED" if can_send else "DRAFT"
            job = QueuedOutboundJob(
                job_id=job_id,
                platform=platform_key,
                comment_id=comment_id,
                reply_text=reply_text,
                status=initial_status,
                reason="Ready for SAFE_AUTO dispatch" if can_send else block_reason,
            )
            self._outbound_queue[job_id] = job
            return job

    def trigger_emergency_stop(
        self, triggered_by: str = "@annreveals", reason: str = "Owner activated Universal Emergency Stop"
    ) -> Dict[str, Any]:
        """
        FR-035: Immediately halt all outgoing writes across all platforms and drain every queued job to `DRAFT`.
        """
        with self._lock:
            now = time.time()
            self.emergency_stop_active = True
            self.emergency_stop_reason = reason
            self.emergency_stop_timestamp = now

            for p in self.SUPPORTED_PLATFORMS:
                self._modes[p] = PlatformMode.OFF
                self._connection_meta[p]["last_reason"] = f"EMERGENCY STOP: {reason}"
                self._connection_meta[p]["updated_at"] = now

            drained_count = self._drain_queue_to_draft_locked(
                platform=None, reason=f"Drained by Universal EMERGENCY STOP ({reason})"
            )

            event = {
                "event": "EMERGENCY_STOP_ACTIVATED",
                "triggered_by": triggered_by,
                "reason": reason,
                "drained_jobs_to_draft": drained_count,
                "timestamp": now,
            }
            self._transition_history.append(event)
            return event

    def release_emergency_stop(
        self, released_by: str = "@annreveals", reason: str = "Owner released Emergency Stop"
    ) -> Dict[str, Any]:
        """
        Release the Universal Emergency Stop and return platforms safely to `DRAFT` mode
        (never jumps straight to `SAFE_AUTO` without explicit re-enablement).
        """
        with self._lock:
            now = time.time()
            self.emergency_stop_active = False
            self.emergency_stop_reason = ""
            for p in self.SUPPORTED_PLATFORMS:
                self._modes[p] = PlatformMode.DRAFT
                self._connection_meta[p]["last_reason"] = reason
                self._connection_meta[p]["updated_at"] = now

            event = {
                "event": "EMERGENCY_STOP_RELEASED",
                "released_by": released_by,
                "reason": reason,
                "restored_mode": PlatformMode.DRAFT.value,
                "timestamp": now,
            }
            self._transition_history.append(event)
            return event

    def set_platform_mode(
        self, platform: str, target_mode: PlatformMode | str, actor: str = "@annreveals", reason: str = "Manual mode update"
    ) -> PlatformStateSnapshot:
        """
        Update a platform's operational mode (`OFF`, `OBSERVE`, `DRAFT`, `SAFE_AUTO`, `PAUSED_BY_SYSTEM`).
        Enforces `FR-006`: `SAFE_AUTO` is only permitted if Emergency Stop is inactive, feature flag is enabled,
        OAuth is connected, and write scope is verified live. Otherwise falls back to `DRAFT`.
        """
        p = platform.lower()
        if p not in self.SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported platform: {platform}")
        mode_enum = PlatformMode(target_mode) if isinstance(target_mode, str) else target_mode

        with self._lock:
            if self.emergency_stop_active and mode_enum != PlatformMode.OFF:
                raise RuntimeError("Cannot enable platform mode while Universal EMERGENCY STOP is active.")

            meta = self._connection_meta[p]
            flag_name = "TIKTOK_WRITE_ENABLED" if p == "tiktok" else "INSTAGRAM_WRITE_ENABLED"
            write_flag = self.feature_flags.get(flag_name, False)

            if mode_enum == PlatformMode.SAFE_AUTO:
                if (
                    not write_flag
                    or not meta["oauth_connected"]
                    or not meta["write_scope_verified"]
                    or meta["needs_reconnect"]
                    or meta["suspended"]
                ):
                    # Honest fallback to DRAFT if write permissions are not live
                    mode_enum = PlatformMode.DRAFT
                    reason = (
                        f"Requested SAFE_AUTO downgraded to DRAFT: write_flag={write_flag}, "
                        f"write_scope_verified={meta['write_scope_verified']}"
                    )

            self._modes[p] = mode_enum
            meta["last_reason"] = reason
            meta["updated_at"] = time.time()

            if mode_enum != PlatformMode.SAFE_AUTO:
                self._drain_queue_to_draft_locked(
                    platform=p, reason=f"Platform {p} mode set to {mode_enum.value}"
                )

            self._transition_history.append(
                {
                    "event": "PLATFORM_MODE_CHANGED",
                    "platform": p,
                    "mode": mode_enum.value,
                    "actor": actor,
                    "reason": reason,
                    "timestamp": meta["updated_at"],
                }
            )
            return self.get_platform_snapshot(p)

    def configure_connection_state(
        self,
        platform: str,
        *,
        oauth_connected: Optional[bool] = None,
        write_scope_verified: Optional[bool] = None,
        review_pending: Optional[bool] = None,
        needs_reconnect: Optional[bool] = None,
        suspended: Optional[bool] = None,
        write_flag_enabled: Optional[bool] = None,
    ) -> PlatformStateSnapshot:
        """Update live OAuth/scope state and recompute truthful status badges (`FR-043`)."""
        p = platform.lower()
        with self._lock:
            meta = self._connection_meta[p]
            if oauth_connected is not None:
                meta["oauth_connected"] = bool(oauth_connected)
            if write_scope_verified is not None:
                meta["write_scope_verified"] = bool(write_scope_verified)
            if review_pending is not None:
                meta["review_pending"] = bool(review_pending)
            if needs_reconnect is not None:
                meta["needs_reconnect"] = bool(needs_reconnect)
            if suspended is not None:
                meta["suspended"] = bool(suspended)
            if write_flag_enabled is not None:
                flag_name = "TIKTOK_WRITE_ENABLED" if p == "tiktok" else "INSTAGRAM_WRITE_ENABLED"
                self.feature_flags[flag_name] = bool(write_flag_enabled)
            meta["updated_at"] = time.time()
            return self.get_platform_snapshot(p)

    def auto_downgrade_on_incident(
        self, platform: str, incident_type: str, details: str = ""
    ) -> PlatformStateSnapshot:
        """
        NFR-10: Automatic downgrade to `PAUSED_BY_SYSTEM` (`DRAFT` queue) on 401/403,
        token revocation, rate-limit anomaly, or policy warning.
        """
        p = platform.lower()
        with self._lock:
            meta = self._connection_meta[p]
            self._modes[p] = PlatformMode.PAUSED_BY_SYSTEM
            if incident_type in ("HTTP_401", "HTTP_403", "TOKEN_REVOKED"):
                meta["needs_reconnect"] = True
                meta["write_scope_verified"] = False
            elif incident_type in ("ACCOUNT_SUSPENDED", "POLICY_RESTRICTION"):
                meta["suspended"] = True
                meta["write_scope_verified"] = False

            reason = f"Auto-downgraded due to {incident_type}: {details}".strip()
            meta["last_reason"] = reason
            meta["updated_at"] = time.time()

            drained = self._drain_queue_to_draft_locked(platform=p, reason=reason)
            self._transition_history.append(
                {
                    "event": "AUTO_DOWNGRADE",
                    "platform": p,
                    "incident_type": incident_type,
                    "details": details,
                    "drained_jobs": drained,
                    "timestamp": meta["updated_at"],
                }
            )
            return self.get_platform_snapshot(p)

    def _drain_queue_to_draft_locked(self, platform: Optional[str], reason: str) -> int:
        drained = 0
        now = time.time()
        for job in self._outbound_queue.values():
            if job.status == "QUEUED" and (platform is None or job.platform == platform):
                job.status = "DRAFT"
                job.reason = reason
                job.updated_at = now
                drained += 1
        return drained

    def compute_badge(self, platform: str) -> ConnectionBadge:
        """
        FR-043: Compute truthful connection status badge from live token & scope state.
        Never reports `Live: can reply` unless OAuth is connected, write flag is on, and write scope is verified.
        """
        p = platform.lower()
        with self._lock:
            meta = self._connection_meta[p]
            flag_name = "TIKTOK_WRITE_ENABLED" if p == "tiktok" else "INSTAGRAM_WRITE_ENABLED"
            write_flag = self.feature_flags.get(flag_name, False)

            if meta["suspended"]:
                return ConnectionBadge.SUSPENDED
            if meta["needs_reconnect"]:
                return ConnectionBadge.NEEDS_RECONNECT
            if not meta["oauth_connected"]:
                return ConnectionBadge.NOT_CONNECTED
            if meta["write_scope_verified"] and write_flag and not self.emergency_stop_active:
                return ConnectionBadge.LIVE_CAN_REPLY
            if meta["review_pending"]:
                return ConnectionBadge.AWAITING_REVIEW
            return ConnectionBadge.CONNECTED_READ_ONLY

    def can_dispatch_outbound(self, platform: str, is_third_party_post: bool = False) -> tuple[bool, str]:
        """Return `(allowed, reason)` indicating whether an automated reply may leave the system."""
        p = platform.lower()
        with self._lock:
            if self.emergency_stop_active:
                return False, "Blocked by Universal EMERGENCY STOP"
            if is_third_party_post and not self.feature_flags.get("THIRD_PARTY_AUTOCOMMENT", False):
                return False, "Third-party auto-commenting is disabled (FR-017 owner-in-the-loop required)"
            mode = self._modes.get(p, PlatformMode.DRAFT)
            if mode != PlatformMode.SAFE_AUTO:
                return False, f"Platform {p} is in {mode.value} mode (held as DRAFT)"
            badge = self.compute_badge(p)
            if badge != ConnectionBadge.LIVE_CAN_REPLY:
                return False, f"Platform {p} badge is '{badge.value}' (held as DRAFT)"
            return True, "Permitted under verified SAFE_AUTO"

    def get_platform_snapshot(self, platform: str) -> PlatformStateSnapshot:
        p = platform.lower()
        with self._lock:
            meta = self._connection_meta[p]
            flag_name = "TIKTOK_WRITE_ENABLED" if p == "tiktok" else "INSTAGRAM_WRITE_ENABLED"
            return PlatformStateSnapshot(
                platform=p,
                mode=self._modes[p],
                write_flag_enabled=self.feature_flags.get(flag_name, False),
                oauth_connected=meta["oauth_connected"],
                write_scope_verified=meta["write_scope_verified"],
                review_pending=meta["review_pending"],
                needs_reconnect=meta["needs_reconnect"],
                suspended=meta["suspended"],
                badge=self.compute_badge(p),
                last_transition_reason=meta["last_reason"],
                updated_at=meta["updated_at"],
            )

    def get_queued_jobs(self, status: Optional[str] = None) -> List[QueuedOutboundJob]:
        with self._lock:
            jobs = list(self._outbound_queue.values())
            if status is not None:
                jobs = [j for j in jobs if j.status == status]
            return jobs

    @property
    def transition_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._transition_history)
