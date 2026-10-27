"""
Agent Echo (Agent 5) — Security, Cryptography, OAuth PKCE, CSRF & RBAC Module.

Provides pure Python 3.9+ standard-library implementations of:
1. Authenticated Envelope Encryption at rest (`ARAIM-ENC-V1`) for OAuth tokens and receipt evidence
   using PBKDF2-HMAC-SHA256 key derivation, SHA-256 counter-mode stream encryption, and
   constant-time HMAC-SHA256 authentication tag verification (zero plaintext secrets on disk or logs).
2. OAuth 2.0 PKCE (`S256`) `code_verifier` / `code_challenge` and signed `state` token generator/validator.
3. Constant-time Webhook HMAC-SHA256 signature verification (Meta & TikTok webhooks).
4. Signed expiring CSRF token generation and validation.
5. RBAC owner verification (`@annreveals`) and log secret redaction filter.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import struct
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


class SecurityError(Exception):
    """Base exception for security and cryptographic failures."""


class TamperDetectedError(SecurityError):
    """Raised when ciphertext, associated data, or authentication tag fails HMAC verification."""


class CSRFValidationError(SecurityError):
    """Raised when a CSRF token is missing, malformed, expired, or forged."""


class RBACPermissionError(SecurityError):
    """Raised when an unauthenticated or non-owner principal attempts a privileged action."""


class OAuthStateError(SecurityError):
    """Raised when an OAuth 2.0 callback state parameter is invalid or expired."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padding = "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode((text + padding).encode("ascii"))


def _counter_keystream(enc_key: bytes, nonce: bytes, length: int) -> bytes:
    """Generate a deterministic cryptographic stream using HMAC-SHA256 in counter mode."""
    blocks = []
    counter = 0
    produced = 0
    while produced < length:
        counter_bytes = struct.pack(">Q", counter)
        block = hmac.new(enc_key, nonce + counter_bytes, hashlib.sha256).digest()
        blocks.append(block)
        produced += len(block)
        counter += 1
    return b"".join(blocks)[:length]


def _xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


class EnvelopeEncryptor:
    """
    Authenticated Envelope Encryption (`ARAIM-ENC-V1`) for OAuth tokens and receipt evidence.

    Envelope structure (JSON base64url encoded or dict):
      - v: "ARAIM-ENC-V1"
      - kid: Key ID (supports seamless secret rotation)
      - salt: 16-byte random salt (base64url)
      - nonce: 16-byte random nonce (base64url)
      - aad: Authenticated Associated Data binding context (e.g. platform/account/purpose)
      - ct: Ciphertext (base64url)
      - tag: 32-byte HMAC-SHA256 authentication tag over (v || kid || salt || nonce || aad || ct)
    """

    VERSION = "ARAIM-ENC-V1"
    PBKDF2_ITERATIONS = 60_000

    def __init__(
        self,
        master_key: Optional[str] = None,
        key_id: str = "k1",
        historical_keys: Optional[Dict[str, str]] = None,
    ) -> None:
        raw_key = master_key or os.environ.get(
            "ARAIM_MASTER_KEY", "araim-default-dev-master-key-change-in-prod-32b!"
        )
        if len(raw_key) < 16:
            raise ValueError("Master encryption key must be at least 16 characters.")
        self._active_key_id = key_id
        self._key_ring: Dict[str, bytes] = {key_id: raw_key.encode("utf-8")}
        if historical_keys:
            for k_id, k_val in historical_keys.items():
                self._key_ring[k_id] = k_val.encode("utf-8")

    @property
    def active_key_id(self) -> str:
        return self._active_key_id

    def rotate_key(self, new_key_id: str, new_master_key: str) -> None:
        """Register a new active encryption key while keeping previous keys for decryption."""
        if len(new_master_key) < 16:
            raise ValueError("New master encryption key must be at least 16 characters.")
        self._key_ring[new_key_id] = new_master_key.encode("utf-8")
        self._active_key_id = new_key_id

    def _derive_subkeys(self, key_id: str, salt: bytes) -> Tuple[bytes, bytes]:
        if key_id not in self._key_ring:
            raise TamperDetectedError(f"Unknown encryption key ID: {key_id}")
        master_bytes = self._key_ring[key_id]
        derived = hashlib.pbkdf2_hmac(
            "sha256", master_bytes, salt, self.PBKDF2_ITERATIONS, dklen=64
        )
        return derived[:32], derived[32:64]

    @staticmethod
    def _canonical_auth_payload(
        version: str,
        key_id: str,
        salt: bytes,
        nonce: bytes,
        aad: bytes,
        ciphertext: bytes,
    ) -> bytes:
        v_bytes = version.encode("utf-8")
        k_bytes = key_id.encode("utf-8")
        return (
            struct.pack(">I", len(v_bytes))
            + v_bytes
            + struct.pack(">I", len(k_bytes))
            + k_bytes
            + struct.pack(">I", len(salt))
            + salt
            + struct.pack(">I", len(nonce))
            + nonce
            + struct.pack(">I", len(aad))
            + aad
            + struct.pack(">I", len(ciphertext))
            + ciphertext
        )

    def encrypt_bytes(self, plaintext: bytes, associated_data: str = "") -> str:
        """Encrypt raw bytes into a compact, tamper-evident `ARAIM-ENC-V1` token string."""
        salt = secrets.token_bytes(16)
        nonce = secrets.token_bytes(16)
        key_id = self._active_key_id
        enc_key, mac_key = self._derive_subkeys(key_id, salt)

        keystream = _counter_keystream(enc_key, nonce, len(plaintext))
        ciphertext = _xor_bytes(plaintext, keystream)
        aad_bytes = associated_data.encode("utf-8")

        auth_payload = self._canonical_auth_payload(
            self.VERSION, key_id, salt, nonce, aad_bytes, ciphertext
        )
        tag = hmac.new(mac_key, auth_payload, hashlib.sha256).digest()

        envelope = {
            "v": self.VERSION,
            "kid": key_id,
            "salt": _b64url_encode(salt),
            "nonce": _b64url_encode(nonce),
            "aad": associated_data,
            "ct": _b64url_encode(ciphertext),
            "tag": _b64url_encode(tag),
        }
        serialized = json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return f"{self.VERSION}.{_b64url_encode(serialized)}"

    def decrypt_bytes(self, token: str, expected_associated_data: Optional[str] = None) -> bytes:
        """
        Verify constant-time HMAC-SHA256 authentication tag and decrypt bytes.
        Raises `TamperDetectedError` on any modification to token, ciphertext, or AAD.
        """
        if not token or not isinstance(token, str) or "." not in token:
            raise TamperDetectedError("Malformed encrypted token header.")
        prefix, encoded_body = token.split(".", 1)
        if prefix != self.VERSION:
            raise TamperDetectedError(f"Unsupported encryption version: {prefix}")

        try:
            raw_json = _b64url_decode(encoded_body)
            envelope = json.loads(raw_json.decode("utf-8"))
            version = str(envelope["v"])
            key_id = str(envelope["kid"])
            salt = _b64url_decode(envelope["salt"])
            nonce = _b64url_decode(envelope["nonce"])
            aad_str = str(envelope.get("aad", ""))
            ciphertext = _b64url_decode(envelope["ct"])
            provided_tag = _b64url_decode(envelope["tag"])
        except Exception as exc:
            raise TamperDetectedError("Corrupted encrypted envelope structure.") from exc

        if version != self.VERSION:
            raise TamperDetectedError("Envelope version mismatch.")

        if expected_associated_data is not None and not hmac.compare_digest(
            aad_str.encode("utf-8"), expected_associated_data.encode("utf-8")
        ):
            raise TamperDetectedError("Associated data context mismatch.")

        enc_key, mac_key = self._derive_subkeys(key_id, salt)
        auth_payload = self._canonical_auth_payload(
            version, key_id, salt, nonce, aad_str.encode("utf-8"), ciphertext
        )
        expected_tag = hmac.new(mac_key, auth_payload, hashlib.sha256).digest()

        if not hmac.compare_digest(expected_tag, provided_tag):
            raise TamperDetectedError("HMAC authentication tag verification failed: tamper detected.")

        keystream = _counter_keystream(enc_key, nonce, len(ciphertext))
        return _xor_bytes(ciphertext, keystream)

    def encrypt_json(self, payload: Dict[str, Any], associated_data: str = "") -> str:
        """Encrypt a dictionary (e.g. OAuth grant or receipt metadata) at rest."""
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return self.encrypt_bytes(raw, associated_data=associated_data)

    def decrypt_json(
        self, token: str, expected_associated_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify and decrypt a dictionary payload."""
        raw = self.decrypt_bytes(token, expected_associated_data=expected_associated_data)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise TamperDetectedError("Decrypted payload is not valid JSON.") from exc

    def reencrypt_token(self, token: str, expected_associated_data: Optional[str] = None) -> str:
        """Decrypt with historical key and re-encrypt under current active key (`FR-044`)."""
        aad = expected_associated_data or ""
        plaintext = self.decrypt_bytes(token, expected_associated_data=expected_associated_data)
        return self.encrypt_bytes(plaintext, associated_data=aad)


@dataclass(frozen=True)
class OAuthPKCEChallenge:
    """OAuth 2.0 PKCE (`S256`) and signed state bundle (`NFR-05`)."""

    platform: str
    code_verifier: str
    code_challenge: str
    code_challenge_method: str
    state: str
    created_at: int
    expires_at: int


class OAuthSecurityManager:
    """Manages OAuth 2.0 PKCE generation, state validation, and encrypted token storage."""

    def __init__(self, encryptor: Optional[EnvelopeEncryptor] = None, state_secret: Optional[str] = None) -> None:
        self.encryptor = encryptor or EnvelopeEncryptor()
        raw_secret = state_secret or os.environ.get(
            "ARAIM_OAUTH_STATE_SECRET", "araim-oauth-state-secret-key-2026"
        )
        self._state_key = raw_secret.encode("utf-8")

    def create_pkce_challenge(self, platform: str, owner_id: str = "@annreveals", ttl_seconds: int = 600) -> OAuthPKCEChallenge:
        """Generate RFC 7636 S256 PKCE `code_verifier`, `code_challenge`, and HMAC-signed `state`."""
        verifier_bytes = secrets.token_bytes(48)
        code_verifier = _b64url_encode(verifier_bytes)
        challenge_digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = _b64url_encode(challenge_digest)

        now = int(time.time())
        exp = now + ttl_seconds
        nonce = secrets.token_hex(12)
        state_body = f"{platform}:{owner_id}:{now}:{exp}:{nonce}"
        sig = hmac.new(self._state_key, state_body.encode("utf-8"), hashlib.sha256).hexdigest()
        signed_state = _b64url_encode(f"{state_body}:{sig}".encode("utf-8"))

        return OAuthPKCEChallenge(
            platform=platform,
            code_verifier=code_verifier,
            code_challenge=code_challenge,
            code_challenge_method="S256",
            state=signed_state,
            created_at=now,
            expires_at=exp,
        )

    def verify_oauth_state(
        self, signed_state: str, expected_platform: str, expected_owner_id: str = "@annreveals", now: Optional[int] = None
    ) -> Dict[str, Any]:
        """Verify constant-time HMAC signature, platform binding, and expiry of an OAuth `state` parameter."""
        try:
            decoded = _b64url_decode(signed_state).decode("utf-8")
            platform, owner_id, iat_str, exp_str, nonce, provided_sig = decoded.split(":", 5)
            iat = int(iat_str)
            exp = int(exp_str)
        except Exception as exc:
            raise OAuthStateError("Malformed OAuth state parameter.") from exc

        state_body = f"{platform}:{owner_id}:{iat}:{exp}:{nonce}"
        expected_sig = hmac.new(self._state_key, state_body.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_sig, provided_sig):
            raise OAuthStateError("OAuth state signature mismatch.")
        if platform != expected_platform:
            raise OAuthStateError(f"OAuth state platform mismatch: expected {expected_platform}, got {platform}")
        if owner_id != expected_owner_id:
            raise OAuthStateError("OAuth state owner mismatch.")

        current_time = int(time.time()) if now is None else now
        if current_time > exp:
            raise OAuthStateError("OAuth state parameter has expired.")

        return {
            "platform": platform,
            "owner_id": owner_id,
            "issued_at": iat,
            "expires_at": exp,
            "nonce": nonce,
        }

    def seal_oauth_grant(
        self,
        platform: str,
        account_id: str,
        access_token: str,
        refresh_token: Optional[str],
        scopes: list[str],
        expires_in: int = 3600,
    ) -> str:
        """Encrypt an OAuth token grant with platform+account associated data binding (`FR-038`, `NFR-05`)."""
        aad = f"oauth:{platform}:{account_id}"
        payload = {
            "platform": platform,
            "account_id": account_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "scopes": list(scopes),
            "issued_at": int(time.time()),
            "expires_at": int(time.time()) + int(expires_in),
        }
        return self.encryptor.encrypt_json(payload, associated_data=aad)

    def unseal_oauth_grant(self, encrypted_grant: str, platform: str, account_id: str) -> Dict[str, Any]:
        """Verify and decrypt an OAuth token grant for a specific platform and account."""
        aad = f"oauth:{platform}:{account_id}"
        return self.encryptor.decrypt_json(encrypted_grant, expected_associated_data=aad)


class CSRFProtection:
    """Stateless HMAC-SHA256 CSRF token issuer and constant-time validator (`NFR-05`)."""

    def __init__(self, secret_key: Optional[str] = None, ttl_seconds: int = 7200) -> None:
        raw = secret_key or os.environ.get("ARAIM_CSRF_SECRET", "araim-csrf-secret-key-2026")
        self._secret = raw.encode("utf-8")
        self.ttl_seconds = ttl_seconds

    def generate_token(self, session_id: str, owner_id: str = "@annreveals", now: Optional[int] = None) -> str:
        ts = int(time.time()) if now is None else now
        nonce = secrets.token_hex(12)
        payload = f"{session_id}|{owner_id}|{ts}|{nonce}"
        sig = hmac.new(self._secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return _b64url_encode(f"{payload}|{sig}".encode("utf-8"))

    def validate_token(
        self, token: str, expected_session_id: str, expected_owner_id: str = "@annreveals", now: Optional[int] = None
    ) -> bool:
        if not token or not isinstance(token, str):
            raise CSRFValidationError("Missing CSRF token.")
        try:
            decoded = _b64url_decode(token).decode("utf-8")
            session_id, owner_id, ts_str, nonce, provided_sig = decoded.split("|", 4)
            ts = int(ts_str)
        except Exception as exc:
            raise CSRFValidationError("Malformed CSRF token.") from exc

        payload = f"{session_id}|{owner_id}|{ts}|{nonce}"
        expected_sig = hmac.new(self._secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, provided_sig):
            raise CSRFValidationError("CSRF token signature mismatch.")
        if session_id != expected_session_id or owner_id != expected_owner_id:
            raise CSRFValidationError("CSRF token session/owner binding mismatch.")

        current_time = int(time.time()) if now is None else now
        if current_time - ts > self.ttl_seconds or ts > current_time + 60:
            raise CSRFValidationError("CSRF token has expired.")
        return True


@dataclass(frozen=True)
class OwnerPrincipal:
    """Authenticated principal representation for RBAC enforcement."""

    user_id: str
    handle: str
    role: str
    authenticated: bool = True
    mfa_verified: bool = True


class RBACGuard:
    """Role-Based Access Control enforcing owner-only administrative and write operations (`NFR-05`)."""

    ALLOWED_OWNER_HANDLES = {"@annreveals", "annreveals"}
    PRIVILEGED_ROLES = {"OWNER", "ADMIN"}

    @classmethod
    def verify_owner(cls, principal: Optional[OwnerPrincipal], action: str = "manage_platform") -> bool:
        if principal is None or not principal.authenticated:
            raise RBACPermissionError(f"Unauthenticated access denied for action '{action}'.")
        if principal.role not in cls.PRIVILEGED_ROLES:
            raise RBACPermissionError(
                f"Role '{principal.role}' is not authorized to perform '{action}'."
            )
        if principal.handle.lower() not in cls.ALLOWED_OWNER_HANDLES:
            raise RBACPermissionError(
                f"Handle '{principal.handle}' is not authorized owner '@annreveals'."
            )
        return True


def verify_webhook_hmac(
    payload_bytes: bytes,
    signature_header: str,
    webhook_secret: str,
    prefix: str = "sha256=",
) -> bool:
    """
    Verify incoming Meta (`X-Hub-Signature-256`) or TikTok webhook HMAC-SHA256 signatures
    using constant-time comparison (`hmac.compare_digest`).
    """
    if not signature_header or not webhook_secret:
        return False
    clean_sig = signature_header.strip()
    if prefix and clean_sig.startswith(prefix):
        clean_sig = clean_sig[len(prefix) :]
    expected = hmac.new(
        webhook_secret.encode("utf-8"), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected.lower(), clean_sig.lower())


class SecretScrubber:
    """Ensures zero plaintext secrets, OAuth tokens, or encryption keys ever appear in logs (`NFR-05`)."""

    _PATTERNS = [
        (re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
        (
            re.compile(
                r'("(?:access_token|refresh_token|client_secret|app_secret|master_key|password|authorization)"\s*:\s*)"[^"]*"',
                re.IGNORECASE,
            ),
            r'\1"[REDACTED_SECRET]"',
        ),
        (
            re.compile(
                r"((?:access_token|refresh_token|client_secret|api_key|secret)=)[^\s&]+",
                re.IGNORECASE,
            ),
            r"\1[REDACTED_SECRET]",
        ),
        (re.compile(r"ARAIM-ENC-V1\.[A-Za-z0-9_\-]+"), "ARAIM-ENC-V1.[REDACTED_CIPHERTEXT]"),
    ]

    @classmethod
    def scrub(cls, text: str) -> str:
        scrubbed = text
        for pattern, replacement in cls._PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)
        return scrubbed
