"""AES-GCM compatibility, authentication, and legacy migration regression checks."""

import base64
import json
import unittest

from apps.backend.platform_ops.security import EnvelopeEncryptor, TamperDetectedError


def unpack(token):
    prefix, body = token.split(".", 1)
    return prefix, json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))


def repack(prefix, envelope):
    encoded = base64.urlsafe_b64encode(json.dumps(envelope).encode()).decode().rstrip("=")
    return prefix + "." + encoded


class TestAESGCMEnvelope(unittest.TestCase):
    def setUp(self):
        self.encryptor = EnvelopeEncryptor(master_key="legacy-master-key-private-32-characters")

    def test_new_writes_use_fresh_gcm_nonce_and_authenticated_metadata(self):
        first = self.encryptor.encrypt_bytes(b"private evidence", "receipt:owner")
        second = self.encryptor.encrypt_bytes(b"private evidence", "receipt:owner")
        prefix, original = unpack(first)
        self.assertEqual(prefix, "ARAIM-ENC-V2")
        self.assertNotEqual(first, second)
        self.assertEqual(len(base64.urlsafe_b64decode(original["nonce"] + "==")), 12)
        self.assertEqual(len(base64.urlsafe_b64decode(original["tag"] + "==")), 16)
        self.assertEqual(self.encryptor.decrypt_bytes(first, "receipt:owner"), b"private evidence")
        for field in ("v", "kid", "salt", "nonce", "aad", "ct", "tag"):
            altered = dict(original)
            value = altered[field]
            altered[field] = ("A" if value[0] != "A" else "B") + value[1:]
            with self.subTest(field=field), self.assertRaises(TamperDetectedError):
                self.encryptor.decrypt_bytes(repack(prefix, altered))

    def test_existing_v1_record_migrates_to_v2_and_preserves_context(self):
        legacy = 'ARAIM-ENC-V1.eyJhYWQiOiJvYXV0aDp0aWt0b2s6YWNjb3VudC0xMjMiLCJjdCI6IjZUclBseVVuMlhLZDN4d1RVR0YtRUsyXzJReW5kM3liQTB2U08td1dQLUlCNVdiT2FxNkYiLCJraWQiOiJrMSIsIm5vbmNlIjoiRUJFU0V4UVZGaGNZR1JvYkhCMGVIdyIsInNhbHQiOiJBQUVDQXdRRkJnY0lDUW9MREEwT0R3IiwidGFnIjoiNG5nVV9zQW5iVnhleUI5N0NfRW9KQnlPV09xeTJyLWs0aU02TnN6RWIwdyIsInYiOiJBUkFJTS1FTkMtVjEifQ'
        self.assertEqual(
            self.encryptor.decrypt_json(legacy, "oauth:tiktok:account-123"),
            {"access_token": "legacy-private-token"},
        )
        migrated = self.encryptor.reencrypt_token(legacy)
        self.assertTrue(migrated.startswith("ARAIM-ENC-V2."))
        self.assertEqual(
            self.encryptor.decrypt_json(migrated, "oauth:tiktok:account-123"),
            {"access_token": "legacy-private-token"},
        )
        with self.assertRaises(TamperDetectedError):
            self.encryptor.decrypt_json(migrated, "another-account")
        prefix, envelope = unpack(legacy)
        envelope["ct"] = "A" + envelope["ct"][1:]
        with self.assertRaises(TamperDetectedError):
            self.encryptor.decrypt_bytes(repack(prefix, envelope))

    def test_empty_payload_and_key_rotation_keep_readability(self):
        encrypted = self.encryptor.encrypt_bytes(b"", "empty")
        self.encryptor.rotate_key("k2", "new-master-key-private-32-characters")
        self.assertEqual(self.encryptor.decrypt_bytes(encrypted, "empty"), b"")
        rewritten = self.encryptor.reencrypt_token(encrypted)
        self.assertEqual(unpack(rewritten)[1]["kid"], "k2")
        self.assertEqual(self.encryptor.decrypt_bytes(rewritten, "empty"), b"")
