# TikTok Integration Sequence Diagrams (`design/tiktok/sequence-diagrams.md`)

**Author:** Agent Alpha (`Agent 1 — Official TikTok Platform Access, Policy, and Integration Specialist`)  
**Date:** 27 October 2026  
**Project:** Ann Reveals AI Manager (`ARAIM` v4.0)  

---

## 1. OAuth 2.0 PKCE + Live Scope Inspection & Truthful Badge Calculation

This flow illustrates how `@annreveals` connects her TikTok Business Account, how tokens are exchanged and inspected against the **March 20, 2026 TikTok Accounts API v1.3** scopes (`comment.list`, `comment.list.manage`, `video.list`), and how the UI badge is truthfully derived (`FR-038`, `FR-043`, `NFR-05`).

```mermaid
sequenceDiagram
    autonumber
    actor Owner as Ann (@annreveals)
    participant PWA as ARAIM Cloud PWA
    participant Adapter as TikTokAdapter
    participant OAuth as TikTok OAuth (open.tiktokapis.com)
    participant BizAPI as TikTok Accounts API v1.3 (business-api.tiktok.com)
    participant Vault as Encrypted Token Vault

    Owner->>PWA: Click "Connect TikTok Business Account"
    PWA->>Adapter: build_authorization_url(state, code_verifier)
    Adapter-->>PWA: HTTPS Auth URL (PKCE S256 + state)
    PWA->>OAuth: Redirect Owner to TikTok Consent Screen
    Owner->>OAuth: Approve Requested Scopes
    OAuth-->>PWA: Callback with code + state
    PWA->>Adapter: refresh_auth / exchange_code(code, code_verifier)
    Adapter->>OAuth: POST /v2/oauth/token/
    OAuth-->>Adapter: access_token, refresh_token, granted_scopes[]
    Adapter->>Adapter: Inspect granted_scopes vs Required Matrix
    alt comment.list.manage NOT in granted_scopes (March 20, 2026 Gate Pending)
        Adapter->>Adapter: Set capability = AWAITING_APPROVAL
        Adapter->>Adapter: Force mode = DRAFT (TIKTOK_WRITE_ENABLED=false)
        Adapter->>Vault: Store AES-GCM Encrypted Token + Badge="Awaiting review"
        Adapter-->>PWA: Badge: "Awaiting review" / "Connected: read only"
    else comment.list & comment.list.manage VERIFIED in granted_scopes
        Adapter->>BizAPI: GET /open_api/v1.3/business/get/ (Verify live token)
        BizAPI-->>Adapter: 200 OK (business_id="@annreveals")
        Adapter->>Vault: Store AES-GCM Encrypted Token + Scopes Verified
        alt TIKTOK_WRITE_ENABLED == false (Default Safe Mode)
            Adapter-->>PWA: Badge: "Connected: read only (Draft Mode)"
        else TIKTOK_WRITE_ENABLED == true
            Adapter-->>PWA: Badge: "Live: can reply"
        end
    end
```

---

## 2. Signed Webhook Ingestion + Self-Loop Guard + Idempotent Owned-Comment Reply

This diagram shows real-time `comment.update` ingestion from TikTok Business Webhook Gateway (`doc_id=1751617884206210`), constant-time HMAC-SHA256 verification, replay defense, self-comment loop filtering (`FR-003`), policy classification (`FR-004`), and idempotent reply dispatch (`NFR-03`, `NFR-04`).

```mermaid
sequenceDiagram
    autonumber
    participant TT as TikTok Webhook Gateway
    participant WH as TikTokWebhookVerifier
    participant Queue as Durable Dedup Queue
    participant AI as Policy & Voice Engine (Charlie)
    participant Adapter as TikTokAdapter
    participant BizAPI as TikTok Accounts API v1.3

    TT->>WH: POST /api/v1/webhooks/tiktok (Header: TikTok-Signature: t=...,s=...)
    WH->>WH: Parse t (timestamp) and s (HMAC-SHA256 hex)
    WH->>WH: Verify abs(now - t) <= 300s (Replay Window)
    WH->>WH: hmac.compare_digest(expected_hmac, s)
    alt Invalid Signature or Expired Timestamp
        WH-->>TT: 401 Unauthorized (Audit Logged, Rejected)
    else Valid Signature & Fresh Timestamp
        WH->>WH: Check Replay Cache for (event_id, comment_id)
        WH->>WH: Check Self-Author Guard (sender_id == business_id)
        alt Sender is @annreveals (Self-Comment)
            WH-->>TT: 200 OK (Ignored: IGNORE_SELF_COMMENT - FR-003)
        else Viewer Comment on Owned Video
            WH->>Queue: Enqueue (platform="tiktok", video_id, comment_id, idempotency_key)
            WH-->>TT: 200 OK (< 3s SLA)
            Queue->>AI: Classify (14 categories) & Draft UK Soft-Luxury Reply
            alt Category is High-Risk (Medical/Allergy/Complaint/Link) or Mode == DRAFT
                AI->>Queue: Save as DRAFT / ESCALATED for Owner Review
            else Category is Safe Ordinary & Mode == SAFE_AUTO & TIKTOK_WRITE_ENABLED == true
                AI->>Adapter: reply_to_owned_comment(video_id, comment_id, text, idempotency_key)
                Adapter->>Adapter: Verify Host Allowlist & Idempotency Store
                Adapter->>BizAPI: POST /open_api/v1.3/business/comment/reply/
                alt HTTP 200 OK (code == 0)
                    BizAPI-->>Adapter: reply_comment_id
                    Adapter->>Queue: Mark SENT (Permalink & Audit Logged)
                else Network Timeout
                    Adapter->>Queue: Mark RECONCILE_PENDING (Poll comment/list before retry - NFR-03)
                end
            end
        end
    end
```

---

## 3. Fail-Closed Downgrade on `401`/`403`, `429` Backoff, and `5xx` Circuit Breaker

This diagram illustrates `NFR-02` and `NFR-10`: automatic downgrade to `DRAFT`/`READ_ONLY` on `401`/`403`, `Retry-After` + jittered `30s/60s/120s` backoff on `429`, and circuit breaker activation after consecutive `5xx` errors.

```mermaid
sequenceDiagram
    autonumber
    participant Worker as Background Dispatch Worker
    participant Adapter as TikTokAdapter
    participant BizAPI as TikTok Accounts API v1.3
    participant Alert as Owner Alert & Dashboard State

    Worker->>Adapter: reply_to_owned_comment(...)
    Adapter->>BizAPI: POST /open_api/v1.3/business/comment/reply/
    alt HTTP 401 Unauthorized or 403 Forbidden (Token Revoked / Scope Removed)
        BizAPI-->>Adapter: 401 / 403 Error
        Adapter->>Adapter: Fail-Closed: Set mode = DRAFT, write_enabled = False
        Adapter->>Adapter: Set badge = NEEDS_RECONNECT, capability = AWAITING_APPROVAL
        Adapter->>Alert: Emit Urgent Auth Alert ("TikTok write paused: Needs reconnect")
        Adapter-->>Worker: Return Fail-Closed Draft Result (Comment saved as Draft)
    else HTTP 429 Too Many Requests
        BizAPI-->>Adapter: 429 (Header: Retry-After: 45)
        Adapter->>Adapter: Calculate Backoff = max(Retry-After, 30 * 2^attempt) + Jitter
        Adapter->>Alert: Set Cooldown Until (now + backoff_seconds)
        Adapter-->>Worker: Raise RateLimitExceededError(retry_after_seconds)
    else HTTP 500 / 502 / 503 / 504 (Consecutive >= 3)
        BizAPI-->>Adapter: 503 Service Unavailable
        Adapter->>Adapter: Increment consecutive_5xx_failures (== 3)
        Adapter->>Adapter: Trip Circuit Breaker (Open for 300s)
        Adapter->>Alert: Notify Degraded Upstream Status
        Adapter-->>Worker: Raise CircuitBreakerOpenError
    end
```
