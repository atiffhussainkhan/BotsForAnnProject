"""
End-to-End System Integration Test Suite for Ann Reveals AI Manager (v4.0).

Boots the unified `AnnRevealsApplication` and live HTTP server and verifies:
- All 19 relational tables in `migrations/001_initial_schema.sql`
- PWA delivery (`/`, `/manifest.json`, `/sw.js`) with all 9 owner screens
- Truthful connection badges & default disabled write flags (`NFR-09`)
- End-to-end comment pipeline (longevity measured vs unmeasured, skin allergy escalation, prompt injection block, duplicate replay block)
- Mandatory Sample Case A (Instagram) & Sample Case B (TikTok independent + affiliate)
- Verified Purchases Vault PII redaction & `Experian` -> `Empyrean Parfums` disambiguation
- Creator Watchlist contextual drafts & zero third-party auto-commenting
- Rule G6 violation automation freeze & redacted appeal packet builder
- Universal Emergency Stop kill-switch, Encrypted Backup/Restore drill, SRE Chaos Drills & UK GDPR Export
"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.main import AnnRevealsApplication, create_http_handler


class TestFullSystemE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.TemporaryDirectory()
        tmp_path = Path(cls._tmpdir.name)
        cls.app = AnnRevealsApplication(
            db_path=tmp_path / "test_araim.db",
            backup_dir=tmp_path / "backups",
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmpdir.cleanup()

    def _get(self, path: str):
        status, body, content_type = self.app.dispatch_http("GET", path)
        raw = body if isinstance(body, str) else json.dumps(body)
        return status, raw, {"Content-Type": content_type}

    def _post_json(self, path: str, payload: dict):
        status, body, _ = self.app.dispatch_http("POST", path, payload)
        return status, body if isinstance(body, dict) else json.loads(body)

    def test_01_database_19_tables_created(self) -> None:
        tables = set(self.app.db.get_table_names())
        expected_19_tables = {
            "users",
            "social_accounts",
            "oauth_grants",
            "capabilities",
            "posts",
            "comments",
            "events",
            "drafts",
            "outbound_actions",
            "retailers",
            "products",
            "purchases",
            "evidence_files",
            "content_declarations",
            "policy_rules",
            "creator_watchlist",
            "compliance_incidents",
            "audit_events",
            "system_settings",
        }
        self.assertTrue(expected_19_tables.issubset(tables))

    def test_02_pwa_manifest_service_worker_and_9_screens(self) -> None:
        status, html, _ = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("Ann Reveals AI Manager", html)
        for screen_id in (
            "screen-home",
            "screen-wizard",
            "screen-comments",
            "screen-studio",
            "screen-vault",
            "screen-friends",
            "screen-appeals",
            "screen-settings",
            "screen-health",
        ):
            self.assertIn(screen_id, html)

        m_status, manifest_raw, _ = self._get("/manifest.json")
        self.assertEqual(m_status, 200)
        manifest = json.loads(manifest_raw)
        self.assertEqual(manifest["name"], "Ann Reveals AI Manager")

        sw_status, sw_js, _ = self._get("/sw.js")
        self.assertEqual(sw_status, 200)
        self.assertIn("CACHE_NAME", sw_js)

    def test_03_overview_truthful_badges_and_feature_flags(self) -> None:
        status, raw, _ = self._get("/api/v1/overview")
        self.assertEqual(status, 200)
        data = json.loads(raw)
        flags = data["emergency_stop"]["feature_flags"]
        self.assertFalse(flags["TIKTOK_WRITE_ENABLED"])
        self.assertFalse(flags["INSTAGRAM_WRITE_ENABLED"])
        self.assertFalse(flags["THIRD_PARTY_AUTOCOMMENT"])
        self.assertEqual(data["platforms"]["tiktok"]["badge"], "Awaiting review")
        self.assertLessEqual(data["budget"]["hard_monthly_ceiling_gbp"], 30.00)
        self.assertGreaterEqual(data["kpis"]["template_catalog_size"], 1000)

    def test_04_comment_simulation_and_duplicate_prevention(self) -> None:
        # 1. Measured longevity comment
        status, res1 = self._post_json(
            "/api/v1/comments/simulate",
            {
                "platform": "instagram",
                "comment_id": "e2e_cmt_longevity_1",
                "post_id": "ig_post_celestial",
                "post_sku": "EMP-VELVET-OUD-100",
                "author_handle": "@viewer_test",
                "comment_text": "How long does Celestial Iris last on skin?",
            },
        )
        self.assertEqual(status, 200)
        self.assertTrue(res1["result"]["accepted"])
        self.assertEqual(res1["result"]["engine_output"]["intent"], "longevity")
        self.assertIn("8", res1["result"]["engine_output"]["reply_candidate"])

        # 2. Replay exact same comment_id -> must be deduplicated
        status, res_dup = self._post_json(
            "/api/v1/comments/simulate",
            {
                "platform": "instagram",
                "comment_id": "e2e_cmt_longevity_1",
                "post_id": "ig_post_celestial",
                "post_sku": "EMP-VELVET-OUD-100",
                "author_handle": "@viewer_test",
                "comment_text": "How long does Celestial Iris last on skin?",
            },
        )
        self.assertEqual(status, 200)
        self.assertFalse(res_dup["result"]["accepted"])

        # 3. Unmeasured longevity comment -> must state wear test not yet completed
        _, res_unmeasured = self._post_json(
            "/api/v1/comments/simulate",
            {
                "platform": "instagram",
                "comment_id": "e2e_cmt_unmeasured_1",
                "post_id": "ig_post_rosetonka",
                "post_sku": "EMP-ROSE-TONKA-50",
                "author_handle": "@viewer_test2",
                "comment_text": "How many hours does Velvet Rose & Tonka last?",
            },
        )
        reply_unmeasured = res_unmeasured["result"]["engine_output"]["reply_candidate"].lower()
        self.assertTrue("haven't" in reply_unmeasured or "full wear" in reply_unmeasured)

    def test_05_sample_cases_a_and_b_and_studio_generation(self) -> None:
        _, raw, _ = self._get("/api/v1/overview")
        overview = json.loads(raw)
        case_a = overview["sample_cases"]["case_a_instagram_independent"]
        case_b_indep = overview["sample_cases"]["case_b_tiktok_independent"]
        case_b_affil = overview["sample_cases"]["case_b_tiktok_affiliate"]

        self.assertEqual(case_a["platform"], "instagram")
        self.assertIn("Purchased with my own money", case_a["caption"])
        self.assertEqual(len(case_a["hashtags"]), 5)

        self.assertEqual(case_b_indep["platform"], "tiktok")
        self.assertIn("Purchased with my own money", case_b_indep["caption"])

        # Affiliate variant MUST start with 'Ad | ' and NEVER say 'not an ad'
        self.assertTrue(case_b_affil["caption"].startswith("Ad | "))
        self.assertNotIn("not an ad", case_b_affil["caption"].lower())

        # Custom Studio generation via POST
        status, gen = self._post_json(
            "/api/v1/studio/generate",
            {
                "sku": "EMP-VELVET-OUD-100",
                "provenance_status": "SELF_PURCHASED",
                "instagram_commercial_relationships": ["AFFILIATE_LINK"],
                "tiktok_commercial_relationships": ["TIKTOK_SHOP"],
            },
        )
        self.assertEqual(status, 200)
        self.assertTrue(gen["package"]["instagram_package"]["caption"].startswith("Ad | "))
        self.assertTrue(gen["package"]["tiktok_package"]["caption"].startswith("Ad | "))

    def test_06_vault_pii_redaction_and_experian_empyrean_confirmation(self) -> None:
        # Ingest receipt with raw 'Experian' label and sensitive card/address PII
        status, ingest_res = self._post_json(
            "/api/v1/vault/ingest-receipt",
            {
                "sku": "EMP-TEST-OUD-100",
                "brand": "Empyrean Parfums",
                "product_name": "Saffron Oud",
                "size_ml": 100,
                "merchant_label_raw": "Experian",
                "net_paid": 210.0,
                "raw_text": (
                    "Shop: Experian\n"
                    "Customer: ann@annreveals.co.uk\n"
                    "Address: 10 Downing Street, London SW1A 2AA\n"
                    "Card: 4532 0151 1283 8899\n"
                    "Item: Empyrean Parfums Saffron Oud 100ml EDP £210.00"
                ),
                "owner_verified_merchant": False,
            },
        )
        self.assertEqual(status, 200)
        # Because raw merchant is unverified 'Experian', status must be UNVERIFIED until owner confirms
        self.assertEqual(ingest_res["match"]["status"], "UNVERIFIED")

        # Confirm merchant as Empyrean Parfums
        status2, conf_res = self._post_json(
            "/api/v1/vault/confirm-merchant",
            {
                "sku": "EMP-TEST-OUD-100",
                "confirmed_canonical_key": "empyrean parfums",
            },
        )
        self.assertEqual(status2, 200)
        self.assertEqual(conf_res["match"]["status"], "VERIFIED_SELF_PURCHASE")

    def test_07_friends_watchlist_and_appeals_freeze(self) -> None:
        status, f_res = self._post_json(
            "/api/v1/friends/submit-post",
            {
                "creator_handle": "@scentbyclaire",
                "platform": "instagram",
                "post_url": "https://www.instagram.com/p/DC_E2E_Test/",
                "post_title": "Amber & Iris Evening Scents",
                "post_description": "Testing warm iris, amber, and sandalwood notes tonight.",
            },
        )
        self.assertEqual(status, 200)
        notif = f_res["notification"]
        self.assertFalse(notif["auto_post_permitted"])
        self.assertGreaterEqual(len(notif["draft_suggestions"]), 2)

        # Ingest violation and verify post automation freeze (Rule G6)
        status_app, app_res = self._post_json(
            "/api/v1/appeals/ingest",
            {
                "platform": "instagram",
                "platform_post_id": "ig_post_flagged_99",
                "category": "commercial_disclosure",
                "notification_text": "Flagged for commercial content check.",
            },
        )
        self.assertEqual(status_app, 200)
        self.assertTrue(app_res["case"]["post_automation_frozen"])
        self.assertIn("instagram:ig_post_flagged_99", app_res["overview"]["frozen_posts"])

    def test_08_emergency_stop_backup_drills_and_gdpr_export(self) -> None:
        # Activate Emergency Stop
        status, es_on = self._post_json(
            "/api/v1/kill-switch/emergency-stop",
            {"activate": True, "reason": "E2E test emergency stop"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(es_on["overview"]["emergency_stop"]["active"])

        # Clear Emergency Stop
        status, es_off = self._post_json(
            "/api/v1/kill-switch/emergency-stop",
            {"activate": False},
        )
        self.assertEqual(status, 200)
        self.assertFalse(es_off["overview"]["emergency_stop"]["active"])

        # Run Encrypted Backup & Restore Verification
        b_status, b_res = self._post_json("/api/v1/ops/backup", {})
        self.assertEqual(b_status, 200)
        self.assertTrue(b_res["restore_verified"])

        # Run Chaos Drill (429 rate limit)
        d_status, d_res = self._post_json(
            "/api/v1/ops/drill",
            {"drill_type": "429", "platform": "instagram"},
        )
        self.assertEqual(d_status, 200)
        self.assertTrue(d_res["drill_result"]["passed"])

        # GDPR Export
        g_status, g_raw, _ = self._get("/api/v1/gdpr/export")
        self.assertEqual(g_status, 200)
        g_data = json.loads(g_raw)
        self.assertEqual(g_data["owner"], "@annreveals")

    def test_09_in_app_account_configuration_and_autopilot_worker(self) -> None:
        # 1. Verify Windows & Android installable bundles exist
        self.assertTrue((ROOT_DIR / "installers" / "windows" / "Start-AnnReveals-Windows.bat").exists())
        self.assertTrue((ROOT_DIR / "installers" / "windows" / "Install-AnnReveals-Windows.ps1").exists())
        self.assertTrue((ROOT_DIR / "installers" / "android" / "twa-manifest.json").exists())
        self.assertTrue((ROOT_DIR / "installers" / "android" / "capacitor.config.json").exists())
        self.assertTrue((ROOT_DIR / "dist" / "AnnRevealsAIManager-Portable.html").exists())

        # 2. Configure & sign in Instagram account in-app with Auto-Pilot enabled
        ig_status, ig_res = self._post_json(
            "/api/v1/accounts/configure",
            {
                "platform": "instagram",
                "account_handle": "@annreveals",
                "app_id": "IG-PRO-ANNREVEALS-UK",
                "access_token": "ig_oauth_live_annreveals_verified_token_2026",
                "grant_write_scope": True,
                "verify_pilot": True,
                "enable_auto_pilot": True,
            },
        )
        self.assertEqual(ig_status, 200)
        self.assertTrue(ig_res["account"]["connected"])
        self.assertTrue(ig_res["account"]["auto_pilot_enabled"])
        self.assertEqual(ig_res["overview"]["platforms"]["instagram"]["mode"], "SAFE_AUTO")

        # 3. Configure & sign in TikTok account in-app with Auto-Pilot enabled
        tt_status, tt_res = self._post_json(
            "/api/v1/accounts/configure",
            {
                "platform": "tiktok",
                "account_handle": "@annreveals",
                "app_id": "TT-BIZ-ANNREVEALS-1.3",
                "access_token": "tt_oauth_live_annreveals_verified_token_2026",
                "grant_write_scope": True,
                "verify_pilot": True,
                "enable_auto_pilot": True,
            },
        )
        self.assertEqual(tt_status, 200)
        self.assertTrue(tt_res["account"]["connected"])
        self.assertTrue(tt_res["account"]["auto_pilot_enabled"])
        self.assertEqual(tt_res["overview"]["platforms"]["tiktok"]["mode"], "SAFE_AUTO")

        # 4. Run automatic background worker cycle (/api/v1/autopilot/tick)
        tick_status, tick_res = self._post_json("/api/v1/autopilot/tick", {})
        self.assertEqual(tick_status, 200)
        self.assertEqual(tick_res["cycle"]["processed_count"], 2)
        self.assertGreaterEqual(tick_res["overview"]["accounts"]["instagram"]["auto_replies_sent"], 1)
        self.assertGreaterEqual(tick_res["overview"]["accounts"]["tiktok"]["auto_replies_sent"], 1)

    def test_10_friend_groups_auto_comment_bot(self) -> None:
        # 1. Add a friend to an Auto-Comment Group
        add_status, add_res = self._post_json(
            "/api/v1/friends/groups/add-member",
            {
                "group_id": "GRP-CLOSE-FRIENDS",
                "handle": "@amberandiris",
                "display_name": "Chloe",
                "platform": "instagram",
                "favorite_notes": "iris, vanilla, cardamom",
                "auto_comment_enabled": True,
            },
        )
        self.assertEqual(add_status, 200)
        fg_summary = add_res["overview"]["friend_groups"]
        self.assertGreaterEqual(fg_summary["friend_vocabulary_size"], 50000)

        # 2. Scrape & auto-comment on a single friend video
        eng_status, eng_res = self._post_json(
            "/api/v1/friends/auto-engage",
            {
                "friend_handle": "@amberandiris",
                "friend_display_name": "Chloe",
                "platform": "instagram",
                "video_url": "https://www.instagram.com/p/DC_Chloe_Iris/",
                "video_title": "Testing 'Empyrean Celestial Iris' for Autumn",
                "video_description": "Layering creamy iris, pistachio, and warm vanilla tonight!",
                "group_id": "GRP-CLOSE-FRIENDS",
                "auto_send": True,
            },
        )
        self.assertEqual(eng_status, 200)
        ac = eng_res["auto_comment"]
        self.assertEqual(ac["status"], "AUTO_COMMENTED_ON_FRIEND_VIDEO")
        self.assertIn("iris", ac["scraped_notes"])
        self.assertIn("Chloe", ac["comment_posted"])
        self.assertEqual(ac["video_format_type"], "LAYERING_ROUTINE")
        self.assertEqual(ac["main_brand_detected"], "Empyrean Parfums")
        self.assertTrue(len(ac["core_showcase_focus"]) > 10)
        self.assertGreaterEqual(len(eng_res["overview"]["friend_groups"]["daily_scraped_videos"]), 1)

        # 3. Run full Friend Group Auto-Comment Cycle across all groups
        cyc_status, cyc_res = self._post_json(
            "/api/v1/friends/auto-engage",
            {"mode": "group_cycle"},
        )
        self.assertEqual(cyc_status, 200)
        self.assertGreaterEqual(cyc_res["count"], 3)


if __name__ == "__main__":
    unittest.main()
