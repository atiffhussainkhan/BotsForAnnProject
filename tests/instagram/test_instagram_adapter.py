"""Unit and contract tests for the Meta / Instagram Platform Adapter (`ARAIM` v4.0).

Runnable via standard library unittest:
    python3 -m unittest discover -s tests/instagram
"""

import json
import unittest
from typing import Dict, List, Optional, Tuple

from apps.backend.integrations.instagram import (
    AutomationMode,
    ConnectionStatus,
    DispatchState,
    InstagramAdapter,
    InstagramAmbiguousTimeoutError,
    InstagramAuthError,
    InstagramError,
    InstagramRateLimitError,
    InstagramWebhookVerifier,
    SelfReplyForbiddenError,
    UnsupportedCapabilityError,
    WebhookVerificationError,
    WriteGateDisabledError,
)


class TestInstagramAdapterAndWebhooks(unittest.TestCase):
    """Comprehensive verification of Agent Bravo Instagram safety & API contracts."""

    def setUp(self) -> None:
        self.app_secret = "test_meta_app_secret_2026"
        self.verify_token = "ann_reveals_verify_token_v4"
        self.owner_id = "17841400008460056"
        self.owner_username = "annreveals"
        self.verifier = InstagramWebhookVerifier(
            app_secret=self.app_secret,
            verify_token=self.verify_token,
            owner_ig_user_id=self.owner_id,
            owner_username=self.owner_username,
        )

    def test_webhook_subscription_challenge(self) -> None:
        """Verify GET hub.mode=subscribe challenge handshake and 403 rejection on mismatch."""
        status, challenge = self.verifier.verify_subscription_challenge(
            hub_mode="subscribe",
            hub_verify_token=self.verify_token,
            hub_challenge="1158201444",
        )
        self.assertEqual(status, 200)
        self.assertEqual(challenge, "1158201444")

        with self.assertRaises(WebhookVerificationError) as ctx:
            self.verifier.verify_subscription_challenge(
                hub_mode="subscribe",
                hub_verify_token="wrong_token",
                hub_challenge="1158201444",
            )
        self.assertEqual(ctx.exception.status_code, 403)

        with self.assertRaises(WebhookVerificationError):
            self.verifier.verify_subscription_challenge(
                hub_mode="unsubscribe",
                hub_verify_token=self.verify_token,
                hub_challenge="1158201444",
            )

    def test_webhook_hmac_sha256_verification_and_deduplication(self) -> None:
        """Verify X-Hub-Signature-256 HMAC-SHA256 check, self-comment filtering, and deduplication."""
        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": self.owner_id,
                    "time": 1761569662,
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "id": "17918273645019283",
                                "text": "Does this project more like Delina or Delina Exclusif?",
                                "from": {
                                    "id": "901283746501928",
                                    "username": "scentlover_uk",
                                },
                                "media": {
                                    "id": "18029910293847561",
                                    "media_product_type": "REELS",
                                },
                            },
                        },
                        {
                            "field": "comments",
                            "value": {
                                "id": "17918273645099999",
                                "text": "Thank you lovely! Full notes are in the caption.",
                                "from": {
                                    "id": self.owner_id,
                                    "username": "annreveals",
                                },
                                "media": {
                                    "id": "18029910293847561",
                                    "media_product_type": "REELS",
                                },
                                "parent_id": "17918273645019283",
                            },
                        },
                    ],
                }
            ],
        }
        raw_body = json.dumps(payload).encode("utf-8")
        valid_sig = InstagramWebhookVerifier.compute_signature(self.app_secret, raw_body)

        # 1. Valid signature parses viewer comment and skips @annreveals self-comment
        result = self.verifier.process_webhook_payload(raw_body, valid_sig)
        self.assertEqual(len(result.actionable_comments), 1)
        self.assertEqual(result.actionable_comments[0].comment_id, "17918273645019283")
        self.assertFalse(result.actionable_comments[0].is_self)
        self.assertEqual(len(result.skipped_self_comments), 1)
        self.assertTrue(result.skipped_self_comments[0].is_self)

        # 2. Re-delivering identical webhook batch deduplicates both events
        second_result = self.verifier.process_webhook_payload(raw_body, valid_sig)
        self.assertEqual(len(second_result.actionable_comments), 0)
        self.assertEqual(len(second_result.skipped_duplicates), 2)

        # 3. Tampered signature raises 401 WebhookVerificationError
        with self.assertRaises(WebhookVerificationError) as ctx:
            self.verifier.process_webhook_payload(raw_body, "sha256=0000deadbeef")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_self_reply_loop_prevention_in_adapter(self) -> None:
        """Verify adapter refuses to reply to @annreveals's own comments (FR-003)."""
        adapter = InstagramAdapter(
            access_token="ig_sandbox_token",
            owner_ig_user_id=self.owner_id,
            owner_username=self.owner_username,
            granted_scopes=["instagram_business_basic", "instagram_business_manage_comments"],
            write_enabled=True,
            automation_mode=AutomationMode.SAFE_AUTO,
            sandbox_mode=True,
        )

        # Comment 17918273645099999 in sandbox fixtures is authored by @annreveals
        with self.assertRaises(SelfReplyForbiddenError):
            adapter.reply_to_owned_comment(
                comment_id="17918273645099999",
                message="Trying to reply to myself should fail!",
            )

        # Also test explicit author username guard even for an uncached comment ID
        with self.assertRaises(SelfReplyForbiddenError):
            adapter.reply_to_owned_comment(
                comment_id="17900000000012345",
                message="Replying to self handle",
                target_comment_author_username="@AnnReveals",
            )

    def test_timeout_reconciliation_prevents_duplicate_replies(self) -> None:
        """Verify RECONCILE_PENDING checks GET /{comment-id}/replies before retry and prevents duplicate POST."""
        call_log: List[Tuple[str, str]] = []
        reply_text = "I used 4 sprays on my coat and could still smell the vanilla the next morning!"

        def mock_transport(
            method: str,
            url: str,
            headers: Dict[str, str],
            body_bytes: Optional[bytes],
            timeout: float,
        ) -> Tuple[int, Dict[str, str], bytes]:
            call_log.append((method, url))
            # 1st call: POST /17918273645019283/replies -> Simulates network timeout AFTER Meta committed the reply
            if method == "POST" and "/17918273645019283/replies" in url and len(call_log) == 1:
                raise TimeoutError("Read timed out waiting for Graph API response")

            # 2nd call (during retry reconciliation): GET /17918273645019283/replies -> Returns the committed reply
            if method == "GET" and "/17918273645019283/replies" in url:
                response_payload = {
                    "data": [
                        {
                            "id": "17999888777666555",
                            "text": reply_text,
                            "username": "annreveals",
                            "from": {"id": self.owner_id, "username": "annreveals"},
                            "timestamp": "2026-10-27T13:10:00+0000",
                        }
                    ]
                }
                return 200, {}, json.dumps(response_payload).encode("utf-8")

            raise AssertionError(f"Unexpected HTTP call: {method} {url}")

        adapter = InstagramAdapter(
            access_token="ig_live_token",
            owner_ig_user_id=self.owner_id,
            owner_username=self.owner_username,
            granted_scopes=["instagram_business_basic", "instagram_business_manage_comments"],
            write_enabled=True,
            automation_mode=AutomationMode.SAFE_AUTO,
            sandbox_mode=False,
            http_transport=mock_transport,
        )

        idem_key = "idem_reply_17918273645019283"

        # Attempt 1 times out and marks record as RECONCILE_PENDING
        with self.assertRaises(InstagramAmbiguousTimeoutError):
            adapter.reply_to_owned_comment(
                comment_id="17918273645019283",
                message=reply_text,
                idempotency_key=idem_key,
                target_comment_author_id="901283746501928",
                target_comment_author_username="scentlover_uk",
            )

        record_after_timeout = adapter._dispatch_records[idem_key]
        self.assertEqual(record_after_timeout.state, DispatchState.RECONCILE_PENDING)

        # Attempt 2 reconciles via GET /replies, finds the existing reply, and NEVER sends a second POST
        reconciled_record = adapter.reply_to_owned_comment(
            comment_id="17918273645019283",
            message=reply_text,
            idempotency_key=idem_key,
            target_comment_author_id="901283746501928",
            target_comment_author_username="scentlover_uk",
        )
        self.assertEqual(reconciled_record.state, DispatchState.SENT_RECONCILED)
        self.assertTrue(reconciled_record.reconciled_from_existing)
        self.assertEqual(reconciled_record.external_comment_id, "17999888777666555")

        # Verify only 1 POST and 1 GET were made (zero duplicate POSTs!)
        post_calls = [c for c in call_log if c[0] == "POST"]
        get_calls = [c for c in call_log if c[0] == "GET"]
        self.assertEqual(len(post_calls), 1)
        self.assertEqual(len(get_calls), 1)

    def test_forbidden_nonowned_post_commenting_and_following_feed(self) -> None:
        """Verify comment_on_nonowned_post and get_following_posts are permanently blocked."""
        adapter = InstagramAdapter(
            access_token="ig_sandbox_token",
            granted_scopes=["instagram_business_basic", "instagram_business_manage_comments"],
            write_enabled=True,
            automation_mode=AutomationMode.SAFE_AUTO,
            sandbox_mode=True,
        )
        with self.assertRaises(UnsupportedCapabilityError):
            adapter.comment_on_nonowned_post(post_id="other_creator_post_999", message="Nice post!")

        with self.assertRaises(UnsupportedCapabilityError):
            adapter.get_following_posts()

    def test_401_403_token_revocation_fail_safe(self) -> None:
        """Verify HTTP 401/403 (Meta Code 190) transitions adapter to Needs reconnect + DRAFT and disables writes."""

        def revoked_token_transport(
            method: str,
            url: str,
            headers: Dict[str, str],
            body_bytes: Optional[bytes],
            timeout: float,
        ) -> Tuple[int, Dict[str, str], bytes]:
            err = {
                "error": {
                    "message": "Error validating access token: Session has expired or been revoked.",
                    "type": "OAuthException",
                    "code": 190,
                    "error_subcode": 460,
                }
            }
            return 401, {}, json.dumps(err).encode("utf-8")

        adapter = InstagramAdapter(
            access_token="revoked_token",
            owner_ig_user_id=self.owner_id,
            owner_username=self.owner_username,
            granted_scopes=["instagram_business_basic", "instagram_business_manage_comments"],
            write_enabled=True,
            automation_mode=AutomationMode.SAFE_AUTO,
            sandbox_mode=False,
            http_transport=revoked_token_transport,
        )
        self.assertEqual(adapter.connection_status, ConnectionStatus.LIVE_CAN_REPLY)

        with self.assertRaises(InstagramAuthError):
            adapter.get_owned_profile()

        self.assertEqual(adapter.connection_status, ConnectionStatus.NEEDS_RECONNECT)
        self.assertEqual(adapter.automation_mode, AutomationMode.DRAFT)
        self.assertFalse(adapter.write_enabled)

    def test_rate_limit_backoff_handling(self) -> None:
        """Verify HTTP 429 / Meta error code 4 surfaces Retry-After seconds."""

        def rate_limited_transport(
            method: str,
            url: str,
            headers: Dict[str, str],
            body_bytes: Optional[bytes],
            timeout: float,
        ) -> Tuple[int, Dict[str, str], bytes]:
            err = {
                "error": {
                    "message": "Application request limit reached",
                    "type": "OAuthException",
                    "code": 4,
                }
            }
            return 429, {"retry-after": "60"}, json.dumps(err).encode("utf-8")

        adapter = InstagramAdapter(
            access_token="valid_token",
            granted_scopes=["instagram_business_basic"],
            sandbox_mode=False,
            http_transport=rate_limited_transport,
        )
        with self.assertRaises(InstagramRateLimitError) as ctx:
            adapter.get_owned_posts()
        self.assertEqual(ctx.exception.retry_after_seconds, 60)

    def test_sandbox_comment_read_and_reply_flow_with_write_gate(self) -> None:
        """Verify default write gate blocks writes until enabled, then sandbox read/reply/ownership comment succeed."""
        adapter = InstagramAdapter(
            access_token="ig_sandbox_token",
            owner_ig_user_id=self.owner_id,
            owner_username=self.owner_username,
            granted_scopes=["instagram_business_basic", "instagram_business_manage_comments"],
            write_enabled=False,  # Default safe state
            automation_mode=AutomationMode.DRAFT,
            sandbox_mode=True,
        )
        self.assertEqual(adapter.connection_status, ConnectionStatus.CONNECTED_READ_ONLY)

        # 1. Read profile, owned posts, and comments in read-only mode
        profile = adapter.get_owned_profile()
        self.assertEqual(profile.username, "annreveals")
        self.assertTrue(profile.is_professional)

        posts_page = adapter.get_owned_posts()
        self.assertEqual(len(posts_page.items), 1)
        post_id = posts_page.items[0].post_id

        comments_page = adapter.list_owned_comments(post_id=post_id)
        self.assertEqual(len(comments_page.items), 2)

        # 2. Attempting to reply while write_enabled=False raises WriteGateDisabledError
        with self.assertRaises(WriteGateDisabledError):
            adapter.reply_to_owned_comment(
                comment_id="17918273645019283",
                message="Thank you! I used 4 sprays.",
            )

        # 3. Enable write gate after pilot approval and verify reply + ownership comment
        adapter.write_enabled = True
        adapter.automation_mode = AutomationMode.SAFE_AUTO
        adapter.connection_status = adapter._compute_connection_status()
        self.assertEqual(adapter.connection_status, ConnectionStatus.LIVE_CAN_REPLY)

        reply_record = adapter.reply_to_owned_comment(
            comment_id="17918273645019283",
            message="I used 4 sprays — two on wrists and two on my scarf!",
        )
        self.assertEqual(reply_record.state, DispatchState.SENT)
        self.assertIsNotNone(reply_record.external_comment_id)

        # 4. Create first-party ownership comment and verify anti-spam duplicate guard (FR-055)
        ownership_msg = "Purchased with my own money from Empyrean. These are my personal impressions after a 7-day wear test."
        post_comment_record = adapter.create_comment_on_owned_post(
            post_id=post_id,
            message=ownership_msg,
        )
        self.assertEqual(post_comment_record.state, DispatchState.SENT)

        with self.assertRaises(InstagramError):
            adapter.create_comment_on_owned_post(
                post_id="another_post_id",
                message=ownership_msg,
            )


if __name__ == "__main__":
    unittest.main()
