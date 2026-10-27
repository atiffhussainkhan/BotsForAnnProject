# Ann Reveals AI Manager (v4.0) — Architecture & Component Diagrams

**Author:** Agent Echo (Agent 5 — Principal Platform Architect, Security Engineer & SRE)  
**Version:** 4.0 FINAL  
**Target Ceiling:** ≤ £30.00/month Managed Cloud Modular Monolith + Mobile-First PWA

---

## 1. System Context & Container Architecture (Mermaid Flowchart)

```mermaid
flowchart TD
    subgraph OwnerDevices["Owner Devices (Zero-CLI Routine Operation)"]
        Phone["Android Phone PWA (44px Touch Targets)"]
        Laptop["Laptop Browser Dashboard"]
    end

    subgraph ExternalPlatforms["External Social & AI APIs"]
        TikTok["TikTok Official API v2 (OAuth2 PKCE + Webhooks)"]
        Meta["Instagram Graph API (OAuth2 + HMAC Webhooks)"]
        LLM["LLM Provider API (Hard £5/mo Cap + Fallback)"]
    end

    subgraph CloudRuntime["Ann Reveals Cloud Runtime (Render / Fly.io <= £30/mo)"]
        PWA["9-Screen Mobile-First PWA Frontend"]
        APIGW["Unified HTTP/API Server + CSRF/RBAC Guard"]
        
        subgraph CoreDomains["Five-Agent Modular Domain Layer"]
            Alpha["Agent Alpha: TikTok Adapter & Capability Matrix"]
            Bravo["Agent Bravo: Instagram Graph & Webhook Engine"]
            Charlie["Agent Charlie: Brand Voice, 14-Class Classifier & Friends Watchlist"]
            Delta["Agent Delta: Verified Purchases Vault, UK ASA/CMA & Appeals"]
            Echo["Agent Echo: Kill-Switch, Idempotency, Budget Guard, GDPR & Encryption"]
        end

        subgraph Storage["Encrypted Persistence & Backups"]
            DB[("SQLite WAL / PostgreSQL Database")]
            Vault[("Encrypted Evidence & Token Vault (ARAIM-ENC-V1)")]
            Backup[("SHA-256 Verified Encrypted Snapshots")]
        end
    end

    Phone -->|HTTPS + Session/CSRF| PWA
    Laptop -->|HTTPS + Session/CSRF| PWA
    PWA --> APIGW
    TikTok -->|Signed Webhook / Poll| APIGW
    Meta -->|X-Hub-Signature-256 Webhook| APIGW

    APIGW --> Echo
    Echo --> Alpha
    Echo --> Bravo
    Echo --> Charlie
    Echo --> Delta

    Alpha -->|Official API Only| TikTok
    Bravo -->|Official API Only| Meta
    Charlie -->|Guarded by BudgetGuard| LLM

    Echo --> DB
    Echo --> Vault
    Vault --> Backup
```

---

## 2. Inbound Comment to Safe Outbound Dispatch Sequence

```mermaid
sequenceDiagram
    autonumber
    participant Social as TikTok / Instagram Webhook
    participant Sec as Echo: Security & Idempotency
    participant KS as Echo: KillSwitch & BudgetGuard
    participant AI as Charlie: Classifier & Voice Engine
    participant Out as Alpha/Bravo: Platform Adapter
    participant Audit as Echo: Audit Log & Owner Inbox

    Social->>Sec: POST /webhooks/{platform} (Payload + HMAC Signature)
    Sec->>Sec: Verify Constant-Time HMAC-SHA256 Signature
    Sec->>Sec: Check Idempotency Key (platform:account:comment:version)
    alt Duplicate or Self-Comment (@annreveals)
        Sec-->>Social: 200 OK (Ignored / Deduplicated)
    else New Legitimate Comment
        Sec->>Sec: Acquire Per-Thread Concurrency Lock
        Sec->>KS: Check Universal Emergency Stop & Platform Mode
        KS->>AI: Classify (14 Categories) + Check Budget (£5 AI Cap)
        alt High-Risk Category (Medical/Skin/Legal/Threat) or Budget Cap Reached
            AI->>Audit: Store Deterministic Draft / Escalation Alert (DRAFT Mode)
        else Safe Category (Compliment / Product Notes)
            AI->>Audit: Generate Grounded UK-English Reply Draft
            alt Platform Mode == SAFE_AUTO and Write Scope Verified Live
                Audit->>Out: Dispatch Official Reply API with Idempotency Token
                alt Network Timeout
                    Out->>Audit: Mark RECONCILE_PENDING (Never Blindly Retry)
                else 401/403/429 Error
                    Out->>KS: Auto-Downgrade Platform to PAUSED_BY_SYSTEM / DRAFT
                else 200 OK
                    Out->>Audit: Record Permalink + Immutable Audit Trail
                end
            else Platform Mode == DRAFT / OBSERVE / OFF
                Audit->>Audit: Hold in Unified Inbox for 1-Tap Owner Review
            end
        end
    end
```

---

## 3. Universal Kill-Switch & Mode State Machine

```mermaid
stateDiagram-v2
    [*] --> DRAFT : Default Safe Initial State
    DRAFT --> OBSERVE : Owner selects Read-Only Observation
    OBSERVE --> DRAFT : Owner enables Drafting
    DRAFT --> SAFE_AUTO : Owner enables Auto-Reply (Requires Live Write Scope)
    SAFE_AUTO --> DRAFT : Owner switches to Manual Approval
    SAFE_AUTO --> PAUSED_BY_SYSTEM : 401/403, Rate-Limit Anomaly, Policy Warning, or £30 Budget Cap
    DRAFT --> PAUSED_BY_SYSTEM : 401/403 Auth Revocation
    PAUSED_BY_SYSTEM --> DRAFT : Owner Reconnects OAuth & Clears Alert
    SAFE_AUTO --> OFF : Universal EMERGENCY STOP Activated (Drains Queue to DRAFT)
    DRAFT --> OFF : Universal EMERGENCY STOP Activated
    OBSERVE --> OFF : Universal EMERGENCY STOP Activated
    OFF --> DRAFT : Owner Explicitly Releases Emergency Stop with Confirmation
```

---

## 4. Verified Purchases Vault & Dual-Platform Disclosure Pipeline

```mermaid
flowchart LR
    Upload["Receipt Upload (PDF / Screenshot / Email)"] --> Redact["UK GDPR PII Redactor (Strip Card PAN, Address, Email)"]
    Redact --> Store["Preserve Raw Store Label ('Experian' vs 'Empyrean')"]
    Store --> Encrypt["Envelope Encrypt Proof (ARAIM-ENC-V1) + SHA-256 Hash"]
    Encrypt --> Link["Fuzzy Match to Perfume SKU & Post (Confidence Score)"]
    Link --> Axis1["Axis 1: Acquisition Provenance (SELF_PURCHASED / PR_GIFTED / etc.)"]
    Link --> Axis2["Axis 2: Commercial Relationship (NONE / AFFILIATE / PAID_COLLAB / TIKTOK_SHOP)"]
    Axis1 --> Eval["Dual-Platform Policy Engine (UK ASA/CMA + Meta + TikTok)"]
    Axis2 --> Eval
    Eval --> Output["Truthful Copy + Required Ad/Affiliate Toggles + Immutable Archive"]
```
