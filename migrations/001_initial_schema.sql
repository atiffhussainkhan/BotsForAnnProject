-- ANN REVEALS AI MANAGER (v4.0) — INITIAL DATABASE SCHEMA (Section O)
-- Compatible with SQLite 3.35+ and PostgreSQL 15+

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    authentication_subject TEXT NOT NULL,
    locale TEXT NOT NULL DEFAULT 'en-GB',
    timezone TEXT NOT NULL DEFAULT 'Europe/London',
    mfa_enabled INTEGER NOT NULL DEFAULT 1,
    role TEXT NOT NULL DEFAULT 'owner',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS social_accounts (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    provider_user_id TEXT NOT NULL,
    handle TEXT NOT NULL,
    account_type TEXT NOT NULL,
    connection_state TEXT NOT NULL,
    permission_reviewed_at TEXT,
    UNIQUE(platform, provider_user_id)
);

CREATE TABLE IF NOT EXISTS oauth_grants (
    id TEXT PRIMARY KEY,
    social_account_id TEXT NOT NULL REFERENCES social_accounts(id),
    encrypted_secret_reference TEXT NOT NULL,
    granted_scopes_json TEXT NOT NULL,
    expires_at TEXT,
    revoked_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS capabilities (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES social_accounts(id),
    capability_code TEXT NOT NULL,
    documented_endpoint TEXT NOT NULL,
    scope TEXT NOT NULL,
    approved INTEGER NOT NULL DEFAULT 0,
    tested_at TEXT,
    test_evidence_id TEXT,
    reason TEXT NOT NULL,
    UNIQUE(account_id, capability_code)
);

CREATE TABLE IF NOT EXISTS retailers (
    id TEXT PRIMARY KEY,
    merchant_label_raw TEXT NOT NULL,
    normalized_name TEXT,
    normalized_domain TEXT,
    owner_verified INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    sku TEXT UNIQUE NOT NULL,
    brand TEXT NOT NULL,
    exact_name TEXT NOT NULL,
    variant TEXT,
    size_ml INTEGER NOT NULL,
    concentration TEXT NOT NULL,
    owner_notes TEXT,
    normalized_aliases_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_files (
    id TEXT PRIMARY KEY,
    object_key TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    redaction_status TEXT NOT NULL,
    encrypted_dek_reference TEXT NOT NULL,
    redacted_excerpt TEXT,
    access_audit_json TEXT,
    retention_due_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS purchases (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(id),
    retailer_id TEXT NOT NULL REFERENCES retailers(id),
    purchase_date TEXT,
    currency TEXT NOT NULL DEFAULT 'GBP',
    amount_encrypted TEXT,
    ownership_state TEXT NOT NULL,
    source_evidence_id TEXT REFERENCES evidence_files(id),
    matched_confidence REAL NOT NULL,
    owner_confirmed_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    account_id TEXT NOT NULL REFERENCES social_accounts(id),
    provider_post_id TEXT NOT NULL,
    original_asset_id TEXT,
    caption_hash TEXT,
    product_sku TEXT,
    owned INTEGER NOT NULL DEFAULT 1,
    automation_frozen INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE(platform, provider_post_id)
);

CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    provider_comment_id TEXT NOT NULL,
    post_id TEXT NOT NULL,
    parent_id TEXT,
    commenter_pseudonym TEXT NOT NULL,
    text_redacted TEXT NOT NULL,
    category TEXT NOT NULL,
    risk_tier TEXT NOT NULL,
    response_status TEXT NOT NULL,
    reply_candidate TEXT,
    audit_trail_json TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(platform, provider_comment_id)
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    received_at TEXT NOT NULL,
    processed_at TEXT,
    state TEXT NOT NULL,
    retries INTEGER NOT NULL DEFAULT 0,
    UNIQUE(provider, external_event_id)
);

CREATE TABLE IF NOT EXISTS drafts (
    id TEXT PRIMARY KEY,
    source_event_id TEXT,
    channel TEXT NOT NULL,
    content TEXT NOT NULL,
    ai_model_version TEXT NOT NULL,
    policy_snapshot_id TEXT NOT NULL,
    confidence REAL NOT NULL,
    mode TEXT NOT NULL,
    state TEXT NOT NULL,
    expires_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outbound_actions (
    action_id TEXT PRIMARY KEY,
    draft_id TEXT,
    platform TEXT NOT NULL,
    target_id TEXT NOT NULL,
    idempotency_key TEXT UNIQUE NOT NULL,
    request_hash TEXT NOT NULL,
    response_id TEXT,
    retry_after INTEGER,
    result TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS content_declarations (
    id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL,
    sku TEXT NOT NULL,
    purchase_status TEXT NOT NULL,
    gifted INTEGER NOT NULL DEFAULT 0,
    sponsored INTEGER NOT NULL DEFAULT 0,
    affiliate INTEGER NOT NULL DEFAULT 0,
    promo_code INTEGER NOT NULL DEFAULT 0,
    paid_partnership INTEGER NOT NULL DEFAULT 0,
    product_tag INTEGER NOT NULL DEFAULT 0,
    platform TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    final_decision_json TEXT NOT NULL,
    source_ids_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS policy_rules (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    rule_version TEXT UNIQUE NOT NULL,
    source_url TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    decision_logic_ref TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS creator_watchlist (
    id TEXT PRIMARY KEY,
    creator_handle TEXT NOT NULL,
    display_name TEXT NOT NULL,
    platform TEXT NOT NULL,
    relationship_context TEXT NOT NULL,
    source_type TEXT NOT NULL,
    consent_source TEXT NOT NULL,
    close_friend INTEGER NOT NULL DEFAULT 0,
    snoozed INTEGER NOT NULL DEFAULT 0,
    last_seen TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    UNIQUE(platform, creator_handle)
);

CREATE TABLE IF NOT EXISTS compliance_incidents (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    post_id TEXT NOT NULL,
    reference_code TEXT NOT NULL,
    alleged_reason TEXT NOT NULL,
    evidence_json TEXT,
    notification_time TEXT NOT NULL,
    deadline TEXT,
    status TEXT NOT NULL,
    appeal_draft_id TEXT
);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    data_classification TEXT NOT NULL,
    result_summary TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS system_settings (
    account_id TEXT PRIMARY KEY,
    instagram_mode TEXT NOT NULL DEFAULT 'DRAFT',
    tiktok_mode TEXT NOT NULL DEFAULT 'DRAFT',
    emergency_stop INTEGER NOT NULL DEFAULT 0,
    max_daily_actions INTEGER NOT NULL DEFAULT 100,
    quiet_hours TEXT NOT NULL DEFAULT '23:00-07:00',
    model_budget_gbp REAL NOT NULL DEFAULT 5.00,
    hard_monthly_ceiling_gbp REAL NOT NULL DEFAULT 30.00,
    retention_days INTEGER NOT NULL DEFAULT 90,
    brand_voice_notes TEXT NOT NULL,
    setup_wizard_step INTEGER NOT NULL DEFAULT 6
);
