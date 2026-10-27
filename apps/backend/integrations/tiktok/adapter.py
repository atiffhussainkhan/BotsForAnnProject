"""Official TikTok Platform Adapter (`adapter.py`) for Ann Reveals AI Manager (v4.0).

Strictly uses ONLY the Python 3.9+ standard library (`hmac`, `hashlib`, `json`, `time`,
`urllib.request`, `urllib.parse`, `urllib.error`, `dataclasses`, `typing`, `enum`, `random`, `pathlib`).

Implements all 12 provider-neutral methods:
1. `get_owned_profile`
2. `get_owned_posts`
3. `list_owned_comments`
4. `reply_to_owned_comment`
5. `create_comment_on_owned_post`
6. `subscribe_to_webhooks`
7. `refresh_auth`
8. `publish_post`
9. `get_post_publication_status`
10. `get_inbox_messages`
11. `get_following_posts` (Permanently UNAVAILABLE -> raises PermissionPolicyError)
12. `comment_on_nonowned_post` (Permanently UNAVAILABLE -> raises PermissionPolicyError)

Enforces:
- `TIKTOK_WRITE_ENABLED=false` by default (NFR-09).
- March 20, 2026 TikTok Accounts API v1.3 access application gate (`AWAITING_APPROVAL` by default).
- Outbound URL host allowlist (`business-api.tiktok.com`, `open.tiktokapis.com`).
- Rate-limit 429 `Retry-After` + jittered `30s/60s/120s` backoff calculations (NFR-02).
- Fail-closed automatic downgrade to `DRAFT`/`READ_ONLY` on HTTP 401/403 (NFR-10).
- Consecutive 5xx circuit breaker.
- Effectively-once idempotency tracking with `RECONCILE_PENDING` on timeout (NFR-03).
- Anti-spam ownership comment guard (FR-055).
"""

import json
import os
from pathlib import Path
import random
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import urllib.error
import urllib.parse
import urllib.request

from .models import (
    CapabilityStatus,
    CircuitBreakerOpenError,
    CommentWriteResult,
    ConnectionBadge,
    DispatchState,
    OperationalMode,
    PermissionPolicyError,
    ProviderResponse,
    PublishPostRequest,
    PublishPostResult,
    RateLimitExceededError,
    ScopeNotApprovedError,
    SecurityConfigurationError,
    TikTokComment,
    TikTokIntegrationError,
    TikTokPost,
    TikTokProfile,
    TokenGrant,
    WriteDisabledError,
)

ALLOWED_OUTBOUND_HOSTS: Set[str] = {
    "business-api.tiktok.com",
    "open.tiktokapis.com",
}

BACKOFF_SCHEDULE_SECONDS: Tuple[int, int, int] = (30, 60, 120)
MAX_COMMENT_LENGTH_CHARS = 150


class TikTokAdapter:
    """Production-grade, fail-closed TikTok Accounts API v1.3 & Content Posting API v2 adapter."""

    def __init__(
        self,
        business_id: str = "annreveals_biz_001",
        handle: str = "@annreveals",
        access_token: Optional[str] = None,
        granted_scopes: Optional[List[str]] = None,
        write_enabled: Optional[bool] = None,
        operational_mode: OperationalMode = OperationalMode.DRAFT,
        sandbox_mode: bool = False,
        accounts_api_approved: bool = False,
        http_transport: Optional[Callable[[urllib.request.Request, float], Tuple[int, Dict[str, str], bytes]]] = None,
        circuit_breaker_threshold: int = 3,
        circuit_breaker_cooldown_seconds: float = 300.0,
    ) -> None:
        self.business_id = business_id
        self.handle = handle
        self._access_token = access_token or ""
        self._granted_scopes: Set[str] = set(granted_scopes or [])

        if write_enabled is None:
            env_val = os.environ.get("TIKTOK_WRITE_ENABLED", "false").strip().lower()
            self.write_enabled = env_val in ("1", "true", "yes")
        else:
            self.write_enabled = bool(write_enabled)

        self.operational_mode = operational_mode
        self.sandbox_mode = bool(sandbox_mode)
        self.accounts_api_approved = bool(accounts_api_approved)
        self._http_transport = http_transport
        self._circuit_breaker_threshold = max(1, circuit_breaker_threshold)
        self._circuit_breaker_cooldown_seconds = circuit_breaker_cooldown_seconds

        # Resiliency & audit state
        self.consecutive_5xx_failures: int = 0
        self.circuit_open_until_epoch: float = 0.0
        self.rate_limit_cooldown_until_epoch: float = 0.0
        self._auth_revoked_or_expired: bool = False
        self._idempotency_store: Dict[str, CommentWriteResult] = {}
        self._recent_ownership_comments: Set[str] = set()
        self.audit_log: List[Dict[str, Any]] = []

        # Load capability manifest
        manifest_path = Path(__file__).with_name("tiktok-capabilities.json")
        with manifest_path.open("r", encoding="utf-8") as fh:
            self._manifest: Dict[str, Any] = json.load(fh)

        # Deterministic sandbox fixtures
        self._sandbox_posts: List[TikTokPost] = [
            TikTokPost(
                video_id="tt_vid_742910001",
                business_id=self.business_id,
                caption="My honest wear-test of Baccarat Rouge 540 Extrait after 8 hours on skin. Purchased with my own money. #perfumetok #fragrancereview #nicheperfume #annreveals #ukfragrance",
                share_url="https://www.tiktok.com/@annreveals/video/742910001",
                create_time=1761560000,
                comment_count=14,
                like_count=320,
                view_count=8450,
                duration_seconds=58,
                is_owned=True,
            ),
            TikTokPost(
                video_id="tt_vid_742910002",
                business_id=self.business_id,
                caption="First impressions of Delina Exclusif — soft velvety rose & vanilla dry-down. #delinaexclusif #parfumsdemarly #perfumecollection #annreveals #scentoftheday",
                share_url="https://www.tiktok.com/@annreveals/video/742910002",
                create_time=1761563600,
                comment_count=9,
                like_count=215,
                view_count=5120,
                duration_seconds=45,
                is_owned=True,
            ),
        ]
        self._sandbox_comments: Dict[str, List[TikTokComment]] = {
            "tt_vid_742910001": [
                TikTokComment(
                    comment_id="tt_cmt_9001",
                    video_id="tt_vid_742910001",
                    business_id=self.business_id,
                    text="How many hours did the almond and ambergris trail last on your coat?",
                    create_time=1761560500,
                    user_id="viewer_uk_101",
                    username="sophie_scents",
                    parent_comment_id=None,
                    is_reply=False,
                    is_self_author=False,
                    status="PUBLIC",
                    like_count=4,
                ),
                TikTokComment(
                    comment_id="tt_cmt_9002",
                    video_id="tt_vid_742910001",
                    business_id=self.business_id,
                    text="Thank you lovely! Purchased with my own money and tested over a full workday.",
                    create_time=1761560600,
                    user_id=self.business_id,
                    username="annreveals",
                    parent_comment_id="tt_cmt_9001",
                    is_reply=True,
                    is_self_author=True,
                    status="PUBLIC",
                    like_count=2,
                ),
            ]
        }

    # -------------------------------------------------------------------------
    # Capability & Connection Badge Inspection
    # -------------------------------------------------------------------------

    def get_capability_status(self, capability_name: str) -> CapabilityStatus:
        """Return truthful capability classification (`VERIFIED_ACTIVE`, `AWAITING_APPROVAL`, `UNAVAILABLE`, `UNKNOWN`)."""
        cap_meta = self._manifest.get("capabilities", {}).get(capability_name)
        if not cap_meta:
            return CapabilityStatus.UNKNOWN

        # Permanent policy prohibitions are always UNAVAILABLE even in sandbox mode
        if cap_meta.get("live_status") == "UNAVAILABLE":
            return CapabilityStatus.UNAVAILABLE

        if self._auth_revoked_or_expired:
            return CapabilityStatus.AWAITING_APPROVAL

        required_scopes: List[str] = cap_meta.get("required_scopes", [])
        if self.sandbox_mode:
            if required_scopes and self._granted_scopes and not all(
                s in self._granted_scopes for s in required_scopes
            ):
                return CapabilityStatus.AWAITING_APPROVAL
            return CapabilityStatus(cap_meta.get("sandbox_status", "VERIFIED_ACTIVE"))

        # Live mode requires March 20, 2026 gate approval (where applicable), access token, and scopes
        if cap_meta.get("march_20_2026_gate", False) and not self.accounts_api_approved:
            return CapabilityStatus.AWAITING_APPROVAL

        if not self._access_token:
            return CapabilityStatus.AWAITING_APPROVAL

        if required_scopes and not all(s in self._granted_scopes for s in required_scopes):
            return CapabilityStatus.AWAITING_APPROVAL

        return CapabilityStatus.VERIFIED_ACTIVE

    def get_connection_badge(self) -> ConnectionBadge:
        """Compute the truthful UI connection status badge (FR-043)."""
        if self._auth_revoked_or_expired:
            return ConnectionBadge.NEEDS_RECONNECT

        if not self._access_token and not self.sandbox_mode:
            return ConnectionBadge.NOT_CONNECTED

        read_active = self.get_capability_status("list_owned_comments") == CapabilityStatus.VERIFIED_ACTIVE
        write_active = self.get_capability_status("reply_to_owned_comment") == CapabilityStatus.VERIFIED_ACTIVE

        if not read_active:
            return ConnectionBadge.AWAITING_REVIEW

        if write_active and self.write_enabled and self.operational_mode == OperationalMode.SAFE_AUTO:
            return ConnectionBadge.LIVE_CAN_REPLY

        return ConnectionBadge.CONNECTED_READ_ONLY

    # -------------------------------------------------------------------------
    # Security, Rate-Limit Backoff, Circuit Breaker & Fail-Closed Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def validate_outbound_url(url: str) -> None:
        """Enforce HTTPS and strict outbound host allowlist (`business-api.tiktok.com`, `open.tiktokapis.com`)."""
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme.lower() != "https":
            raise SecurityConfigurationError(
                f"Outbound TikTok request must use HTTPS, got scheme '{parsed.scheme}'",
                code="ERR_INSECURE_SCHEME",
            )
        host = (parsed.hostname or "").lower()
        if host not in ALLOWED_OUTBOUND_HOSTS:
            raise SecurityConfigurationError(
                f"Outbound host '{host}' is not in the TikTok allowlist {sorted(ALLOWED_OUTBOUND_HOSTS)}",
                code="ERR_OUTBOUND_HOST_FORBIDDEN",
            )

    @staticmethod
    def calculate_backoff_seconds(
        attempt: int,
        retry_after_header: Optional[str] = None,
        jitter_ratio: float = 0.15,
        rng: Optional[random.Random] = None,
    ) -> float:
        """Calculate NFR-02 compliant 30s/60s/120s jittered backoff honoring Retry-After."""
        idx = max(0, min(attempt, len(BACKOFF_SCHEDULE_SECONDS) - 1))
        base_delay = float(BACKOFF_SCHEDULE_SECONDS[idx])

        header_delay = 0.0
        if retry_after_header:
            try:
                header_delay = float(retry_after_header.strip())
            except ValueError:
                header_delay = 0.0

        effective_base = max(base_delay, header_delay)
        rand_source = rng or random
        jitter = effective_base * jitter_ratio * rand_source.uniform(-1.0, 1.0)
        return max(1.0, round(effective_base + jitter, 2))

    def _trigger_fail_closed_downgrade(self, status_code: int, reason: str) -> None:
        """Immediately transition adapter to DRAFT / READ_ONLY on 401/403 (NFR-10)."""
        self.write_enabled = False
        self.operational_mode = OperationalMode.DRAFT
        self._auth_revoked_or_expired = True
        self._record_audit(
            action="FAIL_CLOSED_DOWNGRADE",
            status="DOWNGRADED_TO_DRAFT",
            details={"http_status": status_code, "reason": reason},
        )

    def _record_audit(self, action: str, status: str, details: Dict[str, Any]) -> None:
        self.audit_log.append(
            {
                "timestamp": int(time.time()),
                "provider": "tiktok",
                "action": action,
                "status": status,
                "operational_mode": self.operational_mode.value,
                "write_enabled": self.write_enabled,
                "details": details,
            }
        )

    def _check_circuit_breaker(self, now_epoch: Optional[float] = None) -> None:
        now = float(now_epoch if now_epoch is not None else time.time())
        if self.circuit_open_until_epoch > now:
            raise CircuitBreakerOpenError(
                f"TikTok circuit breaker is OPEN until {self.circuit_open_until_epoch:.0f}",
                open_until_epoch=self.circuit_open_until_epoch,
            )

    def _execute_http_json(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = 10.0,
        attempt: int = 0,
    ) -> Dict[str, Any]:
        """Execute an allowlisted HTTPS request with circuit-breaker, 429 backoff, and 401/403 fail-closed handling."""
        self.validate_outbound_url(url)
        self._check_circuit_breaker()

        req_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
        }
        if self._access_token:
            req_headers["Access-Token"] = self._access_token
            req_headers["Authorization"] = f"Bearer {self._access_token}"
        if headers:
            req_headers.update(headers)

        body_bytes: Optional[bytes] = None
        if json_body is not None:
            body_bytes = json.dumps(json_body).encode("utf-8")

        request = urllib.request.Request(url=url, data=body_bytes, headers=req_headers, method=method.upper())

        try:
            if self._http_transport is not None:
                status_code, resp_headers, raw_resp = self._http_transport(request, timeout_seconds)
            else:
                with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                    status_code = int(response.getcode() or 200)
                    resp_headers = {k.lower(): v for k, v in response.info().items()}
                    raw_resp = response.read()
        except urllib.error.HTTPError as http_err:
            status_code = int(http_err.code)
            resp_headers = {k.lower(): v for k, v in (http_err.headers.items() if http_err.headers else [])}
            raw_resp = http_err.read() if http_err.fp else b"{}"

        if status_code in (401, 403):
            self._trigger_fail_closed_downgrade(status_code, "Upstream returned HTTP 401/403")
            raise PermissionPolicyError(
                f"TikTok authentication/authorization error (HTTP {status_code}). Adapter downgraded to DRAFT.",
                code=f"ERR_HTTP_{status_code}_DOWNGRADED",
            )

        if status_code == 429:
            retry_after_hdr = None
            for k, v in resp_headers.items():
                if k.lower() == "retry-after":
                    retry_after_hdr = v
                    break
            backoff = self.calculate_backoff_seconds(attempt=attempt, retry_after_header=retry_after_hdr)
            self.rate_limit_cooldown_until_epoch = time.time() + backoff
            self._record_audit("RATE_LIMIT_429", "COOLDOWN", {"backoff_seconds": backoff})
            raise RateLimitExceededError(
                f"TikTok API rate limit exceeded (HTTP 429). Retry after {backoff}s.",
                retry_after_seconds=backoff,
            )

        if status_code >= 500:
            self.consecutive_5xx_failures += 1
            if self.consecutive_5xx_failures >= self._circuit_breaker_threshold:
                self.circuit_open_until_epoch = time.time() + self._circuit_breaker_cooldown_seconds
                self._record_audit(
                    "CIRCUIT_BREAKER_TRIPPED",
                    "OPEN",
                    {
                        "consecutive_5xx_failures": self.consecutive_5xx_failures,
                        "open_until_epoch": self.circuit_open_until_epoch,
                    },
                )
                raise CircuitBreakerOpenError(
                    f"TikTok upstream failed {self.consecutive_5xx_failures} consecutive times (HTTP {status_code}). Circuit breaker OPEN.",
                    open_until_epoch=self.circuit_open_until_epoch,
                )
            raise TikTokIntegrationError(
                f"TikTok upstream server error (HTTP {status_code})",
                code=f"ERR_UPSTREAM_{status_code}",
            )

        # Reset 5xx counter on any non-5xx response
        self.consecutive_5xx_failures = 0

        if not raw_resp:
            return {}
        return json.loads(raw_resp.decode("utf-8"))

    def _require_capability_for_live_call(self, capability_name: str) -> CapabilityStatus:
        status = self.get_capability_status(capability_name)
        if status == CapabilityStatus.UNAVAILABLE:
            raise PermissionPolicyError(
                f"Capability '{capability_name}' is permanently UNAVAILABLE on TikTok.",
                code="ERR_CAPABILITY_UNAVAILABLE",
            )
        if status == CapabilityStatus.AWAITING_APPROVAL:
            req_scopes = self._manifest["capabilities"][capability_name].get("required_scopes", [])
            missing = [s for s in req_scopes if s not in self._granted_scopes] or req_scopes
            raise ScopeNotApprovedError(capability=capability_name, missing_scopes=missing)
        return status

    # -------------------------------------------------------------------------
    # 12 Canonical Provider-Neutral Interface Methods
    # -------------------------------------------------------------------------

    def get_owned_profile(self) -> ProviderResponse[TikTokProfile]:
        """1. Retrieve the owned @annreveals TikTok Business Account profile."""
        cap_name = "get_owned_profile"
        status = self.get_capability_status(cap_name)
        if status != CapabilityStatus.VERIFIED_ACTIVE:
            return ProviderResponse(
                ok=False,
                capability=cap_name,
                capability_status=status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                error_code="ERR_AWAITING_APPROVAL",
                error_message="TikTok Accounts API v1.3 profile scope is AWAITING_APPROVAL.",
                fallback_action="MANUAL_PROFILE_CONFIG",
            )

        if self.sandbox_mode and self._http_transport is None:
            profile = TikTokProfile(
                business_id=self.business_id,
                handle=self.handle,
                display_name="Ann Reveals | Luxury Fragrance",
                is_business_account=True,
                follower_count=18400,
                likes_count=245000,
                video_count=len(self._sandbox_posts),
                bio_description="Honest UK luxury & niche perfume reviews.",
            )
            return ProviderResponse(
                ok=True,
                capability=cap_name,
                capability_status=status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                data=profile,
            )

        url = (
            "https://business-api.tiktok.com/open_api/v1.3/business/get/"
            f"?business_id={urllib.parse.quote(self.business_id)}"
        )
        payload = self._execute_http_json("GET", url)
        data = payload.get("data", {})
        profile = TikTokProfile(
            business_id=self.business_id,
            handle=str(data.get("username") or self.handle),
            display_name=str(data.get("display_name") or "Ann Reveals"),
            is_business_account=True,
            follower_count=int(data.get("followers_count") or 0),
            likes_count=int(data.get("total_likes") or 0),
            video_count=int(data.get("videos_count") or 0),
            avatar_url=str(data.get("profile_image") or ""),
            bio_description=str(data.get("bio_description") or ""),
        )
        return ProviderResponse(
            ok=True,
            capability=cap_name,
            capability_status=status,
            operational_mode=self.operational_mode,
            connection_badge=self.get_connection_badge(),
            data=profile,
        )

    def get_owned_posts(self, cursor: int = 0, max_count: int = 20) -> ProviderResponse[List[TikTokPost]]:
        """2. List owned videos on @annreveals Business Account (`/open_api/v1.3/business/video/list/`)."""
        cap_name = "get_owned_posts"
        status = self.get_capability_status(cap_name)
        if status != CapabilityStatus.VERIFIED_ACTIVE:
            return ProviderResponse(
                ok=False,
                capability=cap_name,
                capability_status=status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                error_code="ERR_AWAITING_APPROVAL",
                error_message="TikTok video.list scope is AWAITING_APPROVAL (March 20, 2026 Accounts API gate).",
                fallback_action="MANUAL_URL_IMPORT",
            )

        if self.sandbox_mode and self._http_transport is None:
            return ProviderResponse(
                ok=True,
                capability=cap_name,
                capability_status=status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                data=list(self._sandbox_posts[:max_count]),
                metadata={"cursor": cursor, "has_more": False},
            )

        query = urllib.parse.urlencode(
            {"business_id": self.business_id, "cursor": cursor, "max_count": min(max_count, 20)}
        )
        url = f"https://business-api.tiktok.com/open_api/v1.3/business/video/list/?{query}"
        payload = self._execute_http_json("GET", url)
        raw_videos = payload.get("data", {}).get("videos", [])
        posts = [
            TikTokPost(
                video_id=str(v.get("item_id") or v.get("video_id")),
                business_id=self.business_id,
                caption=str(v.get("caption") or ""),
                share_url=str(v.get("share_url") or ""),
                create_time=int(v.get("create_time") or 0),
                comment_count=int(v.get("comments") or 0),
                like_count=int(v.get("likes") or 0),
                view_count=int(v.get("video_views") or 0),
                duration_seconds=int(v.get("duration") or 0),
                is_owned=True,
            )
            for v in raw_videos
        ]
        return ProviderResponse(
            ok=True,
            capability=cap_name,
            capability_status=status,
            operational_mode=self.operational_mode,
            connection_badge=self.get_connection_badge(),
            data=posts,
        )

    def list_owned_comments(
        self,
        video_id: str,
        cursor: int = 0,
        max_count: int = 20,
        include_replies: bool = True,
    ) -> ProviderResponse[List[TikTokComment]]:
        """3. List comments and replies on an owned TikTok video (`/open_api/v1.3/business/comment/list/`)."""
        cap_name = "list_owned_comments"
        status = self.get_capability_status(cap_name)
        if status != CapabilityStatus.VERIFIED_ACTIVE:
            return ProviderResponse(
                ok=False,
                capability=cap_name,
                capability_status=status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                error_code="ERR_AWAITING_APPROVAL",
                error_message="TikTok comment.list scope is AWAITING_APPROVAL under March 20, 2026 Accounts API policy.",
                fallback_action="WEBHOOK_OR_MANUAL_QUEUE",
            )

        if self.sandbox_mode and self._http_transport is None:
            comments = list(self._sandbox_comments.get(video_id, []))
            if not include_replies:
                comments = [c for c in comments if not c.is_reply]
            return ProviderResponse(
                ok=True,
                capability=cap_name,
                capability_status=status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                data=comments[:max_count],
                metadata={"video_id": video_id, "cursor": cursor},
            )

        query = urllib.parse.urlencode(
            {
                "business_id": self.business_id,
                "video_id": video_id,
                "include_replies": "true" if include_replies else "false",
                "cursor": cursor,
                "max_results": min(max_count, 30),
            }
        )
        url = f"https://business-api.tiktok.com/open_api/v1.3/business/comment/list/?{query}"
        payload = self._execute_http_json("GET", url)
        raw_comments = payload.get("data", {}).get("comments", [])
        parsed_comments: List[TikTokComment] = []
        for item in raw_comments:
            uid = str(item.get("user_id") or "")
            uname = str(item.get("username") or "")
            parent_id = item.get("parent_comment_id")
            is_self = bool(uid == self.business_id or uname.lower().lstrip("@") == "annreveals")
            parsed_comments.append(
                TikTokComment(
                    comment_id=str(item.get("comment_id")),
                    video_id=video_id,
                    business_id=self.business_id,
                    text=str(item.get("text") or ""),
                    create_time=int(item.get("create_time") or 0),
                    user_id=uid,
                    username=uname,
                    parent_comment_id=str(parent_id) if parent_id else None,
                    is_reply=bool(parent_id),
                    is_self_author=is_self,
                    status=str(item.get("status") or "PUBLIC"),
                    like_count=int(item.get("likes") or 0),
                )
            )
        return ProviderResponse(
            ok=True,
            capability=cap_name,
            capability_status=status,
            operational_mode=self.operational_mode,
            connection_badge=self.get_connection_badge(),
            data=parsed_comments,
        )

    def reply_to_owned_comment(
        self,
        video_id: str,
        comment_id: str,
        text: str,
        idempotency_key: str,
        strict_write_check: bool = False,
    ) -> ProviderResponse[CommentWriteResult]:
        """4. Reply to an existing comment on an owned TikTok video (`POST /open_api/v1.3/business/comment/reply/`).

        Enforces:
        - Idempotency deduplication (NFR-03, NFR-04).
        - `TIKTOK_WRITE_ENABLED=false` guard (defaults to DRAFT_ONLY or raises `WriteDisabledError` if `strict_write_check=True`).
        - Self-reply loop check (FR-003).
        - 150-character TikTok comment length validation.
        """
        cap_name = "reply_to_owned_comment"
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Reply text cannot be empty")
        if len(clean_text) > MAX_COMMENT_LENGTH_CHARS:
            clean_text = clean_text[:MAX_COMMENT_LENGTH_CHARS]

        # Idempotency check (NFR-03)
        if idempotency_key in self._idempotency_store:
            existing = self._idempotency_store[idempotency_key]
            return ProviderResponse(
                ok=existing.dispatch_state == DispatchState.SENT,
                capability=cap_name,
                capability_status=existing.capability_status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                data=existing,
                metadata={"idempotent_replay": True},
            )

        # Prevent replying to own comment in sandbox fixtures (FR-003)
        for existing_cmt in self._sandbox_comments.get(video_id, []):
            if existing_cmt.comment_id == comment_id and existing_cmt.is_self_author:
                raise PermissionPolicyError(
                    "Self-comment reply loop prevented (FR-003): cannot reply to @annreveals's own comment.",
                    code="ERR_SELF_REPLY_LOOP_PREVENTED",
                )

        status = self.get_capability_status(cap_name)

        # Enforce TIKTOK_WRITE_ENABLED=false or DRAFT mode
        if not self.write_enabled or self.operational_mode != OperationalMode.SAFE_AUTO or status != CapabilityStatus.VERIFIED_ACTIVE:
            if strict_write_check and not self.write_enabled:
                raise WriteDisabledError()
            if strict_write_check and status != CapabilityStatus.VERIFIED_ACTIVE:
                self._require_capability_for_live_call(cap_name)

            draft_result = CommentWriteResult(
                video_id=video_id,
                text=clean_text,
                idempotency_key=idempotency_key,
                dispatch_state=DispatchState.DRAFT_ONLY,
                capability_status=status,
                comment_id=None,
                parent_comment_id=comment_id,
                fallback_copy_text=clean_text,
                audit_note=(
                    "Saved as DRAFT_ONLY: TIKTOK_WRITE_ENABLED is false or capability is AWAITING_APPROVAL."
                ),
            )
            self._idempotency_store[idempotency_key] = draft_result
            self._record_audit("REPLY_SAVED_AS_DRAFT", "DRAFT_ONLY", {"video_id": video_id, "comment_id": comment_id})
            return ProviderResponse(
                ok=True,
                capability=cap_name,
                capability_status=status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                data=draft_result,
                fallback_action="DRAFT_ONLY_ONE_TAP_COPY",
            )

        # Live or Sandbox active write dispatch
        if self.sandbox_mode and self._http_transport is None:
            new_id = f"tt_reply_{len(self._idempotency_store) + 1001}"
            new_comment = TikTokComment(
                comment_id=new_id,
                video_id=video_id,
                business_id=self.business_id,
                text=clean_text,
                create_time=int(time.time()),
                user_id=self.business_id,
                username="annreveals",
                parent_comment_id=comment_id,
                is_reply=True,
                is_self_author=True,
                status="PUBLIC",
                like_count=0,
            )
            self._sandbox_comments.setdefault(video_id, []).append(new_comment)
            sent_result = CommentWriteResult(
                video_id=video_id,
                text=clean_text,
                idempotency_key=idempotency_key,
                dispatch_state=DispatchState.SENT,
                capability_status=status,
                comment_id=new_id,
                parent_comment_id=comment_id,
                audit_note="Dispatched in verified sandbox mode.",
            )
            self._idempotency_store[idempotency_key] = sent_result
            return ProviderResponse(
                ok=True,
                capability=cap_name,
                capability_status=status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                data=sent_result,
            )

        url = "https://business-api.tiktok.com/open_api/v1.3/business/comment/reply/"
        body = {
            "business_id": self.business_id,
            "video_id": video_id,
            "comment_id": comment_id,
            "text": clean_text,
        }
        try:
            payload = self._execute_http_json("POST", url, json_body=body)
        except PermissionPolicyError:
            # 401/403 triggered fail-closed downgrade to DRAFT (NFR-10)
            downgraded_result = CommentWriteResult(
                video_id=video_id,
                text=clean_text,
                idempotency_key=idempotency_key,
                dispatch_state=DispatchState.DRAFT_ONLY,
                capability_status=CapabilityStatus.AWAITING_APPROVAL,
                comment_id=None,
                parent_comment_id=comment_id,
                fallback_copy_text=clean_text,
                audit_note="Auto-downgraded to DRAFT_ONLY after HTTP 401/403 (NFR-10).",
            )
            self._idempotency_store[idempotency_key] = downgraded_result
            return ProviderResponse(
                ok=False,
                capability=cap_name,
                capability_status=CapabilityStatus.AWAITING_APPROVAL,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                data=downgraded_result,
                error_code="ERR_AUTH_DOWNGRADED_TO_DRAFT",
                error_message="TikTok returned 401/403; adapter automatically downgraded to DRAFT mode.",
                fallback_action="RECONNECT_AND_MANUAL_COPY",
            )
        except TimeoutError:
            # NFR-03: Mark as RECONCILE_PENDING on network timeout to prevent duplicate replies
            reconcile_result = CommentWriteResult(
                video_id=video_id,
                text=clean_text,
                idempotency_key=idempotency_key,
                dispatch_state=DispatchState.RECONCILE_PENDING,
                capability_status=status,
                comment_id=None,
                parent_comment_id=comment_id,
                fallback_copy_text=clean_text,
                audit_note="Network timeout during POST; marked RECONCILE_PENDING (NFR-03).",
            )
            self._idempotency_store[idempotency_key] = reconcile_result
            return ProviderResponse(
                ok=False,
                capability=cap_name,
                capability_status=status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                data=reconcile_result,
                error_code="ERR_TIMEOUT_RECONCILE_PENDING",
                error_message="Request timed out; comment state is RECONCILE_PENDING.",
            )

        created_id = str(payload.get("data", {}).get("comment_id") or f"tt_live_{int(time.time())}")
        live_result = CommentWriteResult(
            video_id=video_id,
            text=clean_text,
            idempotency_key=idempotency_key,
            dispatch_state=DispatchState.SENT,
            capability_status=status,
            comment_id=created_id,
            parent_comment_id=comment_id,
            audit_note="Sent via TikTok Accounts API v1.3 /business/comment/reply/.",
        )
        self._idempotency_store[idempotency_key] = live_result
        return ProviderResponse(
            ok=True,
            capability=cap_name,
            capability_status=status,
            operational_mode=self.operational_mode,
            connection_badge=self.get_connection_badge(),
            data=live_result,
        )

    def create_comment_on_owned_post(
        self,
        video_id: str,
        text: str,
        idempotency_key: str,
        is_ownership_declaration: bool = False,
        has_commercial_relationship: bool = False,
    ) -> ProviderResponse[CommentWriteResult]:
        """5. Create a top-level comment on an owned TikTok video (`POST /open_api/v1.3/business/comment/create/`).

        Enforces FR-022 & FR-055 anti-spam ownership comment guard:
        - Never allows claiming "not an ad" when `has_commercial_relationship=True`.
        - Blocks identical repetitive ownership declarations across videos.
        """
        cap_name = "create_comment_on_owned_post"
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Comment text cannot be empty")

        if has_commercial_relationship and "not an ad" in clean_text.lower():
            raise PermissionPolicyError(
                "Policy violation (FR-022/FR-054): Cannot claim 'not an ad' when an affiliate or commercial relationship exists.",
                code="ERR_FALSE_NON_AD_CLAIM",
            )

        if is_ownership_declaration:
            normalized = " ".join(clean_text.lower().split())
            if normalized in self._recent_ownership_comments:
                raise PermissionPolicyError(
                    "Anti-spam ownership comment guard (FR-055): Identical repetitive ownership declaration blocked.",
                    code="ERR_REPETITIVE_OWNERSHIP_COMMENT",
                )
            self._recent_ownership_comments.add(normalized)

        status = self.get_capability_status(cap_name)
        if not self.write_enabled or self.operational_mode != OperationalMode.SAFE_AUTO or status != CapabilityStatus.VERIFIED_ACTIVE:
            draft_res = CommentWriteResult(
                video_id=video_id,
                text=clean_text[:MAX_COMMENT_LENGTH_CHARS],
                idempotency_key=idempotency_key,
                dispatch_state=DispatchState.DRAFT_ONLY,
                capability_status=status,
                fallback_copy_text=clean_text[:MAX_COMMENT_LENGTH_CHARS],
                audit_note="Saved top-level comment as DRAFT_ONLY.",
            )
            self._idempotency_store[idempotency_key] = draft_res
            return ProviderResponse(
                ok=True,
                capability=cap_name,
                capability_status=status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                data=draft_res,
                fallback_action="DRAFT_ONLY_ONE_TAP_COPY",
            )

        if self.sandbox_mode and self._http_transport is None:
            cid = f"tt_top_cmt_{len(self._idempotency_store) + 2001}"
            sent_res = CommentWriteResult(
                video_id=video_id,
                text=clean_text[:MAX_COMMENT_LENGTH_CHARS],
                idempotency_key=idempotency_key,
                dispatch_state=DispatchState.SENT,
                capability_status=status,
                comment_id=cid,
                audit_note="Created top-level comment on owned video in sandbox mode.",
            )
            self._idempotency_store[idempotency_key] = sent_res
            return ProviderResponse(
                ok=True,
                capability=cap_name,
                capability_status=status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                data=sent_res,
            )

        url = "https://business-api.tiktok.com/open_api/v1.3/business/comment/create/"
        payload = self._execute_http_json(
            "POST",
            url,
            json_body={
                "business_id": self.business_id,
                "video_id": video_id,
                "text": clean_text[:MAX_COMMENT_LENGTH_CHARS],
            },
        )
        cid = str(payload.get("data", {}).get("comment_id") or f"tt_top_{int(time.time())}")
        res = CommentWriteResult(
            video_id=video_id,
            text=clean_text[:MAX_COMMENT_LENGTH_CHARS],
            idempotency_key=idempotency_key,
            dispatch_state=DispatchState.SENT,
            capability_status=status,
            comment_id=cid,
            audit_note="Created top-level comment via TikTok Accounts API v1.3.",
        )
        self._idempotency_store[idempotency_key] = res
        return ProviderResponse(
            ok=True,
            capability=cap_name,
            capability_status=status,
            operational_mode=self.operational_mode,
            connection_badge=self.get_connection_badge(),
            data=res,
        )

    def subscribe_to_webhooks(
        self,
        callback_url: str,
        event_types: Optional[List[str]] = None,
    ) -> ProviderResponse[Dict[str, Any]]:
        """6. Subscribe HTTPS callback URL to TikTok Business `comment.update` webhooks."""
        cap_name = "subscribe_to_webhooks"
        parsed_cb = urllib.parse.urlparse(callback_url)
        if parsed_cb.scheme.lower() != "https":
            raise SecurityConfigurationError(
                "Webhook callback_url must use HTTPS",
                code="ERR_WEBHOOK_CALLBACK_INSECURE",
            )
        events = event_types or ["comment.update"]
        status = self.get_capability_status(cap_name)
        if status != CapabilityStatus.VERIFIED_ACTIVE:
            return ProviderResponse(
                ok=False,
                capability=cap_name,
                capability_status=status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                error_code="ERR_AWAITING_APPROVAL",
                error_message="Webhook subscription awaits March 20, 2026 TikTok Accounts API approval.",
                fallback_action="POLLING_RECONCILIATION",
            )

        if self.sandbox_mode and self._http_transport is None:
            return ProviderResponse(
                ok=True,
                capability=cap_name,
                capability_status=status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                data={"subscribed": True, "callback_url": callback_url, "events": events},
            )

        url = "https://business-api.tiktok.com/open_api/v1.3/business/webhook/update/"
        payload = self._execute_http_json(
            "POST",
            url,
            json_body={"business_id": self.business_id, "callback_url": callback_url, "event_list": events},
        )
        return ProviderResponse(
            ok=True,
            capability=cap_name,
            capability_status=status,
            operational_mode=self.operational_mode,
            connection_badge=self.get_connection_badge(),
            data=payload.get("data", {"subscribed": True, "callback_url": callback_url, "events": events}),
        )

    def refresh_auth(self, refresh_token: str, client_key: str = "sandbox_key") -> ProviderResponse[TokenGrant]:
        """7. Refresh OAuth 2.0 token via `https://open.tiktokapis.com/v2/oauth/token/` and inspect live scopes."""
        cap_name = "refresh_auth"
        if not refresh_token or not refresh_token.strip():
            raise ValueError("refresh_token must be non-empty")

        if self.sandbox_mode and self._http_transport is None:
            scopes = sorted(self._granted_scopes) if self._granted_scopes else [
                "user.info.basic",
                "video.list",
                "comment.list",
                "comment.list.manage",
            ]
            self._granted_scopes = set(scopes)
            self._auth_revoked_or_expired = False
            grant = TokenGrant(
                access_token="sandbox_refreshed_access_token",
                refresh_token="sandbox_refreshed_refresh_token",
                open_id=self.business_id,
                expires_in=86400,
                granted_scopes=scopes,
                badge=self.get_connection_badge(),
                write_scope_verified="comment.list.manage" in self._granted_scopes,
                read_scope_verified="comment.list" in self._granted_scopes,
            )
            return ProviderResponse(
                ok=True,
                capability=cap_name,
                capability_status=CapabilityStatus.VERIFIED_ACTIVE,
                operational_mode=self.operational_mode,
                connection_badge=grant.badge,
                data=grant,
            )

        url = "https://open.tiktokapis.com/v2/oauth/token/"
        payload = self._execute_http_json(
            "POST",
            url,
            json_body={
                "client_key": client_key,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        raw_scope_str = str(payload.get("scope") or "")
        scopes = [s.strip() for s in raw_scope_str.split(",") if s.strip()]
        self._access_token = str(payload.get("access_token") or "")
        self._granted_scopes = set(scopes)
        self._auth_revoked_or_expired = False

        grant = TokenGrant(
            access_token=self._access_token,
            refresh_token=str(payload.get("refresh_token") or refresh_token),
            open_id=str(payload.get("open_id") or self.business_id),
            expires_in=int(payload.get("expires_in") or 86400),
            granted_scopes=scopes,
            badge=self.get_connection_badge(),
            write_scope_verified="comment.list.manage" in self._granted_scopes and self.accounts_api_approved,
            read_scope_verified="comment.list" in self._granted_scopes and self.accounts_api_approved,
        )
        return ProviderResponse(
            ok=True,
            capability=cap_name,
            capability_status=CapabilityStatus.VERIFIED_ACTIVE,
            operational_mode=self.operational_mode,
            connection_badge=grant.badge,
            data=grant,
        )

    def publish_post(self, request: PublishPostRequest) -> ProviderResponse[PublishPostResult]:
        """8. Publish or upload a video to TikTok (`https://open.tiktokapis.com/v2/post/publish/video/init/`).

        Enforces FR-021, FR-026, FR-053, FR-055:
        - Self-purchase provenance never automatically turns on paid partnership disclosure if there is no commercial incentive.
        - Commercial incentives (`has_commercial_incentive=True`) require enabling `brand_content_toggle` or `brand_organic_toggle`.
        """
        cap_name = "publish_post"
        if request.has_commercial_incentive and not (
            request.brand_content_toggle or request.brand_organic_toggle
        ):
            raise PermissionPolicyError(
                "TikTok Commercial Content Disclosure Policy (FR-026/FR-053): Commercial or affiliate posts must enable brand_content_toggle or brand_organic_toggle.",
                code="ERR_MISSING_COMMERCIAL_DISCLOSURE_TOGGLE",
            )

        if request.self_purchased and not request.has_commercial_incentive and request.brand_content_toggle:
            raise PermissionPolicyError(
                "Provenance vs Commercial Rule (FR-055): Do not mark a purely self-purchased non-commercial review as Paid Partnership.",
                code="ERR_FALSE_PAID_PARTNERSHIP_TOGGLE",
            )

        status = self.get_capability_status(cap_name)
        if not self.write_enabled or status != CapabilityStatus.VERIFIED_ACTIVE:
            res = PublishPostResult(
                publish_id="draft_local_only",
                status="DRAFT_PACKAGE_READY",
                dispatch_state=DispatchState.DRAFT_ONLY,
                capability_status=status,
                fallback_caption=request.caption,
                commercial_disclosure_applied=bool(request.brand_content_toggle or request.brand_organic_toggle),
                audit_note="Prepared for One-Tap Copy & Open TikTok App (FR-048).",
            )
            return ProviderResponse(
                ok=True,
                capability=cap_name,
                capability_status=status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                data=res,
                fallback_action="ONE_TAP_COPY_AND_OPEN_APP",
            )

        if self.sandbox_mode and self._http_transport is None:
            res = PublishPostResult(
                publish_id="v_pub_sandbox_001",
                status="PROCESSING_UPLOAD",
                dispatch_state=DispatchState.SENT,
                capability_status=status,
                fallback_caption=request.caption,
                commercial_disclosure_applied=bool(request.brand_content_toggle or request.brand_organic_toggle),
                audit_note="Initialized TikTok Content Posting API upload in sandbox mode.",
            )
            return ProviderResponse(
                ok=True,
                capability=cap_name,
                capability_status=status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                data=res,
            )

        endpoint = (
            "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
            if request.publish_to_draft_inbox
            else "https://open.tiktokapis.com/v2/post/publish/video/init/"
        )
        payload = self._execute_http_json(
            "POST",
            endpoint,
            json_body={
                "post_info": {
                    "title": request.caption,
                    "privacy_level": request.privacy_level,
                    "disable_comment": request.disable_comment,
                    "brand_content_toggle": request.brand_content_toggle,
                    "brand_organic_toggle": request.brand_organic_toggle,
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "video_url": request.video_url,
                },
            },
        )
        pub_id = str(payload.get("data", {}).get("publish_id") or "v_pub_live")
        res = PublishPostResult(
            publish_id=pub_id,
            status="PROCESSING_UPLOAD",
            dispatch_state=DispatchState.SENT,
            capability_status=status,
            fallback_caption=request.caption,
            commercial_disclosure_applied=bool(request.brand_content_toggle or request.brand_organic_toggle),
        )
        return ProviderResponse(
            ok=True,
            capability=cap_name,
            capability_status=status,
            operational_mode=self.operational_mode,
            connection_badge=self.get_connection_badge(),
            data=res,
        )

    def get_post_publication_status(self, publish_id: str) -> ProviderResponse[PublishPostResult]:
        """9. Fetch asynchronous publication status from `https://open.tiktokapis.com/v2/post/publish/status/fetch/`."""
        cap_name = "get_post_publication_status"
        status = self.get_capability_status(cap_name)
        if status != CapabilityStatus.VERIFIED_ACTIVE:
            return ProviderResponse(
                ok=False,
                capability=cap_name,
                capability_status=status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                error_code="ERR_AWAITING_APPROVAL",
                error_message="Content Posting API status check is AWAITING_APPROVAL.",
                fallback_action="MANUAL_STATUS_CHECK",
            )

        if self.sandbox_mode and self._http_transport is None:
            res = PublishPostResult(
                publish_id=publish_id,
                status="PUBLISH_COMPLETE",
                dispatch_state=DispatchState.SENT,
                capability_status=status,
                share_url=f"https://www.tiktok.com/@annreveals/video/{publish_id}",
            )
            return ProviderResponse(
                ok=True,
                capability=cap_name,
                capability_status=status,
                operational_mode=self.operational_mode,
                connection_badge=self.get_connection_badge(),
                data=res,
            )

        url = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
        payload = self._execute_http_json("POST", url, json_body={"publish_id": publish_id})
        pub_status = str(payload.get("data", {}).get("status") or "PROCESSING_UPLOAD")
        res = PublishPostResult(
            publish_id=publish_id,
            status=pub_status,
            dispatch_state=DispatchState.SENT,
            capability_status=status,
        )
        return ProviderResponse(
            ok=True,
            capability=cap_name,
            capability_status=status,
            operational_mode=self.operational_mode,
            connection_badge=self.get_connection_badge(),
            data=res,
        )

    def get_inbox_messages(self, cursor: int = 0) -> ProviderResponse[List[Dict[str, Any]]]:
        """10. TikTok Business Messaging API is unavailable in v1; truthfully returns UNAVAILABLE."""
        return ProviderResponse(
            ok=False,
            capability="get_inbox_messages",
            capability_status=CapabilityStatus.UNAVAILABLE,
            operational_mode=self.operational_mode,
            connection_badge=self.get_connection_badge(),
            error_code="ERR_CAPABILITY_UNAVAILABLE",
            error_message="TikTok Business Direct Messaging API is UNAVAILABLE in v1; use native TikTok inbox.",
            fallback_action="NATIVE_TIKTOK_INBOX",
        )

    def get_following_posts(self, creator_handle: str = "") -> ProviderResponse[List[TikTokPost]]:
        """11. PERMANENTLY PROHIBITED: TikTok provides no official API to scrape following feeds (FR-012)."""
        self._record_audit(
            action="BLOCKED_FOLLOWING_FEED_SCRAPE",
            status="DENIED",
            details={"creator_handle": creator_handle},
        )
        raise PermissionPolicyError(
            "Capability 'get_following_posts' is permanently UNAVAILABLE on TikTok. "
            "Follow-list scraping is strictly prohibited (FR-012). Use owner-curated creator URLs.",
            code="ERR_THIRD_PARTY_INTERACTION_PROHIBITED",
        )

    def comment_on_nonowned_post(
        self,
        target_video_id: str,
        text: str,
        owner_business_id: Optional[str] = None,
    ) -> ProviderResponse[CommentWriteResult]:
        """12. PERMANENTLY PROHIBITED: Automated commenting on third-party/friends' posts is forbidden (FR-014, FR-016)."""
        self._record_audit(
            action="BLOCKED_THIRD_PARTY_AUTOCOMMENT",
            status="DENIED",
            details={"target_video_id": target_video_id, "owner_business_id": owner_business_id},
        )
        raise PermissionPolicyError(
            "Capability 'comment_on_nonowned_post' is permanently UNAVAILABLE. "
            "Automated commenting on third-party or friends' TikTok posts is strictly prohibited. "
            "Use One-Tap Copy Draft + Open Native TikTok App (FR-014).",
            code="ERR_THIRD_PARTY_INTERACTION_PROHIBITED",
        )
