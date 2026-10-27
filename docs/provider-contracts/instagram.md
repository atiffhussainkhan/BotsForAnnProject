# Provider Contract: Instagram Platform (`Instagram API with Instagram Login`)

**Provider Key:** `instagram`  
**Primary Graph Host:** `https://graph.instagram.com/v21.0`  
**OAuth Authorization URL:** `https://www.instagram.com/oauth/authorize`  
**Short-Lived Token URL:** `https://api.instagram.com/oauth/access_token`  
**Fallback Graph Host (Facebook Login):** `https://graph.facebook.com/v21.0`  
**Contract Version:** 4.0 (Verified 27 October 2026)

---

## 1. Authentication & Token Lifecycle Contract

### 1.1 OAuth 2.0 Authorization Request
```http
GET https://www.instagram.com/oauth/authorize
  ?client_id={INSTAGRAM_APP_ID}
  &redirect_uri={REDIRECT_URI}
  &response_type=code
  &scope=instagram_business_basic,instagram_business_manage_comments
  &state={CSRF_STATE_TOKEN}
```

### 1.2 Short-Lived -> Long-Lived Token Exchange
1. **Exchange Code for Short-Lived Token (1 hour):**
   - `POST https://api.instagram.com/oauth/access_token` (form-urlencoded: `client_id`, `client_secret`, `grant_type=authorization_code`, `redirect_uri`, `code`).
2. **Exchange for Long-Lived Token (60 days):**
   - `GET https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_secret={INSTAGRAM_APP_SECRET}&access_token={SHORT_LIVED_TOKEN}`
3. **Refresh Long-Lived Token (`refresh_auth`):**
   - `GET https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token={LONG_LIVED_TOKEN}`
   - Response:
     ```json
     {
       "access_token": "IGQWR...",
       "token_type": "bearer",
       "expires_in": 5184000
     }
     ```

---

## 2. REST Endpoint Contracts (`graph.instagram.com/v21.0`)

### 2.1 `get_owned_profile()` -> `GET /v21.0/me`
- **Query Params:** `fields=id,user_id,username,name,account_type,profile_picture_url,followers_count,follows_count,media_count`
- **Required Scope:** `instagram_business_basic`
- **Success Response (`200 OK`):**
  ```json
  {
    "id": "17841400008460056",
    "user_id": "17841400008460056",
    "username": "annreveals",
    "name": "Ann Reveals | Fragrance & Perfumes",
    "account_type": "MEDIA_CREATOR",
    "followers_count": 14820,
    "follows_count": 312,
    "media_count": 184
  }
  ```

### 2.2 `get_owned_posts(cursor, limit)` -> `GET /v21.0/{ig-user-id}/media`
- **Query Params:** `fields=id,caption,media_type,media_product_type,media_url,permalink,timestamp,like_count,comments_count&limit={limit}&after={cursor}`
- **Required Scope:** `instagram_business_basic`
- **Success Response (`200 OK`):**
  ```json
  {
    "data": [
      {
        "id": "18029910293847561",
        "caption": "First impressions of Vanilla Powder after a full week of wear...",
        "media_type": "VIDEO",
        "media_product_type": "REELS",
        "permalink": "https://www.instagram.com/reel/C9xYz123AbC/",
        "timestamp": "2026-10-26T18:30:00+0000",
        "like_count": 642,
        "comments_count": 48
      }
    ],
    "paging": {
      "cursors": {
        "before": "QVFIUl...",
        "after": "QVFIUm..."
      }
    }
  }
  ```

### 2.3 `list_owned_comments(post_id, cursor, include_replies)` -> `GET /v21.0/{ig-media-id}/comments`
- **Query Params:** `fields=id,text,timestamp,username,from,parent_id,hidden,like_count&limit=50&after={cursor}`
- **Nested Replies Endpoint:** `GET /v21.0/{ig-comment-id}/replies?fields=id,text,timestamp,username,from,parent_id,hidden,like_count`
- **Required Scopes:** `instagram_business_basic`, `instagram_business_manage_comments`
- **Success Response (`200 OK`):**
  ```json
  {
    "data": [
      {
        "id": "17918273645019283",
        "text": "How many hours did the dry-down last on clothes?",
        "timestamp": "2026-10-27T09:14:22+0000",
        "username": "scentlover_uk",
        "from": {
          "id": "901283746501928",
          "username": "scentlover_uk"
        },
        "hidden": false,
        "like_count": 3
      }
    ],
    "paging": {
      "cursors": {
        "after": "QVFIUn..."
      }
    }
  }
  ```

### 2.4 `reply_to_owned_comment(comment_id, message, idempotency_key)` -> `POST /v21.0/{ig-comment-id}/replies`
- **Parameters / Body:** `{"message": "<reply text>"}`
- **Required Scope:** `instagram_business_manage_comments`
- **Pre-Dispatch Guards:**
  1. `INSTAGRAM_WRITE_ENABLED` must be `True`.
  2. Target comment author must **not** be `@annreveals` (`author_id != owner_id` and `author_username.lower() != "annreveals"`).
  3. If a previous attempt for `idempotency_key` is in `RECONCILE_PENDING`, the adapter **must first call** `GET /v21.0/{ig-comment-id}/replies` to verify whether `@annreveals`'s reply already landed on Instagram before issuing a retry `POST`.
- **Success Response (`200 OK`):**
  ```json
  {
    "id": "17999888777666555"
  }
  ```

### 2.5 `create_comment_on_owned_post(post_id, message, idempotency_key)` -> `POST /v21.0/{ig-media-id}/comments`
- **Parameters / Body:** `{"message": "<first-party context or ownership comment>"}`
- **Required Scope:** `instagram_business_manage_comments`
- **Pre-Dispatch Guards:**
  1. `INSTAGRAM_WRITE_ENABLED` must be `True`.
  2. Anti-spam variation check (`FR-055`) must confirm the comment is not a repetitive boilerplate string posted across consecutive videos.
  3. If a previous attempt for `idempotency_key` is in `RECONCILE_PENDING`, the adapter queries `GET /v21.0/{ig-media-id}/comments` to verify whether the comment already exists before retrying.
- **Success Response (`200 OK`):**
  ```json
  {
    "id": "17999888777666999"
  }
  ```

### 2.6 Permanently Blocked Methods
- `get_following_posts()` -> Raises `UnsupportedCapabilityError("Meta Instagram Platform API does not expose an account's following feed.")`
- `comment_on_nonowned_post()` -> Raises `UnsupportedCapabilityError("Meta Instagram Platform API forbids automated commenting on non-owned third-party posts.")`

---

## 3. Webhook Contract (`/webhooks/instagram`)

### 3.1 Subscription Verification (`GET`)
Meta sends:
```http
GET /webhooks/instagram?hub.mode=subscribe&hub.verify_token={VERIFY_TOKEN}&hub.challenge=1158201444
```
- **Verification Rule:** `hub.mode == "subscribe"` and constant-time match of `hub.verify_token == INSTAGRAM_WEBHOOK_VERIFY_TOKEN`.
- **Success Response:** HTTP `200 OK` with raw plain-text body `1158201444`.
- **Failure Response:** HTTP `403 Forbidden`.

### 3.2 Event Notification (`POST`)
- **Required Header:** `X-Hub-Signature-256: sha256=<hex_digest>`
- **Signature Verification Rule:** Compute `hmac.new(app_secret.encode("utf-8"), raw_body_bytes, hashlib.sha256).hexdigest()` and compare using `hmac.compare_digest`. Reject missing or mismatched signatures with `401 Unauthorized`.
- **Sample Payload (`comments` field):**
  ```json
  {
    "object": "instagram",
    "entry": [
      {
        "id": "17841400008460056",
        "time": 1761569662,
        "changes": [
          {
            "field": "comments",
            "value": {
              "id": "17918273645019283",
              "text": "Does this project more like Delina or Delina Exclusif?",
              "from": {
                "id": "901283746501928",
                "username": "scentlover_uk"
              },
              "media": {
                "id": "18029910293847561",
                "media_product_type": "REELS"
              },
              "parent_id": "17918273645000001"
            }
          }
        ]
      }
    ]
  }
  ```

---

## 4. Error Taxonomy & Automatic Fail-Closed Behavior

| HTTP Status | Meta Error Code / Subcode | Meaning | Adapter Action (`NFR-02`, `NFR-10`) |
| :--- | :--- | :--- | :--- |
| `401` / `400` | Code `190` (Subcodes `458`, `460`, `463`, `467`) | Access token expired, revoked, or password changed | Immediately transition connection status to `NEEDS_RECONNECT`, set automation mode to `DRAFT`, disable writes, and raise `InstagramAuthError`. |
| `403` | Code `10` or `200`–`299` | Missing permission (`instagram_business_manage_comments` not granted or removed) | Transition connection status to `NEEDS_RECONNECT`, downgrade mode to `DRAFT`, and raise `InstagramPermissionError`. |
| `429` / `400` | Code `4`, `17`, `32`, `613` | Application or Business Use Case rate limit reached | Parse `Retry-After` or apply jittered backoff (`30s`, `60s`, `120s`), pause outward queue, and raise `InstagramRateLimitError`. |
| `400` | Code `368` | Temporarily blocked for policy violation / spam check | Immediately trip circuit breaker, downgrade platform mode to `DRAFT`, alert owner, and halt auto-replies. |
| Timeout / `502` / `503` / `504` | Network / Gateway Timeout during `POST` | Ambiguous write completion | Mark attempt `RECONCILE_PENDING`; query `GET /{id}/replies` or `GET /{id}/comments` before any retry to prevent duplicate comments. |
