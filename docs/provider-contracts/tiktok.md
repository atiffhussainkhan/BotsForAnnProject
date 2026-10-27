# Provider Contract: TikTok Official Integration (`docs/provider-contracts/tiktok.md`)

**Provider ID:** `tiktok`  
**Package Path:** `apps/backend/integrations/tiktok/`  
**Owner:** Agent Alpha (`Agent 1`)  
**Version:** `4.0.0`  
**Standard Library Only:** Yes (`Python 3.9+` — zero third-party runtime dependencies)

---

## 1. Provider-Neutral Interface Specification

`TikTokAdapter` implements the 12 canonical provider methods required across **Ann Reveals AI Manager (v4.0)**:

```python
class TikTokAdapter:
    def get_owned_profile(self) -> ProviderResponse[TikTokProfile]: ...
    def get_owned_posts(self, cursor: int = 0, max_Count: int = 20) -> ProviderResponse[List[TikTokPost]]: ...
    def list_owned_comments(
        self, video_id: str, cursor: int = 0, max_count: int = 20, include_replies: bool = True
    ) -> ProviderResponse[List[TikTokComment]]: ...
    def reply_to_owned_comment(
        self, video_id: str, comment_id: str, text: str, idempotency_key: str
    ) -> ProviderResponse[CommentWriteResult]: ...
    def create_comment_on_owned_post(
        self, video_id: str, text: str, idempotency_key: str, is_ownership_declaration: bool = False
    ) -> ProviderResponse[CommentWriteResult]: ...
    def subscribe_to_webhooks(
        self, callback_url: str, event_types: Optional[List[str]] = None
    ) -> ProviderResponse[Dict[str, Any]]: ...
    def refresh_auth(self, refresh_token: str) -> ProviderResponse[TokenGrant]: ...
    def publish_post(self, request: PublishPostRequest) -> ProviderResponse[PublishPostResult]: ...
    def get_post_publication_status(self, publish_id: str) -> ProviderResponse[PublishPostResult]: ...
    def get_inbox_messages(self, cursor: int = 0) -> ProviderResponse[List[Dict[str, Any]]]: ...
    def get_following_posts(self, creator_handle: str = "") -> ProviderResponse[List[TikTokPost]]: ...
    def comment_on_nonowned_post(
        self, target_video_id: str, text: str, owner_business_id: Optional[str] = None
    ) -> ProviderResponse[CommentWriteResult]: ...
```

---

## 2. Truthful Capability Status Enum (`CapabilityStatus`)

Every capability in `tiktok-capabilities.json` and `TikTokAdapter.get_capability_status(capability_name)` returns one of four truthful states:

1. `VERIFIED_ACTIVE`: Scope is present in the inspected token grant **and** verified in the active runtime mode (or deterministic sandbox test fixture).
2. `AWAITING_APPROVAL`: Official TikTok endpoint exists (e.g., TikTok Accounts API v1.3 `/business/comment/reply/`), but awaits external approval of the **March 20, 2026 TikTok Accounts API Access Application** or OAuth grant.
3. `UNAVAILABLE`: Capability does not exist in official TikTok APIs or is permanently prohibited by policy (`comment_on_nonowned_post`, `get_following_posts`, `get_inbox_messages`).
4. `UNKNOWN`: Status has not yet been inspected.

---

## 3. Security & Policy Invariants

### 3.1 Outbound Host Allowlist
`TikTokAdapter._validate_outbound_url(url)` parses every request URL using `urllib.parse.urlparse` and enforces:
- Scheme **must** be `https`.
- Hostname **must** be in `{"business-api.tiktok.com", "open.tiktokapis.com"}`.
- Any attempt to call an unapproved host raises `SecurityConfigurationError`.

### 3.2 Webhook Signature & Replay Defense (`apps/backend/integrations/tiktok/webhook.py`)
- Header format: `TikTok-Signature: t=<unix_timestamp>,s=<hex_hmac_sha256>` (also supports `X-TikTok-Signature`).
- Signature calculation: `HMAC-SHA256(client_secret, f"{timestamp}.{raw_body_utf8}")` verified using `hmac.compare_digest`.
- Timestamp freshness: Rejects payloads if `abs(now - timestamp) > max_skew_seconds` (default `300` seconds).
- Replay cache: Rejects duplicate `(event_id, signature)` deliveries within the retention window (`NFR-04`, `NFR-05`).
- Self-comment loop guard (`FR-003`): Automatically flags events where `comment.user_id == business_id` or `comment.is_self_author == True` as `IGNORE_SELF_COMMENT` so the auto-replier never replies to `@annreveals` herself.

### 3.3 Effectively-Once Outward Dispatch & `RECONCILE_PENDING` (`NFR-03`)
- Both `reply_to_owned_comment` and `create_comment_on_owned_post` require a deterministic `idempotency_key` (derived from `platform:account_id:video_id:parent_comment_id:policy_version`).
- If an in-flight POST times out (`TimeoutError`), the adapter records the idempotency key as `RECONCILE_PENDING` rather than blindly retrying, preventing double-replies on a viewer's comment.

### 3.4 Anti-Spam Ownership Comment Guard (`FR-055`)
- When `create_comment_on_owned_post(..., is_ownership_declaration=True)` is called, the adapter checks that the text is non-repetitive against recently posted ownership declarations and never asserts "not an ad" if commercial flags are present.
