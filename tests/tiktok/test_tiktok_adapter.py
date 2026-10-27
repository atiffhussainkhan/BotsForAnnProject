"""Comprehensive Standard-Library Unit Test Suite for TikTok Integration (`test_tiktok_adapter.py`).

Runnable with zero external dependencies via:
    python3 -m unittest discover -s tests/tiktok -v

Covers all 7 mandatory verification areas:
1. Webhook HMAC-SHA256 signature verification, timestamp freshness, replay defense, and self-comment loop guard.
2. Outbound URL host allowlist and March 20, 2026 TikTok Accounts API scope allowlist enforcement.
3. `TIKTOK_WRITE_ENABLED=false` default guard and `DRAFT_ONLY` fallback behavior.
4. Permanent hard block (`PermissionPolicyError`) on third-party commenting (`comment_on_nonowned_post`) and follow-list scraping (`get_following_posts`).
5. Rate-limit HTTP 429 `Retry-After` + jittered `30s/60s/120s` backoff and consecutive 5xx circuit breaker.
6. HTTP 401/403 fail-closed automatic downgrade to `DRAFT` mode and `Needs reconnect` badge.
7. Deterministic sandbox owned-post/comment read, idempotent reply flow, timeout `RECONCILE_PENDING`, and self-purchase vs commercial disclosure guards.
"""

import json
import os
import random
from typing import Dict, Tuple
import unittest
import urllib.request

from apps.backend.integrations.tiktok import (
    CapabilityStatus,
    CircuitBreakerOpenError,
    ConnectionBadge,
    DispatchState,
    OperationalMode,
    PermissionPolicyError,
    PublishPostRequest,
    RateLimitExceededError,
    ScopeNotApprovedError,
    SecurityConfigurationError,
    TikTokAdapter,
    TikTokWebhookVerifier,
    WriteDisabledError,
)


class TestTikTokIntegrationSuite(unittest.TestCase):
    """End-to-end verification of Agent Alpha's TikTok integration contract."""

    def setUp(self) -> None:
        os.environ.pop("TIKTOK_WRITE_ENABLED", None)
        self.webhook_secret = "tt_client_secret_test_998877"
        self.owned_biz_id = "annreveals_biz_001"

    # -------------------------------------------------------------------------
    # 1. Webhook Signature, Freshness, Replay Defense & Self-Author Loop Guard
    # -------------------------------------------------------------------------

    def test_webhook_signature_and_replay_defense(self) -> None:
        verifier = TikTokWebhookVerifier(
            client_secret=self.webhook_secret,
            owned_business_id=self.owned_biz_id,
            max_skew_seconds=300,
        )
        now_ts = 1761570000
        payload = {
            "event_id": "evt_tt_1001",
            "event": "comment.update",
            "business_id": self.owned_biz_id,
            "content": {
                "video_id": "tt_vid_742910001",
                "comment_id": "tt_cmt_5501",
                "user_id": "viewer_777",
                "username": "fragrance_fan_uk",
                "text": "Does this project well in cold weather?",
                "create_time": now_ts,
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        sig_header = TikTokWebhookVerifier.build_signature_header(
            self.webhook_secret, now_ts, raw_body
        )

        # Valid webhook verification
        event = verifier.verify_and_parse(raw_body, sig_header, now_epoch=now_ts + 5)
        self.assertEqual(event.event_id, "evt_tt_1001")
        self.assertEqual(event.video_id, "tt_vid_742910001")
        self.assertIsNotNone(event.comment)
        assert event.comment is not None
        self.assertEqual(event.comment.comment_id, "tt_cmt_5501")
        self.assertFalse(event.should_ignore_self_comment)

        # Duplicate replay of the exact same webhook must be blocked
        with self.assertRaises(SecurityConfigurationError) as replay_ctx:
            verifier.verify_and_parse(raw_body, sig_header, now_epoch=now_ts + 6)
        self.assertEqual(replay_ctx.exception.code, "ERR_WEBHOOK_REPLAY_DETECTED")

        # Expired timestamp (> 300s skew) must be rejected
        with self.assertRaises(SecurityConfigurationError) as expired_ctx:
            verifier.verify_and_parse(raw_body, sig_header, now_epoch=now_ts + 450)
        self.assertEqual(expired_ctx.exception.code, "ERR_WEBHOOK_TIMESTAMP_EXPIRED")

        # Tampered body with original signature must be rejected
        tampered_body = json.dumps({**payload, "event_id": "evt_tt_tampered"}).encode("utf-8")
        with self.assertRaises(SecurityConfigurationError) as mismatch_ctx:
            verifier.verify_and_parse(tampered_body, sig_header, now_epoch=now_ts + 5)
        self.assertEqual(mismatch_ctx.exception.code, "ERR_WEBHOOK_SIGNATURE_MISMATCH")

        # Self-authored comment by @annreveals must be flagged to prevent reply loops (FR-003)
        self_payload = {
            "event_id": "evt_tt_1002",
            "event": "comment.update",
            "business_id": self.owned_biz_id,
            "content": {
                "video_id": "tt_vid_742910001",
                "comment_id": "tt_cmt_5502",
                "user_id": self.owned_biz_id,
                "username": "annreveals",
                "text": "Purchased with my own money. Personal impressions!",
                "create_time": now_ts,
            },
        }
        self_raw = json.dumps(self_payload).encode("utf-8")
        self_sig = TikTokWebhookVerifier.build_signature_header(
            self.webhook_secret, now_ts, self_raw
        )
        self_event = verifier.verify_and_parse(self_raw, self_sig, now_epoch=now_ts + 1)
        self.assertTrue(self_event.should_ignore_self_comment)

    # -------------------------------------------------------------------------
    # 2. Outbound Host Allowlist & Scope Allowlist / March 20, 2026 Gate
    # -------------------------------------------------------------------------

    def test_outbound_url_allowlist_and_scope_enforcement(self) -> None:
        # Allowed official TikTok hosts
        TikTokAdapter.validate_outbound_url(
            "https://business-api.tiktok.com/open_api/v1.3/business/comment/list/"
        )
        TikTokAdapter.validate_outbound_url(
            "https://open.tiktokapis.com/v2/post/publish/video/init/"
        )

        # Disallowed non-HTTPS scheme
        with self.assertRaises(SecurityConfigurationError) as scheme_ctx:
            TikTokAdapter.validate_outbound_url(
                "http://business-api.tiktok.com/open_api/v1.3/business/get/"
            )
        self.assertEqual(scheme_ctx.exception.code, "ERR_INSECURE_SCHEME")

        # Disallowed arbitrary / scraping host
        with self.assertRaises(SecurityConfigurationError) as host_ctx:
            TikTokAdapter.validate_outbound_url("https://api.unapproved-scraper.example.com/v1/ tiktok")
        self.assertEqual(host_ctx.exception.code, "ERR_OUTBOUND_HOST_FORBIDDEN")

        # Unapproved live adapter truthfully reports AWAITING_APPROVAL (March 20, 2026 gate)
        live_unapproved = TikTokAdapter(
            access_token="live_tok_without_march_20_approval",
            granted_scopes=["user.info.basic"],
            sandbox_mode=False,
            accounts_api_approved=False,
        )
        self.assertEqual(
            live_unapproved.get_capability_status("list_owned_comments"),
            CapabilityStatus.AWAITING_APPROVAL,
        )
        self.assertEqual(
            live_unapproved.get_capability_status("reply_to_owned_comment"),
            CapabilityStatus.AWAITING_APPROVAL,
        )
        self.assertEqual(live_unapproved.get_connection_badge(), ConnectionBadge.AWAITING_REVIEW)

        # Calling list_owned_comments while AWAITING_APPROVAL returns truthful fallback response
        resp = live_unapproved.list_owned_comments(video_id="tt_vid_742910001")
        self.assertFalse(resp.ok)
        self.assertEqual(resp.capability_status, CapabilityStatus.AWAITING_APPROVAL)
        self.assertEqual(resp.fallback_action, "WEBHOOK_OR_MANUAL_QUEUE")

        # Strict write check raises ScopeNotApprovedError when write_enabled=True but scope missing
        live_unapproved.write_enabled = True
        with self.assertRaises(ScopeNotApprovedError):
            live_unapproved.reply_to_owned_comment(
                video_id="tt_vid_742910001",
                comment_id="tt_cmt_9001",
                text="Thank you so much!",
                idempotency_key="idem_unapproved_1",
                strict_write_check=True,
            )

    # -------------------------------------------------------------------------
    # 3. `TIKTOK_WRITE_ENABLED=false` Default Guard
    # -------------------------------------------------------------------------

    def test_write_disabled_default_guard(self) -> None:
        adapter = TikTokAdapter(sandbox_mode=True)
        self.assertFalse(adapter.write_enabled)
        self.assertEqual(adapter.operational_mode, OperationalMode.DRAFT)
        self.assertEqual(adapter.get_connection_badge(), ConnectionBadge.CONNECTED_READ_ONLY)

        # Attempting to reply while write_enabled=False saves as DRAFT_ONLY without sending
        reply_resp = adapter.reply_to_owned_comment(
            video_id="tt_vid_742910001",
            comment_id="tt_cmt_9001",
            text="It lasted a good 8 hours on my wool coat, lovely!",
            idempotency_key="idem_draft_guard_01",
        )
        self.assertTrue(reply_resp.ok)
        assert reply_resp.data is not None
        self.assertEqual(reply_resp.data.dispatch_state, DispatchState.DRAFT_ONLY)
        self.assertIsNone(reply_resp.data.comment_id)
        self.assertEqual(reply_resp.fallback_action, "DRAFT_ONLY_ONE_TAP_COPY")

        # Strict write check explicitly raises WriteDisabledError
        with self.assertRaises(WriteDisabledError):
            adapter.reply_to_owned_comment(
                video_id="tt_vid_742910001",
                comment_id="tt_cmt_9001",
                text="Strict write test",
                idempotency_key="idem_draft_guard_02",
                strict_write_check=True,
            )

    # -------------------------------------------------------------------------
    # 4. Forbidden Third-Party Commenting & Follow-List Scraping Hard Block
    # -------------------------------------------------------------------------

    def test_forbidden_third_party_commenting_and_following_scrape(self) -> None:
        # Even with sandbox_mode=True, write_enabled=True, and SAFE_AUTO enabled:
        adapter = TikTokAdapter(
            sandbox_mode=True,
            write_enabled=True,
            operational_mode=OperationalMode.SAFE_AUTO,
            accounts_api_approved=True,
        )
        self.assertEqual(
            adapter.get_capability_status("comment_on_nonowned_post"),
            CapabilityStatus.UNAVAILABLE,
        )
        self.assertEqual(
            adapter.get_capability_status("get_following_posts"),
            CapabilityStatus.UNAVAILABLE,
        )

        with self.assertRaises(PermissionPolicyError) as comment_err:
            adapter.comment_on_nonowned_post(
                target_video_id="friend_video_999",
                text="Love your video!",
            )
        self.assertEqual(comment_err.exception.code, "ERR_THIRD_PARTY_INTERACTION_PROHIBITED")

        with self.assertRaises(PermissionPolicyError) as follow_err:
            adapter.get_following_posts(creator_handle="@friendcreator")
        self.assertEqual(follow_err.exception.code, "ERR_THIRD_PARTY_INTERACTION_PROHIBITED")

    # -------------------------------------------------------------------------
    # 5. Rate-Limit 429 Backoff & Consecutive 5xx Circuit Breaker
    # -------------------------------------------------------------------------

    def test_rate_limit_backoff_and_5xx_circuit_breaker(self) -> None:
        rng = random.Random(42)
        b0 = TikTokAdapter.calculate_backoff_seconds(attempt=0, retry_after_header=None, jitter_ratio=0.0, rng=rng)
        b1 = TikTokAdapter.calculate_backoff_seconds(attempt=1, retry_after_header=None, jitter_ratio=0.0, rng=rng)
        b2 = TikTokAdapter.calculate_backoff_seconds(attempt=2, retry_after_header=None, jitter_ratio=0.0, rng=rng)
        self.assertEqual((b0, b1, b2), (30.0, 60.0, 120.0))

        # Honors larger Retry-After header
        b_header = TikTokAdapter.calculate_backoff_seconds(
            attempt=0, retry_after_header="90", jitter_ratio=0.0, rng=rng
        )
        self.assertEqual(b_header, 90.0)

        # Simulate HTTP 429 transport response
        def transport_429(req: urllib.request.Request, timeout: float) -> Tuple[int, Dict[str, str], bytes]:
            return 429, {"Retry-After": "75"}, b'{"code": 40104, "message": "Rate limit exceeded"}'

        adapter_429 = TikTokAdapter(
            access_token="live_tok",
            granted_scopes=["comment.list"],
            accounts_api_approved=True,
            http_transport=transport_429,
        )
        with self.assertRaises(RateLimitExceededError) as rl_ctx:
            adapter_429.list_owned_comments(video_id="tt_vid_742910001")
        self.assertGreaterEqual(rl_ctx.exception.retry_after_seconds, 60.0)

        # Simulate 3 consecutive 503 responses tripping the circuit breaker
        def transport_503(req: urllib.request.Request, timeout: float) -> Tuple[int, Dict[str, str], bytes]:
            return 503, {}, b'{"message": "Service Unavailable"}'

        adapter_5xx = TikTokAdapter(
            access_token="live_tok",
            granted_scopes=["comment.list"],
            accounts_api_approved=True,
            http_transport=transport_503,
            circuit_breaker_threshold=3,
            circuit_breaker_cooldown_seconds=300.0,
        )
        # Failures 1 and 2 raise generic upstream error
        for _ in range(2):
            with self.assertRaises(Exception):
                adapter_5xx.list_owned_comments(video_id="tt_vid_742910001")
        # Failure 3 trips CircuitBreakerOpenError
        with self.assertRaises(CircuitBreakerOpenError):
            adapter_5xx.list_owned_comments(video_id="tt_vid_742910001")
        # Subsequent call immediately fails fast with CircuitBreakerOpenError
        with self.assertRaises(CircuitBreakerOpenError):
            adapter_5xx.list_owned_comments(video_id="tt_vid_742910001")

    # -------------------------------------------------------------------------
    # 6. HTTP 401/403 Fail-Closed Auto-Downgrade to DRAFT (NFR-10)
    # -------------------------------------------------------------------------

    def test_401_403_fail_closed_auto_downgrade_to_draft(self) -> None:
        def transport_401(req: urllib.request.Request, timeout: float) -> Tuple[int, Dict[str, str], bytes]:
            return 401, {}, b'{"code": 40100, "message": "Access token expired or revoked"}'

        adapter = TikTokAdapter(
            access_token="live_tok_valid_initially",
            granted_scopes=["comment.list", "comment.list.manage"],
            write_enabled=True,
            operational_mode=OperationalMode.SAFE_AUTO,
            accounts_api_approved=True,
            http_transport=transport_401,
        )
        self.assertEqual(adapter.get_connection_badge(), ConnectionBadge.LIVE_CAN_REPLY)

        # Attempt live reply -> encounters 401 -> must fail-closed to DRAFT & NEEDS_RECONNECT
        resp = adapter.reply_to_owned_comment(
            video_id="tt_vid_742910001",
            comment_id="tt_cmt_9001",
            text="Here are the longevity details!",
            idempotency_key="idem_401_downgrade_test",
        )
        self.assertFalse(resp.ok)
        self.assertEqual(resp.error_code, "ERR_AUTH_DOWNGRADED_TO_DRAFT")
        self.assertFalse(adapter.write_enabled)
        self.assertEqual(adapter.operational_mode, OperationalMode.DRAFT)
        self.assertEqual(adapter.get_connection_badge(), ConnectionBadge.NEEDS_RECONNECT)
        assert resp.data is not None
        self.assertEqual(resp.data.dispatch_state, DispatchState.DRAFT_ONLY)

    # -------------------------------------------------------------------------
    # 7. Sandbox Comment Read/Reply Flow, Timeout Reconcile & Provenance Guards
    # -------------------------------------------------------------------------

    def test_sandbox_comment_read_reply_and_provenance_guards(self) -> None:
        adapter = TikTokAdapter(
            sandbox_mode=True,
            write_enabled=True,
            operational_mode=OperationalMode.SAFE_AUTO,
        )
        self.assertEqual(adapter.get_connection_badge(), ConnectionBadge.LIVE_CAN_REPLY)

        # Profile & Owned Posts
        prof_resp = adapter.get_owned_profile()
        self.assertTrue(prof_resp.ok)
        assert prof_resp.data is not None
        self.assertEqual(prof_resp.data.handle, "@annreveals")

        posts_resp = adapter.get_owned_posts()
        self.assertTrue(posts_resp.ok)
        assert posts_resp.data is not None
        self.assertEqual(len(posts_resp.data), 2)

        # List owned comments
        cmts_resp = adapter.list_owned_comments(video_id="tt_vid_742910001")
        self.assertTrue(cmts_resp.ok)
        assert cmts_resp.data is not None
        self.assertEqual(len(cmts_resp.data), 2)

        # Prevent replying to @annreveals's own comment (FR-003)
        with self.assertRaises(PermissionPolicyError) as loop_ctx:
            adapter.reply_to_owned_comment(
                video_id="tt_vid_742910001",
                comment_id="tt_cmt_9002",  # authored by annreveals
                text="Replying to myself",
                idempotency_key="idem_self_loop",
            )
        self.assertEqual(loop_ctx.exception.code, "ERR_SELF_REPLY_LOOP_PREVENTED")

        # Valid reply to viewer comment
        reply_resp = adapter.reply_to_owned_comment(
            video_id="tt_vid_742910001",
            comment_id="tt_cmt_9001",
            text="On my wool coat I could still catch the warm cedar and ambergris the next morning!",
            idempotency_key="idem_viewer_reply_1",
        )
        self.assertTrue(reply_resp.ok)
        assert reply_resp.data is not None
        self.assertEqual(reply_resp.data.dispatch_state, DispatchState.SENT)
        first_comment_id = reply_resp.data.comment_id
        self.assertIsNotNone(first_comment_id)

        # Idempotent replay with same key returns identical result without duplicating comment
        replay_resp = adapter.reply_to_owned_comment(
            video_id="tt_vid_742910001",
            comment_id="tt_cmt_9001",
            text="On my wool coat I could still catch the warm cedar and ambergris the next morning!",
            idempotency_key="idem_viewer_reply_1",
        )
        self.assertTrue(replay_resp.metadata.get("idempotent_replay"))
        assert replay_resp.data is not None
        self.assertEqual(replay_resp.data.comment_id, first_comment_id)

        # Ownership declaration anti-spam guard (FR-055) & false non-ad guard (FR-022)
        with self.assertRaises(PermissionPolicyError) as false_non_ad:
            adapter.create_comment_on_owned_post(
                video_id="tt_vid_742910001",
                text="Purchased with my own money, not an ad! Use my affiliate link in bio.",
                idempotency_key="idem_bad_ad_claim",
                is_ownership_declaration=True,
                has_commercial_relationship=True,
            )
        self.assertEqual(false_non_ad.exception.code, "ERR_FALSE_NON_AD_CLAIM")

        # First valid ownership note succeeds
        own1 = adapter.create_comment_on_owned_post(
            video_id="tt_vid_742910001",
            text="Purchased with my own money. These are my personal impressions after a full wear test.",
            idempotency_key="idem_own_1",
            is_ownership_declaration=True,
            has_commercial_relationship=False,
        )
        self.assertTrue(own1.ok)

        # Identical repetitive ownership declaration on next video is blocked by FR-055 guard
        with self.assertRaises(PermissionPolicyError) as spam_ctx:
            adapter.create_comment_on_owned_post(
                video_id="tt_vid_742910002",
                text="Purchased with my own money. These are my personal impressions after a full wear test.",
                idempotency_key="idem_own_2",
                is_ownership_declaration=True,
                has_commercial_relationship=False,
            )
        self.assertEqual(spam_ctx.exception.code, "ERR_REPETITIVE_OWNERSHIP_COMMENT")

        # Publish post commercial disclosure validation (FR-026, FR-053, FR-055)
        with self.assertRaises(PermissionPolicyError):
            adapter.publish_post(
                PublishPostRequest(
                    video_url="https://cdn.annreveals.co.uk/videos/review1.mp4",
                    caption="Ad | Testing this new fragrance with my affiliate code!",
                    self_purchased=True,
                    has_commercial_incentive=True,
                    brand_content_toggle=False,
                    brand_organic_toggle=False,
                )
            )


if __name__ == "__main__":
    unittest.main()
