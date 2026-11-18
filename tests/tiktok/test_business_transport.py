"""Exercise TikTok Accounts API wire contracts with an injected transport."""

import json
import unittest
import urllib.error
import urllib.parse

from apps.backend.integrations.tiktok import (
    CapabilityStatus,
    ConnectionBadge,
    DispatchState,
    OperationalMode,
    RateLimitExceededError,
    SecurityConfigurationError,
    TikTokAdapter,
    TikTokIntegrationError,
    TikTokWebhookVerifier,
)


class TestBusinessTransport(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.responses = []
        self.adapter = TikTokAdapter(
            business_id="approved-account",
            handle="@owner",
            access_token="test-access-token",
            accounts_api_approved=True,
            write_enabled=True,
            operational_mode=OperationalMode.SAFE_AUTO,
            http_transport=self.transport,
        )

    def transport(self, request, timeout):
        self.requests.append(request)
        status, payload = self.responses.pop(0)
        if isinstance(payload, OSError):
            raise payload
        return status, {}, json.dumps(payload).encode()

    def response(self, data):
        self.responses.append((200, {"code": 0, "data": data, "request_id": "tiktok-request-1"}))

    def approve(self, scopes="video.list,comment.list,comment.list.manage"):
        self.response({"app_id": "test-app", "creator_id": "approved-account", "scope": scopes})
        return self.adapter.inspect_access_token("test-app")

    def test_permission_inspector_binds_app_and_account_and_uses_provider_scopes(self):
        self.assertEqual(
            self.approve("video.list, comment.list"),
            frozenset(("video.list", "comment.list")),
        )
        inspected = self.requests[-1]
        self.assertEqual(inspected.get_method(), "POST")
        self.assertTrue(inspected.full_url.endswith("/tt_user/token_info/get/"))
        self.assertEqual(
            json.loads(inspected.data), {"app_id": "test-app", "access_token": "test-access-token"}
        )
        self.assertIsNone(inspected.get_header("Access-token"))
        self.assertEqual(self.adapter.get_connection_badge(), ConnectionBadge.CONNECTED_READ_ONLY)
        self.response({"app_id": "test-app", "creator_id": "other-account", "scope": "comment.list.manage"})
        with self.assertRaises(SecurityConfigurationError):
            self.adapter.inspect_access_token("test-app")
        self.assertEqual(
            self.adapter.get_capability_status("reply_to_owned_comment"),
            CapabilityStatus.AWAITING_APPROVAL,
        )
        self.assertFalse(self.adapter.write_enabled)

    def test_reads_provider_video_pages_and_comment_ownership(self):
        self.approve()
        self.response({"videos": [{"item_id": "501", "caption": "A review"}], "has_more": True, "cursor": 7})
        posts = self.adapter.get_owned_posts()
        self.assertEqual(posts.data[0].video_id, "501")
        self.assertTrue(posts.metadata["has_more"])
        self.assertEqual(posts.metadata["cursor"], 7)
        get_posts = self.requests[-1]
        url = urllib.parse.urlsplit(get_posts.full_url)
        self.assertEqual(url.path, "/open_api/v1.3/business/video/list/")
        self.assertEqual(urllib.parse.parse_qs(url.query)["business_id"], ["approved-account"])
        self.assertEqual(get_posts.get_header("Access-token"), "test-access-token")
        self.assertIsNone(get_posts.get_header("Authorization"))
        self.assertIn("item_id", json.loads(urllib.parse.parse_qs(url.query)["fields"][0]))
        self.response({
            "comments": [
                {"comment_id": "701", "video_id": "501", "owner": True, "status": "PUBLIC", "replies": 1,
                 "reply_list": [{"comment_id": 702, "video_id": 501, "owner": False, "status": "HIDDEN"}]},
                {"comment_id": "703", "video_id": "501", "username": "other"},
            ],
            "cursor": 4,
            "has_more": True,
        })
        comments = self.adapter.list_owned_comments("501", cursor=2)
        self.assertEqual(comments.metadata["cursor"], 4)
        self.assertTrue(comments.data[0].is_self_author)
        self.assertEqual(comments.data[0].reply_count, 1)
        self.assertEqual(comments.data[1].parent_comment_id, "701")
        self.assertTrue(comments.data[1].is_reply)
        self.assertEqual(comments.data[1].status, "HIDDEN")
        self.assertEqual(comments.data[2].status, "UNKNOWN")
        params = urllib.parse.parse_qs(urllib.parse.urlsplit(self.requests[-1].full_url).query)
        self.assertEqual(params["max_count"], ["20"])
        self.assertEqual(params["cursor"], ["2"])
        self.assertNotIn("max_results", params)

    def test_reads_reply_thread_back_with_required_tiktok_identifiers(self):
        self.approve()
        self.response({"comments": [{"comment_id": "903", "owner": True, "status": "PUBLIC"}]})
        response = self.adapter.list_comment_replies("501", "701")
        self.assertEqual(response.data[0].comment_id, "903")
        self.assertEqual(response.data[0].parent_comment_id, "701")
        self.assertTrue(response.data[0].is_self_author)
        self.assertFalse(response.metadata["has_more"])
        request = urllib.parse.urlsplit(self.requests[-1].full_url)
        self.assertEqual(request.path, "/open_api/v1.3/business/comment/reply/list/")
        query = urllib.parse.parse_qs(request.query)
        self.assertEqual(query["comment_id"], ["701"])
        self.assertEqual(query["video_id"], ["501"])

    def test_reply_requires_an_upstream_id_and_preserves_the_confirmed_id(self):
        self.approve()
        self.response({"comment_id": "805", "video_id": "501", "parent_comment_id": "701"})
        posted = self.adapter.reply_to_owned_comment("501", "701", "Lovely, thank you!", "job-1")
        self.assertTrue(posted.ok)
        self.assertEqual(posted.data.dispatch_state, DispatchState.SENT)
        self.assertEqual(posted.data.comment_id, "805")
        self.assertEqual(posted.metadata["request_id"], "tiktok-request-1")
        request = self.requests[-1]
        self.assertEqual(request.get_method(), "POST")
        self.assertTrue(request.full_url.endswith("/business/comment/reply/create/"))
        self.assertEqual(json.loads(request.data), {
            "business_id": "approved-account", "video_id": "501", "comment_id": "701",
            "text": "Lovely, thank you!",
        })
        self.response({})
        pending = self.adapter.reply_to_owned_comment("501", "703", "Thank you!", "job-2")
        self.assertFalse(pending.ok)
        self.assertEqual(pending.data.dispatch_state, DispatchState.RECONCILE_PENDING)
        self.assertIsNone(pending.data.comment_id)
        before = len(self.requests)
        replay = self.adapter.reply_to_owned_comment("501", "703", "Thank you!", "job-2")
        self.assertEqual(replay.data.dispatch_state, DispatchState.RECONCILE_PENDING)
        self.assertEqual(len(self.requests), before)

    def test_rejected_or_unconfirmed_dispatches_never_report_sent(self):
        self.approve()
        self.responses.append((200, {"code": 40002, "message": "Parameter error"}))
        with self.assertRaises(TikTokIntegrationError) as rejected:
            self.adapter.reply_to_owned_comment("501", "701", "Thanks!", "job-1")
        self.assertEqual(rejected.exception.code, "ERR_TIKTOK_40002")
        self.responses.append((200, urllib.error.URLError(TimeoutError())))
        pending = self.adapter.reply_to_owned_comment("501", "702", "Thank you!", "job-2")
        self.assertEqual(pending.data.dispatch_state, DispatchState.RECONCILE_PENDING)
        self.responses.append((200, {"code": 40105, "message": "Expired token"}))
        denied = self.adapter.reply_to_owned_comment("501", "703", "Thank you!", "job-3")
        self.assertEqual(denied.data.dispatch_state, DispatchState.DRAFT_ONLY)
        self.assertEqual(self.adapter.get_connection_badge(), ConnectionBadge.NEEDS_RECONNECT)

    def test_pagination_shape_cannot_claim_success_without_a_moving_cursor(self):
        self.approve()
        self.response({"videos": [], "cursor": 2, "has_more": True})
        with self.assertRaises(TikTokIntegrationError):
            self.adapter.get_owned_posts(cursor=2)

    def test_provider_rate_limit_blocks_followup_before_transport(self):
        self.approve()
        self.responses.append((200, {"code": 40100, "message": "Requests made too frequently"}))
        with self.assertRaises(RateLimitExceededError):
            self.adapter.get_owned_posts()
        before = len(self.requests)
        with self.assertRaises(RateLimitExceededError):
            self.adapter.list_owned_comments("501")
        self.assertEqual(len(self.requests), before)

    def test_business_webhook_accepts_serialized_content_from_configured_app_and_account(self):
        verifier = TikTokWebhookVerifier("test-secret", "approved-account", expected_client_key="test-app")
        signed_at = 1761570000
        payload = {
            "client_key": "test-app",
            "event": "comment.update",
            "user_openid": "approved-account",
            "create_time": signed_at,
            "content": json.dumps({"video_id": "501", "comment_id": "701", "text": "Lovely!", "owner": True}),
        }

        def verify(payload, at=signed_at):
            raw = json.dumps(payload).encode()
            header = verifier.build_signature_header("test-secret", at, raw)
            return verifier.verify_and_parse(raw, header, now_epoch=at)

        result = verify(payload)
        self.assertEqual(result.video_id, "501")
        self.assertEqual(result.comment.comment_id, "701")
        self.assertTrue(result.should_ignore_self_comment)
        with self.assertRaises(SecurityConfigurationError) as duplicate:
            verify(payload, signed_at + 1)
        self.assertEqual(duplicate.exception.code, "ERR_WEBHOOK_REPLAY_DETECTED")
        with self.assertRaises(SecurityConfigurationError):
            verify({**payload, "user_openid": "other-account"})
        with self.assertRaises(SecurityConfigurationError):
            verify({**payload, "client_key": "other-app"})


if __name__ == "__main__":
    unittest.main()
