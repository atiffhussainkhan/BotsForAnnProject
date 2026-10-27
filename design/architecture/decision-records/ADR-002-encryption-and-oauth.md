# ADR-002: Authenticated Envelope Encryption at Rest & OAuth 2.0 PKCE Security Model

- **Status:** Accepted
- **Date:** 27 October 2026
- **Author:** Agent Echo (Agent 5 — Security Engineer)
- **Requirements Addressed:** `FR-038`, `FR-043`, `FR-044`, `NFR-05`, `NFR-06`

---

## 1. Context

Ann Reveals AI Manager stores two classes of high-sensitivity assets:
1. **Independent OAuth 2.0 Grants** (access tokens, refresh tokens, scope grants) for TikTok and Meta Instagram (`FR-038`).
2. **Redacted Purchase Proof Files & Metadata** (receipt screenshots, PDFs, private prices, private order references) in the Verified Purchases Vault (`FR-018`, `FR-019`).

If the database or backup archive were ever exposed, neither OAuth tokens nor purchase evidence may be readable in plaintext. Furthermore, OAuth authorization flows must prevent interception and CSRF attacks (`NFR-05`), and the encryption implementation must be portable across any Python 3.9+ environment without fragile native C-extension build failures.

## 2. Decision

1. **Authenticated Envelope Encryption (`ARAIM-ENC-V1`)**:
   - Every sensitive secret or evidence payload is encrypted with an ephemeral per-record 16-byte random salt/nonce and an ephemeral data encryption key (DEK) derived via `PBKDF2-HMAC-SHA256` (100,000 iterations for master key derivation + per-message HKDF/SHA-256 counter keystream) and sealed with a 32-byte **HMAC-SHA256 authentication tag** over `(version || key_id || salt || nonce || associated_data || ciphertext)`.
   - Decryption verifies the HMAC-SHA256 tag in constant time (`hmac.compare_digest`) **before** decrypting a single byte. Any bit flip in ciphertext, nonce, or associated context immediately raises `TamperDetectedError`.
   - Supports seamless key rotation via versioned `key_id` headers (`FR-044`).

2. **OAuth 2.0 with PKCE (`S256`) + Cryptographic State**:
   - All TikTok and Instagram OAuth flows generate a high-entropy 64-character `code_verifier`, compute `code_challenge = BASE64URL_NOPAD(SHA256(code_verifier))`, and bind the authorization request to a signed, expiring `state` token verified in constant time upon callback.

3. **Zero Secrets in Logs**:
   - A mandatory `SecretScrubber` filter strips Bearer tokens, `access_token`, `refresh_token`, API keys, cookie headers, and encrypted blobs from all structured application and audit logs (`NFR-05`).

## 3. Consequences

### Positive
- **Cryptographic Tamper Detection:** Modifying even one byte of an encrypted OAuth token or backup archive is caught deterministically before decryption.
- **Zero Dependency Hell:** Uses Python's FIPS/OpenSSL-backed `hashlib`, `hmac`, and `secrets` modules in the standard library.
- **Independent Platform Isolation:** Revoking or rotating TikTok credentials has zero impact on Instagram OAuth tokens (`FR-038`).
