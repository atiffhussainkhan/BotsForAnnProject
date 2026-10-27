# Instagram Integration — System Sequence Diagrams

**Agent:** Agent Bravo (Agent 2 — Meta/Instagram Developer Platform & Integrations Specialist)  
**Project:** Ann Reveals AI Manager (`ARAIM` v4.0)  
**Last Updated:** 27 October 2026

---

## 1. Instagram OAuth 2.0 Connection & Live Scope Verification

This flow shows how `@annreveals` connects her Instagram Professional (Creator/Business) account via **Instagram API with Instagram Login** without needing a Facebook Page, and how `ARAIM` truthfully sets connection status and keeps `INSTAGRAM_WRITE_ENABLED=false` until pilot verification.

```mermaid
sequenceDiagram
    autonumber
    actor Owner as @annreveals (Browser/PWA)
    participant UI as ARAIM Dashboard
    participant API as ARAIM Backend (InstagramAdapter)
    participant MetaAuth as Instagram OAuth (instagram.com)
    participant Graph as Instagram Graph API (graph.instagram.com)

    Owner->>UI: Click "Connect Instagram"
    UI->>API: GET /api/oauth/instagram/start
    API->>API: Generate CSRF state & store in session
    API-->>Owner: 302 Redirect to instagram.com/oauth/authorize (scopes: instagram_business_basic, instagram_business_manage_comments)
    Owner->>MetaAuth: Approve permissions on instagram.com
    MetaAuth-->>API: GET /api/oauth/instagram/callback?code=AUTH_CODE&state=CSRF_STATE
    API->>API: Verify CSRF state matches
    API->>MetaAuth: POST https://api.instagram.com/oauth/access_token (exchange code for short-lived token)
    MetaAuth-->>API: { access_token (1h), user_id, permissions }
    API->>Graph: GET /access_token?grant_type=ig_exchange_token (exchange for 60-day token)
    Graph-->>API: { access_token (60d), expires_in: 5184000 }
    API->>Graph: GET /v21.0/me?fields=id,user_id,username,account_type
    Graph-->>API: { id: "178414...", username: "annreveals", account_type: "MEDIA_CREATOR" }
    API->>API: Encrypt token at rest (AES-GCM/Fernet)<br/>Keep INSTAGRAM_WRITE_ENABLED=false (DRAFT mode)
    API-->>UI: Connection Status = "Connected: read only (Draft mode)"
```

---

## 2. `X-Hub-Signature-256` Webhook Verification, Deduplication & Self-Reply Loop Guard

This flow illustrates how incoming Instagram comment webhooks are cryptographically verified, deduplicated, checked for self-authored comments (`@annreveals`), and threaded before entering the AI classification pipeline.

```mermaid
sequenceDiagram
    autonumber
    participant MetaWH as Meta Webhook Dispatcher
    participant WH as WebhookVerifier (/webhooks/instagram)
    participant Adapter as InstagramAdapter
    participant Queue as Durable Comment Queue
    participant AI as Agent Charlie (Classifier & Voice Engine)

    Note over MetaWH,WH: Phase A: Subscription Handshake (One-Time Setup)
    MetaWH->>WH: GET /webhooks/instagram?hub.mode=subscribe&hub.verify_token=TOKEN&hub.challenge=998877
    WH->>WH: Constant-time compare hub.verify_token == INSTAGRAM_WEBHOOK_VERIFY_TOKEN
    WH-->>MetaWH: 200 OK (body: "998877")

    Note over MetaWH,AI: Phase B: Real-Time Comment Event Delivery
    MetaWH->>WH: POST /webhooks/instagram (Header: X-Hub-Signature-256: sha256=...)
    WH->>WH: Compute HMAC-SHA256(INSTAGRAM_APP_SECRET, raw_body)<br/>Verify via hmac.compare_digest()
    alt Invalid or Missing Signature
        WH-->>MetaWH: 401 Unauthorized ( Security Audit Log )
    else Valid Signature
        WH-->>MetaWH: 200 OK (Immediate Ack)
        WH->>Adapter: parse_webhook_events(payload)
        loop For each comment change event
            Adapter->>Adapter: Check Deduplication Key (instagram + account_id + comment_id)
            alt Already Processed
                Adapter->>Adapter: Skip duplicate delivery
            else New Event
                Adapter->>Adapter: Check Self-Reply Guard (from.id == owner_id OR from.username == "annreveals")
                alt Authored by @annreveals (Self)
                    Adapter->>Adapter: Mark is_self=True, skip auto-reply generation (Loop Prevention FR-003)
                else Viewer Comment or Reply
                    Adapter->>Queue: Enqueue Normalized Comment (top-level or nested via parent_id)
                    Queue->>AI: Classify (14 categories) & Draft UK Soft-Luxury Reply
                end
            end
        end
    end
```

---

## 3. Safe Auto-Reply Dispatch & Ambiguous Timeout Reconciliation (`RECONCILE_PENDING`)

This diagram shows how `ARAIM` guarantees **effectively-once** comment replies (`NFR-03`) even when Meta's Graph API or the network times out mid-flight, preventing embarrassing duplicate replies under a follower's comment.

```mermaid
sequenceDiagram
    autonumber
    participant Worker as Outbound Dispatch Worker
    participant Adapter as InstagramAdapter
    participant StateStore as Attempt State Store
    participant Graph as Instagram Graph API (graph.instagram.com)

    Worker->>Adapter: reply_to_owned_comment(comment_id, message, idempotency_key)
    Adapter->>Adapter: Verify INSTAGRAM_WRITE_ENABLED == true<br/>Verify mode == SAFE_AUTO (or explicit owner send)<br/>Verify target author != @annreveals
    Adapter->>StateStore: Lookup idempotency_key
    alt First Attempt (No Prior Ambiguous Timeout)
        Adapter->>StateStore: Record status = IN_FLIGHT
        Adapter->>Graph: POST /v21.0/{ig-comment-id}/replies { message }
        alt Network Timeout / HTTP 502 / 503 / 504
            Graph--xAdapter: TimeoutError / Gateway Error
            Adapter->>StateStore: Transition status = RECONCILE_PENDING
            Adapter-->>Worker: Return ReconcilePendingResult (Schedule Backoff 30s)
        else HTTP 401 / 403 (Token Revoked or Scope Missing)
            Graph-->>Adapter: Error Code 190 / 10 / 200
            Adapter->>Adapter: Downgrade Connection = NEEDS_RECONNECT, Mode = DRAFT, Write = false
            Adapter-->>Worker: Raise InstagramAuthError (Fail-Closed NFR-10)
        else HTTP 200 OK
            Graph-->>Adapter: { "id": "17999888777666555" }
            Adapter->>StateStore: Transition status = SENT (external_id="17999888777666555")
            Adapter-->>Worker: Return CommentReplyResult(status=SENT)
        end
    else Retry After Timeout (status == RECONCILE_PENDING)
        Adapter->>Graph: GET /v21.0/{ig-comment-id}/replies?fields=id,text,username,from,timestamp
        Graph-->>Adapter: List of existing replies on comment_id
        Adapter->>Adapter: Search replies where from.username == "annreveals"<br/>and normalized(text) == normalized(message)
        alt Matching Reply Found on Instagram
            Adapter->>StateStore: Transition status = SENT_RECONCILED (external_id=matched.id)
            Adapter-->>Worker: Return CommentReplyResult(status=SENT_RECONCILED, deduplicated=True)
        else Reply Confirmed Absent on Instagram
            Adapter->>Graph: POST /v21.0/{ig-comment-id}/replies { message }
            Graph-->>Adapter: { "id": "17999888777666888" }
            Adapter->>StateStore: Transition status = SENT (external_id="17999888777666888")
            Adapter-->>Worker: Return CommentReplyResult(status=SENT)
        end
    end
```
