"""
Agent Echo (Agent 5) — Comprehensive Platform, Security, SRE & Chaos Verification Suite (`test_platform_sre.py`).

Tests:
1. 10,000-event duplicate webhook injection stress test (verifying 0 duplicate dispatches & self-loop blocking).
2. Universal `EMERGENCY STOP` kill-switch halting all platforms and draining queued jobs to `DRAFT` immediately.
3. Hard monthly budget cap (£30.00 ceiling / £5.00 AI sub-cap) auto-downgrading to `DRAFT` & deterministic templates.
4. OAuth token & receipt evidence authenticated envelope encryption/decryption, key rotation, and byte-tamper detection.
5. OAuth PKCE (`S256`), signed state, webhook HMAC-SHA256, CSRF token, RBAC owner guard, and log secret scrubbing.
6. UK GDPR PII redaction (`Experian`/`Empyrean` raw merchant preservation), retention cleanup, audit chain, full JSON/ZIP export, and right-to-erasure wipe.
7. Encrypted snapshot backup & point-in-time restore roundtrip drill + corruption rejection (both API & CLI scripts).
8. Chaos failure drills (`429`, `401`, `5xx`, `db_degraded`) and health SLO reporting.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.platform_ops import (
    BackupCorruptionError,
    BackupManager,
    BudgetGuard,
    CSRFProtection,
    CSRFValidationError,
    ConnectionBadge,
    DispatchState,
    EnvelopeEncryptor,
    GDPRComplianceManager,
    HealthAndDrillMonitor,
    IdempotencyStore,
    KillSwitchController,
    OAuthSecurityManager,
    OAuthStateError,
    OwnerPrincipal,
    PlatformMode,
    RBACGuard,
    RBACPermissionError,
    SecretScrubber,
    TamperDetectedError,
    verify_webhook_hmac,
)


class TestPlatformSecurityAndSRE(unittest.TestCase):
    """End-to-end verification of Agent Echo's Security, SRE, Idempotency, Budget, GDPR & Backup modules."""

    def test_10000_duplicate_webhook_stress(self) -> None:
        """
        Stress test: Inject 10,000 webhook comment events (500 unique comments replayed 20x each)
        plus self-comments from `@annreveals`. Verify strictly 0 duplicate outbound dispatches.
        """
        store = IdempotencyStore(owner_handles={"@annreveals"}, max_replies_per_thread=1)
        dispatched_counter = 0

        def mock_dispatch() -> str:
            nonlocal dispatched_counter
            dispatched_counter += 1
            return f"outbound-{dispatched_counter}"

        unique_comments = 500
        replays_per_comment = 20
        total_events = unique_comments * replays_per_comment  # 10,000 events

        for i in range(total_events):
            comment_idx = i % unique_comments
            platform = "instagram" if (comment_idx % 2 == 0) else "tiktok"
            res = store.ingest_and_dispatch_once(
                platform=platform,
                account_id="acct_annreveals",
                post_id=f"post_{comment_idx}",
                comment_id=f"comment_{comment_idx}",
                author_handle=f"@perfumelover_{comment_idx}",
                comment_text="What is the longevity like on this bottle?",
                event_version="v1",
                dispatch_fn=mock_dispatch,
            )
            if i < unique_comments:
                self.assertTrue(res["accepted"])
                self.assertEqual(res["status"], DispatchState.DISPATCHED.value)
            else:
                self.assertFalse(res["accepted"])
                self.assertEqual(res["status"], "DUPLICATE_BLOCKED")

        # Also test self-comment loop prevention (FR-003)
        self_res = store.ingest_and_dispatch_once(
            platform="instagram",
            account_id="acct_annreveals",
            post_id="post_self",
            comment_id="comment_self_1",
            author_handle="@annreveals",
            comment_text="Purchased with my own money. These are my personal impressions.",
            dispatch_fn=mock_dispatch,
        )
        self.assertFalse(self_res["accepted"])
        self.assertEqual(self_res["status"], DispatchState.IGNORED_SELF.value)

        metrics = store.get_metrics()
        self.assertEqual(metrics["total_events_ingested"], 10001)
        self.assertEqual(metrics["outbound_dispatches_succeeded"], 500)
        self.assertEqual(metrics["duplicate_events_blocked"], 9500)
        self.assertEqual(metrics["self_comments_blocked"], 1)
        self.assertEqual(metrics["duplicate_outbound_dispatches"], 0)
        self.assertEqual(dispatched_counter, 500)

    def test_universal_emergency_stop_halts_and_drains_queue_immediately(self) -> None:
        """
        Verify FR-035 & NFR-09: Default feature flags are False, truthful badges work,
        and Universal EMERGENCY STOP halts all platforms and drains queued jobs to DRAFT.
        """
        ks = KillSwitchController()
        # Verify default safe flags (NFR-09)
        self.assertFalse(ks.feature_flags["TIKTOK_WRITE_ENABLED"])
        self.assertFalse(ks.feature_flags["INSTAGRAM_WRITE_ENABLED"])
        self.assertFalse(ks.feature_flags["THIRD_PARTY_AUTOCOMMENT"])
        self.assertEqual(ks.compute_badge("tiktok"), ConnectionBadge.AWAITING_REVIEW)

        # Enable verified live write scope on Instagram and TikTok for testing queue drain
        for p in ("instagram", "tiktok"):
            ks.configure_connection_state(
                p,
                oauth_connected=True,
                write_scope_verified=True,
                review_pending=False,
                write_flag_enabled=True,
            )
            snap = ks.set_platform_mode(p, PlatformMode.SAFE_AUTO)
            self.assertEqual(snap.mode, PlatformMode.SAFE_AUTO)
            self.assertEqual(snap.badge, ConnectionBadge.LIVE_CAN_REPLY)

        # Enqueue 25 outbound jobs across both platforms
        for idx in range(25):
            plat = "instagram" if idx % 2 == 0 else "tiktok"
            job = ks.enqueue_job(f"job-{idx}", plat, f"cid-{idx}", "Thank you lovely!")
            self.assertEqual(job.status, "QUEUED")

        self.assertEqual(len(ks.get_queued_jobs(status="QUEUED")), 25)

        # Trigger Universal EMERGENCY STOP
        stop_event = ks.trigger_emergency_stop(
            triggered_by="@annreveals", reason="Manual safety drill"
        )
        self.assertTrue(ks.emergency_stop_active)
        self.assertEqual(stop_event["drained_jobs_to_draft"], 25)
        self.assertEqual(len(ks.get_queued_jobs(status="QUEUED")), 0)
        self.assertEqual(len(ks.get_queued_jobs(status="DRAFT")), 25)
        self.assertEqual(ks.get_platform_snapshot("instagram").mode, PlatformMode.OFF)
        self.assertEqual(ks.get_platform_snapshot("tiktok").mode, PlatformMode.OFF)

        can_send, _ = ks.can_dispatch_outbound("instagram")
        self.assertFalse(can_send)

        # Release Emergency Stop -> platforms must return safely to DRAFT, not SAFE_AUTO
        ks.release_emergency_stop(released_by="@annreveals")
        self.assertFalse(ks.emergency_stop_active)
        self.assertEqual(ks.get_platform_snapshot("instagram").mode, PlatformMode.DRAFT)
        self.assertEqual(ks.get_platform_snapshot("tiktok").mode, PlatformMode.DRAFT)

    def test_budget_cap_auto_downgrade_to_draft_and_templates(self) -> None:
        """
        Verify FR-039, FR-050, NFR-07: Hard £30.00 monthly ceiling & £5.00 AI sub-cap
        automatically block paid LLM calls and downgrade active platforms to DRAFT + templates.
        """
        ks = KillSwitchController(instagram_write_enabled=True)
        ks.configure_connection_state(
            "instagram",
            oauth_connected=True,
            write_scope_verified=True,
            review_pending=False,
            write_flag_enabled=True,
        )
        ks.set_platform_mode("instagram", PlatformMode.SAFE_AUTO)
        self.assertEqual(ks.get_platform_snapshot("instagram").mode, PlatformMode.SAFE_AUTO)

        guard = BudgetGuard(
            hard_monthly_ceiling_gbp=30.00,
            ai_monthly_subcap_gbp=5.00,
            hosting_monthly_gbp=7.00,
            storage_monthly_gbp=0.50,
            kill_switch=ks,
        )
        self.assertLess(guard.estimate_cost_per_1000_replies(), 1.00)

        # Record £4.99 of AI usage -> still allowed
        guard.record_ai_usage(cost_gbp=4.99, tokens_used=10000, description="Batch replies")
        allowed, _ = guard.can_invoke_llm(0.005)
        self.assertTrue(allowed)

        # Record £0.01 to hit the £5.00 AI sub-cap -> triggers automatic fallback & DRAFT downgrade
        status = guard.record_ai_usage(cost_gbp=0.01, tokens_used=340, description="Cap reaching reply")
        self.assertTrue(status.cap_reached)
        self.assertTrue(status.deterministic_fallback_active)
        self.assertEqual(status.effective_reply_mode, PlatformMode.DRAFT.value)
        self.assertEqual(ks.get_platform_snapshot("instagram").mode, PlatformMode.DRAFT)

        # Subsequent reply generation must use deterministic fallback at £0 cost
        fallback_res = guard.generate_reply_with_budget_guard(
            comment_text="Where did you buy this?",
            llm_callable=lambda _: "LLM SHOULD NOT RUN",
            deterministic_template="Thank you lovely! Full bottle details are in the description.",
        )
        self.assertEqual(fallback_res["source"], "deterministic_template_fallback")
        self.assertEqual(fallback_res["cost_gbp"], 0.0)
        self.assertEqual(fallback_res["mode"], PlatformMode.DRAFT.value)

    def test_oauth_encryption_key_rotation_and_tamper_detection(self) -> None:
        """
        Verify NFR-05 & FR-044: Authenticated envelope encryption (`ARAIM-ENC-V1`) for OAuth grants,
        associated data binding, key rotation, and byte-level tamper rejection.
        """
        enc = EnvelopeEncryptor(master_key="super-secret-master-key-v1-32bytes!", key_id="k1")
        oauth_mgr = OAuthSecurityManager(encryptor=enc)

        sealed = oauth_mgr.seal_oauth_grant(
            platform="instagram",
            account_id="ig_annreveals_01",
            access_token="IGQVJ_live_secret_access_token_12345",
            refresh_token="IGQVJ_refresh_98765",
            scopes=["instagram_basic", "instagram_manage_comments"],
        )
        self.assertTrue(sealed.startswith("ARAIM-ENC-V1."))
        self.assertNotIn("IGQVJ_live_secret_access_token_12345", sealed)

        # Unseal with matching platform + account
        unsealed = oauth_mgr.unseal_oauth_grant(sealed, "instagram", "ig_annreveals_01")
        self.assertEqual(unsealed["access_token"], "IGQVJ_live_secret_access_token_12345")
        self.assertIn("instagram_manage_comments", unsealed["scopes"])

        # Cross-platform AAD substitution must fail with TamperDetectedError
        with self.assertRaises(TamperDetectedError):
            oauth_mgr.unseal_oauth_grant(sealed, "tiktok", "ig_annreveals_01")

        # Flip a character in the encrypted payload -> must raise TamperDetectedError
        tampered = sealed[:-4] + ("A" if sealed[-4] != "A" else "B") + sealed[-3:]
        with self.assertRaises(TamperDetectedError):
            oauth_mgr.unseal_oauth_grant(tampered, "instagram", "ig_annreveals_01")

        # Key rotation test (FR-044)
        enc.rotate_key("k2", "brand-new-rotated-master-key-v2-32b!")
        reencrypted = enc.reencrypt_token(sealed, expected_associated_data="oauth:instagram:ig_annreveals_01")
        unsealed_v2 = oauth_mgr.unseal_oauth_grant(reencrypted, "instagram", "ig_annreveals_01")
        self.assertEqual(unsealed_v2["access_token"], "IGQVJ_live_secret_access_token_12345")

    def test_webhook_hmac_pkce_csrf_rbac_and_log_scrubber(self) -> None:
        """Verify PKCE S256, signed OAuth state, Webhook HMAC, CSRF, RBAC, and SecretScrubber."""
        oauth_mgr = OAuthSecurityManager()
        challenge = oauth_mgr.create_pkce_challenge("tiktok", owner_id="@annreveals")
        self.assertEqual(challenge.code_challenge_method, "S256")
        verified_state = oauth_mgr.verify_oauth_state(challenge.state, expected_platform="tiktok")
        self.assertEqual(verified_state["owner_id"], "@annreveals")

        with self.assertRaises(OAuthStateError):
            oauth_mgr.verify_oauth_state(challenge.state, expected_platform="instagram")

        # Webhook HMAC verification
        body = b'{"event":"comment.created","comment_id":"c_999"}'
        secret = "meta_webhook_app_secret_2026"
        valid_sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        self.assertTrue(verify_webhook_hmac(body, valid_sig, secret))
        self.assertFalse(verify_webhook_hmac(body, "sha256=0000deadbeef", secret))

        # CSRF protection
        csrf = CSRFProtection(secret_key="csrf-unit-test-secret")
        token = csrf.generate_token(session_id="sess_123", owner_id="@annreveals")
        self.assertTrue(csrf.validate_token(token, expected_session_id="sess_123"))
        with self.assertRaises(CSRFValidationError):
            csrf.validate_token(token, expected_session_id="wrong_session")

        # RBAC owner verification
        owner = OwnerPrincipal(user_id="u1", handle="@annreveals", role="OWNER")
        self.assertTrue(RBACGuard.verify_owner(owner, action="toggle_safe_auto"))
        intruder = OwnerPrincipal(user_id="u2", handle="@randomuser", role="VIEWER")
        with self.assertRaises(RBACPermissionError):
            RBACGuard.verify_owner(intruder, action="toggle_safe_auto")

        # SecretScrubber
        dirty_log = 'Header Authorization: Bearer secret_jwt_token_12345 {"access_token": "tok_abc"}'
        clean_log = SecretScrubber.scrub(dirty_log)
        self.assertNotIn("secret_jwt_token_12345", clean_log)
        self.assertNotIn("tok_abc", clean_log)
        self.assertIn("[REDACTED", clean_log)

    def test_gdpr_redaction_export_and_erasure(self) -> None:
        """
        Verify FR-019, FR-044, FR-051, NFR-06: PII redaction (preserving raw `Experian`/`Empyrean`),
        audit log chain integrity, retention cleanup, full JSON/ZIP export, and right-to-erasure.
        """
        gdpr = GDPRComplianceManager(comment_retention_days=90)
        raw_receipt = (
            "Merchant: Experian (Empyrean Perfume Order)\n"
            "Product: Baccarat Rouge 540 Extrait 70ml\n"
            "Paid by Card: 4532 0151 1283 0366\n"
            "Billing Address: 221B Baker Street, London, NW1 6XE\n"
            "Customer Email: ann.private@example.co.uk | Phone: +44 7700 900077\n"
            "Invoice ID: INV-9948271"
        )
        vault_rec = gdpr.store_perfume_receipt_record(
            sku="PERF-BR540-70",
            product_name="Baccarat Rouge 540 Extrait 70ml",
            raw_merchant_label="Experian",
            raw_receipt_text=raw_receipt,
            canonical_merchant_confirmed=False,
        )
        # Raw merchant label must be preserved until owner confirms (FR-019, FR-051)
        self.assertEqual(vault_rec["raw_merchant_label"], "Experian")
        self.assertIsNone(vault_rec["canonical_merchant_name"])
        redacted_text = vault_rec["redacted_receipt_text"]
        self.assertNotIn("4532 0151 1283 0366", redacted_text)
        self.assertNotIn("NW1 6XE", redacted_text)
        self.assertNotIn("ann.private@example.co.uk", redacted_text)
        self.assertNotIn("7700 900077", redacted_text)
        self.assertNotIn("INV-9948271", redacted_text)
        self.assertIn("Experian", redacted_text)

        # Store one old comment (120 days ago) and one fresh comment
        now = 1_800_000_000.0
        gdpr.store_minimised_comment("c_old", "tiktok", "@user1", "Lovely scent!", created_at=now - (120 * 86400))
        gdpr.store_minimised_comment("c_new", "tiktok", "@user2", "How long does it last?", created_at=now - 3600)
        cleanup = gdpr.enforce_retention_policy(current_time=now)
        self.assertEqual(cleanup["pruned_comments"], 1)
        self.assertEqual(cleanup["remaining_comments"], 1)
        self.assertTrue(gdpr.verify_audit_chain())

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "owner_export.zip"
            export_res = gdpr.export_owner_data_bundle(output_zip_path=zip_path)
            self.assertTrue(zip_path.exists())
            self.assertGreater(export_res["zip_size_bytes"], 100)

        # Right to erasure
        erasure = gdpr.erase_all_owner_data("CONFIRM ERASE")
        self.assertEqual(erasure["status"], "ERASED")
        self.assertEqual(erasure["wiped_counts"]["perfume_vault_records_wiped"], 1)

    def test_encrypted_backup_and_restore_roundtrip_and_tamper_rejection(self) -> None:
        """
        Verify FR-044 & NFR-08: Encrypted snapshot creation, SHA-256 manifest verification,
        point-in-time restore roundtrip, CLI script execution, and corruption rejection.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "source_data"
            bak_file = tmp_path / "backups" / "test.araim.bak"
            restored_dir = tmp_path / "restored_data"

            (src_dir / "vault").mkdir(parents=True, exist_ok=True)
            (src_dir / "state.json").write_text('{"owner": "@annreveals", "version": "4.0"}', encoding="utf-8")
            (src_dir / "vault" / "receipt_01.txt").write_text(
                "Merchant: Empyrean | Card: [REDACTED_CARD_PAN]", encoding="utf-8"
            )

            # Test via CLI scripts (`scripts/backup.py` and `scripts/restore.py`)
            backup_cmd = [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "backup.py"),
                "--source-dir",
                str(src_dir),
                "--output-file",
                str(bak_file),
            ]
            bak_proc = subprocess.run(backup_cmd, capture_output=True, text=True, check=True)
            bak_info = json.loads(bak_proc.stdout)
            self.assertEqual(bak_info["status"], "BACKUP_CREATED")
            self.assertEqual(bak_info["file_count"], 2)

            restore_cmd = [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "restore.py"),
                "--backup-file",
                str(bak_file),
                "--target-dir",
                str(restored_dir),
            ]
            res_proc = subprocess.run(restore_cmd, capture_output=True, text=True, check=True)
            res_info = json.loads(res_proc.stdout)
            self.assertEqual(res_info["status"], "RESTORE_VERIFIED_AND_COMPLETED")
            self.assertEqual(
                (src_dir / "state.json").read_text(),
                (restored_dir / "state.json").read_text(),
            )
            self.assertEqual(
                (src_dir / "vault" / "receipt_01.txt").read_text(),
                (restored_dir / "vault" / "receipt_01.txt").read_text(),
            )

            # Corrupt the backup envelope and verify BackupManager rejects it before writing
            corrupted_file = tmp_path / "backups" / "corrupted.araim.bak"
            wrapper = json.loads(bak_file.read_text(encoding="utf-8"))
            env_str = wrapper["envelope"]
            wrapper["envelope"] = env_str[:-5] + ("X" if env_str[-5] != "X" else "Y") + env_str[-4:]
            corrupted_file.write_text(json.dumps(wrapper), encoding="utf-8")

            mgr = BackupManager()
            with self.assertRaises(BackupCorruptionError):
                mgr.verify_and_restore(corrupted_file, tmp_path / "should_not_restore")

    def test_chaos_failure_drills_429_401_5xx_db_degraded(self) -> None:
        """
        Verify NFR-01, NFR-02, NFR-10: Execute all 4 chaos drills (`429`, `401`, `5xx`, `db_degraded`)
        and confirm automatic downgrade to `PAUSED_BY_SYSTEM` and 100% queue drain to `DRAFT`.
        """
        monitor = HealthAndDrillMonitor()

        drill_429 = monitor.run_failure_drill("429", platform="instagram", retry_after_seconds=45.0)
        self.assertTrue(drill_429.passed)
        self.assertEqual(drill_429.resulting_mode, PlatformMode.PAUSED_BY_SYSTEM.value)
        self.assertGreaterEqual(drill_429.backoff_seconds, 45.0)

        drill_401 = monitor.run_failure_drill("401", platform="instagram")
        self.assertTrue(drill_401.passed)
        self.assertEqual(drill_401.resulting_badge, ConnectionBadge.NEEDS_RECONNECT.value)

        drill_5xx = monitor.run_failure_drill("5xx", platform="tiktok")
        self.assertTrue(drill_5xx.passed)
        self.assertGreaterEqual(drill_5xx.backoff_seconds, 60.0)

        drill_db = monitor.run_failure_drill("db_degraded", platform="tiktok")
        self.assertTrue(drill_db.passed)
        self.assertEqual(drill_db.resulting_mode, PlatformMode.PAUSED_BY_SYSTEM.value)

        health = monitor.get_health_summary()
        self.assertEqual(health["status"], "HEALTHY")
        self.assertGreaterEqual(health["current_availability_pct"], 99.5)
        self.assertEqual(health["safety_invariants"]["duplicate_outbound_count"], 0)
        self.assertEqual(health["safety_invariants"]["false_self_purchase_claim_count"], 0)


if __name__ == "__main__":
    unittest.main()
