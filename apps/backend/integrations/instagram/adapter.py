"""Production Meta / Instagram Platform Adapter for `@annreveals` (`ARAIM` v4.0).

Implements the provider-neutral interface using ONLY Python 3.9+ standard library:
- `get_owned_profile`
- `get_owned_posts`
- `list_owned_comments`
- `reply_to_owned_comment`
- `create_comment_on_owned_post`
- `subscribe_to_webhooks`
- `refresh_auth`
- `get_post_publication_status`
- `publish_post`
- `get_inbox_messages`
- `get_following_posts` (permanently blocked per Meta Platform rules)
- `comment_on_nonowned_post` (permanently blocked per Meta Platform rules)

Enforces:
- `INSTAGRAM_WRITE_ENABLED=false` by default until live scope & pilot verification pass.
- Self-reply loop prevention (never reply to `@annreveals` own comments).
- Ambiguous timeout reconciliation (`RECONCILE_PENDING` check against existing replies/comments before retry so duplicates are never posted).
- 401/403 token revocation fail-closed transition to `Needs reconnect` (`NEEDS_RECONNECT`) and `DRAFT` mode.
- Rate-limit backoff and `Retry-After` compliance.
"""

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .models import (
    AuthRoute,
    AutomationMode,
    CommentDispatchRecord,
    ConnectionStatus,
    DispatchState,
    InstagramAmbiguousTimeoutError,
    InstagramAuthError,
    InstagramComment,
    InstagramError,
    InstagramPost,
    InstagramProfile,
    InstagramRateLimitError,
    PaginatedResult,
    SelfReplyForbiddenError,
    UnsupportedCapabilityError,
    WriteGateDisabledError,
)

# Type alias for injectable HTTP transport: (method, url, headers, body_bytes, timeout) -> (status_code, response_headers, response_body_bytes)
HttpTransportCallable = Callable[
    [str, str, Dict[str, str], Optional[bytes], float],
    Tuple[int, Dict[str, str], bytes],
]


def _normalize_text(text: str) -> str:
    """Normalize whitespace and casing for duplicate/reconciliation comparison."""
    return " ".join((text or "").strip().split()).lower()


class InstagramAdapter:
    """Official Meta / Instagram Platform Adapter (`Instagram API with Instagram Login`)."""

    GRAPH_INSTAGRAM_BASE = "https://graph.instagram.com/v21.0"
    GRAPH_FACEBOOK_BASE = "https://graph.facebook.com/v21.0"
    REQUIRED_WRITE_SCOPE = "instagram_business_manage_comments"
    REQUIRED_READ_SCOPE = "instagram_business_basic"

    def __init__(
        self,
        access_token: Optional[str] = None,
        owner_ig_user_id: str = "17841400008460056",
        owner_username: str = "annreveals",
        granted_scopes: Optional[List[str]] = None,
        write_enabled: Optional[bool] = None,
        automation_mode: AutomationMode = AutomationMode.DRAFT,
        auth_route: AuthRoute = AuthRoute.INSTAGRAM_LOGIN,
        sandbox_mode: bool = False,
        http_transport: Optional[HttpTransportCallable] = None,
        request_timeout_seconds: float = 10.0,
    ) -> None:
        self.access_token = access_token
        self.owner_ig_user_id = str(owner_ig_user_id).strip()
        self.owner_username = owner_username.strip().lstrip("@").lower()
        self.granted_scopes: Set[str] = set(granted_scopes or [])
        self.auth_route = auth_route
        self.sandbox_mode = sandbox_mode
        self._http_transport = http_transport or self._default_urllib_transport
        self.request_timeout_seconds = request_timeout_seconds

        # DefaultINSTAGRAM_WRITE_ENABLED to false per PRD Section 1 & NFR-09
        if write_enabled is None:
            env_val = os.environ.get("INSTAGRAM_WRITE_ENABLED", "false").strip().lower()
            self.write_enabled = env_val in {"1", "true", "yes"}
        else:
            self.write_enabled = bool(write_enabled)

        # THIRD_PARTY_AUTOCOMMENT is permanently false on Instagram
        self.third_party_autocomment = False
        self.automation_mode = automation_mode
        self.emergency_stop = False

        # Determine initial truthful connection status (FR-043)
        self.connection_status = self._compute_connection_status()

        # Idempotency & RECONCILE_PENDING state store: idempotency_key -> CommentDispatchRecord
        self._dispatch_records: Dict[str, CommentDispatchRecord] = {}
        # Recent first-party ownership comments for anti-spam uniqueness check (FR-055)
        self._recent_ownership_comments: List[str] = []
        # Known comment metadata cache (comment_id -> InstagramComment) for self-reply loop checks
        self._known_comments: Dict[str, InstagramComment] = {}

        # Built-in deterministic sandbox state for local testing & contract verification
        self._sandbox_posts: Dict[str, InstagramPost] = {}
        self._sandbox_comments_by_post: Dict[str, List[InstagramComment]] = {}
        self._sandbox_replies_by_comment: Dict[str, List[InstagramComment]] = {}
        if self.sandbox_mode:
            self._seed_sandbox_fixtures()

    # ------------------------------------------------------------------
    # Connection Status & Fail-Closed Governance
    # ------------------------------------------------------------------

    def _compute_connection_status(self) -> ConnectionStatus:
        if not self.access_token:
            return ConnectionStatus.NOT_CONNECTED
        if self.REQUIRED_READ_SCOPE not in self.granted_scopes and "instagram_basic" not in self.granted_scopes:
            return ConnectionStatus.AWAITING_REVIEW
        has_write_scope = (
            self.REQUIRED_WRITE_SCOPE in self.granted_scopes
            or "instagram_manage_comments" in self.granted_scopes
        )
        if has_write_scope and self.write_enabled and not self.emergency_stop:
            return ConnectionStatus.LIVE_CAN_REPLY
        return ConnectionStatus.CONNECTED_READ_ONLY

    def _trigger_auth_fail_safe(self, reason: str, status_code: int, error_code: Optional[int] = None) -> None:
        """Automatic fail-closed downgrade to NEEDS_RECONNECT and DRAFT on 401/403 (NFR-10)."""
        self.connection_status = ConnectionStatus.NEEDS_RECONNECT
        self.automation_mode = AutomationMode.DRAFT
        self.write_enabled = False
        raise InstagramAuthError(
            f"Instagram authentication/permission failure ({reason}). "
            f"Transitioned to '{self.connection_status.value}' and mode='{self.automation_mode.value}'.",
            status_code=status_code,
            error_code=error_code,
        )

    def _assert_write_permitted(self) -> None:
        """Enforce write gate, emergency kill-switch, and scope verification before any outward POST."""
        if self.emergency_stop:
            raise WriteGateDisabledError(
                "Universal EMERGENCY STOP is active; all outgoing Instagram writes are halted."
            )
        if self.connection_status == ConnectionStatus.NEEDS_RECONNECT:
            raise InstagramAuthError(
                "Instagram connection requires reconnect; outgoing writes are blocked.",
                status_code=401,
            )
        if not self.access_token:
            raise WriteGateDisabledError(
                "Cannot perform write operation: Instagram account is Not connected (DRAFT_ONLY)."
            )
        has_write_scope = (
            self.REQUIRED_WRITE_SCOPE in self.granted_scopes
            or "instagram_manage_comments" in self.granted_scopes
        )
        if not has_write_scope:
            raise WriteGateDisabledError(
                f"Cannot perform write operation: scope '{self.REQUIRED_WRITE_SCOPE}' is not granted."
            )
        if not self.write_enabled:
            raise WriteGateDisabledError(
                "INSTAGRAM_WRITE_ENABLED is false (Draft-only mode). Outward comment dispatch is blocked."
            )
        if self.automation_mode == AutomationMode.OFF:
            raise WriteGateDisabledError("Instagram automation mode is OFF.")

    def is_self_user(self, author_id: Optional[str], author_username: Optional[str]) -> bool:
        """Return True if author matches `@annreveals` owner ID or handle."""
        if author_id and self.owner_ig_user_id and str(author_id).strip() == self.owner_ig_user_id:
            return True
        if author_username:
            clean = author_username.strip().lstrip("@").lower()
            if clean == self.owner_username:
                return True
        return False

    # ------------------------------------------------------------------
    # Sandbox Fixtures
    # ------------------------------------------------------------------

    def _seed_sandbox_fixtures(self) -> None:
        post_id = "18029910293847561"
        self._sandbox_posts[post_id] = InstagramPost(
            post_id=post_id,
            caption="Wearing Matiere Premiere Vanilla Powder for 8 hours in London rain. Purchased with my own money. These are my personal impressions.",
            media_type="VIDEO",
            media_product_type="REELS",
            permalink="https://www.instagram.com/reel/C9xYz123AbC/",
            timestamp="2026-10-26T18:30:00+0000",
            like_count=642,
            comments_count=2,
            owner_id=self.owner_ig_user_id,
        )
        viewer_comment = InstagramComment(
            comment_id="17918273645019283",
            post_id=post_id,
            text="How many sprays did you use for that 8-hour wear test?",
            author_id="901283746501928",
            author_username="scentlover_uk",
            timestamp="2026-10-27T09:14:22+0000",
            is_self=False,
        )
        owner_comment = InstagramComment(
            comment_id="17918273645099999",
            post_id=post_id,
            text="Notes breakdown: coconut powder, Palo Santo, Madagascar vanilla, white musk.",
            author_id=self.owner_ig_user_id,
            author_username=self.owner_username,
            timestamp="2026-10-26T18:32:00+0000",
            is_self=True,
        )
        self._sandbox_comments_by_post[post_id] = [viewer_comment, owner_comment]
        self._sandbox_replies_by_comment[viewer_comment.comment_id] = []
        self._known_comments[viewer_comment.comment_id] = viewer_comment
        self._known_comments[owner_comment.comment_id] = owner_comment

    # ------------------------------------------------------------------
    # Low-Level HTTP Transport & Error Handling
    # ------------------------------------------------------------------

    @property
    def _base_url(self) -> str:
        if self.auth_route == AuthRoute.FACEBOOK_LOGIN:
            return self.GRAPH_FACEBOOK_BASE
        return self.GRAPH_INSTAGRAM_BASE

    @staticmethod
    def _default_urllib_transport(
        method: str,
        url: str,
        headers: Dict[str, str],
        body_bytes: Optional[bytes],
        timeout: float,
    ) -> Tuple[int, Dict[str, str], bytes]:
        req = urllib.request.Request(url=url, data=body_bytes, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.getcode()
                resp_headers = {k.lower(): v for k, v in resp.headers.items()}
                return status, resp_headers, resp.read()
        except urllib.error.HTTPError as http_err:
            resp_headers = {k.lower(): v for k, v in (http_err.headers.items() if http_err.headers else [])}
            err_body = http_err.read() if http_err.fp else b"{}"
            return http_err.code, resp_headers, err_body

    def _request_json(
        self,
        method: str,
        path: str,
        query_params: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        params = dict(query_params or {})
        url = f"{self._base_url}/{path.lstrip('/')}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"

        headers: Dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": "AnnRevealsAIManager/4.0 (AgentBravo; +https://github.com/atiffhussainkhan/BotsForAnnProject)",
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        body_bytes: Optional[bytes] = None
        if json_body is not None:
            headers["Content-Type"] = "application/json; charset=utf-8"
            body_bytes = json.dumps(json_body).encode("utf-8")

        try:
            status_code, resp_headers, raw_bytes = self._http_transport(
                method, url, headers, body_bytes, self.request_timeout_seconds
            )
        except TimeoutError as exc:
            raise InstagramAmbiguousTimeoutError(
                f"Transport timeout during {method} {path}: {exc}"
            ) from exc
        except urllib.error.URLError as exc:
            raise InstagramAmbiguousTimeoutError(
                f"Ambiguous transport error during {method} {path}: {exc}"
            ) from exc

        try:
            parsed: Dict[str, Any] = json.loads(raw_bytes.decode("utf-8")) if raw_bytes else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed = {}

        if 200 <= status_code < 300:
            return parsed

        error_obj: Dict[str, Any] = parsed.get("error") if isinstance(parsed.get("error"), dict) else {}
        err_code = error_obj.get("code")
        err_subcode = error_obj.get("error_subcode")
        err_msg = str(error_obj.get("message") or f"HTTP {status_code} from Instagram Graph API")

        # 1. Ambiguous 502/503/504 gateway failure on POST
        if status_code in {502, 503, 504}:
            raise InstagramAmbiguousTimeoutError(
                f"Gateway timeout ({status_code}) on {method} {path}: {err_msg}",
                status_code=status_code,
            )

        # 2. Token revocation / expiration / missing permission -> Fail-closed NFR-10
        if status_code in {401, 403} or err_code in {190, 10, 200}:
            self._trigger_auth_fail_safe(err_msg, status_code=status_code, error_code=err_code)

        # 3. Rate limit (HTTP 429 or Meta error codes 4, 17, 32, 613)
        if status_code == 429 or err_code in {4, 17, 32, 613}:
            retry_after_raw = resp_headers.get("retry-after", "30")
            try:
                retry_after = max(1, int(retry_after_raw))
            except ValueError:
                retry_after = 30
            raise InstagramRateLimitError(
                f"Instagram Graph API rate limit reached: {err_msg}",
                retry_after_seconds=retry_after,
                status_code=status_code,
                error_code=err_code,
            )

        # 4. Meta policy/spam block (error code 368) -> downgrade to DRAFT
        if err_code == 368:
            self.automation_mode = AutomationMode.DRAFT
            self.write_enabled = False
            raise InstagramError(
                f"Meta policy block (code 368): {err_msg}. Downgraded to DRAFT mode.",
                status_code=status_code,
                error_code=err_code,
                error_subcode=err_subcode,
            )

        raise InstagramError(
            err_msg,
            status_code=status_code,
            error_code=err_code,
            error_subcode=err_subcode,
        )

    # ------------------------------------------------------------------
    # Provider-Neutral Interface Implementation (12 Required Methods)
    # ------------------------------------------------------------------

    def get_owned_profile(self) -> InstagramProfile:
        """Fetch `@annreveals` professional profile metadata (`GET /v21.0/me`)."""
        if self.sandbox_mode:
            return InstagramProfile(
                ig_user_id=self.owner_ig_user_id,
                username=self.owner_username,
                name="Ann Reveals | Fragrance & Perfumes",
                account_type="MEDIA_CREATOR",
                followers_count=14820,
                follows_count=312,
                media_count=len(self._sandbox_posts),
            )

        data = self._request_json(
            "GET",
            "/me",
            query_params={
                "fields": "id,user_id,username,name,account_type,profile_picture_url,followers_count,follows_count,media_count"
            },
        )
        ig_uid = str(data.get("user_id") or data.get("id") or self.owner_ig_user_id)
        username = str(data.get("username") or self.owner_username)
        self.owner_ig_user_id = ig_uid
        self.owner_username = username.strip().lstrip("@").lower()
        return InstagramProfile(
            ig_user_id=ig_uid,
            username=username,
            name=str(data.get("name") or ""),
            account_type=str(data.get("account_type") or "MEDIA_CREATOR"),
            followers_count=int(data.get("followers_count", 0) or 0),
            follows_count=int(data.get("follows_count", 0) or 0),
            media_count=int(data.get("media_count", 0) or 0),
            profile_picture_url=data.get("profile_picture_url"),
            raw=data,
        )

    def get_owned_posts(
        self,
        cursor: Optional[str] = None,
        limit: int = 25,
    ) -> PaginatedResult:
        """List owned Reels and Posts (`GET /v21.0/{ig-user-id}/media`)."""
        if self.sandbox_mode:
            items = list(self._sandbox_posts.values())[:limit]
            return PaginatedResult(items=items, next_cursor=None, has_more=False)

        params: Dict[str, str] = {
            "fields": "id,caption,media_type,media_product_type,media_url,permalink,timestamp,like_count,comments_count",
            "limit": str(limit),
        }
        if cursor:
            params["after"] = cursor

        data = self._request_json("GET", f"/{self.owner_ig_user_id}/media", query_params=params)
        posts: List[InstagramPost] = []
        for item in data.get("data", []):
            posts.append(
                InstagramPost(
                    post_id=str(item.get("id")),
                    caption=str(item.get("caption") or ""),
                    media_type=str(item.get("media_type") or "VIDEO"),
                    media_product_type=str(item.get("media_product_type") or "REELS"),
                    media_url=item.get("media_url"),
                    permalink=str(item.get("permalink") or ""),
                    timestamp=str(item.get("timestamp") or ""),
                    like_count=int(item.get("like_count", 0) or 0),
                    comments_count=int(item.get("comments_count", 0) or 0),
                    owner_id=self.owner_ig_user_id,
                    raw=item,
                )
            )
        next_cursor = data.get("paging", {}).get("cursors", {}).get("after")
        has_more = bool(next_cursor and data.get("paging", {}).get("next"))
        return PaginatedResult(items=posts, next_cursor=next_cursor, has_more=has_more)

    def list_owned_comments(
        self,
        post_id: str,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> PaginatedResult:
        """List comments on an owned post (`GET /v21.0/{ig-media-id}/comments`)."""
        if self.sandbox_mode:
            comments = list(self._sandbox_comments_by_post.get(post_id, []))
            for c in comments:
                self._known_comments[c.comment_id] = c
            return PaginatedResult(items=comments, next_cursor=None, has_more=False)

        params: Dict[str, str] = {
            "fields": "id,text,timestamp,username,from,parent_id,hidden,like_count",
            "limit": str(limit),
        }
        if cursor:
            params["after"] = cursor

        data = self._request_json("GET", f"/{post_id}/comments", query_params=params)
        comments = self._parse_comment_list(data.get("data", []), post_id=post_id)
        next_cursor = data.get("paging", {}).get("cursors", {}).get("after")
        has_more = bool(next_cursor and data.get("paging", {}).get("next"))
        return PaginatedResult(items=comments, next_cursor=next_cursor, has_more=has_more)

    def list_comment_replies(self, comment_id: str, post_id: str = "") -> List[InstagramComment]:
        """List nested replies on a specific comment (`GET /v21.0/{ig-comment-id}/replies`)."""
        if self.sandbox_mode:
            return list(self._sandbox_replies_by_comment.get(comment_id, []))

        data = self._request_json(
            "GET",
            f"/{comment_id}/replies",
            query_params={"fields": "id,text,timestamp,username,from,parent_id,hidden,like_count"},
        )
        return self._parse_comment_list(
            data.get("data", []),
            post_id=post_id,
            default_parent_id=comment_id,
        )

    def _parse_comment_list(
        self,
        raw_items: List[Dict[str, Any]],
        post_id: str,
        default_parent_id: Optional[str] = None,
    ) -> List[InstagramComment]:
        results: List[InstagramComment] = []
        for item in raw_items:
            cid = str(item.get("id") or "")
            from_obj = item.get("from") or {}
            author_id = str(from_obj.get("id") or "")
            author_username = str(from_obj.get("username") or item.get("username") or "")
            parent_id = item.get("parent_id") or default_parent_id
            is_self = self.is_self_user(author_id, author_username)
            comment = InstagramComment(
                comment_id=cid,
                post_id=post_id,
                text=str(item.get("text") or ""),
                author_id=author_id,
                author_username=author_username,
                timestamp=str(item.get("timestamp") or ""),
                parent_id=str(parent_id) if parent_id else None,
                hidden=bool(item.get("hidden", False)),
                like_count=int(item.get("like_count", 0) or 0),
                is_self=is_self,
                raw=item,
            )
            self._known_comments[cid] = comment
            results.append(comment)
        return results

    def reply_to_owned_comment(
        self,
        comment_id: str,
        message: str,
        idempotency_key: Optional[str] = None,
        target_comment_author_id: Optional[str] = None,
        target_comment_author_username: Optional[str] = None,
    ) -> CommentDispatchRecord:
        """Reply to a viewer comment on an owned post (`POST /v21.0/{ig-comment-id}/replies`).

        Guarantees:
        1. Blocks self-replies (`@annreveals` never replies to her own comment).
        2. Blocks writes when `INSTAGRAM_WRITE_ENABLED=false`.
        3. Reconciles `RECONCILE_PENDING` attempts via `GET /{ig-comment-id}/replies` before retrying.
        """
        clean_message = (message or "").strip()
        if not clean_message:
            raise ValueError("Reply message cannot be empty.")

        # 1. Check self-reply loop prevention (FR-003)
        known = self._known_comments.get(comment_id)
        author_id = target_comment_author_id or (known.author_id if known else None)
        author_username = target_comment_author_username or (known.author_username if known else None)
        if (known and known.is_self) or self.is_self_user(author_id, author_username):
            raise SelfReplyForbiddenError(
                f"Loop prevention (FR-003): Refusing to reply to comment '{comment_id}' authored by @{self.owner_username}."
            )

        # 2. Check write gate
        self._assert_write_permitted()

        idem_key = idempotency_key or hashlib.sha256(
            f"ig_reply:{comment_id}:{_normalize_text(clean_message)}".encode("utf-8")
        ).hexdigest()

        existing_record = self._dispatch_records.get(idem_key)
        if existing_record and existing_record.state in {DispatchState.SENT, DispatchState.SENT_RECONCILED}:
            return existing_record

        # 3. If previous attempt timed out (RECONCILE_PENDING), reconcile against existing replies BEFORE retry
        if existing_record and existing_record.state == DispatchState.RECONCILE_PENDING:
            reconciled_id = self._reconcile_comment_reply(comment_id, clean_message)
            if reconciled_id:
                existing_record.state = DispatchState.SENT_RECONCILED
                existing_record.external_comment_id = reconciled_id
                existing_record.reconciled_from_existing = True
                existing_record.updated_at = time.time()
                return existing_record

        record = existing_record or CommentDispatchRecord(
            idempotency_key=idem_key,
            target_id=comment_id,
            target_type="comment_reply",
            message=clean_message,
            state=DispatchState.IN_FLIGHT,
        )
        record.state = DispatchState.IN_FLIGHT
        record.attempts += 1
        record.updated_at = time.time()
        self._dispatch_records[idem_key] = record

        if self.sandbox_mode:
            new_id = f"17999000{len(self._known_comments) + 1:06d}"
            reply_obj = InstagramComment(
                comment_id=new_id,
                post_id=known.post_id if known else "",
                text=clean_message,
                author_id=self.owner_ig_user_id,
                author_username=self.owner_username,
                timestamp="2026-10-27T13:05:00+0000",
                parent_id=comment_id,
                is_self=True,
            )
            self._sandbox_replies_by_comment.setdefault(comment_id, []).append(reply_obj)
            self._known_comments[new_id] = reply_obj
            record.state = DispatchState.SENT
            record.external_comment_id = new_id
            record.updated_at = time.time()
            return record

        try:
            resp = self._request_json(
                "POST",
                f"/{comment_id}/replies",
                json_body={"message": clean_message},
            )
            ext_id = str(resp.get("id") or "")
            record.state = DispatchState.SENT
            record.external_comment_id = ext_id
            record.updated_at = time.time()
            return record
        except InstagramAmbiguousTimeoutError as exc:
            record.state = DispatchState.RECONCILE_PENDING
            record.last_error = str(exc)
            record.updated_at = time.time()
            raise

    def _reconcile_comment_reply(self, comment_id: str, expected_message: str) -> Optional[str]:
        """Inspect `GET /{ig-comment-id}/replies` to check if `@annreveals` reply already landed."""
        expected_norm = _normalize_text(expected_message)
        replies = self.list_comment_replies(comment_id)
        for reply in replies:
            if reply.is_self and _normalize_text(reply.text) == expected_norm:
                return reply.comment_id
        return None

    def create_comment_on_owned_post(
        self,
        post_id: str,
        message: str,
        idempotency_key: Optional[str] = None,
    ) -> CommentDispatchRecord:
        """Create a top-level comment on an owned post (`POST /v21.0/{ig-media-id}/comments`).

        Enforces:
        - Write gate (`INSTAGRAM_WRITE_ENABLED=true`).
        - Anti-spam ownership comment uniqueness guard (`FR-055`).
        - `RECONCILE_PENDING` timeout reconciliation before retry.
        """
        clean_message = (message or "").strip()
        if not clean_message:
            raise ValueError("Comment message cannot be empty.")

        self._assert_write_permitted()

        norm_msg = _normalize_text(clean_message)
        if norm_msg in self._recent_ownership_comments:
            raise InstagramError(
                "Anti-spam ownership comment guard (FR-055): Refusing to post an identical boilerplate declaration across consecutive posts."
            )

        idem_key = idempotency_key or hashlib.sha256(
            f"ig_post_comment:{post_id}:{norm_msg}".encode("utf-8")
        ).hexdigest()

        existing_record = self._dispatch_records.get(idem_key)
        if existing_record and existing_record.state in {DispatchState.SENT, DispatchState.SENT_RECONCILED}:
            return existing_record

        if existing_record and existing_record.state == DispatchState.RECONCILE_PENDING:
            reconciled_id = self._reconcile_post_comment(post_id, clean_message)
            if reconciled_id:
                existing_record.state = DispatchState.SENT_RECONCILED
                existing_record.external_comment_id = reconciled_id
                existing_record.reconciled_from_existing = True
                existing_record.updated_at = time.time()
                self._recent_ownership_comments.append(norm_msg)
                return existing_record

        record = existing_record or CommentDispatchRecord(
            idempotency_key=idem_key,
            target_id=post_id,
            target_type="post_comment",
            message=clean_message,
            state=DispatchState.IN_FLIGHT,
        )
        record.state = DispatchState.IN_FLIGHT
        record.attempts += 1
        record.updated_at = time.time()
        self._dispatch_records[idem_key] = record

        if self.sandbox_mode:
            new_id = f"17999500{len(self._known_comments) + 1:06d}"
            comment_obj = InstagramComment(
                comment_id=new_id,
                post_id=post_id,
                text=clean_message,
                author_id=self.owner_ig_user_id,
                author_username=self.owner_username,
                timestamp="2026-10-27T13:06:00+0000",
                is_self=True,
            )
            self._sandbox_comments_by_post.setdefault(post_id, []).append(comment_obj)
            self._known_comments[new_id] = comment_obj
            record.state = DispatchState.SENT
            record.external_comment_id = new_id
            record.updated_at = time.time()
            self._recent_ownership_comments.append(norm_msg)
            return record

        try:
            resp = self._request_json(
                "POST",
                f"/{post_id}/comments",
                json_body={"message": clean_message},
            )
            ext_id = str(resp.get("id") or "")
            record.state = DispatchState.SENT
            record.external_comment_id = ext_id
            record.updated_at = time.time()
            self._recent_ownership_comments.append(norm_msg)
            return record
        except InstagramAmbiguousTimeoutError as exc:
            record.state = DispatchState.RECONCILE_PENDING
            record.last_error = str(exc)
            record.updated_at = time.time()
            raise

    def _reconcile_post_comment(self, post_id: str, expected_message: str) -> Optional[str]:
        """Inspect `GET /{ig-media-id}/comments` to check if `@annreveals` comment already landed."""
        expected_norm = _normalize_text(expected_message)
        page = self.list_owned_comments(post_id=post_id, limit=50)
        for comment in page.items:
            if comment.is_self and _normalize_text(comment.text) == expected_norm:
                return comment.comment_id
        return None

    def subscribe_to_webhooks(self, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Subscribe the Instagram account to webhook fields (`comments`)."""
        subscribed_fields = fields or ["comments"]
        if self.sandbox_mode:
            return {"success": True, "subscribed_fields": subscribed_fields, "mode": "sandbox"}

        return self._request_json(
            "POST",
            f"/{self.owner_ig_user_id}/subscribed_apps",
            query_params={"subscribed_fields": ",".join(subscribed_fields)},
        )

    def refresh_auth(self) -> Dict[str, Any]:
        """Refresh a 60-day long-lived Instagram access token (`GET /refresh_access_token`)."""
        if not self.access_token:
            raise InstagramAuthError("Cannot refresh auth: no access_token present.", status_code=401)
        if self.sandbox_mode:
            return {
                "access_token": self.access_token,
                "token_type": "bearer",
                "expires_in": 5184000,
            }

        data = self._request_json(
            "GET",
            "/refresh_access_token",
            query_params={
                "grant_type": "ig_refresh_token",
                "access_token": self.access_token,
            },
        )
        if data.get("access_token"):
            self.access_token = str(data["access_token"])
        return data

    def get_post_publication_status(self, container_id: str) -> Dict[str, Any]:
        """Check Instagram media container publication status (`GET /{ig-container-id}`)."""
        if self.sandbox_mode:
            return {"id": container_id, "status_code": "FINISHED", "status": "FINISHED"}

        return self._request_json(
            "GET",
            f"/{container_id}",
            query_params={"fields": "id,status_code,status"},
        )

    def publish_post(
        self,
        media_url: str,
        caption: str,
        media_type: str = "REELS",
        is_paid_partnership: bool = False,
    ) -> Dict[str, Any]:
        """Create and publish an Instagram Media container, or return a manual copy-package fallback when write/publish scope is disabled."""
        if not self.write_enabled or "instagram_business_content_publish" not in self.granted_scopes:
            return {
                "published": False,
                "mode": "MANUAL_COPY_FALLBACK",
                "reason": "Direct publishing is disabled or awaiting instagram_business_content_publish scope. Use One-Tap Copy & Open Instagram.",
                "prepared_package": {
                    "media_url": media_url,
                    "caption": caption,
                    "media_type": media_type,
                    "require_paid_partnership_label": is_paid_partnership,
                },
            }

        if self.sandbox_mode:
            return {
                "published": True,
                "id": "18099999999999999",
                "mode": "SANDBOX",
                "require_paid_partnership_label": is_paid_partnership,
            }

        container = self._request_json(
            "POST",
            f"/{self.owner_ig_user_id}/media",
            json_body={
                "media_type": media_type,
                "video_url" if media_type == "REELS" else "image_url": media_url,
                "caption": caption,
            },
        )
        container_id = str(container.get("id") or "")
        published = self._request_json(
            "POST",
            f"/{self.owner_ig_user_id}/media_publish",
            json_body={"creation_id": container_id},
        )
        return {"published": True, "container_id": container_id, "id": published.get("id")}

    def get_inbox_messages(self, cursor: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        """List Instagram Direct Message conversations if `instagram_business_manage_messages` is enabled."""
        if "instagram_business_manage_messages" not in self.granted_scopes:
            return {
                "supported": True,
                "enabled": False,
                "items": [],
                "fallback": "Handled manually in native Instagram inbox (instagram_business_manage_messages not enabled in v4.0).",
            }
        if self.sandbox_mode:
            return {"supported": True, "enabled": True, "items": []}

        params: Dict[str, str] = {"platform": "instagram", "limit": str(limit)}
        if cursor:
            params["after"] = cursor
        return self._request_json("GET", "/me/conversations", query_params=params)

    def get_following_posts(self, *args: Any, **kwargs: Any) -> Any:
        """Permanently blocked (`ADR-IG-002`): Meta API does not expose an account's following feed."""
        raise UnsupportedCapabilityError(
            "Forbidden / Unsupported by Meta Instagram Platform API: get_following_posts is permanently blocked. "
            "Use the Owner-Curated Creator Shortlist and shared URL import instead (never scrape follow lists)."
        )

    def comment_on_nonowned_post(self, *args: Any, **kwargs: Any) -> Any:
        """Permanently blocked (`ADR-IG-002`, `FR-014`, `FR-017`): Meta API forbids automated third-party commenting."""
        raise UnsupportedCapabilityError(
            "Forbidden / Unsupported by Meta Instagram Platform API: comment_on_nonowned_post is permanently blocked "
            "(THIRD_PARTY_AUTOCOMMENT=false). Use Owner-in-the-Loop Assisted Mode (One-Tap Copy & Open Instagram)."
        )
